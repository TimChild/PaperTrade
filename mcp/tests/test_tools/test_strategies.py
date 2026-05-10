"""Tests for the strategy read + create tools."""

from __future__ import annotations

import json

import httpx
import pytest
import respx
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError


def _structured(result: object) -> dict[str, object]:
    if isinstance(result, tuple):
        _content, structured = result
        assert isinstance(structured, dict)
        return structured
    assert isinstance(result, dict)
    return result


STRATEGY_ID = "33333333-3333-3333-3333-333333333333"
USER_ID = "22222222-2222-2222-2222-222222222222"


def _strategy_json(name: str = "MA Crossover") -> dict[str, object]:
    return {
        "id": STRATEGY_ID,
        "user_id": USER_ID,
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


class TestCreateStrategy:
    async def test_posts_request_body_and_returns_strategy(
        self,
        server: FastMCP,
        respx_mock_session: respx.MockRouter,
    ) -> None:
        route = respx_mock_session.post("/strategies").mock(
            return_value=httpx.Response(201, json=_strategy_json()),
        )

        result = await server.call_tool(
            "create_strategy",
            {
                "name": "MA Crossover",
                "strategy_type": "MOVING_AVERAGE_CROSSOVER",
                "tickers": ["AAPL"],
                "parameters": {
                    "fast_window": 10,
                    "slow_window": 30,
                    "invest_fraction": "1.0",
                },
            },
        )
        out = _structured(result)

        assert route.called
        request = route.calls.last.request
        assert request.headers["X-API-Key"]  # auth header present
        body = json.loads(request.content.decode())
        assert body["name"] == "MA Crossover"
        assert body["strategy_type"] == "MOVING_AVERAGE_CROSSOVER"
        assert body["tickers"] == ["AAPL"]
        assert body["parameters"]["fast_window"] == 10
        assert body["parameters"]["slow_window"] == 30
        assert out["id"] == STRATEGY_ID

    async def test_validation_error_surfaces_typed_fields(
        self,
        server: FastMCP,
        respx_mock_session: respx.MockRouter,
    ) -> None:
        """422 from the backend is mapped to a ToolError carrying the
        envelope's per-field detail."""
        respx_mock_session.post("/strategies").mock(
            return_value=httpx.Response(
                422,
                json={
                    "detail": "'invest_fraction' must be > 0 and <= 1.0",
                    "code": "validation_error",
                    "fields": {
                        "invest_fraction": "must be > 0 and <= 1.0",
                    },
                },
            ),
        )

        with pytest.raises(ToolError) as exc_info:
            await server.call_tool(
                "create_strategy",
                {
                    "name": "MA Crossover",
                    "strategy_type": "MOVING_AVERAGE_CROSSOVER",
                    "tickers": ["AAPL"],
                    "parameters": {
                        "fast_window": 10,
                        "slow_window": 30,
                        "invest_fraction": "0",
                    },
                },
            )
        # The underlying ZebuApiError's detail is preserved in the
        # ToolError message string.
        assert "invest_fraction" in str(exc_info.value)

    async def test_auth_error_surfaces(
        self,
        server: FastMCP,
        respx_mock_session: respx.MockRouter,
    ) -> None:
        respx_mock_session.post("/strategies").mock(
            return_value=httpx.Response(
                401,
                json={
                    "detail": "Invalid API key",
                    "code": "invalid_credentials",
                    "fields": None,
                },
            ),
        )

        with pytest.raises(ToolError, match="401"):
            await server.call_tool(
                "create_strategy",
                {
                    "name": "Buy Hold",
                    "strategy_type": "BUY_AND_HOLD",
                    "tickers": ["AAPL"],
                    "parameters": {"allocation": {"AAPL": "1.0"}},
                },
            )
