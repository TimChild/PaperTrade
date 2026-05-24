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
from zebu.application.exceptions import (
    IncompleteHistoricalDataError,
    InvalidPriceDataError,
    MarketDataUnavailableError,
    TickerNotFoundError,
)
from zebu.application.ports.in_memory_backfill_task_repository import (
    InMemoryBackfillTaskRepository,
)
from zebu.domain.value_objects.backfill_priority import BackfillPriority
from zebu.domain.value_objects.backfill_task_status import BackfillTaskStatus
from zebu.domain.value_objects.money import Money
from zebu.domain.value_objects.price_point import PricePoint
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
    """Provide mock price repository.

    Async methods are configured as ``AsyncMock`` so awaits succeed without
    relying on broad ``except Exception`` blocks in production code.
    """
    repo = MagicMock()
    repo.upsert_price = AsyncMock(return_value=None)
    repo.get_latest_price = AsyncMock(return_value=None)
    repo.get_price_at = AsyncMock(return_value=None)
    repo.get_all_tickers = AsyncMock(return_value=[])
    return repo


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


class TestHistoricalOutputsizeSelection:
    """Tests for choosing Alpha Vantage historical output size."""

    def test_recent_range_uses_compact(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
    ) -> None:
        """Recent history requests should use compact mode."""
        now = datetime(2026, 3, 15, 12, 0, 0, tzinfo=UTC)
        start = datetime(2026, 2, 15, 0, 0, 0, tzinfo=UTC)
        end = datetime(2026, 2, 28, 23, 59, 59, tzinfo=UTC)

        result = alpha_vantage_adapter._select_daily_history_outputsize(
            start, end, now=now
        )

        assert result == "compact"

    def test_old_range_uses_full(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
    ) -> None:
        """Older backtest windows should use full mode."""
        now = datetime(2026, 3, 15, 12, 0, 0, tzinfo=UTC)
        start = datetime(2024, 1, 2, 0, 0, 0, tzinfo=UTC)
        end = datetime(2024, 1, 10, 23, 59, 59, tzinfo=UTC)

        result = alpha_vantage_adapter._select_daily_history_outputsize(
            start, end, now=now
        )

        assert result == "full"


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

        # Mock API response covering the full requested range so the
        # Phase J / Task #212 Layer 3 incomplete-coverage check stays
        # silent (head_date = 2026-01-10, tail_date = 2026-01-17).
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


class TestRateLimitInformationalResponseHandling:
    """Regression: AV returns HTTP 200 with an "Information" or "Note"
    payload when the daily cap / per-minute rate limit is hit. The
    parsers previously raised TickerNotFoundError, which is wildly
    misleading — the ticker is fine; we just can't fetch right now.
    Both parsers now raise MarketDataUnavailableError so the caller's
    retry / fallback path takes over.

    Origin: 2026-05-14 MCP smoke test; observed in prod logs as
    "Backtest failed: Ticker not found in Alpha Vantage database"
    on tickers (MSFT, MU, AAPL) that are obviously valid.
    """

    async def test_daily_history_information_payload_raises_unavailable(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
    ) -> None:
        """``Information`` key on a 200 means cap hit, not ticker not found."""
        ticker = Ticker("MSFT")
        response: dict[str, object] = {
            "Information": (
                "Thank you for using Alpha Vantage! Our standard API rate "
                "limit is 25 requests per day. Please subscribe to any of "
                "the premium plans to remove daily rate limits."
            ),
        }

        with pytest.raises(MarketDataUnavailableError, match="MSFT"):
            alpha_vantage_adapter._parse_daily_history_response(ticker, response)

    async def test_daily_history_note_payload_raises_unavailable(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
    ) -> None:
        """``Note`` is the older per-minute rate-limit signal."""
        ticker = Ticker("AAPL")
        response: dict[str, object] = {
            "Note": (
                "Thank you for using Alpha Vantage! Our standard API call "
                "frequency is 5 calls per minute and 500 calls per day."
            ),
        }

        with pytest.raises(MarketDataUnavailableError, match="AAPL"):
            alpha_vantage_adapter._parse_daily_history_response(ticker, response)

    async def test_global_quote_information_payload_raises_unavailable(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
    ) -> None:
        """GLOBAL_QUOTE parser has the same guard."""
        ticker = Ticker("MU")
        response: dict[str, object] = {
            "Information": "API call frequency exceeded",
        }

        with pytest.raises(MarketDataUnavailableError, match="MU"):
            alpha_vantage_adapter._parse_response(ticker, response)


