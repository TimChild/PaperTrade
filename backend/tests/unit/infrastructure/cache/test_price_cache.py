"""Tests for PriceCache with Redis backend."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from fakeredis import aioredis as fakeredis

from papertrade.application.dtos.price_point import PricePoint
from papertrade.domain.value_objects.money import Money
from papertrade.domain.value_objects.ticker import Ticker
from papertrade.infrastructure.cache.price_cache import PriceCache


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
        cache = PriceCache(redis, "papertrade:price")

        key = cache._get_key(Ticker("AAPL"))

        assert key == "papertrade:price:AAPL"

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
