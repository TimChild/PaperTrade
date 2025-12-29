"""Redis-backed price cache for PricePoint objects.

This module provides a simple Redis wrapper for caching PricePoint objects
with configurable TTL. Uses JSON serialization for human-readable storage.
"""

import json
from typing import Protocol

from papertrade.application.dtos.price_point import PricePoint
from papertrade.domain.value_objects.ticker import Ticker


class RedisClient(Protocol):
    """Protocol for Redis client interface.
    
    This allows us to use both real Redis and fakeredis for testing.
    """

    async def get(self, key: str) -> bytes | None:
        """Get value for key."""
        ...

    async def set(
        self, key: str, value: str | bytes, ex: int | None = None
    ) -> bool:
        """Set key to value with optional expiration in seconds."""
        ...

    async def delete(self, key: str) -> int:
        """Delete key."""
        ...

    async def exists(self, key: str) -> int:
        """Check if key exists."""
        ...

    async def ttl(self, key: str) -> int:
        """Get TTL of key in seconds."""
        ...


class PriceCache:
    """Redis-backed cache for PricePoint objects.
    
    Provides simple CRUD operations for caching stock prices with TTL support.
    Uses JSON serialization for human-readable and debuggable storage.
    
    Attributes:
        redis_client: Redis client for storage
        default_ttl: Default TTL in seconds (default: 3600 = 1 hour)
        key_prefix: Redis key prefix for namespacing
    """

    def __init__(
        self,
        redis_client: RedisClient,
        default_ttl: int = 3600,
        key_prefix: str = "papertrade:price",
    ) -> None:
        """Initialize price cache.
        
        Args:
            redis_client: Redis client for storage
            default_ttl: Default TTL in seconds (default: 3600 = 1 hour)
            key_prefix: Redis key prefix (default: "papertrade:price")
        """
        self.redis_client = redis_client
        self.default_ttl = default_ttl
        self.key_prefix = key_prefix

    def _make_key(self, ticker: Ticker) -> str:
        """Generate Redis key for ticker.
        
        Args:
            ticker: Stock ticker
            
        Returns:
            Redis key like "papertrade:price:AAPL"
        """
        return f"{self.key_prefix}:{ticker.symbol}"

    async def get(self, ticker: Ticker) -> PricePoint | None:
        """Get cached price for ticker.
        
        Args:
            ticker: Stock ticker to get price for
            
        Returns:
            PricePoint if cached and not expired, None otherwise
        """
        key = self._make_key(ticker)
        value_bytes = await self.redis_client.get(key)

        if value_bytes is None:
            return None

        # Deserialize JSON to PricePoint
        try:
            value_str = value_bytes.decode("utf-8")
            data = json.loads(value_str)
            return self._deserialize_price_point(data)
        except (json.JSONDecodeError, ValueError, KeyError):
            # Invalid data in cache, ignore
            return None

    async def set(
        self, price: PricePoint, ttl: int | None = None
    ) -> None:
        """Set cached price for ticker.
        
        Args:
            price: PricePoint to cache
            ttl: TTL in seconds (uses default_ttl if None)
        """
        key = self._make_key(price.ticker)
        ttl_seconds = ttl if ttl is not None else self.default_ttl

        # Serialize PricePoint to JSON
        data = self._serialize_price_point(price)
        value_str = json.dumps(data)

        await self.redis_client.set(key, value_str, ex=ttl_seconds)

    async def delete(self, ticker: Ticker) -> None:
        """Delete cached price for ticker.
        
        Args:
            ticker: Stock ticker to delete from cache
        """
        key = self._make_key(ticker)
        await self.redis_client.delete(key)

    async def exists(self, ticker: Ticker) -> bool:
        """Check if ticker has cached price.
        
        Args:
            ticker: Stock ticker to check
            
        Returns:
            True if ticker has cached price (even if expired)
        """
        key = self._make_key(ticker)
        result = await self.redis_client.exists(key)
        return result > 0

    async def get_ttl(self, ticker: Ticker) -> int:
        """Get remaining TTL for cached price.
        
        Args:
            ticker: Stock ticker to check
            
        Returns:
            Remaining TTL in seconds, -2 if key doesn't exist, -1 if no TTL
        """
        key = self._make_key(ticker)
        return await self.redis_client.ttl(key)

    def _serialize_price_point(self, price: PricePoint) -> dict[str, object]:
        """Convert PricePoint to JSON-serializable dict.
        
        Args:
            price: PricePoint to serialize
            
        Returns:
            Dictionary suitable for JSON serialization
        """
        return {
            "ticker": price.ticker.symbol,
            "price": {
                "amount": str(price.price.amount),
                "currency": price.price.currency,
            },
            "timestamp": price.timestamp.isoformat(),
            "source": price.source,
            "interval": price.interval,
            "open": (
                {
                    "amount": str(price.open.amount),
                    "currency": price.open.currency,
                }
                if price.open
                else None
            ),
            "high": (
                {
                    "amount": str(price.high.amount),
                    "currency": price.high.currency,
                }
                if price.high
                else None
            ),
            "low": (
                {
                    "amount": str(price.low.amount),
                    "currency": price.low.currency,
                }
                if price.low
                else None
            ),
            "close": (
                {
                    "amount": str(price.close.amount),
                    "currency": price.close.currency,
                }
                if price.close
                else None
            ),
            "volume": price.volume,
        }

    def _deserialize_price_point(self, data: dict[str, object]) -> PricePoint:
        """Convert JSON dict to PricePoint.
        
        Args:
            data: Dictionary from JSON deserialization
            
        Returns:
            PricePoint object
            
        Raises:
            ValueError: If data is invalid
            KeyError: If required fields missing
        """
        from datetime import datetime
        from decimal import Decimal

        from papertrade.domain.value_objects.money import Money

        # Parse required fields
        ticker = Ticker.create(str(data["ticker"]))
        price_dict = data["price"]  # type: ignore[assignment]
        price = Money(
            amount=Decimal(price_dict["amount"]),  # type: ignore[index]
            currency=str(price_dict["currency"]),  # type: ignore[index]
        )
        timestamp = datetime.fromisoformat(str(data["timestamp"]))
        source = str(data["source"])
        interval = str(data["interval"])

        # Parse optional OHLCV fields
        open_data = data.get("open")
        open_price = (
            Money(
                amount=Decimal(open_data["amount"]),  # type: ignore[index]
                currency=str(open_data["currency"]),  # type: ignore[index]
            )
            if open_data
            else None
        )

        high_data = data.get("high")
        high_price = (
            Money(
                amount=Decimal(high_data["amount"]),  # type: ignore[index]
                currency=str(high_data["currency"]),  # type: ignore[index]
            )
            if high_data
            else None
        )

        low_data = data.get("low")
        low_price = (
            Money(
                amount=Decimal(low_data["amount"]),  # type: ignore[index]
                currency=str(low_data["currency"]),  # type: ignore[index]
            )
            if low_data
            else None
        )

        close_data = data.get("close")
        close_price = (
            Money(
                amount=Decimal(close_data["amount"]),  # type: ignore[index]
                currency=str(close_data["currency"]),  # type: ignore[index]
            )
            if close_data
            else None
        )

        volume = int(data["volume"]) if data.get("volume") is not None else None

        return PricePoint(
            ticker=ticker,
            price=price,
            timestamp=timestamp,
            source=source,
            interval=interval,
            open=open_price,
            high=high_price,
            low=low_price,
            close=close_price,
            volume=volume,
        )


async def create_price_cache(
    redis_url: str = "redis://localhost:6379",
    default_ttl: int = 3600,
    key_prefix: str = "papertrade:price",
) -> PriceCache:
    """Factory function to create a PriceCache with Redis connection.
    
    Args:
        redis_url: Redis connection URL
        default_ttl: Default TTL in seconds
        key_prefix: Redis key prefix
        
    Returns:
        Configured PriceCache instance
    """
    import redis.asyncio as redis

    redis_client = redis.from_url(redis_url, decode_responses=False)
    return PriceCache(
        redis_client=redis_client,
        default_ttl=default_ttl,
        key_prefix=key_prefix,
    )
