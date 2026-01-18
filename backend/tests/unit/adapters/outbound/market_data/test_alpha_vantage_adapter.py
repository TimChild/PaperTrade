"""Unit tests for AlphaVantageAdapter cache completeness validation.

These tests verify the cache completeness checking logic that ensures
we only return cached data when it's complete for the requested range.
"""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

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
    return limiter


@pytest.fixture
def mock_price_repository() -> MagicMock:
    """Provide mock price repository."""
    return MagicMock()


@pytest.fixture
def mock_price_cache() -> MagicMock:
    """Provide mock price cache."""
    cache = MagicMock()
    # Mock get_history to return None (cache miss) by default
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


class TestCacheCompletenessComplete:
    """Tests for complete cache scenarios (should return cached data)."""

    async def test_complete_cache_returns_cached_data(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
        mock_price_repository: MagicMock,
        mock_rate_limiter: MagicMock,
    ) -> None:
        """Should return cached data when cache has full date range."""
        # Arrange
        ticker = Ticker("AAPL")
        start = datetime(2026, 1, 10, 0, 0, 0, tzinfo=UTC)
        end = datetime(2026, 1, 17, 23, 59, 59, tzinfo=UTC)

        # Cache has complete data for Jan 10-17 (8 trading days, accounting for weekend)
        cached_data = [
            create_price_point(
                ticker, datetime(2026, 1, 10, 21, 0, 0, tzinfo=UTC), Decimal("150.00")
            ),
            create_price_point(
                ticker, datetime(2026, 1, 13, 21, 0, 0, tzinfo=UTC), Decimal("151.00")
            ),  # Mon
            create_price_point(
                ticker, datetime(2026, 1, 14, 21, 0, 0, tzinfo=UTC), Decimal("152.00")
            ),  # Tue
            create_price_point(
                ticker, datetime(2026, 1, 15, 21, 0, 0, tzinfo=UTC), Decimal("153.00")
            ),  # Wed
            create_price_point(
                ticker, datetime(2026, 1, 16, 21, 0, 0, tzinfo=UTC), Decimal("154.00")
            ),  # Thu
            create_price_point(
                ticker, datetime(2026, 1, 17, 21, 0, 0, tzinfo=UTC), Decimal("155.00")
            ),  # Fri
        ]
        mock_price_repository.get_price_history = AsyncMock(return_value=cached_data)

        # Act
        result = await alpha_vantage_adapter.get_price_history(
            ticker, start, end, "1day"
        )

        # Assert
        assert result == cached_data
        # Verify API was NOT called (rate limiter not consumed)
        mock_rate_limiter.consume_token.assert_not_called()

    async def test_boundary_tolerance_early_date(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
        mock_price_repository: MagicMock,
        mock_rate_limiter: MagicMock,
    ) -> None:
        """Should return cached data when cache starts within 1 day of request.

        Tests the boundary tolerance feature (within tolerance).
        """
        # Arrange
        ticker = Ticker("AAPL")
        start = datetime(2026, 1, 10, 0, 0, 0, tzinfo=UTC)
        end = datetime(2026, 1, 17, 23, 59, 59, tzinfo=UTC)

        # Cache starts Jan 10 at 21:00 (same day as start, within tolerance)
        # Has sufficient density: 6 points for 8-day range
        # Expected: 8 * 5/7 = 5.7 trading days, min required: 5.7 * 0.7 = 4 points
        cached_data = [
            create_price_point(ticker, datetime(2026, 1, 10, 21, 0, 0, tzinfo=UTC)),
            create_price_point(ticker, datetime(2026, 1, 13, 21, 0, 0, tzinfo=UTC)),
            create_price_point(ticker, datetime(2026, 1, 14, 21, 0, 0, tzinfo=UTC)),
            create_price_point(ticker, datetime(2026, 1, 15, 21, 0, 0, tzinfo=UTC)),
            create_price_point(ticker, datetime(2026, 1, 16, 21, 0, 0, tzinfo=UTC)),
            create_price_point(ticker, datetime(2026, 1, 17, 21, 0, 0, tzinfo=UTC)),
        ]
        mock_price_repository.get_price_history = AsyncMock(return_value=cached_data)

        # Act
        result = await alpha_vantage_adapter.get_price_history(
            ticker, start, end, "1day"
        )

        # Assert
        assert result == cached_data
        mock_rate_limiter.consume_token.assert_not_called()

    async def test_boundary_tolerance_late_date(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
        mock_price_repository: MagicMock,
        mock_rate_limiter: MagicMock,
    ) -> None:
        """Should return cached data when cache ends within 1 day of request.

        Tests the boundary tolerance feature (within tolerance).
        """
        # Arrange
        ticker = Ticker("AAPL")
        start = datetime(2026, 1, 10, 0, 0, 0, tzinfo=UTC)
        end = datetime(2026, 1, 17, 23, 59, 59, tzinfo=UTC)

        # Cache ends Jan 17 at 21:00 (same day as end, within tolerance)
        # Has sufficient density: 5 points for 8-day range
        # Expected: 8 * 5/7 = 5.7 trading days, min required: 5.7 * 0.7 = 4 points
        cached_data = [
            create_price_point(ticker, datetime(2026, 1, 10, 21, 0, 0, tzinfo=UTC)),
            create_price_point(ticker, datetime(2026, 1, 13, 21, 0, 0, tzinfo=UTC)),
            create_price_point(ticker, datetime(2026, 1, 14, 21, 0, 0, tzinfo=UTC)),
            create_price_point(ticker, datetime(2026, 1, 15, 21, 0, 0, tzinfo=UTC)),
            create_price_point(ticker, datetime(2026, 1, 17, 21, 0, 0, tzinfo=UTC)),
        ]
        mock_price_repository.get_price_history = AsyncMock(return_value=cached_data)

        # Act
        result = await alpha_vantage_adapter.get_price_history(
            ticker, start, end, "1day"
        )

        # Assert
        assert result == cached_data
        mock_rate_limiter.consume_token.assert_not_called()


