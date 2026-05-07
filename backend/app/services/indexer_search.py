"""Indexer search service.

Searches configured Newznab/Torznab indexers for releases matching a UFC event.
"""

import logging

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.event import Event
from app.models.indexer import Indexer
from app.services.newznab import NewznabClient, NewznabRelease

logger = logging.getLogger(__name__)


async def search_all_wanted() -> int:
    """Search indexers for all wanted events. Returns count grabbed."""
    logger.debug("search_all_wanted: not yet implemented")
    return 0


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
        return {"event_id": event_id, "releases": [], "message": "No indexers configured"}

    queries = _build_queries(event)
    all_releases: list[NewznabRelease] = []

    for indexer in indexers:
        client = NewznabClient(indexer.name, indexer.url, indexer.api_key)
        for query in queries:
            try:
                releases = await client.search(query, categories=indexer.categories)
                all_releases.extend(releases)
                logger.info("Indexer %s query %r → %d results", indexer.name, query, len(releases))
            except Exception as exc:
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
        "releases": [
            {
                "title": r.title,
                "size_bytes": r.size_bytes,
                "indexer_name": r.indexer_name,
                "nzb_url": r.nzb_url,
                "pub_date": r.pub_date,
                "guid": r.guid,
            }
            for r in unique
        ],
    }


def _build_queries(event: Event) -> list[str]:
    if event.event_number:
        return [f"UFC {event.event_number}", f"UFC.{event.event_number}"]
    d = event.event_date
    return [
        f"UFC Fight Night {d.strftime('%Y %m %d')}",
        f"UFC.Fight.Night.{d.strftime('%Y.%m.%d')}",
    ]
