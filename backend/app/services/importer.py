"""Post-processing pipeline — Radarr-style import for Plex.

When a download completes:
  1. Find the largest video file in the download folder (skip samples).
  2. Detect Radarr-style quality profile: WEBDL-1080p, Bluray-2160p, etc.
  3. Build a Plex-compatible folder/file structure:
       {media_root}/UFC 300 - Pereira vs Hill (2024)/
         UFC 300 - Pereira vs Hill (2024) WEBDL-1080p.mkv
         poster.jpg
  4. Hardlink (or copy if cross-device) the video file.
  5. Download poster.jpg from event.poster_url so Plex picks it up locally.
  6. Update Event.file_path / quality / status and QueueItem.status.
  7. Notify Plex / Jellyfin if configured.
"""

import logging
import os
import re
import shutil
from datetime import UTC, datetime
from pathlib import Path

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event, EventStatus
from app.models.queue_item import QueueItem, QueueStatus

logger = logging.getLogger(__name__)

VIDEO_EXTS = {".mkv", ".mp4", ".avi", ".m4v", ".mov", ".wmv", ".ts", ".mpg", ".mpeg"}
SAMPLE_RE = re.compile(r"\bsample\b", re.IGNORECASE)
MIN_FILE_BYTES = 100 * 1024 * 1024  # 100 MB — anything smaller is almost certainly a sample


async def import_download(session: AsyncSession, item: QueueItem) -> None:
    """Move a completed download into the media library, Radarr-style."""
    from app.services.settings_service import load_settings

    event = await session.get(Event, item.event_id)
    if event is None:
        raise ValueError(f"Event {item.event_id} not found")

    db_settings = await load_settings()
    media_root = Path(db_settings.media_root)

    video_file = _find_video_file(item.download_path)
    if video_file is None:
        raise FileNotFoundError(f"No video file in {item.download_path!r}")

    quality = _detect_quality(video_file.name) or _detect_quality(item.release_title)

    folder_name = _build_event_folder_name(event)
    dest_dir = media_root / folder_name
    dest_dir.mkdir(parents=True, exist_ok=True)

    dest_file = dest_dir / _build_filename(folder_name, quality, video_file.suffix)
    _move_file(video_file, dest_file, use_hardlinks=db_settings.use_hardlinks)

    await _save_poster(event, dest_dir)

    event.file_path = str(dest_file)
    event.quality = quality
    event.status = EventStatus.DOWNLOADED

    item.status = QueueStatus.IMPORTED
    item.completed_at = datetime.now(UTC)
    item.download_path = str(dest_file)

    await _notify_media_servers(db_settings)
    logger.info("Imported %s → %s", video_file, dest_file)


def _find_video_file(download_path: str | None) -> Path | None:
    """Largest non-sample video file under download_path."""
    if not download_path:
        return None
    root = Path(download_path)
    if not root.exists():
        return None
    if root.is_file() and root.suffix.lower() in VIDEO_EXTS:
        return root

    candidates: list[Path] = []
    for f in root.rglob("*"):
        if not f.is_file() or f.suffix.lower() not in VIDEO_EXTS:
            continue
        if SAMPLE_RE.search(f.name):
            continue
        try:
            if f.stat().st_size < MIN_FILE_BYTES:
                continue
        except OSError:
            continue
        candidates.append(f)

    if not candidates:
        return None
    return max(candidates, key=lambda f: f.stat().st_size)


def _detect_quality(name: str) -> str:
    """Radarr-style quality profile: 'WEBDL-1080p', 'Bluray-2160p', etc."""
    upper = name.upper()

    res = ""
    if "2160P" in upper or "4K" in upper or "UHD" in upper:
        res = "2160p"
    elif "1080P" in upper:
        res = "1080p"
    elif "720P" in upper:
        res = "720p"
    elif "480P" in upper:
        res = "480p"

    src = ""
    if "WEB-DL" in upper or "WEBDL" in upper or "WEB DL" in upper:
        src = "WEBDL"
    elif "WEBRIP" in upper or "WEB-RIP" in upper or "WEB RIP" in upper:
        src = "WEBRip"
    elif "BLURAY" in upper or "BLU-RAY" in upper or "BLU RAY" in upper:
        src = "Bluray"
    elif "HDTV" in upper:
        src = "HDTV"

    if src and res:
        return f"{src}-{res}"
    if res:
        return res
    if src:
        return src
    return "Unknown"


def _sanitize(name: str) -> str:
    """Strip filesystem-illegal characters and collapse whitespace."""
    cleaned = name.replace(":", " -").replace("/", "-").replace("\\", "-")
    cleaned = re.sub(r'[?*"<>|]', "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _build_event_folder_name(event: Event) -> str:
    """Plex-compatible folder name: 'UFC 300 - Pereira vs Hill (2024)'."""
    title = _sanitize(event.title)
    year = event.event_date.year if event.event_date else None
    return f"{title} ({year})" if year else title


def _build_filename(folder_name: str, quality: str, ext: str) -> str:
    """Final filename: '{folder_name} {quality}.{ext}'.

    Matches Radarr's default movie naming so Plex picks up quality automatically.
    """
    if quality and quality != "Unknown":
        return f"{folder_name} {quality}{ext}"
    return f"{folder_name}{ext}"


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


async def _save_poster(event: Event, dest_dir: Path) -> None:
    """Download event.poster_url into dest_dir/poster.{ext}.

    Plex's Local Media Assets agent reads poster.jpg / poster.png from the movie
    folder, so this gives Plex the correct cover art even without TMDB matches.
    """
    if not event.poster_url:
        return
    # Don't redownload if poster already exists in this folder
    for existing in ("poster.jpg", "poster.png", "poster.webp"):
        if (dest_dir / existing).exists():
            return
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            r = await client.get(event.poster_url)
            r.raise_for_status()
            ct = r.headers.get("content-type", "").lower()
            ext = ".jpg"
            if "png" in ct:
                ext = ".png"
            elif "webp" in ct:
                ext = ".webp"
            (dest_dir / f"poster{ext}").write_bytes(r.content)
            logger.info("Saved poster%s for %s", ext, event.slug)
    except Exception as exc:
        logger.warning("Could not save poster for %s: %s", event.slug, exc)


async def _notify_media_servers(db_settings) -> None:
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
