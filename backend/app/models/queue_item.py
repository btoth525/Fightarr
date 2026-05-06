"""Queue item model — tracks downloads currently in SABnzbd."""
from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class QueueStatus(str, Enum):
    GRABBED = "grabbed"        # Pushed to SABnzbd
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"
    IMPORTED = "imported"      # Renamed and moved to library


class QueueItem(Base):
    __tablename__ = "queue"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    event_id: Mapped[int] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), index=True
    )

    release_title: Mapped[str] = mapped_column(Text)
    release_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    indexer_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    nzb_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    sabnzbd_nzo_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # SABnzbd's identifier for the download

    status: Mapped[QueueStatus] = mapped_column(
        String(32), default=QueueStatus.GRABBED, index=True
    )

    progress_percent: Mapped[float] = mapped_column(default=0.0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    grabbed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