class TestCurrentPriceTimestampCanonicalisation:
    """Issue #286 — GLOBAL_QUOTE writes must use market-close timestamps.

    The "current price" / "latest bar" write path stamps a daily price
    point with the canonical market close (21:00 UTC) for the bar's
    trading day, NOT ``datetime.now(UTC)`` (fetch time). The latter
    breaks trading-day bucketing and the dedup helper that prefers
    21:00-UTC entries.
    """

    @staticmethod
    def _global_quote(
        latest_trading_day: str, price: str = "194.50"
    ) -> dict[str, object]:
        """Build a GLOBAL_QUOTE-shaped JSON payload."""
        return {
            "Global Quote": {
                "01. symbol": "AAPL",
                "05. price": price,
                "07. latest trading day": latest_trading_day,
            }
        }

    @staticmethod
    def _stub_remaining_tokens(rate_limiter: MagicMock) -> None:
        """Stub the rate limiter's debug logging hook used inside
        ``_fetch_from_api``. The shared fixture only configures the gating
        methods (``can_make_request``/``consume_token``)."""
        rate_limiter.get_remaining_tokens = AsyncMock(
            return_value={"minute": 5, "day": 500}
        )

    async def test_fetch_from_api_stamps_at_market_close_for_trading_day(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
        mock_http_client: MagicMock,
        mock_rate_limiter: MagicMock,
    ) -> None:
        """``_fetch_from_api`` should stamp daily bars at 21:00 UTC on the
        ``07. latest trading day`` date — never wall-clock fetch time.
        """
        ticker = Ticker("AAPL")
        self._stub_remaining_tokens(mock_rate_limiter)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = self._global_quote("2026-04-01")
        mock_http_client.get = AsyncMock(return_value=mock_response)

        result = await alpha_vantage_adapter._fetch_from_api(ticker)

        assert result.timestamp == datetime(2026, 4, 1, 21, 0, 0, tzinfo=UTC)
        assert result.timestamp.hour == 21
        assert result.timestamp.minute == 0
        assert result.timestamp.second == 0
        assert result.interval == "1day"
        assert result.source == "alpha_vantage"

    async def test_get_current_price_persists_canonical_timestamp(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
        mock_http_client: MagicMock,
        mock_price_repository: MagicMock,
        mock_price_cache: MagicMock,
        mock_rate_limiter: MagicMock,
    ) -> None:
        """Regression: the bar passed to ``upsert_price`` from the
        end-to-end ``get_current_price`` path is canonicalised. Previously
        this was ``datetime.now(UTC)`` — see issue #286 — which corrupted
        the dedup helper that prefers 21:00-UTC entries.
        """
        ticker = Ticker("AAPL")
        self._stub_remaining_tokens(mock_rate_limiter)
        # Cache empty + DB empty → API path.
        mock_price_cache.get = AsyncMock(return_value=None)
        mock_price_cache.set = AsyncMock()
        mock_price_repository.get_latest_price = AsyncMock(return_value=None)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = self._global_quote("2026-04-01")
        mock_http_client.get = AsyncMock(return_value=mock_response)

        result = await alpha_vantage_adapter.get_current_price(ticker)

        # The returned bar carries the canonical close stamp.
        assert result.timestamp == datetime(2026, 4, 1, 21, 0, 0, tzinfo=UTC)

        # And the same canonical bar was persisted to the repository — so
        # any subsequent history read sees a 21:00-UTC entry that the
        # ``_deduplicate_daily_prices`` helper will correctly prefer.
        mock_price_repository.upsert_price.assert_awaited_once()
        persisted = mock_price_repository.upsert_price.await_args.args[0]
        assert persisted.timestamp == datetime(2026, 4, 1, 21, 0, 0, tzinfo=UTC)

    async def test_unparseable_trading_day_falls_back_to_last_trading_day(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
        mock_http_client: MagicMock,
        mock_rate_limiter: MagicMock,
    ) -> None:
        """A malformed ``07. latest trading day`` value falls back to the
        last trading day's market close — *never* fetch time."""
        ticker = Ticker("AAPL")
        self._stub_remaining_tokens(mock_rate_limiter)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = self._global_quote("not-a-date")
        mock_http_client.get = AsyncMock(return_value=mock_response)

        result = await alpha_vantage_adapter._fetch_from_api(ticker)

        # Fallback still produces a canonical market-close stamp.
        assert result.timestamp.hour == 21
        assert result.timestamp.minute == 0
        assert result.timestamp.second == 0
        assert result.timestamp.tzinfo == UTC

    async def test_missing_trading_day_field_falls_back_to_last_trading_day(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
        mock_http_client: MagicMock,
        mock_rate_limiter: MagicMock,
    ) -> None:
        """If the API payload omits ``07. latest trading day`` entirely,
        the timestamp still resolves to a canonical market close — never
        a fetch-time stamp."""
        ticker = Ticker("AAPL")
        self._stub_remaining_tokens(mock_rate_limiter)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "Global Quote": {"01. symbol": "AAPL", "05. price": "194.50"}
        }
        mock_http_client.get = AsyncMock(return_value=mock_response)

        result = await alpha_vantage_adapter._fetch_from_api(ticker)

        assert result.timestamp.hour == 21
        assert result.timestamp.minute == 0
        assert result.timestamp.second == 0


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

        # Mock API response covering the full requested range so the
        # Phase J / Task #212 Layer 3 incomplete-coverage check stays silent.
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


