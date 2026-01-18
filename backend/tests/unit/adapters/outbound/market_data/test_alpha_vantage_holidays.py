"""Integration tests for AlphaVantageAdapter holiday cache validation.

These tests verify that the market holiday calendar correctly prevents wasteful
API calls on days after holidays, similar to how weekend validation works.
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


class TestGetLastTradingDayWithHolidays:
    """Tests for _get_last_trading_day() with market holidays."""

    def test_get_last_trading_day_on_independence_day(
        self, alpha_vantage_adapter: AlphaVantageAdapter
    ) -> None:
        """Should return July 3 when requesting ON July 4 (holiday itself)."""
        # Thursday, July 4, 2024, 10:00 AM (Independence Day - holiday)
        thursday = datetime(2024, 7, 4, 10, 0, 0, tzinfo=UTC)
        result = alpha_vantage_adapter._get_last_trading_day(thursday)

        # Should return Wednesday, July 3 (last trading day before holiday)
        assert result.date().day == 3
        assert result.date().month == 7
        assert result.date().weekday() == 2  # Wednesday

    def test_get_last_trading_day_on_christmas(
        self, alpha_vantage_adapter: AlphaVantageAdapter
    ) -> None:
        """Should return Dec 24 when requesting ON Dec 25 (holiday itself)."""
        # Wednesday, Dec 25, 2024, 10:00 AM (Christmas - holiday)
        wednesday = datetime(2024, 12, 25, 10, 0, 0, tzinfo=UTC)
        result = alpha_vantage_adapter._get_last_trading_day(wednesday)

        # Should return Tuesday, Dec 24 (last trading day before holiday)
        assert result.date().day == 24
        assert result.date().month == 12
        assert result.date().weekday() == 1  # Tuesday

    def test_get_last_trading_day_after_independence_day(
        self, alpha_vantage_adapter: AlphaVantageAdapter
    ) -> None:
        """Should return same day when requesting on July 5 (regular trading day)."""
        # Friday, July 5, 2024, 10:00 AM (July 4 was Thursday holiday)
        # July 5 is a Friday, which is a regular trading day
        friday = datetime(2024, 7, 5, 10, 0, 0, tzinfo=UTC)
        result = alpha_vantage_adapter._get_last_trading_day(friday)

        # Should return Friday, July 5 (it's a regular trading day)
        assert result.date().day == 5
        assert result.date().month == 7
        assert result.date().weekday() == 4  # Friday

    def test_get_last_trading_day_after_christmas(
        self, alpha_vantage_adapter: AlphaVantageAdapter
    ) -> None:
        """Should return same day when requesting on Dec 26 (regular trading day)."""
        # Thursday, Dec 26, 2024, 10:00 AM (Dec 25 was Wednesday holiday)
        # Dec 26 is a Thursday, which is a regular trading day
        thursday = datetime(2024, 12, 26, 10, 0, 0, tzinfo=UTC)
        result = alpha_vantage_adapter._get_last_trading_day(thursday)

        # Should return Thursday, Dec 26 (it's a regular trading day)
        assert result.date().day == 26
        assert result.date().month == 12
        assert result.date().weekday() == 3  # Thursday

    def test_get_last_trading_day_after_thanksgiving(
        self, alpha_vantage_adapter: AlphaVantageAdapter
    ) -> None:
        """Should return Nov 27 when requesting on Thanksgiving (Nov 28)."""
        # Thursday, Nov 28, 2024 (Thanksgiving)
        thanksgiving = datetime(2024, 11, 28, 10, 0, 0, tzinfo=UTC)
        result = alpha_vantage_adapter._get_last_trading_day(thanksgiving)

        # Should return Wednesday, Nov 27
        assert result.date().day == 27
        assert result.date().month == 11
        assert result.date().weekday() == 2  # Wednesday

    def test_get_last_trading_day_after_mlk_day(
        self, alpha_vantage_adapter: AlphaVantageAdapter
    ) -> None:
        """Should return Jan 12 when requesting on Jan 15 (MLK Day)."""
        # Monday, Jan 15, 2024 (MLK Day)
        mlk_day = datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)
        result = alpha_vantage_adapter._get_last_trading_day(mlk_day)

        # Should return Friday, Jan 12
        assert result.date().day == 12
        assert result.date().month == 1
        assert result.date().weekday() == 4  # Friday

    def test_get_last_trading_day_after_long_weekend(
        self, alpha_vantage_adapter: AlphaVantageAdapter
    ) -> None:
        """Should skip holiday + weekend when necessary."""
        # Monday, Jan 20, 2025 (MLK Day - 3rd Monday in January)
        # This is a Monday holiday, so last trading day is Friday Jan 17
        mlk_2025 = datetime(2025, 1, 20, 10, 0, 0, tzinfo=UTC)
        result = alpha_vantage_adapter._get_last_trading_day(mlk_2025)

        # Should return Friday, Jan 17
        assert result.date().day == 17
        assert result.date().month == 1
        assert result.date().weekday() == 4  # Friday

    def test_get_last_trading_day_independence_day_saturday_2026(
        self, alpha_vantage_adapter: AlphaVantageAdapter
    ) -> None:
        """Should return July 2 when July 4 is Saturday (observed Friday July 3)."""
        # Sunday, July 5, 2026 (after Saturday July 4)
        # July 4 is Saturday, observed Friday July 3
        sunday = datetime(2026, 7, 5, 10, 0, 0, tzinfo=UTC)
        result = alpha_vantage_adapter._get_last_trading_day(sunday)

        # Should return Thursday, July 2 (last trading day before observed holiday)
        assert result.date().day == 2
        assert result.date().month == 7
        assert result.date().weekday() == 3  # Thursday


class TestCacheCompleteAfterHolidays:
    """Tests for cache validation scenarios after market holidays."""

    def test_cache_complete_after_independence_day_holiday(
        self, alpha_vantage_adapter: AlphaVantageAdapter
    ) -> None:
        """Should accept July 3rd data as complete when requesting on July 5th."""
        ticker = Ticker("AAPL")

        # Friday, July 5, 2024, 10:00 AM (after July 4th holiday)
        mock_now = datetime(2024, 7, 5, 10, 0, 0, tzinfo=UTC)

        with patch(
            "zebu.adapters.outbound.market_data.alpha_vantage_adapter.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(
                *args, **kwargs
            )

            # Request data through Friday (July 5)
            start = datetime(2024, 6, 28, 0, 0, 0, tzinfo=UTC)
            end = datetime(2024, 7, 5, 23, 59, 59, tzinfo=UTC)

            # Cache has data through July 3 (last trading day before holiday)
            cached_data = [
                create_price_point(ticker, datetime(2024, 6, 28, 21, 0, 0, tzinfo=UTC)),
                create_price_point(ticker, datetime(2024, 7, 1, 21, 0, 0, tzinfo=UTC)),
                create_price_point(ticker, datetime(2024, 7, 2, 21, 0, 0, tzinfo=UTC)),
                create_price_point(
                    ticker, datetime(2024, 7, 3, 21, 0, 0, tzinfo=UTC)
                ),  # Last trading day
            ]

            # Should be complete (market closed July 4, not open yet on July 5)
            result = alpha_vantage_adapter._is_cache_complete(cached_data, start, end)

            assert result is True

    def test_cache_complete_after_christmas_holiday(
        self, alpha_vantage_adapter: AlphaVantageAdapter
    ) -> None:
        """Should accept Dec 24 data as complete when requesting on Dec 26."""
        ticker = Ticker("AAPL")

        # Thursday, Dec 26, 2024, 10:00 AM (after Christmas)
        mock_now = datetime(2024, 12, 26, 10, 0, 0, tzinfo=UTC)

        with patch(
            "zebu.adapters.outbound.market_data.alpha_vantage_adapter.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(
                *args, **kwargs
            )

            # Request data through Dec 26
            start = datetime(2024, 12, 18, 0, 0, 0, tzinfo=UTC)
            end = datetime(2024, 12, 26, 23, 59, 59, tzinfo=UTC)

            # Cache has data through Dec 24 (last trading day before Christmas)
            cached_data = [
                create_price_point(
                    ticker, datetime(2024, 12, 18, 21, 0, 0, tzinfo=UTC)
                ),
                create_price_point(
                    ticker, datetime(2024, 12, 19, 21, 0, 0, tzinfo=UTC)
                ),
                create_price_point(
                    ticker, datetime(2024, 12, 20, 21, 0, 0, tzinfo=UTC)
                ),
                create_price_point(
                    ticker, datetime(2024, 12, 23, 21, 0, 0, tzinfo=UTC)
                ),
                create_price_point(
                    ticker, datetime(2024, 12, 24, 21, 0, 0, tzinfo=UTC)
                ),  # Last trading day
            ]

            # Should be complete (market closed Dec 25, not open yet on Dec 26)
            result = alpha_vantage_adapter._is_cache_complete(cached_data, start, end)

            assert result is True

    def test_cache_complete_after_thanksgiving_long_weekend(
        self, alpha_vantage_adapter: AlphaVantageAdapter
    ) -> None:
        """Should accept Wed data as complete on Monday after Thanksgiving weekend."""
        ticker = Ticker("AAPL")

        # Monday, Dec 2, 2024, 9:00 AM (after Thanksgiving weekend)
        # Thanksgiving was Nov 28 (Thursday)
        mock_now = datetime(2024, 12, 2, 9, 0, 0, tzinfo=UTC)

        with patch(
            "zebu.adapters.outbound.market_data.alpha_vantage_adapter.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(
                *args, **kwargs
            )

            # Request data through Monday Dec 2
            start = datetime(2024, 11, 20, 0, 0, 0, tzinfo=UTC)
            end = datetime(2024, 12, 2, 23, 59, 59, tzinfo=UTC)

            # Cache has data through Nov 27 (Wed before Thanksgiving)
            # and Nov 29 (Black Friday)
            cached_data = [
                create_price_point(
                    ticker, datetime(2024, 11, 20, 21, 0, 0, tzinfo=UTC)
                ),
                create_price_point(
                    ticker, datetime(2024, 11, 21, 21, 0, 0, tzinfo=UTC)
                ),
                create_price_point(
                    ticker, datetime(2024, 11, 22, 21, 0, 0, tzinfo=UTC)
                ),
                create_price_point(
                    ticker, datetime(2024, 11, 25, 21, 0, 0, tzinfo=UTC)
                ),
                create_price_point(
                    ticker, datetime(2024, 11, 26, 21, 0, 0, tzinfo=UTC)
                ),
                create_price_point(
                    ticker, datetime(2024, 11, 27, 21, 0, 0, tzinfo=UTC)
                ),  # Wed before Thanksgiving
                create_price_point(
                    ticker, datetime(2024, 11, 29, 21, 0, 0, tzinfo=UTC)
                ),  # Black Friday (market open)
            ]

            # Should be complete (market hasn't closed on Monday Dec 2 yet)
            result = alpha_vantage_adapter._is_cache_complete(cached_data, start, end)

            assert result is True

    def test_cache_complete_after_mlk_weekend(
        self, alpha_vantage_adapter: AlphaVantageAdapter
    ) -> None:
        """Should accept Friday data as complete on Tuesday after MLK Day weekend."""
        ticker = Ticker("AAPL")

        # Tuesday, Jan 16, 2024, 9:00 AM (after MLK Day Monday Jan 15)
        mock_now = datetime(2024, 1, 16, 9, 0, 0, tzinfo=UTC)

        with patch(
            "zebu.adapters.outbound.market_data.alpha_vantage_adapter.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(
                *args, **kwargs
            )

            # Request data through Tuesday Jan 16
            start = datetime(2024, 1, 8, 0, 0, 0, tzinfo=UTC)
            end = datetime(2024, 1, 16, 23, 59, 59, tzinfo=UTC)

            # Cache has data through Friday Jan 12 (before MLK Day)
            cached_data = [
                create_price_point(ticker, datetime(2024, 1, 8, 21, 0, 0, tzinfo=UTC)),
                create_price_point(ticker, datetime(2024, 1, 9, 21, 0, 0, tzinfo=UTC)),
                create_price_point(ticker, datetime(2024, 1, 10, 21, 0, 0, tzinfo=UTC)),
                create_price_point(ticker, datetime(2024, 1, 11, 21, 0, 0, tzinfo=UTC)),
                create_price_point(
                    ticker, datetime(2024, 1, 12, 21, 0, 0, tzinfo=UTC)
                ),  # Friday before MLK Day
            ]

            # Should be complete (market hasn't closed on Tuesday yet)
            result = alpha_vantage_adapter._is_cache_complete(cached_data, start, end)

            assert result is True

    def test_cache_incomplete_on_wednesday_missing_tuesday_after_holiday(
        self, alpha_vantage_adapter: AlphaVantageAdapter
    ) -> None:
        """Should reject old data on Wednesday when missing Tuesday after holiday."""
        ticker = Ticker("AAPL")

        # Wednesday, Jan 17, 2024, 9:00 AM
        mock_now = datetime(2024, 1, 17, 9, 0, 0, tzinfo=UTC)

        with patch(
            "zebu.adapters.outbound.market_data.alpha_vantage_adapter.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(
                *args, **kwargs
            )

            # Request data through Wednesday Jan 17
            start = datetime(2024, 1, 8, 0, 0, 0, tzinfo=UTC)
            end = datetime(2024, 1, 17, 23, 59, 59, tzinfo=UTC)

            # Cache only has data through Friday Jan 12 (missing Tuesday Jan 16)
            cached_data = [
                create_price_point(ticker, datetime(2024, 1, 8, 21, 0, 0, tzinfo=UTC)),
                create_price_point(ticker, datetime(2024, 1, 9, 21, 0, 0, tzinfo=UTC)),
                create_price_point(ticker, datetime(2024, 1, 10, 21, 0, 0, tzinfo=UTC)),
                create_price_point(ticker, datetime(2024, 1, 11, 21, 0, 0, tzinfo=UTC)),
                create_price_point(ticker, datetime(2024, 1, 12, 21, 0, 0, tzinfo=UTC)),
            ]

            # Should be incomplete (missing Tuesday, the last trading day)
            result = alpha_vantage_adapter._is_cache_complete(cached_data, start, end)

            assert result is False


class TestHolidayNoRepeatedAPICalls:
    """Integration tests verifying no wasteful API calls on holidays."""

    async def test_independence_day_no_api_call(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
        mock_price_repository: MagicMock,
        mock_rate_limiter: MagicMock,
    ) -> None:
        """Test that requests after July 4th don't cause API calls.

        Scenario:
        1. Cache has data through July 3 (last trading day)
        2. Make request on July 5 through July 5
        3. Should return cached data without API call
        """
        ticker = Ticker("AAPL")

        # Setup: July 3 data in cache (via PostgreSQL)
        july_data = [
            create_price_point(ticker, datetime(2024, 6, 28, 21, 0, 0, tzinfo=UTC)),
            create_price_point(ticker, datetime(2024, 7, 1, 21, 0, 0, tzinfo=UTC)),
            create_price_point(ticker, datetime(2024, 7, 2, 21, 0, 0, tzinfo=UTC)),
            create_price_point(ticker, datetime(2024, 7, 3, 21, 0, 0, tzinfo=UTC)),
        ]
        mock_price_repository.get_price_history = AsyncMock(return_value=july_data)

        # Simulate Friday, July 5, 10:00 AM
        mock_now = datetime(2024, 7, 5, 10, 0, 0, tzinfo=UTC)

        with patch(
            "zebu.adapters.outbound.market_data.alpha_vantage_adapter.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(
                *args, **kwargs
            )

            # Request data
            result = await alpha_vantage_adapter.get_price_history(
                ticker,
                start=datetime(2024, 6, 28, tzinfo=UTC),
                end=datetime(2024, 7, 5, tzinfo=UTC),
            )

            # Should return July 3 data
            assert len(result) == 4
            assert result[-1].timestamp.date().day == 3

            # Verify no API call was made
            mock_rate_limiter.consume_token.assert_not_called()

    async def test_christmas_no_api_call(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
        mock_price_repository: MagicMock,
        mock_rate_limiter: MagicMock,
    ) -> None:
        """Test that requests after Christmas don't cause API calls."""
        ticker = Ticker("AAPL")

        # Setup: Dec 24 data in cache
        december_data = [
            create_price_point(ticker, datetime(2024, 12, 18, 21, 0, 0, tzinfo=UTC)),
            create_price_point(ticker, datetime(2024, 12, 19, 21, 0, 0, tzinfo=UTC)),
            create_price_point(ticker, datetime(2024, 12, 20, 21, 0, 0, tzinfo=UTC)),
            create_price_point(ticker, datetime(2024, 12, 23, 21, 0, 0, tzinfo=UTC)),
            create_price_point(ticker, datetime(2024, 12, 24, 21, 0, 0, tzinfo=UTC)),
        ]
        mock_price_repository.get_price_history = AsyncMock(return_value=december_data)

        # Simulate Thursday, Dec 26, 10:00 AM
        mock_now = datetime(2024, 12, 26, 10, 0, 0, tzinfo=UTC)

        with patch(
            "zebu.adapters.outbound.market_data.alpha_vantage_adapter.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(
                *args, **kwargs
            )

            # Request data
            result = await alpha_vantage_adapter.get_price_history(
                ticker,
                start=datetime(2024, 12, 18, tzinfo=UTC),
                end=datetime(2024, 12, 26, tzinfo=UTC),
            )

            # Should return Dec 24 data
            assert len(result) == 5
            assert result[-1].timestamp.date().day == 24

            # Verify no API call was made
            mock_rate_limiter.consume_token.assert_not_called()

    async def test_thanksgiving_weekend_no_api_call(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
        mock_price_repository: MagicMock,
        mock_rate_limiter: MagicMock,
    ) -> None:
        """Test that requests after Thanksgiving weekend don't cause API calls."""
        ticker = Ticker("AAPL")

        # Setup: Data through Nov 29 (Black Friday - market open)
        november_data = [
            create_price_point(ticker, datetime(2024, 11, 20, 21, 0, 0, tzinfo=UTC)),
            create_price_point(ticker, datetime(2024, 11, 21, 21, 0, 0, tzinfo=UTC)),
            create_price_point(ticker, datetime(2024, 11, 22, 21, 0, 0, tzinfo=UTC)),
            create_price_point(ticker, datetime(2024, 11, 25, 21, 0, 0, tzinfo=UTC)),
            create_price_point(ticker, datetime(2024, 11, 26, 21, 0, 0, tzinfo=UTC)),
            create_price_point(ticker, datetime(2024, 11, 27, 21, 0, 0, tzinfo=UTC)),
            create_price_point(ticker, datetime(2024, 11, 29, 21, 0, 0, tzinfo=UTC)),
        ]
        mock_price_repository.get_price_history = AsyncMock(return_value=november_data)

        # Simulate Monday, Dec 2, 9:00 AM
        mock_now = datetime(2024, 12, 2, 9, 0, 0, tzinfo=UTC)

        with patch(
            "zebu.adapters.outbound.market_data.alpha_vantage_adapter.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(
                *args, **kwargs
            )

            # Request data
            result = await alpha_vantage_adapter.get_price_history(
                ticker,
                start=datetime(2024, 11, 20, tzinfo=UTC),
                end=datetime(2024, 12, 2, tzinfo=UTC),
            )

            # Should return data through Nov 29
            assert len(result) == 7
            assert result[-1].timestamp.date().day == 29

            # Verify no API call was made
            mock_rate_limiter.consume_token.assert_not_called()
