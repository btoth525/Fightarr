"""Background job scheduler — Radarr-style periodic tasks.

Job catalog (matches what Radarr shows under System → Tasks):

  schedule_sync       Wikipedia upcoming/past UFC events           every 6h
  search_all_wanted   Search indexers for monitored missing events  every 30m
  queue_monitor       Poll download clients for progress/completion every 60s
  poster_backfill     Retry missing event posters                   every 12h
  cleanup_history     Drop QueueItems older than 90 days            every 24h
  health_check        Probe indexers + download clients             every 15m

All intervals are configurable via FIGHTARR_* env vars. Each job has a
`next_run_time` of "now + interval" so they fire on a predictable cadence
rather than queueing up at startup. Manual trigger via /system/tasks/{id}/run-now.
"""

import logging
from datetime import UTC, datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.core.config import settings

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


def _now_plus(seconds: int) -> datetime:
    return datetime.now(tz=UTC) + timedelta(seconds=seconds)


def start_scheduler() -> None:
    """Wire up periodic jobs and start the scheduler."""
    global _scheduler
    if _scheduler is not None:
        return

    _scheduler = AsyncIOScheduler(timezone=UTC)

    # Lazy imports so this module stays import-cheap
    from app.services.indexer_search import search_all_wanted
    from app.services.maintenance import (
        cleanup_history,
        health_check,
        refresh_poster_cache,
        update_event_statuses,
    )
    from app.services.queue_monitor import poll_queue
    from app.services.schedule_sync import sync_schedule

    # Event status lifecycle — every hour
    _scheduler.add_job(
        update_event_statuses,
        trigger=IntervalTrigger(hours=1),
        id="update_event_statuses",
        name="Update event statuses (announced/upcoming/airing/missing)",
        replace_existing=True,
        next_run_time=_now_plus(10),  # Run quickly on boot so UI shows correct statuses
    )

    # Wikipedia schedule refresh — every 6 hours
    _scheduler.add_job(
        sync_schedule,
        trigger=IntervalTrigger(seconds=settings.schedule_refresh_interval),
        id="schedule_sync",
        name="Refresh UFC schedule from Wikipedia",
        replace_existing=True,
        next_run_time=_now_plus(60),  # First run 60 s after boot
    )

    # Wanted-events search — every 30 min (Radarr "RSS Sync")
    _scheduler.add_job(
        search_all_wanted,
        trigger=IntervalTrigger(seconds=settings.indexer_search_interval),
        id="search_all_wanted",
        name="Search indexers for monitored missing events",
        replace_existing=True,
        next_run_time=_now_plus(120),  # Wait 2 min for Wikipedia sync to finish
    )

    # Download client polling — every minute
    _scheduler.add_job(
        poll_queue,
        trigger=IntervalTrigger(seconds=60),
        id="queue_monitor",
        name="Poll download clients for queue updates",
        replace_existing=True,
        next_run_time=_now_plus(30),
    )

    # Poster backfill — every 12 hours
    _scheduler.add_job(
        refresh_poster_cache,
        trigger=IntervalTrigger(hours=12),
        id="poster_backfill",
        name="Refresh missing poster art",
        replace_existing=True,
        next_run_time=_now_plus(180),
    )

    # History cleanup — daily
    _scheduler.add_job(
        cleanup_history,
        trigger=IntervalTrigger(hours=24),
        id="cleanup_history",
        name="Clean up old queue history (>90 days)",
        replace_existing=True,
        next_run_time=_now_plus(3600),  # Run an hour after startup
    )

    # Health check — every 15 minutes
    _scheduler.add_job(
        health_check,
        trigger=IntervalTrigger(minutes=15),
        id="health_check",
        name="Probe indexers and download clients",
        replace_existing=True,
        next_run_time=_now_plus(300),  # First run 5 min after boot
    )

    _scheduler.start()
    logger.info("Scheduler started with %d jobs", len(_scheduler.get_jobs()))
    for job in _scheduler.get_jobs():
        logger.info("  • %s — next run %s", job.id, job.next_run_time)


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("Scheduler stopped")


def get_scheduler() -> AsyncIOScheduler | None:
    return _scheduler
