"""DB-backed application settings.

The app_settings table has exactly one row (id=1). On first access,
if the row is missing, it is seeded from FIGHTARR_* env vars so
Docker env-var configs migrate automatically into the GUI.

Token fields use the sentinel "***" — API callers return this when a
token is set but should not be exposed; PUT handlers preserve the
existing DB value when they receive the sentinel back.
"""

from __future__ import annotations

from app.core.database import AsyncSessionLocal
from app.models.app_settings import AppSettings

SENTINEL = "***"


async def load_settings() -> AppSettings:
    """Return the settings row, creating it from env vars on first boot."""
    async with AsyncSessionLocal() as session:
        row = await session.get(AppSettings, 1)
        if row is None:
            row = await _seed_from_env(session)
        return row


async def _seed_from_env(session) -> AppSettings:
    """Create settings row #1 from FIGHTARR_* environment variables."""
    from app.core.config import settings as env

    row = AppSettings(
        id=1,
        media_root=str(env.media_root),
        use_hardlinks=env.use_hardlinks,
        tmdb_api_key=env.tmdb_api_key,
        plex_host=env.plex_host,
        plex_token=env.plex_token,
        plex_section_id=env.plex_section_id,
        jellyfin_host=env.jellyfin_host,
        jellyfin_token=env.jellyfin_token,
        jellyfin_library_id=env.jellyfin_library_id,
        webhook_url=getattr(env, "webhook_url", ""),
        webhook_events=getattr(env, "webhook_events", "grab,import,failed"),
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row
