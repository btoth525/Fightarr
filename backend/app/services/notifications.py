"""Notification dispatch — Discord/Slack/generic webhooks.

Settings holds a webhook_url and a comma-separated list of enabled events:
  grab    — fired when a release is sent to a download client
  import  — fired when a download is renamed/moved to the library
  failed  — fired when a download fails or is blocklisted
  health  — fired when an indexer or download client goes unreachable

Discord webhooks accept a flexible JSON shape; we use the embeds format which
also renders correctly on Slack-compatible endpoints. ntfy/Apprise/etc. can be
added later as alternative dispatchers — same trigger surface.
"""

from __future__ import annotations

import logging

import httpx

from app.models.event import Event

logger = logging.getLogger(__name__)

# Discord embed colors (decimal RGB)
COLOR_ACCENT = 0xE8820C  # UFC orange
COLOR_GREEN = 0x4ADE80
COLOR_RED = 0xEF4444
COLOR_AMBER = 0xF59E0B


async def _send(webhook_url: str, embed: dict) -> None:
    """POST a Discord-shaped embed payload to webhook_url."""
    if not webhook_url:
        return
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(
                webhook_url,
                json={"embeds": [embed]},
                headers={"User-Agent": "Fightarr/0.1.0"},
            )
            r.raise_for_status()
    except Exception as exc:
        logger.warning("Webhook delivery failed: %s", exc)


def _is_enabled(events_csv: str, event: str) -> bool:
    enabled = {x.strip().lower() for x in (events_csv or "").split(",") if x.strip()}
    return event in enabled


async def on_grab(
    event: Event, release_title: str, indexer: str | None, download_client: str | None
) -> None:
    from app.services.settings_service import load_settings

    s = await load_settings()
    if not s.webhook_url or not _is_enabled(s.webhook_events, "grab"):
        return

    fields = [
        {"name": "Indexer", "value": indexer or "—", "inline": True},
        {"name": "Client", "value": download_client or "—", "inline": True},
    ]
    await _send(
        s.webhook_url,
        {
            "title": f"Grabbed: {event.title}",
            "description": f"`{release_title}`",
            "color": COLOR_ACCENT,
            "fields": fields,
        },
    )


async def on_import(event: Event, file_path: str, quality: str | None) -> None:
    from app.services.settings_service import load_settings

    s = await load_settings()
    if not s.webhook_url or not _is_enabled(s.webhook_events, "import"):
        return

    await _send(
        s.webhook_url,
        {
            "title": f"Imported: {event.title}",
            "description": f"`{file_path}`",
            "color": COLOR_GREEN,
            "fields": [{"name": "Quality", "value": quality or "Unknown", "inline": True}],
        },
    )


async def on_failed(event: Event, release_title: str, reason: str) -> None:
    from app.services.settings_service import load_settings

    s = await load_settings()
    if not s.webhook_url or not _is_enabled(s.webhook_events, "failed"):
        return

    await _send(
        s.webhook_url,
        {
            "title": f"Download failed: {event.title}",
            "description": f"`{release_title}`",
            "color": COLOR_RED,
            "fields": [{"name": "Reason", "value": reason[:1000], "inline": False}],
        },
    )


async def on_health(failures: list[dict]) -> None:
    from app.services.settings_service import load_settings

    s = await load_settings()
    if not s.webhook_url or not _is_enabled(s.webhook_events, "health"):
        return

    fields = [
        {"name": f["name"], "value": f"{f['kind']}: {f['message'][:200]}", "inline": False}
        for f in failures[:10]
    ]
    await _send(
        s.webhook_url,
        {
            "title": "Health check found problems",
            "color": COLOR_AMBER,
            "fields": fields,
        },
    )


async def test_webhook(url: str) -> tuple[bool, str]:
    """User-triggered test — sends a single embed and reports the outcome."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(
                url,
                json={
                    "embeds": [
                        {
                            "title": "Fightarr — test notification",
                            "description": "If you're seeing this, your webhook is wired up correctly.",
                            "color": COLOR_ACCENT,
                        }
                    ]
                },
                headers={"User-Agent": "Fightarr/0.1.0"},
            )
            r.raise_for_status()
        return True, "Test message delivered"
    except httpx.HTTPStatusError as exc:
        return False, f"HTTP {exc.response.status_code}: {exc.response.text[:200]}"
    except Exception as exc:
        return False, str(exc)