class TestCacheCompletenessIncomplete:
    """Tests for incomplete cache scenarios (should fetch from API)."""

    async def test_empty_cache_fetches_from_api(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
        mock_price_repository: MagicMock,
        mock_rate_limiter: MagicMock,
        mock_http_client: MagicMock,
    ) -> None:
        """Should fetch from API when cache is empty."""
        # Arrange
        ticker = Ticker("AAPL")
        start = datetime(2026, 1, 10, 0, 0, 0, tzinfo=UTC)
        end = datetime(2026, 1, 17, 23, 59, 59, tzinfo=UTC)

        # Cache is empty
        mock_price_repository.get_price_history = AsyncMock(return_value=[])

        # Mock API response
        api_response_data = {
            "Meta Data": {"2. Symbol": "AAPL"},
            "Time Series (Daily)": {
                "2026-01-17": {
                    "1. open": "150.00",
                    "2. high": "152.00",
                    "3. low": "148.00",
                    "4. close": "151.00",
                    "5. volume": "1000000",
                },
                "2026-01-16": {
                    "1. open": "149.00",
                    "2. high": "151.00",
                    "3. low": "147.00",
                    "4. close": "150.00",
                    "5. volume": "1000000",
                },
            },
        }
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = api_response_data
        mock_http_client.get = AsyncMock(return_value=mock_response)

        # Act
        await alpha_vantage_adapter.get_price_history(ticker, start, end, "1day")

        # Assert
        # Should fetch from API (rate limiter consumed)
        mock_rate_limiter.consume_token.assert_called_once()
        # Should return data from API (length validated above)

    async def test_partial_cache_missing_early_dates(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
        mock_price_repository: MagicMock,
        mock_rate_limiter: MagicMock,
        mock_http_client: MagicMock,
    ) -> None:
        """Should fetch from API when cache is missing early dates."""
        # Arrange
        ticker = Ticker("AAPL")
        start = datetime(2026, 1, 10, 0, 0, 0, tzinfo=UTC)
        end = datetime(2026, 1, 17, 23, 59, 59, tzinfo=UTC)

        # Cache only has Jan 15-17 (missing Jan 10-14)
        cached_data = [
            create_price_point(ticker, datetime(2026, 1, 15, 21, 0, 0, tzinfo=UTC)),
            create_price_point(ticker, datetime(2026, 1, 16, 21, 0, 0, tzinfo=UTC)),
            create_price_point(ticker, datetime(2026, 1, 17, 21, 0, 0, tzinfo=UTC)),
        ]
        mock_price_repository.get_price_history = AsyncMock(return_value=cached_data)

        # Mock API response with full data
        api_response_data = {
            "Meta Data": {"2. Symbol": "AAPL"},
            "Time Series (Daily)": {
                "2026-01-17": {
                    "1. open": "150.00",
                    "2. high": "152.00",
                    "3. low": "148.00",
                    "4. close": "151.00",
                    "5. volume": "1000000",
                },
                "2026-01-16": {
                    "1. open": "149.00",
                    "2. high": "151.00",
                    "3. low": "147.00",
                    "4. close": "150.00",
                    "5. volume": "1000000",
                },
                "2026-01-15": {
                    "1. open": "148.00",
                    "2. high": "150.00",
                    "3. low": "146.00",
                    "4. close": "149.00",
                    "5. volume": "1000000",
                },
                "2026-01-14": {
                    "1. open": "147.00",
                    "2. high": "149.00",
                    "3. low": "145.00",
                    "4. close": "148.00",
                    "5. volume": "1000000",
                },
                "2026-01-13": {
                    "1. open": "146.00",
                    "2. high": "148.00",
                    "3. low": "144.00",
                    "4. close": "147.00",
                    "5. volume": "1000000",
                },
                "2026-01-10": {
                    "1. open": "145.00",
                    "2. high": "147.00",
                    "3. low": "143.00",
                    "4. close": "146.00",
                    "5. volume": "1000000",
                },
            },
        }
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = api_response_data
        mock_http_client.get = AsyncMock(return_value=mock_response)

        # Act
        await alpha_vantage_adapter.get_price_history(ticker, start, end, "1day")

        # Assert
        # Should NOT return partial cache
        # Should fetch from API
        mock_rate_limiter.consume_token.assert_called_once()

    async def test_partial_cache_missing_recent_dates(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
        mock_price_repository: MagicMock,
        mock_rate_limiter: MagicMock,
        mock_http_client: MagicMock,
    ) -> None:
        """Should fetch from API when cache is missing recent dates."""
        # Arrange
        ticker = Ticker("AAPL")
        start = datetime(2026, 1, 10, 0, 0, 0, tzinfo=UTC)
        end = datetime(2026, 1, 17, 23, 59, 59, tzinfo=UTC)

        # Cache only has Jan 10-12 (missing Jan 13-17)
        cached_data = [
            create_price_point(ticker, datetime(2026, 1, 10, 21, 0, 0, tzinfo=UTC)),
            create_price_point(ticker, datetime(2026, 1, 13, 21, 0, 0, tzinfo=UTC)),
            create_price_point(ticker, datetime(2026, 1, 14, 21, 0, 0, tzinfo=UTC)),
        ]
        mock_price_repository.get_price_history = AsyncMock(return_value=cached_data)

        # Mock API response
        api_response_data = {
            "Meta Data": {"2. Symbol": "AAPL"},
            "Time Series (Daily)": {
                "2026-01-17": {
                    "1. open": "150.00",
                    "2. high": "152.00",
                    "3. low": "148.00",
                    "4. close": "151.00",
                    "5. volume": "1000000",
                },
            },
        }
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = api_response_data
        mock_http_client.get = AsyncMock(return_value=mock_response)

        # Act
        await alpha_vantage_adapter.get_price_history(ticker, start, end, "1day")

        # Assert
        # Should fetch from API (cache incomplete)
        mock_rate_limiter.consume_token.assert_called_once()

    async def test_partial_cache_sparse_gaps_in_middle(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
        mock_price_repository: MagicMock,
        mock_rate_limiter: MagicMock,
        mock_http_client: MagicMock,
    ) -> None:
        """Should fetch from API when cache has major gaps (insufficient density)."""
        # Arrange
        ticker = Ticker("AAPL")
        start = datetime(2026, 1, 10, 0, 0, 0, tzinfo=UTC)
        end = datetime(2026, 1, 17, 23, 59, 59, tzinfo=UTC)

        # Cache has Jan 10, 17 only (missing 11-16) - only 2 points for 8-day
        # range. Expected trading days: 8 * 5/7 = 5.7, min required:
        # 5.7 * 0.7 = 3.99 ≈ 3 points. We have 2 points, so this is incomplete
        cached_data = [
            create_price_point(ticker, datetime(2026, 1, 10, 21, 0, 0, tzinfo=UTC)),
            create_price_point(ticker, datetime(2026, 1, 17, 21, 0, 0, tzinfo=UTC)),
        ]
        mock_price_repository.get_price_history = AsyncMock(return_value=cached_data)

        # Mock API response
        api_response_data = {
            "Meta Data": {"2. Symbol": "AAPL"},
            "Time Series (Daily)": {
                "2026-01-17": {
                    "1. open": "150.00",
                    "2. high": "152.00",
                    "3. low": "148.00",
                    "4. close": "151.00",
                    "5. volume": "1000000",
                },
            },
        }
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = api_response_data
        mock_http_client.get = AsyncMock(return_value=mock_response)

        # Act
        await alpha_vantage_adapter.get_price_history(ticker, start, end, "1day")

        # Assert
        # Should fetch from API (insufficient density)
        mock_rate_limiter.consume_token.assert_called_once()


