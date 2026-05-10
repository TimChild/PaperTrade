"""Tests for the portfolio-related tools."""

from __future__ import annotations

import httpx
import respx
from mcp.server.fastmcp import FastMCP


def _structured(result: object) -> dict[str, object]:
    if isinstance(result, tuple):
        _content, structured = result
        assert isinstance(structured, dict)
        return structured
    assert isinstance(result, dict)
    return result


PORTFOLIO_ID = "11111111-1111-1111-1111-111111111111"
USER_ID = "22222222-2222-2222-2222-222222222222"


def _portfolio_json(name: str = "Main") -> dict[str, str]:
    return {
        "id": PORTFOLIO_ID,
        "user_id": USER_ID,
        "name": name,
        "created_at": "2026-01-01T00:00:00+00:00",
        "portfolio_type": "REGULAR",
    }


class TestListPortfolios:
    async def test_returns_paginated_response(
        self,
        server: FastMCP,
        respx_mock_session: respx.MockRouter,
    ) -> None:
        respx_mock_session.get("/portfolios").mock(
            return_value=httpx.Response(
                200,
                json={
                    "items": [_portfolio_json("Main"), _portfolio_json("Roth")],
                    "total": 2,
                    "limit": 20,
                    "offset": 0,
                    "has_more": False,
                },
            ),
        )

        result = await server.call_tool("list_portfolios", {})
        out = _structured(result)

        assert out["total"] == 2
        assert out["has_more"] is False
        items = out["items"]
        assert isinstance(items, list)
        assert len(items) == 2

    async def test_include_backtest_param_passes_through(
        self,
        server: FastMCP,
        respx_mock_session: respx.MockRouter,
    ) -> None:
        route = respx_mock_session.get("/portfolios").mock(
            return_value=httpx.Response(
                200,
                json={
                    "items": [],
                    "total": 0,
                    "limit": 20,
                    "offset": 0,
                    "has_more": False,
                },
            ),
        )

        await server.call_tool(
            "list_portfolios",
            {"include_backtest": True},
        )

        assert route.called
        assert "include_backtest=True" in str(route.calls.last.request.url) or (
            "include_backtest=true" in str(route.calls.last.request.url)
        )


class TestGetPortfolioState:
    async def test_aggregates_three_endpoints(
        self,
        server: FastMCP,
        respx_mock_session: respx.MockRouter,
    ) -> None:
        respx_mock_session.get(f"/portfolios/{PORTFOLIO_ID}").mock(
            return_value=httpx.Response(200, json=_portfolio_json()),
        )
        respx_mock_session.get(f"/portfolios/{PORTFOLIO_ID}/balance").mock(
            return_value=httpx.Response(
                200,
                json={
                    "cash_balance": "10000.00",
                    "holdings_value": "1500.00",
                    "total_value": "11500.00",
                    "currency": "USD",
                    "as_of": "2026-05-08T00:00:00+00:00",
                    "daily_change": "20.00",
                    "daily_change_percent": "0.17",
                },
            ),
        )
        respx_mock_session.get(f"/portfolios/{PORTFOLIO_ID}/holdings").mock(
            return_value=httpx.Response(
                200,
                json={
                    "holdings": [
                        {
                            "ticker": "AAPL",
                            "quantity": "10.0000",
                            "cost_basis": "1500.00",
                        },
                    ],
                },
            ),
        )

        result = await server.call_tool(
            "get_portfolio_state",
            {"portfolio_id": PORTFOLIO_ID},
        )
        out = _structured(result)

        assert "portfolio" in out
        assert "balance" in out
        assert "holdings" in out
        portfolio = out["portfolio"]
        balance = out["balance"]
        holdings = out["holdings"]
        assert isinstance(portfolio, dict)
        assert isinstance(balance, dict)
        assert isinstance(holdings, list)
        assert portfolio["name"] == "Main"
        assert balance["total_value"] == "11500.00"
        assert len(holdings) == 1
