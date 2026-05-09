"""Deterministic mock market data adapter for E2E tests and local-fake mode.

This adapter is intended for use in environments where real network calls to
Alpha Vantage are undesirable: CI E2E runs (where the public ``demo`` key is
restricted to ``IBM`` with a 5/min, 25/day cap and is the largest single source
of historical CI flakiness), local-fake docker-compose stacks, and Phase C's
unattended scheduled-execution scenarios.

It differs from :class:`InMemoryMarketDataAdapter` in one important respect:
``InMemoryMarketDataAdapter`` raises :class:`TickerNotFoundError` for any
ticker the test has not explicitly seeded, which is the right behaviour for
unit tests that want to assert "no implicit data". E2E tests, on the other
hand, want a permissive backend that pretends to be a real market data
provider for *any* valid ticker symbol the user types into the trade form.

Prices are deterministic per ticker symbol so:

- Tests can compute expected portfolio values without external state
- Repeated test runs see identical numbers
- Different tickers see different prices (so insufficient-funds scenarios
  remain testable without hard-coding IBM)

The price range is tuned (USD 20.00 to USD 499.99) so that:

- A $1,000 portfolio cannot afford 1,000 shares of any ticker
  (1,000 x 20 = 20,000 > 1,000), preserving the insufficient-funds test
- A $30,000 portfolio can comfortably afford 2-20 shares of any ticker
  (20 x 499.99 = 9,999 < 30,000)

Production code paths are unaffected: this adapter is selected only when
``MARKET_DATA_PROVIDER=mock`` (or ``in_memory``) is set in the environment.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from hashlib import sha256

from zebu.application.dtos.price_point import PricePoint
from zebu.application.exceptions import TickerNotFoundError
from zebu.domain.exceptions import InvalidTickerError
from zebu.domain.value_objects.money import Money
from zebu.domain.value_objects.ticker import Ticker

# Default tickers exposed via get_supported_tickers(). We keep this list short
# and well-known so the frontend's ticker autocomplete (if any) and the test
# fixtures see a stable set. The adapter still serves any valid ticker via
# get_current_price/get_price_at, regardless of whether it is in this list.
_DEFAULT_SUPPORTED_TICKERS: tuple[str, ...] = (
    "AAPL",
    "GOOGL",
    "IBM",
    "MSFT",
    "TSLA",
    "AMZN",
    "META",
    "NVDA",
    "JPM",
    "V",
)

# Price band for deterministic prices. Lower bound stays well above $0.01 so
# 1000 shares of any ticker still costs more than the smallest insufficient-
# funds test deposit ($1,000); upper bound stays low enough that a 20-share
# buy fits in a $30,000 portfolio.
_MIN_PRICE_USD = Decimal("20.00")
_MAX_PRICE_USD = Decimal("499.99")


def _deterministic_price_for(symbol: str) -> Money:
    """Compute a deterministic USD price in the [20.00, 499.99] band for symbol.

    Uses a SHA-256 hash so the same symbol always maps to the same price across
    processes, and small symbol differences (e.g. ``MSFT`` vs ``MSFTX``)
    produce uncorrelated prices.

    Args:
        symbol: Already-normalized ticker symbol (uppercase).

    Returns:
        Money in USD with exactly 2 decimal places, in [20.00, 499.99].
    """
    digest = sha256(symbol.encode("utf-8")).digest()
    # Use first 4 bytes (32 bits) of digest as integer
    raw = int.from_bytes(digest[:4], byteorder="big")
    # Map into the price band, in cents, to get exactly 2 decimal places.
    span_cents = int((_MAX_PRICE_USD - _MIN_PRICE_USD) * 100) + 1
    offset_cents = raw % span_cents
    cents = int(_MIN_PRICE_USD * 100) + offset_cents
    amount = Decimal(cents) / Decimal(100)
    return Money(amount, "USD")


class DeterministicMockMarketDataAdapter:
    """Permissive in-memory MarketDataPort for E2E tests and fake-stack runs.

    This adapter satisfies :class:`MarketDataPort` for any valid ticker symbol,
    returning deterministic prices derived from a hash of the symbol. Unlike
    :class:`InMemoryMarketDataAdapter`, it does *not* require pre-seeding;
    calling ``get_current_price(Ticker("ANY"))`` returns a price.

    The only failure mode for the price-fetch methods is an invalid ticker
    symbol (e.g. malformed input), which surfaces as :class:`TickerNotFoundError`
    to keep the surface API-compatible with the production adapter.

    The supported-tickers list is a fixed set of common symbols so consumers
    that rely on ``get_supported_tickers()`` see a stable, plausible response.
    """

    def __init__(
        self,
        supported_tickers: tuple[str, ...] = _DEFAULT_SUPPORTED_TICKERS,
    ) -> None:
        """Initialize with an optional supported-ticker allowlist.

        Args:
            supported_tickers: Symbols returned from ``get_supported_tickers()``.
                Does not restrict the price-fetch methods, which serve any
                valid symbol.
        """
        self._supported_tickers: tuple[str, ...] = supported_tickers

    async def get_current_price(self, ticker: Ticker) -> PricePoint:
        """Return a deterministic current price for the given ticker.

        Args:
            ticker: Stock ticker (already validated by the value object).

        Returns:
            PricePoint with deterministic price, timestamped 1 minute ago to
            satisfy "at or before now" semantics used elsewhere.
        """
        return self._build_price_point(ticker, datetime.now(UTC) - timedelta(minutes=1))

    async def get_batch_prices(self, tickers: list[Ticker]) -> dict[Ticker, PricePoint]:
        """Return deterministic prices for every ticker in the batch.

        Args:
            tickers: List of tickers to price.

        Returns:
            Mapping from each input ticker to its deterministic PricePoint.
            Never partial: this adapter does not simulate API failures.
        """
        now_minus_one = datetime.now(UTC) - timedelta(minutes=1)
        return {
            ticker: self._build_price_point(ticker, now_minus_one) for ticker in tickers
        }

    async def get_price_at(self, ticker: Ticker, timestamp: datetime) -> PricePoint:
        """Return a deterministic price observed at the requested timestamp.

        For a deterministic mock, the historical price equals the current
        price; ``timestamp`` is echoed back verbatim so backtests and
        as_of-priced trades behave consistently.

        Args:
            ticker: Stock ticker.
            timestamp: Requested observation time (must be UTC-aware).

        Returns:
            PricePoint with the deterministic price at the requested timestamp.

        Raises:
            ValueError: If ``timestamp`` is naive.
        """
        if timestamp.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware (UTC)")
        return self._build_price_point(ticker, timestamp)

    async def get_price_history(
        self,
        ticker: Ticker,
        start: datetime,
        end: datetime,
        interval: str = "1day",
    ) -> list[PricePoint]:
        """Return a daily-spaced history of deterministic prices.

        For a deterministic mock, every observation in the range carries the
        same hash-derived price. Volume is not synthesised; this is enough for
        the rendering paths in E2E tests that just need "some history exists".

        Args:
            ticker: Stock ticker.
            start: Inclusive start of range (must be UTC).
            end: Inclusive end of range (must be UTC).
            interval: Interval label; the adapter serves "1day" only.

        Returns:
            List of PricePoint instances at daily cadence in [start, end].
            Empty list if start > end. Empty list for non-"1day" intervals
            (matches the spirit of an E2E mock — keep it simple).

        Raises:
            ValueError: If ``end`` is before ``start``.
        """
        if end < start:
            raise ValueError(f"end ({end}) must not be before start ({start})")
        if interval != "1day":
            return []

        history: list[PricePoint] = []
        current = start
        while current <= end:
            history.append(self._build_price_point(ticker, current, interval=interval))
            current = current + timedelta(days=1)
        return history

    async def get_supported_tickers(self) -> list[Ticker]:
        """Return the configured list of supported tickers.

        Returns:
            List of Ticker objects derived from the constructor argument.
        """
        out: list[Ticker] = []
        for symbol in self._supported_tickers:
            try:
                out.append(Ticker(symbol))
            except InvalidTickerError:
                # Skip any malformed entries silently rather than raise on
                # startup; the invariant is that the *API surface* always
                # returns a valid list.
                continue
        return out

    def _build_price_point(
        self,
        ticker: Ticker,
        timestamp: datetime,
        interval: str = "real-time",
    ) -> PricePoint:
        """Construct a PricePoint with the deterministic price for ticker.

        Args:
            ticker: Stock ticker.
            timestamp: Observation timestamp (must be UTC-aware).
            interval: Interval label for the PricePoint.

        Returns:
            PricePoint with the deterministic price at the requested timestamp.

        Raises:
            TickerNotFoundError: If the ticker symbol is not a valid identifier.
        """
        symbol = ticker.symbol
        if not symbol:
            # Defensive: Ticker() validates non-empty already, but make the
            # error explicit at the adapter boundary so any future loosening
            # of Ticker rules does not silently produce garbage prices.
            raise TickerNotFoundError(symbol)

        price = _deterministic_price_for(symbol)
        return PricePoint(
            ticker=ticker,
            price=price,
            timestamp=timestamp,
            source="database",
            interval=interval,
        )