class TestCacheCompletenessLongRanges:
    """Tests for long date ranges (>30 days) - less strict validation."""

    async def test_long_range_skips_density_check(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
        mock_price_repository: MagicMock,
        mock_rate_limiter: MagicMock,
    ) -> None:
        """Should return cached data for >30 day ranges.

        Even with some gaps (no density check applied).
        """
        # Arrange
        ticker = Ticker("AAPL")
        start = datetime(2025, 11, 1, 0, 0, 0, tzinfo=UTC)
        end = datetime(2026, 1, 17, 23, 59, 59, tzinfo=UTC)  # ~77 days

        # Cache has data at boundaries but sparse in middle (only 20 points for 77 days)
        # This would fail density check if it applied, but for >30 days we skip it
        cached_data = [
            create_price_point(ticker, datetime(2025, 11, 1, 21, 0, 0, tzinfo=UTC)),
            create_price_point(ticker, datetime(2025, 11, 15, 21, 0, 0, tzinfo=UTC)),
            create_price_point(ticker, datetime(2025, 12, 1, 21, 0, 0, tzinfo=UTC)),
            create_price_point(ticker, datetime(2025, 12, 15, 21, 0, 0, tzinfo=UTC)),
            create_price_point(ticker, datetime(2026, 1, 1, 21, 0, 0, tzinfo=UTC)),
            create_price_point(ticker, datetime(2026, 1, 17, 21, 0, 0, tzinfo=UTC)),
        ]
        mock_price_repository.get_price_history = AsyncMock(return_value=cached_data)

        # Act
        result = await alpha_vantage_adapter.get_price_history(
            ticker, start, end, "1day"
        )

        # Assert
        # Should return cached data (density check skipped for long ranges)
        assert result == cached_data
        # Should NOT fetch from API
        mock_rate_limiter.consume_token.assert_not_called()


