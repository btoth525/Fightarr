"""Newznab API client.

Newznab is the de-facto API standard for Usenet indexers. NZBGeek,
DrunkenSlug, NZBPlanet, and most others all speak it.

Endpoint: GET {base_url}/api?t=search&q={query}&apikey={key}&cat={cats}
Response: RSS-like XML with <item> elements containing <title>, <enclosure
          url=...>, and optionally <newznab:attr name="size" value="..."/>.

parse_search_response() is public so tests (and the manual-search endpoint)
can exercise it directly without making HTTP calls.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx
from lxml import etree

logger = logging.getLogger(__name__)

_NEWZNAB_NS = "http://www.newznab.com/DTD/2010/feeds/attributes/"


@dataclass
class NewznabRelease:
    title: str
    nzb_url: str
    size_bytes: int | None
    indexer_name: str
    pub_date: str | None = None
    guid: str | None = None
    protocol: str = "nzb"


class NewznabError(Exception):
    """Raised when the indexer returns an <error> response."""

    def __init__(self, code: int, description: str) -> None:
        self.code = code
        self.description = description
        super().__init__(f"Newznab error {code}: {description}")


class NewznabClient:
    def __init__(self, name: str, base_url: str, api_key: str) -> None:
        self.name = name
        # Normalize: strip trailing slash and any trailing /api the user may have included
        url = base_url.rstrip("/")
        if url.endswith("/api"):
            url = url[:-4]
        self.base_url = url
        self.api_key = api_key

    async def test_connection(self) -> tuple[bool, str]:
        """Probe the indexer with t=caps. Returns (ok, message)."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(
                    f"{self.base_url}/api",
                    params={"t": "caps", "apikey": self.api_key, "o": "xml"},
                )
                r.raise_for_status()
            return True, "Connected successfully"
        except httpx.HTTPStatusError as exc:
            return False, f"HTTP {exc.response.status_code}: {exc.response.text[:200]}"
        except Exception as exc:
            return False, str(exc)

    async def search(self, query: str, categories: str = "5070,5080") -> list[NewznabRelease]:
        """Search the indexer for *query*. Returns parsed releases.

        Raises NewznabError if the indexer returns an API-level error.
        Raises httpx.HTTPStatusError on non-2xx HTTP responses.
        """
        params = {
            "t": "search",
            "q": query,
            "apikey": self.api_key,
            "cat": categories,
            "o": "xml",
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{self.base_url}/api", params=params)
            response.raise_for_status()

        return parse_search_response(response.content, indexer_name=self.name)


# ---------------------------------------------------------------------------
# Parsing — public so callers can unit-test without HTTP
# ---------------------------------------------------------------------------


def parse_search_response(xml_bytes: bytes, indexer_name: str) -> list[NewznabRelease]:
    """Parse a Newznab XML search response into a list of NewznabRelease objects."""
    try:
        root = etree.fromstring(xml_bytes)
    except etree.XMLSyntaxError as exc:
        raise ValueError(f"Invalid XML from indexer: {exc}") from exc

    # Top-level <error code="..." description="..."/> (no channel wrapper)
    _check_error(root)

    channel = root.find("channel")
    if channel is None:
        return []

    # Some indexers nest the error inside <channel>
    _check_error(channel)

    releases: list[NewznabRelease] = []
    for item in channel.findall("item"):
        release = _parse_item(item, indexer_name)
        if release is not None:
            releases.append(release)

    logger.debug("Parsed %d releases from %s", len(releases), indexer_name)
    return releases


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _check_error(el: etree._Element) -> None:
    target = el if el.tag == "error" else el.find("error")
    if target is None:
        return
    code = int(target.get("code", 0))
    description = target.get("description", "Unknown error")
    raise NewznabError(code, description)


def _parse_item(item: etree._Element, indexer_name: str) -> NewznabRelease | None:
    title_el = item.find("title")
    if title_el is None or not title_el.text:
        return None

    enclosure = item.find("enclosure")
    if enclosure is None:
        return None
    nzb_url = enclosure.get("url")
    if not nzb_url:
        return None

    pub_date: str | None = None
    pd_el = item.find("pubDate")
    if pd_el is not None and pd_el.text:
        pub_date = pd_el.text.strip()

    guid: str | None = None
    guid_el = item.find("guid")
    if guid_el is not None and guid_el.text:
        guid = guid_el.text.strip()

    return NewznabRelease(
        title=title_el.text.strip(),
        nzb_url=nzb_url,
        size_bytes=_parse_size(item, enclosure),
        indexer_name=indexer_name,
        pub_date=pub_date,
        guid=guid,
    )


def _parse_size(item: etree._Element, enclosure: etree._Element) -> int | None:
    """Size in bytes: prefer <newznab:attr name="size">, fall back to enclosure length."""
    for attr in item.findall(f"{{{_NEWZNAB_NS}}}attr"):
        if attr.get("name") == "size":
            try:
                val = int(attr.get("value", 0))
                if val > 0:
                    return val
            except (ValueError, TypeError):
                pass
            break

    length = enclosure.get("length")
    if length:
        try:
            val = int(length)
            if val > 0:
                return val
        except (ValueError, TypeError):
            pass

    return None
