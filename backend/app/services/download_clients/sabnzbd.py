"""SABnzbd download client.

API reference: https://sabnzbd.org/wiki/advanced/api

All calls: GET {host}/api?output=json&apikey={key}&mode={mode}

Relevant modes:
  addurl   — add NZB by URL:  &name={url}&cat={cat}&nzbname={name}
             Returns: {"status": true, "nzo_ids": ["SABnzbd_nzo_xyz"]}
  queue    — current queue:   &start=0&limit=100
  history  — completed items: &start=0&limit=100
  version  — connectivity test
"""

from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)


class SABnzbdClient:
    def __init__(self, host: str, api_key: str, category: str = "ufc") -> None:
        self.host = host.rstrip("/")
        self.api_key = api_key
        self.category = category

    async def add_download(self, url: str, name: str, category: str = "ufc") -> str:
        params = {
            "output": "json",
            "apikey": self.api_key,
            "mode": "addurl",
            "name": url,
            "nzbname": name,
            "cat": category or self.category,
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(f"{self.host}/api", params=params)
            r.raise_for_status()
            data = r.json()

        if not data.get("status"):
            raise RuntimeError(f"SABnzbd rejected download: {data}")

        nzo_ids: list[str] = data.get("nzo_ids", [])
        if not nzo_ids:
            logger.warning(
                "SABnzbd did not return a nzo_id for %r — Fightarr won't be able to "
                "track this download. Check SABnzbd logs and ensure the category exists.",
                name,
            )
        return nzo_ids[0] if nzo_ids else ""

    async def get_queue(self) -> list[dict]:
        params = {
            "output": "json",
            "apikey": self.api_key,
            "mode": "queue",
            "start": 0,
            "limit": 100,
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(f"{self.host}/api", params=params)
            r.raise_for_status()
            data = r.json()

        slots = data.get("queue", {}).get("slots", [])
        return [
            {
                "id": s["nzo_id"],
                "name": s["filename"],
                "status": s["status"].lower(),
                "progress": float(s.get("percentage", 0)),
                "size_bytes": _parse_size(s.get("mb", "0")),
            }
            for s in slots
        ]

    async def get_history(self, job_id: str) -> dict | None:
        """Check SABnzbd history for a completed/failed job by nzo_id.

        Uses the nzo_ids query parameter to fetch only the specific job rather
        than scanning a page of history. This avoids the "scroll off" problem
        where a job disappears from a capped history list before Fightarr sees it.
        Falls back to a paginated scan if the targeted lookup returns nothing.
        """
        slot = await self._history_by_id(job_id) or await self._history_scan(job_id)
        if slot is None:
            return None

        raw_status = slot.get("status", "").lower()
        # SABnzbd post-processing runs through several transient states
        # (Extracting, Verifying, Moving, Running) before settling on Completed
        # or Failed. Return None for transient states so the caller retries on
        # the next poll rather than falsely marking the download as failed.
        if raw_status == "completed":
            status = "completed"
        elif raw_status in ("failed", "bad"):
            status = "failed"
        else:
            return None

        return {
            "id": job_id,
            "name": slot.get("name", ""),
            "status": status,
            "progress": 100.0,
            "size_bytes": slot.get("bytes", 0),
            "download_path": slot.get("storage"),  # "storage" is the authoritative completed path
            "error": slot.get("fail_message") or None if status == "failed" else None,
        }

    async def _history_by_id(self, job_id: str) -> dict | None:
        """Targeted lookup: ask SABnzbd for exactly one nzo_id."""
        try:
            params = {
                "output": "json",
                "apikey": self.api_key,
                "mode": "history",
                "nzo_ids": job_id,
            }
            async with httpx.AsyncClient(timeout=15.0) as client:
                r = await client.get(f"{self.host}/api", params=params)
                r.raise_for_status()
                slots = r.json().get("history", {}).get("slots", [])
            return slots[0] if slots else None
        except Exception:
            return None

    async def _history_scan(self, job_id: str) -> dict | None:
        """Fallback: scan up to 500 history entries for the job_id."""
        try:
            params = {
                "output": "json",
                "apikey": self.api_key,
                "mode": "history",
                "start": 0,
                "limit": 500,
            }
            async with httpx.AsyncClient(timeout=15.0) as client:
                r = await client.get(f"{self.host}/api", params=params)
                r.raise_for_status()
                slots = r.json().get("history", {}).get("slots", [])
            return next((s for s in slots if s.get("nzo_id") == job_id), None)
        except Exception:
            return None

    async def get_complete_dir(self) -> str | None:
        """Return SABnzbd's configured complete_dir (where finished downloads land).

        Used at download-client setup time to auto-create a path mapping so
        Fightarr knows how to reach files SAB has already finished.
        """
        try:
            params = {
                "output": "json",
                "apikey": self.api_key,
                "mode": "get_config",
                "section": "misc",
                "keyword": "complete_dir",
            }
            async with httpx.AsyncClient(timeout=8.0) as client:
                r = await client.get(f"{self.host}/api", params=params)
                r.raise_for_status()
                data = r.json()
            return data.get("config", {}).get("misc", {}).get("complete_dir")
        except Exception as exc:
            logger.debug("Could not fetch SABnzbd complete_dir: %s", exc)
            return None

    async def test_connection(self) -> bool:
        try:
            params = {"output": "json", "apikey": self.api_key, "mode": "version"}
            async with httpx.AsyncClient(timeout=8.0) as client:
                r = await client.get(f"{self.host}/api", params=params)
                r.raise_for_status()
            return True
        except Exception as exc:
            logger.debug("SABnzbd connection test failed: %s", exc)
            return False


def _parse_size(mb_str: str) -> int:
    try:
        return int(float(mb_str) * 1024 * 1024)
    except (ValueError, TypeError):
        return 0
