"""Application layer exceptions.

Application layer exceptions represent errors that occur during use case execution,
including issues with external data sources and integration failures.
"""

from datetime import date
from typing import Literal

from zebu.domain.value_objects.ticker import Ticker

# Reason taxonomy for a per-ticker pricing miss surfaced via
# :class:`PartialPricingError`. ``ticker_not_found`` mirrors the domain
# exception of the same name (ticker is invalid); ``market_data_unavailable``
# covers transient adapter failures (rate limit / network / cache miss).
PartialPricingReason = Literal[
    "ticker_not_found",
    "market_data_unavailable",
]


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


class IncompleteHistoricalDataError(MarketDataError):
    """Raised when historical price data covers only a subset of the requested range.

    Phase J (Task #212 Layer 3) — lazy backfill at the API boundary.

    Distinct from :class:`TickerNotFoundError` (the ticker is invalid) and
    :class:`MarketDataUnavailableError` (a transient failure with no
    cached data): the ticker IS valid and we DO have some data, but the
    returned coverage is a strict subset of what the caller asked for.

    When this is raised, the AV adapter has already enqueued a high-priority
    :class:`BackfillTask` for the missing window (idempotent — duplicate
    pending/running tasks for the same range are skipped). The API layer
    surfaces this to clients as ``503 Service Unavailable`` with a
    structured "fetching" body + ``Retry-After`` header so callers know
    the data is being healed in the background.

    Attributes:
        ticker: The ticker whose history was incomplete.
        requested_range: The ``(start, end)`` date window the caller
            asked for.
        available_range: The ``(first, last)`` date window the adapter
            could actually return, or ``None`` if there was no data at
            all for the ticker yet (still partial because we'd otherwise
            raise :class:`TickerNotFoundError`).
        missing_days_count: Calendar-day count of the missing slice.
            Calendar days (not trading days) — chosen for cheapness and
            because the caller mostly cares about order of magnitude.
        message: Human-readable error description.
    """

    def __init__(
        self,
        ticker: Ticker,
        requested_range: tuple[date, date],
        available_range: tuple[date, date] | None,
        missing_days_count: int,
        message: str | None = None,
    ) -> None:
        """Initialize IncompleteHistoricalDataError.

        Args:
            ticker: Ticker whose history was incomplete.
            requested_range: ``(start, end)`` of the requested window.
            available_range: ``(first, last)`` of what we have, or ``None``
                if we have no data for this ticker yet.
            missing_days_count: Calendar-day count of the missing window.
            message: Optional human-readable override.
        """
        self.ticker = ticker
        self.requested_range = requested_range
        self.available_range = available_range
        self.missing_days_count = missing_days_count
        if message is None:
            req_start, req_end = requested_range
            if available_range is None:
                message = (
                    f"No historical data yet for {ticker.symbol}; "
                    f"requested {req_start} .. {req_end} "
                    f"({missing_days_count} day(s) missing). "
                    "A backfill has been queued."
                )
            else:
                avail_start, avail_end = available_range
                message = (
                    f"Incomplete historical data for {ticker.symbol}; "
                    f"requested {req_start} .. {req_end}, "
                    f"available {avail_start} .. {avail_end} "
                    f"({missing_days_count} day(s) missing). "
                    "A backfill has been queued."
                )
        super().__init__(message)


class PartialPricingError(MarketDataError):
    """Raised when current/previous prices cannot be resolved for every required ticker.

    Phase J (Task #214) — symmetric to :class:`IncompleteHistoricalDataError`
    but for the current-price (and previous-close) fetches that power
    portfolio balance queries. Previously, the
    :class:`GetPortfolioBalancesHandler` would silently drop any ticker whose
    price fetch raised :class:`TickerNotFoundError` /
    :class:`MarketDataUnavailableError`. As background prewarm + lazy backfill
    completed across successive polls, the dashboard saw the same portfolio's
    total jump (e.g. $656 → $7,756 → $11,789 → $13,922).

    The fix is to refuse to compute a balance when any required price is
    missing, and surface that as a structured "data is loading" response at
    the API boundary (503 + ``Retry-After``). Per Tim 2026-05-13: "prefer no
    number over a wrong number."

    Attributes:
        missing_tickers: Tickers whose current (or previous-close) price
            could not be resolved. Ordered for stable rendering.
        failed_reason: Per-ticker reason string from the
            :data:`PartialPricingReason` taxonomy.
        retry_after_seconds: Recommended client retry delay. Mirrors
            ``Retry-After`` at the HTTP layer.
        message: Human-readable error description.
    """

    def __init__(
        self,
        missing_tickers: list[Ticker],
        failed_reason: dict[Ticker, PartialPricingReason],
        retry_after_seconds: int = 5,
        message: str | None = None,
    ) -> None:
        """Initialize PartialPricingError.

        Args:
            missing_tickers: Tickers whose price could not be resolved.
            failed_reason: Per-ticker reason mapping. Must cover every
                entry in ``missing_tickers``.
            retry_after_seconds: Recommended client retry delay (default 5).
            message: Optional human-readable override.
        """
        self.missing_tickers = missing_tickers
        self.failed_reason = failed_reason
        self.retry_after_seconds = retry_after_seconds
        if message is None:
            symbols = ", ".join(t.symbol for t in missing_tickers)
            message = (
                f"Pricing unavailable for {symbols} — data is being fetched. "
                f"Retry in {retry_after_seconds} seconds."
            )
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
