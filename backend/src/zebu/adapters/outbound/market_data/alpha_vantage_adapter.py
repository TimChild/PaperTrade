"""Alpha Vantage market data adapter with rate limiting and caching.

This module implements the MarketDataPort interface using Alpha Vantage
as the data source. It provides tiered caching (Redis → PostgreSQL → API)
and comprehensive rate limiting to prevent quota exhaustion.

The adapter implements graceful degradation: when rate limited, it serves
stale cached data if available rather than failing completely.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING

import httpx

from zebu.application.dtos.price_point import PricePoint
from zebu.application.exceptions import (
    InvalidPriceDataError,
    MarketDataUnavailableError,
    TickerNotFoundError,
)
from zebu.domain.value_objects.money import Money
from zebu.domain.value_objects.ticker import Ticker
from zebu.infrastructure.cache.price_cache import PriceCache
from zebu.infrastructure.rate_limiter import RateLimiter

if TYPE_CHECKING:
    from zebu.adapters.outbound.repositories.price_repository import (
        PriceRepository,
    )

logger = logging.getLogger(__name__)


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

    async def get_batch_prices(self, tickers: list[Ticker]) -> dict[Ticker, PricePoint]:
        """Get current prices for multiple tickers in a single batch request.

        This method optimizes price fetching by:
        1. Checking cache for all tickers first
        2. Only fetching uncached tickers from API (one by one)
        3. Returning partial results if some tickers fail

        Note: Alpha Vantage free tier doesn't have a true batch API, so we fetch
        uncached tickers sequentially. However, we still get the benefit of:
        - Batch cache checking (fast)
        - Only fetching what's needed
        - Graceful handling of partial failures

        Args:
            tickers: List of stock ticker symbols to get prices for

        Returns:
            Dictionary mapping tickers to their price points.
            Only includes tickers for which prices were successfully fetched.

        Example:
            >>> tickers = [Ticker("AAPL"), Ticker("GOOGL")]
            >>> prices = await adapter.get_batch_prices(tickers)
            >>> print(f"Got prices for {len(prices)} tickers")
        """
        import logging

        logger = logging.getLogger(__name__)
        result: dict[Ticker, PricePoint] = {}

        # Empty list, return early
        if not tickers:
            return result

        # Step 1: Check cache for all tickers
        uncached_tickers: list[Ticker] = []
        for ticker in tickers:
            cached = await self.price_cache.get(ticker)
            if cached and not cached.is_stale(max_age=timedelta(hours=1)):
                # Fresh cached data
                result[ticker] = cached.with_source("cache")
            else:
                uncached_tickers.append(ticker)

        # Step 2: Check database for uncached tickers
        if self.price_repository and uncached_tickers:
            db_uncached: list[Ticker] = []
            for ticker in uncached_tickers:
                db_price = await self.price_repository.get_latest_price(
                    ticker, max_age=timedelta(hours=4)
                )
                if db_price and not db_price.is_stale(max_age=timedelta(hours=4)):
                    # Warm the cache
                    await self.price_cache.set(db_price, ttl=3600)
                    result[ticker] = db_price.with_source("database")
                else:
                    db_uncached.append(ticker)
            uncached_tickers = db_uncached

        # Step 3: Fetch remaining uncached tickers from API
        # Note: We fetch sequentially to respect rate limits
        # Alpha Vantage free tier: 5 calls/minute
        if uncached_tickers:
            for ticker in uncached_tickers:
                try:
                    # Check rate limit before each API call
                    if not await self.rate_limiter.can_make_request():
                        logger.warning(
                            f"Rate limit reached, skipping API fetch for "
                            f"{ticker.symbol}"
                        )
                        # Try to serve stale cached data
                        cached = await self.price_cache.get(ticker)
                        if cached:
                            result[ticker] = cached.with_source("cache")
                        continue

                    # Consume rate limit token
                    consumed = await self.rate_limiter.consume_token()
                    if not consumed:
                        logger.warning(
                            f"Failed to consume rate limit token for {ticker.symbol}"
                        )
                        # Try to serve stale cached data
                        cached = await self.price_cache.get(ticker)
                        if cached:
                            result[ticker] = cached.with_source("cache")
                        continue

                    # Fetch from API
                    price = await self._fetch_from_api(ticker)

                    # Store in cache and database
                    await self.price_cache.set(price, ttl=3600)
                    if self.price_repository:
                        await self.price_repository.upsert_price(price)

                    result[ticker] = price

                except Exception as e:
                    # Log but don't fail - just exclude this ticker from results
                    logger.warning(
                        f"Failed to fetch price for {ticker.symbol}: {e}",
                        exc_info=True,
                    )
                    # Try to serve stale cached data as last resort
                    cached = await self.price_cache.get(ticker)
                    if cached:
                        result[ticker] = cached.with_source("cache")

        return result

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
        1. Check price repository for cached date range
        2. If data is missing or incomplete, fetch from Alpha Vantage API
        3. Store fetched data in repository for future use

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
        # Log incoming request
        logger.info(
            "Price history request",
            extra={
                "ticker": ticker.symbol,
                "start": start.isoformat(),
                "end": end.isoformat(),
                "interval": interval,
                "requested_days": (end - start).days,
            },
        )

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

        # Try to get cached data first
        history = await self.price_repository.get_price_history(
            ticker, start, end, interval
        )

        # Log cache query result
        if history:
            first_date = history[0].timestamp.date()
            last_date = history[-1].timestamp.date()
            logger.info(
                "Cache query result",
                extra={
                    "ticker": ticker.symbol,
                    "cached_points": len(history),
                    "cached_range": f"{first_date} to {last_date}",
                },
            )
        else:
            logger.info("Cache miss", extra={"ticker": ticker.symbol})

        # Check if cached data is complete for requested range
        if history and interval == "1day":
            if self._is_cache_complete(history, start, end):
                logger.info(
                    "Returning complete cached data",
                    extra={
                        "ticker": ticker.symbol,
                        "cached_points": len(history),
                        "date_range": f"{start.date()} to {end.date()}",
                    },
                )
                return history
            else:
                logger.info(
                    "Cached data incomplete, fetching from API",
                    extra={
                        "ticker": ticker.symbol,
                        "cached_points": len(history),
                        "requested_range": f"{start.date()} to {end.date()}",
                        "cached_range": (
                            f"{history[0].timestamp.date()} to "
                            f"{history[-1].timestamp.date()}"
                        ),
                    },
                )
                # Fall through to API fetch

        # No cached data or incomplete - fetch from API if interval is "1day"
        # Only support daily data fetching for now (Alpha Vantage free tier)
        if interval == "1day":
            logger.info(
                "Fetching from Alpha Vantage API",
                extra={
                    "ticker": ticker.symbol,
                    "reason": "cache_miss" if not history else "cache_incomplete",
                },
            )

            # Check rate limiting before API call
            if not await self.rate_limiter.can_make_request():
                logger.warning(
                    "Rate limit exceeded, cannot fetch data",
                    extra={"ticker": ticker.symbol},
                )
                raise MarketDataUnavailableError(
                    "Rate limit exceeded. Cannot fetch historical data at this time."
                )

            # Consume rate limit token
            consumed = await self.rate_limiter.consume_token()
            if not consumed:
                logger.warning(
                    "Failed to consume rate limit token",
                    extra={"ticker": ticker.symbol},
                )
                raise MarketDataUnavailableError(
                    "Rate limit exceeded. Cannot fetch historical data."
                )

            # Fetch from API
            try:
                history = await self._fetch_daily_history_from_api(ticker)

                logger.info(
                    "Alpha Vantage API fetch successful",
                    extra={
                        "ticker": ticker.symbol,
                        "total_points_fetched": len(history),
                        "fetched_range": (
                            f"{history[0].timestamp.date()} to "
                            f"{history[-1].timestamp.date()}"
                        )
                        if history
                        else "none",
                    },
                )

                # Filter to requested date range
                filtered_history = [
                    p
                    for p in history
                    if start <= p.timestamp.replace(tzinfo=UTC) <= end
                ]

                logger.info(
                    "Returning filtered API data",
                    extra={
                        "ticker": ticker.symbol,
                        "points_returned": len(filtered_history),
                        "source": "alpha_vantage_api",
                    },
                )

                return filtered_history

            except Exception as e:
                logger.error(
                    "Alpha Vantage API fetch failed",
                    extra={
                        "ticker": ticker.symbol,
                        "error": str(e),
                    },
                    exc_info=True,
                )
                # API call failed - return empty list rather than error
                # This matches the original behavior of returning empty if no data
                return []

        # For other intervals, return empty list if no cached data
        return []

    def _is_cache_complete(
        self,
        cached_data: list[PricePoint],
        start: datetime,
        end: datetime,
    ) -> bool:
        """Check if cached data is complete for the requested date range.

        For daily data, validates:
        1. Boundary coverage: Cache spans from start to end (±1 day tolerance)
        2. Density check: Has at least 70% of expected trading days
           (for ranges ≤30 days)

        Args:
            cached_data: List of cached price points (assumed sorted by timestamp)
            start: Start of requested range (UTC)
            end: End of requested range (UTC)

        Returns:
            True if cached data appears complete, False if likely incomplete
        """
        if not cached_data:
            return False

        # Get boundary timestamps
        first_cached = cached_data[0].timestamp.replace(tzinfo=UTC)
        last_cached = cached_data[-1].timestamp.replace(tzinfo=UTC)

        # Check boundary coverage (allow 1-day tolerance for timezone/market timing)
        if first_cached > start + timedelta(days=1):
            logger.debug(
                "Cache incomplete: missing early dates",
                extra={
                    "first_cached": first_cached.date().isoformat(),
                    "requested_start": start.date().isoformat(),
                },
            )
            return False

        if last_cached < end - timedelta(days=1):
            logger.debug(
                "Cache incomplete: missing recent dates",
                extra={
                    "last_cached": last_cached.date().isoformat(),
                    "requested_end": end.date().isoformat(),
                },
            )
            return False

        # For short date ranges (≤30 days), verify density
        # This catches major gaps in the middle of the range
        days_requested = (end - start).days
        if days_requested <= 30:
            # Estimate expected trading days (rough: 5/7 of calendar days)
            expected_trading_days = days_requested * 5 / 7
            # Require at least 70% of expected days (allows for holidays, minor gaps)
            min_required_points = int(expected_trading_days * 0.7)

            if len(cached_data) < min_required_points:
                logger.debug(
                    "Cache incomplete: insufficient density",
                    extra={
                        "cached_points": len(cached_data),
                        "min_required": min_required_points,
                        "days_requested": days_requested,
                    },
                )
                return False

        # Cache appears complete
        return True

    async def _fetch_daily_history_from_api(self, ticker: Ticker) -> list[PricePoint]:
        """Fetch daily historical price data from Alpha Vantage API.

        Uses TIME_SERIES_DAILY endpoint to get up to 100 days of historical data.
        Stores all fetched data in the price repository for future use.

        Args:
            ticker: Stock ticker to fetch historical data for

        Returns:
            List of PricePoint objects with daily historical prices

        Raises:
            TickerNotFoundError: Ticker not found in API
            MarketDataUnavailableError: API error or network failure
            InvalidPriceDataError: Malformed API response
        """
        params = {
            "function": "TIME_SERIES_DAILY",
            "symbol": ticker.symbol,
            "apikey": self.api_key,
            # Last 100 TRADING days (~4-5 months of calendar time,
            # excluding weekends/holidays)
            "outputsize": "compact",
            # Note: "compact" is limited to 100 data points.
            # For older data, use "full" (requires premium API key).
            # Requests beyond this range will return partial results.
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
                    response_data = response.json()
                    price_points = self._parse_daily_history_response(
                        ticker, response_data
                    )

                    # Store all fetched data in repository
                    if self.price_repository:
                        logger.info(
                            "Storing fetched price data in repository",
                            extra={
                                "ticker": ticker.symbol,
                                "points_to_store": len(price_points),
                            },
                        )
                        for price_point in price_points:
                            await self.price_repository.upsert_price(price_point)

                    return price_points
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

    def _parse_daily_history_response(
        self, ticker: Ticker, data: dict[str, object]
    ) -> list[PricePoint]:
        """Parse Alpha Vantage TIME_SERIES_DAILY response.

        Alpha Vantage response format:
        {
            "Meta Data": {...},
            "Time Series (Daily)": {
                "2025-12-27": {
                    "1. open": "192.00",
                    "2. high": "193.50",
                    "3. low": "191.00",
                    "4. close": "192.53",
                    "5. volume": "52000000"
                },
                ...
            }
        }

        Args:
            ticker: Ticker being parsed
            data: JSON response from API

        Returns:
            List of PricePoint objects, ordered chronologically (oldest first)

        Raises:
            TickerNotFoundError: Empty response (ticker not found)
            InvalidPriceDataError: Malformed or invalid response
        """
        try:
            time_series = data.get("Time Series (Daily)")

            if not time_series or not isinstance(time_series, dict):
                # Empty response means ticker not found
                raise TickerNotFoundError(
                    ticker.symbol, "Ticker not found in Alpha Vantage database"
                )

            price_points: list[PricePoint] = []

            for date_str, daily_data in time_series.items():
                if not isinstance(daily_data, dict):
                    continue

                # Extract close price (field "4. close")
                close_str = daily_data.get("4. close")
                if not close_str:
                    continue  # Skip incomplete data

                close_value = Decimal(str(close_str))
                if close_value <= 0:
                    continue  # Skip invalid prices

                # Parse date and create timestamp at market close
                # (4:00 PM ET = 21:00 UTC)
                date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                timestamp = date_obj.replace(hour=21, minute=0, second=0, tzinfo=UTC)

                # Extract optional OHLCV data
                open_value = None
                high_value = None
                low_value = None
                volume = None

                if open_str := daily_data.get("1. open"):
                    open_value = Money(Decimal(str(open_str)), "USD")
                if high_str := daily_data.get("2. high"):
                    high_value = Money(Decimal(str(high_str)), "USD")
                if low_str := daily_data.get("3. low"):
                    low_value = Money(Decimal(str(low_str)), "USD")
                if volume_str := daily_data.get("5. volume"):
                    volume = int(volume_str)

                # Construct PricePoint
                price_point = PricePoint(
                    ticker=ticker,
                    price=Money(close_value, "USD"),
                    timestamp=timestamp,
                    source="alpha_vantage",
                    interval="1day",
                    open=open_value,
                    high=high_value,
                    low=low_value,
                    close=Money(close_value, "USD"),
                    volume=volume,
                )

                price_points.append(price_point)

            # Sort chronologically (oldest first)
            price_points.sort(key=lambda p: p.timestamp)

            return price_points

        except (KeyError, ValueError, TypeError) as e:
            raise InvalidPriceDataError(
                ticker.symbol, f"Failed to parse daily history response: {e}"
            ) from e

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
