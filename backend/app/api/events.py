"""Event endpoints — list, get, monitor, manual search.

This is the rough equivalent of Radarr's /movie endpoints.
"""

from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.event import Event, EventStatus, EventType

router = APIRouter()


# --- Schemas ---------------------------------------------------------------


class EventOut(BaseModel):
    id: int
    slug: str
    title: str
    event_number: int | None
    event_type: EventType
    event_date: date
    venue: str | None
    location: str | None
    main_event: str | None
    co_main_event: str | None
    status: EventStatus
    monitored: bool
    quality: str | None

    model_config = {"from_attributes": True}


class EventUpdate(BaseModel):
    monitored: bool | None = None


# --- Routes ----------------------------------------------------------------


@router.get("/event", response_model=list[EventOut])
async def list_events(
    monitored: bool | None = Query(None, description="Filter by monitored status"),
    upcoming_only: bool = Query(False, description="Only events on/after today"),
    session: AsyncSession = Depends(get_session),
) -> list[Event]:
    stmt = select(Event).order_by(Event.event_date.desc())
    if monitored is not None:
        stmt = stmt.where(Event.monitored == monitored)
    if upcoming_only:
        stmt = stmt.where(Event.event_date >= date.today())
    result = await session.execute(stmt)
    return list(result.scalars().all())


@router.get("/event/{event_id}", response_model=EventOut)
async def get_event(event_id: int, session: AsyncSession = Depends(get_session)) -> Event:
    event = await session.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@router.put("/event/{event_id}", response_model=EventOut)
async def update_event(
    event_id: int,
    update: EventUpdate,
    session: AsyncSession = Depends(get_session),
) -> Event:
    event = await session.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    if update.monitored is not None:
        event.monitored = update.monitored
    await session.commit()
    await session.refresh(event)
    return event


@router.get("/calendar", response_model=list[EventOut])
async def calendar(
    start: date | None = Query(None),
    end: date | None = Query(None),
    session: AsyncSession = Depends(get_session),
) -> list[Event]:
    """Events within a date range. Defaults to next 30 days."""
    start = start or date.today()
    end = end or (start + timedelta(days=30))
    stmt = (
        select(Event)
        .where(Event.event_date >= start)
        .where(Event.event_date <= end)
        .order_by(Event.event_date.asc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


@router.get("/wanted/missing", response_model=list[EventOut])
async def wanted_missing(session: AsyncSession = Depends(get_session)) -> list[Event]:
    """Events that have aired but we don't have a file for."""
    stmt = (
        select(Event)
        .where(Event.monitored.is_(True))
        .where(Event.status == EventStatus.MISSING)
        .order_by(Event.event_date.desc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


@router.post("/command/refresh-schedule")
async def trigger_schedule_refresh() -> dict:
    """Manually kick off a schedule refresh from upstream sources."""
    from app.services.schedule_sync import sync_schedule

    count = await sync_schedule()
    return {"status": "ok", "events_synced": count}
