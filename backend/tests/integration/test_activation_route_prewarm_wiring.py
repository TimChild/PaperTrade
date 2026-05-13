"""Integration test for the activate route's prewarm scheduling.

Phase J / Task #212 Layer 2.

We test the wiring rather than the full background task because:

* The TestClient runs the FastAPI app inside a thread with its own event
  loop; the background ``asyncio.create_task`` lives on that loop and
  any DB writes it makes are not synchronously visible from the test
  thread without elaborate cross-loop synchronisation.
* The prewarmer itself, the SQL adapter, and the drain helper all have
  dedicated integration tests against the same SQLite engine — that
  chain pins the behaviour end-to-end.

What we verify here:

* :func:`_required_warmup_window` returns sensible windows for the three
  supported strategy types (the helper the route uses to compute
  ``start_date``/``end_date``).
* :func:`_resolve_prewarm_priority` reads ``PREWARM_DEFAULT_PRIORITY``
  from the env and falls back to LOW on unrecognised values.
* The activate route returns 201 — covered by existing tests in
  ``test_strategy_activations_api.py``. We just re-pin one happy-path
  call here to catch regressions where ``_schedule_prewarm`` raises
  synchronously (which would 500 the request).
"""

from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest

from zebu.adapters.inbound.api.strategy_activations import (
    _required_warmup_window,
    _resolve_prewarm_priority,
)
from zebu.domain.entities.strategy import Strategy
from zebu.domain.value_objects.backfill_priority import BackfillPriority
from zebu.domain.value_objects.strategy_parameters import (
    BuyAndHoldParameters,
    DcaParameters,
    MaCrossoverParameters,
)
from zebu.domain.value_objects.strategy_type import StrategyType

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


class TestRequiredWarmupWindow:
    """Unit-style coverage of the strategy → ``(start, end)`` helper."""

    def test_buy_and_hold_uses_five_year_default(self) -> None:
        strategy = Strategy(
            id=uuid4(),
            user_id=uuid4(),
            name="AAPL Buy and Hold",
            strategy_type=StrategyType.BUY_AND_HOLD,
            tickers=["AAPL"],
            parameters=BuyAndHoldParameters(allocation={"AAPL": Decimal("1.0")}),
            created_at=datetime.now(UTC),
        )
        start, end = _required_warmup_window(strategy)
        assert end == datetime.now(UTC).date()
        # 5 years ≈ 1825 days; allow a couple of days slack for
        # day-boundary timing.
        delta = (end - start).days
        assert 1820 <= delta <= 1830

    def test_dca_uses_frequency_plus_buffer(self) -> None:
        strategy = Strategy(
            id=uuid4(),
            user_id=uuid4(),
            name="DCA AAPL",
            strategy_type=StrategyType.DOLLAR_COST_AVERAGING,
            tickers=["AAPL"],
            parameters=DcaParameters(
                frequency_days=7,
                amount_per_period=Decimal("100"),
                allocation={"AAPL": Decimal("1.0")},
            ),
            created_at=datetime.now(UTC),
        )
        start, end = _required_warmup_window(strategy)
        # 7 days frequency + 30 buffer = 37 days.
        delta = (end - start).days
        assert delta == 37

    def test_ma_crossover_uses_indicator_window_plus_buffer(self) -> None:
        strategy = Strategy(
            id=uuid4(),
            user_id=uuid4(),
            name="MA AAPL",
            strategy_type=StrategyType.MOVING_AVERAGE_CROSSOVER,
            tickers=["AAPL"],
            parameters=MaCrossoverParameters(
                fast_window=5,
                slow_window=20,
                invest_fraction=Decimal("0.5"),
            ),
            created_at=datetime.now(UTC),
        )
        start, end = _required_warmup_window(strategy)
        # 20 trading days × 365 / 252 ≈ 28 calendar days + 1 rounding +
        # 30 buffer = ~59 days. Allow a small slack.
        delta = (end - start).days
        assert 55 <= delta <= 65


class TestResolvePrewarmPriority:
    """``PREWARM_DEFAULT_PRIORITY`` env knob."""

    def test_default_is_low(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("PREWARM_DEFAULT_PRIORITY", raising=False)
        assert _resolve_prewarm_priority() is BackfillPriority.LOW

    def test_high_is_respected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PREWARM_DEFAULT_PRIORITY", "high")
        assert _resolve_prewarm_priority() is BackfillPriority.HIGH

    def test_unknown_falls_back_to_low(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PREWARM_DEFAULT_PRIORITY", "ultra")
        assert _resolve_prewarm_priority() is BackfillPriority.LOW


class TestActivateRouteStillReturns201:
    """Activation route remains 201 even with the prewarm scheduler in line."""

    def test_activate_returns_201(
        self,
        client: "TestClient",
        auth_headers: dict[str, str],
    ) -> None:
        # Create portfolio.
        response = client.post(
            "/api/v1/portfolios",
            headers=auth_headers,
            json={
                "name": "P",
                "initial_deposit": "10000.00",
                "currency": "USD",
            },
        )
        assert response.status_code == 201, response.text
        portfolio_id = response.json()["portfolio_id"]

        # Create strategy.
        response = client.post(
            "/api/v1/strategies",
            headers=auth_headers,
            json={
                "name": "S",
                "strategy_type": "BUY_AND_HOLD",
                "tickers": ["AAPL"],
                "parameters": {"allocation": {"AAPL": 1.0}},
            },
        )
        assert response.status_code == 201, response.text
        strategy_id = response.json()["id"]

        # Activate — must still 201 even though _schedule_prewarm runs
        # before the response.
        response = client.post(
            f"/api/v1/strategies/{strategy_id}/activate",
            headers=auth_headers,
            json={"portfolio_id": portfolio_id},
        )
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["strategy_id"] == strategy_id
        assert body["status"] == "ACTIVE"
