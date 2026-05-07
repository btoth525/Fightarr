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
    poster_url: str | None = None
    tmdb_id: int | None = None
    source_url: str | None = None

    model_config = {"from_attributes": True}


class EventUpdate(BaseModel):
    monitored: bool | None = None


class GrabRequest(BaseModel):
    nzb_url: str
    release_title: str
    size_bytes: int | None = None
    indexer_name: str | None = None


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


@router.post("/event/{event_id}/refresh-metadata", response_model=EventOut)
async def refresh_event_metadata(
    event_id: int, session: AsyncSession = Depends(get_session)
) -> Event:
    """Fetch/refresh poster for a single event (Wikipedia first, TMDB optional)."""
    from app.services.tmdb import fetch_event_poster

    from app.services.settings_service import load_settings

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
    """Push a release to the best available download client and create a QueueItem."""
    from app.models.download_client import DownloadClient
    from app.models.queue_item import QueueItem
    from app.services.download_clients.factory import build_client

    event = await session.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")

    result = await session.execute(
        select(DownloadClient)
        .where(DownloadClient.enabled.is_(True))
        .order_by(DownloadClient.priority)
    )
    dc = result.scalar_one_or_none()
    if dc is None:
        raise HTTPException(status_code=400, detail="No download client configured")

    client = build_client(dc)
    try:
        job_id = await client.add_download(grab.nzb_url, grab.release_title, dc.category)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Download client error: {exc}") from exc

    qi = QueueItem(
        event_id=event_id,
        release_title=grab.release_title,
        release_size_bytes=grab.size_bytes,
        indexer_name=grab.indexer_name,
        nzb_url=grab.nzb_url,
        download_client_id=dc.id,
        sabnzbd_nzo_id=job_id,
        status="grabbed",
    )
    session.add(qi)
    await session.commit()

    return {"status": "grabbed", "job_id": job_id, "download_client": dc.name}


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
