"""Tests for PriceCache with Redis backend."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from fakeredis import aioredis as fakeredis

from zebu.application.dtos.price_point import PricePoint
from zebu.domain.value_objects.money import Money
from zebu.domain.value_objects.ticker import Ticker
from zebu.infrastructure.cache.price_cache import PriceCache


@pytest.fixture
async def redis() -> fakeredis.FakeRedis:  # type: ignore[type-arg]
    """Provide a fake Redis instance for testing."""
    return await fakeredis.FakeRedis()


@pytest.fixture
def sample_price() -> PricePoint:
    """Provide a sample PricePoint for testing."""
    return PricePoint(
        ticker=Ticker("AAPL"),
        price=Money(Decimal("150.25"), "USD"),
        timestamp=datetime(2025, 12, 29, 14, 0, 0, tzinfo=UTC),
        source="alpha_vantage",
        interval="real-time",
    )


class TestPriceCacheInitialization:
    """Tests for PriceCache initialization."""

    async def test_valid_initialization(self, redis: fakeredis.FakeRedis) -> None:  # type: ignore[type-arg]
        """Test creating price cache with valid parameters."""
        cache = PriceCache(redis, "test:price", 3600)

        assert cache.key_prefix == "test:price"
        assert cache.default_ttl == 3600

    async def test_initialization_without_ttl(self, redis: fakeredis.FakeRedis) -> None:  # type: ignore[type-arg]
        """Test creating price cache without default TTL."""
        cache = PriceCache(redis, "test:price")

        assert cache.key_prefix == "test:price"
        assert cache.default_ttl is None


class TestPriceCacheSetAndGet:
    """Tests for storing and retrieving prices."""

    async def test_set_and_get_price(
        self,
        redis: fakeredis.FakeRedis,  # type: ignore[type-arg]
        sample_price: PricePoint,
    ) -> None:
        """Test storing and retrieving a price."""
        cache = PriceCache(redis, "test:price")

        await cache.set(sample_price)
        retrieved = await cache.get(Ticker("AAPL"))

        assert retrieved is not None
        assert retrieved.ticker == sample_price.ticker
        assert retrieved.price == sample_price.price
        assert retrieved.timestamp == sample_price.timestamp
        assert retrieved.source == sample_price.source

    async def test_get_nonexistent_price(self, redis: fakeredis.FakeRedis) -> None:  # type: ignore[type-arg]
        """Test getting price that doesn't exist returns None."""
        cache = PriceCache(redis, "test:price")

        result = await cache.get(Ticker("TSLA"))

        assert result is None

    async def test_set_with_custom_ttl(
        self,
        redis: fakeredis.FakeRedis,  # type: ignore[type-arg]
        sample_price: PricePoint,
    ) -> None:
        """Test storing price with custom TTL."""
        cache = PriceCache(redis, "test:price", default_ttl=3600)

        # Set with custom TTL of 7200 seconds
        await cache.set(sample_price, ttl=7200)

        # Verify TTL
        ttl = await cache.get_ttl(Ticker("AAPL"))
        assert 7195 <= ttl <= 7200  # Allow small timing variance

    async def test_set_with_default_ttl(
        self,
        redis: fakeredis.FakeRedis,  # type: ignore[type-arg]
        sample_price: PricePoint,
    ) -> None:
        """Test storing price with default TTL."""
        cache = PriceCache(redis, "test:price", default_ttl=3600)

        await cache.set(sample_price)

        # Verify default TTL was used
        ttl = await cache.get_ttl(Ticker("AAPL"))
        assert 3595 <= ttl <= 3600  # Allow small timing variance

    async def test_set_without_ttl(
        self,
        redis: fakeredis.FakeRedis,  # type: ignore[type-arg]
        sample_price: PricePoint,
    ) -> None:
        """Test storing price without TTL (no expiration)."""
        cache = PriceCache(redis, "test:price")

        await cache.set(sample_price)

        # Verify no expiration
        ttl = await cache.get_ttl(Ticker("AAPL"))
        assert ttl == -1  # -1 means no expiration


