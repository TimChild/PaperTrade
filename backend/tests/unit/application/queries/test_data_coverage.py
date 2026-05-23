"""Unit tests for the data-coverage query handler.

Phase J (Task #212 Layer 4); Task #215 "catch up" UX rework.

Covers:

* Empty DB → empty result.
* Watchlist + recently-traded → active set is the union.
* Daily-bar aggregates → correct coverage_start, coverage_end,
  last_refresh.
* Gap-day computation against ``[target_epoch, today]``: weekends +
  holidays excluded; the head-gap (epoch → coverage_start) counts;
  the tail-gap (coverage_end → today) counts.
* Active flag plumbing for "ticker only known via watchlist".
* Ordering by ticker symbol ascending.
* ``backfill_status`` selection rules — non-terminal always surfaces;
  SUCCEEDED surfaces only within 60s; FAILED surfaces for 24h.

Seeded data goes through the SQLAlchemy session directly (no domain
factories — we want to assert the handler's exact SQL behaviour,
including the daily-only filter and the watchlist ∪ transactions union).
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncEngine
from sqlmodel.ext.asyncio.session import AsyncSession

from zebu.adapters.outbound.database.models import (
    BackfillTaskModel,
    PortfolioModel,
    TransactionModel,
)
from zebu.adapters.outbound.models.price_history import PriceHistoryModel
from zebu.adapters.outbound.models.ticker_watchlist import TickerWatchlistModel
from zebu.application.queries.data_coverage import (
    DataCoverageQuery,
    DataCoverageQueryHandler,
)
from zebu.domain.value_objects.backfill_task_status import BackfillTaskStatus

# Anchor: 2024-01-15 is a Monday. We use this as the canonical "now"
# in tests so the expected-trading-days math is deterministic across
# CI / local runs.
_EPOCH = date(2024, 1, 1)
_TODAY = date(2024, 1, 15)
_NOW = datetime(2024, 1, 15, 14, 30, tzinfo=UTC)


def _default_query() -> DataCoverageQuery:
    """The canonical pinned-clock query used by most tests."""
    return DataCoverageQuery(target_epoch=_EPOCH, now=_NOW)


async def _seed_daily_bars(
    session: AsyncSession,
    *,
    ticker: str,
    days: list[date],
    created_at: datetime,
) -> None:
    """Seed one daily ``price_history`` row per supplied date."""
    for d in days:
        bar_timestamp = datetime(d.year, d.month, d.day, tzinfo=UTC).replace(
            tzinfo=None
        )
        session.add(
            PriceHistoryModel(
                ticker=ticker,
                price_amount=Decimal("100.00"),
                price_currency="USD",
                timestamp=bar_timestamp,
                source="test",
                interval="1day",
                created_at=created_at.replace(tzinfo=None),
            )
        )
    await session.commit()


async def _add_watchlist(
    session: AsyncSession,
    *,
    ticker: str,
    is_active: bool = True,
) -> None:
    """Add a watchlist row."""
    session.add(TickerWatchlistModel(ticker=ticker, is_active=is_active))
    await session.commit()


async def _add_transaction(
    session: AsyncSession,
    *,
    ticker: str,
    days_ago: int,
    now: datetime = _NOW,
) -> None:
    """Add a single BUY transaction for ``ticker`` ``days_ago`` days ago.

    Inserts a parent ``PortfolioModel`` row first because the
    ``transactions.portfolio_id`` FK is enforced in tests (Task #216).
    """
    portfolio_id = uuid4()
    now = datetime.now(UTC).replace(tzinfo=None)
    session.add(
        PortfolioModel(
            id=portfolio_id,
            user_id=uuid4(),
            name=f"test-{ticker}",
            created_at=now,
            updated_at=now,
        )
    )
    session.add(
        TransactionModel(
            id=uuid4(),
            portfolio_id=portfolio_id,
            transaction_type="BUY",
            timestamp=now - timedelta(days=days_ago),
            cash_change_amount=Decimal("-100"),
            cash_change_currency="USD",
            ticker=ticker,
            quantity=Decimal("1"),
            price_per_share_amount=Decimal("100"),
            price_per_share_currency="USD",
        )
    )
    await session.commit()


async def _seed_backfill_task(
    session: AsyncSession,
    *,
    ticker: str,
    status: BackfillTaskStatus,
    created_at: datetime,
    finished_at: datetime | None = None,
    error_message: str | None = None,
    priority: str = "high",
    start_date: date = _EPOCH,
    end_date: date = _TODAY,
) -> BackfillTaskModel:
    """Insert a backfill task row directly with the supplied status.

    Bypasses the domain entity so we can construct otherwise-invalid
    shapes (e.g. ``SUCCEEDED`` long in the past) the handler must
    tolerate at read time.
    """
    model = BackfillTaskModel(
        id=uuid4(),
        ticker=ticker,
        start_date=start_date,
        end_date=end_date,
        priority=priority,
        status=status.value,
        created_at=created_at.replace(tzinfo=None) if created_at.tzinfo else created_at,
        finished_at=(
            finished_at.replace(tzinfo=None)
            if finished_at is not None and finished_at.tzinfo
            else finished_at
        ),
        error_message=error_message,
    )
    session.add(model)
    await session.commit()
    return model


class TestEmptyDatabase:
    """Empty DB → empty result, no exceptions."""

    async def test_returns_empty_list(self, test_engine: AsyncEngine) -> None:
        async with AsyncSession(test_engine, expire_on_commit=False) as session:
            handler = DataCoverageQueryHandler(session)
            result = await handler.execute(_default_query())
            assert result.tickers == []


class TestActiveFlag:
    """``is_active`` derives from watchlist ∪ recently-traded."""

    async def test_watchlist_ticker_with_no_bars_appears_active(
        self, test_engine: AsyncEngine
    ) -> None:
        """A watchlisted ticker with zero price-history rows still gets surfaced."""
        async with AsyncSession(test_engine, expire_on_commit=False) as session:
            await _add_watchlist(session, ticker="AAPL")
            handler = DataCoverageQueryHandler(session)
            result = await handler.execute(_default_query())

        assert len(result.tickers) == 1
        row = result.tickers[0]
        assert row.ticker.symbol == "AAPL"
        assert row.coverage_start is None
        assert row.coverage_end is None
        assert row.last_refresh is None
        # With NO bars the gap is the full [epoch, today] trading-day span.
        assert row.gap_days_count > 0
        assert row.is_active is True
        assert row.target_epoch == _EPOCH
        assert row.backfill_status is None

    async def test_recently_traded_ticker_is_active(
        self, test_engine: AsyncEngine
    ) -> None:
        """A ticker traded within the active window counts as active."""
        async with AsyncSession(test_engine, expire_on_commit=False) as session:
            await _add_transaction(session, ticker="GOOGL", days_ago=5)
            handler = DataCoverageQueryHandler(session)
            result = await handler.execute(_default_query())

        symbols = {row.ticker.symbol: row for row in result.tickers}
        assert "GOOGL" in symbols
        assert symbols["GOOGL"].is_active is True

    async def test_old_transaction_outside_window_inactive(
        self, test_engine: AsyncEngine
    ) -> None:
        """A ticker last traded outside the window has bars but is_active=False."""
        async with AsyncSession(test_engine, expire_on_commit=False) as session:
            # Old transaction (60 days ago, outside default 30-day window).
            await _add_transaction(session, ticker="MSFT", days_ago=60)
            # And seed a bar so the ticker shows up even without watchlist.
            await _seed_daily_bars(
                session,
                ticker="MSFT",
                days=[date(2024, 1, 8)],
                created_at=datetime(2024, 1, 8, 0, 0, tzinfo=UTC),
            )

            handler = DataCoverageQueryHandler(session)
            result = await handler.execute(_default_query())

        symbols = {row.ticker.symbol: row for row in result.tickers}
        assert "MSFT" in symbols
        assert symbols["MSFT"].is_active is False
        assert symbols["MSFT"].coverage_start == date(2024, 1, 8)


class TestCoverageAggregates:
    """``coverage_start``/``coverage_end``/``last_refresh`` from daily bars."""

    async def test_single_bar_returns_same_start_and_end(
        self, test_engine: AsyncEngine
    ) -> None:
        async with AsyncSession(test_engine, expire_on_commit=False) as session:
            ingest_time = datetime(2024, 1, 8, 12, 30, tzinfo=UTC)
            await _seed_daily_bars(
                session,
                ticker="AAPL",
                days=[date(2024, 1, 8)],
                created_at=ingest_time,
            )

            handler = DataCoverageQueryHandler(session)
            result = await handler.execute(_default_query())

        row = result.tickers[0]
        assert row.coverage_start == date(2024, 1, 8)
        assert row.coverage_end == date(2024, 1, 8)
        # The last_refresh value should be UTC-aware.
        assert row.last_refresh is not None
        assert row.last_refresh.tzinfo is not None
        # And equal in UTC to the seeded ingest time.
        assert row.last_refresh.astimezone(UTC) == ingest_time

    async def test_multiple_bars_span_correct_range(
        self, test_engine: AsyncEngine
    ) -> None:
        async with AsyncSession(test_engine, expire_on_commit=False) as session:
            await _seed_daily_bars(
                session,
                ticker="AAPL",
                days=[date(2024, 1, 8), date(2024, 1, 10), date(2024, 1, 12)],
                created_at=datetime(2024, 1, 12, 0, 0, tzinfo=UTC),
            )

            handler = DataCoverageQueryHandler(session)
            result = await handler.execute(_default_query())

        row = result.tickers[0]
        assert row.coverage_start == date(2024, 1, 8)
        assert row.coverage_end == date(2024, 1, 12)

    async def test_intraday_bars_do_not_affect_coverage(
        self, test_engine: AsyncEngine
    ) -> None:
        """Only ``1day`` interval is counted; 1min / 5min / 1hour are ignored."""
        async with AsyncSession(test_engine, expire_on_commit=False) as session:
            # Seed an intraday-only ticker — should be invisible to the query.
            session.add(
                PriceHistoryModel(
                    ticker="INTRA",
                    price_amount=Decimal("100"),
                    price_currency="USD",
                    timestamp=datetime(2024, 1, 8, 10, 30),
                    source="test",
                    interval="1min",
                    created_at=datetime(2024, 1, 8, 10, 30),
                )
            )
            await session.commit()

            handler = DataCoverageQueryHandler(session)
            result = await handler.execute(_default_query())

        # Only the watchlist+transactions add tickers; with neither, INTRA
        # is unreachable from our active union, so the table is empty.
        symbols = {row.ticker.symbol for row in result.tickers}
        assert "INTRA" not in symbols


class TestGapDaysAgainstEpoch:
    """``gap_days_count`` counts missing trading days inside ``[epoch, today]``."""

    async def test_no_bars_yields_full_span_as_gap(
        self, test_engine: AsyncEngine
    ) -> None:
        """A watchlisted ticker with NO daily bars has every expected day as a gap."""
        async with AsyncSession(test_engine, expire_on_commit=False) as session:
            await _add_watchlist(session, ticker="AAPL")
            handler = DataCoverageQueryHandler(session)
            result = await handler.execute(_default_query())

        # [2024-01-01 .. 2024-01-15] — 2024-01-01 is a market holiday (New
        # Year's Day) and 2024-01-15 is MLK Day. Trading days in the
        # range: Jan 2,3,4,5,8,9,10,11,12 — that's 9 days.
        assert result.tickers[0].gap_days_count == 9

    async def test_full_coverage_yields_zero_gaps(
        self, test_engine: AsyncEngine
    ) -> None:
        """Every expected trading day covered → ``gap_days_count == 0``."""
        async with AsyncSession(test_engine, expire_on_commit=False) as session:
            # Cover every trading day in the [epoch, today] window.
            covered = [
                date(2024, 1, 2),
                date(2024, 1, 3),
                date(2024, 1, 4),
                date(2024, 1, 5),
                date(2024, 1, 8),
                date(2024, 1, 9),
                date(2024, 1, 10),
                date(2024, 1, 11),
                date(2024, 1, 12),
            ]
            await _seed_daily_bars(
                session,
                ticker="AAPL",
                days=covered,
                created_at=datetime(2024, 1, 12, tzinfo=UTC),
            )

            handler = DataCoverageQueryHandler(session)
            result = await handler.execute(_default_query())

        row = next(r for r in result.tickers if r.ticker.symbol == "AAPL")
        assert row.gap_days_count == 0

    async def test_head_gap_counts(self, test_engine: AsyncEngine) -> None:
        """Bars only from the middle of the window onward leaves a head gap."""
        async with AsyncSession(test_engine, expire_on_commit=False) as session:
            # Cover only the second half of the trading-day span.
            covered = [
                date(2024, 1, 9),
                date(2024, 1, 10),
                date(2024, 1, 11),
                date(2024, 1, 12),
            ]
            await _seed_daily_bars(
                session,
                ticker="AAPL",
                days=covered,
                created_at=datetime(2024, 1, 12, tzinfo=UTC),
            )

            handler = DataCoverageQueryHandler(session)
            result = await handler.execute(_default_query())

        row = next(r for r in result.tickers if r.ticker.symbol == "AAPL")
        # Trading days in [2024-01-01..2024-01-15] not covered:
        # Jan 2, 3, 4, 5, 8 → 5 days.
        assert row.gap_days_count == 5

    async def test_tail_gap_counts(self, test_engine: AsyncEngine) -> None:
        """Bars only up to the middle of the window leaves a tail gap."""
        async with AsyncSession(test_engine, expire_on_commit=False) as session:
            covered = [
                date(2024, 1, 2),
                date(2024, 1, 3),
                date(2024, 1, 4),
                date(2024, 1, 5),
            ]
            await _seed_daily_bars(
                session,
                ticker="AAPL",
                days=covered,
                created_at=datetime(2024, 1, 5, tzinfo=UTC),
            )

            handler = DataCoverageQueryHandler(session)
            result = await handler.execute(_default_query())

        row = next(r for r in result.tickers if r.ticker.symbol == "AAPL")
        # Trading days in [2024-01-01..2024-01-15] not covered:
        # Jan 8, 9, 10, 11, 12 → 5 days.
        assert row.gap_days_count == 5

    async def test_interior_hole_counts_as_gap(self, test_engine: AsyncEngine) -> None:
        """An interior missing trading day counts as a gap."""
        async with AsyncSession(test_engine, expire_on_commit=False) as session:
            # Skip Wednesday 2024-01-10 (trading day).
            covered = [
                date(2024, 1, 2),
                date(2024, 1, 3),
                date(2024, 1, 4),
                date(2024, 1, 5),
                date(2024, 1, 8),
                date(2024, 1, 9),
                # 2024-01-10 missing.
                date(2024, 1, 11),
                date(2024, 1, 12),
            ]
            await _seed_daily_bars(
                session,
                ticker="AAPL",
                days=covered,
                created_at=datetime(2024, 1, 12, tzinfo=UTC),
            )

            handler = DataCoverageQueryHandler(session)
            result = await handler.execute(_default_query())

        row = next(r for r in result.tickers if r.ticker.symbol == "AAPL")
        # 9 expected, 8 covered → 1 gap.
        assert row.gap_days_count == 1

    async def test_weekends_do_not_count_as_gaps(
        self, test_engine: AsyncEngine
    ) -> None:
        """Saturday + Sunday between two bars do not count."""
        async with AsyncSession(test_engine, expire_on_commit=False) as session:
            # Use a query pinned to 2024-01-08 (Mon) covering 2024-01-05 (Fri)
            # only to validate weekend exclusion explicitly.
            query = DataCoverageQuery(
                target_epoch=date(2024, 1, 5),
                now=datetime(2024, 1, 8, tzinfo=UTC),
            )
            await _seed_daily_bars(
                session,
                ticker="AAPL",
                days=[date(2024, 1, 5), date(2024, 1, 8)],
                created_at=datetime(2024, 1, 8, tzinfo=UTC),
            )

            handler = DataCoverageQueryHandler(session)
            result = await handler.execute(query)

        row = next(r for r in result.tickers if r.ticker.symbol == "AAPL")
        assert row.gap_days_count == 0


class TestBackfillStatus:
    """``backfill_status`` reflects the most-recent surfaceable task per ticker."""

    async def test_pending_task_surfaces(self, test_engine: AsyncEngine) -> None:
        async with AsyncSession(test_engine, expire_on_commit=False) as session:
            await _add_watchlist(session, ticker="AAPL")
            await _seed_backfill_task(
                session,
                ticker="AAPL",
                status=BackfillTaskStatus.PENDING,
                created_at=_NOW - timedelta(minutes=2),
            )

            handler = DataCoverageQueryHandler(session)
            result = await handler.execute(_default_query())

        row = next(r for r in result.tickers if r.ticker.symbol == "AAPL")
        assert row.backfill_status is not None
        assert row.backfill_status.status is BackfillTaskStatus.PENDING
        assert row.backfill_status.error_message is None

    async def test_running_task_surfaces(self, test_engine: AsyncEngine) -> None:
        async with AsyncSession(test_engine, expire_on_commit=False) as session:
            await _add_watchlist(session, ticker="AAPL")
            await _seed_backfill_task(
                session,
                ticker="AAPL",
                status=BackfillTaskStatus.RUNNING,
                created_at=_NOW - timedelta(minutes=2),
            )

            handler = DataCoverageQueryHandler(session)
            result = await handler.execute(_default_query())

        row = next(r for r in result.tickers if r.ticker.symbol == "AAPL")
        assert row.backfill_status is not None
        assert row.backfill_status.status is BackfillTaskStatus.RUNNING

    async def test_recent_succeeded_within_60s_surfaces(
        self, test_engine: AsyncEngine
    ) -> None:
        """A SUCCEEDED task < 60s old shows as 'caught up' on the next poll."""
        async with AsyncSession(test_engine, expire_on_commit=False) as session:
            await _add_watchlist(session, ticker="AAPL")
            await _seed_backfill_task(
                session,
                ticker="AAPL",
                status=BackfillTaskStatus.SUCCEEDED,
                created_at=_NOW - timedelta(seconds=70),
                finished_at=_NOW - timedelta(seconds=30),
            )

            handler = DataCoverageQueryHandler(session)
            result = await handler.execute(_default_query())

        row = next(r for r in result.tickers if r.ticker.symbol == "AAPL")
        assert row.backfill_status is not None
        assert row.backfill_status.status is BackfillTaskStatus.SUCCEEDED

    async def test_stale_succeeded_outside_60s_omitted(
        self, test_engine: AsyncEngine
    ) -> None:
        """SUCCEEDED > 60s ago should fall back to steady-state (no surface)."""
        async with AsyncSession(test_engine, expire_on_commit=False) as session:
            await _add_watchlist(session, ticker="AAPL")
            await _seed_backfill_task(
                session,
                ticker="AAPL",
                status=BackfillTaskStatus.SUCCEEDED,
                created_at=_NOW - timedelta(minutes=10),
                finished_at=_NOW - timedelta(minutes=5),
            )

            handler = DataCoverageQueryHandler(session)
            result = await handler.execute(_default_query())

        row = next(r for r in result.tickers if r.ticker.symbol == "AAPL")
        assert row.backfill_status is None

    async def test_recent_failed_within_24h_surfaces_with_message(
        self, test_engine: AsyncEngine
    ) -> None:
        async with AsyncSession(test_engine, expire_on_commit=False) as session:
            await _add_watchlist(session, ticker="AAPL")
            await _seed_backfill_task(
                session,
                ticker="AAPL",
                status=BackfillTaskStatus.FAILED,
                created_at=_NOW - timedelta(hours=2),
                finished_at=_NOW - timedelta(hours=1),
                error_message="Alpha Vantage rate limit hit",
            )

            handler = DataCoverageQueryHandler(session)
            result = await handler.execute(_default_query())

        row = next(r for r in result.tickers if r.ticker.symbol == "AAPL")
        assert row.backfill_status is not None
        assert row.backfill_status.status is BackfillTaskStatus.FAILED
        assert row.backfill_status.error_message == "Alpha Vantage rate limit hit"

    async def test_old_failed_beyond_24h_omitted(
        self, test_engine: AsyncEngine
    ) -> None:
        async with AsyncSession(test_engine, expire_on_commit=False) as session:
            await _add_watchlist(session, ticker="AAPL")
            await _seed_backfill_task(
                session,
                ticker="AAPL",
                status=BackfillTaskStatus.FAILED,
                created_at=_NOW - timedelta(days=3),
                finished_at=_NOW - timedelta(days=2),
                error_message="Old failure",
            )

            handler = DataCoverageQueryHandler(session)
            result = await handler.execute(_default_query())

        row = next(r for r in result.tickers if r.ticker.symbol == "AAPL")
        assert row.backfill_status is None

    async def test_most_recent_task_wins_when_multiple(
        self, test_engine: AsyncEngine
    ) -> None:
        """Each ticker surfaces only its most-recent task (by created_at DESC)."""
        async with AsyncSession(test_engine, expire_on_commit=False) as session:
            await _add_watchlist(session, ticker="AAPL")
            # Older PENDING — should be ignored in favour of newer RUNNING.
            await _seed_backfill_task(
                session,
                ticker="AAPL",
                status=BackfillTaskStatus.PENDING,
                created_at=_NOW - timedelta(hours=2),
            )
            await _seed_backfill_task(
                session,
                ticker="AAPL",
                status=BackfillTaskStatus.RUNNING,
                created_at=_NOW - timedelta(minutes=2),
            )

            handler = DataCoverageQueryHandler(session)
            result = await handler.execute(_default_query())

        row = next(r for r in result.tickers if r.ticker.symbol == "AAPL")
        assert row.backfill_status is not None
        assert row.backfill_status.status is BackfillTaskStatus.RUNNING

    async def test_most_recent_succeeded_outside_60s_does_not_surface_older_pending(
        self, test_engine: AsyncEngine
    ) -> None:
        """If the most-recent task is a stale SUCCEEDED, don't surface anything.

        We do not fall through to older tasks — the most-recent enqueue
        is the source of truth; if it succeeded long ago, the steady
        state has resumed.
        """
        async with AsyncSession(test_engine, expire_on_commit=False) as session:
            await _add_watchlist(session, ticker="AAPL")
            # Older PENDING task we should NOT fall through to.
            await _seed_backfill_task(
                session,
                ticker="AAPL",
                status=BackfillTaskStatus.PENDING,
                created_at=_NOW - timedelta(days=1),
            )
            # Newer SUCCEEDED task that landed > 60s ago.
            await _seed_backfill_task(
                session,
                ticker="AAPL",
                status=BackfillTaskStatus.SUCCEEDED,
                created_at=_NOW - timedelta(hours=2),
                finished_at=_NOW - timedelta(minutes=5),
            )

            handler = DataCoverageQueryHandler(session)
            result = await handler.execute(_default_query())

        row = next(r for r in result.tickers if r.ticker.symbol == "AAPL")
        assert row.backfill_status is None


class TestTargetEpoch:
    """``target_epoch`` is plumbed through onto every row."""

    async def test_target_epoch_echoes_on_every_row(
        self, test_engine: AsyncEngine
    ) -> None:
        async with AsyncSession(test_engine, expire_on_commit=False) as session:
            await _add_watchlist(session, ticker="AAPL")
            await _add_watchlist(session, ticker="MSFT")
            handler = DataCoverageQueryHandler(session)
            result = await handler.execute(_default_query())

        for row in result.tickers:
            assert row.target_epoch == _EPOCH


class TestOrdering:
    """Result is sorted by ticker symbol ascending."""

    async def test_alphabetical_by_symbol(self, test_engine: AsyncEngine) -> None:
        async with AsyncSession(test_engine, expire_on_commit=False) as session:
            await _add_watchlist(session, ticker="MSFT")
            await _add_watchlist(session, ticker="AAPL")
            await _add_watchlist(session, ticker="ZM")

            handler = DataCoverageQueryHandler(session)
            result = await handler.execute(_default_query())

        assert [row.ticker.symbol for row in result.tickers] == [
            "AAPL",
            "MSFT",
            "ZM",
        ]


class TestQueryValidation:
    """``DataCoverageQuery.active_window_days`` must be positive."""

    async def test_rejects_non_positive_window(self, test_engine: AsyncEngine) -> None:
        async with AsyncSession(test_engine, expire_on_commit=False) as session:
            handler = DataCoverageQueryHandler(session)
            try:
                await handler.execute(
                    DataCoverageQuery(
                        target_epoch=_EPOCH,
                        active_window_days=0,
                        now=_NOW,
                    )
                )
            except ValueError as exc:
                assert "active_window_days" in str(exc)
            else:
                raise AssertionError("Expected ValueError for window=0")