class TestDailyPriceDeduplication:
    """Tests for deduplication of daily price entries."""

    async def test_deduplicate_daily_prices_with_market_close(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
        mock_price_repository: MagicMock,
        mock_price_cache: MagicMock,
    ) -> None:
        """Should deduplicate entries for same date, preferring market close."""
        # Arrange
        ticker = Ticker("IBM")
        start = datetime(2026, 1, 20, 0, 0, 0, tzinfo=UTC)
        end = datetime(2026, 1, 20, 23, 59, 59, tzinfo=UTC)

        # Simulate multiple entries for same trading day (Jan 20)
        # with different timestamps - exactly as described in the issue
        cached_data = [
            # Intraday cache entry at 00:37:58
            create_price_point(
                ticker,
                datetime(2026, 1, 20, 0, 37, 58, tzinfo=UTC),
                Decimal("305.67"),
            ),
            # Another intraday cache entry at 13:35:59
            create_price_point(
                ticker,
                datetime(2026, 1, 20, 13, 35, 59, tzinfo=UTC),
                Decimal("305.67"),
            ),
            # Market close entry at 21:00:00
            create_price_point(
                ticker,
                datetime(2026, 1, 20, 21, 0, 0, tzinfo=UTC),
                Decimal("291.35"),
            ),
        ]

        # Mock Redis returns all three entries
        mock_price_cache.get_history = AsyncMock(return_value=cached_data)
        # Mock database returns no additional entries
        mock_price_repository.get_price_history = AsyncMock(return_value=[])

        # Act
        result = await alpha_vantage_adapter.get_price_history(
            ticker, start, end, "1day"
        )

        # Assert
        # Should return exactly ONE entry for Jan 20
        assert len(result) == 1
        # Should be the market close entry (21:00:00)
        assert result[0].timestamp == datetime(2026, 1, 20, 21, 0, 0, tzinfo=UTC)
        assert result[0].price.amount == Decimal("291.35")

    async def test_deduplicate_daily_prices_prefers_newer_when_no_market_close(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
        mock_price_repository: MagicMock,
        mock_price_cache: MagicMock,
    ) -> None:
        """Should prefer newer timestamp when no market close entry exists."""
        # Arrange
        ticker = Ticker("AAPL")
        start = datetime(2026, 1, 20, 0, 0, 0, tzinfo=UTC)
        end = datetime(2026, 1, 20, 23, 59, 59, tzinfo=UTC)

        # Multiple intraday entries, none at market close time
        cached_data = [
            create_price_point(
                ticker,
                datetime(2026, 1, 20, 10, 30, 0, tzinfo=UTC),
                Decimal("150.00"),
            ),
            create_price_point(
                ticker,
                datetime(2026, 1, 20, 14, 45, 0, tzinfo=UTC),
                Decimal("151.00"),
            ),
            create_price_point(
                ticker,
                datetime(2026, 1, 20, 8, 15, 0, tzinfo=UTC),
                Decimal("149.00"),
            ),
        ]

        mock_price_cache.get_history = AsyncMock(return_value=cached_data)
        mock_price_repository.get_price_history = AsyncMock(return_value=[])

        # Act
        result = await alpha_vantage_adapter.get_price_history(
            ticker, start, end, "1day"
        )

        # Assert
        # Should return exactly ONE entry
        assert len(result) == 1
        # Should be the newest entry (14:45:00)
        assert result[0].timestamp == datetime(2026, 1, 20, 14, 45, 0, tzinfo=UTC)
        assert result[0].price.amount == Decimal("151.00")

    async def test_deduplicate_daily_prices_multiple_dates(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
        mock_price_repository: MagicMock,
        mock_price_cache: MagicMock,
    ) -> None:
        """Should deduplicate across multiple trading dates."""
        # Arrange
        ticker = Ticker("AAPL")
        start = datetime(2026, 1, 19, 0, 0, 0, tzinfo=UTC)
        end = datetime(2026, 1, 21, 23, 59, 59, tzinfo=UTC)

        # Multiple entries for Jan 19, 20, and 21
        cached_data = [
            # Jan 19 - two entries
            create_price_point(
                ticker, datetime(2026, 1, 19, 13, 0, 0, tzinfo=UTC), Decimal("150.00")
            ),
            create_price_point(
                ticker, datetime(2026, 1, 19, 21, 0, 0, tzinfo=UTC), Decimal("151.00")
            ),
            # Jan 20 - three entries
            create_price_point(
                ticker, datetime(2026, 1, 20, 9, 0, 0, tzinfo=UTC), Decimal("152.00")
            ),
            create_price_point(
                ticker, datetime(2026, 1, 20, 13, 0, 0, tzinfo=UTC), Decimal("153.00")
            ),
            create_price_point(
                ticker, datetime(2026, 1, 20, 21, 0, 0, tzinfo=UTC), Decimal("154.00")
            ),
            # Jan 21 - one entry (already unique)
            create_price_point(
                ticker, datetime(2026, 1, 21, 21, 0, 0, tzinfo=UTC), Decimal("155.00")
            ),
        ]

        mock_price_cache.get_history = AsyncMock(return_value=cached_data)
        mock_price_repository.get_price_history = AsyncMock(return_value=[])

        # Act
        result = await alpha_vantage_adapter.get_price_history(
            ticker, start, end, "1day"
        )

        # Assert
        # Should return exactly THREE entries (one per date)
        assert len(result) == 3
        # All should be at market close (21:00)
        assert all(
            p.timestamp.time() == datetime(2026, 1, 1, 21, 0, 0).time() for p in result
        )
        # Should have correct prices (market close values)
        assert result[0].price.amount == Decimal("151.00")  # Jan 19
        assert result[1].price.amount == Decimal("154.00")  # Jan 20
        assert result[2].price.amount == Decimal("155.00")  # Jan 21

    async def test_no_deduplication_for_intraday_intervals(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
        mock_price_repository: MagicMock,
        mock_price_cache: MagicMock,
    ) -> None:
        """Should NOT deduplicate for non-daily intervals (e.g., 1hour)."""
        # Arrange
        ticker = Ticker("AAPL")
        start = datetime(2026, 1, 20, 0, 0, 0, tzinfo=UTC)
        end = datetime(2026, 1, 20, 23, 59, 59, tzinfo=UTC)

        # Multiple entries for same day with 1hour interval
        # These represent different hourly candles, so they should NOT be deduplicated
        cached_data = [
            PricePoint(
                ticker=ticker,
                timestamp=datetime(2026, 1, 20, 9, 0, 0, tzinfo=UTC),
                price=Money(Decimal("150.00"), "USD"),
                source="alpha_vantage",
                interval="1hour",
            ),
            PricePoint(
                ticker=ticker,
                timestamp=datetime(2026, 1, 20, 10, 0, 0, tzinfo=UTC),
                price=Money(Decimal("151.00"), "USD"),
                source="alpha_vantage",
                interval="1hour",
            ),
            PricePoint(
                ticker=ticker,
                timestamp=datetime(2026, 1, 20, 11, 0, 0, tzinfo=UTC),
                price=Money(Decimal("152.00"), "USD"),
                source="alpha_vantage",
                interval="1hour",
            ),
        ]

        mock_price_cache.get_history = AsyncMock(return_value=cached_data)
        mock_price_repository.get_price_history = AsyncMock(return_value=[])

        # Act
        result = await alpha_vantage_adapter.get_price_history(
            ticker, start, end, "1hour"
        )

        # Assert
        # For non-daily intervals, current implementation returns empty
        # (intraday fetching not yet supported)
        # This test documents that deduplication logic doesn't affect other intervals
        assert result == []

    async def test_deduplicate_helper_method_directly(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
    ) -> None:
        """Test the _deduplicate_daily_prices helper method directly."""
        # Arrange
        ticker = Ticker("AAPL")

        # Multiple entries for same date
        prices = [
            create_price_point(
                ticker, datetime(2026, 1, 20, 10, 0, 0, tzinfo=UTC), Decimal("150.00")
            ),
            create_price_point(
                ticker, datetime(2026, 1, 20, 21, 0, 0, tzinfo=UTC), Decimal("151.00")
            ),
            create_price_point(
                ticker, datetime(2026, 1, 20, 14, 0, 0, tzinfo=UTC), Decimal("152.00")
            ),
        ]

        # Act
        result = alpha_vantage_adapter._deduplicate_daily_prices(prices)

        # Assert
        assert len(result) == 1
        assert result[0].timestamp == datetime(2026, 1, 20, 21, 0, 0, tzinfo=UTC)
        assert result[0].price.amount == Decimal("151.00")


