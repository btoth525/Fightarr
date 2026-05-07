"""Release scorer — Radarr-style scoring for picking the best release.

Higher score = better release. The auto-search-and-grab loop picks the highest
scored release above a minimum threshold and sends it to the matching download
client (NZB clients for NZB releases, torrent clients for torrent releases).

Scoring components:
  - Resolution: 2160p > 1080p > 720p > 480p
  - Source:     WEBDL > Bluray > WEBRip > HDTV
  - Codec:      HEVC/x265 small bonus
  - Penalties:  Prelims, Sample, obfuscated names, unreasonable file size
  - Bonus:      Reasonable file size matches expected quality
"""

from __future__ import annotations

import re

# Score weights — calibrated so any 1080p WEB-DL beats any 720p variant
RES_SCORE = {
    "2160p": 200,
    "1080p": 100,
    "720p": 50,
    "480p": 10,
}

SOURCE_SCORE = {
    "WEBDL": 30,  # WEB-DL = direct-from-source, best for streaming sports
    "Bluray": 25,  # rare for UFC, but high quality when available
    "WEBRip": 20,  # re-encoded from web, slightly worse than WEB-DL
    "HDTV": 5,  # broadcast capture, often has banners/commercials
}


def score_release(release: dict) -> int:
    """Score a release dict. Higher = better. Returns int score."""
    title = release.get("title", "").upper()
    score = 0

    # --- Resolution -------------------------------------------------------
    if "2160P" in title or "4K" in title or "UHD" in title:
        score += RES_SCORE["2160p"]
    elif "1080P" in title:
        score += RES_SCORE["1080p"]
    elif "720P" in title:
        score += RES_SCORE["720p"]
    elif "480P" in title:
        score += RES_SCORE["480p"]

    # --- Source -----------------------------------------------------------
    if "WEB-DL" in title or "WEBDL" in title or "WEB DL" in title:
        score += SOURCE_SCORE["WEBDL"]
    elif "BLURAY" in title or "BLU-RAY" in title:
        score += SOURCE_SCORE["Bluray"]
    elif "WEBRIP" in title or "WEB-RIP" in title:
        score += SOURCE_SCORE["WEBRip"]
    elif "HDTV" in title:
        score += SOURCE_SCORE["HDTV"]

    # --- Codec ------------------------------------------------------------
    if "X265" in title or "H265" in title or "HEVC" in title:
        score += 5  # better compression at same quality

    # --- Penalties --------------------------------------------------------
    if re.search(r"\bPRELIM", title):
        # Prelims are valuable but the main card is what we want by default;
        # heavy penalty makes sure a 720p main-card beats a 4K prelims pack.
        score -= 150
    if re.search(r"\bSAMPLE\b", title):
        score -= 1000
    # Obfuscated release names (random hashes instead of words)
    if re.search(r"^[a-f0-9]{20,}\b", title, re.IGNORECASE):
        score -= 50

    # --- File size sanity -------------------------------------------------
    size_bytes = release.get("size_bytes") or 0
    size_gb = size_bytes / (1024**3)
    if size_gb <= 0:
        # No size info — neutral (some indexers don't report)
        pass
    elif size_gb < 0.5:
        score -= 100  # too small, almost certainly not a full event
    elif size_gb > 50:
        score -= 30  # unreasonably large
    else:
        # Modest bonus for reasonable size; caps so a 30GB file doesn't
        # outrank a 4K release with smaller bitrate
        score += min(int(size_gb), 15)

    return score


def pick_best_release(releases: list[dict], min_score: int = 50) -> dict | None:
    """Pick the highest scored release above min_score, or None."""
    if not releases:
        return None
    scored = [(r, score_release(r)) for r in releases]
    scored.sort(key=lambda x: x[1], reverse=True)
    best, best_score = scored[0]
    if best_score < min_score:
        return None
    return best