class TestPriceCacheSerialization:
    """Tests for PricePoint serialization/deserialization."""

    async def test_serialize_basic_price(
        self,
        redis: fakeredis.FakeRedis,  # type: ignore[type-arg]
        sample_price: PricePoint,
    ) -> None:
        """Test serializing and deserializing basic price."""
        cache = PriceCache(redis, "test:price")

        await cache.set(sample_price)
        retrieved = await cache.get(Ticker("AAPL"))

        assert retrieved == sample_price

    async def test_serialize_price_with_ohlcv(
        self,
        redis: fakeredis.FakeRedis,  # type: ignore[type-arg]
    ) -> None:
        """Test serializing price with OHLCV data."""
        price_with_ohlcv = PricePoint(
            ticker=Ticker("AAPL"),
            price=Money(Decimal("150.25"), "USD"),
            timestamp=datetime(2025, 12, 29, 14, 0, 0, tzinfo=UTC),
            source="alpha_vantage",
            interval="1day",
            open=Money(Decimal("148.50"), "USD"),
            high=Money(Decimal("151.00"), "USD"),
            low=Money(Decimal("148.00"), "USD"),
            close=Money(Decimal("150.25"), "USD"),
            volume=1000000,
        )

        cache = PriceCache(redis, "test:price")
        await cache.set(price_with_ohlcv)
        retrieved = await cache.get(Ticker("AAPL"))

        assert retrieved is not None
        assert retrieved.open == price_with_ohlcv.open
        assert retrieved.high == price_with_ohlcv.high
        assert retrieved.low == price_with_ohlcv.low
        assert retrieved.close == price_with_ohlcv.close
        assert retrieved.volume == price_with_ohlcv.volume

    async def test_serialize_price_with_partial_ohlcv(
        self,
        redis: fakeredis.FakeRedis,  # type: ignore[type-arg]
    ) -> None:
        """Test serializing price with partial OHLCV data."""
        price_partial = PricePoint(
            ticker=Ticker("AAPL"),
            price=Money(Decimal("150.25"), "USD"),
            timestamp=datetime(2025, 12, 29, 14, 0, 0, tzinfo=UTC),
            source="alpha_vantage",
            interval="1day",
            open=Money(Decimal("148.50"), "USD"),
            high=None,
            low=None,
            close=Money(Decimal("150.25"), "USD"),
            volume=None,
        )

        cache = PriceCache(redis, "test:price")
        await cache.set(price_partial)
        retrieved = await cache.get(Ticker("AAPL"))

        assert retrieved is not None
        assert retrieved.open == price_partial.open
        assert retrieved.high is None
        assert retrieved.low is None
        assert retrieved.close == price_partial.close
        assert retrieved.volume is None


class TestPriceCacheDelete:
    """Tests for deleting cached prices."""

    async def test_delete_existing_price(
        self,
        redis: fakeredis.FakeRedis,  # type: ignore[type-arg]
        sample_price: PricePoint,
    ) -> None:
        """Test deleting a cached price."""
        cache = PriceCache(redis, "test:price")

        # Store price
        await cache.set(sample_price)
        assert await cache.get(Ticker("AAPL")) is not None

        # Delete price
        await cache.delete(Ticker("AAPL"))
        assert await cache.get(Ticker("AAPL")) is None

    async def test_delete_nonexistent_price(self, redis: fakeredis.FakeRedis) -> None:  # type: ignore[type-arg]
        """Test deleting non-existent price (no error)."""
        cache = PriceCache(redis, "test:price")

        # Delete non-existent price (should not raise error)
        await cache.delete(Ticker("TSLA"))


class TestPriceCacheExists:
    """Tests for checking price existence."""

    async def test_exists_with_cached_price(
        self,
        redis: fakeredis.FakeRedis,  # type: ignore[type-arg]
        sample_price: PricePoint,
    ) -> None:
        """Test exists returns True for cached price."""
        cache = PriceCache(redis, "test:price")

        await cache.set(sample_price)

        assert await cache.exists(Ticker("AAPL")) is True

    async def test_exists_without_cached_price(
        self, redis: fakeredis.FakeRedis
    ) -> None:  # type: ignore[type-arg]
        """Test exists returns False for non-cached price."""
        cache = PriceCache(redis, "test:price")

        assert await cache.exists(Ticker("TSLA")) is False


