"""Download client protocol.

All concrete clients implement this interface. The grab pipeline calls
add_download() and get_queue() through this protocol so it doesn't need
to know which client is configured.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class DownloadClientProtocol(Protocol):
    async def add_download(self, url: str, name: str, category: str = "ufc") -> str:
        """Push a download URL (NZB URL, magnet, or torrent URL) to the client.

        Returns a client-specific download ID (nzo_id, torrent hash, etc.)
        that can be used to track progress via get_queue().
        """
        ...

    async def get_queue(self) -> list[dict]:
        """Return the current download queue.

        Each dict should contain at minimum:
            id: str          — client download ID
            name: str        — release name
            status: str      — downloading | completed | failed | paused
            progress: float  — 0.0 - 100.0
            size_bytes: int  — total size
        """
        ...

    async def test_connection(self) -> bool:
        """Verify the client is reachable and credentials are valid."""
        ...