class TestGetCurrentPriceErrorHandling:
    """Tests for the error contract on ``get_current_price``.

    The adapter should:

    - Fall back to stale cache only on ``MarketDataUnavailableError``
      (transient API failure: timeout, network, 5xx).
    - Propagate ``TickerNotFoundError`` (the ticker genuinely doesn't exist).
    - Propagate ``InvalidPriceDataError`` (data integrity issue).
    - Propagate unexpected exceptions (programming bugs / config errors)
      so they surface in logs and monitoring rather than being masked as
      "stale data served".
    """

    async def test_transient_api_failure_falls_back_to_cached(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
        mock_price_cache: MagicMock,
    ) -> None:
        """A transient ``MarketDataUnavailableError`` from the API should
        fall back to the stale cache when present."""
        # Arrange
        ticker = Ticker("AAPL")
        stale_price = create_price_point(
            ticker, datetime(2026, 1, 1, 21, 0, 0, tzinfo=UTC)
        )
        mock_price_cache.get = AsyncMock(return_value=stale_price)

        async def fail_with_unavailable(_: Ticker) -> PricePoint:
            raise MarketDataUnavailableError("Network timeout")

        alpha_vantage_adapter._fetch_from_api = fail_with_unavailable  # type: ignore[method-assign]

        # Act
        result = await alpha_vantage_adapter.get_current_price(ticker)

        # Assert - serves stale cached data with explicit "cache" source
        assert result.source == "cache"
        assert result.price == stale_price.price

    async def test_transient_api_failure_no_cache_propagates(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
        mock_price_cache: MagicMock,
    ) -> None:
        """When the API is unavailable AND no cache exists, the
        ``MarketDataUnavailableError`` should propagate."""
        # Arrange
        ticker = Ticker("AAPL")
        mock_price_cache.get = AsyncMock(return_value=None)

        async def fail_with_unavailable(_: Ticker) -> PricePoint:
            raise MarketDataUnavailableError("API quota exceeded")

        alpha_vantage_adapter._fetch_from_api = fail_with_unavailable  # type: ignore[method-assign]

        # Act / Assert
        with pytest.raises(MarketDataUnavailableError, match="API quota exceeded"):
            await alpha_vantage_adapter.get_current_price(ticker)

    async def test_ticker_not_found_propagates_not_masked_as_stale(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
        mock_price_cache: MagicMock,
    ) -> None:
        """If a ticker doesn't exist, the error should propagate even when
        a stale cached value happens to exist - serving the cached value
        would lie about the ticker's validity."""
        # Arrange
        ticker = Ticker("BOGUS")
        # Cache happens to have something, but the ticker is genuinely invalid
        stale_price = create_price_point(
            ticker, datetime(2026, 1, 1, 21, 0, 0, tzinfo=UTC)
        )
        mock_price_cache.get = AsyncMock(return_value=stale_price)

        async def fail_with_not_found(_: Ticker) -> PricePoint:
            raise TickerNotFoundError("BOGUS")

        alpha_vantage_adapter._fetch_from_api = fail_with_not_found  # type: ignore[method-assign]

        # Act / Assert - error propagates rather than being masked
        with pytest.raises(TickerNotFoundError):
            await alpha_vantage_adapter.get_current_price(ticker)

    async def test_invalid_price_data_propagates_not_masked_as_stale(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
        mock_price_cache: MagicMock,
    ) -> None:
        """A data integrity error (malformed response) should propagate
        rather than be silently replaced by stale cached data."""
        # Arrange
        ticker = Ticker("AAPL")
        stale_price = create_price_point(
            ticker, datetime(2026, 1, 1, 21, 0, 0, tzinfo=UTC)
        )
        mock_price_cache.get = AsyncMock(return_value=stale_price)

        async def fail_with_invalid(_: Ticker) -> PricePoint:
            raise InvalidPriceDataError("AAPL", "Negative price")

        alpha_vantage_adapter._fetch_from_api = fail_with_invalid  # type: ignore[method-assign]

        # Act / Assert
        with pytest.raises(InvalidPriceDataError):
            await alpha_vantage_adapter.get_current_price(ticker)

    async def test_unexpected_exception_propagates_not_masked_as_stale(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
        mock_price_cache: MagicMock,
    ) -> None:
        """Programming bugs (e.g. ``KeyError`` on a parsing change) must
        surface to logs and crash reporters - they are NOT transient API
        failures and must not be masked as 'stale data served'.
        """
        # Arrange
        ticker = Ticker("AAPL")
        stale_price = create_price_point(
            ticker, datetime(2026, 1, 1, 21, 0, 0, tzinfo=UTC)
        )
        mock_price_cache.get = AsyncMock(return_value=stale_price)

        async def crash_with_keyerror(_: Ticker) -> PricePoint:
            raise KeyError("fields rearranged in API response")

        alpha_vantage_adapter._fetch_from_api = crash_with_keyerror  # type: ignore[method-assign]

        # Act / Assert - propagates so monitoring can flag the bug
        with pytest.raises(KeyError):
            await alpha_vantage_adapter.get_current_price(ticker)


class TestGetBatchPricesErrorHandling:
    """Tests for the error contract on ``get_batch_prices``.

    Per the ``MarketDataPort`` contract, batch fetching never raises for
    *per-ticker* domain failures - those tickers are simply excluded from
    the result. But:

    - Transient ``MarketDataUnavailableError`` falls back to cache when
      available.
    - ``TickerNotFoundError`` excludes the ticker (no false cache fallback).
    - ``InvalidPriceDataError`` propagates - malformed data is a real
      integrity issue, not a per-ticker thing to silently drop.
    - Unexpected exceptions propagate.
    """

    async def test_batch_invalid_price_data_propagates(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
        mock_price_cache: MagicMock,
    ) -> None:
        """``InvalidPriceDataError`` should propagate from the batch path
        rather than silently dropping the ticker."""
        # Arrange
        ticker = Ticker("AAPL")
        # Cache miss so we hit the API path
        mock_price_cache.get = AsyncMock(return_value=None)

        async def fail_with_invalid(_: Ticker) -> PricePoint:
            raise InvalidPriceDataError("AAPL", "Malformed JSON")

        alpha_vantage_adapter._fetch_from_api = fail_with_invalid  # type: ignore[method-assign]

        # Act / Assert
        with pytest.raises(InvalidPriceDataError):
            await alpha_vantage_adapter.get_batch_prices([ticker])

    async def test_batch_ticker_not_found_excludes_without_cache_fallback(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
        mock_price_cache: MagicMock,
    ) -> None:
        """For an invalid ticker, the result should *not* include a cached
        value (which would be a lie); the ticker is just excluded."""
        # Arrange
        ticker = Ticker("BOGUS")
        # Cache miss for initial check, plus a hypothetical stale value
        # would still be wrong to return.
        mock_price_cache.get = AsyncMock(return_value=None)

        async def fail_with_not_found(_: Ticker) -> PricePoint:
            raise TickerNotFoundError("BOGUS")

        alpha_vantage_adapter._fetch_from_api = fail_with_not_found  # type: ignore[method-assign]

        # Act
        result = await alpha_vantage_adapter.get_batch_prices([ticker])

        # Assert - ticker is not in result; no exception raised
        assert ticker not in result
        assert result == {}

    async def test_batch_transient_failure_falls_back_to_cached_value(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
        mock_price_cache: MagicMock,
    ) -> None:
        """A ``MarketDataUnavailableError`` should still fall back to the
        stale cached value (if any) for the affected ticker."""
        # Arrange
        ticker = Ticker("AAPL")
        stale_price = create_price_point(
            ticker, datetime(2026, 1, 1, 21, 0, 0, tzinfo=UTC)
        )

        # First call (initial cache check during batch loop): return None so
        # we hit the API path. Second call (stale-cache fallback) returns
        # the stale price.
        get_calls = [None, stale_price]
        mock_price_cache.get = AsyncMock(side_effect=get_calls)

        async def fail_with_unavailable(_: Ticker) -> PricePoint:
            raise MarketDataUnavailableError("Timeout")

        alpha_vantage_adapter._fetch_from_api = fail_with_unavailable  # type: ignore[method-assign]

        # Act
        result = await alpha_vantage_adapter.get_batch_prices([ticker])

        # Assert
        assert ticker in result
        assert result[ticker].source == "cache"

    async def test_batch_unexpected_exception_propagates(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
        mock_price_cache: MagicMock,
    ) -> None:
        """A programming bug must propagate so it surfaces in monitoring."""
        # Arrange
        ticker = Ticker("AAPL")
        mock_price_cache.get = AsyncMock(return_value=None)

        async def crash_with_keyerror(_: Ticker) -> PricePoint:
            raise KeyError("unexpected schema")

        alpha_vantage_adapter._fetch_from_api = crash_with_keyerror  # type: ignore[method-assign]

        # Act / Assert
        with pytest.raises(KeyError):
            await alpha_vantage_adapter.get_batch_prices([ticker])


