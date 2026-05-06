"""Background job scheduler.

Uses APScheduler to periodically refresh the UFC schedule from Wikipedia and
search indexers for releases of upcoming/recent events. Jobs are added here
but kept thin — the actual work lives in app.services.
"""

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.core.config import settings

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


def start_scheduler() -> None:
    """Wire up periodic jobs and start the scheduler."""
    global _scheduler
    if _scheduler is not None:
        return

    _scheduler = AsyncIOScheduler()

    # Lazy imports so this module stays import-cheap
    from app.services.indexer_search import search_all_wanted
    from app.services.schedule_sync import sync_schedule

    _scheduler.add_job(
        sync_schedule,
        trigger=IntervalTrigger(seconds=settings.schedule_refresh_interval),
        id="schedule_sync",
        name="Refresh UFC schedule from Wikipedia",
        replace_existing=True,
        next_run_time=None,  # Run on first interval; manual trigger via API
    )

    _scheduler.add_job(
        search_all_wanted,
        trigger=IntervalTrigger(seconds=settings.indexer_search_interval),
        id="indexer_search",
        name="Search indexers for wanted events",
        replace_existing=True,
        next_run_time=None,
    )

    _scheduler.start()
    logger.info("Scheduler started with %d jobs", len(_scheduler.get_jobs()))


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("Scheduler stopped")


def get_scheduler() -> AsyncIOScheduler | None:
    return _scheduler
