"""API integration tests for the new ``agent_invocation_mode`` field.

Phase L-1 (Task #217). Asserts that:

* ``POST /api/v1/backtests`` accepts the optional ``agent_invocation_mode``
  field with values ``"none"`` / ``"mock"`` / ``"live"`` and round-trips
  them in the response.
* Default (field omitted) resolves to ``"none"``.
* Invalid mode strings surface as 422 with a clear validation envelope.
* ``GET /api/v1/backtests/{id}`` returns the persisted mode.

The L-3 wiring (actually invoking the agent on simulated trigger fires)
isn't shipped yet — this test only proves the field is stamped onto the
:class:`BacktestRun` row by the command layer and surfaces back through
the response schema.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient


def _create_buy_and_hold_strategy(
    client: TestClient,
    auth_headers: dict[str, str],
) -> dict[str, object]:
    response = client.post(
        "/api/v1/strategies",
        headers=auth_headers,
        json={
            "name": "L1 Smoke Strategy",
            "strategy_type": "BUY_AND_HOLD",
            "tickers": ["AAPL"],
            "parameters": {"allocation": {"AAPL": 1.0}},
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _run_backtest(
    client: TestClient,
    auth_headers: dict[str, str],
    strategy_id: object,
    *,
    extra_body: dict[str, object] | None = None,
) -> dict[str, object]:
    end = date.today() - timedelta(days=1)
    start = end - timedelta(days=10)
    body: dict[str, object] = {
        "strategy_id": strategy_id,
        "backtest_name": "L1 Smoke Run",
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "initial_cash": "10000.00",
    }
    if extra_body is not None:
        body.update(extra_body)
    response = client.post(
        "/api/v1/backtests",
        headers=auth_headers,
        json=body,
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.parametrize("mode", ["none", "mock", "live"])
def test_post_backtest_accepts_each_invocation_mode(
    client: TestClient,
    auth_headers: dict[str, str],
    mode: str,
) -> None:
    """``POST /backtests`` accepts each enum value; response carries it back."""
    strategy = _create_buy_and_hold_strategy(client, auth_headers)
    body = _run_backtest(
        client,
        auth_headers,
        strategy["id"],
        extra_body={"agent_invocation_mode": mode},
    )
    assert body["agent_invocation_mode"] == mode


def test_post_backtest_default_is_none(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """Omitting the field yields ``agent_invocation_mode == 'none'``."""
    strategy = _create_buy_and_hold_strategy(client, auth_headers)
    body = _run_backtest(client, auth_headers, strategy["id"])
    assert body["agent_invocation_mode"] == "none"


def test_post_backtest_invalid_mode_is_422(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """An unknown enum value fails validation cleanly."""
    strategy = _create_buy_and_hold_strategy(client, auth_headers)
    end = date.today() - timedelta(days=1)
    start = end - timedelta(days=10)
    response = client.post(
        "/api/v1/backtests",
        headers=auth_headers,
        json={
            "strategy_id": strategy["id"],
            "backtest_name": "L1 Bad Mode",
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "initial_cash": "10000.00",
            "agent_invocation_mode": "offline",
        },
    )
    assert response.status_code == 422, response.text


def test_get_backtest_returns_persisted_mode(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """Round-trip the mode through ``POST`` + ``GET``."""
    strategy = _create_buy_and_hold_strategy(client, auth_headers)
    posted = _run_backtest(
        client,
        auth_headers,
        strategy["id"],
        extra_body={"agent_invocation_mode": "live"},
    )
    backtest_id = posted["id"]

    fetched = client.get(
        f"/api/v1/backtests/{backtest_id}",
        headers=auth_headers,
    )
    assert fetched.status_code == 200, fetched.text
    assert fetched.json()["agent_invocation_mode"] == "live"


# ---------------------------------------------------------------------------
# Phase L-6 — agent_max_cost_usd / agent_temperature on the request body
# ---------------------------------------------------------------------------


def test_post_backtest_accepts_agent_max_cost_usd_when_positive(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """``agent_max_cost_usd`` is accepted as an optional Decimal field.

    The L-6 cap is plumbed to the command but not echoed on the
    response schema (per L-6's "no new column on backtest_runs"
    decision — exhaustion lives in the audit table only). The HTTP-
    layer test only proves the field is accepted by pydantic + the
    command constructor; the runtime status of the backtest depends
    on price-data seeding which is out of scope here.
    """
    strategy = _create_buy_and_hold_strategy(client, auth_headers)
    # Sufficient that the request returns 201 — that means the field
    # passed pydantic validation, the command was constructed, and the
    # executor was invoked (whether it COMPLETED or FAILED depends on
    # whether price data is available for the test date range).
    body = _run_backtest(
        client,
        auth_headers,
        strategy["id"],
        extra_body={
            "agent_invocation_mode": "mock",
            "agent_max_cost_usd": "1.00",
        },
    )
    # _run_backtest already asserts status_code == 201; the run's
    # COMPLETED/FAILED status isn't the point of this test.
    assert "id" in body


def test_post_backtest_rejects_zero_agent_max_cost_usd(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """``agent_max_cost_usd=0`` is rejected at the pydantic ``gt=0`` boundary."""
    strategy = _create_buy_and_hold_strategy(client, auth_headers)
    end = date.today() - timedelta(days=1)
    start = end - timedelta(days=10)
    response = client.post(
        "/api/v1/backtests",
        headers=auth_headers,
        json={
            "strategy_id": strategy["id"],
            "backtest_name": "L6 Bad Cap",
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "initial_cash": "10000.00",
            "agent_invocation_mode": "mock",
            "agent_max_cost_usd": "0",
        },
    )
    assert response.status_code == 422, response.text


def test_post_backtest_rejects_negative_agent_max_cost_usd(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """Negative budget caps are rejected as well."""
    strategy = _create_buy_and_hold_strategy(client, auth_headers)
    end = date.today() - timedelta(days=1)
    start = end - timedelta(days=10)
    response = client.post(
        "/api/v1/backtests",
        headers=auth_headers,
        json={
            "strategy_id": strategy["id"],
            "backtest_name": "L6 Negative Cap",
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "initial_cash": "10000.00",
            "agent_invocation_mode": "mock",
            "agent_max_cost_usd": "-1.00",
        },
    )
    assert response.status_code == 422, response.text


def test_post_backtest_accepts_agent_temperature(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """``agent_temperature`` is accepted as an optional float field.

    Same scope as the cap test — the field flows through pydantic +
    the command without rejection; runtime status is out of scope.
    """
    strategy = _create_buy_and_hold_strategy(client, auth_headers)
    body = _run_backtest(
        client,
        auth_headers,
        strategy["id"],
        extra_body={
            "agent_invocation_mode": "mock",
            "agent_temperature": 0.5,
        },
    )
    # The temperature flows through to the command + factory but is
    # not echoed on the response (ignored by mock port).
    assert "id" in body
