"""qBittorrent Web API download client.

API reference: https://github.com/qbittorrent/qBittorrent/wiki/WebUI-API-(qBittorrent-4.1)

Authentication:
  POST {host}/api/v2/auth/login  — form: username, password
  Returns "Ok." and sets SID cookie on success.

Relevant endpoints:
  POST /api/v2/torrents/add      — add by URL or magnet
       Form fields: urls (newline-separated), category, savepath, paused
       Returns "Ok." on success
  GET  /api/v2/torrents/info     — list queue, filter by category
  POST /api/v2/auth/logout       — end session
  GET  /api/v2/app/version       — connectivity test
"""

from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)


class QBittorrentClient:
    def __init__(self, host: str, username: str, password: str, category: str = "ufc") -> None:
        self.host = host.rstrip("/")
        self.username = username
        self.password = password
        self.category = category

    async def add_download(self, url: str, name: str, category: str = "ufc") -> str:
        async with httpx.AsyncClient(timeout=15.0) as client:
            await self._login(client)
            r = await client.post(
                f"{self.host}/api/v2/torrents/add",
                data={
                    "urls": url,
                    "category": category or self.category,
                    "rename": name,
                },
            )
            r.raise_for_status()
            if r.text.strip() != "Ok.":
                raise RuntimeError(f"qBittorrent rejected torrent: {r.text}")

        # qBittorrent doesn't return a torrent hash on add-by-URL synchronously.
        # Callers should poll get_queue() and match by name.
        return name

    async def get_queue(self) -> list[dict]:
        async with httpx.AsyncClient(timeout=15.0) as client:
            await self._login(client)
            r = await client.get(
                f"{self.host}/api/v2/torrents/info",
                params={"category": self.category, "filter": "all"},
            )
            r.raise_for_status()
            torrents = r.json()

        result = []
        for t in torrents:
            status = _qbit_status(t["state"])
            entry: dict = {
                "id": t["hash"],
                "name": t["name"],
                "status": status,
                "progress": round(t.get("progress", 0) * 100, 1),
                "size_bytes": t.get("size", 0),
            }
            if status == "completed" and t.get("save_path"):
                entry["download_path"] = t["save_path"]
            result.append(entry)
        return result

    async def test_connection(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                await self._login(client)
                r = await client.get(f"{self.host}/api/v2/app/version")
                r.raise_for_status()
            return True
        except Exception as exc:
            logger.debug("qBittorrent connection test failed: %s", exc)
            return False

    async def _login(self, client: httpx.AsyncClient) -> None:
        r = await client.post(
            f"{self.host}/api/v2/auth/login",
            data={"username": self.username, "password": self.password},
        )
        r.raise_for_status()
        if r.text.strip() not in ("Ok.", ""):
            raise RuntimeError(f"qBittorrent login failed: {r.text}")


def _qbit_status(state: str) -> str:
    downloading = {"downloading", "stalledDL", "checkingDL", "forcedDL", "metaDL"}
    completed = {"uploading", "stalledUP", "checkingUP", "forcedUP", "pausedUP"}
    if state in downloading:
        return "downloading"
    if state in completed:
        return "completed"
    if state == "error":
        return "failed"
    return "paused"
