"""Unit tests for AlphaVantageAdapter weekend cache validation.

These tests verify the fix for Task 147 - ensuring that weekend and holiday
cache validation works correctly and doesn't cause unnecessary API calls.
"""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from zebu.adapters.outbound.market_data.alpha_vantage_adapter import (
    AlphaVantageAdapter,
)
from zebu.application.dtos.price_point import PricePoint
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
    return MagicMock()


@pytest.fixture
def mock_price_cache() -> MagicMock:
    """Provide mock price cache."""
    cache = MagicMock()
    cache.get_history = AsyncMock(return_value=None)
    cache.set_history = AsyncMock()
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
    ticker: Ticker, date: datetime, price: Decimal = Decimal("150.00")
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
        source="alpha_vantage",
        interval="1day",
    )


class TestGetLastTradingDay:
    """Tests for _get_last_trading_day() helper method."""

    def test_get_last_trading_day_weekday(
        self, alpha_vantage_adapter: AlphaVantageAdapter
    ) -> None:
        """Should return same day for weekdays (Mon-Fri) that are not holidays."""
        # Monday, June 2, 2026 (not a holiday)
        monday = datetime(2026, 6, 1, 10, 0, 0, tzinfo=UTC)
        result = alpha_vantage_adapter._get_last_trading_day(monday)
        assert result.date() == monday.date()
        assert result.hour == 21
        assert result.minute == 0

        # Wednesday, June 3, 2026 (not a holiday)
        wednesday = datetime(2026, 6, 3, 15, 30, 0, tzinfo=UTC)
        result = alpha_vantage_adapter._get_last_trading_day(wednesday)
        assert result.date() == wednesday.date()

        # Friday, June 5, 2026 (not a holiday)
        friday = datetime(2026, 6, 5, 9, 0, 0, tzinfo=UTC)
        result = alpha_vantage_adapter._get_last_trading_day(friday)
        assert result.date() == friday.date()

    def test_get_last_trading_day_saturday(
        self, alpha_vantage_adapter: AlphaVantageAdapter
    ) -> None:
        """Should return Friday for Saturday."""
        saturday = datetime(2026, 1, 31, 10, 0, 0, tzinfo=UTC)  # Saturday, Jan 31
        result = alpha_vantage_adapter._get_last_trading_day(saturday)
        # Should return Friday, Jan 30
        assert result.date().weekday() == 4  # Friday
        assert result.date().day == 30

    def test_get_last_trading_day_sunday(
        self, alpha_vantage_adapter: AlphaVantageAdapter
    ) -> None:
        """Should return Friday for Sunday."""
        sunday = datetime(2026, 2, 1, 10, 0, 0, tzinfo=UTC)  # Sunday, Feb 1
        result = alpha_vantage_adapter._get_last_trading_day(sunday)
        # Should return Friday, Jan 30
        assert result.date().weekday() == 4  # Friday
        assert result.date().month == 1
        assert result.date().day == 30

    def test_get_last_trading_day_monday_morning(
        self, alpha_vantage_adapter: AlphaVantageAdapter
    ) -> None:
        """Should return Monday for Monday morning (non-holiday)."""
        # Monday, June 1, 2026 (not a holiday)
        monday_morning = datetime(2026, 6, 1, 9, 0, 0, tzinfo=UTC)
        result = alpha_vantage_adapter._get_last_trading_day(monday_morning)
        # Monday is a weekday and not a holiday, so should return Monday
        assert result.date().weekday() == 0  # Monday
        assert result.date() == monday_morning.date()