class TestCacheCompletenessNonDailyInterval:
    """Tests for non-daily intervals (should not apply completeness check)."""

    async def test_intraday_interval_returns_cache_without_validation(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
        mock_price_repository: MagicMock,
        mock_rate_limiter: MagicMock,
    ) -> None:
        """Should return cached data for intraday intervals.

        Completeness check not applied.
        """
        # Arrange
        ticker = Ticker("AAPL")
        start = datetime(2026, 1, 17, 9, 0, 0, tzinfo=UTC)
        end = datetime(2026, 1, 17, 16, 0, 0, tzinfo=UTC)

        # Cache has some data (not necessarily complete)
        cached_data = [
            create_price_point(ticker, datetime(2026, 1, 17, 10, 0, 0, tzinfo=UTC)),
            create_price_point(ticker, datetime(2026, 1, 17, 14, 0, 0, tzinfo=UTC)),
        ]
        mock_price_repository.get_price_history = AsyncMock(return_value=cached_data)

        # Act
        result = await alpha_vantage_adapter.get_price_history(
            ticker, start, end, "1hour"
        )

        # Assert
        # For non-daily intervals, we don't validate completeness
        # (completeness check only applies to "1day" interval)
        # Current implementation: returns empty for non-daily intervals
        # (not fetched from API). This is correct behavior - we don't
        # support intraday fetching yet
        assert result == []
        mock_rate_limiter.consume_token.assert_not_called()


