"""Tests for the exploration-task read + lifecycle tools."""

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


TASK_ID = "88888888-8888-8888-8888-888888888888"
USER_ID = "22222222-2222-2222-2222-222222222222"
RUN_ID = "44444444-4444-4444-4444-444444444444"
STRATEGY_ID = "33333333-3333-3333-3333-333333333333"


def _task_json(
    status: str = "OPEN",
    *,
    claimed_by: str | None = None,
    findings: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "id": TASK_ID,
        "created_by": USER_ID,
        "prompt": "Explore mean-reversion on AAPL",
        "status": status,
        "target_portfolio_id": None,
        "tickers": ["AAPL"],
        "constraints": None,
        "claimed_by": claimed_by,
        "claimed_at": "2026-05-02T00:00:00+00:00" if claimed_by else None,
        "findings": findings,
        "created_at": "2026-05-01T00:00:00+00:00",
        "updated_at": "2026-05-01T00:00:00+00:00",
    }


class TestListExplorationTasks:
    async def test_default_call_lists_open_queue(
        self,
        server: FastMCP,
        respx_mock_session: respx.MockRouter,
    ) -> None:
        route = respx_mock_session.get("/exploration-tasks").mock(
            return_value=httpx.Response(
                200,
                json={
                    "items": [_task_json()],
                    "total": 1,
                    "limit": 20,
                    "offset": 0,
                    "has_more": False,
                },
            ),
        )

        result = await server.call_tool("list_exploration_tasks", {})
        out = _structured(result)

        assert route.called
        # status not supplied → server returns the OPEN queue by default;
        # the tool just forwards. Confirm we don't accidentally send
        # ``status=None`` as a literal string.
        url = str(route.calls.last.request.url)
        assert "status=" not in url
        assert "scope=all" in url
        assert out["total"] == 1

    async def test_status_filter_passes_through(
        self,
        server: FastMCP,
        respx_mock_session: respx.MockRouter,
    ) -> None:
        route = respx_mock_session.get("/exploration-tasks").mock(
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
            "list_exploration_tasks",
            {"status": "DONE"},
        )

        assert route.called
        assert "status=DONE" in str(route.calls.last.request.url)


class TestGetExplorationTask:
    async def test_returns_single_task(
        self,
        server: FastMCP,
        respx_mock_session: respx.MockRouter,
    ) -> None:
        respx_mock_session.get(f"/exploration-tasks/{TASK_ID}").mock(
            return_value=httpx.Response(200, json=_task_json()),
        )

        result = await server.call_tool(
            "get_exploration_task",
            {"task_id": TASK_ID},
        )
        out = _structured(result)

        assert out["id"] == TASK_ID
        assert out["prompt"] == "Explore mean-reversion on AAPL"
        assert out["status"] == "OPEN"


class TestCreateExplorationTask:
    async def test_posts_minimal_task(
        self,
        server: FastMCP,
        respx_mock_session: respx.MockRouter,
    ) -> None:
        route = respx_mock_session.post("/exploration-tasks").mock(
            return_value=httpx.Response(201, json=_task_json()),
        )

        result = await server.call_tool(
            "create_exploration_task",
            {"prompt": "Explore mean-reversion on AAPL"},
        )
        out = _structured(result)

        assert route.called
        body = json.loads(route.calls.last.request.content.decode())
        assert body["prompt"] == "Explore mean-reversion on AAPL"
        assert body["target_portfolio_id"] is None
        assert body["tickers"] is None
        assert body["constraints"] is None
        assert out["id"] == TASK_ID

    async def test_posts_with_constraints_and_tickers(
        self,
        server: FastMCP,
        respx_mock_session: respx.MockRouter,
    ) -> None:
        route = respx_mock_session.post("/exploration-tasks").mock(
            return_value=httpx.Response(201, json=_task_json()),
        )

        await server.call_tool(
            "create_exploration_task",
            {
                "prompt": "MA crossover param sweep",
                "tickers": ["AAPL", "MSFT"],
                "constraints": {
                    "max_backtests": 50,
                    "allow_live_activation": False,
                    "strategy_type_whitelist": ["MOVING_AVERAGE_CROSSOVER"],
                },
            },
        )

        body = json.loads(route.calls.last.request.content.decode())
        assert body["tickers"] == ["AAPL", "MSFT"]
        assert body["constraints"]["max_backtests"] == 50
        assert body["constraints"]["allow_live_activation"] is False
        assert body["constraints"]["strategy_type_whitelist"] == [
            "MOVING_AVERAGE_CROSSOVER",
        ]

    async def test_validation_error_surfaces(
        self,
        server: FastMCP,
        respx_mock_session: respx.MockRouter,
    ) -> None:
        respx_mock_session.post("/exploration-tasks").mock(
            return_value=httpx.Response(
                422,
                json={
                    "detail": "prompt: too short",
                    "code": "validation_error",
                    "fields": {"prompt": "Field required"},
                },
            ),
        )

        with pytest.raises(ToolError, match="prompt"):
            await server.call_tool(
                "create_exploration_task",
                {"prompt": ""},
            )

    async def test_auth_error_surfaces(
        self,
        server: FastMCP,
        respx_mock_session: respx.MockRouter,
    ) -> None:
        respx_mock_session.post("/exploration-tasks").mock(
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
                "create_exploration_task",
                {"prompt": "demo"},
            )


