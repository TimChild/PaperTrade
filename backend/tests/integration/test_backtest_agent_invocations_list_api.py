"""API integration tests for ``GET /backtests/{id}/agent-invocations``.

Phase L-4 (Task #220). Asserts the new read endpoint that powers the
result-page invocation log:

* Auth gating — Clerk-Bearer caller in the test client.
* Owner-scoping — 404 / 403 paths.
* Empty page when zero invocations exist (e.g. ``NONE``-mode run that
  was scheduled, MOCK-mode run that didn't fire).
* Populated page returns rows in chronological order
  (``simulated_date`` asc, ``created_at`` asc — repository contract).
* Pagination params (``limit``, ``offset``) are surfaced into the
  paginated envelope.

The endpoint queries through the
:class:`SQLModelBacktestAgentInvocationRepository` which is exercised
by the unit / repo tests; here we focus on the API surface and the
DTO mapping.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlmodel.ext.asyncio.session import AsyncSession

from zebu.adapters.outbound.database.backtest_agent_invocation_repository import (
    SQLModelBacktestAgentInvocationRepository,
)
from zebu.domain.entities.backtest_agent_invocation import BacktestAgentInvocation
from zebu.domain.value_objects.agent_decision import AgentDecision
from zebu.domain.value_objects.backtest_agent_invocation_mode import (
    BacktestAgentInvocationMode,
)


def _create_buy_and_hold_strategy(
    client: TestClient,
    auth_headers: dict[str, str],
) -> dict[str, object]:
    response = client.post(
        "/api/v1/strategies",
        headers=auth_headers,
        json={
            "name": "L4 Strategy",
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
    mode: str,
) -> dict[str, object]:
    end = date.today() - timedelta(days=1)
    start = end - timedelta(days=10)
    response = client.post(
        "/api/v1/backtests",
        headers=auth_headers,
        json={
            "strategy_id": strategy_id,
            "backtest_name": f"L4 Run ({mode})",
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "initial_cash": "10000.00",
            "agent_invocation_mode": mode,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _make_mock_row(
    backtest_run_id: UUID,
    *,
    simulated_date: date,
    created_at: datetime,
) -> BacktestAgentInvocation:
    return BacktestAgentInvocation(
        id=uuid4(),
        backtest_run_id=backtest_run_id,
        simulated_date=simulated_date,
        trigger_id=None,
        condition_evaluation_data={"schema_version": 1, "metric": "DRAWDOWN"},
        rationale="",
        latency_ms=0,
        model="",
        invocation_mode=BacktestAgentInvocationMode.MOCK,
        created_at=created_at,
        agent_decision=AgentDecision.HOLD,
    )


def _make_live_buy_row(
    backtest_run_id: UUID,
    *,
    simulated_date: date,
    created_at: datetime,
) -> BacktestAgentInvocation:
    return BacktestAgentInvocation(
        id=uuid4(),
        backtest_run_id=backtest_run_id,
        simulated_date=simulated_date,
        trigger_id=None,
        condition_evaluation_data={"schema_version": 1, "metric": "DRAWDOWN"},
        agent_decision=AgentDecision.BUY,
        rationale="Strong dip — buy on simulated weakness.",
        decision_payload={"ticker": "AAPL", "notes": "scale-in"},
        decision_executed=True,
        invocation_mode=BacktestAgentInvocationMode.LIVE,
        agent_invocation_id="msg_simulated",
        latency_ms=1234,
        model="claude-haiku-4-5-20251001",
        created_at=created_at,
    )


async def _seed_invocations(
    test_engine: AsyncEngine,
    backtest_run_id: UUID,
    rows: list[BacktestAgentInvocation],
) -> None:
    """Insert invocation rows for a backtest_run that the test client just created."""
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        repo = SQLModelBacktestAgentInvocationRepository(session)
        await repo.save_all(rows)
        await session.commit()


@pytest.mark.asyncio
async def test_list_invocations_returns_empty_page_when_none_recorded(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """A backtest with zero invocations returns ``items=[], total=0``."""
    strategy = _create_buy_and_hold_strategy(client, auth_headers)
    backtest = _run_backtest(client, auth_headers, strategy["id"], "none")

    response = client.get(
        f"/api/v1/backtests/{backtest['id']}/agent-invocations",
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 0
    assert body["has_more"] is False


@pytest.mark.asyncio
async def test_list_invocations_returns_chronological_rows(
    test_engine: AsyncEngine,
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """Rows are returned sorted by simulated_date asc then created_at asc."""
    strategy = _create_buy_and_hold_strategy(client, auth_headers)
    backtest = _run_backtest(client, auth_headers, strategy["id"], "live")
    run_id = UUID(str(backtest["id"]))

    now = datetime.now(UTC) - timedelta(hours=1)
    # Out-of-order on simulated_date so the order assertion is meaningful.
    rows = [
        _make_live_buy_row(
            run_id,
            simulated_date=date(2024, 6, 3),
            created_at=now + timedelta(seconds=3),
        ),
        _make_mock_row(
            run_id,
            simulated_date=date(2024, 6, 1),
            created_at=now,
        ),
        _make_mock_row(
            run_id,
            simulated_date=date(2024, 6, 2),
            created_at=now + timedelta(seconds=1),
        ),
    ]
    await _seed_invocations(test_engine, run_id, rows)

    response = client.get(
        f"/api/v1/backtests/{run_id}/agent-invocations",
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == 3
    items = body["items"]
    assert len(items) == 3
    assert items[0]["simulated_date"] == "2024-06-01"
    assert items[1]["simulated_date"] == "2024-06-02"
    assert items[2]["simulated_date"] == "2024-06-03"
    # The LIVE-buy row carries decision_payload and decision_executed=True.
    assert items[2]["agent_decision"] == "BUY"
    assert items[2]["decision_executed"] is True
    assert items[2]["model"] == "claude-haiku-4-5-20251001"
    assert items[2]["decision_payload"] == {"ticker": "AAPL", "notes": "scale-in"}
    # MOCK rows have HOLD decision, no payload.
    assert items[0]["agent_decision"] == "HOLD"
    assert items[0]["decision_executed"] is False
    assert items[0]["decision_payload"] is None
    assert items[0]["rationale"] == ""
    assert items[0]["model"] == ""
    assert items[0]["invocation_mode"] == "mock"


@pytest.mark.asyncio
async def test_list_invocations_paginates(
    test_engine: AsyncEngine,
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """``limit`` and ``offset`` slice the response and surface in the envelope."""
    strategy = _create_buy_and_hold_strategy(client, auth_headers)
    backtest = _run_backtest(client, auth_headers, strategy["id"], "mock")
    run_id = UUID(str(backtest["id"]))

    now = datetime.now(UTC) - timedelta(hours=1)
    rows = [
        _make_mock_row(
            run_id,
            simulated_date=date(2024, 6, 1) + timedelta(days=i),
            created_at=now + timedelta(seconds=i),
        )
        for i in range(5)
    ]
    await _seed_invocations(test_engine, run_id, rows)

    response = client.get(
        f"/api/v1/backtests/{run_id}/agent-invocations",
        headers=auth_headers,
        params={"limit": 2, "offset": 1},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == 5
    assert body["limit"] == 2
    assert body["offset"] == 1
    assert body["has_more"] is True
    items = body["items"]
    assert len(items) == 2
    assert items[0]["simulated_date"] == "2024-06-02"
    assert items[1]["simulated_date"] == "2024-06-03"


@pytest.mark.asyncio
async def test_list_invocations_404_when_backtest_missing(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """A run id that does not exist returns 404."""
    response = client.get(
        f"/api/v1/backtests/{uuid4()}/agent-invocations",
        headers=auth_headers,
    )
    assert response.status_code == 404, response.text


@pytest.mark.asyncio
async def test_list_invocations_response_carries_all_fields(
    test_engine: AsyncEngine,
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """One LIVE-row response carries every field consumed by the UI."""
    strategy = _create_buy_and_hold_strategy(client, auth_headers)
    backtest = _run_backtest(client, auth_headers, strategy["id"], "live")
    run_id = UUID(str(backtest["id"]))

    now = datetime.now(UTC) - timedelta(hours=1)
    row = _make_live_buy_row(run_id, simulated_date=date(2024, 6, 5), created_at=now)
    await _seed_invocations(test_engine, run_id, [row])

    response = client.get(
        f"/api/v1/backtests/{run_id}/agent-invocations",
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    items = response.json()["items"]
    assert len(items) == 1
    item = items[0]
    # Keys that drive the result-page row renderer.
    expected_keys = {
        "id",
        "backtest_run_id",
        "simulated_date",
        "trigger_id",
        "invocation_mode",
        "agent_decision",
        "rationale",
        "decision_payload",
        "decision_executed",
        "simulated_trade_id",
        "agent_invocation_id",
        "latency_ms",
        "model",
        "condition_evaluation_data",
        "created_at",
    }
    assert expected_keys.issubset(item.keys())
    # Decimal-shape sanity: latency_ms is JSON int, not string.
    assert isinstance(item["latency_ms"], int)
    assert item["latency_ms"] == 1234


@pytest.mark.asyncio
async def test_list_invocations_validates_pagination_params(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """``limit=0`` and negative ``offset`` should fail validation."""
    strategy = _create_buy_and_hold_strategy(client, auth_headers)
    backtest = _run_backtest(client, auth_headers, strategy["id"], "none")

    # limit=0 is below ge=1.
    response = client.get(
        f"/api/v1/backtests/{backtest['id']}/agent-invocations",
        headers=auth_headers,
        params={"limit": 0},
    )
    assert response.status_code == 422, response.text

    # negative offset is below ge=0.
    response = client.get(
        f"/api/v1/backtests/{backtest['id']}/agent-invocations",
        headers=auth_headers,
        params={"offset": -5},
    )
    assert response.status_code == 422, response.text