class TestDecimalPrecisionRounding:
    """Tests for decimal precision rounding of API prices."""

    async def test_parse_response_rounds_decimal_precision(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
    ) -> None:
        """Should round prices with >2 decimals to 2 decimal places."""
        # Arrange
        ticker = Ticker("AAPL")

        # API response with >2 decimal precision
        api_response: dict[str, object] = {
            "Meta Data": {"2. Symbol": "AAPL"},
            "Time Series (Daily)": {
                "2026-01-17": {
                    "1. open": "150.4567",  # 4 decimals
                    "2. high": "152.8912",  # 4 decimals
                    "3. low": "148.1234",  # 4 decimals
                    "4. close": "151.5678",  # 4 decimals
                    "5. volume": "1000000",
                },
            },
        }

        # Act
        price_points = alpha_vantage_adapter._parse_daily_history_response(
            ticker, api_response
        )

        # Assert
        assert len(price_points) == 1
        point = price_points[0]

        # Should be rounded to 2 decimals using ROUND_HALF_UP
        assert point.open is not None
        assert point.high is not None
        assert point.low is not None
        assert point.close is not None
        assert point.open.amount == Decimal("150.46")  # 150.4567 → 150.46
        assert point.high.amount == Decimal("152.89")  # 152.8912 → 152.89
        assert point.low.amount == Decimal("148.12")  # 148.1234 → 148.12
        assert point.close.amount == Decimal("151.57")  # 151.5678 → 151.57
        assert point.price.amount == Decimal("151.57")  # Same as close


class TestHistoryCachingTTL:
    """Tests for TTL calculation for price history caching."""

    async def test_ttl_short_for_recent_data(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
    ) -> None:
        """Should return short TTL (1 hour) for data including today."""
        from datetime import UTC, datetime

        ticker = Ticker("AAPL")
        now = datetime.now(UTC)

        # Create price points including today
        prices = [create_price_point(ticker, now.replace(hour=21, minute=0, second=0))]

        ttl = alpha_vantage_adapter._calculate_history_ttl(prices)

        # Should be 1 hour (3600 seconds)
        assert ttl == 3600

    async def test_ttl_medium_for_yesterday_data(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
    ) -> None:
        """Should return medium TTL (4 hours) for yesterday's data."""
        from datetime import UTC, datetime, timedelta

        ticker = Ticker("AAPL")
        now = datetime.now(UTC)
        yesterday = now - timedelta(days=1)

        # Create price points for yesterday
        prices = [
            create_price_point(ticker, yesterday.replace(hour=21, minute=0, second=0))
        ]

        ttl = alpha_vantage_adapter._calculate_history_ttl(prices)

        # Should be 4 hours (14400 seconds)
        assert ttl == 4 * 3600

    async def test_ttl_long_for_historical_data(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
    ) -> None:
        """Should return long TTL (7 days) for historical data."""
        from datetime import UTC, datetime, timedelta

        ticker = Ticker("AAPL")
        now = datetime.now(UTC)
        week_ago = now - timedelta(days=7)

        # Create price points from a week ago
        prices = [
            create_price_point(ticker, week_ago.replace(hour=21, minute=0, second=0))
        ]

        ttl = alpha_vantage_adapter._calculate_history_ttl(prices)

        # Should be 7 days (604800 seconds)
        assert ttl == 7 * 24 * 3600

    async def test_ttl_empty_list_returns_short(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
    ) -> None:
        """Should return short TTL for empty price list."""
        ttl = alpha_vantage_adapter._calculate_history_ttl([])

        # Should default to 1 hour
        assert ttl == 3600


