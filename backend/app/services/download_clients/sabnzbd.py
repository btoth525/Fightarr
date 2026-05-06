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
