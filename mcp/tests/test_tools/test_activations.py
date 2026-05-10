"""Tests for the strategy-activation read + lifecycle tools."""

from __future__ import annotations

import json

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
    last_error: str | None = None,
) -> dict[str, object]:
    return {
        "id": activation_id,
        "user_id": USER_ID,
        "strategy_id": STRATEGY_ID,
        "portfolio_id": PORTFOLIO_ID,
        "status": status,
        "frequency": "DAILY_MARKET_CLOSE",
        "last_executed_at": None,
        "last_error": last_error,
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


class TestActivateStrategy:
    async def test_posts_to_activate_endpoint(
        self,
        server: FastMCP,
        respx_mock_session: respx.MockRouter,
    ) -> None:
        route = respx_mock_session.post(f"/strategies/{STRATEGY_ID}/activate").mock(
            return_value=httpx.Response(201, json=_activation_json()),
        )

        result = await server.call_tool(
            "activate_strategy",
            {
                "strategy_id": STRATEGY_ID,
                "portfolio_id": PORTFOLIO_ID,
            },
        )
        out = _structured(result)

        assert route.called
        body = json.loads(route.calls.last.request.content.decode())
        assert body["portfolio_id"] == PORTFOLIO_ID
        # Default frequency forwarded explicitly so the backend always
        # sees a stable value rather than relying on its own default.
        assert body["frequency"] == "DAILY_MARKET_CLOSE"
        assert out["status"] == "ACTIVE"

    async def test_conflict_when_already_active(
        self,
        server: FastMCP,
        respx_mock_session: respx.MockRouter,
    ) -> None:
        from mcp.server.fastmcp.exceptions import ToolError

        respx_mock_session.post(f"/strategies/{STRATEGY_ID}/activate").mock(
            return_value=httpx.Response(
                409,
                json={
                    "detail": (
                        f"Strategy {STRATEGY_ID} already has an active activation."
                    ),
                    "code": "conflict",
                    "fields": None,
                },
            ),
        )

        with pytest.raises(ToolError, match="409"):
            await server.call_tool(
                "activate_strategy",
                {
                    "strategy_id": STRATEGY_ID,
                    "portfolio_id": PORTFOLIO_ID,
                },
            )

    async def test_auth_error_surfaces(
        self,
        server: FastMCP,
        respx_mock_session: respx.MockRouter,
    ) -> None:
        from mcp.server.fastmcp.exceptions import ToolError

        respx_mock_session.post(f"/strategies/{STRATEGY_ID}/activate").mock(
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
                "activate_strategy",
                {
                    "strategy_id": STRATEGY_ID,
                    "portfolio_id": PORTFOLIO_ID,
                },
            )


class TestDeactivateActivation:
    async def test_pauses_activation(
        self,
        server: FastMCP,
        respx_mock_session: respx.MockRouter,
    ) -> None:
        route = respx_mock_session.post(
            f"/activations/{ACTIVATION_ID}/deactivate"
        ).mock(
            return_value=httpx.Response(
                200,
                json=_activation_json(status="PAUSED", last_error="agent test"),
            ),
        )

        result = await server.call_tool(
            "deactivate_activation",
            {
                "activation_id": ACTIVATION_ID,
                "reason": "agent test",
            },
        )
        out = _structured(result)

        assert route.called
        body = json.loads(route.calls.last.request.content.decode())
        assert body["reason"] == "agent test"
        assert out["status"] == "PAUSED"

    async def test_optional_reason_omitted(
        self,
        server: FastMCP,
        respx_mock_session: respx.MockRouter,
    ) -> None:
        route = respx_mock_session.post(
            f"/activations/{ACTIVATION_ID}/deactivate"
        ).mock(
            return_value=httpx.Response(
                200,
                json=_activation_json(status="PAUSED"),
            ),
        )

        await server.call_tool(
            "deactivate_activation",
            {"activation_id": ACTIVATION_ID},
        )
        body = json.loads(route.calls.last.request.content.decode())
        # The wire body always includes the field (set to None) so the
        # backend's pydantic model parses cleanly.
        assert body["reason"] is None

    async def test_validation_error_surfaces(
        self,
        server: FastMCP,
        respx_mock_session: respx.MockRouter,
    ) -> None:
        from mcp.server.fastmcp.exceptions import ToolError

        respx_mock_session.post(f"/activations/{ACTIVATION_ID}/deactivate").mock(
            return_value=httpx.Response(
                422,
                json={
                    "detail": "reason: too long",
                    "code": "validation_error",
                    "fields": {"reason": "ensure this value has at most 500 chars"},
                },
            ),
        )

        with pytest.raises(ToolError, match="reason"):
            await server.call_tool(
                "deactivate_activation",
                {
                    "activation_id": ACTIVATION_ID,
                    "reason": "x" * 600,
                },
            )

    async def test_auth_error_surfaces(
        self,
        server: FastMCP,
        respx_mock_session: respx.MockRouter,
    ) -> None:
        from mcp.server.fastmcp.exceptions import ToolError

        respx_mock_session.post(f"/activations/{ACTIVATION_ID}/deactivate").mock(
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
                "deactivate_activation",
                {"activation_id": ACTIVATION_ID},
            )


class TestRunActivationNow:
    async def test_returns_post_run_state(
        self,
        server: FastMCP,
        respx_mock_session: respx.MockRouter,
    ) -> None:
        route = respx_mock_session.post(f"/activations/{ACTIVATION_ID}/run-now").mock(
            return_value=httpx.Response(
                200,
                json={
                    "activation": _activation_json(),
                    "succeeded": True,
                    "trades": 2,
                    "error": None,
                },
            ),
        )

        result = await server.call_tool(
            "run_activation_now",
            {"activation_id": ACTIVATION_ID},
        )
        out = _structured(result)

        assert route.called
        assert out["succeeded"] is True
        assert out["trades"] == 2
        activation = out["activation"]
        assert isinstance(activation, dict)
        assert activation["id"] == ACTIVATION_ID

    async def test_run_failure_surfaces_in_response(
        self,
        server: FastMCP,
        respx_mock_session: respx.MockRouter,
    ) -> None:
        """A 200 with succeeded=false carries the post-run error info — the
        tool returns it normally (the HTTP call succeeded; the strategy run
        didn't)."""
        respx_mock_session.post(f"/activations/{ACTIVATION_ID}/run-now").mock(
            return_value=httpx.Response(
                200,
                json={
                    "activation": _activation_json(
                        status="ERROR", last_error="upstream failure"
                    ),
                    "succeeded": False,
                    "trades": 0,
                    "error": "upstream failure",
                },
            ),
        )

        result = await server.call_tool(
            "run_activation_now",
            {"activation_id": ACTIVATION_ID},
        )
        out = _structured(result)

        assert out["succeeded"] is False
        assert out["error"] == "upstream failure"

    async def test_auth_error_surfaces(
        self,
        server: FastMCP,
        respx_mock_session: respx.MockRouter,
    ) -> None:
        from mcp.server.fastmcp.exceptions import ToolError

        respx_mock_session.post(f"/activations/{ACTIVATION_ID}/run-now").mock(
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
                "run_activation_now",
                {"activation_id": ACTIVATION_ID},
            )
