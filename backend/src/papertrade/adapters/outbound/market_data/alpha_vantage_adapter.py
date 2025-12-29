"""Alpha Vantage adapter implementing MarketDataPort with rate limiting and caching.

This adapter implements a tiered caching strategy:
1. Tier 1 (Hot): Redis cache - Fast access to recently queried prices
2. Tier 2 (Warm): PostgreSQL - Historical price storage (stubbed for now)
3. Tier 3 (Cold): Alpha Vantage API - External data source (rate limited)
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

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


class AlphaVantageAdapter:
    """Alpha Vantage API adapter with tiered caching and rate limiting.
    
    Implements MarketDataPort protocol to fetch stock prices from Alpha Vantage.
    Uses Redis cache and rate limiter to minimize API calls and respect quotas.
    
    Attributes:
        rate_limiter: Token bucket rate limiter
        price_cache: Redis-backed price cache
        http_client: HTTP client for API requests
        api_key: Alpha Vantage API key
        base_url: Alpha Vantage API base URL
        timeout: Request timeout in seconds
        max_retries: Maximum retry attempts for transient errors
    """

    def __init__(
        self,
        rate_limiter: RateLimiter,
        price_cache: PriceCache,
        api_key: str,
        base_url: str = "https://www.alphavantage.co/query",
        timeout: float = 5.0,
        max_retries: int = 3,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        """Initialize Alpha Vantage adapter.
        
        Args:
            rate_limiter: Rate limiter for API quota management
            price_cache: Redis cache for price data
            api_key: Alpha Vantage API key
            base_url: API base URL (default: Alpha Vantage production)
            timeout: Request timeout in seconds (default: 5.0)
            max_retries: Maximum retry attempts (default: 3)
            http_client: Optional HTTP client (creates default if None)
        """
        self.rate_limiter = rate_limiter
        self.price_cache = price_cache
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.http_client = http_client or httpx.AsyncClient(timeout=timeout)

    async def get_current_price(self, ticker: Ticker) -> PricePoint:
        """Get the most recent available price for a ticker.
        
        Implements tiered caching strategy:
        1. Check Redis cache (fast)
        2. Check PostgreSQL (future - stubbed for now)
        3. Fetch from Alpha Vantage API (rate limited)
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            PricePoint with latest available price
            
        Raises:
            TickerNotFoundError: Ticker doesn't exist
            MarketDataUnavailableError: Cannot fetch price (API down, rate limited)
        """
        # Tier 1: Check Redis cache
        cached = await self.price_cache.get(ticker)
        if cached and not cached.is_stale(max_age=timedelta(hours=1)):
            return cached.with_source("cache")

        # Tier 2: Check PostgreSQL (stub - will implement in Task 021)
        # if self.price_repository:
        #     db_price = await self.price_repository.get_latest_price(ticker)
        #     if db_price and not db_price.is_stale(max_age=timedelta(hours=4)):
        #         await self.price_cache.set(db_price)  # Warm cache
        #         return db_price

        # Tier 3: Fetch from Alpha Vantage API
        # Check rate limiter
        if not await self.rate_limiter.can_make_request():
            # Serve stale data if available, else raise error
            if cached:
                return cached.with_source("cache")
            raise MarketDataUnavailableError(
                "Rate limit exceeded, no cached data available"
            )

        # Consume token and make API request
        if not await self.rate_limiter.consume_token():
            # Token consumed by another request between check and consume
            if cached:
                return cached.with_source("cache")
            raise MarketDataUnavailableError(
                "Rate limit exceeded, no cached data available"
            )

        try:
            price = await self._fetch_from_api(ticker)
        except (TickerNotFoundError, InvalidPriceDataError):
            # Don't serve stale data for invalid tickers
            raise
        except MarketDataUnavailableError:
            # API error - serve stale data if available
            if cached:
                return cached.with_source("cache")
            raise

        # Store in cache (and database when implemented)
        await self.price_cache.set(price)
        # if self.price_repository:
        #     await self.price_repository.upsert_price(price)

        return price

    async def get_price_at(self, ticker: Ticker, timestamp: datetime) -> PricePoint:
        """Get price at specific point in time (not implemented in Phase 2a).
        
        This method will be implemented in Phase 2b when historical data
        fetching is added.
        
        Args:
            ticker: Stock ticker symbol
            timestamp: When to get the price
            
        Raises:
            NotImplementedError: Not implemented in Phase 2a
        """
        raise NotImplementedError("Historical price queries not yet implemented")

    async def get_price_history(
        self,
        ticker: Ticker,
        start: datetime,
        end: datetime,
        interval: str = "1day",
    ) -> list[PricePoint]:
        """Get price history over time range (not implemented in Phase 2a).
        
        This method will be implemented in Phase 2b when historical data
        fetching is added.
        
        Args:
            ticker: Stock ticker symbol
            start: Start of time range
            end: End of time range
            interval: Price interval type
            
        Raises:
            NotImplementedError: Not implemented in Phase 2a
        """
        raise NotImplementedError("Historical price queries not yet implemented")

    async def get_supported_tickers(self) -> list[Ticker]:
        """Get list of supported tickers (not implemented in Phase 2a).
        
        This method will be implemented properly in Phase 2b with database
        integration. For now, returns empty list.
        
        Returns:
            Empty list (to be implemented)
        """
        return []

    async def _fetch_from_api(self, ticker: Ticker) -> PricePoint:
        """Fetch current price from Alpha Vantage API.
        
        Makes HTTP request to GLOBAL_QUOTE endpoint with retry logic.
        
        Args:
            ticker: Stock ticker to fetch
            
        Returns:
            PricePoint with fresh data from API
            
        Raises:
            TickerNotFoundError: Ticker doesn't exist
            MarketDataUnavailableError: API error or network failure
            InvalidPriceDataError: Malformed API response
        """
        url = self.base_url
        params = {
            "function": "GLOBAL_QUOTE",
            "symbol": ticker.symbol,
            "apikey": self.api_key,
        }

        last_exception: Exception | None = None

        # Retry loop with exponential backoff
        for attempt in range(self.max_retries):
            try:
                response = await self.http_client.get(url, params=params)
                response.raise_for_status()

                data = response.json()
                return self._parse_global_quote(ticker, data)

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    raise TickerNotFoundError(
                        ticker.symbol, "Ticker not found in Alpha Vantage"
                    )
                elif e.response.status_code == 429:
                    raise MarketDataUnavailableError("API rate limit exceeded")
                else:
                    last_exception = e
                    # Retry on other HTTP errors
                    if attempt < self.max_retries - 1:
                        await self._backoff(attempt)
                        continue

            except httpx.RequestError as e:
                last_exception = e
                # Retry on network errors
                if attempt < self.max_retries - 1:
                    await self._backoff(attempt)
                    continue

            except (KeyError, ValueError, InvalidPriceDataError) as e:
                # Don't retry on data parsing errors
                raise InvalidPriceDataError(
                    ticker.symbol, f"Invalid API response: {e!s}"
                )

        # All retries exhausted
        raise MarketDataUnavailableError(
            f"API request failed after {self.max_retries} attempts: {last_exception}"
        )

    async def _backoff(self, attempt: int) -> None:
        """Exponential backoff delay.
        
        Args:
            attempt: Current attempt number (0-indexed)
        """
        import asyncio

        delay = 2**attempt  # 1s, 2s, 4s, etc.
        await asyncio.sleep(delay)

    def _parse_global_quote(
        self, ticker: Ticker, data: dict[str, Any]
    ) -> PricePoint:
        """Parse Alpha Vantage GLOBAL_QUOTE response.
        
        Args:
            ticker: Stock ticker
            data: JSON response from API
            
        Returns:
            PricePoint parsed from response
            
        Raises:
            TickerNotFoundError: Response indicates ticker not found
            InvalidPriceDataError: Malformed response or invalid data
        """
        # Check for error messages in response
        if "Error Message" in data:
            raise TickerNotFoundError(
                ticker.symbol, f"Alpha Vantage error: {data['Error Message']}"
            )

        if "Note" in data:
            # API rate limit message in response body
            raise MarketDataUnavailableError(
                f"Alpha Vantage rate limit: {data['Note']}"
            )

        # Extract Global Quote object
        if "Global Quote" not in data:
            raise InvalidPriceDataError(
                ticker.symbol, "Missing 'Global Quote' in API response"
            )

        quote = data["Global Quote"]

        # Check for empty quote (invalid ticker)
        if not quote or len(quote) == 0:
            raise TickerNotFoundError(
                ticker.symbol, "Ticker not found (empty quote)"
            )

        # Parse required fields
        try:
            symbol = quote.get("01. symbol", "")
            if symbol != ticker.symbol:
                raise InvalidPriceDataError(
                    ticker.symbol,
                    f"Symbol mismatch: expected {ticker.symbol}, got {symbol}",
                )

            price_str = quote.get("05. price", "")
            if not price_str:
                raise InvalidPriceDataError(ticker.symbol, "Missing price field")

            price = Money(amount=Decimal(price_str), currency="USD")

            # Parse timestamp (latest trading day)
            trading_day_str = quote.get("07. latest trading day", "")
            if not trading_day_str:
                raise InvalidPriceDataError(
                    ticker.symbol, "Missing trading day field"
                )

            # Alpha Vantage returns date only, assume market close time (4 PM ET = 9 PM UTC)
            timestamp = datetime.fromisoformat(trading_day_str).replace(
                hour=21, minute=0, second=0, tzinfo=timezone.utc
            )

            # Parse optional OHLCV fields
            open_str = quote.get("02. open")
            high_str = quote.get("03. high")
            low_str = quote.get("04. low")
            volume_str = quote.get("06. volume")
            prev_close_str = quote.get("08. previous close")

            return PricePoint(
                ticker=ticker,
                price=price,
                timestamp=timestamp,
                source="alpha_vantage",
                interval="1day",
                open=(
                    Money(amount=Decimal(open_str), currency="USD")
                    if open_str
                    else None
                ),
                high=(
                    Money(amount=Decimal(high_str), currency="USD")
                    if high_str
                    else None
                ),
                low=(
                    Money(amount=Decimal(low_str), currency="USD")
                    if low_str
                    else None
                ),
                close=(
                    Money(amount=Decimal(prev_close_str), currency="USD")
                    if prev_close_str
                    else None
                ),
                volume=int(volume_str) if volume_str else None,
            )

        except (KeyError, ValueError, Decimal.InvalidOperation) as e:
            raise InvalidPriceDataError(
                ticker.symbol, f"Failed to parse API response: {e!s}"
            )


async def create_alpha_vantage_adapter(
    redis_url: str = "redis://localhost:6379",
    api_key: str = "",
    calls_per_minute: int = 5,
    calls_per_day: int = 500,
) -> AlphaVantageAdapter:
    """Factory function to create Alpha Vantage adapter with dependencies.
    
    Args:
        redis_url: Redis connection URL
        api_key: Alpha Vantage API key
        calls_per_minute: Rate limit per minute
        calls_per_day: Rate limit per day
        
    Returns:
        Configured AlphaVantageAdapter instance
    """
    from papertrade.infrastructure.cache.price_cache import create_price_cache
    from papertrade.infrastructure.rate_limiter import create_rate_limiter

    rate_limiter = await create_rate_limiter(
        redis_url=redis_url,
        calls_per_minute=calls_per_minute,
        calls_per_day=calls_per_day,
    )

    price_cache = await create_price_cache(redis_url=redis_url)

    return AlphaVantageAdapter(
        rate_limiter=rate_limiter,
        price_cache=price_cache,
        api_key=api_key,
    )
