"""MarketDataPort interface for fetching market price data.

This port defines the contract for accessing market data in the application layer.
Adapters (e.g., Alpha Vantage, database, cache) implement this interface to provide
price data from various sources.
"""

from datetime import datetime
from typing import Protocol

from zebu.application.dtos.price_point import PricePoint
from zebu.domain.value_objects.ticker import Ticker


class MarketDataPort(Protocol):
    """Port interface for fetching market data.

    This Protocol defines the contract that all market data adapters must implement.
    It provides read-only access to stock prices, both current and historical.

    Design Philosophy:
    - Read-only: Market data is external; we don't change it
    - Async: Network/database calls may be slow
    - Time-aware: Support historical queries for backtesting
    - Source-transparent: Caller knows if data is cached/stale via PricePoint.source
    - Extensible: Easy to add new methods in future phases

    All methods are async to support I/O operations (network, database).
    All timestamps must be in UTC timezone.

    Errors:
        TickerNotFoundError: Ticker doesn't exist in data source
        MarketDataUnavailableError: Cannot fetch data
            (API down, rate limited, network error)
        InvalidPriceDataError: Data received but invalid/corrupted
    """

    async def get_current_price(self, ticker: Ticker) -> PricePoint:
        """Get the most recent available price for a ticker.

        This method returns the latest price available, which may be:
        - Real-time (if market is open and API is available)
        - Last closing price (if market is closed)
        - Cached data (if API is rate limited or unavailable)

        The PricePoint.timestamp indicates when the price was observed.
        The PricePoint.source indicates where the data came from
        ("alpha_vantage", "cache", etc).

        Args:
            ticker: Stock ticker symbol to get price for

        Returns:
            PricePoint with latest available price

        Raises:
            TickerNotFoundError: Ticker doesn't exist in data source
            MarketDataUnavailableError: Cannot fetch price
                (API down, rate limited, network error)

        Performance Target:
            <100ms for cache hit
            <2s for API call

        Example:
            >>> ticker = Ticker("AAPL")
            >>> price_point = await market_data.get_current_price(ticker)
            >>> print(f"AAPL is trading at {price_point.price}")
            >>> if price_point.is_stale(timedelta(minutes=15)):
            ...     print("Warning: Price data is stale")
        """
        ...

    async def get_batch_prices(self, tickers: list[Ticker]) -> dict[Ticker, PricePoint]:
        """Get current prices for multiple tickers in a single batch request.

        This method optimizes price fetching for multiple tickers by:
        - Checking cache for all tickers first
        - Only fetching uncached tickers from API
        - Returning partial results if some tickers fail

        The method never raises exceptions. Instead, failed tickers are simply
        excluded from the result dict. Callers should check which tickers are
        in the result.

        Args:
            tickers: List of stock ticker symbols to get prices for

        Returns:
            Dictionary mapping tickers to their price points.
            Only includes tickers for which prices were successfully fetched.
            Missing tickers indicate failures (ticker not found, API unavailable, etc).

        Performance Target:
            <200ms for all cache hits
            <5s for mixed cache/API calls

        Example:
            >>> tickers = [Ticker("AAPL"), Ticker("GOOGL"), Ticker("MSFT")]
            >>> prices = await market_data.get_batch_prices(tickers)
            >>> if Ticker("AAPL") in prices:
            ...     print(f"AAPL: {prices[Ticker('AAPL')].price}")
            >>> else:
            ...     print("AAPL price unavailable")
        """
        ...

    async def get_price_at(self, ticker: Ticker, timestamp: datetime) -> PricePoint:
        """Get the price for a ticker at a specific point in time.

        This method is primarily for backtesting and historical
        analysis (Phase 3). It returns the price closest to the requested
        timestamp within a reasonable window.

        If an exact match for the timestamp is not available, this method returns
        the closest price within ±1 hour. The actual observation time is indicated
        by PricePoint.timestamp.

        Args:
            ticker: Stock ticker symbol
            timestamp: When to get the price (must be UTC)

        Returns:
            PricePoint with price closest to requested timestamp

        Raises:
            TickerNotFoundError: Ticker doesn't exist
            MarketDataUnavailableError: No data available for that time period,
                or timestamp is in the future, or timestamp is before available data

        Performance Target:
            <500ms for database query

        Semantics:
            - Returns closest available price within ±1 hour window
            - Raises MarketDataUnavailableError if timestamp is in future
            - Raises MarketDataUnavailableError if timestamp before available data
            - Returned PricePoint.timestamp shows actual observation time
            - Source typically "database" for historical queries

        Example:
            >>> ticker = Ticker("AAPL")
            >>> past_time = datetime(2025, 1, 1, 14, 30, tzinfo=timezone.utc)
            >>> price_point = await market_data.get_price_at(ticker, past_time)
            >>> print(f"AAPL was {price_point.price} at {price_point.timestamp}")
        """
        ...

    async def get_price_history(
        self,
        ticker: Ticker,
        start: datetime,
        end: datetime,
        interval: str = "1day",
    ) -> list[PricePoint]:
        """Get price history over a time range.

        This method returns a list of price observations covering the
        requested time range. Useful for:
        - Generating price charts
        - Technical analysis
        - Performance calculations

        The results are ordered chronologically (oldest first).
        Each PricePoint may include OHLCV (candlestick) data when available.

        Args:
            ticker: Stock ticker symbol
            start: Start of time range (inclusive, must be UTC)
            end: End of time range (inclusive, must be UTC)
            interval: Price interval type (default: "1day")
                Options: "1min", "5min", "1hour", "1day"

        Returns:
            List of PricePoint objects, ordered chronologically (oldest first).
            Returns empty list if no data available in range (not an error).

        Raises:
            TickerNotFoundError: Ticker doesn't exist
            MarketDataUnavailableError: Insufficient data for range
            ValueError: Invalid interval or end before start

        Performance Target:
            <1s for 1 year of daily data

        Interval Semantics:
            - "1day": One price per day (typically closing price)
            - "1hour": One price per hour during market hours
            - "5min": One price per 5 minutes (high frequency)
            - "1min": One price per minute (very high frequency, use with caution)

        Example:
            >>> ticker = Ticker("AAPL")
            >>> start = datetime(2025, 1, 1, tzinfo=timezone.utc)
            >>> end = datetime(2025, 1, 31, tzinfo=timezone.utc)
            >>> history = await market_data.get_price_history(
            ...     ticker, start, end, "1day"
            ... )
            >>> print(f"Got {len(history)} price points for January 2025")
        """
        ...

    async def get_supported_tickers(self) -> list[Ticker]:
        """Get list of tickers we have data for.

        This method returns all tickers for which we have ANY price data available.
        Useful for:
        - Search/autocomplete in frontend
        - Validating user input
        - Discovering available tickers

        The list may grow over time as users query new tickers or data is imported.

        Returns:
            List of Ticker objects for all supported tickers

        Raises:
            MarketDataUnavailableError: Cannot access ticker list

        Performance Target:
            <200ms (should be cached aggressively)

        Semantics:
            - Returns all tickers with ANY price data
            - May include tickers not currently tracked
            - List may grow as new tickers are queried
            - Should be cached as it changes infrequently

        Note:
            For Phase 2a, implementations may return empty list or hardcoded list.
            Phase 2b will implement this properly with database queries.

        Example:
            >>> tickers = await market_data.get_supported_tickers()
            >>> print(f"We have data for {len(tickers)} tickers")
            >>> if Ticker("AAPL") in tickers:
            ...     print("AAPL is supported")
        """
        ...