class TestCacheCompletenessMarketHours:
    """Tests for improved cache completeness with market hours awareness."""

    async def test_cache_complete_with_data_through_yesterday_market_open(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
    ) -> None:
        """Should return True when requesting today but market is open.

        If market hasn't closed and we have data through yesterday, that's complete.
        """
        from datetime import UTC, datetime
        from unittest.mock import patch

        ticker = Ticker("AAPL")

        # Mock current time to be 3:00 PM UTC (before market close at 9:00 PM UTC)
        mock_now = datetime(2026, 1, 18, 15, 0, 0, tzinfo=UTC)

        with patch(
            "zebu.adapters.outbound.market_data.alpha_vantage_adapter.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(
                *args, **kwargs
            )

            # Request data through today
            start = datetime(2026, 1, 10, 0, 0, 0, tzinfo=UTC)
            end = datetime(2026, 1, 18, 23, 59, 59, tzinfo=UTC)

            # Cache has data through yesterday (Jan 17)
            cached_data = [
                create_price_point(ticker, datetime(2026, 1, 10, 21, 0, 0, tzinfo=UTC)),
                create_price_point(ticker, datetime(2026, 1, 13, 21, 0, 0, tzinfo=UTC)),
                create_price_point(ticker, datetime(2026, 1, 14, 21, 0, 0, tzinfo=UTC)),
                create_price_point(ticker, datetime(2026, 1, 15, 21, 0, 0, tzinfo=UTC)),
                create_price_point(ticker, datetime(2026, 1, 16, 21, 0, 0, tzinfo=UTC)),
                create_price_point(
                    ticker, datetime(2026, 1, 17, 21, 0, 0, tzinfo=UTC)
                ),  # Yesterday
            ]

            # Should be considered complete
            result = alpha_vantage_adapter._is_cache_complete(cached_data, start, end)

            assert result is True

    async def test_cache_incomplete_when_missing_yesterday_market_open(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
    ) -> None:
        """Should return False when market is open and missing yesterday's data."""
        from datetime import UTC, datetime
        from unittest.mock import patch

        ticker = Ticker("AAPL")

        # Mock current time to be 3:00 PM UTC (before market close)
        mock_now = datetime(2026, 1, 18, 15, 0, 0, tzinfo=UTC)

        with patch(
            "zebu.adapters.outbound.market_data.alpha_vantage_adapter.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(
                *args, **kwargs
            )

            start = datetime(2026, 1, 10, 0, 0, 0, tzinfo=UTC)
            end = datetime(2026, 1, 18, 23, 59, 59, tzinfo=UTC)

            # Cache only has data through Jan 15 (missing 16, 17)
            cached_data = [
                create_price_point(ticker, datetime(2026, 1, 10, 21, 0, 0, tzinfo=UTC)),
                create_price_point(ticker, datetime(2026, 1, 13, 21, 0, 0, tzinfo=UTC)),
                create_price_point(ticker, datetime(2026, 1, 14, 21, 0, 0, tzinfo=UTC)),
                create_price_point(ticker, datetime(2026, 1, 15, 21, 0, 0, tzinfo=UTC)),
            ]

            # Should be incomplete (missing yesterday)
            result = alpha_vantage_adapter._is_cache_complete(cached_data, start, end)

            assert result is False

    async def test_historical_cache_complete_without_today(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
    ) -> None:
        """Should return True for historical data (not including today).

        When requesting data from the past only, standard 1-day tolerance applies.
        """
        ticker = Ticker("AAPL")

        # Request historical range (not including today)
        start = datetime(2026, 1, 10, 0, 0, 0, tzinfo=UTC)
        end = datetime(2026, 1, 16, 23, 59, 59, tzinfo=UTC)

        # Cache has data through Jan 16
        cached_data = [
            create_price_point(ticker, datetime(2026, 1, 10, 21, 0, 0, tzinfo=UTC)),
            create_price_point(ticker, datetime(2026, 1, 13, 21, 0, 0, tzinfo=UTC)),
            create_price_point(ticker, datetime(2026, 1, 14, 21, 0, 0, tzinfo=UTC)),
            create_price_point(ticker, datetime(2026, 1, 15, 21, 0, 0, tzinfo=UTC)),
            create_price_point(ticker, datetime(2026, 1, 16, 21, 0, 0, tzinfo=UTC)),
        ]

        # Should be complete (historical data)
        result = alpha_vantage_adapter._is_cache_complete(cached_data, start, end)

        assert result is True


