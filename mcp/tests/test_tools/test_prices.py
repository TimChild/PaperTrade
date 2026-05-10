"""Tests for the price-related tools."""

from __future__ import annotations

import httpx
import respx
from mcp.server.fastmcp import FastMCP


def _structured(result: object) -> dict[str, object]:
    """Extract structured output from a FastMCP call_tool result."""
    if isinstance(result, tuple):
        _content, structured = result
        assert isinstance(structured, dict)
        return structured
    assert isinstance(result, dict)
    return result


class TestGetCurrentPrice:
    async def test_returns_price_payload(
        self,
        server: FastMCP,
        respx_mock_session: respx.MockRouter,
    ) -> None:
        respx_mock_session.get("/prices/AAPL").mock(
            return_value=httpx.Response(
                200,
                json={
                    "ticker": "AAPL",
                    "price": "184.32",
                    "currency": "USD",
                    "timestamp": "2026-05-08T20:00:00+00:00",
                    "source": "alpha_vantage",
                    "is_stale": False,
                },
            ),
        )

        result = await server.call_tool("get_current_price", {"ticker": "AAPL"})
        out = _structured(result)
        assert out["ticker"] == "AAPL"
        assert out["price"] == "184.32"
        assert out["is_stale"] is False


class TestGetPriceHistory:
    async def test_passes_dates_and_interval_as_query_params(
        self,
        server: FastMCP,
        respx_mock_session: respx.MockRouter,
    ) -> None:
        route = respx_mock_session.get("/prices/AAPL/history").mock(
            return_value=httpx.Response(
                200,
                json={
                    "ticker": "AAPL",
                    "prices": [],
                    "start": "2026-01-01T00:00:00+00:00",
                    "end": "2026-02-01T00:00:00+00:00",
                    "interval": "1day",
                    "count": 0,
                },
            ),
        )

        await server.call_tool(
            "get_price_history",
            {
                "ticker": "AAPL",
                "start": "2026-01-01",
                "end": "2026-02-01",
                "interval": "1day",
            },
        )

        assert route.called
        url = str(route.calls.last.request.url)
        assert "start=2026-01-01" in url
        assert "end=2026-02-01" in url
        assert "interval=1day" in url

    async def test_default_interval_is_1day(
        self,
        server: FastMCP,
        respx_mock_session: respx.MockRouter,
    ) -> None:
        route = respx_mock_session.get("/prices/AAPL/history").mock(
            return_value=httpx.Response(
                200,
                json={
                    "ticker": "AAPL",
                    "prices": [],
                    "start": "2026-01-01T00:00:00+00:00",
                    "end": "2026-02-01T00:00:00+00:00",
                    "interval": "1day",
                    "count": 0,
                },
            ),
        )

        await server.call_tool(
            "get_price_history",
            {"ticker": "AAPL", "start": "2026-01-01", "end": "2026-02-01"},
        )

        assert route.called
        assert "interval=1day" in str(route.calls.last.request.url)