class TestClaimExplorationTask:
    async def test_claim_returns_in_progress_task(
        self,
        server: FastMCP,
        respx_mock_session: respx.MockRouter,
    ) -> None:
        route = respx_mock_session.post(f"/exploration-tasks/{TASK_ID}/claim").mock(
            return_value=httpx.Response(
                200,
                json=_task_json(status="IN_PROGRESS", claimed_by="agent-1"),
            ),
        )

        result = await server.call_tool(
            "claim_exploration_task",
            {"task_id": TASK_ID, "agent_id": "agent-1"},
        )
        out = _structured(result)

        assert route.called
        body = json.loads(route.calls.last.request.content.decode())
        assert body["agent_id"] == "agent-1"
        assert out["status"] == "IN_PROGRESS"
        assert out["claimed_by"] == "agent-1"

    async def test_claim_without_explicit_agent_id(
        self,
        server: FastMCP,
        respx_mock_session: respx.MockRouter,
    ) -> None:
        route = respx_mock_session.post(f"/exploration-tasks/{TASK_ID}/claim").mock(
            return_value=httpx.Response(
                200,
                json=_task_json(status="IN_PROGRESS", claimed_by=USER_ID),
            ),
        )

        await server.call_tool(
            "claim_exploration_task",
            {"task_id": TASK_ID},
        )
        # The body should still be sent (with agent_id=None) so the
        # backend's optional ClaimRequest body parses cleanly.
        body = json.loads(route.calls.last.request.content.decode())
        assert body["agent_id"] is None

    async def test_conflict_when_already_claimed(
        self,
        server: FastMCP,
        respx_mock_session: respx.MockRouter,
    ) -> None:
        respx_mock_session.post(f"/exploration-tasks/{TASK_ID}/claim").mock(
            return_value=httpx.Response(
                409,
                json={
                    "detail": (
                        f"Task {TASK_ID} is in IN_PROGRESS status and cannot be claimed"
                    ),
                    "code": "conflict",
                    "fields": None,
                },
            ),
        )

        with pytest.raises(ToolError, match="409"):
            await server.call_tool(
                "claim_exploration_task",
                {"task_id": TASK_ID},
            )

    async def test_auth_error_surfaces(
        self,
        server: FastMCP,
        respx_mock_session: respx.MockRouter,
    ) -> None:
        respx_mock_session.post(f"/exploration-tasks/{TASK_ID}/claim").mock(
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
                "claim_exploration_task",
                {"task_id": TASK_ID},
            )


