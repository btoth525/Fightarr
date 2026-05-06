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


@router.get("/settings/downloadclient", response_model=DownloadClientSettings)
async def get_download_client_settings() -> DownloadClientSettings:
    return DownloadClientSettings(
        sabnzbd_url=settings.sabnzbd_url,
        sabnzbd_apikey="***" if settings.sabnzbd_apikey else "",
        sabnzbd_category=settings.sabnzbd_category,
    )


# TODO: PUT endpoint that persists to a settings table
