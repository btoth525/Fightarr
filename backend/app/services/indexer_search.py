"""Indexer search service.

Searches configured Newznab/Torznab indexers for releases matching a UFC event.
"""

import logging
import re

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.event import Event
from app.models.indexer import Indexer
from app.services.newznab import NewznabClient, NewznabRelease

logger = logging.getLogger(__name__)


async def search_all_wanted() -> dict:
    """Scheduled job — Radarr-style "RSS sync" for monitored missing events.

    For every monitored event that has aired and doesn't yet have a file:
      1. Skip if there's already an active QueueItem for it
      2. Run auto_search_and_grab() — search indexers, score, grab the best
      3. Brief sleep between events so we don't hammer indexers / hit rate limits

    Returns a summary dict for logging and the /system/tasks UI.
    """
    import asyncio
    from datetime import date

    from app.core.database import AsyncSessionLocal
    from app.models.event import Event, EventStatus
    from app.models.queue_item import QueueItem
    from app.services.grab_service import IN_FLIGHT_STATUSES, auto_search_and_grab

    async with AsyncSessionLocal() as session:
        # Monitored, aired, no file yet
        result = await session.execute(
            select(Event)
            .where(Event.monitored.is_(True))
            .where(Event.file_path.is_(None))
            .where(Event.event_date <= date.today())
            .where(Event.status != EventStatus.DOWNLOADED)
            .order_by(Event.event_date.desc())
        )
        wanted = list(result.scalars().all())

        # Skip events that already have any in-flight grab (GRABBED, DOWNLOADING,
        # OR COMPLETED-pending-import) — without the COMPLETED check, a stuck
        # import would let RSS sync re-grab the same event repeatedly.
        active_q = await session.execute(
            select(QueueItem.event_id).where(QueueItem.status.in_(IN_FLIGHT_STATUSES))
        )
        active_event_ids = {row[0] for row in active_q.all()}

    candidates = [e for e in wanted if e.id not in active_event_ids]
    logger.info(
        "RSS sync: %d wanted events, %d already in queue, %d to search",
        len(wanted),
        len(wanted) - len(candidates),
        len(candidates),
    )

    grabbed = 0
    for event in candidates:
        try:
            result = await auto_search_and_grab(event.id)
            if result is not None:
                grabbed += 1
                logger.info("RSS sync grabbed %s for event %d", result.get("job_id"), event.id)
        except Exception as exc:
            logger.warning("RSS sync failed for event %d: %s", event.id, exc)
        # Be nice to indexers — short delay between events
        await asyncio.sleep(2.0)

    return {
        "checked": len(candidates),
        "grabbed": grabbed,
        "skipped_in_queue": len(active_event_ids),
    }


async def search_event(event_id: int) -> dict:
    """Manual search for a single event across all enabled indexers."""
    async with AsyncSessionLocal() as session:
        event = await session.get(Event, event_id)
        if not event:
            return {"event_id": event_id, "releases": [], "error": "Event not found"}

        result = await session.execute(
            select(Indexer).where(Indexer.enabled.is_(True)).order_by(Indexer.priority)
        )
        indexers = list(result.scalars().all())

    if not indexers:
        return {
            "event_id": event_id,
            "releases": [],
            "queries_tried": [],
            "errors": ["No indexers configured. Add an indexer in Settings → Indexers."],
        }

    queries = _build_queries(event)
    all_releases: list[NewznabRelease] = []
    errors: list[str] = []
    searched_queries: list[str] = []

    for indexer in indexers:
        protocol = "torrent" if indexer.indexer_type == "torznab" else "nzb"
        client = NewznabClient(indexer.name, indexer.url, indexer.api_key)
        for query in queries:
            try:
                releases, url = await client.search(query, categories=indexer.categories)
                for r in releases:
                    r.protocol = protocol
                all_releases.extend(releases)
                searched_queries.append(
                    f"{indexer.name} [{query!r}] cat={indexer.categories or '∅'} → {len(releases)} | {url}"
                )
                logger.info(
                    "Indexer %s query %r cat=%s → %d results",
                    indexer.name,
                    query,
                    indexer.categories,
                    len(releases),
                )
                # Fallback: if nothing came back AND we filtered by categories,
                # retry the same query with no category filter. Some indexers
                # categorize UFC content under codes outside our default set.
                if not releases and indexer.categories:
                    retry_releases, retry_url = await client.search(query, categories="")
                    for r in retry_releases:
                        r.protocol = protocol
                    all_releases.extend(retry_releases)
                    searched_queries.append(
                        f"{indexer.name} [{query!r}] cat=∅ (fallback) → {len(retry_releases)} | {retry_url}"
                    )
                    logger.info(
                        "Indexer %s fallback (no cat) query %r → %d results",
                        indexer.name,
                        query,
                        len(retry_releases),
                    )
            except Exception as exc:
                msg = f"{indexer.name} [{query!r}]: {exc}"
                errors.append(msg)
                searched_queries.append(f"{indexer.name} [{query!r}] → ERROR: {exc}")
                logger.warning("Search failed on %s for %r: %s", indexer.name, query, exc)

    seen: set[str] = set()
    unique: list[NewznabRelease] = []
    for r in all_releases:
        key = r.title.lower()
        if key not in seen:
            seen.add(key)
            unique.append(r)

    return {
        "event_id": event_id,
        "total": len(unique),
        "queries_tried": searched_queries,
        "errors": errors,
        "releases": [
            {
                "title": r.title,
                "size_bytes": r.size_bytes,
                "indexer_name": r.indexer_name,
                "nzb_url": r.nzb_url,
                "pub_date": r.pub_date,
                "guid": r.guid,
                "protocol": r.protocol,
            }
            for r in unique
        ],
    }