class TestSubmitExplorationFinding:
    async def test_done_transition_with_summary(
        self,
        server: FastMCP,
        respx_mock_session: respx.MockRouter,
    ) -> None:
        findings: dict[str, object] = {
            "summary": "MA(10/30) is the best fit",
            "backtest_run_ids": [RUN_ID],
            "strategy_ids": [STRATEGY_ID],
            "notes": ["sharpe ~0.8"],
        }
        route = respx_mock_session.post(f"/exploration-tasks/{TASK_ID}/findings").mock(
            return_value=httpx.Response(
                200,
                json=_task_json(status="DONE", findings=findings),
            ),
        )

        result = await server.call_tool(
            "submit_exploration_finding",
            {
                "task_id": TASK_ID,
                "summary": "MA(10/30) is the best fit",
                "backtest_run_ids": [RUN_ID],
                "strategy_ids": [STRATEGY_ID],
                "notes": ["sharpe ~0.8"],
            },
        )
        out = _structured(result)

        assert route.called
        body = json.loads(route.calls.last.request.content.decode())
        assert body["summary"] == "MA(10/30) is the best fit"
        assert body["backtest_run_ids"] == [RUN_ID]
        assert body["strategy_ids"] == [STRATEGY_ID]
        assert body["notes"] == ["sharpe ~0.8"]
        assert out["status"] == "DONE"

    async def test_minimal_payload_defaults_empty_lists(
        self,
        server: FastMCP,
        respx_mock_session: respx.MockRouter,
    ) -> None:
        route = respx_mock_session.post(f"/exploration-tasks/{TASK_ID}/findings").mock(
            return_value=httpx.Response(
                200,
                json=_task_json(
                    status="DONE",
                    findings={
                        "summary": "all done",
                        "backtest_run_ids": [],
                        "strategy_ids": [],
                        "notes": None,
                    },
                ),
            ),
        )

        await server.call_tool(
            "submit_exploration_finding",
            {"task_id": TASK_ID, "summary": "all done"},
        )
        body = json.loads(route.calls.last.request.content.decode())
        assert body["backtest_run_ids"] == []
        assert body["strategy_ids"] == []

    async def test_structured_payload_forwards_all_e2_fields(
        self,
        server: FastMCP,
        respx_mock_session: respx.MockRouter,
    ) -> None:
        """Phase E2 — the new structured kwargs forward through to the
        backend body intact. Validates the tool wiring rather than the
        backend semantics (which the integration tests cover)."""
        route = respx_mock_session.post(f"/exploration-tasks/{TASK_ID}/findings").mock(
            return_value=httpx.Response(
                200,
                json=_task_json(
                    status="DONE",
                    findings={
                        "summary": "MA(20/50) won",
                        "backtest_run_ids": [RUN_ID],
                        "strategy_ids": [STRATEGY_ID],
                        "notes": None,
                        "recommended_strategy_id": STRATEGY_ID,
                        "recommended_parameters": {"fast_window": 20},
                        "metrics": {"total_return_pct": "24.4"},
                        "comparison_to_baseline": None,
                        "confidence": 0.75,
                    },
                ),
            ),
        )

        await server.call_tool(
            "submit_exploration_finding",
            {
                "task_id": TASK_ID,
                "summary": "MA(20/50) won",
                "backtest_run_ids": [RUN_ID],
                "strategy_ids": [STRATEGY_ID],
                "recommended_strategy_id": STRATEGY_ID,
                "recommended_parameters": {
                    "fast_window": 20,
                    "slow_window": 50,
                    "invest_fraction": "1.0",
                },
                "metrics": {
                    "total_return_pct": "24.4",
                    "sharpe_ratio": "1.32",
                    "max_drawdown_pct": "-11.7",
                    "n_trades": 14,
                    "annualized_return_pct": "12.5",
                },
                "comparison_to_baseline": {
                    "baseline_strategy_id": "11111111-1111-1111-1111-111111111111",
                    "baseline_total_return_pct": "18.1",
                    "delta_total_return_pct": "6.3",
                    "delta_sharpe": "0.38",
                },
                "confidence": 0.75,
            },
        )

        assert route.called
        body = json.loads(route.calls.last.request.content.decode())
        # Every E2 field made it onto the wire body.
        assert body["recommended_strategy_id"] == STRATEGY_ID
        assert body["recommended_parameters"] == {
            "fast_window": 20,
            "slow_window": 50,
            "invest_fraction": "1.0",
        }
        assert body["metrics"]["total_return_pct"] == "24.4"
        assert body["metrics"]["sharpe_ratio"] == "1.32"
        assert body["metrics"]["max_drawdown_pct"] == "-11.7"
        assert body["metrics"]["n_trades"] == 14
        assert body["comparison_to_baseline"]["delta_total_return_pct"] == "6.3"
        assert body["comparison_to_baseline"]["delta_sharpe"] == "0.38"
        assert body["confidence"] == 0.75

    async def test_conflict_when_not_in_progress(
        self,
        server: FastMCP,
        respx_mock_session: respx.MockRouter,
    ) -> None:
        respx_mock_session.post(f"/exploration-tasks/{TASK_ID}/findings").mock(
            return_value=httpx.Response(
                409,
                json={
                    "detail": (
                        f"Task {TASK_ID} is in OPEN status; findings can "
                        "only be submitted for IN_PROGRESS tasks"
                    ),
                    "code": "conflict",
                    "fields": None,
                },
            ),
        )

        with pytest.raises(ToolError, match="409"):
            await server.call_tool(
                "submit_exploration_finding",
                {"task_id": TASK_ID, "summary": "premature"},
            )

    async def test_auth_error_surfaces(
        self,
        server: FastMCP,
        respx_mock_session: respx.MockRouter,
    ) -> None:
        respx_mock_session.post(f"/exploration-tasks/{TASK_ID}/findings").mock(
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
                "submit_exploration_finding",
                {"task_id": TASK_ID, "summary": "demo"},
            )


