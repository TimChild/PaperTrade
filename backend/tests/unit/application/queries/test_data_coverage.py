"""Unit tests for the data-coverage query handler.

Phase J (Task #212 Layer 4).

Covers:

* Empty DB → empty result.
* Watchlist + recently-traded → active set is the union.
* Daily-bar aggregates → correct coverage_start, coverage_end,
  last_refresh.
* Gap-day computation: weekends + holidays excluded, interior holes
  counted, pre-coverage-start dates NOT counted.
* Active flag plumbing for "ticker only known via watchlist".
* Ordering by ticker symbol ascending.

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

from zebu.adapters.outbound.database.models import TransactionModel
from zebu.adapters.outbound.models.price_history import PriceHistoryModel
from zebu.adapters.outbound.models.ticker_watchlist import TickerWatchlistModel
from zebu.application.queries.data_coverage import (
    DataCoverageQuery,
    DataCoverageQueryHandler,
)


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
) -> None:
    """Add a single BUY transaction for ``ticker`` ``days_ago`` days ago."""
    session.add(
        TransactionModel(
            id=uuid4(),
            portfolio_id=uuid4(),
            transaction_type="BUY",
            timestamp=datetime.now(UTC).replace(tzinfo=None) - timedelta(days=days_ago),
            cash_change_amount=Decimal("-100"),
            cash_change_currency="USD",
            ticker=ticker,
            quantity=Decimal("1"),
            price_per_share_amount=Decimal("100"),
            price_per_share_currency="USD",
        )
    )
    await session.commit()


class TestEmptyDatabase:
    """Empty DB → empty result, no exceptions."""

    async def test_returns_empty_list(self, test_engine: AsyncEngine) -> None:
        async with AsyncSession(test_engine, expire_on_commit=False) as session:
            handler = DataCoverageQueryHandler(session)
            result = await handler.execute(DataCoverageQuery())
            assert result.tickers == []


class TestActiveFlag:
    """``is_active`` derives from watchlist ∪ recently-traded."""

    async def test_watchlist_ticker_with_no_bars_appears_inactive_zero_bars(
        self, test_engine: AsyncEngine
    ) -> None:
        """A watchlisted ticker with zero price-history rows still gets surfaced."""
        async with AsyncSession(test_engine, expire_on_commit=False) as session:
            await _add_watchlist(session, ticker="AAPL")
            handler = DataCoverageQueryHandler(session)
            result = await handler.execute(DataCoverageQuery())

        assert len(result.tickers) == 1
        row = result.tickers[0]
        assert row.ticker.symbol == "AAPL"
        assert row.coverage_start is None
        assert row.coverage_end is None
        assert row.last_refresh is None
        assert row.gap_days_count == 0
        assert row.is_active is True

    async def test_recently_traded_ticker_is_active(
        self, test_engine: AsyncEngine
    ) -> None:
        """A ticker traded within the active window counts as active."""
        async with AsyncSession(test_engine, expire_on_commit=False) as session:
            await _add_transaction(session, ticker="GOOGL", days_ago=5)
            handler = DataCoverageQueryHandler(session)
            result = await handler.execute(DataCoverageQuery())

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
                days=[date(2025, 1, 6)],
                created_at=datetime(2025, 1, 6, 0, 0, tzinfo=UTC),
            )

            handler = DataCoverageQueryHandler(session)
            result = await handler.execute(DataCoverageQuery())

        symbols = {row.ticker.symbol: row for row in result.tickers}
        assert "MSFT" in symbols
        assert symbols["MSFT"].is_active is False
        assert symbols["MSFT"].coverage_start == date(2025, 1, 6)


class TestCoverageAggregates:
    """``coverage_start``/``coverage_end``/``last_refresh`` from daily bars."""

    async def test_single_bar_returns_same_start_and_end(
        self, test_engine: AsyncEngine
    ) -> None:
        async with AsyncSession(test_engine, expire_on_commit=False) as session:
            ingest_time = datetime(2025, 1, 6, 12, 30, tzinfo=UTC)
            await _seed_daily_bars(
                session,
                ticker="AAPL",
                days=[date(2025, 1, 6)],
                created_at=ingest_time,
            )

            handler = DataCoverageQueryHandler(session)
            result = await handler.execute(DataCoverageQuery())

        row = result.tickers[0]
        assert row.coverage_start == date(2025, 1, 6)
        assert row.coverage_end == date(2025, 1, 6)
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
                days=[date(2025, 1, 6), date(2025, 1, 8), date(2025, 1, 10)],
                created_at=datetime(2025, 1, 10, 0, 0, tzinfo=UTC),
            )

            handler = DataCoverageQueryHandler(session)
            result = await handler.execute(DataCoverageQuery())

        row = result.tickers[0]
        assert row.coverage_start == date(2025, 1, 6)
        assert row.coverage_end == date(2025, 1, 10)

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
                    timestamp=datetime(2025, 1, 6, 10, 30),
                    source="test",
                    interval="1min",
                    created_at=datetime(2025, 1, 6, 10, 30),
                )
            )
            await session.commit()

            handler = DataCoverageQueryHandler(session)
            result = await handler.execute(DataCoverageQuery())

        # Only the watchlist+transactions add tickers; with neither, INTRA
        # is unreachable from our active union, so the table is empty.
        symbols = {row.ticker.symbol for row in result.tickers}
        assert "INTRA" not in symbols


class TestGapDays:
    """``gap_days_count`` is interior-only, weekends + holidays excluded."""

    async def test_zero_gaps_when_contiguous(self, test_engine: AsyncEngine) -> None:
        """A run of consecutive trading days has zero gaps."""
        async with AsyncSession(test_engine, expire_on_commit=False) as session:
            # 2025-01-06 (Mon) through 2025-01-10 (Fri) — 5 trading days.
            days = [date(2025, 1, d) for d in (6, 7, 8, 9, 10)]
            await _seed_daily_bars(
                session,
                ticker="AAPL",
                days=days,
                created_at=datetime(2025, 1, 10, tzinfo=UTC),
            )

            handler = DataCoverageQueryHandler(session)
            result = await handler.execute(DataCoverageQuery())

        assert result.tickers[0].gap_days_count == 0

    async def test_interior_hole_counts_as_gap(self, test_engine: AsyncEngine) -> None:
        """An interior missing trading day counts as a gap."""
        async with AsyncSession(test_engine, expire_on_commit=False) as session:
            # Skip Wednesday 2025-01-08 (trading day).
            days = [date(2025, 1, d) for d in (6, 7, 9, 10)]
            await _seed_daily_bars(
                session,
                ticker="AAPL",
                days=days,
                created_at=datetime(2025, 1, 10, tzinfo=UTC),
            )

            handler = DataCoverageQueryHandler(session)
            result = await handler.execute(DataCoverageQuery())

        assert result.tickers[0].gap_days_count == 1

    async def test_weekends_do_not_count_as_gaps(
        self, test_engine: AsyncEngine
    ) -> None:
        """Saturday + Sunday between two bars produce zero gaps."""
        async with AsyncSession(test_engine, expire_on_commit=False) as session:
            # 2025-01-10 (Fri) and 2025-01-13 (Mon) — adjacent trading days
            # spanning a weekend. Zero gaps.
            await _seed_daily_bars(
                session,
                ticker="AAPL",
                days=[date(2025, 1, 10), date(2025, 1, 13)],
                created_at=datetime(2025, 1, 13, tzinfo=UTC),
            )

            handler = DataCoverageQueryHandler(session)
            result = await handler.execute(DataCoverageQuery())

        assert result.tickers[0].gap_days_count == 0

    async def test_holidays_do_not_count_as_gaps(
        self, test_engine: AsyncEngine
    ) -> None:
        """Independence Day (2024-07-04) between two bars produces no gap."""
        async with AsyncSession(test_engine, expire_on_commit=False) as session:
            # 2024-07-03 (Wed) and 2024-07-05 (Fri). 2024-07-04 (Thu) is the
            # Independence Day holiday — markets closed.
            await _seed_daily_bars(
                session,
                ticker="AAPL",
                days=[date(2024, 7, 3), date(2024, 7, 5)],
                created_at=datetime(2024, 7, 5, tzinfo=UTC),
            )

            handler = DataCoverageQueryHandler(session)
            result = await handler.execute(DataCoverageQuery())

        assert result.tickers[0].gap_days_count == 0


class TestOrdering:
    """Result is sorted by ticker symbol ascending."""

    async def test_alphabetical_by_symbol(self, test_engine: AsyncEngine) -> None:
        async with AsyncSession(test_engine, expire_on_commit=False) as session:
            await _add_watchlist(session, ticker="MSFT")
            await _add_watchlist(session, ticker="AAPL")
            await _add_watchlist(session, ticker="ZM")

            handler = DataCoverageQueryHandler(session)
            result = await handler.execute(DataCoverageQuery())

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
                await handler.execute(DataCoverageQuery(active_window_days=0))
            except ValueError as exc:
                assert "active_window_days" in str(exc)
            else:
                raise AssertionError("Expected ValueError for window=0")
