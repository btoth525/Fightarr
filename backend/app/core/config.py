"""Application configuration loaded from environment variables."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration. Override via env vars prefixed with FIGHTARR_."""

    model_config = SettingsConfigDict(
        env_prefix="FIGHTARR_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Storage
    db_path: Path = Path("./fightarr.db")

    # Logging
    log_level: str = "INFO"

    # CORS — allow Vite dev server by default
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost:7878",
        "http://127.0.0.1:5173",
    ]

    # Scheduler intervals (seconds)
    schedule_refresh_interval: int = 60 * 60 * 6  # 6 hours
    indexer_search_interval: int = 60 * 30  # 30 minutes

    # Newznab — at least one indexer required for actual searching
    # These can be set via the UI; env vars are just defaults for dev
    default_indexer_url: str = ""
    default_indexer_apikey: str = ""

    # TMDB metadata
    tmdb_api_key: str = ""

    # SABnzbd
    sabnzbd_url: str = ""
    sabnzbd_apikey: str = ""
    sabnzbd_category: str = "ufc"


settings = Settings()
