"""Tests for the Newznab API client.

All parsing tests use fixture XML files — no live indexer calls.
The search() integration test mocks httpx so the HTTP layer is covered
without network access.
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.newznab import NewznabClient, NewznabError, parse_search_response

FIXTURE_DIR = Path(__file__).parent / "fixtures"


def _fixture(name: str) -> bytes:
    return (FIXTURE_DIR / name).read_bytes()


# ---------------------------------------------------------------------------
# parse_search_response — pure parsing, no HTTP
# ---------------------------------------------------------------------------


def test_parse_returns_only_valid_items():
    # Fixture has 3 items; the third has no enclosure and must be skipped.
    releases = parse_search_response(_fixture("newznab_search.xml"), "TestIndexer")
    assert len(releases) == 2


def test_parse_release_fields_from_newznab_attr():
    releases = parse_search_response(_fixture("newznab_search.xml"), "TestIndexer")
    r = releases[0]

    assert r.title == "UFC.300.Pereira.vs.Hill.1080p.WEB-DL.H264-GROUP"
    assert "abc123" in r.nzb_url
    assert r.size_bytes == 6442450944  # from newznab:attr, not enclosure length=0
    assert r.indexer_name == "TestIndexer"
    assert r.pub_date == "Sat, 13 Apr 2024 22:00:00 +0000"
    assert "abc123" in (r.guid or "")


def test_parse_size_falls_back_to_enclosure_length():
    # Second fixture item has no newznab:attr size — must read enclosure length.
    releases = parse_search_response(_fixture("newznab_search.xml"), "TestIndexer")
    assert releases[1].size_bytes == 3221225472


def test_error_xml_raises_newznab_error():
    with pytest.raises(NewznabError) as exc_info:
        parse_search_response(_fixture("newznab_error.xml"), "TestIndexer")
    assert exc_info.value.code == 100
    assert "credentials" in exc_info.value.description.lower()


# ---------------------------------------------------------------------------
# NewznabClient.search() — HTTP layer via mock
# ---------------------------------------------------------------------------


async def test_search_calls_correct_endpoint():
    xml_bytes = _fixture("newznab_search.xml")

    mock_response = MagicMock()
    mock_response.content = xml_bytes
    mock_response.raise_for_status = MagicMock()
    mock_response.request.url = (
        "https://example.com/api?t=search&q=UFC+300&apikey=secret-key&o=xml&cat=5070%2C5080"
    )
    mock_response.status_code = 200

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("app.services.newznab.httpx.AsyncClient", return_value=mock_client):
        client = NewznabClient("MyIndexer", "https://example.com", "secret-key")
        releases, url = await client.search("UFC 300", "5070,5080")

    mock_client.get.assert_called_once_with(
        "https://example.com/api",
        params={
            "t": "search",
            "q": "UFC 300",
            "apikey": "secret-key",
            "o": "xml",
            "cat": "5070,5080",
        },
    )
    assert len(releases) == 2
    assert "apikey=***" in url
    assert "secret-key" not in url
    assert releases[0].indexer_name == "MyIndexer"
