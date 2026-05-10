"""Integration tests for the strategy activation API.

Phase C1.3 — covers:

* Activate / deactivate happy paths against a real DB.
* Ownership checks: 403 when caller doesn't own the strategy or portfolio.
* List endpoint returns the standard PaginatedResponse envelope.
* GET /strategies/{id}/activation returns 404 when no activation exists.
* Re-activating an already-active strategy is a 409.
* run-now is wired through both Bearer JWT and API-key auth (Phase C3).
* Auth gating — every route returns 401/403 without credentials.

All tests use the in-memory adapters wired in ``conftest.py`` (in-memory
auth, in-memory market data, SQLite in-memory DB).
"""

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_portfolio(
    client: "TestClient",
    auth_headers: dict[str, str],
    *,
    name: str = "Live Trading Portfolio",
    initial_deposit: str = "10000.00",
) -> str:
    """Create a portfolio (with seed cash) and return its id."""
    response = client.post(
        "/api/v1/portfolios",
        headers=auth_headers,
        json={
            "name": name,
            "initial_deposit": initial_deposit,
            "currency": "USD",
        },
    )
    assert response.status_code == 201, response.text
    pid = response.json()["portfolio_id"]
    assert isinstance(pid, str)
    return pid


def _create_strategy(
    client: "TestClient",
    auth_headers: dict[str, str],
    *,
    name: str = "AAPL Buy and Hold",
    ticker: str = "AAPL",
) -> str:
    """Create a BUY_AND_HOLD strategy and return its id."""
    response = client.post(
        "/api/v1/strategies",
        headers=auth_headers,
        json={
            "name": name,
            "strategy_type": "BUY_AND_HOLD",
            "tickers": [ticker],
            "parameters": {"allocation": {ticker: 1.0}},
        },
    )
    assert response.status_code == 201, response.text
    sid = response.json()["id"]
    assert isinstance(sid, str)
    return sid


def _activate(
    client: "TestClient",
    auth_headers: dict[str, str],
    *,
    strategy_id: str,
    portfolio_id: str,
    expected_status: int = 201,
) -> dict[str, object]:
    """Activate a strategy + assert the response status. Returns the body."""
    response = client.post(
        f"/api/v1/strategies/{strategy_id}/activate",
        headers=auth_headers,
        json={"portfolio_id": portfolio_id},
    )
    assert response.status_code == expected_status, response.text
    body: dict[str, object] = response.json()
    return body


# ---------------------------------------------------------------------------
# Activate
# ---------------------------------------------------------------------------


