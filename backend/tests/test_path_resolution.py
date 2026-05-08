"""Tests for auto-discovery path resolution in the importer."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services import importer


@pytest.fixture
def fake_mounts(tmp_path: Path):
    """Set up tmp_path/{downloads,data,media} to look like Fightarr container mounts.

    Patches importer._PROBE_ROOTS to point at the temp dirs so we don't depend
    on real filesystem layout.
    """
    downloads = tmp_path / "downloads"
    data = tmp_path / "data"
    media = tmp_path / "media"
    for d in (downloads, data, media):
        d.mkdir()

    with patch.object(
        importer,
        "_PROBE_ROOTS",
        (str(downloads), str(data), str(media)),
    ):
        yield {"downloads": downloads, "data": data, "media": media}


@pytest.mark.asyncio
async def test_auto_discover_finds_path_under_alternate_mount(fake_mounts):
    # SAB reports /data/complete/UFC 327 — but in our test, we made the file
    # exist under {downloads}/complete/UFC 327, mimicking a container that has
    # /downloads mounted at the same physical share SAB calls /data.
    job_folder = fake_mounts["downloads"] / "complete" / "UFC 327"
    job_folder.mkdir(parents=True)

    sab_reported = "/data/complete/UFC 327"

    result = await importer._auto_discover_path(sab_reported)
    assert result is not None
    resolved, remote_prefix, local_prefix = result

    assert resolved == str(job_folder)
    assert remote_prefix == "/data/"
    assert local_prefix == str(fake_mounts["downloads"]) + "/"


@pytest.mark.asyncio
async def test_auto_discover_returns_none_when_folder_missing(fake_mounts):
    result = await importer._auto_discover_path("/data/complete/Does Not Exist")
    assert result is None


@pytest.mark.asyncio
async def test_auto_discover_handles_single_segment_path(fake_mounts):
    # When SAB reports just "/UFC 300" (no parent folders), discovery still
    # walks the probe roots and finds it under any matching mount.
    (fake_mounts["data"] / "UFC 300").mkdir()
    result = await importer._auto_discover_path("/UFC 300")
    assert result is not None
    resolved, _, _ = result
    assert resolved.endswith("UFC 300")


@pytest.mark.asyncio
async def test_auto_discover_prefers_longest_match(fake_mounts):
    # If two roots both contain matching folders, the one matching the longer
    # suffix (more specific) wins via _PROBE_ROOTS ordering.
    (fake_mounts["downloads"] / "complete" / "UFC 327").mkdir(parents=True)
    (fake_mounts["data"] / "UFC 327").mkdir()

    result = await importer._auto_discover_path("/foo/complete/UFC 327")
    assert result is not None
    resolved, _, _ = result
    # /downloads matches the full /complete/UFC 327 suffix → wins
    assert "downloads" in resolved
    assert resolved.endswith(os.path.join("complete", "UFC 327"))


@pytest.mark.asyncio
async def test_persist_auto_mapping_uses_caller_session():
    """_persist_auto_mapping must reuse the provided session, not open a new one.

    Opening a second AsyncSessionLocal while the caller already holds one causes
    'database is locked' on SQLite. This test verifies we never touch
    AsyncSessionLocal inside _persist_auto_mapping.
    """
    from app.models.path_mapping import PathMapping

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.add = MagicMock()
    mock_session.flush = AsyncMock()

    with patch("app.core.database.AsyncSessionLocal") as mock_local:
        await importer._persist_auto_mapping(mock_session, "/data/", "/downloads/")
        mock_local.assert_not_called()

    mock_session.add.assert_called_once()
    added: PathMapping = mock_session.add.call_args[0][0]
    assert added.remote_path == "/data/"
    assert added.local_path == "/downloads/"
    assert added.host == "auto-discovered"
    mock_session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_persist_auto_mapping_skips_duplicate():
    """_persist_auto_mapping is a no-op if the mapping already exists."""
    from app.models.path_mapping import PathMapping

    existing_mapping = PathMapping(host="auto-discovered", remote_path="/data/", local_path="/downloads/")
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing_mapping

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.add = MagicMock()

    await importer._persist_auto_mapping(mock_session, "/data/", "/downloads/")

    mock_session.add.assert_not_called()
