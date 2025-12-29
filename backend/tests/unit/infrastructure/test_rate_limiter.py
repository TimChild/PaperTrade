"""Tests for RateLimiter with token bucket algorithm."""

import pytest
from fakeredis import aioredis as fakeredis

from papertrade.infrastructure.rate_limiter import RateLimiter


class TestRateLimiterInitialization:
    """Tests for RateLimiter initialization and validation."""

    async def test_valid_initialization(self) -> None:
        """Test creating rate limiter with valid parameters."""
        redis = await fakeredis.FakeRedis()
        limiter = RateLimiter(redis, "test:limit", 5, 500)
        
        assert limiter.calls_per_minute == 5
        assert limiter.calls_per_day == 500
        assert limiter.key_prefix == "test:limit"

    async def test_invalid_calls_per_minute(self) -> None:
        """Test that zero or negative calls_per_minute raises ValueError."""
        redis = await fakeredis.FakeRedis()
        
        with pytest.raises(ValueError, match="calls_per_minute must be positive"):
            RateLimiter(redis, "test:limit", 0, 500)
        
        with pytest.raises(ValueError, match="calls_per_minute must be positive"):
            RateLimiter(redis, "test:limit", -1, 500)

    async def test_invalid_calls_per_day(self) -> None:
        """Test that zero or negative calls_per_day raises ValueError."""
        redis = await fakeredis.FakeRedis()
        
        with pytest.raises(ValueError, match="calls_per_day must be positive"):
            RateLimiter(redis, "test:limit", 5, 0)
        
        with pytest.raises(ValueError, match="calls_per_day must be positive"):
            RateLimiter(redis, "test:limit", 5, -1)


class TestRateLimiterTokenConsumption:
    """Tests for token consumption and availability checking."""

    async def test_can_make_request_initially(self) -> None:
        """Test that requests are allowed initially (full buckets)."""
        redis = await fakeredis.FakeRedis()
        limiter = RateLimiter(redis, "test:limit", 5, 500)
        
        assert await limiter.can_make_request() is True

    async def test_consume_token_success(self) -> None:
        """Test successfully consuming a token."""
        redis = await fakeredis.FakeRedis()
        limiter = RateLimiter(redis, "test:limit", 5, 500)
        
        result = await limiter.consume_token()
        
        assert result is True

    async def test_consume_multiple_tokens(self) -> None:
        """Test consuming multiple tokens within limits."""
        redis = await fakeredis.FakeRedis()
        limiter = RateLimiter(redis, "test:limit", 5, 500)
        
        # Consume 3 tokens
        for _ in range(3):
            result = await limiter.consume_token()
            assert result is True
        
        # Should still have tokens available
        assert await limiter.can_make_request() is True

    async def test_exhaust_minute_bucket(self) -> None:
        """Test exhausting the minute bucket."""
        redis = await fakeredis.FakeRedis()
        limiter = RateLimiter(redis, "test:limit", 3, 500)
        
        # Consume all 3 minute tokens
        for _ in range(3):
            result = await limiter.consume_token()
            assert result is True
        
        # Next request should fail (minute bucket empty)
        assert await limiter.can_make_request() is False
        assert await limiter.consume_token() is False

    async def test_exhaust_day_bucket(self) -> None:
        """Test exhausting the day bucket."""
        redis = await fakeredis.FakeRedis()
        limiter = RateLimiter(redis, "test:limit", 500, 3)
        
        # Consume all 3 day tokens
        for _ in range(3):
            result = await limiter.consume_token()
            assert result is True
        
        # Next request should fail (day bucket empty)
        assert await limiter.can_make_request() is False
        assert await limiter.consume_token() is False


