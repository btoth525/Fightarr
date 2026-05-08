"""Download queue and history endpoints."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
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


@router.post("/queue/{item_id}/retry")
async def retry_import(
    item_id: int,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Re-run the import pipeline for a FAILED queue item.

    Use after fixing a path mapping or download client config so a stuck
    download can be imported without re-grabbing it from the indexer.
    """
    from app.services.importer import import_download

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

    try:
        await import_download(session, item)
        return {"status": "imported", "id": item_id}
    except FileNotFoundError as exc:
        return {"status": "pending", "message": str(exc)}
    except Exception as exc:
        return {"status": "error", "message": str(exc)}
