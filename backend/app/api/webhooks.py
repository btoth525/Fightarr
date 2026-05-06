"""Incoming webhooks from download clients.

SABnzbd — configure under Settings > Notifications > Script (or Category Script).
Set the script URL to:  http://fightarr:7878/api/v1/webhook/sabnzbd

NZBGet — configure under Settings > Extension Scripts.
Set Post-Processing URL to: http://fightarr:7878/api/v1/webhook/nzbget

Both endpoints:
  1. Match the job ID against a QueueItem
  2. Run the post-processing pipeline (rename → import → notify)
  3. Return JSON with the result
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Form
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.event import Event
from app.models.queue_item import QueueItem
from app.services.postprocessor import run_postprocess
from app.services.settings_service import load_settings

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/webhook/sabnzbd")
async def sabnzbd_webhook(
    # SABnzbd post-processing script env vars sent as form fields
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
    """
    logger.info("SABnzbd webhook: nzo_id=%s name=%s status=%s", nzo_id, final_name, status)

    if status and status != "0":
        logger.warning("SABnzbd reports non-success status %s for %s", status, nzo_id)

    # Find the QueueItem by SABnzbd job ID
    result = await session.execute(select(QueueItem).where(QueueItem.sabnzbd_nzo_id == nzo_id))
    queue_item = result.scalar_one_or_none()

    if queue_item is None:
        logger.info("No QueueItem found for nzo_id=%s — may be untracked", nzo_id)
        return {"status": "untracked", "nzo_id": nzo_id}

    event = await session.get(Event, queue_item.event_id)
    if event is None:
        return {"status": "error", "message": "event not found"}

    download_path = complete_dir or final_name
    if not download_path:
        return {"status": "error", "message": "no download path provided"}

    s = await load_settings()
    return await run_postprocess(
        event=event,
        download_path=download_path,
        queue_item=queue_item,
        session=session,
        media_root=s.media_root,
        use_hardlinks=s.use_hardlinks,
        plex_host=s.plex_host,
        plex_token=s.plex_token,
        plex_section_id=s.plex_section_id,
        jellyfin_host=s.jellyfin_host,
        jellyfin_token=s.jellyfin_token,
        jellyfin_library_id=s.jellyfin_library_id,
    )


@router.post("/webhook/nzbget")
async def nzbget_webhook(
    # NZBGet post-processing script env vars
    nzbid: str = Form(..., alias="NZBID"),
    nzbname: str = Form(default="", alias="NZBNAME"),
    destdir: str = Form(default="", alias="DESTDIR"),
    nzbfilename: str = Form(default="", alias="NZBFILENAME"),
    total_status: str = Form(default="", alias="TOTALSTATUS"),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Handle NZBGet download completion.

    NZBGet calls this via HTTP POST after each job. Configure in NZBGet:
    Settings > Extension Scripts > Post-Processing Scripts.
    Set URL to: http://fightarr:7878/api/v1/webhook/nzbget
    """
    logger.info("NZBGet webhook: nzbid=%s name=%s status=%s", nzbid, nzbname, total_status)

    if total_status and total_status.upper() not in ("SUCCESS", ""):
        logger.warning("NZBGet reports status %s for %s", total_status, nzbname)

    result = await session.execute(select(QueueItem).where(QueueItem.sabnzbd_nzo_id == nzbid))
    queue_item = result.scalar_one_or_none()

    if queue_item is None:
        logger.info("No QueueItem for NZBGet NZBID=%s", nzbid)
        return {"status": "untracked", "nzbid": nzbid}

    event = await session.get(Event, queue_item.event_id)
    if event is None:
        return {"status": "error", "message": "event not found"}

    s = await load_settings()
    return await run_postprocess(
        event=event,
        download_path=destdir,
        queue_item=queue_item,
        session=session,
        media_root=s.media_root,
        use_hardlinks=s.use_hardlinks,
        plex_host=s.plex_host,
        plex_token=s.plex_token,
        plex_section_id=s.plex_section_id,
        jellyfin_host=s.jellyfin_host,
        jellyfin_token=s.jellyfin_token,
        jellyfin_library_id=s.jellyfin_library_id,
    )


@router.post("/command/ManualImport")
async def manual_import(
    event_id: int,
    file_path: str,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Manually import a file for an event (no QueueItem required)."""
    event = await session.get(Event, event_id)
    if event is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Event not found")

    s = await load_settings()
    return await run_postprocess(
        event=event,
        download_path=file_path,
        queue_item=None,
        session=session,
        media_root=s.media_root,
        use_hardlinks=s.use_hardlinks,
        plex_host=s.plex_host,
        plex_token=s.plex_token,
        plex_section_id=s.plex_section_id,
        jellyfin_host=s.jellyfin_host,
        jellyfin_token=s.jellyfin_token,
        jellyfin_library_id=s.jellyfin_library_id,
    )
