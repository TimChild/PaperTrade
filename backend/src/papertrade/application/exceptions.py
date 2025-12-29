"""Application layer exceptions.

Application layer exceptions represent errors that occur during use case execution,
including issues with external data sources and integration failures.
"""


class MarketDataError(Exception):
    """Base exception for all market data related errors.

    All market data exceptions inherit from this base class to allow
    catching all market data errors with a single except clause.

    Attributes:
        message: Human-readable error description
    """

    def __init__(self, message: str) -> None:
        """Initialize MarketDataError.

        Args:
            message: Human-readable error description
        """
        self.message = message
        super().__init__(message)


class TickerNotFoundError(MarketDataError):
    """Raised when ticker symbol doesn't exist in data source.

    This error indicates that the requested ticker symbol is not recognized
    by the market data provider. This could mean:
    - The ticker symbol is invalid
    - The ticker is not supported by the data source
    - The ticker has been delisted

    Attributes:
        ticker: The ticker symbol that was not found
        message: Human-readable error description
    """

    def __init__(self, ticker: str, message: str | None = None) -> None:
        """Initialize TickerNotFoundError.

        Args:
            ticker: The ticker symbol that was not found
            message: Optional custom error message
        """
        self.ticker = ticker
        if message is None:
            message = f"Ticker not found: {ticker}"
        super().__init__(message)


class MarketDataUnavailableError(MarketDataError):
    """Raised when market data cannot be fetched for temporary reasons.

    This error indicates a temporary failure to access market data, such as:
    - API rate limits exceeded
    - Network connectivity issues
    - External service downtime
    - Cache miss with no fallback available

    The caller may retry the request after some time.

    Attributes:
        reason: Specific cause of unavailability
        message: Human-readable error description
    """

    def __init__(self, reason: str, message: str | None = None) -> None:
        """Initialize MarketDataUnavailableError.

        Args:
            reason: Specific cause (e.g., "API rate limit exceeded", "Network timeout")
            message: Optional custom error message
        """
        self.reason = reason
        if message is None:
            message = f"Market data unavailable: {reason}"
        super().__init__(message)


class InvalidPriceDataError(MarketDataError):
    """Raised when market data is received but invalid or corrupted.

    This error indicates that the data source returned data, but it's malformed
    or violates business rules:
    - Negative prices
    - Invalid OHLCV relationships
    - Missing required fields
    - Corrupted data format

    Attributes:
        ticker: Which ticker had invalid data
        reason: What was invalid about the data
        message: Human-readable error description
    """

    def __init__(self, ticker: str, reason: str, message: str | None = None) -> None:
        """Initialize InvalidPriceDataError.

        Args:
            ticker: Which ticker had invalid data
            reason: What was invalid about the data
            message: Optional custom error message
        """
        self.ticker = ticker
        self.reason = reason
        if message is None:
            message = f"Invalid price data for {ticker}: {reason}"
        super().__init__(message)
