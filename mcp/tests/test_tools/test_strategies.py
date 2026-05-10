"""Tests for the strategy read tools."""

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


STRATEGY_ID = "33333333-3333-3333-3333-333333333333"


def _strategy_json(name: str = "MA Crossover") -> dict[str, object]:
    return {
        "id": STRATEGY_ID,
        "user_id": "22222222-2222-2222-2222-222222222222",
        "name": name,
        "strategy_type": "MOVING_AVERAGE_CROSSOVER",
        "tickers": ["AAPL"],
        "parameters": {"fast_window": 10, "slow_window": 30},
        "created_at": "2026-01-01T00:00:00+00:00",
    }


class TestListStrategies:
    async def test_returns_strategy_page(
        self,
        server: FastMCP,
        respx_mock_session: respx.MockRouter,
    ) -> None:
        respx_mock_session.get("/strategies").mock(
            return_value=httpx.Response(
                200,
                json={
                    "items": [_strategy_json()],
                    "total": 1,
                    "limit": 20,
                    "offset": 0,
                    "has_more": False,
                },
            ),
        )

        result = await server.call_tool("list_strategies", {})
        out = _structured(result)

        assert out["total"] == 1
        items = out["items"]
        assert isinstance(items, list)
        assert items[0]["name"] == "MA Crossover"

    async def test_pagination_params_pass_through(
        self,
        server: FastMCP,
        respx_mock_session: respx.MockRouter,
    ) -> None:
        route = respx_mock_session.get("/strategies").mock(
            return_value=httpx.Response(
                200,
                json={
                    "items": [],
                    "total": 0,
                    "limit": 50,
                    "offset": 100,
                    "has_more": False,
                },
            ),
        )

        await server.call_tool(
            "list_strategies",
            {"limit": 50, "offset": 100},
        )

        assert route.called
        url = str(route.calls.last.request.url)
        assert "limit=50" in url
        assert "offset=100" in url


class TestGetStrategy:
    async def test_returns_single_strategy(
        self,
        server: FastMCP,
        respx_mock_session: respx.MockRouter,
    ) -> None:
        respx_mock_session.get(f"/strategies/{STRATEGY_ID}").mock(
            return_value=httpx.Response(200, json=_strategy_json()),
        )

        result = await server.call_tool(
            "get_strategy",
            {"strategy_id": STRATEGY_ID},
        )
        out = _structured(result)

        assert out["id"] == STRATEGY_ID
        assert out["strategy_type"] == "MOVING_AVERAGE_CROSSOVER"
        params = out["parameters"]
        assert isinstance(params, dict)
        assert params["fast_window"] == 10
