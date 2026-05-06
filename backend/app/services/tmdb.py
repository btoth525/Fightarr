"""Event metadata and poster art service.

Poster sources (in priority order):

1. Wikipedia REST API — zero config, no API key.
   Each event's Wikipedia article (source_url already stored on the Event row)
   exposes a public summary endpoint that returns the article's main image.
   GET https://en.wikipedia.org/api/rest_v1/page/summary/{title}
   → .originalimage.source  (full-res)
   → .thumbnail.source       (fallback)

   This is how we ship cover art out of the box — exactly like Sonarr/Radarr
   ship TMDB art with a baked-in key, but requiring zero user configuration.

2. TMDB (optional) — set FIGHTARR_TMDB_API_KEY for official promo posters.
   Higher quality art for numbered PPVs but requires an API key.
   GET https://api.themoviedb.org/3/search/multi?query={title}&api_key={key}
   Image CDN: https://image.tmdb.org/t/p/w500{poster_path}
"""

from __future__ import annotations

import logging
from urllib.parse import unquote, urlparse

import httpx

logger = logging.getLogger(__name__)

_WIKI_REST = "https://en.wikipedia.org/api/rest_v1/page/summary"
_WIKI_UA = "Fightarr/1.0 (https://github.com/btoth525/Fightarr)"

_TMDB_BASE = "https://api.themoviedb.org/3"
_IMAGE_BASE = "https://image.tmdb.org/t/p/w500"


async def fetch_event_poster(
    title: str,
    year: int | None,
    api_key: str,
    source_url: str | None = None,
) -> tuple[str | None, int | None]:
    """Return (poster_url, tmdb_id) for a UFC event.

    Tries Wikipedia first (always), then TMDB if an api_key is set.
    tmdb_id is None for Wikipedia-sourced posters.
    """
    # 1. Wikipedia — free, no key
    if source_url:
        wiki_url = await _fetch_wikipedia_poster(source_url)
        if wiki_url:
            return wiki_url, None

    # 2. TMDB — optional key
    if api_key:
        return await _fetch_tmdb_poster(title, year, api_key)

    return None, None


async def _fetch_wikipedia_poster(source_url: str) -> str | None:
    """Extract the main image from a Wikipedia article via the REST summary API."""
    if not source_url or "wikipedia.org/wiki/" not in source_url:
        return None

    path = urlparse(source_url).path  # /wiki/UFC_300
    page_title = unquote(path.split("/wiki/", 1)[-1])  # UFC_300

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                f"{_WIKI_REST}/{page_title}",
                headers={"User-Agent": _WIKI_UA},
            )
            r.raise_for_status()
            data = r.json()
    except Exception as exc:
        logger.debug("Wikipedia image fetch failed for %s: %s", page_title, exc)
        return None

    img = data.get("originalimage") or data.get("thumbnail")
    return img.get("source") if img else None


async def _fetch_tmdb_poster(
    title: str,
    year: int | None,
    api_key: str,
) -> tuple[str | None, int | None]:
    """Search TMDB and return (poster_url, tmdb_id) or (None, None)."""
    params: dict[str, str | int] = {
        "api_key": api_key,
        "query": title,
        "include_adult": "false",
        "language": "en-US",
        "page": 1,
    }
    if year:
        params["year"] = year

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(f"{_TMDB_BASE}/search/multi", params=params)
            r.raise_for_status()
            results = r.json().get("results", [])
    except Exception as exc:
        logger.warning("TMDB search failed for %r: %s", title, exc)
        return None, None

    if not results:
        short = title.split(":")[0].strip()
        if short != title:
            return await _fetch_tmdb_poster(short, year, api_key)
        return None, None

    def _score(res: dict) -> int:
        return (1 if res.get("poster_path") else 0) * 10 + (
            1 if res.get("media_type") == "movie" else 0
        )

    best = max(results, key=_score)
    if not best.get("poster_path"):
        return None, None

    return f"{_IMAGE_BASE}{best['poster_path']}", int(best["id"])


async def test_connection(api_key: str) -> bool:
    """Return True if the TMDB api_key is valid (optional — Wikipedia never needs this)."""
    if not api_key:
        return False
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            r = await client.get(
                f"{_TMDB_BASE}/configuration",
                params={"api_key": api_key},
            )
            r.raise_for_status()
        return True
    except Exception as exc:
        logger.debug("TMDB connection test failed: %s", exc)
        return False
