"""Integration tests for activation-time pre-warm (Phase J / Task #212 Layer 2).

Scope:

* End-to-end prewarmer + SQL adapter: a strategy's required-window
  prewarm enqueues a BackfillTask, runs through the
  ``MarketDataPort``, and finishes as SUCCEEDED — all written to the
  same SQLite engine used by the rest of the test suite.

* Scheduler pickup drain: a PENDING task is picked up by
  :func:`drain_one_backfill` (the helper invoked by the scheduler's
  ``refresh_active_stocks`` loop) and flips to SUCCEEDED.

* Failure path: a missing ticker in the market-data adapter ends in
  FAILED with a non-empty error message.

The activate route's HTTP-level "returns 201" behaviour is already
pinned by ``test_strategy_activations_api.py``. The route's call to
:func:`_schedule_prewarm` is exercised via the prewarmer unit tests
and the integration tests below — together they cover the full chain
without the brittleness of waiting on a background asyncio task in
the TestClient thread.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

from zebu.adapters.outbound.database.backfill_task_repository import (
    SQLModelBackfillTaskRepository,
)
from zebu.adapters.outbound.market_data.in_memory_adapter import (
    InMemoryMarketDataAdapter,
)
from zebu.application.services.historical_data_prewarmer import (
    HistoricalDataPrewarmer,
)
from zebu.domain.entities.backfill_task import BackfillTask
from zebu.domain.value_objects.backfill_priority import BackfillPriority
from zebu.domain.value_objects.backfill_task_status import BackfillTaskStatus
from zebu.domain.value_objects.money import Money
from zebu.domain.value_objects.price_point import PricePoint
from zebu.domain.value_objects.ticker import Ticker
from zebu.infrastructure.scheduler import drain_one_backfill


@pytest.fixture
def test_engine_session_maker(
    test_engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    """Session factory bound to the test SQLite engine."""
    return async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


def _seeded_adapter(*tickers: str) -> InMemoryMarketDataAdapter:
    """In-memory market-data adapter with one bar per ticker."""
    adapter = InMemoryMarketDataAdapter()
    seed_dt = datetime(2024, 1, 2, 12, 0, 0, tzinfo=UTC)
    for symbol in tickers:
        adapter.seed_price(
            PricePoint(
                ticker=Ticker(symbol),
                price=Money(Decimal("150"), "USD"),
                timestamp=seed_dt,
                source="database",
                interval="1day",
            )
        )
    return adapter


@pytest.mark.asyncio
class TestPrewarmEndToEnd:
    """Prewarmer + SQL adapter against a real (in-memory) SQLite engine."""

    async def test_prewarm_succeeded_persists_succeeded_row(
        self,
        test_engine_session_maker: async_sessionmaker[AsyncSession],
    ) -> None:
        """Mirrors what fires from the activate route: prewarm a single ticker."""
        adapter = _seeded_adapter("AAPL")
        end_date = datetime.now(UTC).date()
        start_date = end_date - timedelta(days=30)

        async with test_engine_session_maker() as session:
            repo = SQLModelBackfillTaskRepository(session)
            prewarmer = HistoricalDataPrewarmer(market_data=adapter, repository=repo)
            result = await prewarmer.prewarm(
                [Ticker("AAPL")],
                start_date,
                end_date,
                priority=BackfillPriority.LOW,
            )
            await session.commit()

        assert [t.symbol for t in result.succeeded] == ["AAPL"]
        assert result.failed == []

        # The row landed and is in SUCCEEDED.
        async with test_engine_session_maker() as session:
            repo = SQLModelBackfillTaskRepository(session)
            found = await repo.find_existing(
                Ticker("AAPL"),
                start_date,
                end_date,
                status_in=[BackfillTaskStatus.SUCCEEDED],
            )
        assert found is not None
        assert found.status is BackfillTaskStatus.SUCCEEDED
        assert found.priority is BackfillPriority.LOW

    async def test_prewarm_failed_ticker_persists_failed_row(
        self,
        test_engine_session_maker: async_sessionmaker[AsyncSession],
    ) -> None:
        """A ticker missing from the adapter ends up FAILED with a reason."""
        adapter = _seeded_adapter()  # empty
        end_date = datetime.now(UTC).date()
        start_date = end_date - timedelta(days=30)

        async with test_engine_session_maker() as session:
            repo = SQLModelBackfillTaskRepository(session)
            prewarmer = HistoricalDataPrewarmer(market_data=adapter, repository=repo)
            result = await prewarmer.prewarm(
                [Ticker("AAPL")],
                start_date,
                end_date,
                priority=BackfillPriority.LOW,
            )
            await session.commit()

        assert [t.symbol for t, _ in result.failed] == ["AAPL"]

        async with test_engine_session_maker() as session:
            repo = SQLModelBackfillTaskRepository(session)
            found = await repo.find_existing(
                Ticker("AAPL"),
                start_date,
                end_date,
                status_in=[BackfillTaskStatus.FAILED],
            )
        assert found is not None
        assert found.error_message is not None
        assert found.error_message.strip() != ""


@pytest.mark.asyncio
class TestSchedulerPickupDrainsPending:
    """The scheduler's pickup loop drains PENDING tasks to SUCCEEDED."""

    async def test_pending_task_flips_to_succeeded_with_in_memory_adapter(
        self,
        test_engine_session_maker: async_sessionmaker[AsyncSession],
    ) -> None:
        adapter = _seeded_adapter("AAPL")
        ticker = Ticker("AAPL")
        start_date = (datetime.now(UTC) - timedelta(days=30)).date()
        end_date = datetime.now(UTC).date()
        task = BackfillTask(
            id=uuid4(),
            ticker=ticker,
            start_date=start_date,
            end_date=end_date,
            priority=BackfillPriority.LOW,
            status=BackfillTaskStatus.PENDING,
            created_at=datetime.now(UTC),
        )
        async with test_engine_session_maker() as session:
            repo = SQLModelBackfillTaskRepository(session)
            await repo.create(task)
            await session.commit()

        async with test_engine_session_maker() as session:
            repo = SQLModelBackfillTaskRepository(session)
            await drain_one_backfill(
                market_data=adapter,
                repo=repo,
                task_id=task.id,
                ticker=ticker,
                start_date=start_date,
                end_date=end_date,
            )
            await session.commit()

        async with test_engine_session_maker() as session:
            repo = SQLModelBackfillTaskRepository(session)
            found = await repo.find_existing(
                ticker,
                start_date,
                end_date,
                status_in=[BackfillTaskStatus.SUCCEEDED],
            )
        assert found is not None
        assert found.status is BackfillTaskStatus.SUCCEEDED

    async def test_drain_failed_fetch_marks_task_failed(
        self,
        test_engine_session_maker: async_sessionmaker[AsyncSession],
    ) -> None:
        """A ticker missing from the market-data adapter ends up FAILED."""
        adapter = _seeded_adapter()  # empty — AAPL is missing
        ticker = Ticker("AAPL")
        start_date = (datetime.now(UTC) - timedelta(days=30)).date()
        end_date = datetime.now(UTC).date()
        task = BackfillTask(
            id=uuid4(),
            ticker=ticker,
            start_date=start_date,
            end_date=end_date,
            priority=BackfillPriority.LOW,
            status=BackfillTaskStatus.PENDING,
            created_at=datetime.now(UTC),
        )
        async with test_engine_session_maker() as session:
            repo = SQLModelBackfillTaskRepository(session)
            await repo.create(task)
            await session.commit()

        async with test_engine_session_maker() as session:
            repo = SQLModelBackfillTaskRepository(session)
            await drain_one_backfill(
                market_data=adapter,
                repo=repo,
                task_id=task.id,
                ticker=ticker,
                start_date=start_date,
                end_date=end_date,
            )
            await session.commit()

        async with test_engine_session_maker() as session:
            repo = SQLModelBackfillTaskRepository(session)
            found = await repo.find_existing(
                ticker,
                start_date,
                end_date,
                status_in=[BackfillTaskStatus.FAILED],
            )
        assert found is not None
        assert found.error_message is not None
