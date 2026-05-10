"""Tests for the strategy-activation read tools."""

from __future__ import annotations

import httpx
import pytest
import respx
from mcp.server.fastmcp import FastMCP

# pyright: reportUnknownArgumentType=false


def _structured(result: object) -> dict[str, object]:
    if isinstance(result, tuple):
        _content, structured = result
        assert isinstance(structured, dict)
        return structured
    assert isinstance(result, dict)
    return result


STRATEGY_ID = "33333333-3333-3333-3333-333333333333"
ACTIVATION_ID = "77777777-7777-7777-7777-777777777777"
USER_ID = "22222222-2222-2222-2222-222222222222"
PORTFOLIO_ID = "11111111-1111-1111-1111-111111111111"


def _activation_json(
    *,
    activation_id: str = ACTIVATION_ID,
    status: str = "ACTIVE",
) -> dict[str, object]:
    return {
        "id": activation_id,
        "user_id": USER_ID,
        "strategy_id": STRATEGY_ID,
        "portfolio_id": PORTFOLIO_ID,
        "status": status,
        "frequency": "DAILY_MARKET_CLOSE",
        "last_executed_at": None,
        "last_error": None,
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00",
    }


class TestListActiveStrategies:
    async def test_filters_to_active_status(
        self,
        server: FastMCP,
        respx_mock_session: respx.MockRouter,
    ) -> None:
        """The tool is a client-side filter over list_activations."""
        respx_mock_session.get("/activations").mock(
            return_value=httpx.Response(
                200,
                json={
                    "items": [
                        _activation_json(
                            activation_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                            status="ACTIVE",
                        ),
                        _activation_json(
                            activation_id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
                            status="PAUSED",
                        ),
                    ],
                    "total": 2,
                    "limit": 20,
                    "offset": 0,
                    "has_more": False,
                },
            ),
        )

        result = await server.call_tool("list_active_strategies", {})
        out = _structured(result)

        assert out["total"] == 1
        items = out["items"]
        assert isinstance(items, list)
        assert all(item["status"] == "ACTIVE" for item in items)


class TestGetActivation:
    async def test_by_strategy_id_hits_strategy_endpoint(
        self,
        server: FastMCP,
        respx_mock_session: respx.MockRouter,
    ) -> None:
        respx_mock_session.get(f"/strategies/{STRATEGY_ID}/activation").mock(
            return_value=httpx.Response(200, json=_activation_json()),
        )

        result = await server.call_tool(
            "get_activation",
            {"strategy_id": STRATEGY_ID},
        )
        out = _structured(result)

        assert out["id"] == ACTIVATION_ID
        assert out["status"] == "ACTIVE"

    async def test_by_activation_id_paginates_until_found(
        self,
        server: FastMCP,
        respx_mock_session: respx.MockRouter,
    ) -> None:
        respx_mock_session.get("/activations").mock(
            return_value=httpx.Response(
                200,
                json={
                    "items": [_activation_json()],
                    "total": 1,
                    "limit": 100,
                    "offset": 0,
                    "has_more": False,
                },
            ),
        )

        result = await server.call_tool(
            "get_activation",
            {"activation_id": ACTIVATION_ID},
        )
        out = _structured(result)

        assert out["id"] == ACTIVATION_ID

    async def test_neither_id_supplied_raises(
        self,
        server: FastMCP,
    ) -> None:
        # FastMCP wraps tool exceptions; we need to catch the ToolError
        # umbrella. The underlying ValueError message is preserved.
        from mcp.server.fastmcp.exceptions import ToolError

        with pytest.raises(ToolError, match="strategy_id or activation_id"):
            await server.call_tool("get_activation", {})

    async def test_both_ids_supplied_raises(self, server: FastMCP) -> None:
        from mcp.server.fastmcp.exceptions import ToolError

        with pytest.raises(ToolError, match="not both"):
            await server.call_tool(
                "get_activation",
                {
                    "strategy_id": STRATEGY_ID,
                    "activation_id": ACTIVATION_ID,
                },
            )