class TestPriceCacheGetTTL:
    """Tests for getting remaining TTL."""

    async def test_get_ttl_with_expiration(
        self,
        redis: fakeredis.FakeRedis,  # type: ignore[type-arg]
        sample_price: PricePoint,
    ) -> None:
        """Test getting TTL for price with expiration."""
        cache = PriceCache(redis, "test:price")

        await cache.set(sample_price, ttl=3600)
        ttl = await cache.get_ttl(Ticker("AAPL"))

        assert 3595 <= ttl <= 3600  # Allow small timing variance

    async def test_get_ttl_without_expiration(
        self,
        redis: fakeredis.FakeRedis,  # type: ignore[type-arg]
        sample_price: PricePoint,
    ) -> None:
        """Test getting TTL for price without expiration."""
        cache = PriceCache(redis, "test:price")

        await cache.set(sample_price)  # No TTL
        ttl = await cache.get_ttl(Ticker("AAPL"))

        assert ttl == -1  # -1 means no expiration

    async def test_get_ttl_nonexistent_key(self, redis: fakeredis.FakeRedis) -> None:  # type: ignore[type-arg]
        """Test getting TTL for non-existent key."""
        cache = PriceCache(redis, "test:price")

        ttl = await cache.get_ttl(Ticker("TSLA"))

        assert ttl == -2  # -2 means key doesn't exist


class TestPriceCacheKeyGeneration:
    """Tests for Redis key generation."""

    async def test_key_format(
        self,
        redis: fakeredis.FakeRedis,  # type: ignore[type-arg]
        sample_price: PricePoint,
    ) -> None:
        """Test that keys are formatted correctly."""
        cache = PriceCache(redis, "zebu:price")

        key = cache._get_key(Ticker("AAPL"))

        assert key == "zebu:price:AAPL"

    async def test_different_prefixes_isolated(
        self,
        redis: fakeredis.FakeRedis,  # type: ignore[type-arg]
        sample_price: PricePoint,
    ) -> None:
        """Test that different key prefixes are isolated."""
        cache1 = PriceCache(redis, "cache1:price")
        cache2 = PriceCache(redis, "cache2:price")

        # Store in cache1
        await cache1.set(sample_price)

        # Should exist in cache1
        assert await cache1.exists(Ticker("AAPL")) is True

        # Should NOT exist in cache2
        assert await cache2.exists(Ticker("AAPL")) is False


