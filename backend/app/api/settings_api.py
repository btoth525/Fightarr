"""Settings endpoints — SABnzbd config, naming, quality profiles.

Stubbed for now. Backed by a small key/value config table in a future PR.
"""

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import settings

router = APIRouter()


class DownloadClientSettings(BaseModel):
    sabnzbd_url: str
    sabnzbd_apikey: str
    sabnzbd_category: str


class MetadataSettings(BaseModel):
    tmdb_api_key: str
    configured: bool


@router.get("/settings/downloadclient", response_model=DownloadClientSettings)
async def get_download_client_settings() -> DownloadClientSettings:
    return DownloadClientSettings(
        sabnzbd_url=settings.sabnzbd_url,
        sabnzbd_apikey="***" if settings.sabnzbd_apikey else "",
        sabnzbd_category=settings.sabnzbd_category,
    )


@router.get("/settings/metadata", response_model=MetadataSettings)
async def get_metadata_settings() -> MetadataSettings:
    return MetadataSettings(
        tmdb_api_key="***" if settings.tmdb_api_key else "",
        configured=bool(settings.tmdb_api_key),
    )


@router.post("/settings/metadata/test")
async def test_tmdb_connection() -> dict:
    from app.services.tmdb import test_connection

    ok = await test_connection(settings.tmdb_api_key)
    return {"success": ok, "message": "Connected to TMDB" if ok else "Connection failed"}


# ── Media management ──────────────────────────────────────────────────────────


class MediaSettings(BaseModel):
    media_root: str
    use_hardlinks: bool


@router.get("/settings/media", response_model=MediaSettings)
async def get_media_settings() -> MediaSettings:
    return MediaSettings(
        media_root=settings.media_root,
        use_hardlinks=settings.use_hardlinks,
    )


# ── Connect (Plex / Jellyfin) ─────────────────────────────────────────────────


class PlexSettings(BaseModel):
    host: str
    token_set: bool
    section_id: str


class JellyfinSettings(BaseModel):
    host: str
    token_set: bool
    library_id: str


@router.get("/settings/connect/plex", response_model=PlexSettings)
async def get_plex_settings() -> PlexSettings:
    return PlexSettings(
        host=settings.plex_host,
        token_set=bool(settings.plex_token),
        section_id=settings.plex_section_id,
    )


@router.post("/settings/connect/plex/test")
async def test_plex_connection() -> dict:

    if not settings.plex_host or not settings.plex_token:
        return {"success": False, "message": "Host or token not configured"}

    # Use /identity to test without triggering a full scan
    import httpx

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            r = await client.get(
                f"{settings.plex_host.rstrip('/')}/identity",
                params={"X-Plex-Token": settings.plex_token},
            )
            r.raise_for_status()
        return {"success": True, "message": "Connected to Plex"}
    except Exception as exc:
        return {"success": False, "message": str(exc)}


@router.get("/settings/connect/jellyfin", response_model=JellyfinSettings)
async def get_jellyfin_settings() -> JellyfinSettings:
    return JellyfinSettings(
        host=settings.jellyfin_host,
        token_set=bool(settings.jellyfin_token),
        library_id=settings.jellyfin_library_id,
    )


@router.post("/settings/connect/jellyfin/test")
async def test_jellyfin_connection() -> dict:
    import httpx

    if not settings.jellyfin_host or not settings.jellyfin_token:
        return {"success": False, "message": "Host or token not configured"}

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            r = await client.get(
                f"{settings.jellyfin_host.rstrip('/')}/System/Info",
                headers={"X-Emby-Token": settings.jellyfin_token},
            )
            r.raise_for_status()
        return {"success": True, "message": "Connected to Jellyfin"}
    except Exception as exc:
        return {"success": False, "message": str(exc)}
