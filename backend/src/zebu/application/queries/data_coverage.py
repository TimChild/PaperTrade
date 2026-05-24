"""Data-coverage query — per-ticker price-history coverage summary.

Phase J (Task #212 Layer 4) — operator-facing data freshness UI.
Task #215 — "Catch up" backfill UX rework.

Given the union of ``ticker_watchlist`` (active) + recently-traded
tickers + any ticker with rows in ``price_history``, emit one entry per
ticker carrying:

* ``coverage_start`` / ``coverage_end`` — first and last bar timestamps
  in ``price_history``.
* ``last_refresh`` — most-recent ``created_at`` on any
  ``price_history`` row for that ticker (when the bar was inserted /
  upserted, distinct from the bar's own ``timestamp``).
* ``gap_days_count`` — number of NYSE/NASDAQ trading days inside
  ``[target_epoch, today_utc()]`` that do NOT have a ``daily`` bar in
  ``price_history``. So a ticker with no bars yields the full span as
  gaps; a ticker covered from epoch contiguously yields 0; a ticker
  covered only from 2024-01-01 onwards yields the count from epoch
  through 2023-12-31 (the head-gap). This redefinition (Task #215)
  ensures the count actually moves when an operator-driven backfill
  lands.
* ``target_epoch`` — the configured ``ZEBU_HISTORY_EPOCH`` so the UI
  can render "Target: 2015-01-01" without re-reading the env.
* ``is_active`` — ``True`` when the ticker is in the watchlist OR has
  been traded in the active-tickers window (default 30 days). Matches
  the union used by ``scheduler.refresh_active_stocks``.
* ``backfill_status`` — populated when the ticker has a recent
  :class:`BackfillTask`. Surfaces ``pending``/``running`` always;
  ``failed`` for 24 hours after ``finished_at``; ``succeeded`` for
  60 seconds after ``finished_at`` (so the UI can flash "Caught up"
  for one poll cycle, then revert to the steady-state pill).

Tickers with no ``price_history`` rows but in the active-set are
returned with ``coverage_start = coverage_end = last_refresh = None``
and a ``gap_days_count`` equal to the trading days from epoch to
today (i.e. "we have zero bars; the catch-up button has work to do").

Layering: this is a pure application-layer query handler. The
``SessionDep``-bound implementation lives at the endpoint
(``adapters/inbound/api/admin_data_coverage.py``); the handler itself
accepts the session via constructor injection so it stays unit-testable
against the in-memory SQLite fixture used by the test suite.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, or_
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from zebu.adapters.outbound.database.models import (
    BackfillTaskModel,
    TransactionModel,
)
from zebu.adapters.outbound.models.price_history import PriceHistoryModel
from zebu.adapters.outbound.models.ticker_watchlist import TickerWatchlistModel
from zebu.domain.value_objects.backfill_task_status import BackfillTaskStatus
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

# Surface a SUCCEEDED backfill on the page for this many seconds after
# ``finished_at`` — long enough for one 30s poll cycle to render
# "Caught up", short enough that the page settles back to the
# steady-state pill on the next refresh.
_SUCCEEDED_SURFACE_WINDOW_SECONDS: int = 60

# Surface a FAILED backfill for this long so the operator has a
# realistic chance of seeing it without polling at the exact moment of
# failure. 24 hours is well beyond the scheduler's retry cadence so
# repeats won't pile up multiple visible failures.
_FAILED_SURFACE_WINDOW_HOURS: int = 24

# Pull only this many hours of terminal-task history into the
# backfill-status query. Non-terminal tasks (PENDING / RUNNING) are
# never excluded by this window — they're caught by a separate branch
# of the WHERE clause so a long-stuck task still surfaces. 48 hours
# comfortably covers the 24-hour FAILED surface window plus typical
# gap between created_at and finished_at on a backfill task.
_RECENT_TASKS_WINDOW_HOURS: int = 48


@dataclass(frozen=True)
class BackfillStatusInfo:
    """Most-recent backfill task surfaced for a ticker.

    Attributes:
        task_id: ID of the :class:`BackfillTask` row.
        status: Current lifecycle state.
        enqueued_at: UTC timestamp the task was created.
        error_message: Truncated reason when ``status == FAILED``;
            ``None`` otherwise.
    """

    task_id: UUID
    status: BackfillTaskStatus
    enqueued_at: datetime
    error_message: str | None


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
        gap_days_count: Trading days in
            ``[target_epoch, today_utc()]`` that have no daily bar.
            Always ``>= 0``.
        target_epoch: ``ZEBU_HISTORY_EPOCH`` — the earliest target
            date for the "catch up" backfill.
        is_active: ``True`` when the ticker is in the watchlist OR has
            been traded in the active-tickers window.
        is_watchlisted: ``True`` iff the ticker has an active row in
            ``ticker_watchlist``. Orthogonal to ``is_active`` — a
            recently-traded ticker can be active without being
            watchlisted, and a watchlisted ticker can lapse out of the
            recently-traded window while staying active via the
            watchlist arm of the union. (Task #220.)
        backfill_status: Most-recent task summary, or ``None`` when no
            task exists (or the most-recent one is SUCCEEDED outside
            the 60s surface window / FAILED outside the 24h window).
    """

    ticker: Ticker
    coverage_start: date | None
    coverage_end: date | None
    last_refresh: datetime | None
    gap_days_count: int
    target_epoch: date
    is_active: bool
    is_watchlisted: bool
    backfill_status: BackfillStatusInfo | None


