"""Tests for the exploration-task read tools."""

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


TASK_ID = "88888888-8888-8888-8888-888888888888"
USER_ID = "22222222-2222-2222-2222-222222222222"


def _task_json(status: str = "OPEN") -> dict[str, object]:
    return {
        "id": TASK_ID,
        "created_by": USER_ID,
        "prompt": "Explore mean-reversion on AAPL",
        "status": status,
        "target_portfolio_id": None,
        "tickers": ["AAPL"],
        "constraints": None,
        "claimed_by": None,
        "claimed_at": None,
        "findings": None,
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
