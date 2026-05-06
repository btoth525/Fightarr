"""Deluge JSON-RPC download client.

API reference: https://deluge.readthedocs.io/en/latest/reference/api.html

Deluge's Web UI uses JSON-RPC over HTTP:
  POST {host}/json
  Body: {"method": "...", "params": [...], "id": 1}

Authentication:
  POST /json  method=auth.login  params=[password]
  Returns true on success and sets a session cookie.

Relevant methods:
  web.add_torrents   — add by URL / magnet:
                       params: [[ {path: url, options: {add_paused: false,
                                                        label: category}} ]]
  core.get_torrents_status — list queue:
                       params: [{}, [keys...]]
  auth.check_session — connectivity test (returns true if authed)
  daemon.info        — version / reachability
"""

from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)

_STATE_MAP = {
    "Downloading": "downloading",
    "Seeding": "completed",
    "Queued": "paused",
    "Paused": "paused",
    "Error": "failed",
    "Checking": "downloading",
}


class DelugeClient:
    def __init__(self, host: str, password: str, category: str = "ufc") -> None:
        self.host = host.rstrip("/")
        self.password = password
        self.category = category

    async def add_download(self, url: str, name: str, category: str = "ufc") -> str:
        async with httpx.AsyncClient(timeout=15.0) as client:
            await self._login(client)
            result = await self._rpc(
                client,
                "web.add_torrents",
                [
                    [
                        {
                            "path": url,
                            "options": {"add_paused": False, "label": category or self.category},
                        }
                    ]
                ],
            )

        # web.add_torrents returns a list of [success, torrent_id] pairs
        if isinstance(result, list) and result:
            pair = result[0]
            if isinstance(pair, list) and len(pair) >= 2 and pair[0]:
                return pair[1]
        raise RuntimeError(f"Deluge rejected torrent: {result}")

    async def get_queue(self) -> list[dict]:
        async with httpx.AsyncClient(timeout=15.0) as client:
            await self._login(client)
            result = await self._rpc(
                client,
                "core.get_torrents_status",
                [{}, ["name", "state", "progress", "total_size"]],
            )

        return [
            {
                "id": torrent_id,
                "name": info.get("name", torrent_id),
                "status": _STATE_MAP.get(info.get("state", ""), "downloading"),
                "progress": round(info.get("progress", 0), 1),
                "size_bytes": info.get("total_size", 0),
            }
            for torrent_id, info in (result or {}).items()
        ]

    async def test_connection(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                await self._login(client)
            return True
        except Exception as exc:
            logger.debug("Deluge connection test failed: %s", exc)
            return False

    async def _login(self, client: httpx.AsyncClient) -> None:
        result = await self._rpc(client, "auth.login", [self.password])
        if not result:
            raise RuntimeError("Deluge authentication failed")

    async def _rpc(self, client: httpx.AsyncClient, method: str, params: list) -> object:
        payload = {"method": method, "params": params, "id": 1}
        r = await client.post(f"{self.host}/json", json=payload)
        r.raise_for_status()
        body = r.json()
        if body.get("error"):
            raise RuntimeError(f"Deluge RPC error: {body['error']}")
        return body.get("result")
