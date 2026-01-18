"""Unit tests for weekend/holiday price fetching in AlphaVantageAdapter.

These tests verify the fix for Task 159 - ensuring that the backend returns
cached prices from the last trading day when markets are closed (weekends/holidays),
instead of returning "Ticker not found" errors.
"""

from datetime import UTC, datetime
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
    """Provide mock rate limiter that allows requests."""
    limiter = MagicMock()
    limiter.can_make_request = AsyncMock(return_value=True)
    limiter.consume_token = AsyncMock(return_value=True)
    return limiter


@pytest.fixture
def mock_price_repository() -> MagicMock:
    """Provide mock price repository."""
    return MagicMock()


@pytest.fixture
def mock_price_cache() -> MagicMock:
    """Provide mock price cache."""
    cache = MagicMock()
    cache.get = AsyncMock(return_value=None)  # No Redis cache by default
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
    ticker: Ticker, timestamp: datetime, price: Decimal = Decimal("259.96")
) -> PricePoint:
    """Helper to create a price point for testing."""
    return PricePoint(
        ticker=ticker,
        timestamp=timestamp,
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
    """Tests for get_current_price() on weekends."""

    @pytest.mark.asyncio
    async def test_get_current_price_sunday_returns_friday_price(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
        mock_price_repository: MagicMock,
        mock_rate_limiter: MagicMock,
    ) -> None:
        """Should return Friday's cached price on Sunday without API call."""
        # Mock current time as Sunday, Jan 18, 2026 at 3:00 PM UTC
        # (Verify: Jan 18, 2026 is a Sunday - weekday 6)
        mock_now = datetime(2026, 1, 18, 15, 0, 0, tzinfo=UTC)
        assert mock_now.weekday() == 6  # Sunday

        # Mock Friday's price from database (Jan 16, 2026 at market close)
        # (Verify: Jan 16, 2026 is a Friday - weekday 4)
        friday_price = create_price_point(
            ticker=Ticker("AAPL"),
            timestamp=datetime(2026, 1, 16, 21, 0, 0, tzinfo=UTC),
            price=Decimal("259.96"),
        )
        assert friday_price.timestamp.weekday() == 4  # Friday
        mock_price_repository.get_latest_price = AsyncMock(return_value=None)
        mock_price_repository.get_price_at = AsyncMock(return_value=friday_price)

        with patch(
            "zebu.adapters.outbound.market_data.alpha_vantage_adapter.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(
                *args, **kwargs
            )

            # Execute
            result = await alpha_vantage_adapter.get_current_price(Ticker("AAPL"))

            # Assert: Should return Friday's price
            assert result.price.amount == Decimal("259.96")
            assert result.source == "database"
            assert result.timestamp.date().weekday() == 4  # Friday (weekday: 0=Mon, 4=Fri, 6=Sun)

            # Verify get_price_at was called with last trading day
            mock_price_repository.get_price_at.assert_called_once()
            call_args = mock_price_repository.get_price_at.call_args
            assert call_args[0][0] == Ticker("AAPL")
            # Friday, Jan 16 at market close (21:00 UTC)
            assert call_args[0][1].date().day == 16
            assert call_args[0][1].date().month == 1
            assert call_args[0][1].hour == 21

            # Verify NO API call was made (rate limiter not consumed)
            mock_rate_limiter.consume_token.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_current_price_saturday_returns_friday_price(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
        mock_price_repository: MagicMock,
        mock_rate_limiter: MagicMock,
    ) -> None:
        """Should return Friday's cached price on Saturday without API call."""
        # Mock current time as Saturday, Jan 17, 2026 at 10:00 AM UTC
        # (Verify: Jan 17, 2026 is a Saturday - weekday 5)
        mock_now = datetime(2026, 1, 17, 10, 0, 0, tzinfo=UTC)
        assert mock_now.weekday() == 5  # Saturday

        # Mock Friday's price
        friday_price = create_price_point(
            ticker=Ticker("MSFT"),
            timestamp=datetime(2026, 1, 16, 21, 0, 0, tzinfo=UTC),
            price=Decimal("420.50"),
        )
        mock_price_repository.get_latest_price = AsyncMock(return_value=None)
        mock_price_repository.get_price_at = AsyncMock(return_value=friday_price)

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
            assert result.price.amount == Decimal("420.50")
            assert result.source == "database"

            # Verify no API call
            mock_rate_limiter.consume_token.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_current_price_holiday_returns_last_trading_day(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
        mock_price_repository: MagicMock,
        mock_rate_limiter: MagicMock,
    ) -> None:
        """Should return last trading day price on holidays (MLK Day).

        MLK Day 2026 is Monday, January 19 (3rd Monday in January).
        Last trading day before MLK Day is Friday, January 16.
        """
        # Mock current time as Monday, Jan 19, 2026 (MLK Day - holiday)
        # (Verify: Jan 19, 2026 is the 3rd Monday in January = MLK Day)
        mock_now = datetime(2026, 1, 19, 15, 0, 0, tzinfo=UTC)
        assert mock_now.weekday() == 0  # Monday

        # Mock Friday's price (Jan 16, last trading day before MLK Day)
        friday_price = create_price_point(
            ticker=Ticker("AAPL"),
            timestamp=datetime(2026, 1, 16, 21, 0, 0, tzinfo=UTC),
            price=Decimal("259.96"),
        )
        mock_price_repository.get_latest_price = AsyncMock(return_value=None)
        mock_price_repository.get_price_at = AsyncMock(return_value=friday_price)

        with patch(
            "zebu.adapters.outbound.market_data.alpha_vantage_adapter.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(
                *args, **kwargs
            )

            # Execute
            result = await alpha_vantage_adapter.get_current_price(Ticker("AAPL"))

            # Assert: Should return Friday's price
            assert result.price.amount == Decimal("259.96")
            assert result.source == "database"

            # Verify no API call on holiday
            mock_rate_limiter.consume_token.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_current_price_weekend_no_cached_data_raises_error(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
        mock_price_repository: MagicMock,
        mock_price_cache: MagicMock,
    ) -> None:
        """Should raise TickerNotFoundError if no cached data on weekend."""
        # Mock current time as Sunday
        mock_now = datetime(2026, 1, 18, 15, 0, 0, tzinfo=UTC)

        # No data available anywhere
        mock_price_repository.get_latest_price = AsyncMock(return_value=None)
        mock_price_repository.get_price_at = AsyncMock(return_value=None)
        mock_price_cache.get = AsyncMock(return_value=None)

        with patch(
            "zebu.adapters.outbound.market_data.alpha_vantage_adapter.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(
                *args, **kwargs
            )

            # Execute and expect error
            with pytest.raises(TickerNotFoundError) as exc_info:
                await alpha_vantage_adapter.get_current_price(Ticker("ZZZZ"))

            # Verify error message mentions markets closed
            assert "markets closed" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_get_current_price_weekend_falls_back_to_stale_cache(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
        mock_price_repository: MagicMock,
        mock_price_cache: MagicMock,
    ) -> None:
        """Should fall back to stale cache if no DB data on weekend."""
        # Mock current time as Sunday
        mock_now = datetime(2026, 1, 18, 15, 0, 0, tzinfo=UTC)

        # No DB data, but stale cache exists
        mock_price_repository.get_latest_price = AsyncMock(return_value=None)
        mock_price_repository.get_price_at = AsyncMock(return_value=None)

        # Stale cached price (from 3 hours ago, beyond 1 hour freshness)
        stale_cached = create_price_point(
            ticker=Ticker("AAPL"),
            timestamp=datetime(2026, 1, 18, 12, 0, 0, tzinfo=UTC),
            price=Decimal("258.00"),
        )
        mock_price_cache.get = AsyncMock(return_value=stale_cached)

        with patch(
            "zebu.adapters.outbound.market_data.alpha_vantage_adapter.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(
                *args, **kwargs
            )

            # Execute
            result = await alpha_vantage_adapter.get_current_price(Ticker("AAPL"))

            # Assert: Should return stale cached price as fallback
            assert result.price.amount == Decimal("258.00")
            assert result.source == "cache"


class TestGetBatchPricesOnWeekend:
    """Tests for get_batch_prices() on weekends."""

    @pytest.mark.asyncio
    async def test_get_batch_prices_sunday_returns_friday_prices(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
        mock_price_repository: MagicMock,
        mock_rate_limiter: MagicMock,
    ) -> None:
        """Should return Friday's prices for multiple tickers on Sunday."""
        # Mock current time as Sunday, Jan 18, 2026
        mock_now = datetime(2026, 1, 18, 15, 0, 0, tzinfo=UTC)

        # Mock Friday prices for multiple tickers
        friday_prices = {
            Ticker("AAPL"): create_price_point(
                Ticker("AAPL"),
                datetime(2026, 1, 16, 21, 0, 0, tzinfo=UTC),
                Decimal("259.96"),
            ),
            Ticker("MSFT"): create_price_point(
                Ticker("MSFT"),
                datetime(2026, 1, 16, 21, 0, 0, tzinfo=UTC),
                Decimal("420.50"),
            ),
            Ticker("GOOGL"): create_price_point(
                Ticker("GOOGL"),
                datetime(2026, 1, 16, 21, 0, 0, tzinfo=UTC),
                Decimal("180.25"),
            ),
        }

        mock_price_repository.get_latest_price = AsyncMock(return_value=None)
        mock_price_repository.get_price_at = AsyncMock(
            side_effect=lambda ticker, _: friday_prices.get(ticker)
        )

        with patch(
            "zebu.adapters.outbound.market_data.alpha_vantage_adapter.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(
                *args, **kwargs
            )

            # Execute
            result = await alpha_vantage_adapter.get_batch_prices(
                [Ticker("AAPL"), Ticker("MSFT"), Ticker("GOOGL")]
            )

            # Assert: Should return all three prices from database
            assert len(result) == 3
            assert Ticker("AAPL") in result
            assert Ticker("MSFT") in result
            assert Ticker("GOOGL") in result

            assert result[Ticker("AAPL")].price.amount == Decimal("259.96")
            assert result[Ticker("MSFT")].price.amount == Decimal("420.50")
            assert result[Ticker("GOOGL")].price.amount == Decimal("180.25")

            # All should come from database
            assert all(p.source == "database" for p in result.values())

            # Verify NO API calls were made
            mock_rate_limiter.consume_token.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_batch_prices_weekend_partial_results(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
        mock_price_repository: MagicMock,
        mock_rate_limiter: MagicMock,
    ) -> None:
        """Should return partial results if some tickers have no cached data."""
        # Mock current time as Sunday
        mock_now = datetime(2026, 1, 18, 15, 0, 0, tzinfo=UTC)

        # Only AAPL has cached data, MSFT doesn't
        def get_price_at_side_effect(ticker: Ticker, _: datetime) -> PricePoint | None:
            if ticker == Ticker("AAPL"):
                return create_price_point(
                    ticker,
                    datetime(2026, 1, 16, 21, 0, 0, tzinfo=UTC),
                    Decimal("259.96"),
                )
            return None

        mock_price_repository.get_latest_price = AsyncMock(return_value=None)
        mock_price_repository.get_price_at = AsyncMock(
            side_effect=get_price_at_side_effect
        )

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

            # Assert: Should only return AAPL (MSFT has no data)
            assert len(result) == 1
            assert Ticker("AAPL") in result
            assert Ticker("MSFT") not in result

            assert result[Ticker("AAPL")].price.amount == Decimal("259.96")

            # No API calls on weekend
            mock_rate_limiter.consume_token.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_batch_prices_trading_day_fetches_from_api(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
        mock_price_repository: MagicMock,
        mock_rate_limiter: MagicMock,
    ) -> None:
        """Should fetch from API on trading days when cache misses."""
        # Mock current time as Thursday, Jan 15, 2026 (trading day)
        mock_now = datetime(2026, 1, 15, 15, 0, 0, tzinfo=UTC)

        # No cached data
        mock_price_repository.get_latest_price = AsyncMock(return_value=None)
        mock_price_repository.upsert_price = AsyncMock()

        # Mock API fetch
        api_price = create_price_point(
            Ticker("AAPL"),
            mock_now,
            Decimal("260.00"),
        )
        alpha_vantage_adapter._fetch_from_api = AsyncMock(return_value=api_price)

        with patch(
            "zebu.adapters.outbound.market_data.alpha_vantage_adapter.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(
                *args, **kwargs
            )

            # Execute
            result = await alpha_vantage_adapter.get_batch_prices([Ticker("AAPL")])

            # Assert: Should fetch from API (this is a trading day)
            assert len(result) == 1
            assert Ticker("AAPL") in result

            # Verify API was called (rate limiter consumed)
            mock_rate_limiter.consume_token.assert_called_once()


class TestWeekendCacheTTL:
    """Tests for cache TTL behavior on weekends."""

    @pytest.mark.asyncio
    async def test_weekend_cache_has_longer_ttl(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
        mock_price_repository: MagicMock,
        mock_price_cache: MagicMock,
    ) -> None:
        """Should use 2 hour TTL for cached prices on weekends."""
        # Mock current time as Sunday
        mock_now = datetime(2026, 1, 18, 15, 0, 0, tzinfo=UTC)

        friday_price = create_price_point(
            Ticker("AAPL"),
            datetime(2026, 1, 16, 21, 0, 0, tzinfo=UTC),
            Decimal("259.96"),
        )
        mock_price_repository.get_latest_price = AsyncMock(return_value=None)
        mock_price_repository.get_price_at = AsyncMock(return_value=friday_price)

        with patch(
            "zebu.adapters.outbound.market_data.alpha_vantage_adapter.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(
                *args, **kwargs
            )

            # Execute
            await alpha_vantage_adapter.get_current_price(Ticker("AAPL"))

            # Assert: Cache should be set with 2 hour TTL (7200 seconds)
            mock_price_cache.set.assert_called_once()
            call_args = mock_price_cache.set.call_args
            assert call_args[1]["ttl"] == 7200  # 2 hours