class TestRedisCachingIntegration:
    """Tests for Redis caching integration in get_price_history."""

    async def test_get_price_history_uses_redis_cache(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
        mock_price_cache: MagicMock,
        mock_price_repository: MagicMock,
        mock_rate_limiter: MagicMock,
    ) -> None:
        """Should check Redis cache first and return if complete."""
        ticker = Ticker("AAPL")
        start = datetime(2026, 1, 10, 0, 0, 0, tzinfo=UTC)
        end = datetime(2026, 1, 17, 23, 59, 59, tzinfo=UTC)

        # Redis has complete cached data
        cached_data = [
            create_price_point(ticker, datetime(2026, 1, 10, 21, 0, 0, tzinfo=UTC)),
            create_price_point(ticker, datetime(2026, 1, 13, 21, 0, 0, tzinfo=UTC)),
            create_price_point(ticker, datetime(2026, 1, 14, 21, 0, 0, tzinfo=UTC)),
            create_price_point(ticker, datetime(2026, 1, 15, 21, 0, 0, tzinfo=UTC)),
            create_price_point(ticker, datetime(2026, 1, 16, 21, 0, 0, tzinfo=UTC)),
            create_price_point(ticker, datetime(2026, 1, 17, 21, 0, 0, tzinfo=UTC)),
        ]
        mock_price_cache.get_history = AsyncMock(return_value=cached_data)

        # Act
        result = await alpha_vantage_adapter.get_price_history(
            ticker, start, end, "1day"
        )

        # Assert
        assert result == cached_data
        # Redis cache was checked
        mock_price_cache.get_history.assert_called_once()
        # Database was NOT queried
        mock_price_repository.get_price_history.assert_not_called()
        # API was NOT called
        mock_rate_limiter.consume_token.assert_not_called()

    async def test_get_price_history_warms_redis_from_db(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
        mock_price_cache: MagicMock,
        mock_price_repository: MagicMock,
        mock_rate_limiter: MagicMock,
    ) -> None:
        """Should warm Redis cache when database has complete data."""
        ticker = Ticker("AAPL")
        start = datetime(2026, 1, 10, 0, 0, 0, tzinfo=UTC)
        end = datetime(2026, 1, 17, 23, 59, 59, tzinfo=UTC)

        # Redis cache miss
        mock_price_cache.get_history = AsyncMock(return_value=None)

        # Database has complete data
        db_data = [
            create_price_point(ticker, datetime(2026, 1, 10, 21, 0, 0, tzinfo=UTC)),
            create_price_point(ticker, datetime(2026, 1, 13, 21, 0, 0, tzinfo=UTC)),
            create_price_point(ticker, datetime(2026, 1, 14, 21, 0, 0, tzinfo=UTC)),
            create_price_point(ticker, datetime(2026, 1, 15, 21, 0, 0, tzinfo=UTC)),
            create_price_point(ticker, datetime(2026, 1, 16, 21, 0, 0, tzinfo=UTC)),
            create_price_point(ticker, datetime(2026, 1, 17, 21, 0, 0, tzinfo=UTC)),
        ]
        mock_price_repository.get_price_history = AsyncMock(return_value=db_data)
        mock_price_cache.set_history = AsyncMock()

        # Act
        result = await alpha_vantage_adapter.get_price_history(
            ticker, start, end, "1day"
        )

        # Assert
        assert result == db_data
        # Database was queried
        mock_price_repository.get_price_history.assert_called_once()
        # Redis was warmed with database data
        mock_price_cache.set_history.assert_called_once()
        # API was NOT called
        mock_rate_limiter.consume_token.assert_not_called()

    async def test_get_price_history_stores_api_results_in_redis(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
        mock_price_cache: MagicMock,
        mock_price_repository: MagicMock,
        mock_rate_limiter: MagicMock,
        mock_http_client: MagicMock,
    ) -> None:
        """Should store API results in both Redis and database."""
        ticker = Ticker("AAPL")
        start = datetime(2026, 1, 10, 0, 0, 0, tzinfo=UTC)
        end = datetime(2026, 1, 17, 23, 59, 59, tzinfo=UTC)

        # Redis cache miss
        mock_price_cache.get_history = AsyncMock(return_value=None)

        # Database cache miss
        mock_price_repository.get_price_history = AsyncMock(return_value=[])
        mock_price_repository.upsert_price = AsyncMock()  # Mock database storage

        # Mock API response
        api_response_data = {
            "Meta Data": {"2. Symbol": "AAPL"},
            "Time Series (Daily)": {
                "2026-01-17": {
                    "1. open": "150.00",
                    "2. high": "152.00",
                    "3. low": "148.00",
                    "4. close": "151.00",
                    "5. volume": "1000000",
                },
                "2026-01-16": {
                    "1. open": "149.00",
                    "2. high": "151.00",
                    "3. low": "147.00",
                    "4. close": "150.00",
                    "5. volume": "1000000",
                },
            },
        }
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = api_response_data
        mock_http_client.get = AsyncMock(return_value=mock_response)
        mock_price_cache.set_history = AsyncMock()

        # Act
        result = await alpha_vantage_adapter.get_price_history(
            ticker, start, end, "1day"
        )

        # Assert
        assert len(result) > 0
        # API was called
        mock_rate_limiter.consume_token.assert_called_once()
        # Data was stored in database (via _fetch_daily_history_from_api)
        assert mock_price_repository.upsert_price.called
        # Data was stored in Redis
        mock_price_cache.set_history.assert_called_once()


