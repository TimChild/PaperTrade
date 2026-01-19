"""Integration tests for AlphaVantageAdapter.

These tests verify the full integration of the Alpha Vantage adapter including:
- HTTP requests to Alpha Vantage API (mocked with respx library)
- Rate limiting behavior
- Cache integration
- Error handling

We use the `respx` library to mock HTTP responses for httpx, which works seamlessly
with async code and is more reliable than VCR cassettes for CI/CD environments.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import httpx
import pytest
import respx
from fakeredis import aioredis as fakeredis

from zebu.adapters.outbound.market_data.alpha_vantage_adapter import (
    AlphaVantageAdapter,
)
from zebu.application.exceptions import (
    MarketDataUnavailableError,
    TickerNotFoundError,
)
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
async def adapter(
    rate_limiter: RateLimiter,
    price_cache: PriceCache,
    http_client: httpx.AsyncClient,
    api_key: str,
) -> AlphaVantageAdapter:
    """Provide configured Alpha Vantage adapter for testing."""
    return AlphaVantageAdapter(
        rate_limiter=rate_limiter,
        price_cache=price_cache,
        http_client=http_client,
        api_key=api_key,
    )


class TestAlphaVantageAdapterCacheMiss:
    """Tests for cache miss scenarios (API calls)."""

    @respx.mock
    async def test_get_current_price_aapl(
        self,
        adapter: AlphaVantageAdapter,
    ) -> None:
        """Test fetching AAPL price from API (cache miss)."""
        # Mock datetime to return a trading day (Monday, Jan 13, 2026)
        from unittest.mock import patch

        mock_now = datetime(2026, 1, 13, 10, 0, 0, tzinfo=UTC)

        # Mock Alpha Vantage API response
        respx.get("https://www.alphavantage.co/query").mock(
            return_value=httpx.Response(
                200,
                json={
                    "Global Quote": {
                        "01. symbol": "AAPL",
                        "05. price": "194.50",
                        "07. latest trading day": "2025-12-27",
                    }
                },
            )
        )

        with patch(
            "zebu.adapters.outbound.market_data.alpha_vantage_adapter.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(
                *args, **kwargs
            )

            price = await adapter.get_current_price(Ticker("AAPL"))

        # Verify basic properties
        assert price.ticker.symbol == "AAPL"
        assert price.price.amount == Decimal("194.50")
        assert price.price.currency == "USD"
        assert price.source == "alpha_vantage"
        assert price.interval == "1day"
        assert price.timestamp.tzinfo == UTC

    @respx.mock
    async def test_get_current_price_tsla(
        self,
        adapter: AlphaVantageAdapter,
    ) -> None:
        """Test fetching TSLA price from API (cache miss)."""
        # Mock datetime to return a trading day (Monday, Jan 13, 2026)
        from unittest.mock import patch

        mock_now = datetime(2026, 1, 13, 10, 0, 0, tzinfo=UTC)

        respx.get("https://www.alphavantage.co/query").mock(
            return_value=httpx.Response(
                200,
                json={
                    "Global Quote": {
                        "01. symbol": "TSLA",
                        "05. price": "383.75",
                        "07. latest trading day": "2025-12-27",
                    }
                },
            )
        )

        with patch(
            "zebu.adapters.outbound.market_data.alpha_vantage_adapter.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(
                *args, **kwargs
            )

            price = await adapter.get_current_price(Ticker("TSLA"))

        assert price.ticker.symbol == "TSLA"
        assert price.price.amount == Decimal("383.75")
        assert price.source == "alpha_vantage"

    @respx.mock
    async def test_get_current_price_invalid_ticker(
        self,
        adapter: AlphaVantageAdapter,
    ) -> None:
        """Test fetching price for invalid ticker raises TickerNotFoundError."""
        # Mock datetime to return a trading day (Monday, Jan 13, 2026)
        from unittest.mock import patch

        mock_now = datetime(2026, 1, 13, 10, 0, 0, tzinfo=UTC)

        # Alpha Vantage returns empty Global Quote for invalid tickers
        respx.get("https://www.alphavantage.co/query").mock(
            return_value=httpx.Response(
                200,
                json={"Global Quote": {}},
            )
        )

        with patch(
            "zebu.adapters.outbound.market_data.alpha_vantage_adapter.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(
                *args, **kwargs
            )

            with pytest.raises(TickerNotFoundError) as exc_info:
                await adapter.get_current_price(Ticker("XXXXX"))

        # Check that error message mentions ticker
        assert exc_info.value.ticker == "XXXXX"


class TestAlphaVantageAdapterCacheHit:
    """Tests for cache hit scenarios (no API calls)."""

    @respx.mock
    async def test_get_current_price_cache_hit(
        self,
        adapter: AlphaVantageAdapter,
        price_cache: PriceCache,
    ) -> None:
        """Test that second request hits cache (no API call)."""
        from datetime import date
        from unittest.mock import patch

        # Mock datetime to return a trading day (Monday, Jan 13, 2026)
        # Use the same time for both calls to ensure cache doesn't expire
        mock_now = datetime(2026, 1, 13, 10, 0, 0, tzinfo=UTC)

        # Use today's date to ensure price is fresh (not stale)
        today = date.today().isoformat()

        mock_route = respx.get("https://www.alphavantage.co/query").mock(
            return_value=httpx.Response(
                200,
                json={
                    "Global Quote": {
                        "01. symbol": "AAPL",
                        "05. price": "194.50",
                        "07. latest trading day": today,
                    }
                },
            )
        )

        # Patch datetime in both adapter and price_point modules
        with (
            patch(
                "zebu.adapters.outbound.market_data.alpha_vantage_adapter.datetime"
            ) as mock_datetime_adapter,
            patch("zebu.application.dtos.price_point.datetime") as mock_datetime_price,
        ):
            mock_datetime_adapter.now.return_value = mock_now
            mock_datetime_adapter.side_effect = lambda *args, **kwargs: datetime(
                *args, **kwargs
            )
            mock_datetime_price.now.return_value = mock_now
            mock_datetime_price.side_effect = lambda *args, **kwargs: datetime(
                *args, **kwargs
            )

            # First call - populates cache
            price1 = await adapter.get_current_price(Ticker("AAPL"))
            assert price1.source == "alpha_vantage"
            assert mock_route.called

            # Verify cache was populated (with original alpha_vantage source)
            cached = await price_cache.get(Ticker("AAPL"))
            assert cached is not None
            assert cached.source == "alpha_vantage"  # Cached value has original source

            # Reset mock call count
            initial_call_count = len(mock_route.calls)

            # Second call - hits cache (no new HTTP request)
            price2 = await adapter.get_current_price(Ticker("AAPL"))
            assert (
                price2.source == "cache"
            )  # Returned value has source changed to "cache"
            assert price2.ticker == price1.ticker
            assert price2.price == price1.price
            # Verify no additional API calls were made
            assert len(mock_route.calls) == initial_call_count

    @respx.mock
    async def test_get_current_price_stale_cache_refresh(
        self,
        adapter: AlphaVantageAdapter,
        price_cache: PriceCache,
    ) -> None:
        """Test that stale cache triggers API refresh."""
        from unittest.mock import patch

        from zebu.application.dtos.price_point import PricePoint
        from zebu.domain.value_objects.money import Money

        # Mock datetime to return a trading day (Monday, Jan 13, 2026)
        mock_now = datetime(2026, 1, 13, 10, 0, 0, tzinfo=UTC)

        # Manually insert stale price (2 hours old)
        stale_price = PricePoint(
            ticker=Ticker("AAPL"),
            price=Money(Decimal("100.00"), "USD"),
            timestamp=datetime.now(UTC) - timedelta(hours=2),
            source="alpha_vantage",
            interval="1day",
        )
        await price_cache.set(stale_price)

        # Mock API response with fresh price
        respx.get("https://www.alphavantage.co/query").mock(
            return_value=httpx.Response(
                200,
                json={
                    "Global Quote": {
                        "01. symbol": "AAPL",
                        "05. price": "194.50",
                        "07. latest trading day": "2025-12-27",
                    }
                },
            )
        )

        with patch(
            "zebu.adapters.outbound.market_data.alpha_vantage_adapter.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(
                *args, **kwargs
            )

            # Request should fetch fresh data from API (not serve stale cache)
            price = await adapter.get_current_price(Ticker("AAPL"))

        assert price.price.amount == Decimal("194.50")
        assert price.source == "alpha_vantage"


class TestAlphaVantageAdapterRateLimiting:
    """Tests for rate limiting behavior."""

    async def test_rate_limit_serves_stale_cache(
        self,
        adapter: AlphaVantageAdapter,
        price_cache: PriceCache,
        rate_limiter: RateLimiter,
    ) -> None:
        """Test that rate limiting serves stale cached data when available."""
        from unittest.mock import patch

        from zebu.application.dtos.price_point import PricePoint
        from zebu.domain.value_objects.money import Money

        # Mock datetime to return a trading day (Monday, Jan 13, 2026)
        mock_now = datetime(2026, 1, 13, 10, 0, 0, tzinfo=UTC)

        # Manually insert stale price
        stale_price = PricePoint(
            ticker=Ticker("AAPL"),
            price=Money(Decimal("100.00"), "USD"),
            timestamp=datetime.now(UTC) - timedelta(hours=2),
            source="alpha_vantage",
            interval="1day",
        )
        await price_cache.set(stale_price)

        # Exhaust rate limiter
        for _ in range(5):
            await rate_limiter.consume_token()

        with patch(
            "zebu.adapters.outbound.market_data.alpha_vantage_adapter.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(
                *args, **kwargs
            )

            # Should serve stale cache when rate limited
            price = await adapter.get_current_price(Ticker("AAPL"))

        assert price.source == "cache"
        assert price.price.amount == Decimal("100.00")

    async def test_rate_limit_no_cache_raises_error(
        self,
        adapter: AlphaVantageAdapter,
        rate_limiter: RateLimiter,
    ) -> None:
        """Test that rate limiting without cached data raises error."""
        from unittest.mock import patch

        # Mock datetime to return a trading day (Monday, Jan 13, 2026)
        mock_now = datetime(2026, 1, 13, 10, 0, 0, tzinfo=UTC)

        # Exhaust rate limiter
        for _ in range(5):
            await rate_limiter.consume_token()

        with patch(
            "zebu.adapters.outbound.market_data.alpha_vantage_adapter.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(
                *args, **kwargs
            )

            # Should raise error when rate limited and no cache
            with pytest.raises(MarketDataUnavailableError) as exc_info:
                await adapter.get_current_price(Ticker("AAPL"))

        assert "Rate limit exceeded" in str(exc_info.value)


class TestAlphaVantageAdapterHistoricalData:
    """Tests for historical data methods (Phase 2b)."""

    async def test_get_price_at_without_repository(
        self,
        adapter: AlphaVantageAdapter,
    ) -> None:
        """Test get_price_at raises error when repository not configured."""
        with pytest.raises(MarketDataUnavailableError) as exc_info:
            await adapter.get_price_at(
                Ticker("AAPL"),
                datetime(2024, 6, 15, 16, 0, tzinfo=UTC),
            )

        assert "Price repository not configured" in str(exc_info.value)

    async def test_get_price_at_future_timestamp(
        self,
        adapter: AlphaVantageAdapter,
    ) -> None:
        """Test get_price_at raises error for future timestamp."""
        future = datetime.now(UTC) + timedelta(days=1)

        with pytest.raises(MarketDataUnavailableError) as exc_info:
            await adapter.get_price_at(Ticker("AAPL"), future)

        assert "future timestamp" in str(exc_info.value).lower()

    async def test_get_price_history_without_repository(
        self,
        adapter: AlphaVantageAdapter,
    ) -> None:
        """Test get_price_history raises error when repository not configured."""
        with pytest.raises(MarketDataUnavailableError) as exc_info:
            await adapter.get_price_history(
                Ticker("AAPL"),
                datetime(2024, 1, 1, tzinfo=UTC),
                datetime(2024, 12, 31, tzinfo=UTC),
            )

        assert "Price repository not configured" in str(exc_info.value)

    async def test_get_price_history_invalid_range(
        self,
        adapter: AlphaVantageAdapter,
    ) -> None:
        """Test get_price_history raises ValueError for invalid date range."""
        # End before start
        with pytest.raises(ValueError) as exc_info:
            await adapter.get_price_history(
                Ticker("AAPL"),
                datetime(2024, 12, 31, tzinfo=UTC),
                datetime(2024, 1, 1, tzinfo=UTC),
            )

        assert "End date" in str(exc_info.value)

    async def test_get_price_history_invalid_interval(
        self,
        adapter: AlphaVantageAdapter,
    ) -> None:
        """Test get_price_history raises ValueError for invalid interval."""
        with pytest.raises(ValueError) as exc_info:
            await adapter.get_price_history(
                Ticker("AAPL"),
                datetime(2024, 1, 1, tzinfo=UTC),
                datetime(2024, 12, 31, tzinfo=UTC),
                interval="invalid",
            )

        assert "Invalid interval" in str(exc_info.value)

    async def test_get_supported_tickers_without_repository(
        self,
        adapter: AlphaVantageAdapter,
    ) -> None:
        """Test get_supported_tickers returns empty list without repository."""
        tickers = await adapter.get_supported_tickers()
        assert tickers == []


class TestAlphaVantageAdapterPerformance:
    """Tests for performance characteristics."""

    @respx.mock
    async def test_cache_hit_performance(
        self,
        adapter: AlphaVantageAdapter,
    ) -> None:
        """Test that cache hits are fast (<100ms)."""
        import time
        from unittest.mock import patch

        # Mock datetime to return a trading day (Monday, Jan 13, 2026)
        mock_now = datetime(2026, 1, 13, 10, 0, 0, tzinfo=UTC)

        respx.get("https://www.alphavantage.co/query").mock(
            return_value=httpx.Response(
                200,
                json={
                    "Global Quote": {
                        "01. symbol": "AAPL",
                        "05. price": "194.50",
                        "07. latest trading day": "2025-12-27",
                    }
                },
            )
        )

        with patch(
            "zebu.adapters.outbound.market_data.alpha_vantage_adapter.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(
                *args, **kwargs
            )

            # First call - populate cache
            await adapter.get_current_price(Ticker("AAPL"))

            # Second call - should be fast (cache hit)
            start = time.time()
            await adapter.get_current_price(Ticker("AAPL"))
            elapsed = time.time() - start

        # Cache hit should be very fast (well under 100ms)
        # Using 100ms threshold
        assert elapsed < 0.1
