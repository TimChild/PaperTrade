"""Data-coverage query — per-ticker price-history coverage summary.

Phase J (Task #212 Layer 4) — operator-facing data freshness UI.

Given the union of ``ticker_watchlist`` (active) + recently-traded
tickers + any ticker with rows in ``price_history``, emit one entry per
ticker carrying:

* ``coverage_start`` / ``coverage_end`` — first and last bar timestamps
  in ``price_history``.
* ``last_refresh`` — most-recent ``created_at`` on any
  ``price_history`` row for that ticker (when the bar was inserted /
  upserted, distinct from the bar's own ``timestamp``).
* ``gap_days_count`` — number of NYSE/NASDAQ trading days inside
  ``[coverage_start, coverage_end]`` that do NOT have a ``daily`` bar
  in ``price_history``. Pre-``coverage_start`` data is explicitly NOT
  a gap — we only count interior holes, since "we just don't have
  data older than 2019" is a deliberate truncation, not a gap.
* ``is_active`` — ``True`` when the ticker is in the watchlist OR has
  been traded in the active-tickers window (default 30 days). Matches
  the union used by ``scheduler.refresh_active_stocks``.

Tickers with no ``price_history`` rows but in the active-set are
returned with ``coverage_start = coverage_end = last_refresh = None``
and ``gap_days_count = 0`` — the page renders them so the operator
sees "we know this ticker is active but we have zero bars for it"
rather than them being invisible.

Layering: this is a pure application-layer query handler. The
``SessionDep``-bound implementation lives at the endpoint
(``adapters/inbound/api/admin_data_coverage.py``); the handler itself
accepts the session via constructor injection so it stays unit-testable
against the in-memory SQLite fixture used by the test suite.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import func
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from zebu.adapters.outbound.database.models import TransactionModel
from zebu.adapters.outbound.models.price_history import PriceHistoryModel
from zebu.adapters.outbound.models.ticker_watchlist import TickerWatchlistModel
from zebu.domain.value_objects.ticker import Ticker
from zebu.infrastructure.market_calendar import MarketCalendar

# Match the scheduler's default window (see
# ``zebu.infrastructure.scheduler.SchedulerConfig.active_stock_days``).
DEFAULT_ACTIVE_WINDOW_DAYS: int = 30

# Only count ``daily`` bars when computing coverage. Intraday rows
# (1min, 5min, 1hour) populate the same table but represent a different
# product surface; coverage policy is "we have THIS ticker's daily
# bars for THIS date range".
_DAILY_INTERVAL: str = "1day"


@dataclass(frozen=True)
class TickerCoverage:
    """Per-ticker coverage summary.

    Attributes:
        ticker: Stock ticker symbol (uppercase).
        coverage_start: Earliest daily bar's date in ``price_history``,
            or ``None`` if no rows.
        coverage_end: Latest daily bar's date in ``price_history``, or
            ``None`` if no rows.
        last_refresh: Most-recent ``created_at`` across daily rows for
            this ticker, or ``None`` if no rows.
        gap_days_count: Trading days in ``[coverage_start, coverage_end]``
            that have no daily bar. ``0`` when there are no rows (no
            interior to have gaps in) or when coverage is complete.
        is_active: ``True`` when the ticker is in the watchlist OR has
            been traded in the active-tickers window.
    """

    ticker: Ticker
    coverage_start: date | None
    coverage_end: date | None
    last_refresh: datetime | None
    gap_days_count: int
    is_active: bool


@dataclass(frozen=True)
class DataCoverageQuery:
    """Input for the data-coverage query.

    Attributes:
        active_window_days: How many days back to look for
            "recently-traded" tickers when computing ``is_active``.
            Defaults to :data:`DEFAULT_ACTIVE_WINDOW_DAYS` (30) to
            match the scheduler.
    """

    active_window_days: int = DEFAULT_ACTIVE_WINDOW_DAYS


@dataclass(frozen=True)
class DataCoverageResult:
    """Output of the data-coverage query.

    Attributes:
        tickers: Per-ticker coverage rows, sorted by ticker symbol
            ascending so the operator sees a stable order across polls.
    """

    tickers: list[TickerCoverage]


class DataCoverageQueryHandler:
    """Compute per-ticker price-history coverage summaries.

    The handler iterates over the union of (watchlist tickers) +
    (recently-traded tickers) + (tickers with any price_history rows)
    and emits one :class:`TickerCoverage` per ticker. The trading-day
    gap calculation uses :class:`MarketCalendar` so weekends and US
    market holidays are correctly excluded.

    Performance note: the implementation aggregates per ticker via SQL
    (``MIN(timestamp)``, ``MAX(timestamp)``, ``MAX(created_at)``,
    ``COUNT(DISTINCT date(timestamp))``) to keep the round-trip count
    bounded — one aggregate query for all tickers + one watchlist read
    + one recent-transactions read. For thousand-ticker volumes this
    keeps the endpoint well under the 30-second poll budget.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialise with an async DB session.

        Args:
            session: Async session bound to the current unit of work.
                Reads only; no commits issued.
        """
        self._session = session

    async def execute(self, query: DataCoverageQuery) -> DataCoverageResult:
        """Run the query.

        Args:
            query: Query parameters (active-window length).

        Returns:
            One :class:`TickerCoverage` per known ticker, sorted by
            symbol ascending.

        Raises:
            ValueError: If ``query.active_window_days`` is < 1.
        """
        if query.active_window_days < 1:
            raise ValueError(
                f"active_window_days must be >= 1, got {query.active_window_days}"
            )

        # 1. Active-set: watchlist ∪ recently-traded.
        active_tickers = await self._active_tickers(query.active_window_days)

        # 2. Aggregates per ticker across price_history (daily bars).
        aggregates = await self._coverage_aggregates()

        # 3. Distinct trading days per ticker, for the gap computation.
        covered_days = await self._covered_days_by_ticker()

        # 4. Union of ticker keys: active-set + any ticker that has
        #    bars in price_history. Bars-without-active-flag still get
        #    surfaced (e.g. an old transaction whose ticker has dropped
        #    off the watchlist) so the operator can prune coverage.
        all_tickers: set[str] = set(active_tickers) | set(aggregates.keys())

        rows: list[TickerCoverage] = []
        for symbol in sorted(all_tickers):
            agg = aggregates.get(symbol)
            covered = covered_days.get(symbol, frozenset())
            if agg is None:
                rows.append(
                    TickerCoverage(
                        ticker=Ticker(symbol),
                        coverage_start=None,
                        coverage_end=None,
                        last_refresh=None,
                        gap_days_count=0,
                        is_active=symbol in active_tickers,
                    )
                )
                continue

            coverage_start = agg.first_bar_date
            coverage_end = agg.last_bar_date
            gap_days_count = _compute_gap_days(coverage_start, coverage_end, covered)
            rows.append(
                TickerCoverage(
                    ticker=Ticker(symbol),
                    coverage_start=coverage_start,
                    coverage_end=coverage_end,
                    last_refresh=_ensure_aware(agg.last_refresh),
                    gap_days_count=gap_days_count,
                    is_active=symbol in active_tickers,
                )
            )

        return DataCoverageResult(tickers=rows)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    async def _active_tickers(self, window_days: int) -> set[str]:
        """Set of "active" ticker symbols: watchlist ∪ recently-traded."""
        watchlist_stmt = select(TickerWatchlistModel.ticker).where(
            TickerWatchlistModel.is_active == True  # noqa: E712
        )
        result = await self._session.exec(watchlist_stmt)
        symbols: set[str] = {row for row in result.all() if row}

        cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=window_days)
        tx_stmt = (
            select(TransactionModel.ticker)
            .where(col(TransactionModel.ticker).is_not(None))
            .where(TransactionModel.timestamp >= cutoff)
            .distinct()
        )
        tx_result = await self._session.exec(tx_stmt)
        for row in tx_result.all():
            if row:
                symbols.add(row)
        return symbols

    async def _coverage_aggregates(self) -> dict[str, _CoverageAggregate]:
        """Per-ticker MIN/MAX(timestamp) + MAX(created_at) for daily bars."""
        stmt = (
            select(
                PriceHistoryModel.ticker,
                func.min(PriceHistoryModel.timestamp).label("first_bar"),
                func.max(PriceHistoryModel.timestamp).label("last_bar"),
                func.max(PriceHistoryModel.created_at).label("last_refresh"),
            )
            .where(PriceHistoryModel.interval == _DAILY_INTERVAL)
            .group_by(col(PriceHistoryModel.ticker))
        )
        result = await self._session.exec(stmt)
        aggregates: dict[str, _CoverageAggregate] = {}
        for row in result.all():
            ticker_symbol, first_bar, last_bar, last_refresh = row
            # All four columns are NON NULL at the model level; the
            # aggregate functions preserve that invariant when the
            # GROUP BY produces a row (which only happens if at least
            # one underlying row exists for the ticker).
            aggregates[ticker_symbol] = _CoverageAggregate(
                first_bar_date=_to_date(first_bar),
                last_bar_date=_to_date(last_bar),
                last_refresh=last_refresh,
            )
        return aggregates

    async def _covered_days_by_ticker(self) -> dict[str, frozenset[date]]:
        """Per-ticker set of distinct trading dates with at least one daily bar.

        The SQL fetch is one row per (ticker, distinct date). Pythonn
        groups into a per-ticker frozenset so the gap calculation is
        a pure set difference.
        """
        stmt = (
            select(
                PriceHistoryModel.ticker,
                PriceHistoryModel.timestamp,
            )
            .where(PriceHistoryModel.interval == _DAILY_INTERVAL)
            .distinct()
        )
        result = await self._session.exec(stmt)
        grouped: dict[str, set[date]] = {}
        for row in result.all():
            ticker_symbol, timestamp = row
            day = _to_date(timestamp)
            grouped.setdefault(ticker_symbol, set()).add(day)
        return {k: frozenset(v) for k, v in grouped.items()}


# ----------------------------------------------------------------------
# Pure helpers + internal value carriers
# ----------------------------------------------------------------------


@dataclass(frozen=True)
class _CoverageAggregate:
    """Per-ticker scalar aggregates we read from price_history."""

    first_bar_date: date
    last_bar_date: date
    last_refresh: datetime


def _to_date(value: datetime | date) -> date:
    """Normalise a SQL-returned timestamp/date to a plain ``date``."""
    if isinstance(value, datetime):
        return value.date()
    return value


def _ensure_aware(value: datetime) -> datetime:
    """Stamp UTC on SQLite-returned naive timestamps.

    The price_history table stores timestamps without timezone (see
    ``PriceHistoryModel.created_at``); ensure the value we hand back
    to callers is unambiguously UTC so ``.isoformat()`` produces a
    proper ``Z``-suffixed string instead of a naive one.
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def _compute_gap_days(
    coverage_start: date,
    coverage_end: date,
    covered: frozenset[date],
) -> int:
    """Count trading days in ``[coverage_start, coverage_end]`` with no bar.

    Pre-``coverage_start`` data is NOT a gap — we only count interior
    holes. A trading day is one where the US stock market is open
    (per :class:`MarketCalendar`).

    Args:
        coverage_start: First daily bar's date (inclusive).
        coverage_end: Last daily bar's date (inclusive).
        covered: Set of dates where we have at least one daily bar.

    Returns:
        Count of trading days in the interior that have no bar.
        Always ``>= 0``.
    """
    if coverage_end < coverage_start:
        return 0
    expected = MarketCalendar.trading_days_between(coverage_start, coverage_end)
    return sum(1 for day in expected if day not in covered)


__all__ = [
    "DEFAULT_ACTIVE_WINDOW_DAYS",
    "DataCoverageQuery",
    "DataCoverageQueryHandler",
    "DataCoverageResult",
    "TickerCoverage",
]
