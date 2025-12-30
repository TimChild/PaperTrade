"""PricePoint DTO for representing stock price observations."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from papertrade.domain.value_objects.money import Money
from papertrade.domain.value_objects.ticker import Ticker

# Valid data source identifiers
VALID_SOURCES = {"alpha_vantage", "cache", "database"}

# Valid interval types
VALID_INTERVALS = {"real-time", "1day", "1hour", "5min", "1min"}


@dataclass(frozen=True)
class PricePoint:
    """Represents a single price observation for a ticker at a specific point in time.

    PricePoint is an immutable DTO used to transfer price data between layers.
    It includes core price information and optional OHLCV (candlestick) data.

    Attributes:
        ticker: Stock ticker symbol
        price: Price at observation time
        timestamp: When price was observed (must be UTC)
        source: Data source identifier
        interval: Interval type for this price
        open: Opening price for interval (optional)
        high: Highest price in interval (optional)
        low: Lowest price in interval (optional)
        close: Closing price for interval (optional)
        volume: Trading volume (optional, non-negative)

    Raises:
        ValueError: If validation constraints are violated
    """

    ticker: Ticker
    price: Money
    timestamp: datetime
    source: str
    interval: str
    open: Money | None = None
    high: Money | None = None
    low: Money | None = None
    close: Money | None = None
    volume: int | None = None

    def __post_init__(self) -> None:
        """Validate PricePoint constraints after initialization."""
        # Validate source
        if self.source not in VALID_SOURCES:
            raise ValueError(
                f"Invalid source '{self.source}'. "
                f"Must be one of: {', '.join(sorted(VALID_SOURCES))}"
            )

        # Validate interval
        if self.interval not in VALID_INTERVALS:
            raise ValueError(
                f"Invalid interval '{self.interval}'. "
                f"Must be one of: {', '.join(sorted(VALID_INTERVALS))}"
            )

        # Validate timestamp is timezone-aware UTC
        if self.timestamp.tzinfo is None:
            raise ValueError(
                "Timestamp must be timezone-aware (UTC). Got naive datetime instead."
            )
        if self.timestamp.tzinfo != UTC:
            raise ValueError(
                f"Timestamp must be in UTC timezone. "
                f"Got timezone: {self.timestamp.tzinfo}"
            )

        # Validate price is positive (Money object already enforces numeric validity)
        if not self.price.is_positive():
            raise ValueError(f"Price must be positive, got: {self.price.amount}")

        # Collect all Money values for currency consistency check
        money_values = [self.price]
        if self.open is not None:
            money_values.append(self.open)
        if self.high is not None:
            money_values.append(self.high)
        if self.low is not None:
            money_values.append(self.low)
        if self.close is not None:
            money_values.append(self.close)

        # Validate all Money values have same currency
        currencies = {m.currency for m in money_values}
        if len(currencies) > 1:
            raise ValueError(
                f"All Money values must have the same currency. "
                f"Found: {', '.join(sorted(currencies))}"
            )

        # Validate OHLCV relationships if OHLCV data present
        if self.open is not None and self.high is not None and self.low is not None:
            # low <= open <= high
            if self.low > self.open:
                raise ValueError(
                    f"Low price ({self.low.amount}) cannot be greater than "
                    f"open price ({self.open.amount})"
                )
            if self.open > self.high:
                raise ValueError(
                    f"Open price ({self.open.amount}) cannot be greater than "
                    f"high price ({self.high.amount})"
                )

        if self.close is not None and self.high is not None and self.low is not None:
            # low <= close <= high
            if self.low > self.close:
                raise ValueError(
                    f"Low price ({self.low.amount}) cannot be greater than "
                    f"close price ({self.close.amount})"
                )
            if self.close > self.high:
                raise ValueError(
                    f"Close price ({self.close.amount}) cannot be greater than "
                    f"high price ({self.high.amount})"
                )

        # Validate volume is non-negative if present
        if self.volume is not None and self.volume < 0:
            raise ValueError(f"Volume must be non-negative, got: {self.volume}")

    def is_stale(self, max_age: timedelta) -> bool:
        """Check if this price observation is stale.

        Args:
            max_age: Maximum age before price is considered stale

        Returns:
            True if timestamp is older than max_age from now (UTC)
        """
        now = datetime.now(UTC)
        age = now - self.timestamp
        return age > max_age

    def with_source(self, new_source: str) -> "PricePoint":
        """Create a new PricePoint with different source.

        This is useful when returning cached data - the original PricePoint
        can be copied with source changed to "cache".

        Args:
            new_source: New source identifier (must be valid)

        Returns:
            New PricePoint with updated source

        Raises:
            ValueError: If new_source is not valid
        """
        if new_source not in VALID_SOURCES:
            raise ValueError(
                f"Invalid source '{new_source}'. "
                f"Must be one of: {', '.join(sorted(VALID_SOURCES))}"
            )

        return PricePoint(
            ticker=self.ticker,
            price=self.price,
            timestamp=self.timestamp,
            source=new_source,
            interval=self.interval,
            open=self.open,
            high=self.high,
            low=self.low,
            close=self.close,
            volume=self.volume,
        )

    def __str__(self) -> str:
        """Return string representation.

        Returns:
            Formatted string like "AAPL @ $150.25 as of 2025-12-28 14:30:00 UTC (source: alpha_vantage)"
        """
        return (
            f"{self.ticker} @ {self.price} as of {self.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')} "
            f"(source: {self.source})"
        )

    def __repr__(self) -> str:
        """Return repr for debugging.

        Returns:
            String like "PricePoint(ticker=Ticker('AAPL'), price=Money(...), ...)"
        """
        return (
            f"PricePoint(ticker={self.ticker!r}, price={self.price!r}, "
            f"timestamp={self.timestamp!r}, source={self.source!r}, "
            f"interval={self.interval!r})"
        )