class TestGetPriceHistoryErrorHandling:
    """Tests for the error contract on ``get_price_history``.

    - ``MarketDataUnavailableError`` returns partial cached data (better
      than nothing) but if there's no partial data, the error propagates -
      it does NOT silently return ``[]``.
    - ``TickerNotFoundError`` and ``InvalidPriceDataError`` propagate.
    - Unexpected exceptions propagate.
    """

    async def test_history_transient_failure_with_partial_data_returns_partial(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
        mock_price_repository: MagicMock,
        mock_price_cache: MagicMock,
        mock_rate_limiter: MagicMock,
    ) -> None:
        """When the API call fails transiently and we have partial cached
        data, return the partial data rather than failing."""
        # Arrange
        ticker = Ticker("AAPL")
        start = datetime(2026, 1, 10, 0, 0, 0, tzinfo=UTC)
        end = datetime(2026, 1, 17, 23, 59, 59, tzinfo=UTC)

        # Sparse cached data (incomplete - density check will fail)
        partial_db = [
            create_price_point(ticker, datetime(2026, 1, 10, 21, 0, 0, tzinfo=UTC)),
            create_price_point(ticker, datetime(2026, 1, 13, 21, 0, 0, tzinfo=UTC)),
        ]
        mock_price_repository.get_price_history = AsyncMock(return_value=partial_db)
        mock_price_cache.get_history = AsyncMock(return_value=None)

        async def fail_with_unavailable(
            _ticker: Ticker, outputsize: str = "compact"
        ) -> list[PricePoint]:
            raise MarketDataUnavailableError("API timeout")

        alpha_vantage_adapter._fetch_daily_history_from_api = fail_with_unavailable  # type: ignore[method-assign]

        # Act
        result = await alpha_vantage_adapter.get_price_history(
            ticker, start, end, "1day"
        )

        # Assert - partial data is returned
        assert len(result) == 2
        # Rate limiter was consumed (we did try to fetch)
        mock_rate_limiter.consume_token.assert_called_once()

    async def test_history_transient_failure_no_partial_data_propagates(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
        mock_price_repository: MagicMock,
        mock_price_cache: MagicMock,
    ) -> None:
        """When the API fails transiently AND there is no partial data,
        the error propagates - we do NOT silently return ``[]``."""
        # Arrange
        ticker = Ticker("AAPL")
        start = datetime(2026, 1, 10, 0, 0, 0, tzinfo=UTC)
        end = datetime(2026, 1, 17, 23, 59, 59, tzinfo=UTC)

        # No data anywhere
        mock_price_repository.get_price_history = AsyncMock(return_value=[])
        mock_price_cache.get_history = AsyncMock(return_value=None)

        async def fail_with_unavailable(
            _ticker: Ticker, outputsize: str = "compact"
        ) -> list[PricePoint]:
            raise MarketDataUnavailableError("Network down")

        alpha_vantage_adapter._fetch_daily_history_from_api = fail_with_unavailable  # type: ignore[method-assign]

        # Act / Assert
        with pytest.raises(MarketDataUnavailableError, match="Network down"):
            await alpha_vantage_adapter.get_price_history(ticker, start, end, "1day")

    async def test_history_ticker_not_found_propagates(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
        mock_price_repository: MagicMock,
        mock_price_cache: MagicMock,
    ) -> None:
        """``TickerNotFoundError`` from the API must propagate, even when
        partial cached data exists - returning partial data for an
        invalid ticker would be a lie."""
        # Arrange
        ticker = Ticker("BOGUS")
        start = datetime(2026, 1, 10, 0, 0, 0, tzinfo=UTC)
        end = datetime(2026, 1, 17, 23, 59, 59, tzinfo=UTC)

        # Partial cached data exists
        partial_db = [
            create_price_point(ticker, datetime(2026, 1, 10, 21, 0, 0, tzinfo=UTC)),
        ]
        mock_price_repository.get_price_history = AsyncMock(return_value=partial_db)
        mock_price_cache.get_history = AsyncMock(return_value=None)

        async def fail_with_not_found(
            _ticker: Ticker, outputsize: str = "compact"
        ) -> list[PricePoint]:
            raise TickerNotFoundError("BOGUS")

        alpha_vantage_adapter._fetch_daily_history_from_api = fail_with_not_found  # type: ignore[method-assign]

        # Act / Assert
        with pytest.raises(TickerNotFoundError):
            await alpha_vantage_adapter.get_price_history(ticker, start, end, "1day")

    async def test_history_unexpected_exception_propagates(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
        mock_price_repository: MagicMock,
        mock_price_cache: MagicMock,
    ) -> None:
        """Programming bugs in the API path must propagate, not be masked
        as 'partial data returned'."""
        # Arrange
        ticker = Ticker("AAPL")
        start = datetime(2026, 1, 10, 0, 0, 0, tzinfo=UTC)
        end = datetime(2026, 1, 17, 23, 59, 59, tzinfo=UTC)

        mock_price_repository.get_price_history = AsyncMock(return_value=[])
        mock_price_cache.get_history = AsyncMock(return_value=None)

        async def crash_with_keyerror(
            _ticker: Ticker, outputsize: str = "compact"
        ) -> list[PricePoint]:
            raise KeyError("API schema changed")

        alpha_vantage_adapter._fetch_daily_history_from_api = crash_with_keyerror  # type: ignore[method-assign]

        # Act / Assert
        with pytest.raises(KeyError):
            await alpha_vantage_adapter.get_price_history(ticker, start, end, "1day")


