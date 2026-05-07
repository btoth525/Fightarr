"""Queue item model — tracks downloads currently in SABnzbd."""

from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class QueueStatus(str, Enum):
    GRABBED = "grabbed"  # Pushed to SABnzbd
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"
    IMPORTED = "imported"  # Renamed and moved to library


class QueueItem(Base):
    __tablename__ = "queue"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"), index=True)

    release_title: Mapped[str] = mapped_column(Text)
    release_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    indexer_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    nzb_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    download_client_id: Mapped[int | None] = mapped_column(
        ForeignKey("download_clients.id", ondelete="SET NULL"), nullable=True
    )
    # which download client holds this job

    sabnzbd_nzo_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # generic external job ID (SABnzbd nzo_id, NZBGet NZBID, qBit hash, etc.)

    download_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    # set by the webhook / post-process to the completed download dir

    status: Mapped[QueueStatus] = mapped_column(String(32), default=QueueStatus.GRABBED, index=True)

    progress_percent: Mapped[float] = mapped_column(default=0.0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # How many times we've attempted to import this download. Caps the retry
    # loop so a stuck COMPLETED item eventually flips to FAILED (which then
    # triggers blocklist + auto-search for an alternative release).
    import_attempts: Mapped[int] = mapped_column(Integer, default=0)

    grabbed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