@dataclass(frozen=True)
class DataCoverageQuery:
    """Input for the data-coverage query.

    Attributes:
        target_epoch: Earliest date considered when computing
            ``gap_days_count`` and rendered to the UI as the
            catch-up target. Sourced from ``ZEBU_HISTORY_EPOCH``.
        active_window_days: How many days back to look for
            "recently-traded" tickers when computing ``is_active``.
            Defaults to :data:`DEFAULT_ACTIVE_WINDOW_DAYS` (30) to
            match the scheduler.
        now: Reference timestamp for "today" and for resolving the
            SUCCEEDED / FAILED surface windows. Injectable so tests
            can pin a deterministic clock; defaults to
            :func:`datetime.now(UTC)`.
    """

    target_epoch: date
    active_window_days: int = DEFAULT_ACTIVE_WINDOW_DAYS
    now: datetime | None = None


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
    + one recent-transactions read + one most-recent-backfill-task
    read. For thousand-ticker volumes this keeps the endpoint well
    under the 30-second poll budget.
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
            query: Query parameters (epoch + active-window length).

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

        now = query.now if query.now is not None else datetime.now(UTC)
        today = now.astimezone(UTC).date()

        # Pre-compute the expected trading days in [epoch, today] once —
        # shared across every ticker so the gap calc is a single set
        # difference per row.
        expected_trading_days: frozenset[date] = frozenset(
            MarketCalendar.trading_days_between(query.target_epoch, today)
        )

        # 1a. Watchlist set (separate from the union so we can stamp the
        #     orthogonal ``is_watchlisted`` flag per row — Task #220).
        watchlisted_tickers = await self._watchlisted_tickers()

        # 1b. Recently-traded set (the other arm of the active-set union).
        recently_traded_tickers = await self._recently_traded_tickers(
            query.active_window_days, now
        )

        # 1c. Active-set: watchlist ∪ recently-traded.
        active_tickers = watchlisted_tickers | recently_traded_tickers

        # 2. Aggregates per ticker across price_history (daily bars).
        aggregates = await self._coverage_aggregates()

        # 3. Distinct trading days per ticker, for the gap computation.
        covered_days = await self._covered_days_by_ticker()

        # 4. Most-recent backfill task per ticker, after applying the
        #    surface-window rules.
        backfill_status_by_ticker = await self._backfill_status_by_ticker(now=now)

        # 5. Union of ticker keys: active-set + any ticker that has
        #    bars in price_history. Bars-without-active-flag still get
        #    surfaced (e.g. an old transaction whose ticker has dropped
        #    off the watchlist) so the operator can prune coverage.
        all_tickers: set[str] = set(active_tickers) | set(aggregates.keys())

        rows: list[TickerCoverage] = []
        for symbol in sorted(all_tickers):
            agg = aggregates.get(symbol)
            covered = covered_days.get(symbol, frozenset())
            gap_days_count = _count_missing_days(expected_trading_days, covered)
            backfill_status = backfill_status_by_ticker.get(symbol)
            if agg is None:
                rows.append(
                    TickerCoverage(
                        ticker=Ticker(symbol),
                        coverage_start=None,
                        coverage_end=None,
                        last_refresh=None,
                        gap_days_count=gap_days_count,
                        target_epoch=query.target_epoch,
                        is_active=symbol in active_tickers,
                        is_watchlisted=symbol in watchlisted_tickers,
                        backfill_status=backfill_status,
                    )
                )
                continue

            rows.append(
                TickerCoverage(
                    ticker=Ticker(symbol),
                    coverage_start=agg.first_bar_date,
                    coverage_end=agg.last_bar_date,
                    last_refresh=_ensure_aware(agg.last_refresh),
                    gap_days_count=gap_days_count,
                    target_epoch=query.target_epoch,
                    is_active=symbol in active_tickers,
                    is_watchlisted=symbol in watchlisted_tickers,
                    backfill_status=backfill_status,
                )
            )

        return DataCoverageResult(tickers=rows)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    async def _watchlisted_tickers(self) -> set[str]:
        """Set of active watchlist ticker symbols.

        Task #220 broke this out from ``_active_tickers`` so the per-row
        ``is_watchlisted`` flag can be stamped without re-reading the
        table. The union semantics for ``is_active`` are unchanged —
        callers compose this set with :meth:`_recently_traded_tickers`.
        """
        watchlist_stmt = select(TickerWatchlistModel.ticker).where(
            TickerWatchlistModel.is_active == True  # noqa: E712
        )
        result = await self._session.exec(watchlist_stmt)
        return {row for row in result.all() if row}

    async def _recently_traded_tickers(
        self, window_days: int, now: datetime
    ) -> set[str]:
        """Set of ticker symbols traded within ``window_days``.

        The other arm of the active-set union — composed with
        :meth:`_watchlisted_tickers` to produce the steady-state
        "active" flag used by the scheduler.
        """
        cutoff = now.astimezone(UTC).replace(tzinfo=None) - timedelta(days=window_days)
        tx_stmt = (
            select(TransactionModel.ticker)
            .where(col(TransactionModel.ticker).is_not(None))
            .where(TransactionModel.timestamp >= cutoff)
            .distinct()
        )
        tx_result = await self._session.exec(tx_stmt)
        return {row for row in tx_result.all() if row}

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

    async def _backfill_status_by_ticker(
        self, *, now: datetime
    ) -> dict[str, BackfillStatusInfo]:
        """Most-recent surfaceable backfill task per ticker.

        Strategy: pull the most-recent-enqueue-per-ticker, group by
        ticker in Python, and apply the surface-window rules:

        * Non-terminal (PENDING / RUNNING) → always surface.
        * SUCCEEDED → surface only within
          :data:`_SUCCEEDED_SURFACE_WINDOW_SECONDS` of ``finished_at``.
        * FAILED → surface for :data:`_FAILED_SURFACE_WINDOW_HOURS`.

        Query scope (added Task #215 follow-up): we bound the scan with
        a WHERE that admits either non-terminal tasks (always, so a
        stuck PENDING / RUNNING surfaces no matter how old it is) OR
        terminal tasks within
        :data:`_RECENT_TASKS_WINDOW_HOURS` — anything older than that
        couldn't surface under either window. Without this bound the
        query is O(all task rows ever written), which bloats the
        operator's 30s poll after a year of activity.

        We sort by ``created_at`` (the wire-level enqueue time) DESC
        so the first row per ticker is the most recent enqueue. We
        don't use ``finished_at`` because PENDING/RUNNING tasks don't
        have one — the entity carrying the latest enqueue is the one
        the operator cares about.
        """
        # created_at is stored naive UTC; build a matching naive cutoff.
        cutoff_naive = now.astimezone(UTC).replace(tzinfo=None) - timedelta(
            hours=_RECENT_TASKS_WINDOW_HOURS
        )
        stmt = (
            select(BackfillTaskModel)
            .where(
                or_(
                    col(BackfillTaskModel.status).in_(
                        [
                            BackfillTaskStatus.PENDING.value,
                            BackfillTaskStatus.RUNNING.value,
                        ]
                    ),
                    col(BackfillTaskModel.created_at) >= cutoff_naive,
                )
            )
            .order_by(col(BackfillTaskModel.created_at).desc())
        )
        result = await self._session.exec(stmt)

        seen: set[str] = set()
        surfaced: dict[str, BackfillStatusInfo] = {}
        now_utc = now.astimezone(UTC)
        for model in result.all():
            if model.ticker in seen:
                # We've already taken the most-recent for this ticker.
                continue
            seen.add(model.ticker)

            task_status = BackfillTaskStatus(model.status)
            enqueued_at_aware = _ensure_aware(model.created_at)
            finished_at_aware = (
                _ensure_aware(model.finished_at)
                if model.finished_at is not None
                else None
            )

            if not _should_surface(
                status=task_status,
                finished_at=finished_at_aware,
                now=now_utc,
            ):
                continue

            surfaced[model.ticker] = BackfillStatusInfo(
                task_id=model.id,
                status=task_status,
                enqueued_at=enqueued_at_aware,
                error_message=model.error_message
                if task_status is BackfillTaskStatus.FAILED
                else None,
            )
        return surfaced


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

    The price_history and backfill_tasks tables store timestamps
    without timezone; ensure the value we hand back to callers is
    unambiguously UTC so ``.isoformat()`` produces a proper
    ``Z``-suffixed string instead of a naive one.
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def _count_missing_days(
    expected: frozenset[date],
    covered: frozenset[date],
) -> int:
    """Count expected trading days that aren't in the covered set.

    A pure set difference — no calendar math required since the caller
    has already computed the expected days from
    :class:`MarketCalendar`.
    """
    return len(expected - covered)