class TestWeekendCacheValidation:
    """Tests for weekend cache validation scenarios."""

    def test_cache_complete_on_saturday_with_friday_data(
        self, alpha_vantage_adapter: AlphaVantageAdapter
    ) -> None:
        """Should accept Friday data as complete when requesting on Saturday."""
        ticker = Ticker("AAPL")

        # Saturday, Jan 31, 10:00 AM
        mock_now = datetime(2026, 1, 31, 10, 0, 0, tzinfo=UTC)

        with patch(
            "zebu.adapters.outbound.market_data.alpha_vantage_adapter.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(
                *args, **kwargs
            )

            # Request data through Saturday
            start = datetime(2026, 1, 20, 0, 0, 0, tzinfo=UTC)
            end = datetime(2026, 1, 31, 23, 59, 59, tzinfo=UTC)

            # Cache has data through Friday (Jan 30)
            cached_data = [
                create_price_point(
                    ticker, datetime(2026, 1, 20, 21, 0, 0, tzinfo=UTC)
                ),  # Mon
                create_price_point(
                    ticker, datetime(2026, 1, 21, 21, 0, 0, tzinfo=UTC)
                ),  # Tue
                create_price_point(
                    ticker, datetime(2026, 1, 22, 21, 0, 0, tzinfo=UTC)
                ),  # Wed
                create_price_point(
                    ticker, datetime(2026, 1, 23, 21, 0, 0, tzinfo=UTC)
                ),  # Thu
                create_price_point(
                    ticker, datetime(2026, 1, 29, 21, 0, 0, tzinfo=UTC)
                ),  # Thu
                create_price_point(
                    ticker, datetime(2026, 1, 30, 21, 0, 0, tzinfo=UTC)
                ),  # Friday
            ]

            # Should be considered complete
            result = alpha_vantage_adapter._is_cache_complete(cached_data, start, end)

            assert result is True

    def test_cache_complete_on_sunday_with_friday_data(
        self, alpha_vantage_adapter: AlphaVantageAdapter
    ) -> None:
        """Should accept Friday data as complete when requesting on Sunday."""
        ticker = Ticker("AAPL")

        # Sunday, Feb 1, 10:00 AM
        mock_now = datetime(2026, 2, 1, 10, 0, 0, tzinfo=UTC)

        with patch(
            "zebu.adapters.outbound.market_data.alpha_vantage_adapter.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(
                *args, **kwargs
            )

            # Request data through Sunday
            start = datetime(2026, 1, 20, 0, 0, 0, tzinfo=UTC)
            end = datetime(2026, 2, 1, 23, 59, 59, tzinfo=UTC)

            # Cache has data through Friday (Jan 30)
            cached_data = [
                create_price_point(
                    ticker, datetime(2026, 1, 20, 21, 0, 0, tzinfo=UTC)
                ),  # Mon
                create_price_point(
                    ticker, datetime(2026, 1, 21, 21, 0, 0, tzinfo=UTC)
                ),  # Tue
                create_price_point(
                    ticker, datetime(2026, 1, 22, 21, 0, 0, tzinfo=UTC)
                ),  # Wed
                create_price_point(
                    ticker, datetime(2026, 1, 23, 21, 0, 0, tzinfo=UTC)
                ),  # Thu
                create_price_point(
                    ticker, datetime(2026, 1, 29, 21, 0, 0, tzinfo=UTC)
                ),  # Thu
                create_price_point(
                    ticker, datetime(2026, 1, 30, 21, 0, 0, tzinfo=UTC)
                ),  # Friday Jan 30
            ]

            # Should be considered complete
            result = alpha_vantage_adapter._is_cache_complete(cached_data, start, end)

            assert result is True

    def test_cache_complete_on_monday_morning_with_friday_data(
        self, alpha_vantage_adapter: AlphaVantageAdapter
    ) -> None:
        """Should accept Friday data as complete on Monday before market close."""
        ticker = Ticker("AAPL")

        # Monday, Feb 2, 9:00 AM (before 21:00 market close)
        mock_now = datetime(2026, 2, 2, 9, 0, 0, tzinfo=UTC)

        with patch(
            "zebu.adapters.outbound.market_data.alpha_vantage_adapter.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(
                *args, **kwargs
            )

            # Request data through Monday
            start = datetime(2026, 1, 20, 0, 0, 0, tzinfo=UTC)
            end = datetime(2026, 2, 2, 23, 59, 59, tzinfo=UTC)

            # Cache has data through Friday (Jan 30)
            cached_data = [
                create_price_point(ticker, datetime(2026, 1, 20, 21, 0, 0, tzinfo=UTC)),
                create_price_point(ticker, datetime(2026, 1, 21, 21, 0, 0, tzinfo=UTC)),
                create_price_point(ticker, datetime(2026, 1, 22, 21, 0, 0, tzinfo=UTC)),
                create_price_point(ticker, datetime(2026, 1, 23, 21, 0, 0, tzinfo=UTC)),
                create_price_point(ticker, datetime(2026, 1, 29, 21, 0, 0, tzinfo=UTC)),
                create_price_point(
                    ticker, datetime(2026, 1, 30, 21, 0, 0, tzinfo=UTC)
                ),  # Friday
            ]

            # Should be considered complete (market hasn't closed on Monday yet)
            result = alpha_vantage_adapter._is_cache_complete(cached_data, start, end)

            assert result is True

    def test_cache_incomplete_on_tuesday_with_friday_data(
        self, alpha_vantage_adapter: AlphaVantageAdapter
    ) -> None:
        """Should reject Friday data as incomplete on Tuesday morning."""
        ticker = Ticker("AAPL")

        # Tuesday, Feb 3, 9:00 AM (before market close)
        mock_now = datetime(2026, 2, 3, 9, 0, 0, tzinfo=UTC)

        with patch(
            "zebu.adapters.outbound.market_data.alpha_vantage_adapter.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(
                *args, **kwargs
            )

            # Request data through Tuesday
            start = datetime(2026, 1, 20, 0, 0, 0, tzinfo=UTC)
            end = datetime(2026, 2, 3, 23, 59, 59, tzinfo=UTC)

            # Cache only has data through Friday (missing Monday)
            cached_data = [
                create_price_point(ticker, datetime(2026, 1, 20, 21, 0, 0, tzinfo=UTC)),
                create_price_point(ticker, datetime(2026, 1, 21, 21, 0, 0, tzinfo=UTC)),
                create_price_point(ticker, datetime(2026, 1, 22, 21, 0, 0, tzinfo=UTC)),
                create_price_point(ticker, datetime(2026, 1, 23, 21, 0, 0, tzinfo=UTC)),
                create_price_point(ticker, datetime(2026, 1, 29, 21, 0, 0, tzinfo=UTC)),
                create_price_point(ticker, datetime(2026, 1, 30, 21, 0, 0, tzinfo=UTC)),
            ]

            # Should be incomplete (missing Monday, the last trading day)
            result = alpha_vantage_adapter._is_cache_complete(cached_data, start, end)

            assert result is False

    def test_cache_incomplete_on_monday_after_market_close_with_friday_data(
        self, alpha_vantage_adapter: AlphaVantageAdapter
    ) -> None:
        """Should reject Friday data as incomplete on Monday after market close."""
        ticker = Ticker("AAPL")

        # Monday, Feb 2, 10:00 PM (after 21:00 market close)
        mock_now = datetime(2026, 2, 2, 22, 0, 0, tzinfo=UTC)

        with patch(
            "zebu.adapters.outbound.market_data.alpha_vantage_adapter.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(
                *args, **kwargs
            )

            # Request data through Monday
            start = datetime(2026, 1, 20, 0, 0, 0, tzinfo=UTC)
            end = datetime(2026, 2, 2, 23, 59, 59, tzinfo=UTC)

            # Cache only has data through Friday (missing Monday)
            cached_data = [
                create_price_point(ticker, datetime(2026, 1, 20, 21, 0, 0, tzinfo=UTC)),
                create_price_point(ticker, datetime(2026, 1, 21, 21, 0, 0, tzinfo=UTC)),
                create_price_point(ticker, datetime(2026, 1, 22, 21, 0, 0, tzinfo=UTC)),
                create_price_point(ticker, datetime(2026, 1, 23, 21, 0, 0, tzinfo=UTC)),
                create_price_point(ticker, datetime(2026, 1, 29, 21, 0, 0, tzinfo=UTC)),
                create_price_point(ticker, datetime(2026, 1, 30, 21, 0, 0, tzinfo=UTC)),
            ]

            # Should be incomplete (market closed, should have Monday's data)
            result = alpha_vantage_adapter._is_cache_complete(cached_data, start, end)

            assert result is False