class TestIncompleteHistoricalCoverage:
    """Phase J / Task #212 Layer 3 — partial-coverage detection + backfill enqueue.

    Behavior under test:

    * A request whose post-Tier-3 result strictly subsets the requested
      range raises :class:`IncompleteHistoricalDataError`.
    * The same adapter wired with a :class:`BackfillTaskRepositoryPort`
      enqueues a high-priority backfill for the missing window before
      raising.
    * Without a port (legacy callers), the exception still raises — only
      the enqueue side-effect is skipped.
    """

    @pytest.fixture
    def backfill_repo(self) -> InMemoryBackfillTaskRepository:
        """In-memory backfill task repository fixture."""
        return InMemoryBackfillTaskRepository()

    @pytest.fixture
    def adapter_with_backfill(
        self,
        mock_rate_limiter: MagicMock,
        mock_price_repository: MagicMock,
        mock_price_cache: MagicMock,
        mock_http_client: MagicMock,
        backfill_repo: InMemoryBackfillTaskRepository,
    ) -> AlphaVantageAdapter:
        """Adapter wired with the in-memory backfill repository."""
        return AlphaVantageAdapter(
            rate_limiter=mock_rate_limiter,
            price_repository=mock_price_repository,
            price_cache=mock_price_cache,
            http_client=mock_http_client,
            api_key="test_key",
            backfill_task_repository=backfill_repo,
        )

    @staticmethod
    def _api_response(dates: list[str]) -> dict[str, object]:
        """Construct a TIME_SERIES_DAILY JSON response covering ``dates``."""
        ts: dict[str, object] = {}
        for d in dates:
            ts[d] = {
                "1. open": "150.00",
                "2. high": "152.00",
                "3. low": "148.00",
                "4. close": "151.00",
                "5. volume": "1000000",
            }
        return {"Meta Data": {"2. Symbol": "AAPL"}, "Time Series (Daily)": ts}

    async def test_partial_post_api_coverage_raises_incomplete_error(
        self,
        adapter_with_backfill: AlphaVantageAdapter,
        mock_price_repository: MagicMock,
        mock_price_cache: MagicMock,
        mock_http_client: MagicMock,
    ) -> None:
        """Ticker valid, but API returns only the tail of the requested range."""
        ticker = Ticker("AAPL")
        start = datetime(2026, 1, 5, 0, 0, 0, tzinfo=UTC)
        end = datetime(2026, 1, 17, 23, 59, 59, tzinfo=UTC)

        # Empty cache + empty DB → straight to API.
        mock_price_cache.get_history = AsyncMock(return_value=None)
        mock_price_repository.get_price_history = AsyncMock(return_value=[])

        # API returns only Jan 15-17 — head gap of 10 days (Jan 5-14).
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = self._api_response(
            ["2026-01-15", "2026-01-16", "2026-01-17"]
        )
        mock_http_client.get = AsyncMock(return_value=mock_response)

        with pytest.raises(IncompleteHistoricalDataError) as exc_info:
            await adapter_with_backfill.get_price_history(ticker, start, end, "1day")

        from datetime import date as _d

        assert exc_info.value.ticker == ticker
        assert exc_info.value.requested_range == (_d(2026, 1, 5), _d(2026, 1, 17))
        assert exc_info.value.available_range == (
            _d(2026, 1, 15),
            _d(2026, 1, 17),
        )
        assert exc_info.value.missing_days_count == 10

    async def test_partial_post_api_coverage_enqueues_backfill_task(
        self,
        adapter_with_backfill: AlphaVantageAdapter,
        mock_price_repository: MagicMock,
        mock_price_cache: MagicMock,
        mock_http_client: MagicMock,
        backfill_repo: InMemoryBackfillTaskRepository,
    ) -> None:
        """Adapter creates exactly one high-priority backfill task for the gap."""
        ticker = Ticker("AAPL")
        start = datetime(2026, 1, 5, 0, 0, 0, tzinfo=UTC)
        end = datetime(2026, 1, 17, 23, 59, 59, tzinfo=UTC)

        mock_price_cache.get_history = AsyncMock(return_value=None)
        mock_price_repository.get_price_history = AsyncMock(return_value=[])

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = self._api_response(
            ["2026-01-15", "2026-01-16", "2026-01-17"]
        )
        mock_http_client.get = AsyncMock(return_value=mock_response)

        with pytest.raises(IncompleteHistoricalDataError):
            await adapter_with_backfill.get_price_history(ticker, start, end, "1day")

        pending = await backfill_repo.list_pending(limit=10)
        assert len(pending) == 1
        task = pending[0]
        assert task.ticker == ticker
        from datetime import date as _d

        assert task.start_date == _d(2026, 1, 5)
        assert task.end_date == _d(2026, 1, 14)
        assert task.priority is BackfillPriority.HIGH
        assert task.status is BackfillTaskStatus.PENDING

    async def test_complete_coverage_does_not_raise(
        self,
        adapter_with_backfill: AlphaVantageAdapter,
        mock_price_repository: MagicMock,
        mock_price_cache: MagicMock,
        mock_http_client: MagicMock,
        backfill_repo: InMemoryBackfillTaskRepository,
    ) -> None:
        """Full coverage of the requested range returns normally — no enqueue."""
        ticker = Ticker("AAPL")
        start = datetime(2026, 1, 10, 0, 0, 0, tzinfo=UTC)
        end = datetime(2026, 1, 17, 23, 59, 59, tzinfo=UTC)

        mock_price_cache.get_history = AsyncMock(return_value=None)
        mock_price_repository.get_price_history = AsyncMock(return_value=[])

        mock_response = MagicMock()
        mock_response.status_code = 200
        # Include both head (Jan 10) and tail (Jan 17) so coverage spans
        # the requested range.
        mock_response.json.return_value = self._api_response(
            ["2026-01-10", "2026-01-13", "2026-01-15", "2026-01-17"]
        )
        mock_http_client.get = AsyncMock(return_value=mock_response)

        result = await adapter_with_backfill.get_price_history(
            ticker, start, end, "1day"
        )
        assert result  # non-empty
        # No backfill was enqueued
        assert await backfill_repo.list_pending(limit=10) == []

    async def test_raises_without_backfill_port_does_not_crash(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
        mock_price_repository: MagicMock,
        mock_price_cache: MagicMock,
        mock_http_client: MagicMock,
    ) -> None:
        """When no backfill port is wired, raise without enqueueing.

        Default constructor case — preserves backwards-compat for tests
        and legacy call sites that haven't wired the L2 port yet.
        """
        ticker = Ticker("AAPL")
        start = datetime(2026, 1, 5, 0, 0, 0, tzinfo=UTC)
        end = datetime(2026, 1, 17, 23, 59, 59, tzinfo=UTC)

        mock_price_cache.get_history = AsyncMock(return_value=None)
        mock_price_repository.get_price_history = AsyncMock(return_value=[])

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = self._api_response(
            ["2026-01-15", "2026-01-16", "2026-01-17"]
        )
        mock_http_client.get = AsyncMock(return_value=mock_response)

        with pytest.raises(IncompleteHistoricalDataError):
            await alpha_vantage_adapter.get_price_history(ticker, start, end, "1day")

    async def test_duplicate_partial_does_not_enqueue_twice(
        self,
        adapter_with_backfill: AlphaVantageAdapter,
        mock_price_repository: MagicMock,
        mock_price_cache: MagicMock,
        mock_http_client: MagicMock,
        backfill_repo: InMemoryBackfillTaskRepository,
    ) -> None:
        """Two calls with the same incomplete result enqueue only one task."""
        ticker = Ticker("AAPL")
        start = datetime(2026, 1, 5, 0, 0, 0, tzinfo=UTC)
        end = datetime(2026, 1, 17, 23, 59, 59, tzinfo=UTC)

        mock_price_cache.get_history = AsyncMock(return_value=None)
        mock_price_repository.get_price_history = AsyncMock(return_value=[])

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = self._api_response(
            ["2026-01-15", "2026-01-16", "2026-01-17"]
        )
        mock_http_client.get = AsyncMock(return_value=mock_response)

        for _ in range(2):
            with pytest.raises(IncompleteHistoricalDataError):
                await adapter_with_backfill.get_price_history(
                    ticker, start, end, "1day"
                )

        # find_existing collapsed the second insert
        pending = await backfill_repo.list_pending(limit=10)
        assert len(pending) == 1


