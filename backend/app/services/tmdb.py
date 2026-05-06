"""TMDB (The Movie Database) metadata client.

API reference: https://developer.themoviedb.org/reference/intro/getting-started

Auth: api_key query param (v3) or Authorization: Bearer <token> (v4).
Base URL: https://api.themoviedb.org/3

Image CDN: https://image.tmdb.org/t/p/{size}{poster_path}
Common sizes: w92, w154, w185, w342, w500, w780, original

Search strategy for UFC events:
  1. /search/multi?query={title}  — covers movies + TV in one call
  2. Pick first result that has a poster_path
  3. For numbered PPVs (UFC 300) a movie result is usually better;
     for Fight Nights the TV entry is more reliable.
"""

from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)

_TMDB_BASE = "https://api.themoviedb.org/3"
_IMAGE_BASE = "https://image.tmdb.org/t/p/w500"


async def fetch_event_poster(
    title: str,
    year: int | None,
    api_key: str,
) -> tuple[str | None, int | None]:
    """Search TMDB for a UFC event and return (poster_url, tmdb_id).

    Returns (None, None) if nothing found or api_key is empty.
    """
    if not api_key:
        return None, None

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
        # Fallback: strip subtitle (e.g. "UFC 300: Pereira vs Hill" → "UFC 300")
        short_title = title.split(":")[0].strip()
        if short_title != title:
            return await fetch_event_poster(short_title, year, api_key)
        return None, None

    # Prefer results with a poster; prefer movie over TV for numbered PPVs
    def _score(r: dict) -> int:
        has_poster = 1 if r.get("poster_path") else 0
        is_movie = 1 if r.get("media_type") == "movie" else 0
        return has_poster * 10 + is_movie

    best = max(results, key=_score)
    if not best.get("poster_path"):
        return None, None

    poster_url = f"{_IMAGE_BASE}{best['poster_path']}"
    tmdb_id: int = best["id"]
    return poster_url, tmdb_id


async def test_connection(api_key: str) -> bool:
    """Return True if the api_key can reach TMDB."""
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
