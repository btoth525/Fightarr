"""Blocklist model — releases that should never be auto-grabbed again.

When a download fails (corrupt NZB, broken torrent, password-protected, wrong
content, etc.), the queue monitor adds the release to this table. The next
auto-search run filters out anything matching by URL or title so we don't grab
the same broken release in an infinite loop. Mirrors Radarr's blocklist.
"""

from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class BlocklistEntry(Base):
    __tablename__ = "blocklist"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    event_id: Mapped[int | None] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), nullable=True, index=True
    )
    release_title: Mapped[str] = mapped_column(Text, index=True)
    nzb_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    indexer_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    blocked_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
