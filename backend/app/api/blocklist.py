"""Blocklist endpoints — manage releases that should never be auto-grabbed."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.blocklist import BlocklistEntry
from app.models.event import Event

router = APIRouter()


class BlocklistOut(BaseModel):
    id: int
    event_id: int | None
    event_title: str | None
    release_title: str
    nzb_url: str | None
    indexer_name: str | None
    reason: str | None
    blocked_at: datetime


@router.get("/blocklist", response_model=list[BlocklistOut])
async def list_blocklist(session: AsyncSession = Depends(get_session)) -> list[BlocklistOut]:
    """Active blocklist entries, newest first."""
    result = await session.execute(
        select(BlocklistEntry).order_by(BlocklistEntry.blocked_at.desc())
    )
    entries = list(result.scalars().all())

    # Batch-load event titles for display
    event_ids = list({e.event_id for e in entries if e.event_id})
    titles: dict[int, str] = {}
    if event_ids:
        ev_result = await session.execute(select(Event).where(Event.id.in_(event_ids)))
        titles = {e.id: e.title for e in ev_result.scalars().all()}

    return [
        BlocklistOut(
            id=e.id,
            event_id=e.event_id,
            event_title=titles.get(e.event_id) if e.event_id else None,
            release_title=e.release_title,
            nzb_url=e.nzb_url,
            indexer_name=e.indexer_name,
            reason=e.reason,
            blocked_at=e.blocked_at,
        )
        for e in entries
    ]


@router.delete("/blocklist/{entry_id}", status_code=204)
async def delete_blocklist_entry(
    entry_id: int, session: AsyncSession = Depends(get_session)
) -> None:
    """Remove a release from the blocklist so auto-search can grab it again."""
    entry = await session.get(BlocklistEntry, entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Blocklist entry not found")
    await session.delete(entry)
    await session.commit()


@router.post("/blocklist/clear")
async def clear_blocklist(session: AsyncSession = Depends(get_session)) -> dict:
    """Wipe the entire blocklist."""
    result = await session.execute(select(BlocklistEntry))
    entries = list(result.scalars().all())
    for e in entries:
        await session.delete(e)
    await session.commit()
    return {"deleted": len(entries)}
