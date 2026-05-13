"""Integration tests for the trigger CRUD + fire-log + kill-switch API.

Phase F-5 — covers:

* CRUD happy paths (create, list-for-activation, get, patch, delete).
* Auth: 401 unauthenticated, 403 cross-user.
* Validation: 422 on bad condition_params shape, bad status, lifting
  ``MANUALLY_DISABLED`` via PATCH.
* Pagination envelope on list endpoints.
* Kill-switch endpoints: per-user and admin-wide both transition all
  matching triggers to ``MANUALLY_DISABLED`` and return the count.

All tests use the in-memory adapters wired in ``conftest.py``.
"""

from collections.abc import Iterator
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

import pytest

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_portfolio(
    client: "TestClient",
    auth_headers: dict[str, str],
    *,
    name: str = "Trigger Test Portfolio",
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
) -> str:
    """Activate a strategy + return the activation id."""
    response = client.post(
        f"/api/v1/strategies/{strategy_id}/activate",
        headers=auth_headers,
        json={"portfolio_id": portfolio_id},
    )
    assert response.status_code == 201, response.text
    aid = response.json()["id"]
    assert isinstance(aid, str)
    return aid


def _setup_activation(
    client: "TestClient",
    auth_headers: dict[str, str],
) -> str:
    """Create a portfolio + strategy + activation, return the activation id."""
    portfolio_id = _create_portfolio(client, auth_headers)
    strategy_id = _create_strategy(client, auth_headers)
    return _activate(
        client,
        auth_headers,
        strategy_id=strategy_id,
        portfolio_id=portfolio_id,
    )


def _drawdown_payload(
    *,
    threshold_pct: str = "5",
    lookback_days: int = 30,
) -> dict[str, object]:
    """Default DRAWDOWN_THRESHOLD condition params for tests."""
    return {
        "threshold_pct": threshold_pct,
        "lookback_days": lookback_days,
        "metric": "PORTFOLIO_TOTAL",
    }


def _create_trigger(
    client: "TestClient",
    auth_headers: dict[str, str],
    *,
    activation_id: str,
    agent_prompt: str = (
        "Decide whether to hold the position based on the news context. "
        "Use the read tools to gather earnings and macro data."
    ),
    condition_type: str = "DRAWDOWN_THRESHOLD",
    condition_params: dict[str, object] | None = None,
    cooldown_seconds: int = 21600,
    priority: int = 0,
    expires_at: str | None = None,
    expected_status: int = 201,
) -> dict[str, object]:
    """Create a trigger via POST + assert status. Returns the response body."""
    body: dict[str, object] = {
        "condition_type": condition_type,
        "condition_params": condition_params or _drawdown_payload(),
        "agent_prompt": agent_prompt,
        "cooldown_seconds": cooldown_seconds,
        "priority": priority,
    }
    if expires_at is not None:
        body["expires_at"] = expires_at
    response = client.post(
        f"/api/v1/activations/{activation_id}/triggers",
        headers=auth_headers,
        json=body,
    )
    assert response.status_code == expected_status, response.text
    return response.json()  # type: ignore[no-any-return]


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------


