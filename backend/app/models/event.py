"""UFC event model.

An "event" is one fight card — UFC 300, UFC Fight Night: Hill vs Pereira,
UFC on ABC 6, etc. Each event has a date, a venue, a main event, and a
status that tracks its lifecycle through the system.
"""

from datetime import date, datetime
from enum import Enum

from sqlalchemy import Date, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class EventStatus(str, Enum):
    """Lifecycle states for an event, mirroring Radarr's movie statuses."""

    ANNOUNCED = "announced"  # On the schedule, in the future
    UPCOMING = "upcoming"  # Within search window (e.g. 7 days out)
    AIRING = "airing"  # Happening today
    RELEASED = "released"  # Aired, looking for downloads
    DOWNLOADED = "downloaded"  # Have a file
    MISSING = "missing"  # Aired, monitored, no file


class EventType(str, Enum):
    """UFC event categories."""

    PPV = "ppv"  # Numbered events (UFC 300)
    FIGHT_NIGHT = "fight_night"  # Fight Night cards
    ON_ABC = "on_abc"  # UFC on ABC / Fox / ESPN specials
    TUF_FINALE = "tuf_finale"  # The Ultimate Fighter finales
    OTHER = "other"


class Event(Base):
    """A single UFC fight card."""

    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Identity
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    # e.g. "ufc-300", "ufc-fight-night-2024-04-06"

    title: Mapped[str] = mapped_column(String(255))
    # e.g. "UFC 300: Pereira vs Hill"

    event_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # e.g. 300 for UFC 300; null for Fight Nights

    event_type: Mapped[EventType] = mapped_column(String(32))

    # Schedule
    event_date: Mapped[date] = mapped_column(Date, index=True)
    venue: Mapped[str | None] = mapped_column(String(255), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Card info
    main_event: Mapped[str | None] = mapped_column(String(255), nullable=True)
    co_main_event: Mapped[str | None] = mapped_column(String(255), nullable=True)
    card_data: Mapped[str | None] = mapped_column(Text, nullable=True)
    # JSON blob of full card structure (main, prelims, early prelims)

    # Status
    status: Mapped[EventStatus] = mapped_column(
        String(32), default=EventStatus.ANNOUNCED, index=True
    )
    monitored: Mapped[bool] = mapped_column(default=True)

    # File info (once downloaded)
    file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    quality: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # e.g. "1080p WEB-DL"

    # Bookkeeping
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Source tracking — where did we learn about this event?
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<Event {self.slug} ({self.event_date})>"
