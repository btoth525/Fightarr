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

            if job is not None:
                _apply_job(db_item, job)
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
                    _apply_job(db_item, hist)

            # Fire import when job reached completed state
            if db_item.status == QueueStatus.COMPLETED:
                await _run_import(session, db_item)

        await session.commit()


def _apply_job(item: QueueItem, job: dict) -> None:
    """Map a client job dict onto a QueueItem row."""
    status = job.get("status", "")
    item.progress_percent = float(job.get("progress", item.progress_percent))

    if status == "downloading":
        item.status = QueueStatus.DOWNLOADING
    elif status in ("failed", "error"):
        item.status = QueueStatus.FAILED
        item.error_message = job.get("error") or "Download failed in client"
        item.completed_at = datetime.now(UTC)
    elif status == "completed":
        item.progress_percent = 100.0
        if job.get("download_path"):
            item.download_path = job["download_path"]
        item.status = QueueStatus.COMPLETED


async def _run_import(session, item: QueueItem) -> None:
    from app.services.importer import import_download

    try:
        await import_download(session, item)
        logger.info("Imported %s", item.release_title)
    except FileNotFoundError as exc:
        logger.warning("Import skipped — no video file yet: %s", exc)
        # Leave as COMPLETED so we retry next poll
    except Exception as exc:
        logger.error("Import failed for item %d: %s", item.id, exc)
        item.status = QueueStatus.FAILED
        item.error_message = f"Import failed: {exc}"
        item.completed_at = datetime.now(UTC)
