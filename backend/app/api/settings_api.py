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


# TODO: PUT endpoint that persists to a settings table
