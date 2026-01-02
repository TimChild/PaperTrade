"""Integration tests for PriceRepository.

Tests the PostgreSQL price repository implementation against a real database
(SQLite in test mode) to verify all CRUD operations and query performance.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from papertrade.adapters.outbound.repositories.price_repository import PriceRepository
from papertrade.application.dtos.price_point import PricePoint
from papertrade.domain.value_objects.money import Money
from papertrade.domain.value_objects.ticker import Ticker


class TestPriceRepositoryUpsert:
    """Tests for upsert_price method."""

    @pytest.mark.asyncio
    async def test_upsert_inserts_new_price(self, session):
        """Test inserting a new price record."""
        # Arrange
        repo = PriceRepository(session)
        price = PricePoint(
            ticker=Ticker("AAPL"),
            price=Money(Decimal("150.25"), "USD"),
            timestamp=datetime(2024, 6, 15, 16, 0, 0, tzinfo=UTC),
            source="alpha_vantage",
            interval="real-time",
        )

        # Act
        await repo.upsert_price(price)
        await session.commit()

        # Assert - verify price was inserted
        result = await repo.get_latest_price(Ticker("AAPL"))
        assert result is not None
        assert result.ticker == Ticker("AAPL")
        assert result.price.amount == Decimal("150.25")
        assert result.source == "alpha_vantage"

    @pytest.mark.asyncio
    async def test_upsert_updates_existing_price(self, session):
        """Test updating an existing price record."""
        # Arrange
        repo = PriceRepository(session)
        timestamp = datetime(2024, 6, 15, 16, 0, 0, tzinfo=UTC)

        # Insert initial price
        price1 = PricePoint(
            ticker=Ticker("AAPL"),
            price=Money(Decimal("150.00"), "USD"),
            timestamp=timestamp,
            source="alpha_vantage",
            interval="real-time",
        )
        await repo.upsert_price(price1)
        await session.commit()

        # Act - update with new price
        price2 = PricePoint(
            ticker=Ticker("AAPL"),
            price=Money(Decimal("151.00"), "USD"),
            timestamp=timestamp,
            source="alpha_vantage",
            interval="real-time",
        )
        await repo.upsert_price(price2)
        await session.commit()

        # Assert - should have only one record with updated price
        result = await repo.get_latest_price(Ticker("AAPL"))
        assert result is not None
        assert result.price.amount == Decimal("151.00")

    @pytest.mark.asyncio
    async def test_upsert_with_ohlcv_data(self, session):
        """Test upserting price with OHLCV data."""
        # Arrange
        repo = PriceRepository(session)
        price = PricePoint(
            ticker=Ticker("AAPL"),
            price=Money(Decimal("150.25"), "USD"),
            timestamp=datetime(2024, 6, 15, 16, 0, 0, tzinfo=UTC),
            source="alpha_vantage",
            interval="1day",
            open=Money(Decimal("149.00"), "USD"),
            high=Money(Decimal("151.50"), "USD"),
            low=Money(Decimal("148.50"), "USD"),
            close=Money(Decimal("150.25"), "USD"),
            volume=1000000,
        )

        # Act
        await repo.upsert_price(price)
        await session.commit()

        # Assert
        result = await repo.get_latest_price(Ticker("AAPL"))
        assert result is not None
        assert result.open is not None
        assert result.open.amount == Decimal("149.00")
        assert result.high is not None
        assert result.high.amount == Decimal("151.50")
        assert result.low is not None
        assert result.low.amount == Decimal("148.50")
        assert result.close is not None
        assert result.close.amount == Decimal("150.25")
        assert result.volume == 1000000


class TestPriceRepositoryGetLatest:
    """Tests for get_latest_price method."""

    @pytest.mark.asyncio
    async def test_get_latest_returns_most_recent(self, session):
        """Test getting the most recent price."""
        # Arrange
        repo = PriceRepository(session)
        base_time = datetime(2024, 6, 15, 16, 0, 0, tzinfo=UTC)

        # Insert multiple prices at different times
        for i in range(3):
            price = PricePoint(
                ticker=Ticker("AAPL"),
                price=Money(Decimal(f"150.{i:02d}"), "USD"),
                timestamp=base_time + timedelta(hours=i),
                source="alpha_vantage",
                interval="real-time",
            )
            await repo.upsert_price(price)
        await session.commit()

        # Act
        result = await repo.get_latest_price(Ticker("AAPL"))

        # Assert - should return most recent (hour 2)
        assert result is not None
        assert result.price.amount == Decimal("150.02")
        assert result.timestamp == base_time + timedelta(hours=2)

    @pytest.mark.asyncio
    async def test_get_latest_returns_none_for_unknown_ticker(self, session):
        """Test getting price for non-existent ticker."""
        # Arrange
        repo = PriceRepository(session)

        # Act
        result = await repo.get_latest_price(Ticker("XYZ"))

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_get_latest_respects_max_age(self, session):
        """Test that max_age filter works correctly."""
        # Arrange
        repo = PriceRepository(session)
        old_time = datetime.now(UTC) - timedelta(hours=5)
        recent_time = datetime.now(UTC) - timedelta(minutes=30)

        # Insert old price
        old_price = PricePoint(
            ticker=Ticker("AAPL"),
            price=Money(Decimal("150.00"), "USD"),
            timestamp=old_time,
            source="alpha_vantage",
            interval="real-time",
        )
        await repo.upsert_price(old_price)

        # Insert recent price
        recent_price = PricePoint(
            ticker=Ticker("AAPL"),
            price=Money(Decimal("151.00"), "USD"),
            timestamp=recent_time,
            source="alpha_vantage",
            interval="real-time",
        )
        await repo.upsert_price(recent_price)
        await session.commit()

        # Act - get with 1 hour max age
        result = await repo.get_latest_price(Ticker("AAPL"), max_age=timedelta(hours=1))

        # Assert - should return recent price
        assert result is not None
        assert result.price.amount == Decimal("151.00")

        # Act - get with 10 minute max age (should exclude recent price)
        result_strict = await repo.get_latest_price(
            Ticker("AAPL"), max_age=timedelta(minutes=10)
        )

        # Assert - should return None (both prices too old)
        assert result_strict is None


class TestPriceRepositoryGetPriceAt:
    """Tests for get_price_at method."""

    @pytest.mark.asyncio
    async def test_get_price_at_finds_exact_match(self, session):
        """Test finding price at exact timestamp."""
        # Arrange
        repo = PriceRepository(session)
        target_time = datetime(2024, 6, 15, 16, 0, 0, tzinfo=UTC)

        price = PricePoint(
            ticker=Ticker("AAPL"),
            price=Money(Decimal("150.00"), "USD"),
            timestamp=target_time,
            source="alpha_vantage",
            interval="1day",
        )
        await repo.upsert_price(price)
        await session.commit()

        # Act
        result = await repo.get_price_at(Ticker("AAPL"), target_time)

        # Assert
        assert result is not None
        assert result.timestamp == target_time
        assert result.price.amount == Decimal("150.00")

    @pytest.mark.asyncio
    async def test_get_price_at_finds_closest_before(self, session):
        """Test finding price closest to (but before) timestamp."""
        # Arrange
        repo = PriceRepository(session)
        base_time = datetime(2024, 6, 15, 16, 0, 0, tzinfo=UTC)

        # Insert prices at hour 0 and hour 2
        for hour in [0, 2]:
            price = PricePoint(
                ticker=Ticker("AAPL"),
                price=Money(Decimal(f"150.{hour:02d}"), "USD"),
                timestamp=base_time + timedelta(hours=hour),
                source="alpha_vantage",
                interval="1day",
            )
            await repo.upsert_price(price)
        await session.commit()

        # Act - query for hour 1 (between hour 0 and 2)
        target_time = base_time + timedelta(hours=1)
        result = await repo.get_price_at(Ticker("AAPL"), target_time)

        # Assert - should return hour 0 (closest before target)
        assert result is not None
        assert result.timestamp == base_time
        assert result.price.amount == Decimal("150.00")

    @pytest.mark.asyncio
    async def test_get_price_at_returns_none_for_future_date(self, session):
        """Test that future dates return None."""
        # Arrange
        repo = PriceRepository(session)
        past_time = datetime(2024, 6, 15, 16, 0, 0, tzinfo=UTC)
        datetime(2025, 6, 15, 16, 0, 0, tzinfo=UTC)

        price = PricePoint(
            ticker=Ticker("AAPL"),
            price=Money(Decimal("150.00"), "USD"),
            timestamp=past_time,
            source="alpha_vantage",
            interval="1day",
        )
        await repo.upsert_price(price)
        await session.commit()

        # Act - query before price exists
        before_time = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        result = await repo.get_price_at(Ticker("AAPL"), before_time)

        # Assert
        assert result is None


class TestPriceRepositoryGetHistory:
    """Tests for get_price_history method."""

    @pytest.mark.asyncio
    async def test_get_price_history_returns_range(self, session):
        """Test getting price history over a date range."""
        # Arrange
        repo = PriceRepository(session)
        base_time = datetime(2024, 6, 1, 16, 0, 0, tzinfo=UTC)

        # Insert 10 days of prices
        for day in range(10):
            price = PricePoint(
                ticker=Ticker("AAPL"),
                price=Money(Decimal(f"150.{day:02d}"), "USD"),
                timestamp=base_time + timedelta(days=day),
                source="alpha_vantage",
                interval="1day",
            )
            await repo.upsert_price(price)
        await session.commit()

        # Act - get prices from day 2 to day 7 (inclusive)
        start = base_time + timedelta(days=2)
        end = base_time + timedelta(days=7)
        result = await repo.get_price_history(
            Ticker("AAPL"), start=start, end=end, interval="1day"
        )

        # Assert - should return 6 prices (days 2-7)
        assert len(result) == 6
        assert result[0].price.amount == Decimal("150.02")
        assert result[-1].price.amount == Decimal("150.07")

    @pytest.mark.asyncio
    async def test_get_price_history_filters_by_interval(self, session):
        """Test that interval filter works correctly."""
        # Arrange
        repo = PriceRepository(session)
        timestamp = datetime(2024, 6, 15, 16, 0, 0, tzinfo=UTC)

        # Insert prices with different intervals
        for interval in ["real-time", "1day", "1hour"]:
            price = PricePoint(
                ticker=Ticker("AAPL"),
                price=Money(Decimal("150.00"), "USD"),
                timestamp=timestamp,
                source="alpha_vantage",
                interval=interval,
            )
            await repo.upsert_price(price)
        await session.commit()

        # Act - get only daily prices
        result = await repo.get_price_history(
            Ticker("AAPL"),
            start=timestamp,
            end=timestamp,
            interval="1day",
        )

        # Assert - should return only 1 price (1day interval)
        assert len(result) == 1
        assert result[0].interval == "1day"

    @pytest.mark.asyncio
    async def test_get_price_history_returns_chronological_order(self, session):
        """Test that results are ordered chronologically."""
        # Arrange
        repo = PriceRepository(session)
        base_time = datetime(2024, 6, 1, 16, 0, 0, tzinfo=UTC)

        # Insert prices in reverse order
        for day in reversed(range(5)):
            price = PricePoint(
                ticker=Ticker("AAPL"),
                price=Money(Decimal(f"150.{day:02d}"), "USD"),
                timestamp=base_time + timedelta(days=day),
                source="alpha_vantage",
                interval="1day",
            )
            await repo.upsert_price(price)
        await session.commit()

        # Act
        result = await repo.get_price_history(
            Ticker("AAPL"),
            start=base_time,
            end=base_time + timedelta(days=4),
            interval="1day",
        )

        # Assert - should be in chronological order
        assert len(result) == 5
        for i in range(5):
            assert result[i].price.amount == Decimal(f"150.{i:02d}")

    @pytest.mark.asyncio
    async def test_get_price_history_returns_empty_for_no_data(self, session):
        """Test that empty list is returned when no data exists."""
        # Arrange
        repo = PriceRepository(session)
        start = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        end = datetime(2024, 12, 31, 23, 59, 59, tzinfo=UTC)

        # Act
        result = await repo.get_price_history(
            Ticker("XYZ"), start=start, end=end, interval="1day"
        )

        # Assert
        assert result == []


class TestPriceRepositoryGetAllTickers:
    """Tests for get_all_tickers method."""

    @pytest.mark.asyncio
    async def test_get_all_tickers_returns_unique_tickers(self, session):
        """Test getting list of all tickers with data."""
        # Arrange
        repo = PriceRepository(session)
        timestamp = datetime(2024, 6, 15, 16, 0, 0, tzinfo=UTC)

        # Insert prices for multiple tickers
        tickers = ["AAPL", "GOOGL", "MSFT"]
        for ticker_symbol in tickers:
            price = PricePoint(
                ticker=Ticker(ticker_symbol),
                price=Money(Decimal("150.00"), "USD"),
                timestamp=timestamp,
                source="alpha_vantage",
                interval="real-time",
            )
            await repo.upsert_price(price)
        await session.commit()

        # Act
        result = await repo.get_all_tickers()

        # Assert
        assert len(result) == 3
        ticker_symbols = [t.symbol for t in result]
        assert "AAPL" in ticker_symbols
        assert "GOOGL" in ticker_symbols
        assert "MSFT" in ticker_symbols

    @pytest.mark.asyncio
    async def test_get_all_tickers_returns_sorted(self, session):
        """Test that tickers are returned in alphabetical order."""
        # Arrange
        repo = PriceRepository(session)
        timestamp = datetime(2024, 6, 15, 16, 0, 0, tzinfo=UTC)

        # Insert in random order
        for ticker_symbol in ["TSLA", "AAPL", "MSFT"]:
            price = PricePoint(
                ticker=Ticker(ticker_symbol),
                price=Money(Decimal("150.00"), "USD"),
                timestamp=timestamp,
                source="alpha_vantage",
                interval="real-time",
            )
            await repo.upsert_price(price)
        await session.commit()

        # Act
        result = await repo.get_all_tickers()

        # Assert - should be alphabetically sorted
        assert len(result) == 3
        assert result[0].symbol == "AAPL"
        assert result[1].symbol == "MSFT"
        assert result[2].symbol == "TSLA"

    @pytest.mark.asyncio
    async def test_get_all_tickers_returns_empty_when_no_data(self, session):
        """Test that empty list is returned when no prices exist."""
        # Arrange
        repo = PriceRepository(session)

        # Act
        result = await repo.get_all_tickers()

        # Assert
        assert result == []