def _should_surface(
    *,
    status: BackfillTaskStatus,
    finished_at: datetime | None,
    now: datetime,
) -> bool:
    """Decide whether a backfill task is current enough to surface.

    Rules (mirror the spec in ``agent_docs/tasks/215_backfill_ux_rework.md``):

    * PENDING / RUNNING → always surface.
    * SUCCEEDED → surface only for the first
      :data:`_SUCCEEDED_SURFACE_WINDOW_SECONDS` after ``finished_at``.
    * FAILED → surface for :data:`_FAILED_SURFACE_WINDOW_HOURS` after
      ``finished_at`` so the operator can act.

    A terminal task with a missing ``finished_at`` is a domain-level
    invariant violation that should have been caught at write time;
    treat it conservatively as "don't surface" to avoid wedging the UI
    on bad data.
    """
    if status is BackfillTaskStatus.PENDING or status is BackfillTaskStatus.RUNNING:
        return True
    if finished_at is None:
        return False
    elapsed = now - finished_at
    if status is BackfillTaskStatus.SUCCEEDED:
        return elapsed.total_seconds() <= _SUCCEEDED_SURFACE_WINDOW_SECONDS
    if status is BackfillTaskStatus.FAILED:
        return elapsed <= timedelta(hours=_FAILED_SURFACE_WINDOW_HOURS)
    return False


__all__ = [
    "DEFAULT_ACTIVE_WINDOW_DAYS",
    "BackfillStatusInfo",
    "DataCoverageQuery",
    "DataCoverageQueryHandler",
    "DataCoverageResult",
    "TickerCoverage",
]