class TestHistoricalRequestsWithWeekendEndDates:
    """Tests for historical requests that end on weekends."""

    def test_historical_request_ending_saturday(
        self, alpha_vantage_adapter: AlphaVantageAdapter
    ) -> None:
        """Should accept Friday data for historical request ending on Saturday."""
        ticker = Ticker("AAPL")

        # Request historical range ending on Saturday (Jan 31)
        start = datetime(2026, 1, 20, 0, 0, 0, tzinfo=UTC)
        end = datetime(2026, 1, 31, 23, 59, 59, tzinfo=UTC)  # Saturday

        # Cache has data through Friday (Jan 17)
        cached_data = [
            create_price_point(ticker, datetime(2026, 1, 10, 21, 0, 0, tzinfo=UTC)),
            create_price_point(ticker, datetime(2026, 1, 13, 21, 0, 0, tzinfo=UTC)),
            create_price_point(ticker, datetime(2026, 1, 14, 21, 0, 0, tzinfo=UTC)),
            create_price_point(ticker, datetime(2026, 1, 15, 21, 0, 0, tzinfo=UTC)),
            create_price_point(ticker, datetime(2026, 1, 16, 21, 0, 0, tzinfo=UTC)),
            create_price_point(
                ticker, datetime(2026, 1, 17, 21, 0, 0, tzinfo=UTC)
            ),  # Friday
        ]

        # Should be complete (Friday is last trading day before Saturday)
        result = alpha_vantage_adapter._is_cache_complete(cached_data, start, end)

        assert result is True

    def test_historical_request_ending_sunday(
        self, alpha_vantage_adapter: AlphaVantageAdapter
    ) -> None:
        """Should accept Friday data for historical request ending on Sunday."""
        ticker = Ticker("AAPL")

        # Request historical range ending on Sunday (Feb 1)
        start = datetime(2026, 1, 20, 0, 0, 0, tzinfo=UTC)
        end = datetime(2026, 2, 1, 23, 59, 59, tzinfo=UTC)  # Sunday

        # Cache has data through Friday (Jan 17)
        cached_data = [
            create_price_point(ticker, datetime(2026, 1, 10, 21, 0, 0, tzinfo=UTC)),
            create_price_point(ticker, datetime(2026, 1, 13, 21, 0, 0, tzinfo=UTC)),
            create_price_point(ticker, datetime(2026, 1, 14, 21, 0, 0, tzinfo=UTC)),
            create_price_point(ticker, datetime(2026, 1, 15, 21, 0, 0, tzinfo=UTC)),
            create_price_point(ticker, datetime(2026, 1, 16, 21, 0, 0, tzinfo=UTC)),
            create_price_point(
                ticker, datetime(2026, 1, 17, 21, 0, 0, tzinfo=UTC)
            ),  # Friday
        ]

        # Should be complete (Friday is last trading day before Sunday)
        result = alpha_vantage_adapter._is_cache_complete(cached_data, start, end)

        assert result is True