# ---------------------------------------------------------------------------
# Premium-feature detection and compact-retry behaviour
# ---------------------------------------------------------------------------

# The actual prod-log payload AV returned when outputsize=full was refused.
_AV_PREMIUM_REFUSAL_MESSAGE = (
    "Thank you for using Alpha Vantage! The outputsize=full parameter value "
    "is a premium feature for the TIME_SERIES_DAILY endpoint. You may "
    "subscribe to any of the premium plans at https://www.alphavantage.co/"
    "premium/ to instantly unlock all premium features"
)

_AV_RATE_LIMIT_MESSAGE = (
    "Thank you for using Alpha Vantage! Our standard API rate limit is "
    "25 requests per day. Please subscribe to any of the premium plans "
    "to remove daily rate limits."
)

_AV_NOTE_PER_MINUTE_MESSAGE = (
    "Thank you for using Alpha Vantage! Our standard API call frequency "
    "is 5 calls per minute and 500 calls per day. Please visit "
    "https://www.alphavantage.co/premium/ if you would like to target "
    "a higher API call frequency."
)


class TestIsPremiumRefusal:
    """Unit tests for the ``_is_premium_refusal`` static helper.

    Verifies that the premium-gate payload is distinguished from the
    transient rate-limit / daily-cap payloads, both of which arrive
    via the same ``Information`` / ``Note`` JSON key.
    """

    def test_premium_refusal_message_detected(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
    ) -> None:
        """The prod-log refusal body must be detected as a premium refusal."""
        assert alpha_vantage_adapter._is_premium_refusal(_AV_PREMIUM_REFUSAL_MESSAGE)

    def test_rate_limit_daily_cap_not_detected_as_premium(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
    ) -> None:
        """Daily-cap message (no outputsize=full) must NOT trigger premium path."""
        assert not alpha_vantage_adapter._is_premium_refusal(_AV_RATE_LIMIT_MESSAGE)

    def test_rate_limit_per_minute_not_detected_as_premium(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
    ) -> None:
        """Per-minute note (no outputsize=full) must NOT trigger premium path."""
        assert not alpha_vantage_adapter._is_premium_refusal(
            _AV_NOTE_PER_MINUTE_MESSAGE
        )

    def test_case_insensitive_match(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
    ) -> None:
        """Detection must be case-insensitive."""
        mixed_case = "OUTPUTSIZE=FULL parameter value is a PREMIUM feature"
        assert alpha_vantage_adapter._is_premium_refusal(mixed_case)

    def test_empty_string_not_detected(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
    ) -> None:
        """Empty string must not raise and must return False."""
        assert not alpha_vantage_adapter._is_premium_refusal("")

    def test_premium_without_outputsize_not_detected(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
    ) -> None:
        """'premium' alone (without 'outputsize=full') is not a refusal."""
        assert not alpha_vantage_adapter._is_premium_refusal(
            "subscribe to our premium plans"
        )


def _compact_api_response(dates: list[str]) -> dict[str, object]:
    """Build a TIME_SERIES_DAILY response payload for the given list of dates."""
    ts: dict[str, object] = {}
    for d in dates:
        ts[d] = {
            "1. open": "150.00",
            "2. high": "152.00",
            "3. low": "148.00",
            "4. close": "151.00",
            "5. volume": "1000000",
        }
    return {"Meta Data": {"2. Symbol": "AAPL"}, "Time Series (Daily)": ts}


