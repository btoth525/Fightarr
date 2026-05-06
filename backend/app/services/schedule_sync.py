"""Schedule sync service.

Pulls UFC events from Wikipedia and upserts them into the database.
Idempotent: safe to run repeatedly. Existing events are updated in place
based on slug; new events are inserted.
"""

import logging
from datetime import date

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.event import Event, EventStatus, EventType
from app.scrapers.wikipedia import ScrapedEvent, fetch_year

logger = logging.getLogger(__name__)


async def sync_schedule(years: list[int] | None = None) -> int:
    """Fetch the UFC schedule and merge into the database.

    Args:
        years: Years to fetch. Defaults to last year, this year, next year
               so we capture both recent past and announced future events.

    Returns:
        Number of events upserted.
    """
    if years is None:
        current = date.today().year
        years = [current - 1, current, current + 1]

    all_scraped: list[ScrapedEvent] = []
    for year in years:
        try:
            scraped = await fetch_year(year)
            all_scraped.extend(scraped)
        except Exception as e:
            logger.exception("Failed to fetch %d_in_UFC: %s", year, e)
            continue

    if not all_scraped:
        logger.warning("No events scraped — skipping merge")
        return 0

    return await _merge_events(all_scraped)


async def _merge_events(scraped: list[ScrapedEvent]) -> int:
    """Upsert scraped events into the DB."""
    count = 0
    today = date.today()

    async with AsyncSessionLocal() as session:
        for s in scraped:
            if s.event_date is None:
                # Skip TBD events for now — we'll surface them in a later PR
                continue

            existing = await session.execute(select(Event).where(Event.slug == s.slug))
            existing = existing.scalar_one_or_none()

            status = _derive_status(s.event_date, today, has_existing=existing is not None)

            if existing is None:
                event = Event(
                    slug=s.slug,
                    title=s.title,
                    event_number=s.event_number,
                    event_type=EventType(s.event_type),
                    event_date=s.event_date,
                    venue=s.venue,
                    location=s.location,
                    main_event=s.main_event,
                    status=status,
                    monitored=True,
                    source_url=s.source_url,
                )
                session.add(event)
                count += 1
            else:
                # Update mutable fields — date/venue can change as cards finalize
                existing.title = s.title
                existing.event_number = s.event_number
                existing.event_type = EventType(s.event_type)
                existing.event_date = s.event_date
                existing.venue = s.venue or existing.venue
                existing.location = s.location or existing.location
                existing.main_event = s.main_event or existing.main_event
                existing.source_url = s.source_url
                # Don't downgrade status if we already have a file
                if existing.status not in (EventStatus.DOWNLOADED,):
                    existing.status = status
                count += 1

        await session.commit()

    logger.info("Merged %d events into the database", count)

    # Fire-and-forget TMDB poster fetch for any events still missing art
    await _backfill_posters()

    return count


async def _backfill_posters() -> None:
    """Fetch TMDB posters for events that don't have one."""
    from app.core.config import settings
    from app.services.tmdb import fetch_event_poster

    if not settings.tmdb_api_key:
        return

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Event).where(Event.poster_url.is_(None)))
        events = list(result.scalars().all())

        for event in events:
            year = event.event_date.year if event.event_date else None
            try:
                poster_url, tmdb_id = await fetch_event_poster(
                    event.title, year, settings.tmdb_api_key, source_url=event.source_url
                )
                if poster_url:
                    event.poster_url = poster_url
                    event.tmdb_id = tmdb_id
            except Exception as exc:
                logger.debug("TMDB fetch failed for %s: %s", event.slug, exc)

        await session.commit()
    logger.info("TMDB poster backfill complete")


def _derive_status(event_date: date, today: date, has_existing: bool) -> EventStatus:
    """Infer status from event date."""
    delta = (event_date - today).days
    if delta > 7:
        return EventStatus.ANNOUNCED
    if delta > 0:
        return EventStatus.UPCOMING
    if delta == 0:
        return EventStatus.AIRING
    # In the past
    if has_existing:
        # Don't override; caller decides whether to downgrade
        return EventStatus.RELEASED
    return EventStatus.MISSING
