"""Fightarr — UFC event manager for Usenet and Plex.

This is the FastAPI entry point. It wires up the database, the routers, and
the background scheduler that periodically refreshes UFC event data from
upstream sources (Wikipedia, UFCStats).
"""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import download_clients, events, health, indexers, queue, settings_api, webhooks
from app.core.config import settings
from app.core.database import init_db
from app.core.scheduler import start_scheduler, stop_scheduler

logger = logging.getLogger(__name__)


async def _startup_sync() -> None:
    """Run an initial schedule sync in the background so the DB isn't empty on first boot."""
    from app.services.schedule_sync import sync_schedule

    try:
        count = await sync_schedule()
        logger.info("Startup sync complete: %d events", count)
    except Exception as exc:
        logger.warning("Startup sync failed (non-fatal): %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run on startup and shutdown."""
    await init_db()
    start_scheduler()
    asyncio.create_task(_startup_sync())
    yield
    stop_scheduler()


app = FastAPI(
    title="Fightarr",
    description="UFC event manager for Usenet and Plex.",
    version="0.0.1",
    lifespan=lifespan,
)

# CORS — parse comma-separated string; "*" means allow all
_raw_origins = settings.cors_origins.strip()
_allow_all = _raw_origins == "*"
_cors_origins = ["*"] if _allow_all else [o.strip() for o in _raw_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_origin_regex=None,
    allow_credentials=not _allow_all,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers — mirror Radarr's /api/v3 shape but at /api/v1 to keep our own versioning
API_PREFIX = "/api/v1"

app.include_router(health.router, prefix=API_PREFIX, tags=["health"])
app.include_router(events.router, prefix=API_PREFIX, tags=["events"])
app.include_router(indexers.router, prefix=API_PREFIX, tags=["indexers"])
app.include_router(download_clients.router, prefix=API_PREFIX, tags=["download-clients"])
app.include_router(queue.router, prefix=API_PREFIX, tags=["queue"])
app.include_router(settings_api.router, prefix=API_PREFIX, tags=["settings"])
app.include_router(webhooks.router, prefix=API_PREFIX, tags=["webhooks"])


@app.get("/")
async def root():
    return {
        "app": "Fightarr",
        "version": "0.0.1",
        "docs": "/docs",
        "api": API_PREFIX,
    }
