"""Tests for the backtest read tools."""

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


RUN_ID = "44444444-4444-4444-4444-444444444444"
STRATEGY_A = "55555555-5555-5555-5555-555555555555"
STRATEGY_B = "66666666-6666-6666-6666-666666666666"


def _run_json(strategy_id: str = STRATEGY_A) -> dict[str, object]:
    return {
        "id": RUN_ID,
        "user_id": "22222222-2222-2222-2222-222222222222",
        "strategy_id": strategy_id,
        "portfolio_id": "11111111-1111-1111-1111-111111111111",
        "backtest_name": "Test run",
        "start_date": "2026-01-01",
        "end_date": "2026-02-01",
        "initial_cash": "10000.00",
        "status": "COMPLETED",
        "created_at": "2026-02-01T00:00:00+00:00",
        "completed_at": "2026-02-01T00:01:00+00:00",
        "error_message": None,
        "total_return_pct": "12.5000",
        "max_drawdown_pct": "3.1000",
        "annualized_return_pct": "150.0000",
        "total_trades": 8,
    }


class TestListBacktests:
    async def test_returns_backtest_page(
        self,
        server: FastMCP,
        respx_mock_session: respx.MockRouter,
    ) -> None:
        respx_mock_session.get("/backtests").mock(
            return_value=httpx.Response(
                200,
                json={
                    "items": [_run_json()],
                    "total": 1,
                    "limit": 20,
                    "offset": 0,
                    "has_more": False,
                },
            ),
        )

        result = await server.call_tool("list_backtests", {})
        out = _structured(result)

        assert out["total"] == 1
        items = out["items"]
        assert isinstance(items, list)
        assert items[0]["id"] == RUN_ID

    async def test_strategy_id_filter_applied_client_side(
        self,
        server: FastMCP,
        respx_mock_session: respx.MockRouter,
    ) -> None:
        """Until backend supports server-side strategy_id filtering, the client
        filters on the page that comes back. The result should contain only
        the matching runs."""
        respx_mock_session.get("/backtests").mock(
            return_value=httpx.Response(
                200,
                json={
                    "items": [_run_json(STRATEGY_A), _run_json(STRATEGY_B)],
                    "total": 2,
                    "limit": 20,
                    "offset": 0,
                    "has_more": False,
                },
            ),
        )

        result = await server.call_tool(
            "list_backtests",
            {"strategy_id": STRATEGY_A},
        )
        out = _structured(result)

        assert out["total"] == 1
        items = out["items"]
        assert isinstance(items, list)
        assert all(item["strategy_id"] == STRATEGY_A for item in items)


class TestGetBacktestResult:
    async def test_returns_run_with_metrics(
        self,
        server: FastMCP,
        respx_mock_session: respx.MockRouter,
    ) -> None:
        respx_mock_session.get(f"/backtests/{RUN_ID}").mock(
            return_value=httpx.Response(200, json=_run_json()),
        )

        result = await server.call_tool(
            "get_backtest_result",
            {"run_id": RUN_ID},
        )
        out = _structured(result)

        assert out["id"] == RUN_ID
        assert out["status"] == "COMPLETED"
        assert out["total_return_pct"] == "12.5000"
        assert out["total_trades"] == 8