class TestActivate:
    """``POST /strategies/{id}/activate``."""

    def test_activate_happy_path(
        self,
        client: "TestClient",
        auth_headers: dict[str, str],
    ) -> None:
        portfolio_id = _create_portfolio(client, auth_headers)
        strategy_id = _create_strategy(client, auth_headers)

        body = _activate(
            client,
            auth_headers,
            strategy_id=strategy_id,
            portfolio_id=portfolio_id,
        )
        assert body["strategy_id"] == strategy_id
        assert body["portfolio_id"] == portfolio_id
        assert body["status"] == "ACTIVE"
        assert body["frequency"] == "DAILY_MARKET_CLOSE"
        assert body["last_executed_at"] is None
        assert body["last_error"] is None
        # Sanity: id is a uuid.
        UUID(str(body["id"]))

    def test_activate_invalid_frequency_returns_422(
        self,
        client: "TestClient",
        auth_headers: dict[str, str],
    ) -> None:
        portfolio_id = _create_portfolio(client, auth_headers)
        strategy_id = _create_strategy(client, auth_headers)

        response = client.post(
            f"/api/v1/strategies/{strategy_id}/activate",
            headers=auth_headers,
            json={"portfolio_id": portfolio_id, "frequency": "WEEKLY"},
        )
        assert response.status_code == 422
        body = response.json()
        assert "detail" in body
        assert isinstance(body["detail"], str)

    def test_activate_missing_strategy_returns_404(
        self,
        client: "TestClient",
        auth_headers: dict[str, str],
    ) -> None:
        portfolio_id = _create_portfolio(client, auth_headers)
        response = client.post(
            f"/api/v1/strategies/{uuid4()}/activate",
            headers=auth_headers,
            json={"portfolio_id": portfolio_id},
        )
        assert response.status_code == 404

    def test_activate_missing_portfolio_returns_404(
        self,
        client: "TestClient",
        auth_headers: dict[str, str],
    ) -> None:
        strategy_id = _create_strategy(client, auth_headers)
        response = client.post(
            f"/api/v1/strategies/{strategy_id}/activate",
            headers=auth_headers,
            json={"portfolio_id": str(uuid4())},
        )
        assert response.status_code == 404

    def test_activate_twice_returns_409(
        self,
        client: "TestClient",
        auth_headers: dict[str, str],
    ) -> None:
        portfolio_id = _create_portfolio(client, auth_headers)
        strategy_id = _create_strategy(client, auth_headers)
        _activate(
            client,
            auth_headers,
            strategy_id=strategy_id,
            portfolio_id=portfolio_id,
        )
        # Second activate must fail with 409.
        response = client.post(
            f"/api/v1/strategies/{strategy_id}/activate",
            headers=auth_headers,
            json={"portfolio_id": portfolio_id},
        )
        assert response.status_code == 409

    def test_activate_unauthenticated_rejects(
        self,
        client: "TestClient",
    ) -> None:
        # No auth header at all.
        response = client.post(
            f"/api/v1/strategies/{uuid4()}/activate",
            json={"portfolio_id": str(uuid4())},
        )
        assert response.status_code in (401, 403)

    def test_activate_strategy_owned_by_other_user_returns_403(
        self,
        client: "TestClient",
        auth_headers: dict[str, str],
    ) -> None:
        # The default user creates the portfolio and strategy.
        portfolio_id = _create_portfolio(client, auth_headers)
        strategy_id = _create_strategy(client, auth_headers)

        # A second user calls activate for the same strategy.
        from zebu.adapters.auth.in_memory_adapter import InMemoryAuthAdapter
        from zebu.adapters.inbound.api.dependencies import get_auth_port
        from zebu.application.ports.auth_port import AuthenticatedUser

        override = client.app.dependency_overrides[get_auth_port]
        adapter = override()
        assert isinstance(adapter, InMemoryAuthAdapter)
        adapter.add_user(
            AuthenticatedUser(id="other-user", email="other@example.com"),
            "other-token",
        )

        response = client.post(
            f"/api/v1/strategies/{strategy_id}/activate",
            headers={"Authorization": "Bearer other-token"},
            json={"portfolio_id": portfolio_id},
        )
        assert response.status_code == 403

    def test_activate_with_other_users_portfolio_returns_403(
        self,
        client: "TestClient",
        auth_headers: dict[str, str],
    ) -> None:
        # Strategy belongs to default user; portfolio belongs to other user.
        strategy_id = _create_strategy(client, auth_headers)

        from zebu.adapters.auth.in_memory_adapter import InMemoryAuthAdapter
        from zebu.adapters.inbound.api.dependencies import get_auth_port
        from zebu.application.ports.auth_port import AuthenticatedUser

        override = client.app.dependency_overrides[get_auth_port]
        adapter = override()
        assert isinstance(adapter, InMemoryAuthAdapter)
        adapter.add_user(
            AuthenticatedUser(id="other-user", email="other@example.com"),
            "other-token",
        )

        # Other user creates a portfolio.
        other_portfolio_id = _create_portfolio(
            client,
            {"Authorization": "Bearer other-token"},
            name="Other's Portfolio",
        )

        # Default user tries to activate the strategy against the other
        # user's portfolio — must 403.
        response = client.post(
            f"/api/v1/strategies/{strategy_id}/activate",
            headers=auth_headers,
            json={"portfolio_id": other_portfolio_id},
        )
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# Get strategy activation
# ---------------------------------------------------------------------------


