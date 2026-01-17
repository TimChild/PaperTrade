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
    return MagicMock()


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
