"""Periodic maintenance jobs scheduled by APScheduler.

These mirror Radarr's background tasks:
  - cleanup_history       Drop very old completed/failed QueueItems
  - refresh_poster_cache  Backfill posters for events that don't have one yet
  - health_check          Probe every enabled indexer + download client and log
                          any failures so the user sees them in the System page
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select

from app.core.database import AsyncSessionLocal
from app.models.download_client import DownloadClient
from app.models.event import Event
from app.models.indexer import Indexer
from app.models.queue_item import QueueItem, QueueStatus

logger = logging.getLogger(__name__)

HISTORY_RETENTION_DAYS = 90

# Cached last health check result so the System page can display it without
# re-running probes on every page load. Populated by health_check().
_last_health: dict = {
    "checked_at": None,
    "indexers_checked": 0,
    "clients_checked": 0,
    "failures": [],
}


def get_last_health() -> dict:
    """Return the most recent health_check() result for the System page."""
    return _last_health


async def cleanup_history() -> dict:
    """Delete QueueItems older than HISTORY_RETENTION_DAYS that are imported/failed."""
    cutoff = datetime.now(UTC) - timedelta(days=HISTORY_RETENTION_DAYS)
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            delete(QueueItem)
            .where(QueueItem.status.in_([QueueStatus.IMPORTED, QueueStatus.FAILED]))
            .where(QueueItem.completed_at.isnot(None))
            .where(QueueItem.completed_at < cutoff)
        )
        await session.commit()
        deleted = result.rowcount or 0
    if deleted:
        logger.info(
            "History cleanup: removed %d items older than %d days", deleted, HISTORY_RETENTION_DAYS
        )
    return {"deleted": deleted, "retention_days": HISTORY_RETENTION_DAYS}


async def refresh_poster_cache() -> dict:
    """Try once more to fetch posters for any event still missing one.

    Wikipedia / TMDB sometimes fail transiently — running this every few hours
    catches events that came in without art on the first sync.
    """
    from app.services.settings_service import load_settings
    from app.services.tmdb import fetch_event_poster

    db_settings = await load_settings()

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Event).where(Event.poster_url.is_(None)))
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
                    if tmdb_id:
                        event.tmdb_id = tmdb_id
                    updated += 1
            except Exception as exc:
                logger.debug("Poster backfill failed for %s: %s", event.slug, exc)
        await session.commit()

    if updated:
        logger.info("Poster backfill: filled %d missing posters", updated)
    return {"checked": len(events), "updated": updated}


async def health_check() -> dict:
    """Test every enabled indexer + download client. Surfaces failures in logs.

    Frontend can poll /system/health to display these as warnings on the
    System page (Radarr's "Health" tab equivalent).
    """
    from app.services.download_clients.factory import build_client
    from app.services.newznab import NewznabClient

    failures: list[dict] = []

    async with AsyncSessionLocal() as session:
        ix_result = await session.execute(select(Indexer).where(Indexer.enabled.is_(True)))
        indexers = list(ix_result.scalars().all())

        dc_result = await session.execute(
            select(DownloadClient).where(DownloadClient.enabled.is_(True))
        )
        clients = list(dc_result.scalars().all())

    for ix in indexers:
        client = NewznabClient(ix.name, ix.url, ix.api_key)
        ok, msg = await client.test_connection()
        if not ok:
            failures.append({"kind": "indexer", "name": ix.name, "message": msg})
            logger.warning("Health check: indexer %s unreachable — %s", ix.name, msg)

    for dc in clients:
        try:
            client = build_client(dc)
            ok = await client.test_connection()
            if not ok:
                failures.append(
                    {"kind": "download_client", "name": dc.name, "message": "Connection failed"}
                )
                logger.warning("Health check: download client %s unreachable", dc.name)
        except Exception as exc:
            failures.append({"kind": "download_client", "name": dc.name, "message": str(exc)})
            logger.warning("Health check: download client %s error — %s", dc.name, exc)

    result = {
        "checked_at": datetime.now(UTC).isoformat(),
        "indexers_checked": len(indexers),
        "clients_checked": len(clients),
        "failures": failures,
    }
    _last_health.clear()
    _last_health.update(result)
    return result