class TestGetStrategyActivation:
    def test_get_returns_activation_body(
        self,
        client: "TestClient",
        auth_headers: dict[str, str],
    ) -> None:
        portfolio_id = _create_portfolio(client, auth_headers)
        strategy_id = _create_strategy(client, auth_headers)
        activation = _activate(
            client,
            auth_headers,
            strategy_id=strategy_id,
            portfolio_id=portfolio_id,
        )

        response = client.get(
            f"/api/v1/strategies/{strategy_id}/activation",
            headers=auth_headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["id"] == activation["id"]

    def test_get_no_activation_returns_404(
        self,
        client: "TestClient",
        auth_headers: dict[str, str],
    ) -> None:
        strategy_id = _create_strategy(client, auth_headers)
        response = client.get(
            f"/api/v1/strategies/{strategy_id}/activation",
            headers=auth_headers,
        )
        assert response.status_code == 404

    def test_get_missing_strategy_returns_404(
        self,
        client: "TestClient",
        auth_headers: dict[str, str],
    ) -> None:
        response = client.get(
            f"/api/v1/strategies/{uuid4()}/activation",
            headers=auth_headers,
        )
        assert response.status_code == 404

    def test_get_other_users_strategy_returns_403(
        self,
        client: "TestClient",
        auth_headers: dict[str, str],
    ) -> None:
        # Default user creates a strategy, other user tries to read its
        # activation slot — must 403, not 404.
        strategy_id = _create_strategy(client, auth_headers)

        from zebu.adapters.auth.in_memory_adapter import InMemoryAuthAdapter
        from zebu.adapters.inbound.api.dependencies import get_auth_port
        from zebu.application.ports.auth_port import AuthenticatedUser

        override = client.app.dependency_overrides[get_auth_port]
        adapter = override()
        assert isinstance(adapter, InMemoryAuthAdapter)
        adapter.add_user(
            AuthenticatedUser(id="other-user", email="other@example.com"),
            "other-token",
        )

        response = client.get(
            f"/api/v1/strategies/{strategy_id}/activation",
            headers={"Authorization": "Bearer other-token"},
        )
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# Deactivate
# ---------------------------------------------------------------------------


class TestDeactivate:
    """``POST /activations/{id}/deactivate``."""

    def test_deactivate_flips_status_to_paused(
        self,
        client: "TestClient",
        auth_headers: dict[str, str],
    ) -> None:
        portfolio_id = _create_portfolio(client, auth_headers)
        strategy_id = _create_strategy(client, auth_headers)
        activation = _activate(
            client,
            auth_headers,
            strategy_id=strategy_id,
            portfolio_id=portfolio_id,
        )
        activation_id = str(activation["id"])

        response = client.post(
            f"/api/v1/activations/{activation_id}/deactivate",
            headers=auth_headers,
            json={"reason": "User paused for the holiday"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "PAUSED"
        assert body["last_error"] == "User paused for the holiday"

    def test_deactivate_without_body_works(
        self,
        client: "TestClient",
        auth_headers: dict[str, str],
    ) -> None:
        portfolio_id = _create_portfolio(client, auth_headers)
        strategy_id = _create_strategy(client, auth_headers)
        activation = _activate(
            client,
            auth_headers,
            strategy_id=strategy_id,
            portfolio_id=portfolio_id,
        )

        response = client.post(
            f"/api/v1/activations/{activation['id']}/deactivate",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["status"] == "PAUSED"

    def test_deactivate_missing_returns_404(
        self,
        client: "TestClient",
        auth_headers: dict[str, str],
    ) -> None:
        response = client.post(
            f"/api/v1/activations/{uuid4()}/deactivate",
            headers=auth_headers,
        )
        assert response.status_code == 404

    def test_deactivate_other_users_activation_returns_403(
        self,
        client: "TestClient",
        auth_headers: dict[str, str],
    ) -> None:
        portfolio_id = _create_portfolio(client, auth_headers)
        strategy_id = _create_strategy(client, auth_headers)
        activation = _activate(
            client,
            auth_headers,
            strategy_id=strategy_id,
            portfolio_id=portfolio_id,
        )

        from zebu.adapters.auth.in_memory_adapter import InMemoryAuthAdapter
        from zebu.adapters.inbound.api.dependencies import get_auth_port
        from zebu.application.ports.auth_port import AuthenticatedUser

        override = client.app.dependency_overrides[get_auth_port]
        adapter = override()
        assert isinstance(adapter, InMemoryAuthAdapter)
        adapter.add_user(
            AuthenticatedUser(id="other-user", email="other@example.com"),
            "other-token",
        )

        response = client.post(
            f"/api/v1/activations/{activation['id']}/deactivate",
            headers={"Authorization": "Bearer other-token"},
        )
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# List activations
# ---------------------------------------------------------------------------


class TestList:
    """``GET /activations``."""

    def test_list_empty(
        self,
        client: "TestClient",
        auth_headers: dict[str, str],
    ) -> None:
        response = client.get("/api/v1/activations", headers=auth_headers)
        assert response.status_code == 200
        page = response.json()
        assert page["items"] == []
        assert page["total"] == 0
        assert page["limit"] == 20
        assert page["offset"] == 0
        assert page["has_more"] is False

    def test_list_returns_paginated_envelope(
        self,
        client: "TestClient",
        auth_headers: dict[str, str],
    ) -> None:
        portfolio_id = _create_portfolio(client, auth_headers)
        for i in range(3):
            sid = _create_strategy(client, auth_headers, name=f"Strategy {i}")
            _activate(
                client,
                auth_headers,
                strategy_id=sid,
                portfolio_id=portfolio_id,
            )

        page = client.get(
            "/api/v1/activations?limit=2&offset=0",
            headers=auth_headers,
        ).json()
        assert page["total"] == 3
        assert page["limit"] == 2
        assert page["offset"] == 0
        assert len(page["items"]) == 2
        assert page["has_more"] is True

        page2 = client.get(
            "/api/v1/activations?limit=2&offset=2",
            headers=auth_headers,
        ).json()
        assert page2["total"] == 3
        assert len(page2["items"]) == 1
        assert page2["has_more"] is False

    def test_list_rejects_limit_above_max(
        self,
        client: "TestClient",
        auth_headers: dict[str, str],
    ) -> None:
        response = client.get("/api/v1/activations?limit=101", headers=auth_headers)
        assert response.status_code == 422

    def test_list_only_includes_callers_activations(
        self,
        client: "TestClient",
        auth_headers: dict[str, str],
    ) -> None:
        # Default user has one activation.
        portfolio_id = _create_portfolio(client, auth_headers)
        strategy_id = _create_strategy(client, auth_headers)
        _activate(
            client,
            auth_headers,
            strategy_id=strategy_id,
            portfolio_id=portfolio_id,
        )

        # Other user has a separate activation.
        from zebu.adapters.auth.in_memory_adapter import InMemoryAuthAdapter
        from zebu.adapters.inbound.api.dependencies import get_auth_port
        from zebu.application.ports.auth_port import AuthenticatedUser

        override = client.app.dependency_overrides[get_auth_port]
        adapter = override()
        assert isinstance(adapter, InMemoryAuthAdapter)
        adapter.add_user(
            AuthenticatedUser(id="other-user", email="other@example.com"),
            "other-token",
        )
        other_headers = {"Authorization": "Bearer other-token"}
        other_portfolio_id = _create_portfolio(client, other_headers)
        other_strategy_id = _create_strategy(client, other_headers)
        _activate(
            client,
            other_headers,
            strategy_id=other_strategy_id,
            portfolio_id=other_portfolio_id,
        )

        # Default user's list contains only their activation.
        page = client.get("/api/v1/activations", headers=auth_headers).json()
        assert page["total"] == 1


# ---------------------------------------------------------------------------
# Run now — exercises BOTH Bearer JWT and API-key auth (Phase C3)
# ---------------------------------------------------------------------------


class TestRunNow:
    """``POST /activations/{id}/run-now``."""

    def test_run_now_executes_and_returns_outcome(
        self,
        client: "TestClient",
        auth_headers: dict[str, str],
    ) -> None:
        portfolio_id = _create_portfolio(client, auth_headers)
        strategy_id = _create_strategy(client, auth_headers)
        activation = _activate(
            client,
            auth_headers,
            strategy_id=strategy_id,
            portfolio_id=portfolio_id,
        )

        response = client.post(
            f"/api/v1/activations/{activation['id']}/run-now",
            headers=auth_headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["succeeded"] is True
        # AAPL is seeded in the test market data adapter — Buy-and-Hold
        # produces exactly one BUY trade on the first run.
        assert body["trades"] == 1
        assert body["error"] is None
        assert body["activation"]["last_executed_at"] is not None

    def test_run_now_missing_returns_404(
        self,
        client: "TestClient",
        auth_headers: dict[str, str],
    ) -> None:
        response = client.post(
            f"/api/v1/activations/{uuid4()}/run-now",
            headers=auth_headers,
        )
        assert response.status_code == 404

    def test_run_now_other_users_activation_returns_403(
        self,
        client: "TestClient",
        auth_headers: dict[str, str],
    ) -> None:
        portfolio_id = _create_portfolio(client, auth_headers)
        strategy_id = _create_strategy(client, auth_headers)
        activation = _activate(
            client,
            auth_headers,
            strategy_id=strategy_id,
            portfolio_id=portfolio_id,
        )

        from zebu.adapters.auth.in_memory_adapter import InMemoryAuthAdapter
        from zebu.adapters.inbound.api.dependencies import get_auth_port
        from zebu.application.ports.auth_port import AuthenticatedUser

        override = client.app.dependency_overrides[get_auth_port]
        adapter = override()
        assert isinstance(adapter, InMemoryAuthAdapter)
        adapter.add_user(
            AuthenticatedUser(id="other-user", email="other@example.com"),
            "other-token",
        )

        response = client.post(
            f"/api/v1/activations/{activation['id']}/run-now",
            headers={"Authorization": "Bearer other-token"},
        )
        assert response.status_code == 403

    def test_run_now_accepts_api_key_auth(
        self,
        client: "TestClient",
    ) -> None:
        """Phase C3 — run-now must accept the API-key transports too.

        The default test user is wired up in conftest.py with a seeded
        API key (raw value: ``"test-token-default"``). Sending it via
        ``X-API-Key`` should resolve to the same UUID and let the same
        ownership check pass.
        """
        # Set up portfolio + strategy + activation via Bearer first.
        bearer_headers = {"Authorization": "Bearer test-token-default"}
        portfolio_id = _create_portfolio(client, bearer_headers)
        strategy_id = _create_strategy(client, bearer_headers)
        activation = _activate(
            client,
            bearer_headers,
            strategy_id=strategy_id,
            portfolio_id=portfolio_id,
        )

        # Now hit run-now with the X-API-Key header; same user.
        response = client.post(
            f"/api/v1/activations/{activation['id']}/run-now",
            headers={"X-API-Key": "test-token-default"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["succeeded"] is True

    def test_run_now_unauthenticated_rejects(
        self,
        client: "TestClient",
    ) -> None:
        response = client.post(
            f"/api/v1/activations/{uuid4()}/run-now",
        )
        assert response.status_code in (401, 403)
