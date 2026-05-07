"""Incoming webhooks from download clients.

SABnzbd — configure under Settings > Notifications > Script (or Category Script).
Set the script URL to:  http://fightarr:7878/api/v1/webhook/sabnzbd

NZBGet — configure under Settings > Extension Scripts.
Set Post-Processing URL to: http://fightarr:7878/api/v1/webhook/nzbget

Both endpoints:
  1. Match the job ID against a QueueItem
  2. Store the completed download path on the QueueItem
  3. Run the shared import pipeline (same as queue_monitor — rename, move, notify)
  4. Return JSON with the result

Using the shared importer guarantees consistent naming, path-mapping support,
and permissions regardless of how the import was triggered.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Form, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.event import Event
from app.models.queue_item import QueueItem, QueueStatus
from app.services.importer import import_download

router = APIRouter()
logger = logging.getLogger(__name__)


async def _run_import(
    *,
    job_id: str,
    download_path: str,
    session: AsyncSession,
) -> dict:
    """Shared import logic for all webhook endpoints.

    Finds the QueueItem by job_id, sets its download_path to what the client
    reports, then calls the same import_download() used by the queue monitor.
    """
    result = await session.execute(select(QueueItem).where(QueueItem.sabnzbd_nzo_id == job_id))
    queue_item = result.scalar_one_or_none()

    if queue_item is None:
        logger.info("No QueueItem for job_id=%s — may be untracked by Fightarr", job_id)
        return {"status": "untracked", "job_id": job_id}

    if queue_item.status == QueueStatus.IMPORTED:
        logger.info("QueueItem %d already imported — webhook duplicate, skipping", queue_item.id)
        return {"status": "already_imported", "job_id": job_id}

    # Store the client-reported path so the importer (and path-mapping logic) can find it.
    if download_path:
        queue_item.download_path = download_path
    queue_item.status = QueueStatus.COMPLETED
    await session.commit()

    try:
        await import_download(session, queue_item)
        logger.info("Webhook import complete for job_id=%s", job_id)
        return {"status": "imported", "job_id": job_id}
    except FileNotFoundError as exc:
        logger.warning("Webhook import — file not found for job_id=%s: %s", job_id, exc)
        return {"status": "pending", "message": str(exc)}
    except Exception as exc:
        logger.error("Webhook import failed for job_id=%s: %s", job_id, exc)
        return {"status": "error", "message": str(exc)}


@router.post("/webhook/sabnzbd")
async def sabnzbd_webhook(
    nzo_id: str = Form(..., alias="nzo_id"),
    final_name: str = Form(default="", alias="final_name"),
    complete_dir: str = Form(default="", alias="complete_dir"),
    category: str = Form(default="", alias="cat"),
    status: str = Form(default="", alias="status"),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Handle SABnzbd download completion.

    SABnzbd calls this via HTTP POST with form fields after each job completes.
    Configure in SABnzbd: Config > Notifications > Script, or per-category script.
    Set URL to: http://fightarr:7878/api/v1/webhook/sabnzbd
    """
    logger.info("SABnzbd webhook: nzo_id=%s name=%s status=%s", nzo_id, final_name, status)

    if status and status not in ("0", "", "success"):
        logger.warning("SABnzbd reports non-success status %s for %s", status, nzo_id)

    download_path = complete_dir or final_name
    return await _run_import(
        job_id=nzo_id,
        download_path=download_path,
        session=session,
    )


@router.post("/webhook/nzbget")
async def nzbget_webhook(
    nzbid: str = Form(..., alias="NZBID"),
    nzbname: str = Form(default="", alias="NZBNAME"),
    destdir: str = Form(default="", alias="DESTDIR"),
    nzbfilename: str = Form(default="", alias="NZBFILENAME"),
    total_status: str = Form(default="", alias="TOTALSTATUS"),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Handle NZBGet download completion.

    Configure in NZBGet: Settings > Extension Scripts > Post-Processing Scripts.
    Set URL to: http://fightarr:7878/api/v1/webhook/nzbget
    """
    logger.info("NZBGet webhook: nzbid=%s name=%s status=%s", nzbid, nzbname, total_status)

    if total_status and total_status.upper() not in ("SUCCESS", ""):
        logger.warning("NZBGet reports status %s for %s", total_status, nzbname)

    return await _run_import(
        job_id=nzbid,
        download_path=destdir,
        session=session,
    )


@router.post("/command/ManualImport")
async def manual_import(
    event_id: int,
    file_path: str,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Manually import a local file for an event (Radarr Manual Import equivalent).

    Creates a one-off QueueItem so the standard import pipeline handles naming,
    permissions, path mapping, poster download, and Plex notification.
    """
    event = await session.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")

    qi = QueueItem(
        event_id=event_id,
        release_title=file_path.split("/")[-1],
        download_path=file_path,
        status=QueueStatus.COMPLETED,
    )
    session.add(qi)
    await session.commit()
    await session.refresh(qi)

    try:
        await import_download(session, qi)
        return {"status": "imported", "event_id": event_id, "file": file_path}
    except FileNotFoundError as exc:
        return {"status": "error", "message": str(exc)}
    except Exception as exc:
        logger.error("Manual import failed for event %d: %s", event_id, exc)
        return {"status": "error", "message": str(exc)}