class TestWeekendNoRepeatedAPICalls:
    """Integration test for the reported bug.

    Tests weekend requests causing repeated API calls.
    """

    async def test_weekend_does_not_trigger_repeated_api_calls(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
        mock_price_repository: MagicMock,
        mock_rate_limiter: MagicMock,
    ) -> None:
        """Test that weekend requests don't cause repeated API calls.

        This is the core bug scenario from Task 147:
        1. Populate cache with Friday's data
        2. Make request on Sunday through Sunday
        3. Should return cached data without API call
        4. Repeat request - still no API call
        """
        ticker = Ticker("AAPL")

        # Setup: Friday, Jan 30 data in cache (via PostgreSQL)
        friday_data = [
            create_price_point(ticker, datetime(2026, 1, 10, 21, 0, 0, tzinfo=UTC)),
            create_price_point(ticker, datetime(2026, 1, 13, 21, 0, 0, tzinfo=UTC)),
            create_price_point(ticker, datetime(2026, 1, 14, 21, 0, 0, tzinfo=UTC)),
            create_price_point(ticker, datetime(2026, 1, 15, 21, 0, 0, tzinfo=UTC)),
            create_price_point(ticker, datetime(2026, 1, 16, 21, 0, 0, tzinfo=UTC)),
            create_price_point(ticker, datetime(2026, 1, 30, 21, 0, 0, tzinfo=UTC)),
        ]
        mock_price_repository.get_price_history = AsyncMock(return_value=friday_data)

        # Simulate Sunday, Feb 1, 10:00 AM
        mock_now = datetime(2026, 2, 1, 10, 0, 0, tzinfo=UTC)

        with patch(
            "zebu.adapters.outbound.market_data.alpha_vantage_adapter.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(
                *args, **kwargs
            )

            # First request
            result1 = await alpha_vantage_adapter.get_price_history(
                ticker,
                start=datetime(2026, 1, 20, tzinfo=UTC),
                end=datetime(2026, 2, 1, tzinfo=UTC),
            )

            # Should return Friday's data
            assert len(result1) == 6
            assert result1[-1].timestamp.date().weekday() == 4  # Friday

            # Verify no API call was made (rate limiter wasn't consumed)
            mock_rate_limiter.consume_token.assert_not_called()

            # Second request immediately after
            result2 = await alpha_vantage_adapter.get_price_history(
                ticker,
                start=datetime(2026, 1, 20, tzinfo=UTC),
                end=datetime(2026, 2, 1, tzinfo=UTC),
            )

            # Should still return cached data without API call
            assert len(result2) == 6
            # Still no API call
            mock_rate_limiter.consume_token.assert_not_called()
