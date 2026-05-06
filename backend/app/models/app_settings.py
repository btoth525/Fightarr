"""Single-row settings table — all GUI-configurable app settings."""

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AppSettings(Base):
    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Media library
    media_root: Mapped[str] = mapped_column(String(500), default="/media")
    use_hardlinks: Mapped[bool] = mapped_column(Boolean, default=True)

    # TMDB (optional)
    tmdb_api_key: Mapped[str] = mapped_column(String(200), default="")

    # Plex
    plex_host: Mapped[str] = mapped_column(String(500), default="")
    plex_token: Mapped[str] = mapped_column(String(200), default="")
    plex_section_id: Mapped[str] = mapped_column(String(50), default="")

    # Jellyfin
    jellyfin_host: Mapped[str] = mapped_column(String(500), default="")
    jellyfin_token: Mapped[str] = mapped_column(String(200), default="")
    jellyfin_library_id: Mapped[str] = mapped_column(String(50), default="")
