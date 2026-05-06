"""Download client model.

Supports NZB clients (SABnzbd, NZBGet), torrent clients (qBittorrent,
Deluge, Transmission), and Real-Debrid for premium link resolution.
"""

from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class DownloadClientType(str, Enum):
    SABNZBD = "sabnzbd"
    NZBGET = "nzbget"
    QBITTORRENT = "qbittorrent"
    DELUGE = "deluge"
    TRANSMISSION = "transmission"
    REAL_DEBRID = "real_debrid"


# Which protocol each client speaks — used to match indexer type to client type.
NZB_CLIENTS = {DownloadClientType.SABNZBD, DownloadClientType.NZBGET}
TORRENT_CLIENTS = {
    DownloadClientType.QBITTORRENT,
    DownloadClientType.DELUGE,
    DownloadClientType.TRANSMISSION,
}


class DownloadClient(Base):
    """A configured download client."""

    __tablename__ = "download_clients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    name: Mapped[str] = mapped_column(String(128))
    client_type: Mapped[DownloadClientType] = mapped_column(String(32))

    # Connection
    host: Mapped[str] = mapped_column(String(512))
    # e.g. "http://localhost:8080" — no trailing slash

    # Auth — NZB clients and Real-Debrid use api_key; torrent clients use user/pass
    api_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    username: Mapped[str | None] = mapped_column(String(128), nullable=True)
    password: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Download category / label applied to grabbed items
    category: Mapped[str] = mapped_column(String(64), default="ufc")

    enabled: Mapped[bool] = mapped_column(default=True)
    priority: Mapped[int] = mapped_column(Integer, default=25)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<DownloadClient {self.name} ({self.client_type})>"
