"""Transmission RPC download client.

API reference: https://github.com/transmission/transmission/blob/main/docs/rpc-spec.md

Transmission uses JSON-RPC over HTTP with a CSRF token header:
  POST {host}/transmission/rpc
  Headers: X-Transmission-Session-Id: <token>
  Body: {"method": "...", "arguments": {...}}

The session token is obtained by making a request and reading the
X-Transmission-Session-Id header from the 409 response. Clients must
retry with the token; this is a simple CSRF protection mechanism.

Relevant methods:
  torrent-add      — add by URL or magnet:
                     arguments: {filename: url, download-dir: path,
                                 labels: [category], paused: false}
                     Returns: {torrent-added: {id, name, hashString}}
  torrent-get      — list torrents:
                     arguments: {fields: [id, name, status, percentDone,
                                          totalSize, hashString]}
  session-get      — connectivity test
"""

from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)

_STATUS_MAP = {
    0: "paused",
    1: "paused",
    2: "paused",
    3: "downloading",
    4: "downloading",
    5: "downloading",
    6: "completed",
}


class TransmissionClient:
    def __init__(
        self,
        host: str,
        username: str | None = None,
        password: str | None = None,
        category: str = "ufc",
    ) -> None:
        self.host = host.rstrip("/")
        self.username = username
        self.password = password
        self.category = category
        self._session_id: str = ""

    async def add_download(self, url: str, name: str, category: str = "ufc") -> str:
        result = await self._rpc(
            "torrent-add",
            {"filename": url, "labels": [category or self.category], "paused": False},
        )
        torrent = result.get("torrent-added") or result.get("torrent-duplicate", {})
        return torrent.get("hashString", name)

    async def get_queue(self) -> list[dict]:
        result = await self._rpc(
            "torrent-get",
            {
                "fields": [
                    "id", "name", "status", "percentDone",
                    "totalSize", "hashString", "downloadDir",
                ]
            },
        )
        entries = []
        for t in result.get("torrents", []):
            status = _STATUS_MAP.get(t["status"], "downloading")
            entry: dict = {
                "id": t["hashString"],
                "name": t["name"],
                "status": status,
                "progress": round(t.get("percentDone", 0) * 100, 1),
                "size_bytes": t.get("totalSize", 0),
            }
            if status == "completed" and t.get("downloadDir"):
                entry["download_path"] = t["downloadDir"]
            entries.append(entry)
        return entries

    async def test_connection(self) -> bool:
        try:
            await self._rpc("session-get", {})
            return True
        except Exception as exc:
            logger.debug("Transmission connection test failed: %s", exc)
            return False

    async def _rpc(self, method: str, arguments: dict) -> dict:
        auth = (self.username, self.password) if self.username else None
        payload = {"method": method, "arguments": arguments}

        async with httpx.AsyncClient(timeout=15.0) as client:
            for attempt in range(2):
                headers = {"X-Transmission-Session-Id": self._session_id}
                r = await client.post(
                    f"{self.host}/transmission/rpc",
                    json=payload,
                    headers=headers,
                    auth=auth,
                )
                if r.status_code == 409:
                    self._session_id = r.headers.get("X-Transmission-Session-Id", "")
                    if attempt == 0:
                        continue
                r.raise_for_status()
                body = r.json()
                if body.get("result") != "success":
                    raise RuntimeError(f"Transmission RPC error: {body.get('result')}")
                return body.get("arguments", {})
        return {}
