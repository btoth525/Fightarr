"""Health and system status endpoints."""
from fastapi import APIRouter

from app import __version__

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    return {"status": "ok", "version": __version__}


@router.get("/system/status")
async def system_status() -> dict:
    """Mirrors Radarr's /system/status shape, loosely."""
    return {
        "appName": "Fightarr",
        "version": __version__,
        "buildTime": None,
        "isDebug": False,
        "isProduction": True,
        "branch": "main",
    }
