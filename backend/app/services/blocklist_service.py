"""Blocklist helpers — used by grab_service and queue_monitor."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.blocklist import BlocklistEntry

logger = logging.getLogger(__name__)


async def add(
    *,
    event_id: int | None,
    release_title: str,
    nzb_url: str | None,
    indexer_name: str | None,
    reason: str | None,
) -> None:
    """Add a release to the blocklist (idempotent on title)."""
    async with AsyncSessionLocal() as session:
        existing = await session.execute(
            select(BlocklistEntry).where(BlocklistEntry.release_title == release_title)
        )
        if existing.scalar_one_or_none() is not None:
            return

        entry = BlocklistEntry(
            event_id=event_id,
            release_title=release_title,
            nzb_url=nzb_url,
            indexer_name=indexer_name,
            reason=reason,
        )
        session.add(entry)
        await session.commit()
        logger.info("Blocklisted %r — %s", release_title, reason)


async def get_blocked_keys(session: AsyncSession) -> tuple[set[str], set[str]]:
    """Return (titles, urls) currently blocklisted. Used to filter releases pre-grab."""
    result = await session.execute(select(BlocklistEntry.release_title, BlocklistEntry.nzb_url))
    titles: set[str] = set()
    urls: set[str] = set()
    for title, url in result.all():
        if title:
            titles.add(title.lower())
        if url:
            urls.add(url)
    return titles, urls


def filter_releases(
    releases: list[dict], blocked_titles: set[str], blocked_urls: set[str]
) -> list[dict]:
    """Drop any release that matches a blocklist entry by title or URL."""
    out: list[dict] = []
    for r in releases:
        title = (r.get("title") or "").lower()
        url = r.get("nzb_url") or ""
        if title in blocked_titles or url in blocked_urls:
            continue
        out.append(r)
    return out
