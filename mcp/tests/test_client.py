"""Unit tests for :class:`ZebuClient`.

Boundary tests at the httpx layer: every assertion is about what the
client SENDS (auth header, params) or what it RAISES on error responses.
The full per-tool happy-path coverage lives in ``test_tools/``.
"""

from __future__ import annotations

import httpx
import pytest
import respx

from zebu_mcp.client import ZebuApiError, ZebuClient
from zebu_mcp.config import ZebuMcpConfig

# Mirror the constant from conftest so tests don't depend on a
# package-style ``from tests.conftest import …`` (pytest doesn't put the
# tests dir on sys.path as a package by default).
TEST_API_KEY = "NOT-A-REAL-API-KEY"


class TestRequiresContextManager:
    """Calling client methods outside ``async with`` is a developer error."""

    async def test_raises_runtime_error_when_not_entered(
        self,
        config: ZebuMcpConfig,
    ) -> None:
        client = ZebuClient(config)
        with pytest.raises(RuntimeError, match="async with"):
            await client.list_supported_tickers()


class TestAuthHeaderInjection:
    """Every request carries ``X-API-Key`` set from the config."""

    async def test_sets_api_key_on_simple_get(
        self,
        client: ZebuClient,
        respx_mock_session: respx.MockRouter,
    ) -> None:
        route = respx_mock_session.get("/prices/").mock(
            return_value=httpx.Response(
                200,
                json={"tickers": ["AAPL"], "count": 1},
            ),
        )

        await client.list_supported_tickers()

        assert route.called
        assert route.calls.last.request.headers["X-API-Key"] == TEST_API_KEY

    async def test_sets_api_key_on_request_with_params(
        self,
        client: ZebuClient,
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

        await client.list_portfolios(limit=20, offset=0)

        assert route.called
        assert route.calls.last.request.headers["X-API-Key"] == TEST_API_KEY


class TestErrorMapping:
    """Non-2xx responses raise typed :class:`ZebuApiError`."""

    async def test_404_with_envelope_carries_code_and_detail(
        self,
        client: ZebuClient,
        respx_mock_session: respx.MockRouter,
    ) -> None:
        respx_mock_session.get("/prices/UNKNOWN").mock(
            return_value=httpx.Response(
                404,
                json={
                    "detail": "Ticker not found: UNKNOWN",
                    "code": "ticker_not_found",
                    "fields": {"ticker": "UNKNOWN"},
                },
            ),
        )

        with pytest.raises(ZebuApiError) as exc_info:
            await client.get_current_price("UNKNOWN")

        err = exc_info.value
        assert err.status_code == 404
        assert err.code == "ticker_not_found"
        assert err.detail == "Ticker not found: UNKNOWN"
        assert err.fields == {"ticker": "UNKNOWN"}
        # The exception's str() form is useful for log messages.
        assert "404" in str(err)
        assert "ticker_not_found" in str(err)

    async def test_422_with_per_field_map(
        self,
        client: ZebuClient,
        respx_mock_session: respx.MockRouter,
    ) -> None:
        respx_mock_session.get("/strategies").mock(
            return_value=httpx.Response(
                422,
                json={
                    "detail": "Validation error",
                    "code": "validation_error",
                    "fields": {
                        "limit": "Input should be less than or equal to 100",
                    },
                },
            ),
        )

        with pytest.raises(ZebuApiError) as exc_info:
            await client.list_strategies(limit=20)

        assert exc_info.value.fields == {
            "limit": "Input should be less than or equal to 100",
        }

    async def test_500_with_non_json_body_falls_back_to_text(
        self,
        client: ZebuClient,
        respx_mock_session: respx.MockRouter,
    ) -> None:
        respx_mock_session.get("/prices/").mock(
            return_value=httpx.Response(500, text="Upstream exploded"),
        )

        with pytest.raises(ZebuApiError) as exc_info:
            await client.list_supported_tickers()

        err = exc_info.value
        assert err.status_code == 500
        assert err.detail == "Upstream exploded"
        # No envelope → no code, no fields.
        assert err.code is None
        assert err.fields is None


class TestPaginationDeserialization:
    """``Page[T]`` deserializes the backend's ``PaginatedResponse[T]``."""

    async def test_preserves_pagination_metadata(
        self,
        client: ZebuClient,
        respx_mock_session: respx.MockRouter,
    ) -> None:
        respx_mock_session.get("/portfolios").mock(
            return_value=httpx.Response(
                200,
                json={
                    "items": [
                        {
                            "id": "00000000-0000-0000-0000-000000000001",
                            "user_id": "00000000-0000-0000-0000-000000000099",
                            "name": "Main",
                            "created_at": "2026-01-01T00:00:00+00:00",
                            "portfolio_type": "REGULAR",
                        },
                    ],
                    "total": 134,
                    "limit": 20,
                    "offset": 0,
                    "has_more": True,
                },
            ),
        )

        page = await client.list_portfolios()

        assert page.total == 134
        assert page.limit == 20
        assert page.offset == 0
        assert page.has_more is True
        assert len(page.items) == 1
        assert page.items[0].name == "Main"

    async def test_drops_none_query_params(
        self,
        client: ZebuClient,
        respx_mock_session: respx.MockRouter,
    ) -> None:
        """``status=None`` should be stripped, not serialised as the literal 'None'."""
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

        await client.list_exploration_tasks(status=None, scope="all")

        assert route.called
        url = str(route.calls.last.request.url)
        assert "status=" not in url, f"None status should be dropped; got {url}"
        assert "scope=all" in url


class TestHoldingsResponseUnwrapping:
    """The holdings endpoint returns ``{"holdings": [...]}`` — the client unwraps."""

    async def test_unwraps_holdings_envelope(
        self,
        client: ZebuClient,
        respx_mock_session: respx.MockRouter,
    ) -> None:
        portfolio_id = "00000000-0000-0000-0000-000000000001"
        respx_mock_session.get(f"/portfolios/{portfolio_id}/holdings").mock(
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

        from uuid import UUID

        holdings = await client.get_portfolio_holdings(UUID(portfolio_id))

        assert len(holdings) == 1
        assert holdings[0].ticker == "AAPL"
        assert holdings[0].quantity == "10.0000"


class TestUserAgent:
    """Sanity: the client sets a recognisable User-Agent header."""

    async def test_user_agent_contains_zebu_mcp(
        self,
        client: ZebuClient,
        respx_mock_session: respx.MockRouter,
    ) -> None:
        route = respx_mock_session.get("/prices/").mock(
            return_value=httpx.Response(
                200,
                json={"tickers": [], "count": 0},
            ),
        )

        await client.list_supported_tickers()

        ua = route.calls.last.request.headers.get("user-agent", "")
        assert "zebu-mcp" in ua
