"""Tests for the post-processing service."""

import tempfile
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.services.postprocessor import (
    build_file_name,
    build_folder_name,
    detect_quality,
    find_video_file,
    import_file,
)


def _make_event(number=300, main_event="Pereira vs Hill", d=date(2024, 4, 13)):
    return SimpleNamespace(
        id=1,
        slug="ufc-300",
        title=f"UFC {number}: {main_event}",
        event_number=number,
        event_date=d,
        main_event=main_event,
    )


def _make_fight_night(d=date(2024, 6, 1), main="Hill vs Pereira 2"):
    return SimpleNamespace(
        id=2,
        slug="ufc-fight-night-2024-06-01",
        title=f"UFC Fight Night: {main}",
        event_number=None,
        event_date=d,
        main_event=main,
    )


# ── detect_quality ─────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "filename,expected",
    [
        ("UFC.300.1080p.WEB-DL.x265-GROUP.mkv", "1080p WEB-DL x265"),
        ("UFC.Fight.Night.720p.HDTV.x264.mkv", "720p HDTV x264"),
        ("UFC.300.2160p.AMZN.WEB-DL.mkv", "2160p WEB-DL"),
        ("ufc300_ESPN_1080p_h264.mp4", "1080p WEB-DL x264"),
        ("UFC.Fight.Night.480p.mkv", "480p"),
        ("UFC.300.mkv", "Unknown"),
    ],
)
def test_detect_quality(filename: str, expected: str) -> None:
    assert detect_quality(filename) == expected


# ── build_folder_name ──────────────────────────────────────────────────────────


def test_folder_name_ppv() -> None:
    event = _make_event()
    assert build_folder_name(event) == "UFC 300 - Pereira vs Hill (2024-04-13)"


def test_folder_name_fight_night() -> None:
    event = _make_fight_night()
    assert build_folder_name(event) == "UFC Fight Night 2024-06-01 - Hill vs Pereira 2 (2024-06-01)"


def test_folder_name_no_main_event() -> None:
    event = _make_event()
    event.main_event = None
    assert build_folder_name(event) == "UFC 300 (2024-04-13)"


# ── build_file_name ────────────────────────────────────────────────────────────


def test_file_name_ppv() -> None:
    event = _make_event()
    result = build_file_name(event, "1080p WEB-DL x265", ".mkv")
    assert result == "UFC 300 - Pereira vs Hill (2024-04-13) [1080p-WEBDL-x265].mkv"


def test_file_name_no_quality() -> None:
    event = _make_event()
    result = build_file_name(event, "", ".mkv")
    assert result.endswith(".mkv")
    assert "[" not in result


# ── find_video_file ────────────────────────────────────────────────────────────


def test_find_video_file_direct() -> None:
    with tempfile.NamedTemporaryFile(suffix=".mkv", delete=False) as f:
        path = Path(f.name)
    try:
        result = find_video_file(str(path))
        assert result == path
    finally:
        path.unlink(missing_ok=True)


def test_find_video_file_in_dir() -> None:
    with tempfile.TemporaryDirectory() as d:
        small = Path(d) / "sample.mkv"
        large = Path(d) / "UFC.300.1080p.mkv"
        small.write_bytes(b"x" * 100)
        large.write_bytes(b"x" * 1000)
        result = find_video_file(d)
        assert result == large


def test_find_video_file_none() -> None:
    with tempfile.TemporaryDirectory() as d:
        Path(d, "readme.txt").write_text("no video here")
        assert find_video_file(d) is None


# ── import_file ────────────────────────────────────────────────────────────────


def test_import_file_copy() -> None:
    event = _make_event()
    with tempfile.TemporaryDirectory() as src_dir, tempfile.TemporaryDirectory() as media_root:
        src = Path(src_dir) / "UFC.300.1080p.WEB-DL.mkv"
        src.write_bytes(b"fake video content")

        dest = import_file(event, str(src), media_root, use_hardlinks=False)
        assert Path(dest).exists()
        assert "UFC 300" in dest
        assert dest.endswith(".mkv")


def test_import_file_no_video_raises() -> None:
    event = _make_event()
    with tempfile.TemporaryDirectory() as src_dir, tempfile.TemporaryDirectory() as media_root:
        Path(src_dir, "info.txt").write_text("nothing here")
        with pytest.raises(FileNotFoundError):
            import_file(event, src_dir, media_root)
