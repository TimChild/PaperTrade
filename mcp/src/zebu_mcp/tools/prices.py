"""Price-related read tools."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from zebu_mcp.client import ZebuClient
from zebu_mcp.schemas import CurrentPrice, PriceHistory


def register(server: FastMCP, client: ZebuClient) -> None:
    """Register price tools on ``server``."""

    @server.tool(
        name="get_current_price",
        description=(
            "Get the most recent observed price for a single ticker. "
            "Returns price, currency, timestamp, source, and a staleness flag "
            "(true when the price is older than 1 hour). Useful for sanity-"
            "checking that a ticker has a fresh price before activating a "
            "strategy on it."
        ),
    )
    async def get_current_price(ticker: str) -> CurrentPrice:
        """Get current price for ``ticker`` (e.g. ``AAPL``)."""
        return await client.get_current_price(ticker)

    @server.tool(
        name="get_price_history",
        description=(
            "Get historical price data for a ticker over a date range. "
            "Use this to feed backtest-strategy ideas: e.g. fetch 1y of "
            "daily closes, look for mean-reversion windows, then propose a "
            "strategy. Dates accept either YYYY-MM-DD (interpreted as UTC "
            "midnight) or full ISO-8601 datetimes. Interval is one of "
            "'1min', '5min', '1hour', '1day' (default '1day')."
        ),
    )
    async def get_price_history(
        ticker: str,
        start: str,
        end: str,
        interval: str = "1day",
    ) -> PriceHistory:
        """Get a ticker's historical price series."""
        return await client.get_price_history(
            ticker,
            start=start,
            end=end,
            interval=interval,
        )