class TestAbandonExplorationTask:
    async def test_deletes_returns_ack(
        self,
        server: FastMCP,
        respx_mock_session: respx.MockRouter,
    ) -> None:
        route = respx_mock_session.delete(f"/exploration-tasks/{TASK_ID}").mock(
            return_value=httpx.Response(204),
        )

        result = await server.call_tool(
            "abandon_exploration_task",
            {"task_id": TASK_ID},
        )
        out = _structured(result)

        assert route.called
        assert out["task_id"] == TASK_ID
        assert out["deleted"] is True

    async def test_forbidden_when_not_creator(
        self,
        server: FastMCP,
        respx_mock_session: respx.MockRouter,
    ) -> None:
        respx_mock_session.delete(f"/exploration-tasks/{TASK_ID}").mock(
            return_value=httpx.Response(
                403,
                json={
                    "detail": "You don't have permission to delete this task",
                    "code": "forbidden",
                    "fields": None,
                },
            ),
        )

        with pytest.raises(ToolError, match="403"):
            await server.call_tool(
                "abandon_exploration_task",
                {"task_id": TASK_ID},
            )

    async def test_auth_error_surfaces(
        self,
        server: FastMCP,
        respx_mock_session: respx.MockRouter,
    ) -> None:
        respx_mock_session.delete(f"/exploration-tasks/{TASK_ID}").mock(
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
                "abandon_exploration_task",
                {"task_id": TASK_ID},
            )


class TestNote:
    async def test_with_task_id_advises_submit_findings(
        self,
        server: FastMCP,
    ) -> None:
        result = await server.call_tool(
            "note",
            {
                "text": "interesting drawdown around earnings",
                "exploration_task_id": TASK_ID,
            },
        )
        out = _structured(result)

        assert out["text"] == "interesting drawdown around earnings"
        assert out["exploration_task_id"] == TASK_ID
        assert out["persisted"] is False
        advice = out["advice"]
        assert isinstance(advice, str)
        assert "submit_exploration_finding" in advice

    async def test_with_strategy_id_advises_create_task(
        self,
        server: FastMCP,
    ) -> None:
        result = await server.call_tool(
            "note",
            {
                "text": "context for AAPL strategy",
                "strategy_id": STRATEGY_ID,
            },
        )
        out = _structured(result)

        assert out["strategy_id"] == STRATEGY_ID
        advice = out["advice"]
        assert isinstance(advice, str)
        assert "exploration_task" in advice

    async def test_bare_note_advises_create_first(
        self,
        server: FastMCP,
    ) -> None:
        result = await server.call_tool(
            "note",
            {"text": "thinking out loud"},
        )
        out = _structured(result)

        assert out["persisted"] is False
        advice = out["advice"]
        assert isinstance(advice, str)
        assert "create" in advice.lower()
