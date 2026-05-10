"""Ticker-listing tool."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from zebu_mcp.client import ZebuClient
from zebu_mcp.schemas import SupportedTickers


def register(server: FastMCP, client: ZebuClient) -> None:
    """Register ticker tools on ``server``."""

    @server.tool(
        name="list_supported_tickers",
        description=(
            "List every stock ticker the Zebu platform has price data for. "
            "Use this before issuing other price/strategy requests to verify "
            "that a symbol is supported — strategies referencing unsupported "
            "tickers fail at create-time."
        ),
    )
    async def list_supported_tickers() -> SupportedTickers:
        """Return the supported-tickers list."""
        return await client.list_supported_tickers()