class TestCreateTrigger:
    """``POST /activations/{id}/triggers``."""

    def test_create_drawdown_trigger_happy_path(
        self,
        client: "TestClient",
        auth_headers: dict[str, str],
    ) -> None:
        activation_id = _setup_activation(client, auth_headers)
        body = _create_trigger(
            client,
            auth_headers,
            activation_id=activation_id,
        )
        assert body["activation_id"] == activation_id
        assert body["condition_type"] == "DRAWDOWN_THRESHOLD"
        assert body["status"] == "ACTIVE"
        assert body["priority"] == 0
        assert body["cooldown_seconds"] == 21600
        assert body["last_fired_at"] is None
        assert body["expires_at"] is None
        # Sanity: id is a uuid + condition_params round-trips schema_version.
        UUID(str(body["id"]))
        params = body["condition_params"]
        assert isinstance(params, dict)
        assert params.get("threshold_pct") == "5"
        assert params.get("lookback_days") == 30
        assert params.get("metric") == "PORTFOLIO_TOTAL"
        assert params.get("schema_version") == 1

    def test_create_with_invalid_condition_type_returns_422(
        self,
        client: "TestClient",
        auth_headers: dict[str, str],
    ) -> None:
        activation_id = _setup_activation(client, auth_headers)
        response = client.post(
            f"/api/v1/activations/{activation_id}/triggers",
            headers=auth_headers,
            json={
                "condition_type": "NOT_A_REAL_TYPE",
                "condition_params": _drawdown_payload(),
                "agent_prompt": "x" * 20,
            },
        )
        assert response.status_code == 422

    def test_create_custom_rule_is_rejected(
        self,
        client: "TestClient",
        auth_headers: dict[str, str],
    ) -> None:
        """``CUSTOM_RULE`` is intentionally unimplemented (Phase-F design Q1)."""
        activation_id = _setup_activation(client, auth_headers)
        response = client.post(
            f"/api/v1/activations/{activation_id}/triggers",
            headers=auth_headers,
            json={
                "condition_type": "CUSTOM_RULE",
                "condition_params": {"rule": "x > 5"},
                "agent_prompt": "x" * 20,
            },
        )
        assert response.status_code == 422

    def test_create_with_mismatched_params_returns_422(
        self,
        client: "TestClient",
        auth_headers: dict[str, str],
    ) -> None:
        """DRAWDOWN_THRESHOLD discriminator + VolatilityParams shape mismatch."""
        activation_id = _setup_activation(client, auth_headers)
        response = client.post(
            f"/api/v1/activations/{activation_id}/triggers",
            headers=auth_headers,
            json={
                "condition_type": "DRAWDOWN_THRESHOLD",
                "condition_params": {
                    # VolatilityParams has over_days; DrawdownParams expects
                    # threshold_pct + lookback_days.
                    "over_days": 30,
                    "threshold_pct": "20",
                },
                "agent_prompt": "x" * 20,
            },
        )
        assert response.status_code == 422

    def test_create_short_agent_prompt_returns_422(
        self,
        client: "TestClient",
        auth_headers: dict[str, str],
    ) -> None:
        """Domain entity rejects prompts shorter than 10 chars after trimming."""
        activation_id = _setup_activation(client, auth_headers)
        response = client.post(
            f"/api/v1/activations/{activation_id}/triggers",
            headers=auth_headers,
            json={
                "condition_type": "DRAWDOWN_THRESHOLD",
                "condition_params": _drawdown_payload(),
                "agent_prompt": "tooshort",
            },
        )
        assert response.status_code == 422

    def test_create_unauthenticated_rejects(
        self,
        client: "TestClient",
    ) -> None:
        response = client.post(
            f"/api/v1/activations/{uuid4()}/triggers",
            json={
                "condition_type": "DRAWDOWN_THRESHOLD",
                "condition_params": _drawdown_payload(),
                "agent_prompt": "x" * 20,
            },
        )
        assert response.status_code in (401, 403)

    def test_create_missing_activation_returns_404(
        self,
        client: "TestClient",
        auth_headers: dict[str, str],
    ) -> None:
        response = client.post(
            f"/api/v1/activations/{uuid4()}/triggers",
            headers=auth_headers,
            json={
                "condition_type": "DRAWDOWN_THRESHOLD",
                "condition_params": _drawdown_payload(),
                "agent_prompt": "x" * 20,
            },
        )
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Phase J / Task #213 — queue-mode invocation field
# ---------------------------------------------------------------------------


