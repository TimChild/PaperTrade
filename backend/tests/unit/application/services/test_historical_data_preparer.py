"""Tests for HistoricalDataPreparer."""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest

from zebu.adapters.outbound.market_data.in_memory_adapter import (
    InMemoryMarketDataAdapter,
)
from zebu.application.dtos.price_point import PricePoint
from zebu.application.services.historical_data_preparer import HistoricalDataPreparer
from zebu.application.exceptions import TickerNotFoundError
from zebu.domain.exceptions import InsufficientHistoricalDataError
from zebu.domain.value_objects.money import Money
from zebu.domain.value_objects.ticker import Ticker


def _make_price_point(
    ticker: str,
    price: Decimal,
    day: date,
    interval: str = "1day",
) -> PricePoint:
    ts = datetime(day.year, day.month, day.day, 12, 0, 0, tzinfo=UTC)
    return PricePoint(
        ticker=Ticker(ticker),
        price=Money(price, "USD"),
        timestamp=ts,
        source="database",
        interval=interval,
    )


def _make_adapter_with_prices(
    ticker: str,
    start: date,
    end: date,
    price: Decimal = Decimal("100.00"),
    interval: str = "1day",
) -> InMemoryMarketDataAdapter:
    adapter = InMemoryMarketDataAdapter()
    current = start
    while current <= end:
        adapter.seed_price(_make_price_point(ticker, price, current, interval=interval))
        current += timedelta(days=1)
    return adapter


class TestHistoricalDataPreparer:
    """Tests for HistoricalDataPreparer.prepare()."""

    async def test_returns_price_map_for_single_ticker(self) -> None:
        """Returns nested dict ticker -> date -> PricePoint."""
        start = date(2024, 1, 2)
        end = date(2024, 1, 5)
        adapter = _make_adapter_with_prices("AAPL", start, end)
        preparer = HistoricalDataPreparer(market_data=adapter)

        result = await preparer.prepare(
            tickers=["AAPL"], start_date=start, end_date=end
        )

        assert "AAPL" in result
        assert start in result["AAPL"]
        assert end in result["AAPL"]

    async def test_returns_price_map_for_multiple_tickers(self) -> None:
        """Returns data for all requested tickers."""
        start = date(2024, 1, 2)
        end = date(2024, 1, 3)
        adapter = InMemoryMarketDataAdapter()
        for ticker in ["AAPL", "GOOGL"]:
            for d in [start, end]:
                adapter.seed_price(_make_price_point(ticker, Decimal("100"), d))

        preparer = HistoricalDataPreparer(market_data=adapter)
        result = await preparer.prepare(
            tickers=["AAPL", "GOOGL"], start_date=start, end_date=end
        )

        assert "AAPL" in result
        assert "GOOGL" in result

    async def test_raises_when_ticker_has_no_data(self) -> None:
        """Raises InsufficientHistoricalDataError if a ticker returns no data."""
        adapter = InMemoryMarketDataAdapter()
        adapter.seed_price(
            _make_price_point("AAPL", Decimal("100"), date(2024, 1, 2))
        )
        # GOOGL not seeded at all
        preparer = HistoricalDataPreparer(market_data=adapter)

        with pytest.raises((InsufficientHistoricalDataError, TickerNotFoundError)):
            await preparer.prepare(
                tickers=["GOOGL"],
                start_date=date(2024, 1, 2),
                end_date=date(2024, 1, 5),
            )

    async def test_warm_up_days_extends_fetch_window(self) -> None:
        """warm_up_days extends the fetch start backwards."""
        warm_up = 5
        start = date(2024, 1, 10)
        end = date(2024, 1, 15)
        effective_start = start - timedelta(days=warm_up)

        adapter = _make_adapter_with_prices("AAPL", effective_start, end)
        preparer = HistoricalDataPreparer(market_data=adapter)

        result = await preparer.prepare(
            tickers=["AAPL"],
            start_date=start,
            end_date=end,
            warm_up_days=warm_up,
        )

        assert effective_start in result["AAPL"]
