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

    async def scan(
        self,
        cursor: int = 0,
        match: str | None = None,
        count: int | None = None,
    ) -> tuple[int, list[str]]:
        """Scan keys incrementally.
        
        Returns:
            Tuple of (next_cursor, list_of_keys)
        """
        ...

    async def keys(self, pattern: str) -> list[str]:
        """Get keys matching pattern."""
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

    def _parse_dates_from_key(self, key: str) -> tuple[datetime, datetime] | None:
        """Parse start and end dates from cache key.

        Args:
            key: Cache key in format "prefix:TICKER:history:START_DATE:END_DATE:interval"

        Returns:
            Tuple of (start_datetime, end_datetime) or None if parsing fails

        Example:
            >>> key = "papertrade:price:AAPL:history:2025-12-01:2025-12-31:1day"
            >>> start, end = self._parse_dates_from_key(key)
        """
        try:
            # Split key and extract date parts
            # Format: {prefix}:{ticker}:history:{start_date}:{end_date}:{interval}
            parts = key.split(":")
            # Need at least: prefix, ticker, "history", start, end, interval = 6 parts
            if len(parts) < 6:
                return None

            # Find "history" marker
            history_idx = -1
            for i, part in enumerate(parts):
                if part == "history":
                    history_idx = i
                    break

            if history_idx == -1 or history_idx + 3 > len(parts):
                return None

            # Extract dates: they come after "history"
            start_date_str = parts[history_idx + 1]
            end_date_str = parts[history_idx + 2]

            # Parse ISO date strings to datetime objects
            # The keys use date format (YYYY-MM-DD), not full datetime
            from datetime import UTC

            start_date = datetime.fromisoformat(start_date_str)
            end_date = datetime.fromisoformat(end_date_str)

            # Set to start/end of day for proper range comparison
            start_datetime = start_date.replace(hour=0, minute=0, second=0, tzinfo=UTC)
            end_datetime = end_date.replace(
                hour=23, minute=59, second=59, tzinfo=UTC
            )

            return (start_datetime, end_datetime)

        except (ValueError, IndexError, AttributeError):
            # Malformed key - return None to skip it
            return None

    def _is_range_subset(
        self,
        requested_start: datetime,
        requested_end: datetime,
        cached_start: datetime,
        cached_end: datetime,
    ) -> bool:
        """Check if requested range is subset of cached range.

        Args:
            requested_start: Start of requested range
            requested_end: End of requested range
            cached_start: Start of cached range
            cached_end: End of cached range

        Returns:
            True if requested range is fully contained within cached range

        Example:
            >>> # Cached: Jan 1-31, Requested: Jan 25-31
            >>> self._is_range_subset(
            ...     datetime(2026, 1, 25),
            ...     datetime(2026, 1, 31),
            ...     datetime(2026, 1, 1),
            ...     datetime(2026, 1, 31)
            ... )
            True
        """
        return cached_start <= requested_start and cached_end >= requested_end

    def _filter_to_range(
        self,
        price_points: list[PricePoint],
        start: datetime,
        end: datetime,
    ) -> list[PricePoint]:
        """Filter price points to requested date range.

        Args:
            price_points: List of PricePoints to filter
            start: Start of requested range (inclusive)
            end: End of requested range (inclusive)

        Returns:
            Filtered list of PricePoints within the requested range

        Example:
            >>> # Filter month of data to just one week
            >>> filtered = self._filter_to_range(month_data, week_start, week_end)
        """
        from datetime import UTC

        return [
            p
            for p in price_points
            if start <= p.timestamp.replace(tzinfo=UTC) <= end
        ]

    async def _find_broader_cached_ranges(
        self,
        ticker: Ticker,
        start: datetime,
        end: datetime,
        interval: str,
    ) -> list[PricePoint] | None:
        """Search for cached ranges that contain the requested range.

        Uses SCAN to iterate through cache keys matching the ticker and interval,
        looking for a broader range that fully contains the requested range.

        Args:
            ticker: Stock ticker
            start: Start of requested range
            end: End of requested range
            interval: Price interval type

        Returns:
            Filtered PricePoints from broader cached range, or None if not found

        Example:
            >>> # Looking for Jan 25-31, might find cached Jan 1-31
            >>> result = await self._find_broader_cached_ranges(
            ...     Ticker("AAPL"),
            ...     datetime(2026, 1, 25),
            ...     datetime(2026, 1, 31),
            ...     "1day"
            ... )
        """
        pattern = f"{self.key_prefix}:{ticker.symbol}:history:*:*:{interval}"

        cursor = 0
        while True:
            # Use SCAN for non-blocking iteration
            cursor, keys = await self.redis.scan(cursor, match=pattern, count=100)

            for key in keys:
                # Decode bytes to string if needed
                key_str = key.decode("utf-8") if isinstance(key, bytes) else key

                # Parse dates from key
                parsed = self._parse_dates_from_key(key_str)
                if not parsed:
                    continue  # Skip malformed keys

                cached_start, cached_end = parsed

                # Check if this cached range contains our requested range
                if self._is_range_subset(start, end, cached_start, cached_end):
                    # Found a broader range! Get the data
                    value = await self.redis.get(key_str)
                    if value:
                        try:
                            json_str = (
                                value.decode("utf-8")
                                if isinstance(value, bytes)
                                else value
                            )
                            cached_data = self._deserialize_history(json_str)

                            # Filter to requested range and return
                            filtered = self._filter_to_range(cached_data, start, end)
                            if filtered:
                                return filtered
                        except (ValueError, json.JSONDecodeError):
                            # Corrupted data - skip this cache entry
                            continue

            # Check if scan is complete
            if cursor == 0:
                break

        # No suitable cached range found
        return None

    async def get_history(
        self,
        ticker: Ticker,
        start: datetime,
        end: datetime,
        interval: str = "1day",
    ) -> list[PricePoint] | None:
        """Get cached price history for date range.

        Implements subset cache matching: if exact range not found, searches for
        broader cached ranges that contain the requested range and filters them.

        Strategy:
        1. Try exact match (fast path - no SCAN needed)
        2. If miss, search for broader cached ranges using SCAN
        3. Filter broader range to requested subset

        Args:
            ticker: Stock ticker to get history for
            start: Start of time range (inclusive)
            end: End of time range (inclusive)
            interval: Price interval type (default: "1day")

        Returns:
            Cached list of PricePoints if exists (exact or filtered), None if cache miss

        Raises:
            ValueError: If cached data is corrupted

        Example:
            >>> # Exact match
            >>> history = await cache.get_history(
            ...     Ticker("AAPL"),
            ...     datetime(2025, 12, 1, tzinfo=UTC),
            ...     datetime(2026, 1, 17, tzinfo=UTC)
            ... )
            >>> # Subset match (Jan 25-31 found within cached Jan 1-31)
            >>> week = await cache.get_history(
            ...     Ticker("AAPL"),
            ...     datetime(2026, 1, 25, tzinfo=UTC),
            ...     datetime(2026, 1, 31, tzinfo=UTC)
            ... )
        """
        # 1. Try exact match (fast path)
        key = self._get_history_key(ticker, start, end, interval)
        value = await self.redis.get(key)

        if value is not None:
            # Exact match found
            json_str = value.decode("utf-8") if isinstance(value, bytes) else value
            return self._deserialize_history(json_str)

        # 2. Exact match failed - search for broader cached ranges
        return await self._find_broader_cached_ranges(ticker, start, end, interval)

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
