"""Unit tests for AlphaVantageAdapter weekend handling in get_current_price and get_batch_prices.

These tests verify the fix for Task 159 - ensuring that get_current_price and
get_batch_prices return cached prices on weekends/holidays instead of failing with
"Ticker not found" errors.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from zebu.adapters.outbound.market_data.alpha_vantage_adapter import (
    AlphaVantageAdapter,
)
from zebu.application.dtos.price_point import PricePoint
from zebu.application.exceptions import TickerNotFoundError
from zebu.domain.value_objects.money import Money
from zebu.domain.value_objects.ticker import Ticker


@pytest.fixture
def mock_rate_limiter() -> MagicMock:
    """Provide mock rate limiter."""
    limiter = MagicMock()
    limiter.can_make_request = AsyncMock(return_value=True)
    limiter.consume_token = AsyncMock(return_value=True)
    limiter.tokens = 5  # Track available tokens
    return limiter


@pytest.fixture
def mock_price_repository() -> MagicMock:
    """Provide mock price repository."""
    repo = MagicMock()
    # Make repository methods async by default
    repo.get_latest_price = AsyncMock(return_value=None)
    repo.get_price_at = AsyncMock(return_value=None)
    repo.upsert_price = AsyncMock()
    return repo


@pytest.fixture
def mock_price_cache() -> MagicMock:
    """Provide mock price cache."""
    cache = MagicMock()
    cache.get = AsyncMock(return_value=None)
    cache.set = AsyncMock()
    return cache


@pytest.fixture
def mock_http_client() -> MagicMock:
    """Provide mock HTTP client."""
    return MagicMock()


@pytest.fixture
def alpha_vantage_adapter(
    mock_rate_limiter: MagicMock,
    mock_price_repository: MagicMock,
    mock_price_cache: MagicMock,
    mock_http_client: MagicMock,
) -> AlphaVantageAdapter:
    """Provide configured Alpha Vantage adapter for testing."""
    return AlphaVantageAdapter(
        rate_limiter=mock_rate_limiter,
        price_repository=mock_price_repository,
        price_cache=mock_price_cache,
        http_client=mock_http_client,
        api_key="test_key",
    )


def create_price_point(
    ticker: Ticker, date: datetime, price: Decimal = Decimal("259.96")
) -> PricePoint:
    """Helper to create a price point for testing."""
    return PricePoint(
        ticker=ticker,
        timestamp=date,
        price=Money(price, "USD"),
        open=Money(price - Decimal("1.00"), "USD"),
        high=Money(price + Decimal("2.00"), "USD"),
        low=Money(price - Decimal("2.00"), "USD"),
        close=Money(price, "USD"),
        volume=1000000,
        source="database",
        interval="1day",
    )


class TestGetCurrentPriceOnWeekend:
    """Tests for get_current_price() weekend/holiday handling."""

    @pytest.mark.asyncio
    async def test_get_current_price_on_sunday_returns_friday_price(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
        mock_price_repository: MagicMock,
        mock_price_cache: MagicMock,
    ) -> None:
        """Test that get_current_price returns cached price on Sunday."""
        # Mock today as Sunday, Jan 18, 2026
        mock_now = datetime(2026, 1, 18, 15, 0, 0, tzinfo=UTC)  # Sunday 3PM UTC

        # Setup: Cached Friday price exists in database
        friday_price = create_price_point(
            Ticker("AAPL"),
            datetime(2026, 1, 16, 21, 0, 0, tzinfo=UTC),  # Friday close
        )

        mock_price_repository.get_price_at = AsyncMock(return_value=friday_price)
        mock_price_cache.get.return_value = None  # No Redis cache

        with patch(
            "zebu.adapters.outbound.market_data.alpha_vantage_adapter.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(
                *args, **kwargs
            )

            # Execute
            result = await alpha_vantage_adapter.get_current_price(Ticker("AAPL"))

            # Assert
            assert result.price.amount == Decimal("259.96")
            assert result.source == "database"
            # Verify it called get_price_at with the last trading day (Friday)
            mock_price_repository.get_price_at.assert_called_once()
            call_args = mock_price_repository.get_price_at.call_args
            assert call_args[0][0].symbol == "AAPL"
            # Last trading day should be Friday Jan 16
            assert call_args[0][1].date().day == 16
            assert call_args[0][1].date().weekday() == 4  # Friday

    @pytest.mark.asyncio
    async def test_get_current_price_on_saturday_returns_friday_price(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
        mock_price_repository: MagicMock,
        mock_price_cache: MagicMock,
    ) -> None:
        """Test that get_current_price returns cached price on Saturday."""
        # Mock today as Saturday, Jan 17, 2026
        mock_now = datetime(2026, 1, 17, 15, 0, 0, tzinfo=UTC)  # Saturday 3PM UTC

        # Setup: Cached Friday price exists in database
        friday_price = create_price_point(
            Ticker("MSFT"),
            datetime(2026, 1, 16, 21, 0, 0, tzinfo=UTC),  # Friday close
        )

        mock_price_repository.get_price_at = AsyncMock(return_value=friday_price)
        mock_price_cache.get.return_value = None

        with patch(
            "zebu.adapters.outbound.market_data.alpha_vantage_adapter.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(
                *args, **kwargs
            )

            # Execute
            result = await alpha_vantage_adapter.get_current_price(Ticker("MSFT"))

            # Assert
            assert result.price.amount == Decimal("259.96")
            assert result.source == "database"
            # Verify last trading day is Friday
            call_args = mock_price_repository.get_price_at.call_args
            assert call_args[0][1].date().day == 16
            assert call_args[0][1].date().weekday() == 4  # Friday

    @pytest.mark.asyncio
    async def test_get_current_price_on_holiday_returns_last_trading_day_price(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
        mock_price_repository: MagicMock,
        mock_price_cache: MagicMock,
    ) -> None:
        """Test that get_current_price returns cached price on MLK Day."""
        # Mock today as Monday, Jan 20, 2026 (MLK Day - holiday)
        mock_now = datetime(2026, 1, 20, 15, 0, 0, tzinfo=UTC)

        # Setup: Cached Friday price exists (last trading day before 3-day weekend)
        friday_price = create_price_point(
            Ticker("AAPL"),
            datetime(2026, 1, 16, 21, 0, 0, tzinfo=UTC),  # Friday Jan 16
        )

        mock_price_repository.get_price_at = AsyncMock(return_value=friday_price)
        mock_price_cache.get.return_value = None

        with patch(
            "zebu.adapters.outbound.market_data.alpha_vantage_adapter.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(
                *args, **kwargs
            )

            # Execute
            result = await alpha_vantage_adapter.get_current_price(Ticker("AAPL"))

            # Assert
            assert result.price.amount == Decimal("259.96")
            assert result.source == "database"
            # Verify last trading day is Friday Jan 16
            call_args = mock_price_repository.get_price_at.call_args
            assert call_args[0][1].date().day == 16
            assert call_args[0][1].date().weekday() == 4  # Friday

    @pytest.mark.asyncio
    async def test_get_current_price_on_weekend_no_cached_data_raises_error(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
        mock_price_repository: MagicMock,
        mock_price_cache: MagicMock,
    ) -> None:
        """Test that get_current_price raises TickerNotFoundError when no cached data on weekend."""
        # Mock today as Sunday, Jan 18, 2026
        mock_now = datetime(2026, 1, 18, 15, 0, 0, tzinfo=UTC)

        # Setup: No cached data
        mock_price_repository.get_price_at = AsyncMock(return_value=None)
        mock_price_cache.get.return_value = None

        with patch(
            "zebu.adapters.outbound.market_data.alpha_vantage_adapter.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(
                *args, **kwargs
            )

            # Execute & Assert
            with pytest.raises(TickerNotFoundError) as exc_info:
                await alpha_vantage_adapter.get_current_price(Ticker("NONE"))

            assert "No cached data available for NONE" in str(exc_info.value)
            assert "markets closed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_current_price_on_weekend_falls_back_to_stale_cache(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
        mock_price_repository: MagicMock,
        mock_price_cache: MagicMock,
    ) -> None:
        """Test that get_current_price falls back to stale cache if no DB data on weekend."""
        # Mock today as Sunday, Jan 18, 2026
        mock_now = datetime(2026, 1, 18, 15, 0, 0, tzinfo=UTC)

        # Setup: No database data, but have stale cached data
        stale_cached_price = create_price_point(
            Ticker("AAPL"),
            datetime(2026, 1, 15, 21, 0, 0, tzinfo=UTC),  # Thursday (old)
        )
        mock_price_repository.get_price_at = AsyncMock(return_value=None)
        mock_price_cache.get.return_value = stale_cached_price

        with patch(
            "zebu.adapters.outbound.market_data.alpha_vantage_adapter.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(
                *args, **kwargs
            )

            # Execute
            result = await alpha_vantage_adapter.get_current_price(Ticker("AAPL"))

            # Assert - should return the stale cached data as fallback
            assert result.price.amount == Decimal("259.96")
            assert result.source == "cache"

    @pytest.mark.asyncio
    async def test_get_current_price_on_weekday_fetches_from_api(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
        mock_price_repository: MagicMock,
        mock_price_cache: MagicMock,
        mock_rate_limiter: MagicMock,
    ) -> None:
        """Test that get_current_price still fetches from API on weekdays."""
        # Mock today as Tuesday, Jan 21, 2026 (regular trading day)
        mock_now = datetime(2026, 1, 21, 15, 0, 0, tzinfo=UTC)

        # Setup: No cache, will need to fetch from API
        mock_price_repository.get_latest_price = AsyncMock(return_value=None)
        mock_price_cache.get.return_value = None

        # Mock API response
        api_price = create_price_point(
            Ticker("AAPL"),
            mock_now,
        )

        with patch(
            "zebu.adapters.outbound.market_data.alpha_vantage_adapter.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(
                *args, **kwargs
            )

            # Mock _fetch_from_api
            alpha_vantage_adapter._fetch_from_api = AsyncMock(return_value=api_price)

            # Execute
            result = await alpha_vantage_adapter.get_current_price(Ticker("AAPL"))

            # Assert - should have called API (rate limiter consumed)
            assert mock_rate_limiter.consume_token.called
            assert result.price.amount == Decimal("259.96")


class TestGetBatchPricesOnWeekend:
    """Tests for get_batch_prices() weekend/holiday handling."""

    @pytest.mark.asyncio
    async def test_get_batch_prices_on_sunday_returns_friday_prices(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
        mock_price_repository: MagicMock,
        mock_price_cache: MagicMock,
    ) -> None:
        """Test batch prices returns cached data on Sunday."""
        # Mock Sunday, Jan 18, 2026
        mock_now = datetime(2026, 1, 18, 15, 0, 0, tzinfo=UTC)

        # Setup cached prices for multiple tickers
        friday_aapl = create_price_point(
            Ticker("AAPL"),
            datetime(2026, 1, 16, 21, 0, 0, tzinfo=UTC),
            Decimal("259.96"),
        )
        friday_msft = create_price_point(
            Ticker("MSFT"),
            datetime(2026, 1, 16, 21, 0, 0, tzinfo=UTC),
            Decimal("123.45"),
        )

        async def mock_get_price_at(ticker: Ticker, timestamp: datetime) -> PricePoint | None:
            if ticker.symbol == "AAPL":
                return friday_aapl
            elif ticker.symbol == "MSFT":
                return friday_msft
            return None

        mock_price_repository.get_price_at = AsyncMock(side_effect=mock_get_price_at)
        mock_price_cache.get.return_value = None

        with patch(
            "zebu.adapters.outbound.market_data.alpha_vantage_adapter.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(
                *args, **kwargs
            )

            # Execute
            result = await alpha_vantage_adapter.get_batch_prices(
                [Ticker("AAPL"), Ticker("MSFT")]
            )

            # Assert
            assert len(result) == 2
            assert Ticker("AAPL") in result
            assert Ticker("MSFT") in result
            assert result[Ticker("AAPL")].price.amount == Decimal("259.96")
            assert result[Ticker("MSFT")].price.amount == Decimal("123.45")
            assert result[Ticker("AAPL")].source == "database"
            assert result[Ticker("MSFT")].source == "database"

    @pytest.mark.asyncio
    async def test_get_batch_prices_on_weekend_does_not_call_api(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
        mock_price_repository: MagicMock,
        mock_price_cache: MagicMock,
        mock_rate_limiter: MagicMock,
    ) -> None:
        """Test that batch prices doesn't attempt API calls on weekends."""
        # Mock Saturday, Jan 17, 2026
        mock_now = datetime(2026, 1, 17, 15, 0, 0, tzinfo=UTC)

        # Setup: Have one ticker in cache, one in DB, one missing
        # Make cached AAPL price stale (3 hours old) so it goes to DB tier
        cached_aapl = create_price_point(
            Ticker("AAPL"),
            datetime(2026, 1, 17, 12, 0, 0, tzinfo=UTC),  # 3 hours ago - stale
        )

        async def mock_cache_get(ticker: Ticker) -> PricePoint | None:
            if ticker.symbol == "AAPL":
                return cached_aapl
            return None

        mock_price_cache.get.side_effect = mock_cache_get

        db_aapl = create_price_point(
            Ticker("AAPL"),
            datetime(2026, 1, 16, 21, 0, 0, tzinfo=UTC),  # Friday
        )

        db_msft = create_price_point(
            Ticker("MSFT"),
            datetime(2026, 1, 16, 21, 0, 0, tzinfo=UTC),
        )

        async def mock_get_price_at(ticker: Ticker, timestamp: datetime) -> PricePoint | None:
            if ticker.symbol == "AAPL":
                return db_aapl
            elif ticker.symbol == "MSFT":
                return db_msft
            return None  # GOOGL not found

        mock_price_repository.get_price_at = AsyncMock(side_effect=mock_get_price_at)

        with patch(
            "zebu.adapters.outbound.market_data.alpha_vantage_adapter.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(
                *args, **kwargs
            )

            # Execute - request 3 tickers
            result = await alpha_vantage_adapter.get_batch_prices(
                [Ticker("AAPL"), Ticker("MSFT"), Ticker("GOOGL")]
            )

            # Assert - should return 2 tickers (AAPL from DB, MSFT from DB)
            assert len(result) == 2
            assert Ticker("AAPL") in result
            assert Ticker("MSFT") in result
            assert Ticker("GOOGL") not in result  # Missing, but no API call attempted

            # Most importantly: rate limiter should NOT have been called
            mock_rate_limiter.consume_token.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_batch_prices_on_holiday_uses_last_trading_day(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
        mock_price_repository: MagicMock,
        mock_price_cache: MagicMock,
    ) -> None:
        """Test batch prices uses last trading day on MLK Day."""
        # Mock Monday, Jan 20, 2026 (MLK Day)
        mock_now = datetime(2026, 1, 20, 15, 0, 0, tzinfo=UTC)

        friday_price = create_price_point(
            Ticker("AAPL"),
            datetime(2026, 1, 16, 21, 0, 0, tzinfo=UTC),
        )

        mock_price_repository.get_price_at = AsyncMock(return_value=friday_price)
        mock_price_cache.get.return_value = None

        with patch(
            "zebu.adapters.outbound.market_data.alpha_vantage_adapter.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(
                *args, **kwargs
            )

            # Execute
            result = await alpha_vantage_adapter.get_batch_prices([Ticker("AAPL")])

            # Assert
            assert len(result) == 1
            assert result[Ticker("AAPL")].price.amount == Decimal("259.96")

            # Verify it called get_price_at with Friday (last trading day)
            call_args = mock_price_repository.get_price_at.call_args
            assert call_args[0][1].date().day == 16
            assert call_args[0][1].date().weekday() == 4  # Friday

    @pytest.mark.asyncio
    async def test_get_batch_prices_on_weekday_fetches_from_api(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
        mock_price_repository: MagicMock,
        mock_price_cache: MagicMock,
        mock_rate_limiter: MagicMock,
    ) -> None:
        """Test that batch prices still fetches from API on weekdays."""
        # Mock Tuesday, Jan 21, 2026 (regular trading day)
        mock_now = datetime(2026, 1, 21, 15, 0, 0, tzinfo=UTC)

        # Setup: No cache or DB data
        mock_price_repository.get_latest_price = AsyncMock(return_value=None)
        mock_price_repository.upsert_price = AsyncMock()  # Ensure this is mocked
        mock_price_cache.get.return_value = None
        mock_price_cache.set = AsyncMock()  # Ensure this is mocked

        api_price = create_price_point(Ticker("AAPL"), mock_now)

        with patch(
            "zebu.adapters.outbound.market_data.alpha_vantage_adapter.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(
                *args, **kwargs
            )

            # Mock _fetch_from_api
            alpha_vantage_adapter._fetch_from_api = AsyncMock(return_value=api_price)

            # Execute
            result = await alpha_vantage_adapter.get_batch_prices([Ticker("AAPL")])

            # Assert - should have called API
            assert mock_rate_limiter.consume_token.called
            assert len(result) == 1
            assert result[Ticker("AAPL")].price.amount == Decimal("259.96")
