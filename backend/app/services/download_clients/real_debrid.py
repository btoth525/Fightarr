"""Real-Debrid premium download client.

API reference: https://api.real-debrid.com

Real-Debrid is a premium link hoster / torrent debrid service. It downloads
torrents on its own servers and makes them available as direct HTTP links via
its premium infrastructure. This is popular in the *arr community as an
alternative to maintaining a seedbox.

Auth: Bearer token in Authorization header.
Base URL: https://api.real-debrid.com/rest/1.0

Flow for torrents/magnets:
  1. POST /torrents/addMagnet   {magnet: <link>}
       → returns {id: "RD_ID", uri: "..."}
  2. POST /torrents/selectFiles/{id}  {files: "all"}
       → activates download on RD servers
  3. GET  /torrents/info/{id}
       → poll until status == "downloaded", then read .links[]
  4. POST /unrestrict/link  {link: <direct_link>}
       → returns {download: <final_https_url>}  ← push this to a HTTP downloader

Flow for NZBs (Real-Debrid has limited Usenet support via premium servers):
  POST /downloads/add  {link: <nzb_url>}
  → limited availability; not all indexer links are supported.

For magnet-only (no torrent file) the flow skips step 4 as the link from
step 3 is already a direct download URL in most cases.
"""

from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)

_RD_BASE = "https://api.real-debrid.com/rest/1.0"


class RealDebridClient:
    def __init__(self, api_key: str, category: str = "ufc") -> None:
        self.api_key = api_key
        self.category = category  # unused by RD, kept for interface parity

    async def add_download(self, url: str, name: str, category: str = "ufc") -> str:
        """Add a magnet link or torrent URL to Real-Debrid.

        Returns the Real-Debrid torrent ID (used to poll status).
        For plain HTTP NZB/torrent file URLs, fetches the file first and
        posts it as a torrent upload; falls back to addMagnet for magnets.
        """
        if url.startswith("magnet:"):
            return await self._add_magnet(url)
        return await self._add_torrent_url(url)

    async def get_queue(self) -> list[dict]:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(
                f"{_RD_BASE}/torrents",
                headers=self._auth(),
                params={"limit": 100},
            )
            r.raise_for_status()
            torrents = r.json()

        return [
            {
                "id": t["id"],
                "name": t.get("filename", t["id"]),
                "status": _rd_status(t.get("status", "")),
                "progress": float(t.get("progress", 0)),
                "size_bytes": t.get("bytes", 0),
            }
            for t in torrents
        ]

    async def get_history(self, job_id: str) -> dict | None:
        """Check Real-Debrid torrent info for a specific job_id."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(
                    f"{_RD_BASE}/torrents/info/{job_id}", headers=self._auth()
                )
                if r.status_code == 404:
                    return None
                r.raise_for_status()
                t = r.json()
            status = _rd_status(t.get("status", ""))
            if status not in ("completed", "failed"):
                return None
            return {
                "id": job_id,
                "name": t.get("filename", job_id),
                "status": status,
                "progress": float(t.get("progress", 100)),
                "size_bytes": t.get("bytes", 0),
                "download_path": None,  # RD doesn't expose a local path
            }
        except Exception:
            return None

    async def test_connection(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                r = await client.get(f"{_RD_BASE}/user", headers=self._auth())
                r.raise_for_status()
            return True
        except Exception as exc:
            logger.debug("Real-Debrid connection test failed: %s", exc)
            return False

    async def unrestrict_link(self, link: str) -> str:
        """Convert a Real-Debrid hoster link to a direct download URL."""
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(
                f"{_RD_BASE}/unrestrict/link",
                headers=self._auth(),
                data={"link": link},
            )
            r.raise_for_status()
            return r.json()["download"]

    async def select_files(self, torrent_id: str) -> None:
        """Tell Real-Debrid to download all files for a queued torrent."""
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(
                f"{_RD_BASE}/torrents/selectFiles/{torrent_id}",
                headers=self._auth(),
                data={"files": "all"},
            )
            r.raise_for_status()

    # ------------------------------------------------------------------

    async def _add_magnet(self, magnet: str) -> str:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(
                f"{_RD_BASE}/torrents/addMagnet",
                headers=self._auth(),
                data={"magnet": magnet},
            )
            r.raise_for_status()
            torrent_id: str = r.json()["id"]

        await self.select_files(torrent_id)
        return torrent_id

    async def _add_torrent_url(self, url: str) -> str:
        async with httpx.AsyncClient(timeout=30.0) as client:
            torrent_resp = await client.get(url)
            torrent_resp.raise_for_status()
            r = await client.put(
                f"{_RD_BASE}/torrents/addTorrent",
                headers=self._auth(),
                content=torrent_resp.content,
            )
            r.raise_for_status()
            torrent_id: str = r.json()["id"]

        await self.select_files(torrent_id)
        return torrent_id

    def _auth(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"}


def _rd_status(status: str) -> str:
    downloading = {
        "magnet_conversion",
        "waiting_files_selection",
        "queued",
        "downloading",
        "compressing",
        "uploading",
    }
    if status in downloading:
        return "downloading"
    if status == "downloaded":
        return "completed"
    if status in ("error", "dead", "virus"):
        return "failed"
    return "paused"
