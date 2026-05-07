"""Event endpoints — list, get, monitor, manual search.

This is the rough equivalent of Radarr's /movie endpoints.
"""

import logging
from datetime import date, timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.event import Event, EventStatus, EventType

logger = logging.getLogger(__name__)

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
    poster_url: str | None = None
    tmdb_id: int | None = None
    source_url: str | None = None
    file_path: str | None = None

    model_config = {"from_attributes": True}


class EventUpdate(BaseModel):
    monitored: bool | None = None


class GrabRequest(BaseModel):
    nzb_url: str
    release_title: str
    size_bytes: int | None = None
    indexer_name: str | None = None
    protocol: str = "nzb"  # "nzb" → SAB/NZBGet, "torrent" → qBit/Deluge/Transmission/RD


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
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
) -> Event:
    event = await session.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")

    was_monitored = event.monitored
    if update.monitored is not None:
        event.monitored = update.monitored
    await session.commit()
    await session.refresh(event)

    # Radarr "Search on Monitor" behavior — when the user turns monitor ON for
    # an event that has already aired and we don't have a file yet, kick off
    # an auto-search-and-grab in the background. The HTTP response returns
    # immediately so the UI stays snappy.
    if (
        update.monitored is True
        and not was_monitored
        and event.file_path is None
        and event.event_date is not None
        and event.event_date <= date.today()
    ):
        logger.info("Monitor enabled for event %d — triggering auto-search", event_id)
        background_tasks.add_task(_run_auto_search, event_id)

    return event


async def _run_auto_search(event_id: int) -> None:
    """Wrapper so background_tasks can call our async grab_service."""
    from app.services.grab_service import auto_search_and_grab

    try:
        await auto_search_and_grab(event_id)
    except Exception as exc:
        logger.error("Auto-search task crashed for event %d: %s", event_id, exc)


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


@router.post("/event/{event_id}/refresh-metadata", response_model=EventOut)
async def refresh_event_metadata(
    event_id: int, session: AsyncSession = Depends(get_session)
) -> Event:
    """Fetch/refresh poster for a single event (Wikipedia first, TMDB optional)."""
    from app.services.settings_service import load_settings
    from app.services.tmdb import fetch_event_poster

    event = await session.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")

    db_settings = await load_settings()
    year = event.event_date.year if event.event_date else None
    poster_url, tmdb_id = await fetch_event_poster(
        event.title, year, db_settings.tmdb_api_key, source_url=event.source_url
    )

    if poster_url:
        event.poster_url = poster_url
    if tmdb_id:
        event.tmdb_id = tmdb_id

    await session.commit()
    await session.refresh(event)
    return event


@router.post("/command/refresh-metadata")
async def trigger_metadata_refresh(session: AsyncSession = Depends(get_session)) -> dict:
    """Fetch posters (Wikipedia first, TMDB optional) for events missing artwork."""
    from app.services.settings_service import load_settings
    from app.services.tmdb import fetch_event_poster

    db_settings = await load_settings()
    stmt = select(Event).where(Event.poster_url.is_(None))
    result = await session.execute(stmt)
    events = list(result.scalars().all())

    updated = 0
    for event in events:
        year = event.event_date.year if event.event_date else None
        try:
            poster_url, tmdb_id = await fetch_event_poster(
                event.title, year, db_settings.tmdb_api_key, source_url=event.source_url
            )
            if poster_url:
                event.poster_url = poster_url
                event.tmdb_id = tmdb_id
                updated += 1
        except Exception:
            pass

    await session.commit()
    return {"status": "ok", "updated": updated, "skipped": len(events) - updated}


@router.post("/command/refresh-schedule")
async def trigger_schedule_refresh() -> dict:
    """Manually kick off a schedule refresh from upstream sources."""
    from app.services.schedule_sync import sync_schedule

    count = await sync_schedule()
    return {"status": "ok", "events_synced": count}


class SyncYearsRequest(BaseModel):
    from_year: int
    to_year: int