class TestPriceCacheHistoryMethods:
    """Tests for price history caching methods."""

    @pytest.fixture
    def sample_history(self) -> list[PricePoint]:
        """Provide sample price history for testing."""
        return [
            PricePoint(
                ticker=Ticker("AAPL"),
                price=Money(Decimal("150.00"), "USD"),
                timestamp=datetime(2025, 12, 1, 21, 0, 0, tzinfo=UTC),
                source="alpha_vantage",
                interval="1day",
                open=Money(Decimal("149.00"), "USD"),
                high=Money(Decimal("151.00"), "USD"),
                low=Money(Decimal("148.00"), "USD"),
                close=Money(Decimal("150.00"), "USD"),
                volume=1000000,
            ),
            PricePoint(
                ticker=Ticker("AAPL"),
                price=Money(Decimal("151.00"), "USD"),
                timestamp=datetime(2025, 12, 2, 21, 0, 0, tzinfo=UTC),
                source="alpha_vantage",
                interval="1day",
                open=Money(Decimal("150.00"), "USD"),
                high=Money(Decimal("152.00"), "USD"),
                low=Money(Decimal("149.00"), "USD"),
                close=Money(Decimal("151.00"), "USD"),
                volume=1100000,
            ),
            PricePoint(
                ticker=Ticker("AAPL"),
                price=Money(Decimal("152.00"), "USD"),
                timestamp=datetime(2025, 12, 3, 21, 0, 0, tzinfo=UTC),
                source="alpha_vantage",
                interval="1day",
                open=Money(Decimal("151.00"), "USD"),
                high=Money(Decimal("153.00"), "USD"),
                low=Money(Decimal("150.00"), "USD"),
                close=Money(Decimal("152.00"), "USD"),
                volume=1200000,
            ),
        ]

    async def test_set_and_get_history(
        self,
        redis: fakeredis.FakeRedis,  # type: ignore[type-arg]
        sample_history: list[PricePoint],
    ) -> None:
        """Test storing and retrieving price history."""
        cache = PriceCache(redis, "test:price")

        start = datetime(2025, 12, 1, 0, 0, 0, tzinfo=UTC)
        end = datetime(2025, 12, 3, 23, 59, 59, tzinfo=UTC)

        await cache.set_history(
            Ticker("AAPL"), start, end, sample_history, interval="1day"
        )
        retrieved = await cache.get_history(Ticker("AAPL"), start, end, interval="1day")

        assert retrieved is not None
        assert len(retrieved) == len(sample_history)
        for i, price in enumerate(retrieved):
            assert price.ticker == sample_history[i].ticker
            assert price.price == sample_history[i].price
            assert price.timestamp == sample_history[i].timestamp
            assert price.source == sample_history[i].source
            assert price.interval == sample_history[i].interval
            assert price.open == sample_history[i].open
            assert price.high == sample_history[i].high
            assert price.low == sample_history[i].low
            assert price.close == sample_history[i].close
            assert price.volume == sample_history[i].volume

    async def test_get_nonexistent_history(
        self,
        redis: fakeredis.FakeRedis,  # type: ignore[type-arg]
    ) -> None:
        """Test getting history that doesn't exist returns None."""
        cache = PriceCache(redis, "test:price")

        start = datetime(2025, 12, 1, 0, 0, 0, tzinfo=UTC)
        end = datetime(2025, 12, 3, 23, 59, 59, tzinfo=UTC)

        result = await cache.get_history(Ticker("TSLA"), start, end)

        assert result is None

    async def test_set_history_with_custom_ttl(
        self,
        redis: fakeredis.FakeRedis,  # type: ignore[type-arg]
        sample_history: list[PricePoint],
    ) -> None:
        """Test storing history with custom TTL."""
        cache = PriceCache(redis, "test:price", default_ttl=3600)

        start = datetime(2025, 12, 1, 0, 0, 0, tzinfo=UTC)
        end = datetime(2025, 12, 3, 23, 59, 59, tzinfo=UTC)

        # Set with custom TTL of 7 days
        await cache.set_history(
            Ticker("AAPL"),
            start,
            end,
            sample_history,
            interval="1day",
            ttl=7 * 24 * 3600,
        )

        # Verify TTL by checking individual day keys
        from datetime import date

        expected_ttl = 7 * 24 * 3600
        for day_num in [1, 2, 3]:
            key = cache._get_day_key(Ticker("AAPL"), date(2025, 12, day_num), "1day")
            ttl = await redis.ttl(key)
            # Allow for some timing variance (should be close to 7 days)
            assert expected_ttl - 5 <= ttl <= expected_ttl

    async def test_set_history_with_default_ttl(
        self,
        redis: fakeredis.FakeRedis,  # type: ignore[type-arg]
        sample_history: list[PricePoint],
    ) -> None:
        """Test storing history with default TTL."""
        cache = PriceCache(redis, "test:price", default_ttl=3600)

        start = datetime(2025, 12, 1, 0, 0, 0, tzinfo=UTC)
        end = datetime(2025, 12, 3, 23, 59, 59, tzinfo=UTC)

        await cache.set_history(
            Ticker("AAPL"), start, end, sample_history, interval="1day"
        )

        # Verify default TTL was used on individual day keys
        from datetime import date

        for day_num in [1, 2, 3]:
            key = cache._get_day_key(Ticker("AAPL"), date(2025, 12, day_num), "1day")
            ttl = await redis.ttl(key)
            assert 3595 <= ttl <= 3600  # Allow small timing variance

    async def test_different_ranges_isolated(
        self,
        redis: fakeredis.FakeRedis,  # type: ignore[type-arg]
        sample_history: list[PricePoint],
    ) -> None:
        """Test that different date ranges are isolated in cache."""
        cache = PriceCache(redis, "test:price")

        start1 = datetime(2025, 12, 1, 0, 0, 0, tzinfo=UTC)
        end1 = datetime(2025, 12, 3, 23, 59, 59, tzinfo=UTC)

        start2 = datetime(2025, 12, 4, 0, 0, 0, tzinfo=UTC)
        end2 = datetime(2025, 12, 6, 23, 59, 59, tzinfo=UTC)

        # Store in first range
        await cache.set_history(Ticker("AAPL"), start1, end1, sample_history)

        # Should exist for first range
        result1 = await cache.get_history(Ticker("AAPL"), start1, end1)
        assert result1 is not None

        # Should NOT exist for second range
        result2 = await cache.get_history(Ticker("AAPL"), start2, end2)
        assert result2 is None


