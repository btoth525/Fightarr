"""Pytest fixtures and config."""
import pytest


@pytest.fixture
def anyio_backend():
    return "asyncio"
