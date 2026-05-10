"""Tests for the ``list_supported_tickers`` tool."""

from __future__ import annotations

import httpx
import respx
from mcp.server.fastmcp import FastMCP


class TestListSupportedTickers:
    async def test_returns_supported_tickers(
        self,
        server: FastMCP,
        respx_mock_session: respx.MockRouter,
    ) -> None:
        respx_mock_session.get("/prices/").mock(
            return_value=httpx.Response(
                200,
                json={"tickers": ["AAPL", "MSFT", "NVDA"], "count": 3},
            ),
        )

        result = await server.call_tool("list_supported_tickers", {})

        # FastMCP returns (content, structured_output) when structured
        # output is enabled (default for typed return). Treat the
        # structured output as authoritative; we don't assert on the
        # text content shape because that's MCP-internal.
        if isinstance(result, tuple):
            _content, structured = result
        else:
            structured = result

        assert structured == {"tickers": ["AAPL", "MSFT", "NVDA"], "count": 3}

    async def test_tool_is_listed_with_description(
        self,
        server: FastMCP,
    ) -> None:
        tools = await server.list_tools()
        tool = next(t for t in tools if t.name == "list_supported_tickers")
        assert tool.description is not None
        assert "tickers" in tool.description.lower()