class TestPriceCachePerDayStorage:
    """Tests for per-day storage implementation."""

    @pytest.fixture
    def sample_history(self) -> list[PricePoint]:
        """Provide sample price history for testing."""
        return [
            PricePoint(
                ticker=Ticker("AAPL"),
                price=Money(Decimal("150.00"), "USD"),
                timestamp=datetime(2026, 1, 1, 21, 0, 0, tzinfo=UTC),
                source="alpha_vantage",
                interval="1day",
                open=Money(Decimal("149.00"), "USD"),
                high=Money(Decimal("151.00"), "USD"),
                low=Money(Decimal("148.00"), "USD"),
                close=Money(Decimal("150.00"), "USD"),
                volume=1000000,
            ),
            PricePoint(
                ticker=Ticker("AAPL"),
                price=Money(Decimal("151.00"), "USD"),
                timestamp=datetime(2026, 1, 2, 21, 0, 0, tzinfo=UTC),
                source="alpha_vantage",
                interval="1day",
                open=Money(Decimal("150.00"), "USD"),
                high=Money(Decimal("152.00"), "USD"),
                low=Money(Decimal("149.00"), "USD"),
                close=Money(Decimal("151.00"), "USD"),
                volume=1100000,
            ),
            PricePoint(
                ticker=Ticker("AAPL"),
                price=Money(Decimal("152.00"), "USD"),
                timestamp=datetime(2026, 1, 3, 21, 0, 0, tzinfo=UTC),
                source="alpha_vantage",
                interval="1day",
                open=Money(Decimal("151.00"), "USD"),
                high=Money(Decimal("153.00"), "USD"),
                low=Money(Decimal("150.00"), "USD"),
                close=Money(Decimal("152.00"), "USD"),
                volume=1200000,
            ),
        ]

    async def test_set_history_stores_individual_days(
        self,
        redis: fakeredis.FakeRedis,  # type: ignore[type-arg]
        sample_history: list[PricePoint],
    ) -> None:
        """Verify each price point gets its own Redis key."""
        cache = PriceCache(redis, "test:price")

        start = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
        end = datetime(2026, 1, 3, 23, 59, 59, tzinfo=UTC)

        await cache.set_history(
            Ticker("AAPL"), start, end, sample_history, interval="1day"
        )

        # Verify three separate keys exist
        key1 = "test:price:AAPL:1day:2026-01-01"
        key2 = "test:price:AAPL:1day:2026-01-02"
        key3 = "test:price:AAPL:1day:2026-01-03"

        assert await redis.exists(key1) == 1
        assert await redis.exists(key2) == 1
        assert await redis.exists(key3) == 1

    async def test_get_history_returns_partial_results(
        self,
        redis: fakeredis.FakeRedis,  # type: ignore[type-arg]
    ) -> None:
        """Verify partial cache hits return available days."""
        cache = PriceCache(redis, "test:price")

        # Cache only days 1-2
        prices_partial = [
            PricePoint(
                ticker=Ticker("AAPL"),
                price=Money(Decimal("150.00"), "USD"),
                timestamp=datetime(2026, 1, 1, 21, 0, 0, tzinfo=UTC),
                source="alpha_vantage",
                interval="1day",
            ),
            PricePoint(
                ticker=Ticker("AAPL"),
                price=Money(Decimal("151.00"), "USD"),
                timestamp=datetime(2026, 1, 2, 21, 0, 0, tzinfo=UTC),
                source="alpha_vantage",
                interval="1day",
            ),
        ]

        start_cache = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
        end_cache = datetime(2026, 1, 2, 23, 59, 59, tzinfo=UTC)

        await cache.set_history(
            Ticker("AAPL"), start_cache, end_cache, prices_partial, interval="1day"
        )

        # Request days 1-5 (should get back only 1-2)
        start_request = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
        end_request = datetime(2026, 1, 5, 23, 59, 59, tzinfo=UTC)

        result = await cache.get_history(
            Ticker("AAPL"), start_request, end_request, interval="1day"
        )

        # Should return the 2 days we have
        assert result is not None
        assert len(result) == 2
        assert result[0].timestamp.date().day == 1
        assert result[1].timestamp.date().day == 2

    async def test_overlapping_ranges_reuse_cached_days(
        self,
        redis: fakeredis.FakeRedis,  # type: ignore[type-arg]
    ) -> None:
        """Verify time range switching uses cached days."""
        cache = PriceCache(redis, "test:price")

        # Cache 1 month (Jan 1-31)
        month_prices = []
        for day in range(1, 32):
            month_prices.append(
                PricePoint(
                    ticker=Ticker("AAPL"),
                    price=Money(Decimal("150.00") + Decimal(day), "USD"),
                    timestamp=datetime(2026, 1, day, 21, 0, 0, tzinfo=UTC),
                    source="alpha_vantage",
                    interval="1day",
                )
            )

        start_month = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
        end_month = datetime(2026, 1, 31, 23, 59, 59, tzinfo=UTC)

        await cache.set_history(
            Ticker("AAPL"), start_month, end_month, month_prices, interval="1day"
        )

        # Request 1 week (Jan 25-31) - should find all 7 days in cache
        start_week = datetime(2026, 1, 25, 0, 0, 0, tzinfo=UTC)
        end_week = datetime(2026, 1, 31, 23, 59, 59, tzinfo=UTC)

        week_result = await cache.get_history(
            Ticker("AAPL"), start_week, end_week, interval="1day"
        )

        assert week_result is not None
        assert len(week_result) == 7

        # Request 1 day (Jan 31) - should find in cache
        start_day = datetime(2026, 1, 31, 0, 0, 0, tzinfo=UTC)
        end_day = datetime(2026, 1, 31, 23, 59, 59, tzinfo=UTC)

        day_result = await cache.get_history(
            Ticker("AAPL"), start_day, end_day, interval="1day"
        )

        assert day_result is not None
        assert len(day_result) == 1
        assert day_result[0].timestamp.date().day == 31

    async def test_set_history_applies_ttl_to_all_days(
        self,
        redis: fakeredis.FakeRedis,  # type: ignore[type-arg]
    ) -> None:
        """Verify custom TTL is applied to all cached days."""
        cache = PriceCache(redis, "test:price")

        prices = []
        for day in range(1, 4):
            prices.append(
                PricePoint(
                    ticker=Ticker("AAPL"),
                    price=Money(Decimal("150.00"), "USD"),
                    timestamp=datetime(2026, 1, day, 21, 0, 0, tzinfo=UTC),
                    source="alpha_vantage",
                    interval="1day",
                )
            )

        start = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
        end = datetime(2026, 1, 3, 23, 59, 59, tzinfo=UTC)

        custom_ttl = 7 * 24 * 3600  # 7 days
        await cache.set_history(
            Ticker("AAPL"), start, end, prices, interval="1day", ttl=custom_ttl
        )

        # Check TTL on all keys
        for day in [1, 2, 3]:
            key = f"test:price:AAPL:1day:2026-01-0{day}"
            ttl = await redis.ttl(key)
            # Allow for some timing variance
            assert custom_ttl - 5 <= ttl <= custom_ttl

    async def test_per_day_key_format(
        self,
        redis: fakeredis.FakeRedis,  # type: ignore[type-arg]
    ) -> None:
        """Test that per-day keys are formatted correctly."""
        from datetime import date

        cache = PriceCache(redis, "zebu:price")

        key = cache._get_day_key(Ticker("AAPL"), date(2026, 1, 15), "1day")

        assert key == "zebu:price:AAPL:1day:2026-01-15"

    async def test_empty_result_returns_none(
        self,
        redis: fakeredis.FakeRedis,  # type: ignore[type-arg]
    ) -> None:
        """Test that requesting non-cached days returns None."""
        cache = PriceCache(redis, "test:price")

        start = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
        end = datetime(2026, 1, 5, 23, 59, 59, tzinfo=UTC)

        result = await cache.get_history(Ticker("TSLA"), start, end, interval="1day")

        assert result is None