class TestRateLimiterRemainingTokens:
    """Tests for querying remaining token counts."""

    async def test_get_remaining_tokens_initially(self) -> None:
        """Test getting remaining tokens when buckets are full."""
        redis = await fakeredis.FakeRedis()
        limiter = RateLimiter(redis, "test:limit", 5, 500)
        
        tokens = await limiter.get_remaining_tokens()
        
        assert tokens["minute"] == 5
        assert tokens["day"] == 500

    async def test_get_remaining_tokens_after_consumption(self) -> None:
        """Test getting remaining tokens after consuming some."""
        redis = await fakeredis.FakeRedis()
        limiter = RateLimiter(redis, "test:limit", 5, 500)
        
        # Consume 2 tokens
        await limiter.consume_token()
        await limiter.consume_token()
        
        tokens = await limiter.get_remaining_tokens()
        
        assert tokens["minute"] == 3
        assert tokens["day"] == 498

    async def test_get_remaining_tokens_exhausted(self) -> None:
        """Test getting remaining tokens when bucket is exhausted."""
        redis = await fakeredis.FakeRedis()
        limiter = RateLimiter(redis, "test:limit", 2, 500)
        
        # Exhaust minute bucket
        await limiter.consume_token()
        await limiter.consume_token()
        
        tokens = await limiter.get_remaining_tokens()
        
        assert tokens["minute"] == 0
        assert tokens["day"] == 498


class TestRateLimiterWaitTime:
    """Tests for wait time calculation."""

    async def test_wait_time_when_tokens_available(self) -> None:
        """Test wait time is zero when tokens are available."""
        redis = await fakeredis.FakeRedis()
        limiter = RateLimiter(redis, "test:limit", 5, 500)
        
        wait = await limiter.wait_time()
        
        assert wait == 0.0

    async def test_wait_time_after_exhaustion(self) -> None:
        """Test wait time is positive after exhausting bucket."""
        redis = await fakeredis.FakeRedis()
        limiter = RateLimiter(redis, "test:limit", 2, 500)
        
        # Exhaust minute bucket
        await limiter.consume_token()
        await limiter.consume_token()
        
        wait = await limiter.wait_time()
        
        # Should be close to 60 seconds (minute window)
        assert 59.0 <= wait <= 61.0

    async def test_wait_time_after_partial_consumption(self) -> None:
        """Test wait time when some tokens consumed but not exhausted."""
        redis = await fakeredis.FakeRedis()
        limiter = RateLimiter(redis, "test:limit", 5, 500)
        
        # Consume some but not all tokens
        await limiter.consume_token()
        await limiter.consume_token()
        
        wait = await limiter.wait_time()
        
        # Should still be zero (tokens available)
        assert wait == 0.0


class TestRateLimiterAtomicity:
    """Tests for atomic operations (concurrent safety)."""

    async def test_consume_token_is_atomic(self) -> None:
        """Test that consume_token is atomic (no race conditions).
        
        This test simulates concurrent requests by calling consume_token multiple times
        and verifying that exactly the expected number succeed.
        """
        redis = await fakeredis.FakeRedis()
        limiter = RateLimiter(redis, "test:limit", 3, 500)
        
        # Try to consume 5 tokens (but only 3 available)
        results = []
        for _ in range(5):
            result = await limiter.consume_token()
            results.append(result)
        
        # Exactly 3 should succeed, 2 should fail
        successful = sum(1 for r in results if r)
        failed = sum(1 for r in results if not r)
        
        assert successful == 3
        assert failed == 2
        
        # Remaining tokens should be 0
        tokens = await limiter.get_remaining_tokens()
        assert tokens["minute"] == 0


class TestRateLimiterKeyIsolation:
    """Tests for key isolation (different prefixes don't interfere)."""

    async def test_different_key_prefixes_isolated(self) -> None:
        """Test that limiters with different prefixes are isolated."""
        redis = await fakeredis.FakeRedis()
        
        limiter1 = RateLimiter(redis, "api1:limit", 3, 500)
        limiter2 = RateLimiter(redis, "api2:limit", 3, 500)
        
        # Exhaust limiter1
        for _ in range(3):
            await limiter1.consume_token()
        
        # limiter1 should be exhausted
        assert await limiter1.can_make_request() is False
        
        # limiter2 should still have tokens
        assert await limiter2.can_make_request() is True
        
        # Verify token counts
        tokens1 = await limiter1.get_remaining_tokens()
        tokens2 = await limiter2.get_remaining_tokens()
        
        assert tokens1["minute"] == 0
        assert tokens2["minute"] == 3