@router.post("/command/sync-years")
async def trigger_sync_years(req: SyncYearsRequest) -> dict:
    """Sync UFC events for an arbitrary year range (historical or future)."""
    from app.services.schedule_sync import sync_schedule

    current = date.today().year
    from_year = max(2001, min(req.from_year, current + 2))
    to_year = max(from_year, min(req.to_year, current + 2))
    years = list(range(from_year, to_year + 1))
    count = await sync_schedule(years=years)
    return {"status": "ok", "years": years, "events_synced": count}


@router.post("/command/unmonitor-all")
async def unmonitor_all_events(session: AsyncSession = Depends(get_session)) -> dict:
    """Set all events to unmonitored."""
    await session.execute(update(Event).values(monitored=False))
    await session.commit()
    return {"status": "ok"}


@router.post("/event/{event_id}/search")
async def search_event(event_id: int, session: AsyncSession = Depends(get_session)) -> dict:
    """Trigger a manual indexer search for a single event."""
    event = await session.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    from app.services.indexer_search import search_event as _search

    return await _search(event_id)


@router.post("/event/{event_id}/grab")
async def grab_event(
    event_id: int,
    grab: GrabRequest,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Push a release to a matching download client and create a QueueItem."""
    from app.services.grab_service import (
        AlreadyQueuedError,
        NoClientError,
        grab_release,
    )

    event = await session.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")

    try:
        return await grab_release(
            event_id=event_id,
            nzb_url=grab.nzb_url,
            release_title=grab.release_title,
            size_bytes=grab.size_bytes,
            indexer_name=grab.indexer_name,
            protocol=grab.protocol,
        )
    except AlreadyQueuedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except NoClientError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/event/{event_id}/auto-search")
async def trigger_auto_search(event_id: int) -> dict:
    """Manually trigger the same auto-search-and-grab loop that fires on monitor.

    Useful when the user wants to retry after fixing indexer/client config.
    Runs synchronously and returns the grab result so the UI can show feedback.
    """
    from app.services.grab_service import auto_search_and_grab

    result = await auto_search_and_grab(event_id)
    if result is None:
        return {"status": "no-grab", "reason": "No qualifying release found"}
    return result


# Bulk monitor + auto-search trigger — Radarr equivalent of "Mass Editor"
class BulkMonitorRequest(BaseModel):
    event_ids: list[int]
    monitored: bool = True
    search: bool = True


@router.post("/command/bulk-monitor")
async def bulk_monitor(
    body: BulkMonitorRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Set monitored=true/false on many events at once. Optionally auto-search."""
    if not body.event_ids:
        return {"status": "ok", "updated": 0, "searches_queued": 0}

    await session.execute(
        update(Event).where(Event.id.in_(body.event_ids)).values(monitored=body.monitored)
    )
    await session.commit()

    searches = 0
    if body.monitored and body.search:
        # Only auto-search past/aired events with no file
        result = await session.execute(
            select(Event)
            .where(Event.id.in_(body.event_ids))
            .where(Event.file_path.is_(None))
            .where(Event.event_date <= date.today())
        )
        for ev in result.scalars().all():
            background_tasks.add_task(_run_auto_search, ev.id)
            searches += 1

    return {"status": "ok", "updated": len(body.event_ids), "searches_queued": searches}


@router.get("/event/{event_id}/history")
async def event_history(
    event_id: int,
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    """Return all QueueItems (history) for a single event."""
    from app.models.queue_item import QueueItem

    event = await session.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")

    result = await session.execute(
        select(QueueItem)
        .where(QueueItem.event_id == event_id)
        .order_by(QueueItem.grabbed_at.desc())
    )
    items = list(result.scalars().all())
    return [
        {
            "id": q.id,
            "release_title": q.release_title,
            "release_size_bytes": q.release_size_bytes,
            "indexer_name": q.indexer_name,
            "status": q.status,
            "progress_percent": q.progress_percent,
            "grabbed_at": q.grabbed_at.isoformat() if q.grabbed_at else None,
            "completed_at": q.completed_at.isoformat() if q.completed_at else None,
            "error_message": q.error_message,
        }
        for q in items
    ]
