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
