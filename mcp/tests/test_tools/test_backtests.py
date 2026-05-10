"""Tests for the backtest read + run tools."""

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


RUN_ID = "44444444-4444-4444-4444-444444444444"
STRATEGY_A = "55555555-5555-5555-5555-555555555555"
STRATEGY_B = "66666666-6666-6666-6666-666666666666"


def _run_json(
    strategy_id: str = STRATEGY_A,
    *,
    status: str = "COMPLETED",
    completed: bool = True,
) -> dict[str, object]:
    return {
        "id": RUN_ID,
        "user_id": "22222222-2222-2222-2222-222222222222",
        "strategy_id": strategy_id,
        "portfolio_id": "11111111-1111-1111-1111-111111111111",
        "backtest_name": "Test run",
        "start_date": "2026-01-01",
        "end_date": "2026-02-01",
        "initial_cash": "10000.00",
        "status": status,
        "created_at": "2026-02-01T00:00:00+00:00",
        "completed_at": "2026-02-01T00:01:00+00:00" if completed else None,
        "error_message": None,
        "total_return_pct": "12.5000" if completed else None,
        "max_drawdown_pct": "3.1000" if completed else None,
        "annualized_return_pct": "150.0000" if completed else None,
        "total_trades": 8 if completed else None,
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


class TestRunBacktest:
    async def test_completed_response_returned_immediately(
        self,
        server: FastMCP,
        respx_mock_session: respx.MockRouter,
    ) -> None:
        """When the backend responds with COMPLETED (the typical case),
        the tool returns immediately without polling."""
        post_route = respx_mock_session.post("/backtests").mock(
            return_value=httpx.Response(201, json=_run_json()),
        )
        get_route = respx_mock_session.get(f"/backtests/{RUN_ID}")

        result = await server.call_tool(
            "run_backtest",
            {
                "strategy_id": STRATEGY_A,
                "start_date": "2026-01-01",
                "end_date": "2026-02-01",
                "initial_cash": "10000.00",
                "name": "smoke",
            },
        )
        out = _structured(result)

        assert post_route.called
        # No polling round trip needed when status is already terminal.
        assert not get_route.called
        assert out["status"] == "COMPLETED"

        request = post_route.calls.last.request
        body = json.loads(request.content.decode())
        assert body["strategy_id"] == STRATEGY_A
        assert body["start_date"] == "2026-01-01"
        assert body["end_date"] == "2026-02-01"
        assert body["initial_cash"] == "10000.00"
        assert body["backtest_name"] == "smoke"

    async def test_default_name_includes_date_range(
        self,
        server: FastMCP,
        respx_mock_session: respx.MockRouter,
    ) -> None:
        post_route = respx_mock_session.post("/backtests").mock(
            return_value=httpx.Response(201, json=_run_json()),
        )

        await server.call_tool(
            "run_backtest",
            {
                "strategy_id": STRATEGY_A,
                "start_date": "2026-01-01",
                "end_date": "2026-02-01",
                "initial_cash": "10000.00",
            },
        )
        body = json.loads(post_route.calls.last.request.content.decode())
        assert body["backtest_name"]  # default-name branch produced something
        assert "2026-01-01" in body["backtest_name"]

    async def test_polls_until_terminal_when_running(
        self,
        server: FastMCP,
        respx_mock_session: respx.MockRouter,
    ) -> None:
        """If POST returns RUNNING, the tool polls get_backtest_result
        until status flips terminal."""
        respx_mock_session.post("/backtests").mock(
            return_value=httpx.Response(
                201,
                json=_run_json(status="RUNNING", completed=False),
            ),
        )
        # First GET still RUNNING, second GET COMPLETED.
        get_route = respx_mock_session.get(f"/backtests/{RUN_ID}").mock(
            side_effect=[
                httpx.Response(
                    200,
                    json=_run_json(status="RUNNING", completed=False),
                ),
                httpx.Response(200, json=_run_json()),
            ],
        )

        result = await server.call_tool(
            "run_backtest",
            {
                "strategy_id": STRATEGY_A,
                "start_date": "2026-01-01",
                "end_date": "2026-02-01",
                "initial_cash": "10000.00",
                # Use a very small interval to keep the test fast — the
                # implementation sleeps for min(interval, deadline-now).
                "poll_timeout_secs": 5.0,
            },
        )
        out = _structured(result)

        assert get_route.call_count == 2
        assert out["status"] == "COMPLETED"

    async def test_skip_polling_returns_running_run(
        self,
        server: FastMCP,
        respx_mock_session: respx.MockRouter,
    ) -> None:
        respx_mock_session.post("/backtests").mock(
            return_value=httpx.Response(
                201,
                json=_run_json(status="RUNNING", completed=False),
            ),
        )
        get_route = respx_mock_session.get(f"/backtests/{RUN_ID}")

        result = await server.call_tool(
            "run_backtest",
            {
                "strategy_id": STRATEGY_A,
                "start_date": "2026-01-01",
                "end_date": "2026-02-01",
                "initial_cash": "10000.00",
                "wait_for_completion": False,
            },
        )
        out = _structured(result)

        assert not get_route.called
        assert out["status"] == "RUNNING"

    async def test_validation_error_surfaces(
        self,
        server: FastMCP,
        respx_mock_session: respx.MockRouter,
    ) -> None:
        """422 from the backend is mapped to a typed ToolError."""
        respx_mock_session.post("/backtests").mock(
            return_value=httpx.Response(
                422,
                json={
                    "detail": "end_date must be after start_date",
                    "code": "validation_error",
                    "fields": {"end_date": "must be after start_date"},
                },
            ),
        )

        with pytest.raises(ToolError, match="end_date"):
            await server.call_tool(
                "run_backtest",
                {
                    "strategy_id": STRATEGY_A,
                    "start_date": "2026-02-01",
                    "end_date": "2026-01-01",
                    "initial_cash": "10000.00",
                },
            )

    async def test_auth_error_surfaces(
        self,
        server: FastMCP,
        respx_mock_session: respx.MockRouter,
    ) -> None:
        respx_mock_session.post("/backtests").mock(
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
                "run_backtest",
                {
                    "strategy_id": STRATEGY_A,
                    "start_date": "2026-01-01",
                    "end_date": "2026-02-01",
                    "initial_cash": "10000.00",
                },
            )
