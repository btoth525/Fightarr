"""Settings endpoints — DB-backed, fully GUI-editable.

All settings are stored in the app_settings table (single row).
On first boot they are seeded from FIGHTARR_* env vars automatically.

Token fields are masked as "***" in GET responses.
PUT handlers preserve the existing token when they receive "***" back.
"""

import httpx
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.app_settings import AppSettings
from app.services.settings_service import SENTINEL, _seed_from_env

router = APIRouter()


# ── Helpers ───────────────────────────────────────────────────────────────────


def _mask(value: str) -> str:
    return SENTINEL if value else ""


async def _row(session: AsyncSession) -> AppSettings:
    row = await session.get(AppSettings, 1)
    if row is None:
        row = await _seed_from_env(session)
    return row


# ── Output schema ─────────────────────────────────────────────────────────────


class SettingsOut(BaseModel):
    media_root: str
    use_hardlinks: bool
    tmdb_api_key: str
    plex_host: str
    plex_token: str
    plex_section_id: str
    jellyfin_host: str
    jellyfin_token: str
    jellyfin_library_id: str


def _out(r: AppSettings) -> SettingsOut:
    return SettingsOut(
        media_root=r.media_root,
        use_hardlinks=r.use_hardlinks,
        tmdb_api_key=_mask(r.tmdb_api_key),
        plex_host=r.plex_host,
        plex_token=_mask(r.plex_token),
        plex_section_id=r.plex_section_id,
        jellyfin_host=r.jellyfin_host,
        jellyfin_token=_mask(r.jellyfin_token),
        jellyfin_library_id=r.jellyfin_library_id,
    )


# ── GET all ───────────────────────────────────────────────────────────────────


@router.get("/settings", response_model=SettingsOut)
async def get_settings(session: AsyncSession = Depends(get_session)) -> SettingsOut:
    return _out(await _row(session))


# ── PUT per section ───────────────────────────────────────────────────────────


class MediaIn(BaseModel):
    media_root: str
    use_hardlinks: bool


@router.put("/settings/media", response_model=SettingsOut)
async def update_media(body: MediaIn, session: AsyncSession = Depends(get_session)) -> SettingsOut:
    r = await _row(session)
    r.media_root = body.media_root
    r.use_hardlinks = body.use_hardlinks
    await session.commit()
    await session.refresh(r)
    return _out(r)


class TmdbIn(BaseModel):
    tmdb_api_key: str


@router.put("/settings/tmdb", response_model=SettingsOut)
async def update_tmdb(body: TmdbIn, session: AsyncSession = Depends(get_session)) -> SettingsOut:
    r = await _row(session)
    if body.tmdb_api_key != SENTINEL:
        r.tmdb_api_key = body.tmdb_api_key
    await session.commit()
    await session.refresh(r)
    return _out(r)


class PlexIn(BaseModel):
    plex_host: str
    plex_token: str
    plex_section_id: str


@router.put("/settings/connect/plex", response_model=SettingsOut)
async def update_plex(body: PlexIn, session: AsyncSession = Depends(get_session)) -> SettingsOut:
    r = await _row(session)
    r.plex_host = body.plex_host
    if body.plex_token != SENTINEL:
        r.plex_token = body.plex_token
    r.plex_section_id = body.plex_section_id
    await session.commit()
    await session.refresh(r)
    return _out(r)


class JellyfinIn(BaseModel):
    jellyfin_host: str
    jellyfin_token: str
    jellyfin_library_id: str


@router.put("/settings/connect/jellyfin", response_model=SettingsOut)
async def update_jellyfin(
    body: JellyfinIn, session: AsyncSession = Depends(get_session)
) -> SettingsOut:
    r = await _row(session)
    r.jellyfin_host = body.jellyfin_host
    if body.jellyfin_token != SENTINEL:
        r.jellyfin_token = body.jellyfin_token
    r.jellyfin_library_id = body.jellyfin_library_id
    await session.commit()
    await session.refresh(r)
    return _out(r)


# ── Test connections ──────────────────────────────────────────────────────────


@router.post("/settings/metadata/test")
async def test_tmdb(session: AsyncSession = Depends(get_session)) -> dict:
    from app.services.tmdb import test_connection

    r = await _row(session)
    ok = await test_connection(r.tmdb_api_key)
    return {"success": ok, "message": "Connected to TMDB" if ok else "No key or connection failed"}


@router.post("/settings/connect/plex/test")
async def test_plex(session: AsyncSession = Depends(get_session)) -> dict:
    r = await _row(session)
    if not r.plex_host or not r.plex_token:
        return {"success": False, "message": "Host or token not configured"}
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(
                f"{r.plex_host.rstrip('/')}/identity",
                params={"X-Plex-Token": r.plex_token},
            )
            resp.raise_for_status()
        return {"success": True, "message": "Connected to Plex"}
    except Exception as exc:
        return {"success": False, "message": str(exc)}


@router.post("/settings/connect/jellyfin/test")
async def test_jellyfin(session: AsyncSession = Depends(get_session)) -> dict:
    r = await _row(session)
    if not r.jellyfin_host or not r.jellyfin_token:
        return {"success": False, "message": "Host or token not configured"}
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(
                f"{r.jellyfin_host.rstrip('/')}/System/Info",
                headers={"X-Emby-Token": r.jellyfin_token},
            )
            resp.raise_for_status()
        return {"success": True, "message": "Connected to Jellyfin"}
    except Exception as exc:
        return {"success": False, "message": str(exc)}
