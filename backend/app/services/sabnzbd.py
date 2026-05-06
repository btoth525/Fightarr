"""SABnzbd HTTP API client.

SABnzbd's API is a single endpoint with a `mode` query param:
  GET {base}/api?mode=addurl&name={nzb_url}&cat={cat}&apikey={key}

Stub for now — flesh out in a follow-up PR.
"""

from __future__ import annotations


class SABnzbdClient:
    def __init__(self, base_url: str, api_key: str, default_category: str = "ufc"):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.default_category = default_category

    async def add_url(
        self, nzb_url: str, name: str | None = None, category: str | None = None
    ) -> str | None:
        """Push an NZB URL to SABnzbd. Returns the nzo_id on success.

        TODO: Implement with httpx. SAB returns JSON like:
            {"status": true, "nzo_ids": ["SABnzbd_nzo_xyz"]}
        """
        raise NotImplementedError("SABnzbd add_url not yet implemented")

    async def queue_status(self) -> dict:
        """Return current SAB queue (mode=queue). For sync to QueueItem table."""
        raise NotImplementedError("SABnzbd queue_status not yet implemented")
