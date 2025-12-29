"""Tests for MarketDataPort protocol and InMemoryMarketDataAdapter."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from papertrade.adapters.outbound.market_data.in_memory_adapter import (
    InMemoryMarketDataAdapter,
)
from papertrade.application.dtos.price_point import PricePoint
from papertrade.application.exceptions import (
    MarketDataUnavailableError,
    TickerNotFoundError,
)
from papertrade.application.ports.market_data_port import MarketDataPort
from papertrade.domain.value_objects.money import Money
from papertrade.domain.value_objects.ticker import Ticker


class TestMarketDataPortProtocolCompliance:
    """Tests that InMemoryMarketDataAdapter implements MarketDataPort."""

    def test_implements_protocol(self) -> None:
        """Should implement MarketDataPort protocol."""
        adapter = InMemoryMarketDataAdapter()

        # Check that it has all required methods
        assert hasattr(adapter, "get_current_price")
        assert hasattr(adapter, "get_price_at")
        assert hasattr(adapter, "get_price_history")
        assert hasattr(adapter, "get_supported_tickers")

        # Check methods are callable
        assert callable(adapter.get_current_price)
        assert callable(adapter.get_price_at)
        assert callable(adapter.get_price_history)
        assert callable(adapter.get_supported_tickers)


class TestInMemoryMarketDataAdapterSeeding:
    """Tests for seeding data into InMemoryMarketDataAdapter."""

    def test_seed_single_price(self) -> None:
        """Should add single price to storage."""
        adapter = InMemoryMarketDataAdapter()
        price_point = PricePoint(
            ticker=Ticker("AAPL"),
            price=Money(Decimal("150.25"), "USD"),
            timestamp=datetime(2025, 12, 28, 14, 30, tzinfo=timezone.utc),
            source="database",
            interval="real-time",
        )

        adapter.seed_price(price_point)

        # Should have one ticker in storage
        assert "AAPL" in adapter._prices
        assert len(adapter._prices["AAPL"]) == 1
        assert adapter._prices["AAPL"][0] == price_point

    def test_seed_multiple_prices(self) -> None:
        """Should add multiple prices to storage."""
        adapter = InMemoryMarketDataAdapter()
        prices = [
            PricePoint(
                ticker=Ticker("AAPL"),
                price=Money(Decimal("150.00"), "USD"),
                timestamp=datetime(2025, 12, 28, 14, 0, tzinfo=timezone.utc),
                source="database",
                interval="real-time",
            ),
            PricePoint(
                ticker=Ticker("AAPL"),
                price=Money(Decimal("150.25"), "USD"),
                timestamp=datetime(2025, 12, 28, 14, 30, tzinfo=timezone.utc),
                source="database",
                interval="real-time",
            ),
        ]

        adapter.seed_prices(prices)

        assert len(adapter._prices["AAPL"]) == 2

    def test_seed_keeps_chronological_order(self) -> None:
        """Should keep prices sorted by timestamp."""
        adapter = InMemoryMarketDataAdapter()

        # Add prices out of order
        price2 = PricePoint(
            ticker=Ticker("AAPL"),
            price=Money(Decimal("150.50"), "USD"),
            timestamp=datetime(2025, 12, 28, 15, 0, tzinfo=timezone.utc),
            source="database",
            interval="real-time",
        )
        price1 = PricePoint(
            ticker=Ticker("AAPL"),
            price=Money(Decimal("150.00"), "USD"),
            timestamp=datetime(2025, 12, 28, 14, 0, tzinfo=timezone.utc),
            source="database",
            interval="real-time",
        )

        adapter.seed_price(price2)  # Add later price first
        adapter.seed_price(price1)  # Add earlier price second

        # Should be sorted by timestamp
        prices = adapter._prices["AAPL"]
        assert prices[0].timestamp < prices[1].timestamp
        assert prices[0] == price1
        assert prices[1] == price2

    def test_clear(self) -> None:
        """Should remove all data."""
        adapter = InMemoryMarketDataAdapter()
        adapter.seed_price(
            PricePoint(
                ticker=Ticker("AAPL"),
                price=Money(Decimal("150.25"), "USD"),
                timestamp=datetime(2025, 12, 28, 14, 30, tzinfo=timezone.utc),
                source="database",
                interval="real-time",
            )
        )

        adapter.clear()

        assert len(adapter._prices) == 0


class TestInMemoryAdapterGetCurrentPrice:
    """Tests for get_current_price method."""

    @pytest.mark.asyncio
    async def test_get_current_price_empty_adapter(self) -> None:
        """Should raise TickerNotFoundError when no data."""
        adapter = InMemoryMarketDataAdapter()

        with pytest.raises(TickerNotFoundError) as exc_info:
            await adapter.get_current_price(Ticker("AAPL"))

        assert exc_info.value.ticker == "AAPL"

    @pytest.mark.asyncio
    async def test_get_current_price_single_price(self) -> None:
        """Should return seeded price."""
        adapter = InMemoryMarketDataAdapter()
        price_point = PricePoint(
            ticker=Ticker("AAPL"),
            price=Money(Decimal("150.25"), "USD"),
            timestamp=datetime(2025, 12, 28, 14, 30, tzinfo=timezone.utc),
            source="database",
            interval="real-time",
        )
        adapter.seed_price(price_point)

        result = await adapter.get_current_price(Ticker("AAPL"))

        assert result == price_point

    @pytest.mark.asyncio
    async def test_get_current_price_returns_most_recent(self) -> None:
        """Should return most recent price when multiple exist."""
        adapter = InMemoryMarketDataAdapter()

        older_price = PricePoint(
            ticker=Ticker("AAPL"),
            price=Money(Decimal("150.00"), "USD"),
            timestamp=datetime(2025, 12, 28, 14, 0, tzinfo=timezone.utc),
            source="database",
            interval="real-time",
        )
        newer_price = PricePoint(
            ticker=Ticker("AAPL"),
            price=Money(Decimal("150.50"), "USD"),
            timestamp=datetime(2025, 12, 28, 15, 0, tzinfo=timezone.utc),
            source="database",
            interval="real-time",
        )

        adapter.seed_prices([older_price, newer_price])

        result = await adapter.get_current_price(Ticker("AAPL"))

        assert result == newer_price


class TestInMemoryAdapterGetPriceAt:
    """Tests for get_price_at method."""

    @pytest.mark.asyncio
    async def test_get_price_at_empty_adapter(self) -> None:
        """Should raise TickerNotFoundError when no data."""
        adapter = InMemoryMarketDataAdapter()
        timestamp = datetime(2025, 12, 28, 14, 30, tzinfo=timezone.utc)

        with pytest.raises(TickerNotFoundError):
            await adapter.get_price_at(Ticker("AAPL"), timestamp)

    @pytest.mark.asyncio
    async def test_get_price_at_exact_match(self) -> None:
        """Should return exact match when available."""
        adapter = InMemoryMarketDataAdapter()
        timestamp = datetime(2025, 12, 28, 14, 30, tzinfo=timezone.utc)
        price_point = PricePoint(
            ticker=Ticker("AAPL"),
            price=Money(Decimal("150.25"), "USD"),
            timestamp=timestamp,
            source="database",
            interval="real-time",
        )
        adapter.seed_price(price_point)

        result = await adapter.get_price_at(Ticker("AAPL"), timestamp)

        assert result == price_point

    @pytest.mark.asyncio
    async def test_get_price_at_finds_closest_within_window(self) -> None:
        """Should return closest price within ±1 hour."""
        adapter = InMemoryMarketDataAdapter()

        # Price at 14:00
        price_point = PricePoint(
            ticker=Ticker("AAPL"),
            price=Money(Decimal("150.25"), "USD"),
            timestamp=datetime(2025, 12, 28, 14, 0, tzinfo=timezone.utc),
            source="database",
            interval="real-time",
        )
        adapter.seed_price(price_point)

        # Request at 14:30 (30 minutes later, within window)
        requested_time = datetime(2025, 12, 28, 14, 30, tzinfo=timezone.utc)
        result = await adapter.get_price_at(Ticker("AAPL"), requested_time)

        assert result == price_point

    @pytest.mark.asyncio
    async def test_get_price_at_outside_window(self) -> None:
        """Should raise error when no price within ±1 hour."""
        adapter = InMemoryMarketDataAdapter()

        # Price at 14:00
        price_point = PricePoint(
            ticker=Ticker("AAPL"),
            price=Money(Decimal("150.25"), "USD"),
            timestamp=datetime(2025, 12, 28, 14, 0, tzinfo=timezone.utc),
            source="database",
            interval="real-time",
        )
        adapter.seed_price(price_point)

        # Request at 16:00 (2 hours later, outside window)
        requested_time = datetime(2025, 12, 28, 16, 0, tzinfo=timezone.utc)

        with pytest.raises(MarketDataUnavailableError) as exc_info:
            await adapter.get_price_at(Ticker("AAPL"), requested_time)

        assert "within ±1 hour" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_price_at_selects_closest(self) -> None:
        """Should select closest price when multiple within window."""
        adapter = InMemoryMarketDataAdapter()

        price1 = PricePoint(
            ticker=Ticker("AAPL"),
            price=Money(Decimal("150.00"), "USD"),
            timestamp=datetime(2025, 12, 28, 14, 0, tzinfo=timezone.utc),
            source="database",
            interval="real-time",
        )
        price2 = PricePoint(
            ticker=Ticker("AAPL"),
            price=Money(Decimal("150.50"), "USD"),
            timestamp=datetime(2025, 12, 28, 14, 45, tzinfo=timezone.utc),
            source="database",
            interval="real-time",
        )

        adapter.seed_prices([price1, price2])

        # Request at 14:40 - closer to price2 (14:45)
        requested_time = datetime(2025, 12, 28, 14, 40, tzinfo=timezone.utc)
        result = await adapter.get_price_at(Ticker("AAPL"), requested_time)

        assert result == price2


class TestInMemoryAdapterGetPriceHistory:
    """Tests for get_price_history method."""

    @pytest.mark.asyncio
    async def test_get_price_history_empty_adapter(self) -> None:
        """Should raise TickerNotFoundError when ticker not in storage."""
        adapter = InMemoryMarketDataAdapter()
        start = datetime(2025, 12, 1, tzinfo=timezone.utc)
        end = datetime(2025, 12, 31, tzinfo=timezone.utc)

        with pytest.raises(TickerNotFoundError):
            await adapter.get_price_history(Ticker("AAPL"), start, end)

    @pytest.mark.asyncio
    async def test_get_price_history_end_before_start(self) -> None:
        """Should raise ValueError when end before start."""
        adapter = InMemoryMarketDataAdapter()
        adapter.seed_price(
            PricePoint(
                ticker=Ticker("AAPL"),
                price=Money(Decimal("150.25"), "USD"),
                timestamp=datetime(2025, 12, 15, tzinfo=timezone.utc),
                source="database",
                interval="1day",
            )
        )

        start = datetime(2025, 12, 31, tzinfo=timezone.utc)
        end = datetime(2025, 12, 1, tzinfo=timezone.utc)

        with pytest.raises(ValueError, match="cannot be before start"):
            await adapter.get_price_history(Ticker("AAPL"), start, end)

    @pytest.mark.asyncio
    async def test_get_price_history_returns_prices_in_range(self) -> None:
        """Should return only prices within date range."""
        adapter = InMemoryMarketDataAdapter()

        prices = [
            PricePoint(
                ticker=Ticker("AAPL"),
                price=Money(Decimal("150.00"), "USD"),
                timestamp=datetime(2025, 12, 1, tzinfo=timezone.utc),
                source="database",
                interval="1day",
            ),
            PricePoint(
                ticker=Ticker("AAPL"),
                price=Money(Decimal("151.00"), "USD"),
                timestamp=datetime(2025, 12, 15, tzinfo=timezone.utc),
                source="database",
                interval="1day",
            ),
            PricePoint(
                ticker=Ticker("AAPL"),
                price=Money(Decimal("152.00"), "USD"),
                timestamp=datetime(2025, 12, 31, tzinfo=timezone.utc),
                source="database",
                interval="1day",
            ),
        ]
        adapter.seed_prices(prices)

        # Request Dec 10 - Dec 20 (should only get middle price)
        start = datetime(2025, 12, 10, tzinfo=timezone.utc)
        end = datetime(2025, 12, 20, tzinfo=timezone.utc)
        result = await adapter.get_price_history(Ticker("AAPL"), start, end, "1day")

        assert len(result) == 1
        assert result[0] == prices[1]

    @pytest.mark.asyncio
    async def test_get_price_history_inclusive_boundaries(self) -> None:
        """Should include prices exactly at start and end."""
        adapter = InMemoryMarketDataAdapter()

        prices = [
            PricePoint(
                ticker=Ticker("AAPL"),
                price=Money(Decimal("150.00"), "USD"),
                timestamp=datetime(2025, 12, 1, tzinfo=timezone.utc),
                source="database",
                interval="1day",
            ),
            PricePoint(
                ticker=Ticker("AAPL"),
                price=Money(Decimal("152.00"), "USD"),
                timestamp=datetime(2025, 12, 31, tzinfo=timezone.utc),
                source="database",
                interval="1day",
            ),
        ]
        adapter.seed_prices(prices)

        start = datetime(2025, 12, 1, tzinfo=timezone.utc)
        end = datetime(2025, 12, 31, tzinfo=timezone.utc)
        result = await adapter.get_price_history(Ticker("AAPL"), start, end, "1day")

        assert len(result) == 2
        assert result[0] == prices[0]
        assert result[1] == prices[1]

    @pytest.mark.asyncio
    async def test_get_price_history_empty_result_not_error(self) -> None:
        """Should return empty list when no data in range."""
        adapter = InMemoryMarketDataAdapter()

        price_point = PricePoint(
            ticker=Ticker("AAPL"),
            price=Money(Decimal("150.00"), "USD"),
            timestamp=datetime(2025, 12, 1, tzinfo=timezone.utc),
            source="database",
            interval="1day",
        )
        adapter.seed_price(price_point)

        # Request range with no data
        start = datetime(2025, 11, 1, tzinfo=timezone.utc)
        end = datetime(2025, 11, 30, tzinfo=timezone.utc)
        result = await adapter.get_price_history(Ticker("AAPL"), start, end, "1day")

        assert result == []

    @pytest.mark.asyncio
    async def test_get_price_history_filters_by_interval(self) -> None:
        """Should only return prices matching requested interval."""
        adapter = InMemoryMarketDataAdapter()

        prices = [
            PricePoint(
                ticker=Ticker("AAPL"),
                price=Money(Decimal("150.00"), "USD"),
                timestamp=datetime(2025, 12, 1, 14, 0, tzinfo=timezone.utc),
                source="database",
                interval="1day",
            ),
            PricePoint(
                ticker=Ticker("AAPL"),
                price=Money(Decimal("150.25"), "USD"),
                timestamp=datetime(2025, 12, 1, 14, 30, tzinfo=timezone.utc),
                source="database",
                interval="real-time",
            ),
        ]
        adapter.seed_prices(prices)

        start = datetime(2025, 12, 1, tzinfo=timezone.utc)
        end = datetime(2025, 12, 31, tzinfo=timezone.utc)
        result = await adapter.get_price_history(Ticker("AAPL"), start, end, "1day")

        # Should only get the 1day interval price
        assert len(result) == 1
        assert result[0].interval == "1day"

    @pytest.mark.asyncio
    async def test_get_price_history_chronological_order(self) -> None:
        """Should return results in chronological order (oldest first)."""
        adapter = InMemoryMarketDataAdapter()

        prices = [
            PricePoint(
                ticker=Ticker("AAPL"),
                price=Money(Decimal("152.00"), "USD"),
                timestamp=datetime(2025, 12, 31, tzinfo=timezone.utc),
                source="database",
                interval="1day",
            ),
            PricePoint(
                ticker=Ticker("AAPL"),
                price=Money(Decimal("150.00"), "USD"),
                timestamp=datetime(2025, 12, 1, tzinfo=timezone.utc),
                source="database",
                interval="1day",
            ),
        ]
        adapter.seed_prices(prices)  # Added in reverse chronological order

        start = datetime(2025, 12, 1, tzinfo=timezone.utc)
        end = datetime(2025, 12, 31, tzinfo=timezone.utc)
        result = await adapter.get_price_history(Ticker("AAPL"), start, end, "1day")

        # Should be sorted oldest first
        assert len(result) == 2
        assert result[0].timestamp < result[1].timestamp


class TestInMemoryAdapterGetSupportedTickers:
    """Tests for get_supported_tickers method."""

    @pytest.mark.asyncio
    async def test_get_supported_tickers_empty(self) -> None:
        """Should return empty list when no data."""
        adapter = InMemoryMarketDataAdapter()

        result = await adapter.get_supported_tickers()

        assert result == []

    @pytest.mark.asyncio
    async def test_get_supported_tickers_single_ticker(self) -> None:
        """Should return single ticker."""
        adapter = InMemoryMarketDataAdapter()
        adapter.seed_price(
            PricePoint(
                ticker=Ticker("AAPL"),
                price=Money(Decimal("150.25"), "USD"),
                timestamp=datetime(2025, 12, 28, 14, 30, tzinfo=timezone.utc),
                source="database",
                interval="real-time",
            )
        )

        result = await adapter.get_supported_tickers()

        assert len(result) == 1
        assert result[0].symbol == "AAPL"

    @pytest.mark.asyncio
    async def test_get_supported_tickers_multiple_tickers(self) -> None:
        """Should return all tickers with data."""
        adapter = InMemoryMarketDataAdapter()

        prices = [
            PricePoint(
                ticker=Ticker("AAPL"),
                price=Money(Decimal("150.25"), "USD"),
                timestamp=datetime(2025, 12, 28, 14, 30, tzinfo=timezone.utc),
                source="database",
                interval="real-time",
            ),
            PricePoint(
                ticker=Ticker("GOOGL"),
                price=Money(Decimal("140.50"), "USD"),
                timestamp=datetime(2025, 12, 28, 14, 30, tzinfo=timezone.utc),
                source="database",
                interval="real-time",
            ),
        ]
        adapter.seed_prices(prices)

        result = await adapter.get_supported_tickers()

        assert len(result) == 2
        symbols = {t.symbol for t in result}
        assert "AAPL" in symbols
        assert "GOOGL" in symbols
