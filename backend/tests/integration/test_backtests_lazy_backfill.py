"""Integration tests for the Phase J / Task #212 Layer 3 lazy-backfill flow.

These tests verify the API surface for partial-coverage backtests:

* A fresh ticker (no historical data) gets a 503 with the structured
  ``status=fetching`` body and a ``Retry-After`` header.
* Once the backfill has had a chance to run, the same backtest returns 200.
* Full-coverage tickers are unaffected.

The market-data port is overridden with an adapter that returns partial
data on the first call and full data on the second, mimicking the
real-world "first call kicks off a backfill, second call sees the
populated DB" flow.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from zebu.adapters.inbound.api.dependencies import get_market_data
from zebu.application.exceptions import IncompleteHistoricalDataError
from zebu.domain.value_objects.money import Money
from zebu.domain.value_objects.price_point import PricePoint
from zebu.domain.value_objects.strategy_type import StrategyType
from zebu.domain.value_objects.ticker import Ticker
from zebu.main import app


class _PartialThenFullAdapter:
    """Test double for :class:`MarketDataPort` simulating lazy backfill.

    The first ``get_price_history`` call for a ticker raises
    :class:`IncompleteHistoricalDataError`. Subsequent calls return a
    full set of price points spanning the requested range. Other
    methods are not used by this test suite.
    """

    def __init__(self, ticker: Ticker, raise_first_call: bool = True) -> None:
        self._ticker = ticker
        self._calls = 0
        self._raise_first_call = raise_first_call

    async def get_price_history(
        self,
        ticker: Ticker,
        start: datetime,
        end: datetime,
        interval: str = "1day",
    ) -> list[PricePoint]:
        self._calls += 1
        if self._raise_first_call and self._calls == 1:
            req_start, req_end = start.date(), end.date()
            raise IncompleteHistoricalDataError(
                ticker=ticker,
                requested_range=(req_start, req_end),
                available_range=None,
                missing_days_count=(req_end - req_start).days + 1,
            )

        # Subsequent call: return a full set spanning the range.
        points: list[PricePoint] = []
        current = start.date()
        while current <= end.date():
            if current.weekday() < 5:  # weekdays only
                ts = datetime(
                    current.year, current.month, current.day, 21, 0, 0, tzinfo=UTC
                )
                points.append(
                    PricePoint(
                        ticker=ticker,
                        price=Money(Decimal("100.00"), "USD"),
                        timestamp=ts,
                        source="alpha_vantage",
                        interval=interval,
                    )
                )
            current += timedelta(days=1)
        return points

    # The backtest executor + data preparer do not use these methods on
    # this path, but the protocol requires them.
    async def get_current_price(self, ticker: Ticker) -> PricePoint:  # pragma: no cover
        raise NotImplementedError

    async def get_batch_prices(
        self, tickers: list[Ticker]
    ) -> dict[Ticker, PricePoint]:  # pragma: no cover
        raise NotImplementedError

    async def get_price_at(
        self, ticker: Ticker, timestamp: datetime
    ) -> PricePoint:  # pragma: no cover
        raise NotImplementedError

    async def get_supported_tickers(self) -> list[Ticker]:  # pragma: no cover
        return [self._ticker]


@pytest.fixture
def default_user_uuid() -> UUID:
    """Deterministic UUID matching the conftest-seeded default user."""
    from uuid import NAMESPACE_DNS, uuid5

    return uuid5(NAMESPACE_DNS, "test-user-default")


def _seed_strategy(
    client: TestClient,
    user_id: UUID,
    ticker_symbol: str,
) -> UUID:
    """Persist a single-ticker BUY_AND_HOLD strategy via the API for the test user.

    Returns the strategy's UUID for use in the backtest request.
    """
    response = client.post(
        "/api/v1/strategies",
        json={
            "name": f"lazy-backfill-{ticker_symbol}",
            "strategy_type": StrategyType.BUY_AND_HOLD.value,
            "tickers": [ticker_symbol],
            "parameters": {"allocation": {ticker_symbol: "1.0"}},
        },
        headers={"Authorization": "Bearer test-token-default"},
    )
    assert response.status_code in (200, 201), response.text
    body = response.json()
    return UUID(body["id"])


def test_backtest_with_no_coverage_returns_503_fetching(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """First backtest of an uncovered ticker → 503 with structured body."""
    # Override the market data dependency for this test.
    partial_adapter = _PartialThenFullAdapter(ticker=Ticker("AAPL"))

    async def get_partial_adapter() -> _PartialThenFullAdapter:
        return partial_adapter

    app.dependency_overrides[get_market_data] = get_partial_adapter
    try:
        strategy_id = _seed_strategy(client, uuid4(), "AAPL")
        response = client.post(
            "/api/v1/backtests",
            json={
                "strategy_id": str(strategy_id),
                "backtest_name": "lazy-backfill",
                "start_date": "2024-01-02",
                "end_date": "2024-04-30",
                "initial_cash": "10000.00",
            },
            headers=auth_headers,
        )
    finally:
        del app.dependency_overrides[get_market_data]

    assert response.status_code == 503, response.text
    body = response.json()
    assert body["status"] == "fetching"
    assert body["ticker"] == "AAPL"
    assert body["missing_range"]["start"] == "2024-01-02"
    assert body["missing_range"]["end"] == "2024-04-30"
    assert body["eta_seconds"] == 60
    assert body["retry_after_seconds"] == 60
    assert response.headers.get("Retry-After") == "60"


def test_backtest_with_partial_coverage_returns_503_with_narrowed_range(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """Partial coverage → 503 with the missing-window narrowed to the gap."""

    class _PartialCoverageAdapter:
        """Returns a partial-coverage exception with explicit available_range."""

        async def get_price_history(
            self,
            ticker: Ticker,
            start: datetime,
            end: datetime,
            interval: str = "1day",
        ) -> list[PricePoint]:
            raise IncompleteHistoricalDataError(
                ticker=ticker,
                requested_range=(date(2024, 1, 2), date(2024, 4, 30)),
                available_range=(date(2024, 3, 1), date(2024, 4, 30)),
                missing_days_count=58,
            )

        async def get_current_price(
            self, ticker: Ticker
        ) -> PricePoint:  # pragma: no cover
            raise NotImplementedError

        async def get_batch_prices(
            self, tickers: list[Ticker]
        ) -> dict[Ticker, PricePoint]:  # pragma: no cover
            raise NotImplementedError

        async def get_price_at(
            self, ticker: Ticker, timestamp: datetime
        ) -> PricePoint:  # pragma: no cover
            raise NotImplementedError

        async def get_supported_tickers(
            self,
        ) -> list[Ticker]:  # pragma: no cover
            return [Ticker("AAPL")]

    async def get_partial_adapter() -> _PartialCoverageAdapter:
        return _PartialCoverageAdapter()

    app.dependency_overrides[get_market_data] = get_partial_adapter
    try:
        strategy_id = _seed_strategy(client, uuid4(), "AAPL")
        response = client.post(
            "/api/v1/backtests",
            json={
                "strategy_id": str(strategy_id),
                "backtest_name": "lazy-backfill-partial",
                "start_date": "2024-01-02",
                "end_date": "2024-04-30",
                "initial_cash": "10000.00",
            },
            headers=auth_headers,
        )
    finally:
        del app.dependency_overrides[get_market_data]

    assert response.status_code == 503, response.text
    body = response.json()
    assert body["status"] == "fetching"
    assert body["ticker"] == "AAPL"
    # Head gap: 2024-01-02 to 2024-02-29 (= 2024-03-01 - 1 day)
    assert body["missing_range"]["start"] == "2024-01-02"
    assert body["missing_range"]["end"] == "2024-02-29"


def test_backtest_with_full_coverage_returns_200(
    client: TestClient,
    auth_headers: dict[str, str],
    default_user_uuid: UUID,
) -> None:
    """Full coverage → backtest proceeds, 201 with the run details."""
    # No partial adapter — use the default conftest-seeded in-memory
    # market data adapter, then seed the AAPL daily price points the
    # backtest needs across the requested window.
    from zebu.adapters.outbound.market_data.in_memory_adapter import (
        InMemoryMarketDataAdapter,
    )

    adapter = InMemoryMarketDataAdapter()

    # Seed daily prices for Jan 2 - Jan 12, 2024 (10 weekdays).
    current = date(2024, 1, 2)
    end = date(2024, 1, 12)
    while current <= end:
        ts = datetime(current.year, current.month, current.day, 21, 0, 0, tzinfo=UTC)
        adapter.seed_price(
            PricePoint(
                ticker=Ticker("AAPL"),
                price=Money(Decimal("100.00"), "USD"),
                timestamp=ts,
                source="alpha_vantage",
                interval="1day",
            )
        )
        current += timedelta(days=1)

    async def get_full_adapter() -> InMemoryMarketDataAdapter:
        return adapter

    app.dependency_overrides[get_market_data] = get_full_adapter
    try:
        strategy_id = _seed_strategy(client, default_user_uuid, "AAPL")
        response = client.post(
            "/api/v1/backtests",
            json={
                "strategy_id": str(strategy_id),
                "backtest_name": "full-coverage",
                "start_date": "2024-01-02",
                "end_date": "2024-01-12",
                "initial_cash": "10000.00",
            },
            headers=auth_headers,
        )
    finally:
        del app.dependency_overrides[get_market_data]

    # Should not be 503 — the data was fully available.
    # Acceptable: 201 (created) or any non-503 success outcome.
    assert response.status_code != 503, response.text
    # And specifically: when complete, FastAPI returns 201 for the
    # @router.post(..., status_code=201) decorator.
    assert response.status_code == 201, response.text


def test_backtest_503_fetching_then_200_after_data_lands(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """First call → 503 fetching. Second call (data now available) → 201."""
    partial_adapter = _PartialThenFullAdapter(ticker=Ticker("AAPL"))

    async def get_partial_adapter() -> _PartialThenFullAdapter:
        return partial_adapter

    app.dependency_overrides[get_market_data] = get_partial_adapter
    try:
        strategy_id = _seed_strategy(client, uuid4(), "AAPL")

        first = client.post(
            "/api/v1/backtests",
            json={
                "strategy_id": str(strategy_id),
                "backtest_name": "lazy-1",
                "start_date": "2024-01-02",
                "end_date": "2024-01-12",
                "initial_cash": "10000.00",
            },
            headers=auth_headers,
        )
        assert first.status_code == 503

        # Second call — adapter now returns full data.
        second = client.post(
            "/api/v1/backtests",
            json={
                "strategy_id": str(strategy_id),
                "backtest_name": "lazy-2",
                "start_date": "2024-01-02",
                "end_date": "2024-01-12",
                "initial_cash": "10000.00",
            },
            headers=auth_headers,
        )
        # Should now succeed.
        assert second.status_code == 201, second.text
    finally:
        del app.dependency_overrides[get_market_data]
