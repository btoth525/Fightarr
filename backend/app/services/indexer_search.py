"""Indexer search service.

Searches configured Newznab indexers for releases matching wanted events.
Stub for now — real implementation lands in a later PR.

Architecture:
  1. Pull events with status=MISSING or RELEASED and monitored=True
  2. For each, build query strings: "UFC.300", "UFC 300", "UFC.Fight.Night.YYYY-MM-DD"
  3. Hit each enabled indexer's /api?t=search endpoint
  4. Score releases (resolution, codec, size, prelims/main filters)
  5. Pick best release, push to SABnzbd, create QueueItem
"""
import logging

logger = logging.getLogger(__name__)


async def search_all_wanted() -> int:
    """Search indexers for all wanted events. Returns count grabbed."""
    logger.debug("search_all_wanted: stub — no indexers configured yet")
    return 0


async def search_event(event_id: int) -> dict:
    """Manual search for a single event. Returns matched releases."""
    logger.debug("search_event(%d): stub", event_id)
    return {"event_id": event_id, "releases": []}
