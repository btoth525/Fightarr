"""Wikipedia scraper for UFC events.

Source pages:
  - https://en.wikipedia.org/wiki/{YEAR}_in_UFC      (year-specific summary)
  - https://en.wikipedia.org/wiki/List_of_UFC_events (master list, sortable)

The {YEAR}_in_UFC pages are the most useful for our purposes: they list both
announced (future) and held (past) events with dates, venues, and main events.
The structure is reasonably stable across years.

Output: list of ScrapedEvent dataclasses, ready to be merged into the DB.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import date, datetime

import httpx
from bs4 import BeautifulSoup, Tag

logger = logging.getLogger(__name__)

WIKI_BASE = "https://en.wikipedia.org"
USER_AGENT = "Fightarr/0.0.1 (+https://github.com/btoth525/Fightarr)"


@dataclass
class ScrapedEvent:
    """A UFC event as extracted from Wikipedia. Loosely typed on purpose —
    downstream code is responsible for normalizing into the DB model."""

    title: str
    event_date: date | None = None
    venue: str | None = None
    location: str | None = None
    main_event: str | None = None
    event_number: int | None = None
    event_type: str = "other"  # ppv | fight_night | on_abc | tuf_finale | other
    source_url: str | None = None
    raw_row: list[str] = field(default_factory=list)

    @property
    def slug(self) -> str:
        """Stable slug for deduplication."""
        base = self.title.lower()
        # Strip "ufc " prefix variants and punctuation
        base = re.sub(r"[^\w\s-]", "", base)
        base = re.sub(r"\s+", "-", base.strip())
        return base[:100]


# --- Public API ------------------------------------------------------------


async def fetch_year(year: int) -> list[ScrapedEvent]:
    """Fetch all UFC events for a given year from Wikipedia."""
    url = f"{WIKI_BASE}/wiki/{year}_in_UFC"
    logger.info("Fetching UFC schedule for %d from %s", year, url)

    async with httpx.AsyncClient(
        headers={"User-Agent": USER_AGENT}, timeout=30.0, follow_redirects=True
    ) as client:
        response = await client.get(url)
        response.raise_for_status()

    return _parse_year_page(response.text, year, source_url=url)


# --- Parsing ---------------------------------------------------------------


def _parse_year_page(html: str, year: int, source_url: str) -> list[ScrapedEvent]:
    """Parse a {YEAR}_in_UFC Wikipedia page.

    The page contains multiple tables. We're after the ones with columns
    matching (Event, Date, Venue, City, Country) — there are typically two:
    an 'Announced events' table for upcoming and a numbered table for past.
    """
    soup = BeautifulSoup(html, "lxml")
    events: dict[str, ScrapedEvent] = {}

    for table in soup.find_all("table", class_="wikitable"):
        headers = _table_headers(table)
        if not _is_event_table(headers):
            continue

        col_map = _build_column_map(headers)
        for row in table.find_all("tr")[1:]:  # Skip header row
            cells = row.find_all(["td", "th"])
            if len(cells) < 3:
                continue

            event = _parse_event_row(cells, col_map, year, source_url)
            if event is None:
                continue

            # Dedupe by slug — the same event may appear in multiple tables
            if event.slug not in events:
                events[event.slug] = event

    logger.info("Parsed %d events from %d_in_UFC", len(events), year)
    return list(events.values())


def _table_headers(table: Tag) -> list[str]:
    """Get header row text, lowercased."""
    head = table.find("tr")
    if head is None:
        return []
    return [_clean(c.get_text()) for c in head.find_all(["th", "td"])]


def _is_event_table(headers: list[str]) -> bool:
    """Heuristic: is this table a UFC events listing?"""
    lowered = [h.lower() for h in headers]
    has_event = any("event" in h for h in lowered)
    has_date = any(h == "date" for h in lowered)
    has_venue = any("venue" in h for h in lowered)
    return has_event and has_date and has_venue


def _build_column_map(headers: list[str]) -> dict[str, int]:
    """Map our canonical field names to column indices."""
    mapping = {}
    for i, header in enumerate(headers):
        h = header.lower()
        if "event" in h and "event" not in mapping:
            mapping["event"] = i
        elif h == "date":
            mapping["date"] = i
        elif "venue" in h:
            mapping["venue"] = i
        elif h == "city":
            mapping["city"] = i
        elif h == "country":
            mapping["country"] = i
    return mapping


def _parse_event_row(
    cells: list[Tag], col_map: dict[str, int], year: int, source_url: str
) -> ScrapedEvent | None:
    """Pull a ScrapedEvent out of one row's cells."""
    raw = [_clean(c.get_text()) for c in cells]

    title = _safe_get(raw, col_map.get("event"))
    if not title or len(title) < 3:
        return None
    if not title.lower().startswith("ufc"):
        return None  # Skip TUF/Contender Series rows on these pages

    parsed_date = _parse_date(_safe_get(raw, col_map.get("date")), year)

    venue = _safe_get(raw, col_map.get("venue"))
    city = _safe_get(raw, col_map.get("city"))
    country = _safe_get(raw, col_map.get("country"))
    location = ", ".join(p for p in [city, country] if p) or None

    event_type, event_number = _classify_event(title)
    main_event = _extract_main_event(title)

    return ScrapedEvent(
        title=title,
        event_date=parsed_date,
        venue=venue,
        location=location,
        main_event=main_event,
        event_number=event_number,
        event_type=event_type,
        source_url=source_url,
        raw_row=raw,
    )


def _classify_event(title: str) -> tuple[str, int | None]:
    """Classify by title. Returns (event_type, event_number)."""
    # Numbered PPV: "UFC 300", "UFC 300: Pereira vs Hill"
    m = re.match(r"^UFC\s+(\d+)\b", title)
    if m:
        return "ppv", int(m.group(1))

    if "tuf" in title.lower() or "ultimate fighter" in title.lower():
        return "tuf_finale", None

    if re.search(r"\bon\s+(ABC|FOX|CBS|ESPN)\b", title, re.IGNORECASE):
        return "on_abc", None

    if "fight night" in title.lower():
        return "fight_night", None

    return "other", None


def _extract_main_event(title: str) -> str | None:
    """Pull the 'Fighter A vs Fighter B' from a colon-suffixed title."""
    if ":" not in title:
        return None
    after_colon = title.split(":", 1)[1].strip()
    if " vs" in after_colon.lower():
        return after_colon
    return None


# --- Helpers ---------------------------------------------------------------


def _clean(text: str) -> str:
    """Normalize whitespace and strip Wikipedia citation markers."""
    text = re.sub(r"\[\d+\]", "", text)         # [1], [2]
    text = re.sub(r"\[note\s*\d+\]", "", text)  # [note 1]
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _safe_get(row: list[str], idx: int | None) -> str | None:
    if idx is None or idx >= len(row):
        return None
    val = row[idx].strip()
    return val if val else None


def _parse_date(date_str: str | None, year_hint: int) -> date | None:
    """Parse a date cell. Wikipedia uses several formats."""
    if not date_str:
        return None

    # Formats seen on these pages:
    # "January 24, 2026", "Jan 24, 2026", "2026-01-24", "January 24"
    formats = [
        "%B %d, %Y",
        "%b %d, %Y",
        "%Y-%m-%d",
        "%B %d",
        "%b %d",
    ]
    for fmt in formats:
        try:
            parsed = datetime.strptime(date_str, fmt)
            # If no year was in the string, use the hint
            if "%Y" not in fmt:
                parsed = parsed.replace(year=year_hint)
            return parsed.date()
        except ValueError:
            continue

    logger.debug("Could not parse date: %r", date_str)
    return None
