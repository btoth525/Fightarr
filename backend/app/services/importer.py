"""Post-processing pipeline.

When a download completes:
  1. Find the largest video file in the download folder.
  2. Detect quality from the filename.
  3. Build a destination path under media_root/{year}/{event_slug}/.
  4. Hardlink (or copy if cross-device) the file.
  5. Update Event.file_path / quality / status and QueueItem.status.
  6. Notify Plex / Jellyfin if configured.
"""

import logging
import os
import shutil
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event, EventStatus
from app.models.queue_item import QueueItem, QueueStatus

logger = logging.getLogger(__name__)

VIDEO_EXTS = {".mkv", ".mp4", ".avi", ".m4v", ".mov", ".wmv", ".ts", ".mpg", ".mpeg"}


async def import_download(session: AsyncSession, item: QueueItem) -> None:
    """Move a completed download into the media library."""
    from app.services.settings_service import load_settings

    event = await session.get(Event, item.event_id)
    if event is None:
        raise ValueError(f"Event {item.event_id} not found")

    db_settings = await load_settings()
    media_root = Path(db_settings.media_root)

    video_file = _find_video_file(item.download_path, item.release_title)
    if video_file is None:
        raise FileNotFoundError(f"No video file in {item.download_path!r}")

    quality = _detect_quality(video_file.name) or _detect_quality(item.release_title)

    year = event.event_date.year if event.event_date else "unknown"
    dest_dir = media_root / str(year) / event.slug
    dest_dir.mkdir(parents=True, exist_ok=True)

    dest_file = dest_dir / _build_filename(event, quality, video_file.suffix)
    _move_file(video_file, dest_file, use_hardlinks=db_settings.use_hardlinks)

    event.file_path = str(dest_file)
    event.quality = quality
    event.status = EventStatus.DOWNLOADED

    item.status = QueueStatus.IMPORTED
    item.completed_at = datetime.now(UTC)
    item.download_path = str(dest_file)

    await _notify_media_servers(db_settings)
    logger.info("Imported %s → %s", video_file, dest_file)


def _find_video_file(download_path: str | None, release_title: str) -> Path | None:
    if not download_path:
        return None
    root = Path(download_path)
    if not root.exists():
        return None
    if root.is_file() and root.suffix.lower() in VIDEO_EXTS:
        return root
    candidates = [f for f in root.rglob("*") if f.suffix.lower() in VIDEO_EXTS]
    if not candidates:
        return None
    return max(candidates, key=lambda f: f.stat().st_size)


def _detect_quality(name: str) -> str:
    lower = name.lower()
    if any(x in lower for x in ("2160p", "4k", "uhd")):
        return "2160p"
    if "1080p" in lower:
        return "1080p"
    if "720p" in lower:
        return "720p"
    if "480p" in lower:
        return "480p"
    return "Unknown"


def _build_filename(event: Event, quality: str, ext: str) -> str:
    title = event.title.replace("/", "-").replace(":", " -").strip()
    year = event.event_date.year if event.event_date else ""
    return f"{title} ({year}) [{quality}]{ext}" if year else f"{title} [{quality}]{ext}"


def _move_file(src: Path, dest: Path, *, use_hardlinks: bool) -> None:
    if dest.exists():
        dest.unlink()
    if use_hardlinks:
        try:
            os.link(src, dest)
            return
        except OSError:
            pass  # Cross-device link — fall through to copy
    shutil.copy2(src, dest)


async def _notify_media_servers(db_settings) -> None:
    import httpx

    try:
        if db_settings.plex_host and db_settings.plex_token:
            section = db_settings.plex_section_id or "1"
            url = f"{db_settings.plex_host.rstrip('/')}/library/sections/{section}/refresh"
            async with httpx.AsyncClient(timeout=8.0) as c:
                await c.get(url, params={"X-Plex-Token": db_settings.plex_token})
            logger.info("Plex library scan triggered")
    except Exception as exc:
        logger.debug("Plex notify failed: %s", exc)

    try:
        if db_settings.jellyfin_host and db_settings.jellyfin_token:
            url = f"{db_settings.jellyfin_host.rstrip('/')}/Library/Refresh"
            async with httpx.AsyncClient(timeout=8.0) as c:
                await c.post(url, headers={"X-Emby-Token": db_settings.jellyfin_token})
            logger.info("Jellyfin library scan triggered")
    except Exception as exc:
        logger.debug("Jellyfin notify failed: %s", exc)
