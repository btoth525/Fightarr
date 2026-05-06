"""Post-processing pipeline.

Triggered by a download-client webhook (SABnzbd, NZBGet) or a manual import.

Pipeline:
  1. detect_quality(filename)    — parse resolution + source + codec
  2. build_folder_name(event)    — Radarr-style "UFC 300 - Pereira vs Hill (2024-04-13)"
  3. build_file_name(...)        — "UFC 300 - Pereira vs Hill (2024-04-13) [WEBDL-1080p]"
  4. import_file(...)            — hardlink (same FS) or copy to media_root
  5. update Event + QueueItem    — status = DOWNLOADED, file_path, quality
  6. notify_plex / notify_jellyfin — library section refresh
"""

from __future__ import annotations

import logging
import os
import re
import shutil
from datetime import datetime
from pathlib import Path

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event, EventStatus
from app.models.queue_item import QueueItem, QueueStatus

logger = logging.getLogger(__name__)

# ── Quality detection ──────────────────────────────────────────────────────────

_RES = [
    (r"2160p", "2160p"),
    (r"1080p", "1080p"),
    (r"720p", "720p"),
    (r"480p", "480p"),
]
_SOURCE = [
    (r"WEB[\-\.]?DL", "WEB-DL"),
    (r"WEBRip", "WEBRip"),
    (r"AMZN", "WEB-DL"),
    (r"HULU", "WEB-DL"),
    (r"ESPN\+?", "WEB-DL"),
    (r"HDTV", "HDTV"),
    (r"Blu[\-\.]?Ray|BluRay", "BluRay"),
]
_CODEC = [
    (r"x265|H\.265|HEVC|H265", "x265"),
    (r"x264|H\.264|AVC|H264", "x264"),
]


def detect_quality(filename: str) -> str:
    """Parse a release filename and return a short quality string.

    Examples:
      "UFC.300.1080p.WEB-DL.x265" → "1080p WEB-DL x265"
      "UFC.Fight.Night.720p.HDTV"  → "720p HDTV"
    """
    name = filename.upper().replace(".", " ").replace("_", " ")
    parts: list[str] = []

    for pat, label in _RES:
        if re.search(pat, name, re.I):
            parts.append(label)
            break

    for pat, label in _SOURCE:
        if re.search(pat, name, re.I):
            parts.append(label)
            break

    for pat, label in _CODEC:
        if re.search(pat, name, re.I):
            parts.append(label)
            break

    return " ".join(parts) if parts else "Unknown"


# ── Naming ─────────────────────────────────────────────────────────────────────

_INVALID_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def _clean(s: str) -> str:
    return _INVALID_CHARS.sub("", s).strip()


def build_folder_name(event: Event) -> str:
    """Radarr-style folder: "UFC 300 - Pereira vs Hill (2024-04-13)"."""
    if event.event_number:
        base = f"UFC {event.event_number}"
    else:
        base = f"UFC Fight Night {event.event_date.strftime('%Y-%m-%d')}"

    if event.main_event:
        base += f" - {event.main_event}"

    base += f" ({event.event_date.strftime('%Y-%m-%d')})"
    return _clean(base)


def build_file_name(event: Event, quality: str, extension: str) -> str:
    """Radarr-style file: "UFC 300 - Pereira vs Hill (2024-04-13) [WEBDL-1080p].mkv"."""
    folder = build_folder_name(event)
    tag = quality.replace(" ", "-").replace("WEB-DL", "WEBDL") if quality else ""
    name = f"{folder} [{tag}]" if tag else folder
    ext = extension if extension.startswith(".") else f".{extension}"
    return _clean(name) + ext


# ── File import ────────────────────────────────────────────────────────────────

_VIDEO_EXTS = {".mkv", ".mp4", ".avi", ".ts", ".m2ts", ".mov"}


