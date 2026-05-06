"""Tests for the Wikipedia scraper.

Uses a small synthetic HTML fixture rather than hitting Wikipedia in tests.
The fixture mirrors the table structure of {YEAR}_in_UFC pages.
"""

from app.scrapers.wikipedia import _parse_year_page


FIXTURE_HTML = """
<html><body>
<h2>Held events</h2>
<table class="wikitable">
  <tr>
    <th>#</th><th>Event</th><th>Date</th><th>Venue</th><th>City</th><th>Country</th>
  </tr>
  <tr>
    <td>759</td>
    <td>UFC 324: Gaethje vs. Pimblett</td>
    <td>January 24, 2026</td>
    <td>T-Mobile Arena</td>
    <td>Las Vegas, Nevada</td>
    <td>United States</td>
  </tr>
  <tr>
    <td>760</td>
    <td>UFC Fight Night: Strickland vs. Hernandez</td>
    <td>February 7, 2026</td>
    <td>Toyota Center</td>
    <td>Houston, Texas</td>
    <td>United States</td>
  </tr>
</table>

<h2>Announced events</h2>
<table class="wikitable">
  <tr>
    <th>Event</th><th>Date</th><th>Venue</th><th>City</th><th>Country</th><th>Ref.</th>
  </tr>
  <tr>
    <td>UFC 327: Procházka vs. Ulberg</td>
    <td>April 11, 2026</td>
    <td>Kaseya Center</td>
    <td>Miami, Florida</td>
    <td>United States</td>
    <td></td>
  </tr>
  <tr>
    <td>UFC White House[note 1]</td>
    <td>June 14, 2026</td>
    <td>White House</td>
    <td>Washington, D.C.</td>
    <td>United States</td>
    <td></td>
  </tr>
</table>
</body></html>
"""


def test_parses_numbered_event():
    events = _parse_year_page(FIXTURE_HTML, 2026, source_url="test")
    ufc_324 = next(e for e in events if e.event_number == 324)

    assert ufc_324.title == "UFC 324: Gaethje vs. Pimblett"
    assert ufc_324.event_type == "ppv"
    assert ufc_324.event_number == 324
    assert ufc_324.event_date.isoformat() == "2026-01-24"
    assert ufc_324.venue == "T-Mobile Arena"
    assert "Las Vegas" in ufc_324.location
    assert ufc_324.main_event == "Gaethje vs. Pimblett"


def test_parses_fight_night():
    events = _parse_year_page(FIXTURE_HTML, 2026, source_url="test")
    fn = next(e for e in events if "Strickland vs" in e.title)

    assert fn.event_type == "fight_night"
    assert fn.event_number is None
    assert fn.event_date.isoformat() == "2026-02-07"


def test_strips_citation_markers():
    events = _parse_year_page(FIXTURE_HTML, 2026, source_url="test")
    wh = next(e for e in events if "White House" in e.title)

    # [note 1] should be stripped
    assert "[note" not in wh.title
    assert wh.event_date.isoformat() == "2026-06-14"


def test_dedupes_by_slug():
    """Same event in two tables should appear only once."""
    duplicated = FIXTURE_HTML + FIXTURE_HTML
    events = _parse_year_page(duplicated, 2026, source_url="test")
    titles = [e.title for e in events]
    assert len(titles) == len(set(titles))


def test_slug_is_stable():
    events = _parse_year_page(FIXTURE_HTML, 2026, source_url="test")
    ufc_324 = next(e for e in events if e.event_number == 324)
    assert ufc_324.slug == "ufc-324-gaethje-vs-pimblett"


def test_non_ufc_rows_skipped():
    """Rows that don't start with 'UFC' should be filtered out."""
    html_with_noise = FIXTURE_HTML.replace(
        "<td>UFC 324: Gaethje vs. Pimblett</td>",
        "<td>Random non-UFC row</td>",
        1,
    )
    events = _parse_year_page(html_with_noise, 2026, source_url="test")
    assert all(e.title.lower().startswith("ufc") for e in events)
