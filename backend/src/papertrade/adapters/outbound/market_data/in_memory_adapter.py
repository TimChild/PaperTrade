"""In-memory market data adapter for testing."""

from datetime import datetime, timedelta

from papertrade.application.dtos.price_point import PricePoint
from papertrade.application.exceptions import (
    MarketDataUnavailableError,
    TickerNotFoundError,
)
from papertrade.domain.value_objects.ticker import Ticker


class InMemoryMarketDataAdapter:
    """In-memory implementation of MarketDataPort for testing.

    This adapter stores price data in memory and is designed for testing purposes.
    It allows easy seeding of test data and provides a simple implementation of
    the MarketDataPort interface.

    The adapter stores prices in a dictionary keyed by ticker symbol, with each
    ticker having a list of PricePoint objects ordered chronologically.

    Attributes:
        _prices: Dict mapping ticker symbols to lists of PricePoint objects
    """

    def __init__(self) -> None:
        """Initialize an empty InMemoryMarketDataAdapter."""
        self._prices: dict[str, list[PricePoint]] = {}

    def seed_price(self, price_point: PricePoint) -> None:
        """Add a single price observation to storage.

        Args:
            price_point: PricePoint to add
        """
        ticker_symbol = price_point.ticker.symbol
        if ticker_symbol not in self._prices:
            self._prices[ticker_symbol] = []
        self._prices[ticker_symbol].append(price_point)
        # Keep list sorted by timestamp
        self._prices[ticker_symbol].sort(key=lambda p: p.timestamp)

    def seed_prices(self, price_points: list[PricePoint]) -> None:
        """Add multiple price observations to storage.

        Args:
            price_points: List of PricePoint objects to add
        """
        for price_point in price_points:
            self.seed_price(price_point)

    def clear(self) -> None:
        """Remove all price data from storage."""
        self._prices.clear()

    async def get_current_price(self, ticker: Ticker) -> PricePoint:
        """Get the most recent price for a ticker.

        Args:
            ticker: Stock ticker symbol

        Returns:
            PricePoint with most recent price

        Raises:
            TickerNotFoundError: If ticker not in storage
        """
        ticker_symbol = ticker.symbol
        if ticker_symbol not in self._prices or not self._prices[ticker_symbol]:
            raise TickerNotFoundError(ticker_symbol)

        # Return most recent price (list is sorted by timestamp)
        return self._prices[ticker_symbol][-1]

    async def get_batch_prices(self, tickers: list[Ticker]) -> dict[Ticker, PricePoint]:
        """Get current prices for multiple tickers.

        Args:
            tickers: List of stock ticker symbols

        Returns:
            Dictionary mapping tickers to their most recent price points.
            Only includes tickers that exist in storage.

        Example:
            >>> tickers = [Ticker("AAPL"), Ticker("GOOGL")]
            >>> prices = await adapter.get_batch_prices(tickers)
        """
        result: dict[Ticker, PricePoint] = {}
        for ticker in tickers:
            try:
                price = await self.get_current_price(ticker)
                result[ticker] = price
            except TickerNotFoundError:
                # Skip tickers without data
                continue
        return result

    async def get_price_at(self, ticker: Ticker, timestamp: datetime) -> PricePoint:
        """Get price closest to specified timestamp.

        Finds the price observation closest to the requested timestamp
        within a ±1 hour window.

        Args:
            ticker: Stock ticker symbol
            timestamp: Requested time (UTC)

        Returns:
            PricePoint closest to requested timestamp

        Raises:
            TickerNotFoundError: If ticker not in storage
            MarketDataUnavailableError: If no price found within ±1 hour window
        """
        ticker_symbol = ticker.symbol
        if ticker_symbol not in self._prices or not self._prices[ticker_symbol]:
            raise TickerNotFoundError(ticker_symbol)

        prices = self._prices[ticker_symbol]

        # Find closest price within ±1 hour window
        max_window = timedelta(hours=1)
        closest_price = None
        closest_diff = None

        for price in prices:
            diff = abs(price.timestamp - timestamp)
            if diff <= max_window and (closest_diff is None or diff < closest_diff):
                closest_price = price
                closest_diff = diff

        if closest_price is None:
            raise MarketDataUnavailableError(
                f"No price data found for {ticker_symbol} within ±1 hour of {timestamp}"
            )

        return closest_price

    async def get_price_history(
        self,
        ticker: Ticker,
        start: datetime,
        end: datetime,
        interval: str = "1day",
    ) -> list[PricePoint]:
        """Get price history over time range.

        Args:
            ticker: Stock ticker symbol
            start: Start of range (inclusive, UTC)
            end: End of range (inclusive, UTC)
            interval: Price interval (currently not filtered, returns all data in range)

        Returns:
            List of PricePoint objects in chronological order

        Raises:
            TickerNotFoundError: If ticker not in storage
            ValueError: If end is before start
        """
        if end < start:
            raise ValueError(f"End time ({end}) cannot be before start time ({start})")

        ticker_symbol = ticker.symbol
        if ticker_symbol not in self._prices:
            raise TickerNotFoundError(ticker_symbol)

        prices = self._prices[ticker_symbol]

        # Filter prices within date range (inclusive)
        result = [
            price
            for price in prices
            if start <= price.timestamp <= end and price.interval == interval
        ]

        return result

    async def get_supported_tickers(self) -> list[Ticker]:
        """Get list of all tickers in storage.

        Returns:
            List of Ticker objects for all tickers with data
        """
        return [Ticker(symbol) for symbol in self._prices]