def find_video_file(path: str) -> Path | None:
    """Given a file or directory path, return the largest video file inside."""
    p = Path(path)
    if p.is_file() and p.suffix.lower() in _VIDEO_EXTS:
        return p
    if p.is_dir():
        candidates = [f for f in p.rglob("*") if f.suffix.lower() in _VIDEO_EXTS]
        return max(candidates, key=lambda f: f.stat().st_size) if candidates else None
    return None


def import_file(
    event: Event,
    source_path: str,
    media_root: str,
    use_hardlinks: bool = True,
) -> str:
    """Move or hardlink a video file into the library.

    Returns the final destination path.
    Raises FileNotFoundError if source_path contains no video file.
    """
    video = find_video_file(source_path)
    if video is None:
        raise FileNotFoundError(f"No video file found in {source_path!r}")

    quality = detect_quality(video.name)
    folder = build_folder_name(event)
    filename = build_file_name(event, quality, video.suffix)

    dest_dir = Path(media_root) / folder
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / filename

    if dest_path.exists():
        logger.info("Destination already exists, skipping: %s", dest_path)
        return str(dest_path)

    if use_hardlinks:
        try:
            os.link(video, dest_path)
            logger.info("Hardlinked %s → %s", video, dest_path)
            return str(dest_path)
        except OSError as e:
            logger.debug("Hardlink failed (%s), falling back to copy", e)

    shutil.copy2(video, dest_path)
    logger.info("Copied %s → %s", video, dest_path)
    return str(dest_path)


# ── Notifications ──────────────────────────────────────────────────────────────


async def notify_plex(host: str, token: str, section_id: str) -> bool:
    """Trigger a Plex library section refresh."""
    if not host or not token:
        return False
    url = f"{host.rstrip('/')}/library/sections/{section_id or 'all'}/refresh"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(url, params={"X-Plex-Token": token})
            r.raise_for_status()
        logger.info("Plex library refresh triggered")
        return True
    except Exception as exc:
        logger.warning("Plex notify failed: %s", exc)
        return False


async def notify_jellyfin(host: str, token: str, library_id: str = "") -> bool:
    """Trigger a Jellyfin library scan."""
    if not host or not token:
        return False
    path = f"/Items/{library_id}/Refresh" if library_id else "/Library/Refresh"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(
                f"{host.rstrip('/')}{path}",
                headers={"X-Emby-Token": token},
            )
            r.raise_for_status()
        logger.info("Jellyfin library refresh triggered")
        return True
    except Exception as exc:
        logger.warning("Jellyfin notify failed: %s", exc)
        return False


# ── Full pipeline ──────────────────────────────────────────────────────────────


async def run_postprocess(
    event: Event,
    download_path: str,
    queue_item: QueueItem | None,
    session: AsyncSession,
    media_root: str,
    use_hardlinks: bool,
    plex_host: str = "",
    plex_token: str = "",
    plex_section_id: str = "",
    jellyfin_host: str = "",
    jellyfin_token: str = "",
    jellyfin_library_id: str = "",
) -> dict:
    """Run the full post-processing pipeline for one completed download."""
    try:
        dest_path = import_file(event, download_path, media_root, use_hardlinks)
    except FileNotFoundError as exc:
        logger.error("Post-process failed: %s", exc)
        if queue_item:
            queue_item.status = QueueStatus.FAILED
            queue_item.error_message = str(exc)
            await session.commit()
        return {"status": "error", "message": str(exc)}

    quality = detect_quality(Path(dest_path).name)

    # Update event
    event.file_path = dest_path
    event.quality = quality
    event.status = EventStatus.DOWNLOADED

    # Update queue item
    if queue_item:
        queue_item.status = QueueStatus.IMPORTED
        queue_item.download_path = dest_path
        queue_item.completed_at = datetime.utcnow()

    await session.commit()
    logger.info("Imported %s → %s [%s]", event.slug, dest_path, quality)

    # Notifications (non-fatal)
    await notify_plex(plex_host, plex_token, plex_section_id)
    await notify_jellyfin(jellyfin_host, jellyfin_token, jellyfin_library_id)

    return {"status": "imported", "file": dest_path, "quality": quality}
