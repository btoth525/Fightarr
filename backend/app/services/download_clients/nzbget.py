"""NZBGet download client.

API reference: https://nzbget.net/api

NZBGet uses JSON-RPC over HTTP:
  POST {host}/jsonrpc
  Body: {"method": "...", "params": [...], "id": 1}

Relevant methods:
  version            — connectivity test, returns version string
  append             — add NZB:
                       params: [NZBFilename, Content(b64), Category, Priority,
                                AddToTop, AddPaused, DupeKey, DupeScore, DupeMode,
                                PPParameters]
                       Returns NZBId (int) or 0 on failure
  listgroups         — current queue (returns array of group objects)
  history            — completed/failed items
"""

from __future__ import annotations

import base64
import logging

import httpx

logger = logging.getLogger(__name__)


class NZBGetClient:
    def __init__(self, host: str, username: str, password: str, category: str = "ufc") -> None:
        self.host = host.rstrip("/")
        self.username = username
        self.password = password
        self.category = category

    async def add_download(self, url: str, name: str, category: str = "ufc") -> str:
        # NZBGet's append method requires the NZB file content as base64.
        # We first fetch the NZB file, then post it to NZBGet.
        async with httpx.AsyncClient(timeout=30.0) as client:
            nzb_resp = await client.get(url)
            nzb_resp.raise_for_status()
            nzb_b64 = base64.b64encode(nzb_resp.content).decode()

        result = await self._rpc(
            "append",
            [
                f"{name}.nzb",  # NZBFilename
                nzb_b64,  # Content (base64)
                category or self.category,  # Category
                0,  # Priority (0 = normal)
                False,  # AddToTop
                False,  # AddPaused
                "",  # DupeKey
                0,  # DupeScore
                "SCORE",  # DupeMode
                [],  # PPParameters
            ],
        )
        nzb_id = result if isinstance(result, int) else 0
        if nzb_id == 0:
            raise RuntimeError(f"NZBGet rejected download: {name}")
        return str(nzb_id)

    async def get_queue(self) -> list[dict]:
        groups = await self._rpc("listgroups", [0])
        return [
            {
                "id": str(g["NZBID"]),
                "name": g["NZBName"],
                "status": g["Status"].lower(),
                "progress": _nzbget_progress(g),
                "size_bytes": g.get("FileSizeMB", 0) * 1024 * 1024,
            }
            for g in (groups or [])
        ]

    async def get_history(self, job_id: str) -> dict | None:
        """Check NZBGet history for a completed/failed job by NZBID."""
        history = await self._rpc("history", [False])
        for item in history or []:
            if str(item.get("NZBID")) == str(job_id):
                raw_status = item.get("Status", "").upper()
                if raw_status.startswith("SUCCESS"):
                    status = "completed"
                elif raw_status.startswith(("FAILURE", "DELETED")):
                    status = "failed"
                else:
                    continue
                messages = item.get("MessageList", [])
                err = messages[-1].get("Text") if messages and status == "failed" else None
                return {
                    "id": job_id,
                    "name": item.get("NZBName", ""),
                    "status": status,
                    "progress": 100.0,
                    "size_bytes": item.get("FileSizeMB", 0) * 1024 * 1024,
                    "download_path": item.get("DestDir"),
                    "error": err,
                }
        return None

    async def test_connection(self) -> bool:
        try:
            await self._rpc("version", [])
            return True
        except Exception as exc:
            logger.debug("NZBGet connection test failed: %s", exc)
            return False

    async def _rpc(self, method: str, params: list) -> object:
        payload = {"method": method, "params": params, "id": 1}
        async with httpx.AsyncClient(auth=(self.username, self.password), timeout=15.0) as client:
            r = await client.post(f"{self.host}/jsonrpc", json=payload)
            r.raise_for_status()
            body = r.json()

        if body.get("error"):
            raise RuntimeError(f"NZBGet RPC error: {body['error']}")
        return body.get("result")


def _nzbget_progress(group: dict) -> float:
    total = group.get("FileSizeMB", 0)
    remaining = group.get("RemainingSizeMB", total)
    if total <= 0:
        return 0.0
    return round((1 - remaining / total) * 100, 1)
