"""Download queue endpoints."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.queue_item import QueueItem, QueueStatus

router = APIRouter()


class QueueItemOut(BaseModel):
    id: int
    event_id: int
    release_title: str
    status: QueueStatus
    progress_percent: float

    model_config = {"from_attributes": True}


@router.get("/queue", response_model=list[QueueItemOut])
async def list_queue(session: AsyncSession = Depends(get_session)) -> list[QueueItem]:
    result = await session.execute(
        select(QueueItem).order_by(QueueItem.grabbed_at.desc())
    )
    return list(result.scalars().all())
