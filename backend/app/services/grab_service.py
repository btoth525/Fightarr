"""Grab service — routes a release to the right download client.

NZB releases go to SAB / NZBGet. Torrent releases go to qBit / Deluge /
Transmission / Real-Debrid. Within each protocol, the highest-priority enabled
client wins (matches Radarr/Sonarr behavior).

Used by both the manual /event/{id}/grab endpoint and the auto-search loop.
"""

from __future__ import annotations

import logging

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.download_client import DownloadClient, DownloadClientType
from app.models.queue_item import QueueItem, QueueStatus
from app.services.download_clients.factory import build_client

logger = logging.getLogger(__name__)

NZB_TYPES: tuple[DownloadClientType, ...] = (
    DownloadClientType.SABNZBD,
    DownloadClientType.NZBGET,
)
TORRENT_TYPES: tuple[DownloadClientType, ...] = (
    DownloadClientType.QBITTORRENT,
    DownloadClientType.DELUGE,
    DownloadClientType.TRANSMISSION,
    DownloadClientType.REAL_DEBRID,
)


class NoClientError(Exception):
    """No enabled download client matches the release protocol."""


class AlreadyQueuedError(Exception):
    """An active QueueItem already exists for this release."""


async def grab_release(
    *,
    event_id: int,
    nzb_url: str,
    release_title: str,
    size_bytes: int | None,
    indexer_name: str | None,
    protocol: str = "nzb",
) -> dict:
    """Route a release to the right download client and persist a QueueItem.

    Returns: {"status", "job_id", "download_client", "queue_item_id"}
    Raises NoClientError if no matching client is configured/enabled.
    Raises AlreadyQueuedError if an active QueueItem already exists for this release.
    """
    allowed_types = TORRENT_TYPES if protocol == "torrent" else NZB_TYPES

    async with AsyncSessionLocal() as session:
        # Skip if we already have an active grab for this exact release
        existing = await session.execute(
            select(QueueItem)
            .where(QueueItem.event_id == event_id)
            .where(QueueItem.release_title == release_title)
            .where(QueueItem.status.in_([QueueStatus.GRABBED, QueueStatus.DOWNLOADING]))
        )
        if existing.scalar_one_or_none() is not None:
            raise AlreadyQueuedError(f"Already queued: {release_title}")

        result = await session.execute(
            select(DownloadClient)
            .where(DownloadClient.enabled.is_(True))
            .where(DownloadClient.client_type.in_(allowed_types))
            .order_by(DownloadClient.priority)
        )
        dc = result.scalar_one_or_none()
        if dc is None:
            raise NoClientError(
                f"No enabled {protocol} download client configured. "
                f"Add one in Settings → Download Clients."
            )

        client = build_client(dc)
        try:
            job_id = await client.add_download(nzb_url, release_title, dc.category)
        except Exception as exc:
            raise RuntimeError(f"Download client error ({dc.name}): {exc}") from exc

        qi = QueueItem(
            event_id=event_id,
            release_title=release_title,
            release_size_bytes=size_bytes,
            indexer_name=indexer_name,
            nzb_url=nzb_url,
            download_client_id=dc.id,
            sabnzbd_nzo_id=job_id,
            status=QueueStatus.GRABBED,
        )
        session.add(qi)
        await session.commit()
        await session.refresh(qi)

        logger.info(
            "Grabbed %r → %s (job %s, queue item %d)",
            release_title,
            dc.name,
            job_id,
            qi.id,
        )

        # Fire grab notification (Discord/webhook). Best-effort; don't fail the grab.
        try:
            from app.models.event import Event
            from app.services import notifications

            event = await session.get(Event, event_id)
            if event is not None:
                await notifications.on_grab(event, release_title, indexer_name, dc.name)
        except Exception as exc:
            logger.debug("Grab notification skipped: %s", exc)

        return {
            "status": "grabbed",
            "job_id": job_id,
            "download_client": dc.name,
            "queue_item_id": qi.id,
        }


async def auto_search_and_grab(event_id: int) -> dict | None:
    """Search all indexers for an event, score releases, grab the best one.

    Mirrors Radarr's "Search on add" / "Search on monitor" behavior. Returns
    the grab result dict, or None if nothing was grabbed (no releases / no
    release above min score / already queued).
    """
    from app.services.indexer_search import search_event
    from app.services.release_scorer import pick_best_release

    logger.info("Auto-search starting for event %d", event_id)

    try:
        result = await search_event(event_id)
    except Exception as exc:
        logger.warning("Auto-search: search_event failed for %d: %s", event_id, exc)
        return None

    releases = result.get("releases", [])
    if not releases:
        logger.info("Auto-search: 0 releases for event %d", event_id)
        return None

    # Filter out anything currently blocklisted (failed downloads we won't retry)
    from app.services import blocklist_service

    async with AsyncSessionLocal() as s:
        blocked_titles, blocked_urls = await blocklist_service.get_blocked_keys(s)
    before = len(releases)
    releases = blocklist_service.filter_releases(releases, blocked_titles, blocked_urls)
    if before != len(releases):
        logger.info(
            "Auto-search: filtered %d blocklisted release(s) for event %d",
            before - len(releases),
            event_id,
        )

    best = pick_best_release(releases, min_score=50)
    if best is None:
        logger.info(
            "Auto-search: no release above min score for event %d (%d candidates after blocklist)",
            event_id,
            len(releases),
        )
        return None

    try:
        return await grab_release(
            event_id=event_id,
            nzb_url=best["nzb_url"],
            release_title=best["title"],
            size_bytes=best.get("size_bytes"),
            indexer_name=best.get("indexer_name"),
            protocol=best.get("protocol", "nzb"),
        )
    except AlreadyQueuedError as exc:
        logger.info("Auto-search: %s", exc)
        return None
    except NoClientError as exc:
        logger.warning("Auto-search: %s", exc)
        return None
    except Exception as exc:
        logger.error("Auto-search: grab failed for event %d: %s", event_id, exc)
        return None
