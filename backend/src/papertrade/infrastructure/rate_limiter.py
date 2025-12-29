"""Rate limiter using token bucket algorithm with Redis backend.

This module implements rate limiting for external API calls to prevent quota exhaustion.
Uses a token bucket algorithm with dual time windows (minute and day) to enforce
Alpha Vantage API rate limits.

The implementation is Redis-backed for distributed rate limiting across multiple instances.
Uses Lua scripts for atomic check-and-consume operations to prevent race conditions.
"""

from datetime import datetime, timezone
from typing import Protocol

from redis.asyncio import Redis


class RedisClient(Protocol):
    """Protocol for Redis client interface.
    
    This allows using either real Redis or fakeredis for testing.
    """

    async def eval(
        self,
        script: str,
        num_keys: int,
        *keys_and_args: str | bytes | int | float,
    ) -> int:
        """Execute Lua script atomically."""
        ...

    async def get(self, key: str) -> bytes | None:
        """Get value from Redis."""
        ...

    async def ttl(self, key: str) -> int:
        """Get TTL for key in seconds."""
        ...


class RateLimiter:
    """Token bucket rate limiter with dual time windows.
    
    Enforces rate limits for external API calls using a token bucket algorithm.
    Supports two time windows (minute and day) to match Alpha Vantage quotas.
    
    The limiter maintains two independent token buckets:
    - Minute bucket: Refills every 60 seconds
    - Day bucket: Refills every 86400 seconds (24 hours)
    
    Both buckets must have tokens available for a request to proceed.
    
    Attributes:
        redis: Redis client for token storage
        key_prefix: Prefix for Redis keys (e.g., "papertrade:ratelimit")
        calls_per_minute: Maximum calls allowed per minute
        calls_per_day: Maximum calls allowed per day
    
    Example:
        >>> limiter = RateLimiter(redis, "api:limit", 5, 500)
        >>> if await limiter.can_make_request():
        ...     await limiter.consume_token()
        ...     # Make API call
        >>> else:
        ...     wait_time = await limiter.wait_time()
        ...     # Wait before retry
    """

    # Lua script for atomic token check and consumption
    # Returns: 1 if tokens consumed, 0 if insufficient tokens
    _CONSUME_SCRIPT = """
    local minute_key = KEYS[1]
    local day_key = KEYS[2]
    local minute_limit = tonumber(ARGV[1])
    local day_limit = tonumber(ARGV[2])
    local minute_window = tonumber(ARGV[3])
    local day_window = tonumber(ARGV[4])
    
    -- Get current token counts (default to limit if not set)
    local minute_tokens = tonumber(redis.call('GET', minute_key))
    if not minute_tokens then
        minute_tokens = minute_limit
    end
    
    local day_tokens = tonumber(redis.call('GET', day_key))
    if not day_tokens then
        day_tokens = day_limit
    end
    
    -- Check if we have tokens in both buckets
    if minute_tokens > 0 and day_tokens > 0 then
        -- Consume tokens
        minute_tokens = minute_tokens - 1
        day_tokens = day_tokens - 1
        
        -- Update Redis with new counts
        redis.call('SET', minute_key, minute_tokens, 'EX', minute_window)
        redis.call('SET', day_key, day_tokens, 'EX', day_window)
        
        return 1
    else
        return 0
    end
    """

    def __init__(
        self,
        redis: Redis | RedisClient,  # type: ignore[type-arg]
        key_prefix: str,
        calls_per_minute: int,
        calls_per_day: int,
    ) -> None:
        """Initialize rate limiter.
        
        Args:
            redis: Redis client (real or fake)
            key_prefix: Prefix for Redis keys (e.g., "papertrade:ratelimit")
            calls_per_minute: Maximum calls allowed per minute
            calls_per_day: Maximum calls allowed per day
            
        Raises:
            ValueError: If limits are not positive integers
        """
        if calls_per_minute <= 0:
            raise ValueError("calls_per_minute must be positive")
        if calls_per_day <= 0:
            raise ValueError("calls_per_day must be positive")
        
        self.redis = redis
        self.key_prefix = key_prefix
        self.calls_per_minute = calls_per_minute
        self.calls_per_day = calls_per_day
        
        # Time windows in seconds
        self._minute_window = 60
        self._day_window = 86400  # 24 hours

    def _get_minute_key(self) -> str:
        """Get Redis key for minute bucket."""
        return f"{self.key_prefix}:minute"

    def _get_day_key(self) -> str:
        """Get Redis key for day bucket."""
        return f"{self.key_prefix}:day"

    async def can_make_request(self) -> bool:
        """Check if a request can be made without consuming tokens.
        
        This is a read-only check that doesn't modify token counts.
        Use consume_token() to actually consume a token.
        
        Returns:
            True if both minute and day buckets have tokens available
            
        Example:
            >>> if await limiter.can_make_request():
            ...     await limiter.consume_token()
            ...     # Make API call
        """
        minute_key = self._get_minute_key()
        day_key = self._get_day_key()
        
        # Get current token counts
        minute_tokens_bytes = await self.redis.get(minute_key)
        minute_tokens = (
            int(minute_tokens_bytes) if minute_tokens_bytes else self.calls_per_minute
        )
        
        day_tokens_bytes = await self.redis.get(day_key)
        day_tokens = (
            int(day_tokens_bytes) if day_tokens_bytes else self.calls_per_day
        )
        
        return minute_tokens > 0 and day_tokens > 0

    async def consume_token(self) -> bool:
        """Atomically check and consume a token if available.
        
        This method atomically checks both buckets and consumes a token from each
        if both have tokens available. If either bucket is empty, no tokens are consumed.
        
        Returns:
            True if token was consumed, False if insufficient tokens
            
        Example:
            >>> if await limiter.consume_token():
            ...     # Token consumed, proceed with API call
            ... else:
            ...     # Rate limited, wait before retry
            ...     wait_time = await limiter.wait_time()
        """
        minute_key = self._get_minute_key()
        day_key = self._get_day_key()
        
        result = await self.redis.eval(
            self._CONSUME_SCRIPT,
            2,  # Number of keys
            minute_key,
            day_key,
            str(self.calls_per_minute),
            str(self.calls_per_day),
            str(self._minute_window),
            str(self._day_window),
        )
        
        return bool(result)

    async def wait_time(self) -> float:
        """Calculate seconds until next token will be available.
        
        Returns the minimum wait time before a token will be available in either bucket.
        If tokens are currently available, returns 0.0.
        
        Returns:
            Seconds to wait (0.0 if tokens available now)
            
        Example:
            >>> wait = await limiter.wait_time()
            >>> if wait > 0:
            ...     print(f"Rate limited. Retry in {wait:.1f} seconds")
            ...     await asyncio.sleep(wait)
        """
        minute_key = self._get_minute_key()
        day_key = self._get_day_key()
        
        # Get current token counts
        minute_tokens_bytes = await self.redis.get(minute_key)
        minute_tokens = (
            int(minute_tokens_bytes) if minute_tokens_bytes else self.calls_per_minute
        )
        
        day_tokens_bytes = await self.redis.get(day_key)
        day_tokens = (
            int(day_tokens_bytes) if day_tokens_bytes else self.calls_per_day
        )
        
        # If both have tokens, no wait needed
        if minute_tokens > 0 and day_tokens > 0:
            return 0.0
        
        # Get TTLs to determine when tokens will refill
        wait_times: list[float] = []
        
        if minute_tokens <= 0:
            minute_ttl = await self.redis.ttl(minute_key)
            if minute_ttl > 0:
                wait_times.append(float(minute_ttl))
            else:
                # Key expired or doesn't exist, tokens available immediately
                wait_times.append(0.0)
        
        if day_tokens <= 0:
            day_ttl = await self.redis.ttl(day_key)
            if day_ttl > 0:
                wait_times.append(float(day_ttl))
            else:
                # Key expired or doesn't exist, tokens available immediately
                wait_times.append(0.0)
        
        # Return minimum wait time (when first bucket refills)
        return min(wait_times) if wait_times else 0.0

    async def get_remaining_tokens(self) -> dict[str, int]:
        """Get remaining token counts for monitoring.
        
        Returns current token counts for both time windows.
        Useful for monitoring, logging, and displaying quota status to users.
        
        Returns:
            Dict with "minute" and "day" token counts
            
        Example:
            >>> tokens = await limiter.get_remaining_tokens()
            >>> print(f"Tokens left: {tokens['minute']}/min, {tokens['day']}/day")
        """
        minute_key = self._get_minute_key()
        day_key = self._get_day_key()
        
        minute_tokens_bytes = await self.redis.get(minute_key)
        minute_tokens = (
            int(minute_tokens_bytes) if minute_tokens_bytes else self.calls_per_minute
        )
        
        day_tokens_bytes = await self.redis.get(day_key)
        day_tokens = (
            int(day_tokens_bytes) if day_tokens_bytes else self.calls_per_day
        )
        
        return {
            "minute": minute_tokens,
            "day": day_tokens,
        }
