"""Download queue and history endpoints."""

from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.download_client import DownloadClient
from app.models.event import Event
from app.models.queue_item import QueueItem, QueueStatus

router = APIRouter()

_ACTIVE = {QueueStatus.GRABBED, QueueStatus.DOWNLOADING, QueueStatus.COMPLETED}
_HISTORY = {QueueStatus.IMPORTED, QueueStatus.FAILED}


class QueueItemOut(BaseModel):
    id: int
    event_id: int
    event_title: str | None = None
    event_date: str | None = None
    release_title: str
    release_size_bytes: int | None
    indexer_name: str | None
    download_client_id: int | None
    download_client_name: str | None = None
    status: QueueStatus
    progress_percent: float
    error_message: str | None
    download_path: str | None
    grabbed_at: datetime
    completed_at: datetime | None


async def _enrich(session: AsyncSession, items: list[QueueItem]) -> list[QueueItemOut]:
    if not items:
        return []

    event_ids = list({i.event_id for i in items})
    client_ids = list({i.download_client_id for i in items if i.download_client_id})

    events: dict[int, Event] = {}
    if event_ids:
        r = await session.execute(select(Event).where(Event.id.in_(event_ids)))
        events = {e.id: e for e in r.scalars().all()}

    clients: dict[int, DownloadClient] = {}
    if client_ids:
        r = await session.execute(select(DownloadClient).where(DownloadClient.id.in_(client_ids)))
        clients = {c.id: c for c in r.scalars().all()}

    out = []
    for item in items:
        ev = events.get(item.event_id)
        dc = clients.get(item.download_client_id) if item.download_client_id else None
        out.append(
            QueueItemOut(
                id=item.id,
                event_id=item.event_id,
                event_title=ev.title if ev else None,
                event_date=str(ev.event_date) if ev and ev.event_date else None,
                release_title=item.release_title,
                release_size_bytes=item.release_size_bytes,
                indexer_name=item.indexer_name,
                download_client_id=item.download_client_id,
                download_client_name=dc.name if dc else None,
                status=item.status,
                progress_percent=item.progress_percent,
                error_message=item.error_message,
                download_path=item.download_path,
                grabbed_at=item.grabbed_at,
                completed_at=item.completed_at,
            )
        )
    return out


@router.get("/queue", response_model=list[QueueItemOut])
async def list_queue(session: AsyncSession = Depends(get_session)) -> list[QueueItemOut]:
    """Active downloads (grabbed / downloading / completed-pending-import)."""
    result = await session.execute(
        select(QueueItem).where(QueueItem.status.in_(_ACTIVE)).order_by(QueueItem.grabbed_at.desc())
    )
    return await _enrich(session, list(result.scalars().all()))


@router.get("/queue/history", response_model=list[QueueItemOut])
async def list_history(
    session: AsyncSession = Depends(get_session),
    limit: int = Query(200, le=1000),
) -> list[QueueItemOut]:
    """Completed and failed downloads — the history log."""
    result = await session.execute(
        select(QueueItem)
        .where(QueueItem.status.in_(_HISTORY))
        .order_by(QueueItem.grabbed_at.desc())
        .limit(limit)
    )
    return await _enrich(session, list(result.scalars().all()))


@router.delete("/queue/{item_id}")
async def remove_from_queue(
    item_id: int,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Remove a queue/history item from Fightarr's DB."""
    item = await session.get(QueueItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Queue item not found")
    await session.delete(item)
    await session.commit()
    return {"status": "removed"}


@router.post("/queue/{item_id}/retry", status_code=202)
async def retry_import(
    item_id: int,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Re-queue a FAILED item for import and return immediately (202 Accepted).

    The actual import runs as a background task so the UI doesn't hang waiting
    for a potentially large file move to complete. Poll the queue endpoint to
    see when status flips to IMPORTED.
    """
    item = await session.get(QueueItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Queue item not found")

    if item.status not in (QueueStatus.FAILED, QueueStatus.COMPLETED):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot retry from status '{item.status.value}'",
        )

    item.status = QueueStatus.COMPLETED
    item.import_attempts = 0
    item.error_message = None
    await session.commit()

    # Fire import in the background — returns 202 immediately so the UI
    # doesn't freeze waiting for a large file to be moved across mounts.
    background_tasks.add_task(_run_retry_import, item_id)
    return {"status": "queued", "id": item_id}


async def _run_retry_import(item_id: int) -> None:
    """Background task: run the full import pipeline for a retried item."""
    from app.core.database import AsyncSessionLocal
    from app.services.importer import import_download
    from app.services.queue_monitor import _handle_import_failure, _handle_imported

    async with AsyncSessionLocal() as session:
        item = await session.get(QueueItem, item_id)
        if item is None:
            return
        try:
            await import_download(session, item)
            await session.commit()
            await _handle_imported(item)
        except FileNotFoundError:
            pass  # Leave as COMPLETED — queue monitor will retry next poll
        except Exception:
            await session.commit()
            await _handle_import_failure(item)
