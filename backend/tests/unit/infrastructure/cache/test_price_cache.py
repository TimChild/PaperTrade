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

        # Verify TTL by checking key exists and has expected TTL
        key = cache._get_history_key(Ticker("AAPL"), start, end, "1day")
        ttl = await redis.ttl(key)
        # Allow for some timing variance (should be close to 7 days)
        expected_ttl = 7 * 24 * 3600
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

        # Verify default TTL was used
        key = cache._get_history_key(Ticker("AAPL"), start, end, "1day")
        ttl = await redis.ttl(key)
        assert 3595 <= ttl <= 3600  # Allow small timing variance

    async def test_history_key_format(
        self,
        redis: fakeredis.FakeRedis,  # type: ignore[type-arg]
    ) -> None:
        """Test that history keys are formatted correctly."""
        cache = PriceCache(redis, "zebu:price")

        start = datetime(2025, 12, 1, 0, 0, 0, tzinfo=UTC)
        end = datetime(2025, 12, 3, 23, 59, 59, tzinfo=UTC)

        key = cache._get_history_key(Ticker("AAPL"), start, end, "1day")

        assert key == "zebu:price:AAPL:history:2025-12-01:2025-12-03:1day"

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


class TestPriceCacheSubsetMatching:
    """Tests for subset cache matching (Task 155)."""

    @pytest.fixture
    def month_history(self) -> list[PricePoint]:
        """Provide a full month of price history for testing."""
        from datetime import timedelta

        base_date = datetime(2026, 1, 1, 21, 0, 0, tzinfo=UTC)
        history = []

        # Generate 31 days of data (Jan 1-31)
        for day in range(31):
            price = Decimal("150.00") + Decimal(str(day))
            history.append(
                PricePoint(
                    ticker=Ticker("AAPL"),
                    price=Money(price, "USD"),
                    timestamp=base_date + timedelta(days=day),
                    source="alpha_vantage",
                    interval="1day",
                    open=Money(price - Decimal("1.00"), "USD"),
                    high=Money(price + Decimal("2.00"), "USD"),
                    low=Money(price - Decimal("2.00"), "USD"),
                    close=Money(price, "USD"),
                    volume=1000000 + (day * 10000),
                )
            )

        return history

    async def test_exact_match_still_works(
        self,
        redis: fakeredis.FakeRedis,  # type: ignore[type-arg]
        month_history: list[PricePoint],
    ) -> None:
        """Test that exact cache key matches still work (fast path regression test)."""
        cache = PriceCache(redis, "test:price")

        # Cache full month
        start = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
        end = datetime(2026, 1, 31, 23, 59, 59, tzinfo=UTC)

        await cache.set_history(Ticker("AAPL"), start, end, month_history)

        # Request exact same range
        result = await cache.get_history(Ticker("AAPL"), start, end)

        assert result is not None
        assert len(result) == 31
        assert result[0].timestamp == month_history[0].timestamp
        assert result[-1].timestamp == month_history[-1].timestamp

    async def test_subset_match_finds_broader_range(
        self,
        redis: fakeredis.FakeRedis,  # type: ignore[type-arg]
        month_history: list[PricePoint],
    ) -> None:
        """Test that subset requests find broader cached ranges."""
        cache = PriceCache(redis, "test:price")

        # Cache full month (Jan 1-31)
        month_start = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
        month_end = datetime(2026, 1, 31, 23, 59, 59, tzinfo=UTC)
        await cache.set_history(Ticker("AAPL"), month_start, month_end, month_history)

        # Request subset: last week (Jan 25-31)
        week_start = datetime(2026, 1, 25, 0, 0, 0, tzinfo=UTC)
        week_end = datetime(2026, 1, 31, 23, 59, 59, tzinfo=UTC)

        result = await cache.get_history(Ticker("AAPL"), week_start, week_end)

        # Should find the broader month range and filter it
        assert result is not None
        assert len(result) == 7  # 7 days (Jan 25-31)
        assert result[0].timestamp.date().day == 25
        assert result[-1].timestamp.date().day == 31

    async def test_subset_match_one_day_from_month(
        self,
        redis: fakeredis.FakeRedis,  # type: ignore[type-arg]
        month_history: list[PricePoint],
    ) -> None:
        """Test that single day requests find broader cached ranges."""
        cache = PriceCache(redis, "test:price")

        # Cache full month (Jan 1-31)
        month_start = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
        month_end = datetime(2026, 1, 31, 23, 59, 59, tzinfo=UTC)
        await cache.set_history(Ticker("AAPL"), month_start, month_end, month_history)

        # Request single day (Jan 31)
        day_start = datetime(2026, 1, 31, 0, 0, 0, tzinfo=UTC)
        day_end = datetime(2026, 1, 31, 23, 59, 59, tzinfo=UTC)

        result = await cache.get_history(Ticker("AAPL"), day_start, day_end)

        # Should find the month and filter to single day
        assert result is not None
        assert len(result) == 1
        assert result[0].timestamp.date().day == 31

    async def test_no_overlap_returns_none(
        self,
        redis: fakeredis.FakeRedis,  # type: ignore[type-arg]
        month_history: list[PricePoint],
    ) -> None:
        """Test that non-overlapping ranges return None."""
        cache = PriceCache(redis, "test:price")

        # Cache January
        jan_start = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
        jan_end = datetime(2026, 1, 31, 23, 59, 59, tzinfo=UTC)
        await cache.set_history(Ticker("AAPL"), jan_start, jan_end, month_history)

        # Request February (no overlap)
        feb_start = datetime(2026, 2, 1, 0, 0, 0, tzinfo=UTC)
        feb_end = datetime(2026, 2, 28, 23, 59, 59, tzinfo=UTC)

        result = await cache.get_history(Ticker("AAPL"), feb_start, feb_end)

        # Should return None (trigger API call)
        assert result is None

    async def test_partial_overlap_returns_none(
        self,
        redis: fakeredis.FakeRedis,  # type: ignore[type-arg]
        month_history: list[PricePoint],
    ) -> None:
        """Test that partial overlaps return None (incomplete data)."""
        cache = PriceCache(redis, "test:price")

        # Cache January
        jan_start = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
        jan_end = datetime(2026, 1, 31, 23, 59, 59, tzinfo=UTC)
        await cache.set_history(Ticker("AAPL"), jan_start, jan_end, month_history)

        # Request range that extends beyond cache (Jan 25 - Feb 5)
        extended_start = datetime(2026, 1, 25, 0, 0, 0, tzinfo=UTC)
        extended_end = datetime(2026, 2, 5, 23, 59, 59, tzinfo=UTC)

        result = await cache.get_history(Ticker("AAPL"), extended_start, extended_end)

        # Should return None (not a complete subset)
        assert result is None

    async def test_multiple_cached_ranges_picks_match(
        self,
        redis: fakeredis.FakeRedis,  # type: ignore[type-arg]
        month_history: list[PricePoint],
    ) -> None:
        """Test that with multiple overlapping caches, any valid match works."""
        cache = PriceCache(redis, "test:price")

        # Cache full month (Jan 1-31)
        month_start = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
        month_end = datetime(2026, 1, 31, 23, 59, 59, tzinfo=UTC)
        await cache.set_history(Ticker("AAPL"), month_start, month_end, month_history)

        # Cache two weeks (Jan 15-31) - overlaps with month
        two_weeks = [p for p in month_history if p.timestamp.date().day >= 15]
        two_weeks_start = datetime(2026, 1, 15, 0, 0, 0, tzinfo=UTC)
        two_weeks_end = datetime(2026, 1, 31, 23, 59, 59, tzinfo=UTC)
        await cache.set_history(
            Ticker("AAPL"), two_weeks_start, two_weeks_end, two_weeks
        )

        # Request one week (Jan 25-31) - subset of both
        week_start = datetime(2026, 1, 25, 0, 0, 0, tzinfo=UTC)
        week_end = datetime(2026, 1, 31, 23, 59, 59, tzinfo=UTC)

        result = await cache.get_history(Ticker("AAPL"), week_start, week_end)

        # Should find one of the broader ranges and filter it
        assert result is not None
        assert len(result) == 7  # 7 days
        assert result[0].timestamp.date().day == 25
        assert result[-1].timestamp.date().day == 31

    async def test_different_intervals_isolated(
        self,
        redis: fakeredis.FakeRedis,  # type: ignore[type-arg]
        month_history: list[PricePoint],
    ) -> None:
        """Test that different intervals don't match in subset search."""
        cache = PriceCache(redis, "test:price")

        # Cache month with 1day interval
        month_start = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
        month_end = datetime(2026, 1, 31, 23, 59, 59, tzinfo=UTC)
        await cache.set_history(
            Ticker("AAPL"), month_start, month_end, month_history, interval="1day"
        )

        # Request week with 1hour interval
        week_start = datetime(2026, 1, 25, 0, 0, 0, tzinfo=UTC)
        week_end = datetime(2026, 1, 31, 23, 59, 59, tzinfo=UTC)

        result = await cache.get_history(
            Ticker("AAPL"), week_start, week_end, interval="1hour"
        )

        # Should NOT find the 1day cache (different interval)
        assert result is None

    async def test_different_tickers_isolated(
        self,
        redis: fakeredis.FakeRedis,  # type: ignore[type-arg]
        month_history: list[PricePoint],
    ) -> None:
        """Test that different tickers don't match in subset search."""
        cache = PriceCache(redis, "test:price")

        # Cache AAPL month
        month_start = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
        month_end = datetime(2026, 1, 31, 23, 59, 59, tzinfo=UTC)
        await cache.set_history(Ticker("AAPL"), month_start, month_end, month_history)

        # Request TSLA week
        week_start = datetime(2026, 1, 25, 0, 0, 0, tzinfo=UTC)
        week_end = datetime(2026, 1, 31, 23, 59, 59, tzinfo=UTC)

        result = await cache.get_history(Ticker("TSLA"), week_start, week_end)

        # Should NOT find AAPL cache (different ticker)
        assert result is None

    async def test_empty_filtered_result_continues_search(
        self,
        redis: fakeredis.FakeRedis,  # type: ignore[type-arg]
    ) -> None:
        """Test that empty filtered results trigger continued search."""
        cache = PriceCache(redis, "test:price")

        # Cache month but with NO data (edge case)
        month_start = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
        month_end = datetime(2026, 1, 31, 23, 59, 59, tzinfo=UTC)
        await cache.set_history(Ticker("AAPL"), month_start, month_end, [])

        # Request week
        week_start = datetime(2026, 1, 25, 0, 0, 0, tzinfo=UTC)
        week_end = datetime(2026, 1, 31, 23, 59, 59, tzinfo=UTC)

        result = await cache.get_history(Ticker("AAPL"), week_start, week_end)

        # Should return None (empty data doesn't help)
        assert result is None

    async def test_parse_dates_from_key_valid(
        self,
        redis: fakeredis.FakeRedis,  # type: ignore[type-arg]
    ) -> None:
        """Test parsing dates from valid cache keys."""
        cache = PriceCache(redis, "test:price")

        key = "test:price:AAPL:history:2026-01-01:2026-01-31:1day"
        result = cache._parse_dates_from_key(key)

        assert result is not None
        start, end = result
        assert start.date() == datetime(2026, 1, 1).date()
        assert end.date() == datetime(2026, 1, 31).date()

    async def test_parse_dates_from_key_invalid(
        self,
        redis: fakeredis.FakeRedis,  # type: ignore[type-arg]
    ) -> None:
        """Test parsing dates from malformed keys returns None."""
        cache = PriceCache(redis, "test:price")

        # Malformed keys
        assert cache._parse_dates_from_key("invalid:key") is None
        assert cache._parse_dates_from_key("test:price:AAPL") is None
        assert cache._parse_dates_from_key("test:price:AAPL:invalid:format") is None

    async def test_is_range_subset_true(
        self,
        redis: fakeredis.FakeRedis,  # type: ignore[type-arg]
    ) -> None:
        """Test subset detection returns True for valid subsets."""
        cache = PriceCache(redis, "test:price")

        # Requested range is subset of cached range
        assert (
            cache._is_range_subset(
                datetime(2026, 1, 25, tzinfo=UTC),
                datetime(2026, 1, 31, tzinfo=UTC),
                datetime(2026, 1, 1, tzinfo=UTC),
                datetime(2026, 1, 31, tzinfo=UTC),
            )
            is True
        )

    async def test_is_range_subset_false(
        self,
        redis: fakeredis.FakeRedis,  # type: ignore[type-arg]
    ) -> None:
        """Test subset detection returns False for non-subsets."""
        cache = PriceCache(redis, "test:price")

        # Requested range extends beyond cached range
        assert (
            cache._is_range_subset(
                datetime(2026, 1, 25, tzinfo=UTC),
                datetime(2026, 2, 5, tzinfo=UTC),  # Extends into Feb
                datetime(2026, 1, 1, tzinfo=UTC),
                datetime(2026, 1, 31, tzinfo=UTC),
            )
            is False
        )

    async def test_filter_to_range(
        self,
        redis: fakeredis.FakeRedis,  # type: ignore[type-arg]
        month_history: list[PricePoint],
    ) -> None:
        """Test filtering price points to specific range."""
        cache = PriceCache(redis, "test:price")

        # Filter month to last week
        week_start = datetime(2026, 1, 25, 0, 0, 0, tzinfo=UTC)
        week_end = datetime(2026, 1, 31, 23, 59, 59, tzinfo=UTC)

        result = cache._filter_to_range(month_history, week_start, week_end)

        assert len(result) == 7
        assert all(week_start <= p.timestamp <= week_end for p in result)
        assert result[0].timestamp.date().day == 25
        assert result[-1].timestamp.date().day == 31