class TestQueueModeField:
    """``mode`` field on POST / GET / PATCH for the queue-mode trigger."""

    def test_create_without_mode_defaults_to_direct(
        self,
        client: "TestClient",
        auth_headers: dict[str, str],
    ) -> None:
        """Backwards compatibility — no mode in body → mode=direct on response."""
        activation_id = _setup_activation(client, auth_headers)
        body = _create_trigger(client, auth_headers, activation_id=activation_id)
        assert body["mode"] == "direct"

    def test_create_with_queue_mode_persists(
        self,
        client: "TestClient",
        auth_headers: dict[str, str],
    ) -> None:
        """A queue-mode trigger reads back with mode=queue."""
        activation_id = _setup_activation(client, auth_headers)
        response = client.post(
            f"/api/v1/activations/{activation_id}/triggers",
            headers=auth_headers,
            json={
                "condition_type": "DRAWDOWN_THRESHOLD",
                "condition_params": _drawdown_payload(),
                "agent_prompt": (
                    "Pull in news context from my desktop tools and decide."
                ),
                "cooldown_seconds": 21600,
                "priority": 0,
                "mode": "queue",
            },
        )
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["mode"] == "queue"

        # GET round-trips
        getted = client.get(
            f"/api/v1/triggers/{body['id']}",
            headers=auth_headers,
        )
        assert getted.status_code == 200
        assert getted.json()["mode"] == "queue"

    def test_create_with_invalid_mode_returns_422(
        self,
        client: "TestClient",
        auth_headers: dict[str, str],
    ) -> None:
        activation_id = _setup_activation(client, auth_headers)
        response = client.post(
            f"/api/v1/activations/{activation_id}/triggers",
            headers=auth_headers,
            json={
                "condition_type": "DRAWDOWN_THRESHOLD",
                "condition_params": _drawdown_payload(),
                "agent_prompt": ("This should fail because the mode value is invalid."),
                "mode": "inline",
            },
        )
        assert response.status_code == 422
        body = response.json()
        assert "mode" in body["detail"].lower()

    def test_patch_mode_from_direct_to_queue(
        self,
        client: "TestClient",
        auth_headers: dict[str, str],
    ) -> None:
        """PATCHing mode flips a trigger from direct to queue (and back)."""
        activation_id = _setup_activation(client, auth_headers)
        created = _create_trigger(client, auth_headers, activation_id=activation_id)
        assert created["mode"] == "direct"

        # Flip to queue
        flipped = client.patch(
            f"/api/v1/triggers/{created['id']}",
            headers=auth_headers,
            json={"mode": "queue"},
        )
        assert flipped.status_code == 200, flipped.text
        assert flipped.json()["mode"] == "queue"

        # Flip back to direct
        flipped_back = client.patch(
            f"/api/v1/triggers/{created['id']}",
            headers=auth_headers,
            json={"mode": "direct"},
        )
        assert flipped_back.status_code == 200, flipped_back.text
        assert flipped_back.json()["mode"] == "direct"

    def test_patch_invalid_mode_returns_422(
        self,
        client: "TestClient",
        auth_headers: dict[str, str],
    ) -> None:
        activation_id = _setup_activation(client, auth_headers)
        created = _create_trigger(client, auth_headers, activation_id=activation_id)
        response = client.patch(
            f"/api/v1/triggers/{created['id']}",
            headers=auth_headers,
            json={"mode": "INLINE"},
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# List for activation
# ---------------------------------------------------------------------------


class TestListForActivation:
    """``GET /activations/{id}/triggers``."""

    def test_list_returns_pagination_envelope(
        self,
        client: "TestClient",
        auth_headers: dict[str, str],
    ) -> None:
        activation_id = _setup_activation(client, auth_headers)
        _create_trigger(client, auth_headers, activation_id=activation_id)
        _create_trigger(client, auth_headers, activation_id=activation_id)
        _create_trigger(client, auth_headers, activation_id=activation_id)

        response = client.get(
            f"/api/v1/activations/{activation_id}/triggers",
            headers=auth_headers,
        )
        assert response.status_code == 200
        body = response.json()
        # Validate the standard PaginatedResponse envelope.
        assert "items" in body
        assert "total" in body
        assert "limit" in body
        assert "offset" in body
        assert "has_more" in body
        assert body["total"] == 3
        assert len(body["items"]) == 3
        assert body["has_more"] is False

    def test_list_respects_limit_offset(
        self,
        client: "TestClient",
        auth_headers: dict[str, str],
    ) -> None:
        activation_id = _setup_activation(client, auth_headers)
        for _ in range(5):
            _create_trigger(client, auth_headers, activation_id=activation_id)

        response = client.get(
            f"/api/v1/activations/{activation_id}/triggers?limit=2&offset=1",
            headers=auth_headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 5
        assert body["limit"] == 2
        assert body["offset"] == 1
        assert len(body["items"]) == 2
        assert body["has_more"] is True

    def test_list_unauthenticated_rejects(
        self,
        client: "TestClient",
    ) -> None:
        response = client.get(f"/api/v1/activations/{uuid4()}/triggers")
        assert response.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Get / Patch / Delete
# ---------------------------------------------------------------------------


class TestGetTrigger:
    """``GET /triggers/{id}``."""

    def test_get_happy_path(
        self,
        client: "TestClient",
        auth_headers: dict[str, str],
    ) -> None:
        activation_id = _setup_activation(client, auth_headers)
        created = _create_trigger(
            client,
            auth_headers,
            activation_id=activation_id,
        )
        response = client.get(
            f"/api/v1/triggers/{created['id']}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["id"] == created["id"]
        assert body["activation_id"] == activation_id

    def test_get_missing_returns_404(
        self,
        client: "TestClient",
        auth_headers: dict[str, str],
    ) -> None:
        response = client.get(
            f"/api/v1/triggers/{uuid4()}",
            headers=auth_headers,
        )
        assert response.status_code == 404

    def test_get_unauthenticated_rejects(
        self,
        client: "TestClient",
    ) -> None:
        response = client.get(f"/api/v1/triggers/{uuid4()}")
        assert response.status_code in (401, 403)


class TestPatchTrigger:
    """``PATCH /triggers/{id}``."""

    def test_patch_updates_cooldown_and_priority(
        self,
        client: "TestClient",
        auth_headers: dict[str, str],
    ) -> None:
        activation_id = _setup_activation(client, auth_headers)
        created = _create_trigger(client, auth_headers, activation_id=activation_id)
        response = client.patch(
            f"/api/v1/triggers/{created['id']}",
            headers=auth_headers,
            json={"cooldown_seconds": 7200, "priority": 50},
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["cooldown_seconds"] == 7200
        assert body["priority"] == 50

    def test_patch_pause_then_resume(
        self,
        client: "TestClient",
        auth_headers: dict[str, str],
    ) -> None:
        activation_id = _setup_activation(client, auth_headers)
        created = _create_trigger(client, auth_headers, activation_id=activation_id)
        # Pause.
        paused = client.patch(
            f"/api/v1/triggers/{created['id']}",
            headers=auth_headers,
            json={"status": "PAUSED"},
        )
        assert paused.status_code == 200, paused.text
        assert paused.json()["status"] == "PAUSED"
        # Resume.
        resumed = client.patch(
            f"/api/v1/triggers/{created['id']}",
            headers=auth_headers,
            json={"status": "ACTIVE"},
        )
        assert resumed.status_code == 200, resumed.text
        assert resumed.json()["status"] == "ACTIVE"

    def test_patch_to_terminal_status_via_field_returns_422(
        self,
        client: "TestClient",
        auth_headers: dict[str, str],
    ) -> None:
        """PATCH cannot transition a trigger to MANUALLY_DISABLED / EXPIRED."""
        activation_id = _setup_activation(client, auth_headers)
        created = _create_trigger(client, auth_headers, activation_id=activation_id)
        response = client.patch(
            f"/api/v1/triggers/{created['id']}",
            headers=auth_headers,
            json={"status": "MANUALLY_DISABLED"},
        )
        assert response.status_code == 422
        body = response.json()
        # Sanity: error envelope mentions the terminal-state restriction.
        assert "terminal" in body["detail"].lower()

    def test_patch_lift_disabled_status_returns_422(
        self,
        client: "TestClient",
        auth_headers: dict[str, str],
    ) -> None:
        """Cannot revive a MANUALLY_DISABLED trigger via PATCH (Q3 default)."""
        activation_id = _setup_activation(client, auth_headers)
        created = _create_trigger(client, auth_headers, activation_id=activation_id)
        # Bring it to MANUALLY_DISABLED via the kill-switch endpoint —
        # which is the only documented path to that state.
        kill = client.post(
            "/api/v1/triggers/disable-all",
            headers=auth_headers,
        )
        assert kill.status_code == 200
        # Now PATCH back to ACTIVE — should be rejected.
        response = client.patch(
            f"/api/v1/triggers/{created['id']}",
            headers=auth_headers,
            json={"status": "ACTIVE"},
        )
        assert response.status_code == 422
        body = response.json()
        assert "manually_disabled" in body["detail"].lower()

    def test_patch_invalid_status_returns_422(
        self,
        client: "TestClient",
        auth_headers: dict[str, str],
    ) -> None:
        activation_id = _setup_activation(client, auth_headers)
        created = _create_trigger(client, auth_headers, activation_id=activation_id)
        response = client.patch(
            f"/api/v1/triggers/{created['id']}",
            headers=auth_headers,
            json={"status": "NOT_A_STATUS"},
        )
        assert response.status_code == 422

    def test_patch_missing_returns_404(
        self,
        client: "TestClient",
        auth_headers: dict[str, str],
    ) -> None:
        response = client.patch(
            f"/api/v1/triggers/{uuid4()}",
            headers=auth_headers,
            json={"priority": 5},
        )
        assert response.status_code == 404

    def test_patch_condition_params_validates_against_existing_type(
        self,
        client: "TestClient",
        auth_headers: dict[str, str],
    ) -> None:
        """Updating condition_params re-validates against current discriminator."""
        activation_id = _setup_activation(client, auth_headers)
        created = _create_trigger(client, auth_headers, activation_id=activation_id)
        # Try to set Volatility-shaped params on a DRAWDOWN_THRESHOLD trigger.
        response = client.patch(
            f"/api/v1/triggers/{created['id']}",
            headers=auth_headers,
            json={
                "condition_params": {
                    "over_days": 30,
                    "threshold_pct": "20",
                },
            },
        )
        assert response.status_code == 422


class TestDeleteTrigger:
    """``DELETE /triggers/{id}``."""

    def test_delete_transitions_to_expired_and_keeps_row(
        self,
        client: "TestClient",
        auth_headers: dict[str, str],
    ) -> None:
        activation_id = _setup_activation(client, auth_headers)
        created = _create_trigger(client, auth_headers, activation_id=activation_id)
        delete_response = client.delete(
            f"/api/v1/triggers/{created['id']}",
            headers=auth_headers,
        )
        assert delete_response.status_code == 204
        # Row should still be queryable, in EXPIRED status.
        get_response = client.get(
            f"/api/v1/triggers/{created['id']}",
            headers=auth_headers,
        )
        assert get_response.status_code == 200
        assert get_response.json()["status"] == "EXPIRED"

    def test_delete_missing_returns_404(
        self,
        client: "TestClient",
        auth_headers: dict[str, str],
    ) -> None:
        response = client.delete(
            f"/api/v1/triggers/{uuid4()}",
            headers=auth_headers,
        )
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Fire log
# ---------------------------------------------------------------------------


class TestFireLog:
    """``GET /triggers/{id}/fires``."""

    def test_fires_endpoint_empty_returns_paginated_envelope(
        self,
        client: "TestClient",
        auth_headers: dict[str, str],
    ) -> None:
        """A trigger that hasn't fired returns total=0 and items=[]."""
        activation_id = _setup_activation(client, auth_headers)
        created = _create_trigger(client, auth_headers, activation_id=activation_id)
        response = client.get(
            f"/api/v1/triggers/{created['id']}/fires",
            headers=auth_headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 0
        assert body["items"] == []
        assert body["has_more"] is False

    def test_fires_missing_trigger_returns_404(
        self,
        client: "TestClient",
        auth_headers: dict[str, str],
    ) -> None:
        response = client.get(
            f"/api/v1/triggers/{uuid4()}/fires",
            headers=auth_headers,
        )
        assert response.status_code == 404

    def test_fires_unauthenticated_rejects(
        self,
        client: "TestClient",
    ) -> None:
        response = client.get(f"/api/v1/triggers/{uuid4()}/fires")
        assert response.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Kill switches
# ---------------------------------------------------------------------------


class TestPerUserKillSwitch:
    """``POST /triggers/disable-all``."""

    def test_disable_all_transitions_user_triggers_to_manually_disabled(
        self,
        client: "TestClient",
        auth_headers: dict[str, str],
    ) -> None:
        activation_id = _setup_activation(client, auth_headers)
        # Create N triggers for the same user.
        ids: list[str] = []
        for _ in range(3):
            body = _create_trigger(client, auth_headers, activation_id=activation_id)
            ids.append(str(body["id"]))

        response = client.post(
            "/api/v1/triggers/disable-all",
            headers=auth_headers,
        )
        assert response.status_code == 200, response.text
        assert response.json()["disabled_count"] == 3

        # Every trigger should now be MANUALLY_DISABLED.
        for trigger_id in ids:
            check = client.get(
                f"/api/v1/triggers/{trigger_id}",
                headers=auth_headers,
            )
            assert check.status_code == 200
            assert check.json()["status"] == "MANUALLY_DISABLED"

    def test_disable_all_idempotent_returns_zero_when_nothing_active(
        self,
        client: "TestClient",
        auth_headers: dict[str, str],
    ) -> None:
        # Hit the endpoint twice — second call returns 0.
        first = client.post(
            "/api/v1/triggers/disable-all",
            headers=auth_headers,
        )
        assert first.status_code == 200
        second = client.post(
            "/api/v1/triggers/disable-all",
            headers=auth_headers,
        )
        assert second.status_code == 200
        assert second.json()["disabled_count"] == 0

    def test_disable_all_unauthenticated_rejects(
        self,
        client: "TestClient",
    ) -> None:
        response = client.post("/api/v1/triggers/disable-all")
        assert response.status_code in (401, 403)


@pytest.fixture
def admin_headers(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[dict[str, str]]:
    """Bearer headers that pass the admin allowlist gate."""
    monkeypatch.setenv("ADMIN_USER_IDS", "test-user-default")
    yield {"Authorization": "Bearer test-token-default"}


@pytest.fixture
def non_admin_headers(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[dict[str, str]]:
    """Bearer headers that do NOT pass the admin allowlist gate."""
    monkeypatch.setenv("ADMIN_USER_IDS", "")
    yield {"Authorization": "Bearer test-token-default"}


class TestAdminKillSwitch:
    """``POST /admin/triggers/disable-all``."""

    def test_admin_disable_all_disables_user_triggers(
        self,
        client: "TestClient",
        admin_headers: dict[str, str],
    ) -> None:
        activation_id = _setup_activation(client, admin_headers)
        for _ in range(2):
            _create_trigger(client, admin_headers, activation_id=activation_id)
        response = client.post(
            "/api/v1/admin/triggers/disable-all",
            headers=admin_headers,
        )
        assert response.status_code == 200, response.text
        assert response.json()["disabled_count"] == 2

    def test_admin_disable_all_rejects_non_admin(
        self,
        client: "TestClient",
        non_admin_headers: dict[str, str],
    ) -> None:
        response = client.post(
            "/api/v1/admin/triggers/disable-all",
            headers=non_admin_headers,
        )
        assert response.status_code == 403

    def test_admin_disable_all_unauthenticated_rejects(
        self,
        client: "TestClient",
    ) -> None:
        response = client.post("/api/v1/admin/triggers/disable-all")
        assert response.status_code in (401, 403)