def _build_queries(event: Event) -> list[str]:
    """Build multiple query strings for a UFC event.

    UFC releases never include a year tag (the Radarr #9215 problem).
    Priority order:
      1. Event number (PPV) or sequential Fight Night number extracted from title
      2. Fighter-name queries with "Fight Night" prefix — most reliable when the
         sequential number isn't stored in our DB title
         e.g. "UFC Fight Night Strickland Hernandez" matches
              "UFC Fight Night 267 Strickland vs Hernandez" via AND search
      3. Date-format fallback (only works if the indexer encodes the date in titles)
    """
    queries: list[str] = []
    d = event.event_date

    # Extract fighters once — reused in multiple query variants below
    fighters: list[str] = []
    if event.main_event:
        fighters = _extract_fighters(event.main_event)

    if event.event_number:
        # Numbered PPVs: primary by event number, fighter names as fallback
        queries += [f"UFC {event.event_number}", f"UFC.{event.event_number}"]
        if len(fighters) >= 2:
            queries += [
                f"UFC {fighters[0]} {fighters[1]}",
                f"UFC {fighters[0]}",
            ]
    else:
        # Fight Nights -------------------------------------------------------
        # 1. Sequential number when it's embedded in the Wikipedia title
        fn_number = _extract_fight_night_number(event.title)
        if fn_number:
            queries += [
                f"UFC Fight Night {fn_number}",
                f"UFC.Fight.Night.{fn_number}",
            ]

        # 2. Fighter-name queries — these work even when we don't have the
        #    sequential number, because all words appear in release titles like
        #    "UFC Fight Night 267 Strickland vs Hernandez Main Card 1080p".
        #    "UFC Fight Night Strickland Hernandez" matches that via AND search.
        if len(fighters) >= 2:
            queries += [
                f"UFC Fight Night {fighters[0]} {fighters[1]}",
                f"UFC Fight Night {fighters[0]}",
                f"UFC {fighters[0]} {fighters[1]}",
            ]
        elif len(fighters) == 1:
            queries += [
                f"UFC Fight Night {fighters[0]}",
                f"UFC {fighters[0]}",
            ]

        # 3. Date-format fallback (only works if uploader encodes the date)
        queries += [
            f"UFC Fight Night {d.strftime('%Y %m %d')}",
            f"UFC.Fight.Night.{d.strftime('%Y.%m.%d')}",
        ]

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for q in queries:
        if q not in seen:
            seen.add(q)
            unique.append(q)
    return unique


def _extract_fight_night_number(title: str) -> int | None:
    """Extract sequential Fight Night number from 'UFC Fight Night 273: ...' → 273."""
    m = re.search(r"UFC\s+Fight\s+Night\s+(\d+)", title, re.IGNORECASE)
    return int(m.group(1)) if m else None


def _extract_fighters(main_event: str) -> list[str]:
    """Extract surnames from a 'Fighter A vs Fighter B' string."""
    # Strip descriptors like "(c)" and extra whitespace
    clean = re.sub(r"\(.*?\)", "", main_event).strip()
    parts = re.split(r"\s+vs\.?\s+", clean, flags=re.IGNORECASE)
    surnames: list[str] = []
    for part in parts:
        words = part.strip().split()
        if words:
            surnames.append(words[-1])  # last word = surname
    return surnames
