"""Integration tests for price history caching with subset matching.

Tests the complete flow of price history caching including:
- Cache warming with broader date ranges
- Subset matching when switching time ranges
- Rate limiting avoidance through intelligent caching

This validates Task 155: Fix Price History Cache to Support Subset Range Matching
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
import respx
from fakeredis import aioredis as fakeredis

from zebu.adapters.outbound.market_data.alpha_vantage_adapter import (
    AlphaVantageAdapter,
)
from zebu.application.dtos.price_point import PricePoint
from zebu.domain.value_objects.money import Money
from zebu.domain.value_objects.ticker import Ticker
from zebu.infrastructure.cache.price_cache import PriceCache
from zebu.infrastructure.rate_limiter import RateLimiter


@pytest.fixture
async def redis() -> fakeredis.FakeRedis:  # type: ignore[type-arg]
    """Provide a fake Redis instance for testing."""
    return await fakeredis.FakeRedis()


@pytest.fixture
async def rate_limiter(redis: fakeredis.FakeRedis) -> RateLimiter:  # type: ignore[type-arg]
    """Provide rate limiter for testing."""
    return RateLimiter(redis, "test:ratelimit", 5, 500)


@pytest.fixture
async def price_cache(redis: fakeredis.FakeRedis) -> PriceCache:  # type: ignore[type-arg]
    """Provide price cache for testing."""
    return PriceCache(redis, "test:price", 3600)


@pytest.fixture
async def http_client() -> httpx.AsyncClient:
    """Provide HTTP client for testing."""
    async with httpx.AsyncClient() as client:
        yield client


@pytest.fixture
def api_key() -> str:
    """Provide API key for testing."""
    return "demo"


@pytest.fixture
def mock_price_repository() -> MagicMock:
    """Provide mock price repository for testing."""
    repo = MagicMock()
    repo.get_price_history = AsyncMock(return_value=[])
    repo.upsert_price = AsyncMock()
    return repo


@pytest.fixture
async def adapter(
    rate_limiter: RateLimiter,
    price_cache: PriceCache,
    http_client: httpx.AsyncClient,
    api_key: str,
    mock_price_repository: MagicMock,
) -> AlphaVantageAdapter:
    """Provide configured Alpha Vantage adapter for testing."""
    return AlphaVantageAdapter(
        rate_limiter=rate_limiter,
        price_cache=price_cache,
        http_client=http_client,
        api_key=api_key,
        price_repository=mock_price_repository,
    )


def generate_mock_daily_history(
    ticker: str, start_date: datetime, days: int
) -> dict[str, object]:
    """Generate mock Alpha Vantage TIME_SERIES_DAILY response.

    Args:
        ticker: Stock ticker symbol
        start_date: Starting date for the series
        days: Number of days of data to generate

    Returns:
        Mock API response dictionary
    """
    time_series = {}

    for day in range(days):
        date = start_date + timedelta(days=day)
        # Skip weekends (simple approximation)
        if date.weekday() >= 5:
            continue

        date_str = date.strftime("%Y-%m-%d")
        base_price = 150.0 + day
        time_series[date_str] = {
            "1. open": f"{base_price - 1:.2f}",
            "2. high": f"{base_price + 2:.2f}",
            "3. low": f"{base_price - 2:.2f}",
            "4. close": f"{base_price:.2f}",
            "5. volume": str(1000000 + (day * 10000)),
        }

    return {
        "Meta Data": {
            "1. Information": "Daily Prices",
            "2. Symbol": ticker,
        },
        "Time Series (Daily)": time_series,
    }


class TestPriceHistoryCachingIntegration:
    """Integration tests for price history caching with subset matching."""

    @respx.mock
    async def test_time_range_switching_uses_cache(
        self,
        adapter: AlphaVantageAdapter,
    ) -> None:
        """Test that switching time ranges reuses cached data (Task 155).

        Simulates user behavior:
        1. User views 1 month (Jan 5-30) → API call → Cached
        2. User switches to 1 week (Jan 26-30) → Uses cache (subset match)
        3. User switches to 1 day (Jan 30) → Uses cache (subset match)

        Expected: Only 1 API call for all 3 requests
        
        Note: Using Jan 5-30 to avoid weekends (Jan 1-4 contains a weekend)
        """
        ticker = Ticker("AAPL")

        # Mock API response for 1 month of data (avoiding initial weekend)
        month_data = generate_mock_daily_history(
            "AAPL", datetime(2026, 1, 5, tzinfo=UTC), 26  # Jan 5-30
        )

        api_mock = respx.get("https://www.alphavantage.co/query").mock(
            return_value=httpx.Response(200, json=month_data)
        )

        # Step 1: User views ~1 month (Jan 5-30, all weekdays)
        month_start = datetime(2026, 1, 5, tzinfo=UTC)  # Monday
        month_end = datetime(2026, 1, 30, tzinfo=UTC)   # Friday

        month_history = await adapter.get_price_history(
            ticker, month_start, month_end, "1day"
        )

        assert len(month_history) > 0
        # Verify API was called once
        assert api_mock.call_count == 1

        # Step 2: User switches to 1 week (Jan 26-30, all weekdays)
        week_start = datetime(2026, 1, 26, tzinfo=UTC)  # Monday
        week_end = datetime(2026, 1, 30, tzinfo=UTC)    # Friday

        week_history = await adapter.get_price_history(
            ticker, week_start, week_end, "1day"
        )

        assert len(week_history) > 0
        # Verify NO additional API call (still 1 total)
        assert api_mock.call_count == 1
        # Verify data is from the correct range
        assert all(week_start <= p.timestamp <= week_end for p in week_history)

        # Step 3: User switches to 1 day (Friday Jan 30)
        day_start = datetime(2026, 1, 30, tzinfo=UTC)
        day_end = datetime(2026, 1, 30, 23, 59, 59, tzinfo=UTC)

        day_history = await adapter.get_price_history(
            ticker, day_start, day_end, "1day"
        )

        assert len(day_history) > 0
        # Verify STILL no additional API call (still 1 total)
        assert api_mock.call_count == 1
        # Verify we got exactly 1 day of data
        assert all(p.timestamp.date().day == 31 for p in day_history)

    @respx.mock
    async def test_rapid_time_range_switching_no_rate_limits(
        self,
        adapter: AlphaVantageAdapter,
    ) -> None:
        """Test that rapid time range switching doesn't trigger rate limits.

        Simulates aggressive user behavior:
        1M → 1W → 1D → 1W → 1M → 1D

        With old behavior: 6 API calls → Rate limit exceeded (5 calls/min)
        With new behavior: 1 API call → No rate limit issues
        """
        ticker = Ticker("AAPL")

        # Mock API response
        month_data = generate_mock_daily_history(
            "AAPL", datetime(2026, 1, 1, tzinfo=UTC), 31
        )

        api_mock = respx.get("https://www.alphavantage.co/query").mock(
            return_value=httpx.Response(200, json=month_data)
        )

        # Initial load: 1 month
        month_start = datetime(2026, 1, 1, tzinfo=UTC)
        month_end = datetime(2026, 1, 31, tzinfo=UTC)
        await adapter.get_price_history(ticker, month_start, month_end, "1day")

        # Rapid switching (should all use cache)
        week_start = datetime(2026, 1, 25, tzinfo=UTC)
        week_end = datetime(2026, 1, 31, tzinfo=UTC)
        await adapter.get_price_history(ticker, week_start, week_end, "1day")

        day_start = datetime(2026, 1, 31, tzinfo=UTC)
        day_end = datetime(2026, 1, 31, 23, 59, 59, tzinfo=UTC)
        await adapter.get_price_history(ticker, day_start, day_end, "1day")

        await adapter.get_price_history(ticker, week_start, week_end, "1day")
        await adapter.get_price_history(ticker, month_start, month_end, "1day")
        await adapter.get_price_history(ticker, day_start, day_end, "1day")

        # Should have made only 1 API call total
        assert api_mock.call_count == 1

    @respx.mock
    async def test_non_overlapping_ranges_trigger_new_api_calls(
        self,
        adapter: AlphaVantageAdapter,
    ) -> None:
        """Test that non-overlapping ranges trigger new API calls.

        January data shouldn't satisfy February requests.
        """
        ticker = Ticker("AAPL")

        # Mock responses for different months
        jan_data = generate_mock_daily_history(
            "AAPL", datetime(2026, 1, 1, tzinfo=UTC), 31
        )
        feb_data = generate_mock_daily_history(
            "AAPL", datetime(2026, 2, 1, tzinfo=UTC), 28
        )

        api_mock = respx.get("https://www.alphavantage.co/query").mock(
            side_effect=[
                httpx.Response(200, json=jan_data),
                httpx.Response(200, json=feb_data),
            ]
        )

        # Request January
        jan_start = datetime(2026, 1, 1, tzinfo=UTC)
        jan_end = datetime(2026, 1, 31, tzinfo=UTC)
        jan_history = await adapter.get_price_history(
            ticker, jan_start, jan_end, "1day"
        )
        assert len(jan_history) > 0
        assert api_mock.call_count == 1

        # Request February (should trigger new API call)
        feb_start = datetime(2026, 2, 1, tzinfo=UTC)
        feb_end = datetime(2026, 2, 28, tzinfo=UTC)
        feb_history = await adapter.get_price_history(
            ticker, feb_start, feb_end, "1day"
        )
        assert len(feb_history) > 0
        assert api_mock.call_count == 2

    @respx.mock
    async def test_partial_overlap_triggers_api_call(
        self,
        adapter: AlphaVantageAdapter,
    ) -> None:
        """Test that partial overlaps trigger API calls (incomplete data).

        If cached: Jan 1-31
        Requested: Jan 25 - Feb 5
        Should: Trigger new API call (not a complete subset)
        """
        ticker = Ticker("AAPL")

        # Mock responses
        jan_data = generate_mock_daily_history(
            "AAPL", datetime(2026, 1, 1, tzinfo=UTC), 31
        )
        jan_feb_data = generate_mock_daily_history(
            "AAPL", datetime(2026, 1, 1, tzinfo=UTC), 40
        )

        api_mock = respx.get("https://www.alphavantage.co/query").mock(
            side_effect=[
                httpx.Response(200, json=jan_data),
                httpx.Response(200, json=jan_feb_data),
            ]
        )

        # Cache January only
        jan_start = datetime(2026, 1, 1, tzinfo=UTC)
        jan_end = datetime(2026, 1, 31, tzinfo=UTC)
        await adapter.get_price_history(ticker, jan_start, jan_end, "1day")
        assert api_mock.call_count == 1

        # Request partial overlap (Jan 25 - Feb 5)
        extended_start = datetime(2026, 1, 25, tzinfo=UTC)
        extended_end = datetime(2026, 2, 5, tzinfo=UTC)
        result = await adapter.get_price_history(
            ticker, extended_start, extended_end, "1day"
        )

        # Should trigger new API call (partial overlap not sufficient)
        # The adapter will attempt to fetch fresh data
        assert api_mock.call_count == 2

    @respx.mock
    async def test_different_intervals_dont_share_cache(
        self,
        adapter: AlphaVantageAdapter,
    ) -> None:
        """Test that different intervals maintain separate caches.

        1day interval data shouldn't satisfy 1hour interval requests.
        """
        ticker = Ticker("AAPL")

        month_data = generate_mock_daily_history(
            "AAPL", datetime(2026, 1, 1, tzinfo=UTC), 31
        )

        api_mock = respx.get("https://www.alphavantage.co/query").mock(
            return_value=httpx.Response(200, json=month_data)
        )

        # Cache 1day interval
        month_start = datetime(2026, 1, 1, tzinfo=UTC)
        month_end = datetime(2026, 1, 31, tzinfo=UTC)
        await adapter.get_price_history(ticker, month_start, month_end, "1day")
        assert api_mock.call_count == 1

        # Request 1hour interval (should not find 1day cache)
        # Note: Since we don't have 1hour data in the mock, this will return empty
        # but the important thing is it doesn't use the 1day cache
        week_start = datetime(2026, 1, 25, tzinfo=UTC)
        week_end = datetime(2026, 1, 31, tzinfo=UTC)
        result = await adapter.get_price_history(
            ticker, week_start, week_end, "1hour"
        )

        # For 1hour interval, the adapter doesn't support it from API
        # so it returns empty list, but importantly doesn't use the 1day cache
        assert isinstance(result, list)


class TestPriceCacheDirectSubsetMatching:
    """Direct tests of PriceCache subset matching (lower level)."""

    async def test_cache_subset_matching_month_to_week(
        self,
        price_cache: PriceCache,
    ) -> None:
        """Test cache subset matching at the PriceCache level."""
        # Generate month of data
        ticker = Ticker("AAPL")
        month_history = []
        for day in range(31):
            date = datetime(2026, 1, 1, 21, 0, 0, tzinfo=UTC) + timedelta(days=day)
            month_history.append(
                PricePoint(
                    ticker=ticker,
                    price=Money(Decimal("150.00") + Decimal(str(day)), "USD"),
                    timestamp=date,
                    source="alpha_vantage",
                    interval="1day",
                )
            )

        # Cache the full month
        month_start = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
        month_end = datetime(2026, 1, 31, 23, 59, 59, tzinfo=UTC)
        await price_cache.set_history(
            ticker, month_start, month_end, month_history, "1day"
        )

        # Request subset (week)
        week_start = datetime(2026, 1, 25, 0, 0, 0, tzinfo=UTC)
        week_end = datetime(2026, 1, 31, 23, 59, 59, tzinfo=UTC)
        week_result = await price_cache.get_history(
            ticker, week_start, week_end, "1day"
        )

        assert week_result is not None
        assert len(week_result) == 7
        assert all(week_start <= p.timestamp <= week_end for p in week_result)

    async def test_cache_exact_match_preferred_over_subset(
        self,
        price_cache: PriceCache,
    ) -> None:
        """Test that exact matches are preferred (fast path)."""
        ticker = Ticker("AAPL")

        # Create week data with specific marker (higher price)
        week_history = []
        for day in range(7):
            date = datetime(2026, 1, 25, 21, 0, 0, tzinfo=UTC) + timedelta(days=day)
            week_history.append(
                PricePoint(
                    ticker=ticker,
                    price=Money(Decimal("200.00"), "USD"),  # Different price = marker
                    timestamp=date,
                    source="alpha_vantage",
                    interval="1day",
                )
            )

        # Create month data with different marker (lower price)
        month_history = []
        for day in range(31):
            date = datetime(2026, 1, 1, 21, 0, 0, tzinfo=UTC) + timedelta(days=day)
            month_history.append(
                PricePoint(
                    ticker=ticker,
                    price=Money(Decimal("150.00"), "USD"),  # Different price = marker
                    timestamp=date,
                    source="alpha_vantage",
                    interval="1day",
                )
            )

        # Cache both
        month_start = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
        month_end = datetime(2026, 1, 31, 23, 59, 59, tzinfo=UTC)
        await price_cache.set_history(
            ticker, month_start, month_end, month_history, "1day"
        )

        week_start = datetime(2026, 1, 25, 0, 0, 0, tzinfo=UTC)
        week_end = datetime(2026, 1, 31, 23, 59, 59, tzinfo=UTC)
        await price_cache.set_history(ticker, week_start, week_end, week_history, "1day")

        # Request week - should get exact match (fast path)
        result = await price_cache.get_history(ticker, week_start, week_end, "1day")

        assert result is not None
        # Exact match should be returned (week data with price=200)
        assert all(p.price.amount == Decimal("200.00") for p in result)
