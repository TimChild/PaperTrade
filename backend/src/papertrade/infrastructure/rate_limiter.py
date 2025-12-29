"""Rate limiter implementation using token bucket algorithm with Redis backend.

This module implements a dual time-window rate limiter to respect Alpha Vantage's
API quotas (5 calls/min, 500 calls/day). The token bucket algorithm is backed by
Redis for distributed systems and persistence across application restarts.
"""

from datetime import datetime, timezone
from typing import Protocol

import redis.asyncio as redis


class RedisClient(Protocol):
    """Protocol for Redis client interface.
    
    This allows us to use both real Redis and fakeredis for testing.
    """

    async def get(self, key: str) -> bytes | None:
        """Get value for key."""
        ...

    async def set(
        self, key: str, value: int | str | bytes, ex: int | None = None
    ) -> bool:
        """Set key to value with optional expiration in seconds."""
        ...

    async def decr(self, key: str) -> int:
        """Decrement integer value at key."""
        ...

    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration on key."""
        ...

    async def eval(
        self,
        script: str,
        numkeys: int,
        *keys_and_args: str | int,
    ) -> int:
        """Execute Lua script."""
        ...


class RateLimiter:
    """Token bucket rate limiter with dual time windows.
    
    Enforces both per-minute and per-day API call limits using Redis-backed
    token buckets. Uses Lua scripts for atomic check-and-consume operations.
    
    Attributes:
        redis_client: Redis client for token storage
        calls_per_minute: Maximum calls allowed per minute
        calls_per_day: Maximum calls allowed per day
        key_prefix: Redis key prefix for namespacing
    """

    # Lua script for atomic check-and-consume operation
    _LUA_CONSUME_SCRIPT = """
    local minute_key = KEYS[1]
    local day_key = KEYS[2]
    local minute_cap = tonumber(ARGV[1])
    local day_cap = tonumber(ARGV[2])
    local minute_ttl = tonumber(ARGV[3])
    local day_ttl = tonumber(ARGV[4])
    
    -- Get current token counts (initialize to capacity if not set)
    local minute_tokens = tonumber(redis.call('GET', minute_key))
    if not minute_tokens then
        minute_tokens = minute_cap
        redis.call('SET', minute_key, minute_tokens, 'EX', minute_ttl)
    end
    
    local day_tokens = tonumber(redis.call('GET', day_key))
    if not day_tokens then
        day_tokens = day_cap
        redis.call('SET', day_key, day_tokens, 'EX', day_ttl)
    end
    
    -- Check if both buckets have tokens
    if minute_tokens > 0 and day_tokens > 0 then
        -- Consume from both buckets
        redis.call('DECR', minute_key)
        redis.call('DECR', day_key)
        -- Reset TTL to ensure they don't expire prematurely
        redis.call('EXPIRE', minute_key, minute_ttl)
        redis.call('EXPIRE', day_key, day_ttl)
        return 1  -- Success
    else
        return 0  -- Rate limited
    end
    """

    def __init__(
        self,
        redis_client: RedisClient,
        calls_per_minute: int = 5,
        calls_per_day: int = 500,
        key_prefix: str = "papertrade:ratelimit",
    ) -> None:
        """Initialize rate limiter.
        
        Args:
            redis_client: Redis client for token storage
            calls_per_minute: Maximum calls allowed per minute (default: 5)
            calls_per_day: Maximum calls allowed per day (default: 500)
            key_prefix: Redis key prefix for namespacing (default: "papertrade:ratelimit")
        """
        self.redis_client = redis_client
        self.calls_per_minute = calls_per_minute
        self.calls_per_day = calls_per_day
        self.key_prefix = key_prefix

    def _get_minute_key(self, now: datetime) -> str:
        """Generate Redis key for current minute bucket.
        
        Args:
            now: Current time (must be UTC)
            
        Returns:
            Redis key like "papertrade:ratelimit:minute:2025-12-29-03-45"
        """
        minute_str = now.strftime("%Y-%m-%d-%H-%M")
        return f"{self.key_prefix}:minute:{minute_str}"

    def _get_day_key(self, now: datetime) -> str:
        """Generate Redis key for current day bucket.
        
        Args:
            now: Current time (must be UTC)
            
        Returns:
            Redis key like "papertrade:ratelimit:day:2025-12-29"
        """
        day_str = now.strftime("%Y-%m-%d")
        return f"{self.key_prefix}:day:{day_str}"

    async def can_make_request(self) -> bool:
        """Check if tokens are available in both buckets.
        
        This method checks (but does not consume) tokens. Use consume_token()
        for atomic check-and-consume.
        
        Returns:
            True if both minute and day buckets have tokens available
        """
        now = datetime.now(timezone.utc)
        minute_key = self._get_minute_key(now)
        day_key = self._get_day_key(now)

        # Get current token counts
        minute_tokens_bytes = await self.redis_client.get(minute_key)
        minute_tokens = (
            int(minute_tokens_bytes)
            if minute_tokens_bytes
            else self.calls_per_minute
        )

        day_tokens_bytes = await self.redis_client.get(day_key)
        day_tokens = (
            int(day_tokens_bytes) if day_tokens_bytes else self.calls_per_day
        )

        return minute_tokens > 0 and day_tokens > 0

    async def consume_token(self) -> bool:
        """Atomically check and consume a token from both buckets.
        
        This method uses a Lua script to atomically check both buckets and
        consume tokens if available. This prevents race conditions.
        
        Returns:
            True if token was consumed successfully, False if rate limited
        """
        now = datetime.now(timezone.utc)
        minute_key = self._get_minute_key(now)
        day_key = self._get_day_key(now)

        # TTL: minute keys expire after 2 minutes, day keys after 2 days
        minute_ttl = 120  # 2 minutes (buffer for clock skew)
        day_ttl = 172800  # 2 days (48 hours)

        # Execute Lua script atomically
        result = await self.redis_client.eval(
            self._LUA_CONSUME_SCRIPT,
            2,  # Number of keys
            minute_key,
            day_key,
            str(self.calls_per_minute),
            str(self.calls_per_day),
            str(minute_ttl),
            str(day_ttl),
        )

        return result == 1

    async def wait_time(self) -> int:
        """Calculate seconds until next token is available.
        
        Returns the minimum wait time across both buckets.
        
        Returns:
            Seconds until next token available (0 if tokens currently available)
        """
        now = datetime.now(timezone.utc)

        # Check if tokens currently available
        if await self.can_make_request():
            return 0

        # Calculate time until next minute boundary
        seconds_until_next_minute = 60 - now.second

        # Calculate time until next day boundary (midnight UTC)
        seconds_until_midnight = (
            (24 - now.hour) * 3600 - now.minute * 60 - now.second
        )

        # Get current token counts to determine which bucket is limiting
        minute_key = self._get_minute_key(now)
        day_key = self._get_day_key(now)

        minute_tokens_bytes = await self.redis_client.get(minute_key)
        minute_tokens = (
            int(minute_tokens_bytes)
            if minute_tokens_bytes
            else self.calls_per_minute
        )

        day_tokens_bytes = await self.redis_client.get(day_key)
        day_tokens = (
            int(day_tokens_bytes) if day_tokens_bytes else self.calls_per_day
        )

        # If minute bucket empty, wait until next minute
        if minute_tokens <= 0:
            return seconds_until_next_minute

        # If day bucket empty, wait until midnight
        if day_tokens <= 0:
            return seconds_until_midnight

        # Both buckets should have tokens (shouldn't reach here)
        return 0

    async def get_remaining_tokens(self) -> dict[str, int]:
        """Get remaining tokens in both buckets for monitoring.
        
        Returns:
            Dictionary with keys 'minute' and 'day' containing token counts
        """
        now = datetime.now(timezone.utc)
        minute_key = self._get_minute_key(now)
        day_key = self._get_day_key(now)

        minute_tokens_bytes = await self.redis_client.get(minute_key)
        minute_tokens = (
            int(minute_tokens_bytes)
            if minute_tokens_bytes
            else self.calls_per_minute
        )

        day_tokens_bytes = await self.redis_client.get(day_key)
        day_tokens = (
            int(day_tokens_bytes) if day_tokens_bytes else self.calls_per_day
        )

        return {"minute": minute_tokens, "day": day_tokens}


async def create_rate_limiter(
    redis_url: str = "redis://localhost:6379",
    calls_per_minute: int = 5,
    calls_per_day: int = 500,
    key_prefix: str = "papertrade:ratelimit",
) -> RateLimiter:
    """Factory function to create a RateLimiter with Redis connection.
    
    Args:
        redis_url: Redis connection URL
        calls_per_minute: Maximum calls per minute
        calls_per_day: Maximum calls per day
        key_prefix: Redis key prefix
        
    Returns:
        Configured RateLimiter instance
    """
    redis_client = redis.from_url(redis_url, decode_responses=False)
    return RateLimiter(
        redis_client=redis_client,
        calls_per_minute=calls_per_minute,
        calls_per_day=calls_per_day,
        key_prefix=key_prefix,
    )
