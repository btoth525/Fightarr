"""Indexer model — represents a configured Newznab or Torznab indexer."""

from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class IndexerType(str, Enum):
    NEWZNAB = "newznab"  # NZB indexers (NZBGeek, DrunkenSlug, etc.)
    TORZNAB = "torznab"  # Torrent indexers via Prowlarr/Jackett


class Indexer(Base):
    """A user-configured Newznab indexer (NZBGeek, DrunkenSlug, etc)."""

    __tablename__ = "indexers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    name: Mapped[str] = mapped_column(String(128))
    indexer_type: Mapped[IndexerType] = mapped_column(String(16), default=IndexerType.NEWZNAB)
    url: Mapped[str] = mapped_column(String(512))
    api_key: Mapped[str] = mapped_column(String(255))

    enabled: Mapped[bool] = mapped_column(default=True)
    priority: Mapped[int] = mapped_column(Integer, default=25)
    # Lower number = higher priority, matches Radarr convention

    # Search categories — Usenet sports is typically 5070 or 5080
    categories: Mapped[str] = mapped_column(String(255), default="5070,5080")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<Indexer {self.name}>"
