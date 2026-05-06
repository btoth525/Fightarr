"""Download queue and history endpoints."""

from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.queue_item import QueueItem, QueueStatus

router = APIRouter()

_ACTIVE = {QueueStatus.GRABBED, QueueStatus.DOWNLOADING, QueueStatus.COMPLETED}
_HISTORY = {QueueStatus.IMPORTED, QueueStatus.FAILED}


class QueueItemOut(BaseModel):
    id: int
    event_id: int
    release_title: str
    release_size_bytes: int | None
    indexer_name: str | None
    download_client_id: int | None
    status: QueueStatus
    progress_percent: float
    error_message: str | None
    download_path: str | None
    grabbed_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}


@router.get("/queue", response_model=list[QueueItemOut])
async def list_queue(session: AsyncSession = Depends(get_session)) -> list[QueueItem]:
    """Active downloads only (grabbed / downloading / completed-pending-import)."""
    result = await session.execute(
        select(QueueItem).where(QueueItem.status.in_(_ACTIVE)).order_by(QueueItem.grabbed_at.desc())
    )
    return list(result.scalars().all())


@router.get("/queue/history", response_model=list[QueueItemOut])
async def list_history(
    session: AsyncSession = Depends(get_session),
) -> list[QueueItem]:
    """Completed and failed downloads — the history log."""
    result = await session.execute(
        select(QueueItem)
        .where(QueueItem.status.in_(_HISTORY))
        .order_by(QueueItem.completed_at.desc())
        .limit(200)
    )
    return list(result.scalars().all())


@router.delete("/queue/{item_id}")
async def remove_from_queue(
    item_id: int,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Remove a queue item (does not cancel the download in the client)."""
    item = await session.get(QueueItem, item_id)
    if item is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Queue item not found")
    await session.delete(item)
    await session.commit()
    return {"status": "removed"}
