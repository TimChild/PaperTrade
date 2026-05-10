"""Shared pytest fixtures for the zebu-mcp test suite."""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
import pytest
import respx

from zebu_mcp.client import ZebuClient
from zebu_mcp.config import ZebuMcpConfig

# All tests use the same fake config so the routed URLs are stable.
TEST_BASE_URL = "https://zebu.test"
TEST_API_KEY = "zk_test_abcdef0123456789"


@pytest.fixture
def config() -> ZebuMcpConfig:
    """Standard config for tests — never makes a real network call."""
    return ZebuMcpConfig(
        api_base_url=TEST_BASE_URL,
        api_key=TEST_API_KEY,
        timeout_secs=5.0,
    )


@pytest.fixture
async def respx_mock_session() -> AsyncIterator[respx.MockRouter]:
    """A respx router that intercepts every httpx call.

    Tests register routes against this fixture; any unmatched request
    raises so we don't accidentally hit the real network.
    """
    async with respx.mock(
        base_url=TEST_BASE_URL + "/api/v1",
        assert_all_called=False,
    ) as router:
        yield router


@pytest.fixture
async def client(
    config: ZebuMcpConfig,
    respx_mock_session: respx.MockRouter,
) -> AsyncIterator[ZebuClient]:
    """Live ZebuClient bound to a respx router (no real network).

    The respx fixture must come first so its mock is active *before* the
    httpx client opens its transport.
    """
    _ = respx_mock_session  # ensure the mock is up before httpx opens
    async with ZebuClient(config) as c:
        yield c


def auth_header_assertion(request: httpx.Request) -> None:
    """Reusable assertion: every captured request carries the API-key header."""
    assert request.headers.get("X-API-Key") == TEST_API_KEY, (
        f"Expected X-API-Key header on {request.method} {request.url}; "
        f"got {request.headers.get('X-API-Key')!r}"
    )
