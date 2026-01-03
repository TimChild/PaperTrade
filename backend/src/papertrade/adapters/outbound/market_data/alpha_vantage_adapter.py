"""Alpha Vantage market data adapter with rate limiting and caching.

This module implements the MarketDataPort interface using Alpha Vantage
as the data source. It provides tiered caching (Redis → PostgreSQL → API)
and comprehensive rate limiting to prevent quota exhaustion.

The adapter implements graceful degradation: when rate limited, it serves
stale cached data if available rather than failing completely.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING

import httpx

from papertrade.application.dtos.price_point import PricePoint
from papertrade.application.exceptions import (
    InvalidPriceDataError,
    MarketDataUnavailableError,
    TickerNotFoundError,
)
from papertrade.domain.value_objects.money import Money
from papertrade.domain.value_objects.ticker import Ticker
from papertrade.infrastructure.cache.price_cache import PriceCache
from papertrade.infrastructure.rate_limiter import RateLimiter

if TYPE_CHECKING:
    from papertrade.adapters.outbound.repositories.price_repository import (
        PriceRepository,
    )


class AlphaVantageAdapter:
    """Alpha Vantage implementation of MarketDataPort.

    This adapter fetches stock price data from Alpha Vantage API with tiered caching
    and rate limiting. It implements graceful degradation to serve stale data when
    API quota is exhausted.

    Caching Strategy (Tiered):
        1. Redis cache (hot data, <100ms)
        2. PostgreSQL (warm data, <500ms) - stubbed for Phase 2a
        3. Alpha Vantage API (cold data, <2s)

    Rate Limiting:
        - 5 calls/minute (free tier)
        - 500 calls/day (free tier)
        - Enforced via token bucket algorithm

    Error Handling:
        - Invalid ticker → TickerNotFoundError
        - Rate limited → Serve stale data or MarketDataUnavailableError
        - Network errors → MarketDataUnavailableError
        - Malformed data → InvalidPriceDataError

    Attributes:
        rate_limiter: Token bucket rate limiter
        price_cache: Redis cache for price data
        http_client: HTTP client for API calls
        api_key: Alpha Vantage API key
        base_url: API base URL
        timeout: Request timeout in seconds
        max_retries: Maximum retry attempts for failed requests

    Example:
        >>> adapter = AlphaVantageAdapter(
        ...     rate_limiter=limiter,
        ...     price_cache=cache,
        ...     http_client=httpx.AsyncClient(),
        ...     api_key="demo",
        ... )
        >>> price = await adapter.get_current_price(Ticker("AAPL"))
    """

    def __init__(
        self,
        rate_limiter: RateLimiter,
        price_cache: PriceCache,
        http_client: httpx.AsyncClient,
        api_key: str,
        base_url: str = "https://www.alphavantage.co/query",
        timeout: float = 5.0,
        max_retries: int = 3,
        price_repository: PriceRepository | None = None,
    ) -> None:
        """Initialize Alpha Vantage adapter.

        Args:
            rate_limiter: Rate limiter for API calls
            price_cache: Redis cache for price data
            http_client: HTTP client for API calls
            api_key: Alpha Vantage API key
            base_url: API base URL (default: Alpha Vantage production)
            timeout: Request timeout in seconds (default: 5.0)
            max_retries: Maximum retry attempts (default: 3)
            price_repository: Optional price repository for Tier 2 caching
        """
        self.rate_limiter = rate_limiter
        self.price_cache = price_cache
        self.http_client = http_client
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.price_repository = price_repository

    async def get_current_price(self, ticker: Ticker) -> PricePoint:
        """Get the most recent available price for a ticker.

        Implements tiered caching strategy:
        1. Check Redis cache (return if fresh)
        2. Check PostgreSQL (return if reasonably fresh)
        3. Fetch from Alpha Vantage API (if rate limit allows)
        4. Serve stale cached data if rate limited

        Args:
            ticker: Stock ticker symbol to get price for

        Returns:
            PricePoint with latest available price

        Raises:
            TickerNotFoundError: Ticker doesn't exist in data source
            MarketDataUnavailableError: Cannot fetch price and no cached data available

        Example:
            >>> price = await adapter.get_current_price(Ticker("AAPL"))
            >>> print(f"AAPL: {price.price} (source: {price.source})")
        """
        # Tier 1: Check Redis cache
        cached = await self.price_cache.get(ticker)
        if cached and not cached.is_stale(max_age=timedelta(hours=1)):
            # Fresh cached data, return it
            return cached.with_source("cache")

        # Tier 2: Check PostgreSQL
        if self.price_repository:
            db_price = await self.price_repository.get_latest_price(
                ticker, max_age=timedelta(hours=4)
            )
            if db_price and not db_price.is_stale(max_age=timedelta(hours=4)):
                # Warm the cache with database price
                await self.price_cache.set(db_price, ttl=3600)
                return db_price.with_source("database")

        # Tier 3: Fetch from Alpha Vantage API
        if not await self.rate_limiter.can_make_request():
            # Rate limited - serve stale data if available
            if cached:
                # Serve stale data with source annotation
                return cached.with_source("cache")

            # No cached data and rate limited
            wait_time = await self.rate_limiter.wait_time()
            raise MarketDataUnavailableError(
                f"Rate limit exceeded. No cached data available. "
                f"Retry in {wait_time:.0f} seconds."
            )

        # Consume rate limit token before making API call
        consumed = await self.rate_limiter.consume_token()
        if not consumed:
            # Race condition - another request consumed the last token
            if cached:
                return cached.with_source("cache")
            raise MarketDataUnavailableError("Rate limit exceeded, no cached data")

        # Make API request
        try:
            price = await self._fetch_from_api(ticker)

            # Store in cache for future requests
            await self.price_cache.set(price, ttl=3600)  # 1 hour TTL

            # Store in database for Tier 2 caching
            if self.price_repository:
                await self.price_repository.upsert_price(price)

            return price

        except Exception:
            # API call failed - serve stale cached data if available
            if cached:
                return cached.with_source("cache")

            # No fallback available, re-raise the error
            raise

    async def _fetch_from_api(self, ticker: Ticker) -> PricePoint:
        """Fetch price from Alpha Vantage API.

        Makes HTTP request to Alpha Vantage GLOBAL_QUOTE endpoint and parses response.
        Implements retry logic with exponential backoff for transient failures.

        Args:
            ticker: Stock ticker to fetch

        Returns:
            PricePoint from API response

        Raises:
            TickerNotFoundError: Ticker not found in API
            MarketDataUnavailableError: API error or network failure
            InvalidPriceDataError: Malformed API response
        """
        params = {
            "function": "GLOBAL_QUOTE",
            "symbol": ticker.symbol,
            "apikey": self.api_key,
        }

        last_error: Exception | None = None

        for attempt in range(self.max_retries):
            try:
                response = await self.http_client.get(
                    self.base_url,
                    params=params,
                    timeout=self.timeout,
                )

                # Check HTTP status
                if response.status_code == 200:
                    return self._parse_response(ticker, response.json())
                elif response.status_code == 404:
                    raise TickerNotFoundError(ticker.symbol)
                else:
                    last_error = MarketDataUnavailableError(
                        f"API returned status {response.status_code}"
                    )

            except httpx.TimeoutException as e:
                last_error = MarketDataUnavailableError(f"Request timeout: {e}")
            except httpx.NetworkError as e:
                last_error = MarketDataUnavailableError(f"Network error: {e}")
            except httpx.HTTPError as e:
                last_error = MarketDataUnavailableError(f"HTTP error: {e}")

            # Exponential backoff between retries (except on last attempt)
            if attempt < self.max_retries - 1:
                import asyncio

                await asyncio.sleep(2**attempt)  # 1s, 2s, 4s, etc.

        # All retries exhausted
        if last_error:
            raise last_error

        raise MarketDataUnavailableError("API request failed after retries")

    def _parse_response(self, ticker: Ticker, data: dict[str, object]) -> PricePoint:
        """Parse Alpha Vantage GLOBAL_QUOTE response.

        Alpha Vantage response format:
        {
            "Global Quote": {
                "01. symbol": "AAPL",
                "05. price": "192.53",
                "07. latest trading day": "2025-12-27",
                ...
            }
        }

        Args:
            ticker: Ticker being parsed
            data: JSON response from API

        Returns:
            Parsed PricePoint

        Raises:
            TickerNotFoundError: Empty response (ticker not found)
            InvalidPriceDataError: Malformed or invalid response
        """
        try:
            global_quote = data.get("Global Quote")

            if not global_quote or not isinstance(global_quote, dict):
                # Empty response means ticker not found
                raise TickerNotFoundError(
                    ticker.symbol, "Ticker not found in Alpha Vantage database"
                )

            # Extract price (field "05. price")
            price_str = global_quote.get("05. price")
            if not price_str:
                raise InvalidPriceDataError(
                    ticker.symbol, "Missing price field in API response"
                )

            price_value = Decimal(str(price_str))
            if price_value <= 0:
                raise InvalidPriceDataError(
                    ticker.symbol, f"Invalid price: {price_value}"
                )

            # Extract timestamp - use current time for cache freshness tracking
            # Note: The "07. latest trading day" field tells us which day's
            # data this is, but we use current time to track when we fetched
            # it (for cache expiry)
            timestamp = datetime.now(UTC)

            # Construct PricePoint
            return PricePoint(
                ticker=ticker,
                price=Money(price_value, "USD"),
                timestamp=timestamp,
                source="alpha_vantage",
                interval="1day",  # GLOBAL_QUOTE returns daily closing price
            )

        except (KeyError, ValueError, TypeError) as e:
            raise InvalidPriceDataError(
                ticker.symbol, f"Failed to parse API response: {e}"
            ) from e

    async def get_price_at(self, ticker: Ticker, timestamp: datetime) -> PricePoint:
        """Get the price for a ticker at a specific point in time.

        This method queries the price repository for historical data. It finds the
        price closest to (but not after) the requested timestamp.

        Args:
            ticker: Stock ticker symbol
            timestamp: When to get the price (must be UTC)

        Returns:
            PricePoint with price closest to requested timestamp

        Raises:
            TickerNotFoundError: Ticker doesn't exist
            MarketDataUnavailableError: No data available for that time period

        Example:
            >>> timestamp = datetime(2024, 6, 15, 16, 0, tzinfo=UTC)
            >>> price = await adapter.get_price_at(Ticker("AAPL"), timestamp)
        """
        # Validate timestamp is not in the future
        if timestamp > datetime.now(UTC):
            raise MarketDataUnavailableError(
                f"Cannot get price for future timestamp: {timestamp}"
            )

        # Query repository for price at timestamp
        if not self.price_repository:
            raise MarketDataUnavailableError(
                "Price repository not configured - cannot query historical data"
            )

        price = await self.price_repository.get_price_at(ticker, timestamp)

        if not price:
            raise MarketDataUnavailableError(
                f"No price data available for {ticker.symbol} at {timestamp}"
            )

        return price

    async def get_price_history(
        self,
        ticker: Ticker,
        start: datetime,
        end: datetime,
        interval: str = "1day",
    ) -> list[PricePoint]:
        """Get price history over a time range.

        This method implements tiered caching for historical data:
        1. Check Redis cache for recent history queries
        2. Query price repository for date range
        3. Optionally fetch from Alpha Vantage API if gaps exist

        Args:
            ticker: Stock ticker symbol
            start: Start of time range (inclusive, must be UTC)
            end: End of time range (inclusive, must be UTC)
            interval: Price interval type (default: "1day")

        Returns:
            List of PricePoint objects, ordered chronologically

        Raises:
            ValueError: Invalid interval or end before start
            TickerNotFoundError: Ticker doesn't exist
            MarketDataUnavailableError: Insufficient data for range

        Example:
            >>> start = datetime(2024, 1, 1, tzinfo=UTC)
            >>> end = datetime(2024, 12, 31, tzinfo=UTC)
            >>> history = await adapter.get_price_history(Ticker("AAPL"), start, end)
        """
        # Validate inputs
        if end < start:
            raise ValueError(f"End date ({end}) must be after start date ({start})")

        valid_intervals = ["1min", "5min", "15min", "30min", "1hour", "1day"]
        if interval not in valid_intervals:
            raise ValueError(
                f"Invalid interval: {interval}. Must be one of {valid_intervals}"
            )

        # Query repository for price history
        if not self.price_repository:
            raise MarketDataUnavailableError(
                "Price repository not configured - cannot query historical data"
            )

        history = await self.price_repository.get_price_history(
            ticker, start, end, interval
        )

        # Return results (empty list if no data - not an error per spec)
        return history

    async def get_supported_tickers(self) -> list[Ticker]:
        """Get list of tickers we have data for.

        Queries the price repository to get all tickers with historical data.

        Returns:
            List of Ticker objects for all supported tickers

        Raises:
            MarketDataUnavailableError: Cannot access ticker list

        Example:
            >>> tickers = await adapter.get_supported_tickers()
            >>> print(f"We have data for {len(tickers)} tickers")
        """
        if not self.price_repository:
            # No repository configured - return empty list
            return []

        try:
            return await self.price_repository.get_all_tickers()
        except Exception as e:
            raise MarketDataUnavailableError(
                f"Failed to get supported tickers: {e}"
            ) from e
