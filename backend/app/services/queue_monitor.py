"""Queue monitor — polls download clients and drives the import pipeline.

Runs every 60 seconds via APScheduler. For each active QueueItem:
 1. Ask the download client for current status / progress.
 2. If the job is in-flight, update progress_percent.
 3. If the job completed (or appeared in history for NZB clients), trigger import.
 4. If the job failed, record the error.
"""

import logging
from datetime import UTC, datetime

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.download_client import DownloadClient
from app.models.queue_item import QueueItem, QueueStatus

logger = logging.getLogger(__name__)


async def poll_queue() -> None:
    """Entry point called by the scheduler every 60 s."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(QueueItem).where(
                QueueItem.status.in_([QueueStatus.GRABBED, QueueStatus.DOWNLOADING])
            )
        )
        active = list(result.scalars().all())

    if not active:
        return

    by_client: dict[int, list[QueueItem]] = {}
    for item in active:
        if item.download_client_id:
            by_client.setdefault(item.download_client_id, []).append(item)

    for dc_id, items in by_client.items():
        try:
            await _poll_client(dc_id, items)
        except Exception as exc:
            logger.warning("Poll failed for client %d: %s", dc_id, exc)


async def _poll_client(dc_id: int, items: list[QueueItem]) -> None:
    from app.services.download_clients.factory import build_client

    async with AsyncSessionLocal() as session:
        dc = await session.get(DownloadClient, dc_id)
        if dc is None or not dc.enabled:
            return

        client = build_client(dc)

        try:
            queue_map = {j["id"]: j for j in await client.get_queue()}
        except Exception as exc:
            logger.warning("get_queue() failed for %s: %s", dc.name, exc)
            return

        for item in items:
            if not item.sabnzbd_nzo_id:
                continue

            db_item = await session.get(QueueItem, item.id)
            if db_item is None:
                continue

            job = queue_map.get(item.sabnzbd_nzo_id)

            just_failed = False
            if job is not None:
                just_failed, _ = _apply_job(db_item, job)
            else:
                # Not in active queue — check history (NZB clients move to history on finish)
                get_hist = getattr(client, "get_history", None)
                hist = None
                if get_hist is not None:
                    try:
                        hist = await get_hist(item.sabnzbd_nzo_id)
                    except Exception as exc:
                        logger.debug("get_history() failed: %s", exc)
                if hist is not None:
                    just_failed, _ = _apply_job(db_item, hist)

            # Fire import when job reached completed state
            just_imported = False
            if db_item.status == QueueStatus.COMPLETED:
                just_imported = await _run_import(session, db_item)

            # Side effects after status transitions — done after commit so
            # rows are persisted before notifications/retries kick off.
            if just_failed:
                await session.commit()
                await _handle_failure(db_item)
            elif just_imported:
                await session.commit()
                await _handle_imported(db_item)

        await session.commit()


def _apply_job(item: QueueItem, job: dict) -> tuple[bool, bool]:
    """Map a client job dict onto a QueueItem row.

    Returns (just_failed, just_imported) — used by the caller to decide whether
    to fire blocklist + retry + notification side effects.
    """
    status = job.get("status", "")
    item.progress_percent = float(job.get("progress", item.progress_percent))

    just_failed = False
    if status == "downloading":
        item.status = QueueStatus.DOWNLOADING
    elif status in ("failed", "error"):
        if item.status != QueueStatus.FAILED:
            just_failed = True
        item.status = QueueStatus.FAILED
        item.error_message = job.get("error") or "Download failed in client"
        item.completed_at = datetime.now(UTC)
    elif status == "completed":
        item.progress_percent = 100.0
        if job.get("download_path"):
            item.download_path = job["download_path"]
        item.status = QueueStatus.COMPLETED

    return just_failed, False


async def _run_import(session, item: QueueItem) -> bool:
    """Import a completed download. Returns True if just imported."""
    from app.services.importer import import_download

    try:
        await import_download(session, item)
        logger.info("Imported %s", item.release_title)
        return True
    except FileNotFoundError as exc:
        logger.warning("Import skipped — no video file yet: %s", exc)
        # Leave as COMPLETED so we retry next poll
        return False
    except Exception as exc:
        logger.error("Import failed for item %d: %s", item.id, exc)
        item.status = QueueStatus.FAILED
        item.error_message = f"Import failed: {exc}"
        item.completed_at = datetime.now(UTC)
        return False


async def _handle_failure(item: QueueItem) -> None:
    """Blocklist the failed release, fire a notification, and trigger retry."""
    from app.core.database import AsyncSessionLocal as _SL
    from app.models.event import Event
    from app.services import blocklist_service, notifications
    from app.services.grab_service import auto_search_and_grab

    reason = item.error_message or "Download failed"
    await blocklist_service.add(
        event_id=item.event_id,
        release_title=item.release_title,
        nzb_url=item.nzb_url,
        indexer_name=item.indexer_name,
        reason=reason,
    )

    try:
        async with _SL() as s:
            event = await s.get(Event, item.event_id)
        if event is not None:
            await notifications.on_failed(event, item.release_title, reason)
    except Exception as exc:
        logger.debug("Failure notification skipped: %s", exc)

    # Auto-retry: pick the next-best release that isn't blocklisted
    try:
        retry = await auto_search_and_grab(item.event_id)
        if retry is not None:
            logger.info(
                "Auto-retry: grabbed alternative for event %d after %r failed",
                item.event_id,
                item.release_title,
            )
    except Exception as exc:
        logger.warning("Auto-retry failed for event %d: %s", item.event_id, exc)


async def _handle_imported(item: QueueItem) -> None:
    """Fire import notification (Plex notify is handled inside importer)."""
    from app.core.database import AsyncSessionLocal as _SL
    from app.models.event import Event
    from app.services import notifications

    try:
        async with _SL() as s:
            event = await s.get(Event, item.event_id)
        if event is not None:
            await notifications.on_import(event, event.file_path or "", event.quality)
    except Exception as exc:
        logger.debug("Import notification skipped: %s", exc)
