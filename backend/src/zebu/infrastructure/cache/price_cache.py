"""Redis-based cache for PricePoint data.

This module provides a simple wrapper around Redis for caching stock price data.
Uses JSON serialization for PricePoint storage with configurable TTL.

The cache supports hot data caching to reduce API calls and improve response times.
TTL is configurable to balance freshness vs. API quota usage.
"""

import json
from datetime import datetime
from typing import Protocol

from redis.asyncio import Redis

from zebu.application.dtos.price_point import PricePoint
from zebu.domain.value_objects.money import Money
from zebu.domain.value_objects.ticker import Ticker


class RedisClient(Protocol):
    """Protocol for Redis client interface.

    This allows using either real Redis or fakeredis for testing.
    """

    async def get(self, key: str) -> bytes | None:
        """Get value from Redis."""
        ...

    async def set(
        self,
        key: str,
        value: str | bytes,
        ex: int | None = None,
    ) -> bool | None:
        """Set value in Redis with optional expiration."""
        ...

    async def delete(self, *keys: str) -> int:
        """Delete keys from Redis."""
        ...

    async def exists(self, *keys: str) -> int:
        """Check if keys exist."""
        ...

    async def ttl(self, key: str) -> int:
        """Get TTL for key in seconds."""
        ...


class PriceCache:
    """Redis-based cache for stock price data.

    Provides simple CRUD operations for PricePoint objects with automatic
    JSON serialization/deserialization. Supports configurable TTL to control
    cache freshness.

    Attributes:
        redis: Redis client for cache storage
        key_prefix: Prefix for cache keys (e.g., "papertrade:price")
        default_ttl: Default TTL in seconds (None = no expiration)

    Key Format:
        {key_prefix}:{ticker.symbol}
        Example: "papertrade:price:AAPL"

    Example:
        >>> cache = PriceCache(redis, "papertrade:price", 3600)
        >>> price = PricePoint(...)
        >>> await cache.set(price)
        >>> cached = await cache.get(Ticker("AAPL"))
    """

    def __init__(
        self,
        redis: Redis | RedisClient,  # type: ignore[type-arg]  # Redis generic type parameter not needed for our usage
        key_prefix: str,
        default_ttl: int | None = None,
    ) -> None:
        """Initialize price cache.

        Args:
            redis: Redis client (real or fake)
            key_prefix: Prefix for cache keys (e.g., "papertrade:price")
            default_ttl: Default TTL in seconds (None = no expiration)
        """
        self.redis = redis
        self.key_prefix = key_prefix
        self.default_ttl = default_ttl

    def _get_key(self, ticker: Ticker) -> str:
        """Generate Redis key for ticker.

        Args:
            ticker: Stock ticker

        Returns:
            Redis key like "papertrade:price:AAPL"
        """
        return f"{self.key_prefix}:{ticker.symbol}"

    def _get_history_key(
        self,
        ticker: Ticker,
        start: datetime,
        end: datetime,
        interval: str = "1day",
    ) -> str:
        """Generate Redis key for price history range.

        Args:
            ticker: Stock ticker
            start: Start of time range
            end: End of time range
            interval: Price interval type

        Returns:
            Redis key like "papertrade:price:AAPL:history:2025-12-01:2026-01-17:1day"
        """
        start_date = start.date().isoformat()
        end_date = end.date().isoformat()
        return (
            f"{self.key_prefix}:{ticker.symbol}:history:"
            f"{start_date}:{end_date}:{interval}"
        )

    def _serialize_price(self, price: PricePoint) -> str:
        """Serialize PricePoint to JSON string.

        Args:
            price: PricePoint to serialize

        Returns:
            JSON string representation
        """
        # Convert to dict with proper serialization
        data = {
            "ticker": price.ticker.symbol,
            "price_amount": str(price.price.amount),
            "price_currency": price.price.currency,
            "timestamp": price.timestamp.isoformat(),
            "source": price.source,
            "interval": price.interval,
            "open_amount": str(price.open.amount) if price.open else None,
            "open_currency": price.open.currency if price.open else None,
            "high_amount": str(price.high.amount) if price.high else None,
            "high_currency": price.high.currency if price.high else None,
            "low_amount": str(price.low.amount) if price.low else None,
            "low_currency": price.low.currency if price.low else None,
            "close_amount": str(price.close.amount) if price.close else None,
            "close_currency": price.close.currency if price.close else None,
            "volume": price.volume,
        }
        return json.dumps(data)

    def _deserialize_price(self, json_str: str) -> PricePoint:
        """Deserialize JSON string to PricePoint.

        Args:
            json_str: JSON string to deserialize

        Returns:
            Reconstructed PricePoint

        Raises:
            ValueError: If JSON is malformed or invalid
        """
        from datetime import datetime
        from decimal import Decimal

        data = json.loads(json_str)

        # Reconstruct Money objects
        price = Money(Decimal(data["price_amount"]), data["price_currency"])

        open_price = None
        if data.get("open_amount") is not None:
            open_price = Money(Decimal(data["open_amount"]), data["open_currency"])

        high_price = None
        if data.get("high_amount") is not None:
            high_price = Money(Decimal(data["high_amount"]), data["high_currency"])

        low_price = None
        if data.get("low_amount") is not None:
            low_price = Money(Decimal(data["low_amount"]), data["low_currency"])

        close_price = None
        if data.get("close_amount") is not None:
            close_price = Money(Decimal(data["close_amount"]), data["close_currency"])

        # Reconstruct PricePoint
        return PricePoint(
            ticker=Ticker(data["ticker"]),
            price=price,
            timestamp=datetime.fromisoformat(data["timestamp"]),
            source=data["source"],
            interval=data["interval"],
            open=open_price,
            high=high_price,
            low=low_price,
            close=close_price,
            volume=data.get("volume"),
        )

    async def get(self, ticker: Ticker) -> PricePoint | None:
        """Get cached price for ticker.

        Args:
            ticker: Stock ticker to get price for

        Returns:
            Cached PricePoint if exists, None if cache miss

        Raises:
            ValueError: If cached data is corrupted

        Example:
            >>> price = await cache.get(Ticker("AAPL"))
            >>> if price is None:
            ...     # Cache miss, fetch from API
        """
        key = self._get_key(ticker)
        value = await self.redis.get(key)

        if value is None:
            return None

        # Deserialize from JSON
        json_str = value.decode("utf-8") if isinstance(value, bytes) else value
        return self._deserialize_price(json_str)

    async def set(
        self,
        price: PricePoint,
        ttl: int | None = None,
    ) -> None:
        """Store price in cache.

        Args:
            price: PricePoint to cache
            ttl: Time-to-live in seconds (overrides default_ttl if provided)

        Example:
            >>> price = PricePoint(...)
            >>> await cache.set(price, ttl=3600)  # Cache for 1 hour
        """
        key = self._get_key(price.ticker)
        value = self._serialize_price(price)

        # Use provided TTL or default
        expiration = ttl if ttl is not None else self.default_ttl

        await self.redis.set(key, value, ex=expiration)

    async def delete(self, ticker: Ticker) -> None:
        """Delete cached price for ticker.

        Args:
            ticker: Ticker to delete from cache

        Example:
            >>> await cache.delete(Ticker("AAPL"))
        """
        key = self._get_key(ticker)
        await self.redis.delete(key)

    async def exists(self, ticker: Ticker) -> bool:
        """Check if ticker has cached price.

        Args:
            ticker: Ticker to check

        Returns:
            True if price is cached, False otherwise

        Example:
            >>> if await cache.exists(Ticker("AAPL")):
            ...     price = await cache.get(Ticker("AAPL"))
        """
        key = self._get_key(ticker)
        result = await self.redis.exists(key)
        return bool(result)

    async def get_ttl(self, ticker: Ticker) -> int:
        """Get remaining TTL for cached price.

        Args:
            ticker: Ticker to check TTL for

        Returns:
            Remaining seconds until expiration
            -1 if key has no expiration
            -2 if key doesn't exist

        Example:
            >>> ttl = await cache.get_ttl(Ticker("AAPL"))
            >>> if ttl > 0:
            ...     print(f"Cache expires in {ttl} seconds")
        """
        key = self._get_key(ticker)
        return await self.redis.ttl(key)

    def _serialize_history(self, prices: list[PricePoint]) -> str:
        """Serialize list of PricePoints to JSON string.

        Args:
            prices: List of PricePoints to serialize

        Returns:
            JSON string representation
        """
        # Convert each price point to dict
        data = [
            {
                "ticker": p.ticker.symbol,
                "price_amount": str(p.price.amount),
                "price_currency": p.price.currency,
                "timestamp": p.timestamp.isoformat(),
                "source": p.source,
                "interval": p.interval,
                "open_amount": str(p.open.amount) if p.open else None,
                "open_currency": p.open.currency if p.open else None,
                "high_amount": str(p.high.amount) if p.high else None,
                "high_currency": p.high.currency if p.high else None,
                "low_amount": str(p.low.amount) if p.low else None,
                "low_currency": p.low.currency if p.low else None,
                "close_amount": str(p.close.amount) if p.close else None,
                "close_currency": p.close.currency if p.close else None,
                "volume": p.volume,
            }
            for p in prices
        ]
        return json.dumps(data)

    def _deserialize_history(self, json_str: str) -> list[PricePoint]:
        """Deserialize JSON string to list of PricePoints.

        Args:
            json_str: JSON string to deserialize

        Returns:
            List of reconstructed PricePoints

        Raises:
            ValueError: If JSON is malformed or invalid
        """
        from decimal import Decimal

        data = json.loads(json_str)

        price_points: list[PricePoint] = []
        for item in data:
            # Reconstruct Money objects
            price = Money(Decimal(item["price_amount"]), item["price_currency"])

            open_price = None
            if item.get("open_amount") is not None:
                open_price = Money(Decimal(item["open_amount"]), item["open_currency"])

            high_price = None
            if item.get("high_amount") is not None:
                high_price = Money(Decimal(item["high_amount"]), item["high_currency"])

            low_price = None
            if item.get("low_amount") is not None:
                low_price = Money(Decimal(item["low_amount"]), item["low_currency"])

            close_price = None
            if item.get("close_amount") is not None:
                close_price = Money(
                    Decimal(item["close_amount"]), item["close_currency"]
                )

            # Reconstruct PricePoint
            price_point = PricePoint(
                ticker=Ticker(item["ticker"]),
                price=price,
                timestamp=datetime.fromisoformat(item["timestamp"]),
                source=item["source"],
                interval=item["interval"],
                open=open_price,
                high=high_price,
                low=low_price,
                close=close_price,
                volume=item.get("volume"),
            )
            price_points.append(price_point)

        return price_points

    async def get_history(
        self,
        ticker: Ticker,
        start: datetime,
        end: datetime,
        interval: str = "1day",
    ) -> list[PricePoint] | None:
        """Get cached price history for date range.

        Args:
            ticker: Stock ticker to get history for
            start: Start of time range (inclusive)
            end: End of time range (inclusive)
            interval: Price interval type (default: "1day")

        Returns:
            Cached list of PricePoints if exists, None if cache miss

        Raises:
            ValueError: If cached data is corrupted

        Example:
            >>> history = await cache.get_history(
            ...     Ticker("AAPL"),
            ...     datetime(2025, 12, 1, tzinfo=UTC),
            ...     datetime(2026, 1, 17, tzinfo=UTC)
            ... )
            >>> if history is None:
            ...     # Cache miss, fetch from database or API
        """
        key = self._get_history_key(ticker, start, end, interval)
        value = await self.redis.get(key)

        if value is None:
            return None

        # Deserialize from JSON
        json_str = value.decode("utf-8") if isinstance(value, bytes) else value
        return self._deserialize_history(json_str)

    async def set_history(
        self,
        ticker: Ticker,
        start: datetime,
        end: datetime,
        prices: list[PricePoint],
        interval: str = "1day",
        ttl: int | None = None,
    ) -> None:
        """Cache price history with appropriate TTL.

        Args:
            ticker: Stock ticker
            start: Start of time range
            end: End of time range
            prices: List of PricePoints to cache
            interval: Price interval type (default: "1day")
            ttl: Time-to-live in seconds (overrides default_ttl if provided)

        Example:
            >>> await cache.set_history(
            ...     Ticker("AAPL"),
            ...     datetime(2025, 12, 1, tzinfo=UTC),
            ...     datetime(2026, 1, 17, tzinfo=UTC),
            ...     price_points,
            ...     ttl=7 * 24 * 3600  # 7 days
            ... )
        """
        key = self._get_history_key(ticker, start, end, interval)
        value = self._serialize_history(prices)

        # Use provided TTL or default
        expiration = ttl if ttl is not None else self.default_ttl

        await self.redis.set(key, value, ex=expiration)
