"""Tests for auto-discovery path resolution in the importer."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

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