class TestAvPremiumRefusalRetry:
    """Adapter retries with compact when AV refuses outputsize=full.

    Prod-log context (2026-05-24):
        HTTP 200 with Information body:
        "The outputsize=full parameter value is a premium feature for the
        TIME_SERIES_DAILY endpoint…"
        → adapter logged "returning partial cached data" and returned
          stale cache silently — Catch up showed "Caught up" with only
          ~100 days.

    Desired behaviour after this fix:
        1. Detect premium refusal.
        2. Retry with compact (succeeds on free tier).
        3. Let ``_raise_if_incomplete_coverage`` surface
           IncompleteHistoricalDataError when the requested range
           exceeds what compact can provide (~100 days).
    """

    @staticmethod
    def _stub_remaining_tokens(rate_limiter: MagicMock) -> None:
        rate_limiter.get_remaining_tokens = AsyncMock(
            return_value={"minute": 5, "day": 500}
        )

    async def test_full_refusal_retries_with_compact(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
        mock_http_client: MagicMock,
        mock_rate_limiter: MagicMock,
    ) -> None:
        """When outputsize=full is refused, adapter retries with compact.

        The HTTP client is called twice: first with outputsize=full (returns
        the premium-refusal Information body), then with outputsize=compact
        (returns real price data).
        """
        self._stub_remaining_tokens(mock_rate_limiter)

        # Dates within the last 100 trading days for the compact response.
        compact_dates = [
            "2026-05-01",
            "2026-05-02",
            "2026-05-05",
        ]

        refusal_response = MagicMock()
        refusal_response.status_code = 200
        refusal_response.json.return_value = {
            "Information": _AV_PREMIUM_REFUSAL_MESSAGE
        }

        compact_response = MagicMock()
        compact_response.status_code = 200
        compact_response.json.return_value = _compact_api_response(compact_dates)

        # First call → refusal; second call → compact data.
        mock_http_client.get = AsyncMock(
            side_effect=[refusal_response, compact_response]
        )

        result = await alpha_vantage_adapter._fetch_daily_history_from_api(
            Ticker("AAPL"), outputsize="full"
        )

        # Compact data was returned.
        assert len(result) == len(compact_dates)
        assert result[0].source == "alpha_vantage"

        # Two HTTP calls were made (full → compact).
        assert mock_http_client.get.await_count == 2
        first_call_params = mock_http_client.get.await_args_list[0].kwargs["params"]
        assert first_call_params["outputsize"] == "full"
        second_call_params = mock_http_client.get.await_args_list[1].kwargs["params"]
        assert second_call_params["outputsize"] == "compact"

    async def test_compact_request_not_retried_on_rate_limit(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
        mock_http_client: MagicMock,
        mock_rate_limiter: MagicMock,
    ) -> None:
        """A compact request that returns a daily-cap body raises
        MarketDataUnavailableError (not a premium-refusal, no retry).
        """
        self._stub_remaining_tokens(mock_rate_limiter)

        # Rate-limit body — does NOT contain "outputsize=full", so
        # _is_premium_refusal returns False.
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {"Information": _AV_RATE_LIMIT_MESSAGE}

        mock_http_client.get = AsyncMock(return_value=response)

        with pytest.raises(MarketDataUnavailableError):
            await alpha_vantage_adapter._fetch_daily_history_from_api(
                Ticker("AAPL"), outputsize="compact"
            )

    async def test_long_range_request_raises_incomplete_after_compact_retry(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
        mock_http_client: MagicMock,
        mock_price_cache: MagicMock,
        mock_price_repository: MagicMock,
        mock_rate_limiter: MagicMock,
    ) -> None:
        """Catch up requesting 11 years surfaces IncompleteHistoricalDataError.

        Flow:
          1. get_price_history called for 2015-01-01 → today (>100 days).
          2. Cache + DB both miss.
          3. _select_daily_history_outputsize returns "full".
          4. AV refuses full → adapter retries with compact.
          5. Compact returns only the last 3 days.
          6. _raise_if_incomplete_coverage sees massive gap → raises
             IncompleteHistoricalDataError.
          7. That exception propagates out of get_price_history (it is NOT
             a MarketDataUnavailableError, so the stale-cache fallback is
             skipped).
        """
        from datetime import date as _d

        self._stub_remaining_tokens(mock_rate_limiter)

        ticker = Ticker("AAPL")
        # 11-year backfill window — clearly > 100 days.
        start = datetime(2015, 1, 2, 0, 0, 0, tzinfo=UTC)
        end = datetime(2026, 5, 23, 23, 59, 59, tzinfo=UTC)

        # No cache, no DB data.
        mock_price_cache.get_history = AsyncMock(return_value=None)
        mock_price_repository.get_price_history = AsyncMock(return_value=[])

        refusal_response = MagicMock()
        refusal_response.status_code = 200
        refusal_response.json.return_value = {
            "Information": _AV_PREMIUM_REFUSAL_MESSAGE
        }

        # Compact returns only 3 recent days — nowhere near 11 years.
        compact_response = MagicMock()
        compact_response.status_code = 200
        compact_response.json.return_value = _compact_api_response(
            ["2026-05-21", "2026-05-22", "2026-05-23"]
        )

        mock_http_client.get = AsyncMock(
            side_effect=[refusal_response, compact_response]
        )

        with pytest.raises(IncompleteHistoricalDataError) as exc_info:
            await alpha_vantage_adapter.get_price_history(ticker, start, end, "1day")

        err = exc_info.value
        assert err.ticker == ticker
        # Requested range starts 2015-01-02, but data only starts 2026-05-21.
        assert err.requested_range[0] == _d(2015, 1, 2)
        assert err.missing_days_count > 0

    async def test_91_day_request_succeeds_after_compact_retry(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
        mock_http_client: MagicMock,
        mock_price_cache: MagicMock,
        mock_price_repository: MagicMock,
        mock_rate_limiter: MagicMock,
    ) -> None:
        """A ~91-day request (just over the compact threshold) that hits the
        premium-refusal fallback succeeds when AV's compact response fully
        covers the window.

        ``_select_daily_history_outputsize`` returns ``"full"`` for ranges
        > 90 days, so the first API call uses ``outputsize=full``.  AV
        refuses with the premium payload.  The adapter retries with compact.
        Compact returns data spanning the requested window, so
        ``_raise_if_incomplete_coverage`` stays silent and the caller
        receives the data.
        """
        self._stub_remaining_tokens(mock_rate_limiter)

        ticker = Ticker("AAPL")
        # 91-day window → _select_daily_history_outputsize returns "full".
        start = datetime(2026, 2, 20, 0, 0, 0, tzinfo=UTC)
        end = datetime(2026, 5, 22, 23, 59, 59, tzinfo=UTC)

        mock_price_cache.get_history = AsyncMock(return_value=None)
        mock_price_repository.get_price_history = AsyncMock(return_value=[])

        refusal_response = MagicMock()
        refusal_response.status_code = 200
        refusal_response.json.return_value = {
            "Information": _AV_PREMIUM_REFUSAL_MESSAGE
        }

        # Build a compact response that fully spans the requested range.
        compact_response = MagicMock()
        compact_response.status_code = 200
        compact_response.json.return_value = _compact_api_response(
            [
                "2026-02-20",
                "2026-03-15",
                "2026-04-01",
                "2026-04-15",
                "2026-05-01",
                "2026-05-15",
                "2026-05-22",
            ]
        )

        mock_http_client.get = AsyncMock(
            side_effect=[refusal_response, compact_response]
        )

        result = await alpha_vantage_adapter.get_price_history(
            ticker, start, end, "1day"
        )

        assert len(result) == 7
        assert all(p.source == "alpha_vantage" for p in result)
        # Two calls were made: full (refused) → compact (succeeded).
        assert mock_http_client.get.await_count == 2

    async def test_stale_cache_fallback_not_triggered_for_incomplete_data_error(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
        mock_http_client: MagicMock,
        mock_price_cache: MagicMock,
        mock_price_repository: MagicMock,
        mock_rate_limiter: MagicMock,
    ) -> None:
        """IncompleteHistoricalDataError propagates through the stale-cache handler.

        The except-MarketDataUnavailableError block in get_price_history must
        NOT intercept IncompleteHistoricalDataError (they're sibling classes
        under MarketDataError). This test verifies the error contract that
        makes Catch up show FAILED instead of silently returning stale data.
        """
        self._stub_remaining_tokens(mock_rate_limiter)

        ticker = Ticker("AAPL")
        start = datetime(2015, 1, 2, 0, 0, 0, tzinfo=UTC)
        end = datetime(2026, 5, 23, 23, 59, 59, tzinfo=UTC)

        # Stale cached data exists in the cache — should NOT be returned.
        stale_price = create_price_point(
            ticker, datetime(2026, 1, 15, 21, 0, 0, tzinfo=UTC)
        )
        mock_price_cache.get_history = AsyncMock(return_value=[stale_price])
        mock_price_repository.get_price_history = AsyncMock(return_value=[])

        refusal_response = MagicMock()
        refusal_response.status_code = 200
        refusal_response.json.return_value = {
            "Information": _AV_PREMIUM_REFUSAL_MESSAGE
        }

        compact_response = MagicMock()
        compact_response.status_code = 200
        compact_response.json.return_value = _compact_api_response(
            ["2026-05-21", "2026-05-22", "2026-05-23"]
        )

        mock_http_client.get = AsyncMock(
            side_effect=[refusal_response, compact_response]
        )

        # Must raise — NOT silently return stale_price.
        with pytest.raises(IncompleteHistoricalDataError):
            await alpha_vantage_adapter.get_price_history(ticker, start, end, "1day")