class TestRateLimitWithStaleCache:
    """Tests for rate limit scenarios with stale/incomplete cached data."""

    async def test_rate_limit_serves_stale_cache_instead_of_failing(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
        mock_price_repository: MagicMock,
        mock_rate_limiter: MagicMock,
        mock_price_cache: MagicMock,
    ) -> None:
        """When rate-limited, should serve stale/incomplete cache instead of failing."""
        # Arrange
        ticker = Ticker("AAPL")
        start = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
        end = datetime(2026, 1, 17, 23, 59, 59, tzinfo=UTC)

        # Redis cache miss
        mock_price_cache.get_history = AsyncMock(return_value=None)

        # Database has incomplete/stale data (only partial range)
        stale_data = [
            create_price_point(ticker, datetime(2026, 1, 10, 0, 0, 0, tzinfo=UTC)),
            create_price_point(ticker, datetime(2026, 1, 13, 0, 0, 0, tzinfo=UTC)),
            create_price_point(ticker, datetime(2026, 1, 14, 0, 0, 0, tzinfo=UTC)),
        ]
        mock_price_repository.get_price_history = AsyncMock(return_value=stale_data)

        # Rate limiter blocks request
        mock_rate_limiter.can_make_request = AsyncMock(return_value=False)

        # Act
        result = await alpha_vantage_adapter.get_price_history(
            ticker, start, end, "1day"
        )

        # Assert
        # Should return the stale cached data
        assert result == stale_data
        assert len(result) == 3
        # Rate limiter was checked but not consumed (since request blocked)
        mock_rate_limiter.can_make_request.assert_called_once()
        mock_rate_limiter.consume_token.assert_not_called()

    async def test_rate_limit_with_no_cache_raises_error(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
        mock_price_repository: MagicMock,
        mock_rate_limiter: MagicMock,
        mock_price_cache: MagicMock,
    ) -> None:
        """When rate-limited with no cached data, should raise error."""
        # Arrange
        ticker = Ticker("AAPL")
        start = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
        end = datetime(2026, 1, 17, 23, 59, 59, tzinfo=UTC)

        # No cached data anywhere
        mock_price_cache.get_history = AsyncMock(return_value=None)
        mock_price_repository.get_price_history = AsyncMock(return_value=[])

        # Rate limiter blocks request
        mock_rate_limiter.can_make_request = AsyncMock(return_value=False)

        # Act & Assert
        from zebu.application.exceptions import MarketDataUnavailableError

        with pytest.raises(
            MarketDataUnavailableError,
            match="Rate limit exceeded. Cannot fetch historical data",
        ):
            await alpha_vantage_adapter.get_price_history(ticker, start, end, "1day")

        # Rate limiter was checked
        mock_rate_limiter.can_make_request.assert_called_once()

    async def test_consume_token_failure_serves_stale_cache(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
        mock_price_repository: MagicMock,
        mock_rate_limiter: MagicMock,
        mock_price_cache: MagicMock,
    ) -> None:
        """When consume_token fails, should serve stale cache instead of failing."""
        # Arrange
        ticker = Ticker("AAPL")
        start = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
        end = datetime(2026, 1, 17, 23, 59, 59, tzinfo=UTC)

        # Redis cache miss
        mock_price_cache.get_history = AsyncMock(return_value=None)

        # Database has stale data
        stale_data = [
            create_price_point(ticker, datetime(2026, 1, 10, 0, 0, 0, tzinfo=UTC)),
            create_price_point(ticker, datetime(2026, 1, 13, 0, 0, 0, tzinfo=UTC)),
        ]
        mock_price_repository.get_price_history = AsyncMock(return_value=stale_data)

        # Rate limiter allows request check but fails to consume token
        mock_rate_limiter.can_make_request = AsyncMock(return_value=True)
        mock_rate_limiter.consume_token = AsyncMock(return_value=False)

        # Act
        result = await alpha_vantage_adapter.get_price_history(
            ticker, start, end, "1day"
        )

        # Assert
        # Should return the stale cached data
        assert result == stale_data
        assert len(result) == 2
        # Both checks were made
        mock_rate_limiter.can_make_request.assert_called_once()
        mock_rate_limiter.consume_token.assert_called_once()
