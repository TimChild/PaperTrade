"""Opt-in integration smoke test against a real Zebu backend.

Off by default. To run:

    ZEBU_MCP_INTEGRATION=1 \
    ZEBU_API_BASE_URL=http://localhost:8000 \
    ZEBU_API_KEY=zk_... \
    uv run pytest tests/test_smoke.py -v

The test deliberately exercises the *easiest* read tool
(``list_supported_tickers``) — it requires only an unrevoked key with
the ``read`` scope and doesn't depend on the user having any
portfolios / strategies / etc. We don't try to enumerate every tool;
that's what the unit tests are for. This one's job is "prove the
process can talk to a real API".
"""

from __future__ import annotations

import os

import pytest

from zebu_mcp.client import ZebuClient
from zebu_mcp.config import ZebuMcpConfig

_INTEGRATION_REASON = (
    "Set ZEBU_MCP_INTEGRATION=1 (plus ZEBU_API_BASE_URL and ZEBU_API_KEY) to run"
)


@pytest.mark.integration
@pytest.mark.skipif(
    os.getenv("ZEBU_MCP_INTEGRATION") != "1",
    reason=_INTEGRATION_REASON,
)
async def test_smoke_list_supported_tickers() -> None:
    """End-to-end: the client can talk to a real Zebu backend.

    Hits ``GET /api/v1/prices/`` with the configured API key and asserts
    a non-empty ticker list comes back. Anything else is a failure of
    the integration plumbing, not of the test.
    """
    config = ZebuMcpConfig.from_env()
    async with ZebuClient(config) as client:
        result = await client.list_supported_tickers()

    assert result.count >= 1, (
        "Expected at least one supported ticker — is the backend "
        "configured with a market-data adapter that has data?"
    )
    assert len(result.tickers) == result.count
