"""Integration tests for :class:`SQLModelBackfillTaskRepository`.

Phase J (Task #212 Layer 2) — verifies round-trip persistence against
SQLite and pins the state-machine transitions on the SQL path.
"""

from collections.abc import AsyncGenerator
from datetime import UTC, date, datetime
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

# Import all SQL models so their tables register.
from zebu.adapters.outbound.database.api_key_model import ApiKeyModel  # noqa: F401
from zebu.adapters.outbound.database.backfill_task_repository import (
    SQLModelBackfillTaskRepository,
)
from zebu.adapters.outbound.database.models import (  # noqa: F401
    BackfillTaskModel,
    BacktestRunModel,
    ExplorationTaskModel,
    JobExecutionModel,
    PortfolioModel,
    PortfolioSnapshotModel,
    StrategyActivationModel,
    StrategyConditionTriggerModel,
    StrategyModel,
    TransactionModel,
    TriggerFireRecordModel,
)
from zebu.adapters.outbound.models.price_history import PriceHistoryModel  # noqa: F401
from zebu.adapters.outbound.models.ticker_watchlist import (  # noqa: F401
    TickerWatchlistModel,
)
from zebu.domain.entities.backfill_task import BackfillTask
from zebu.domain.value_objects.backfill_priority import BackfillPriority
from zebu.domain.value_objects.backfill_task_status import BackfillTaskStatus
from zebu.domain.value_objects.ticker import Ticker


@pytest_asyncio.fixture
async def isolated_engine() -> AsyncGenerator[AsyncEngine, None]:
    """In-memory SQLite engine with the backfill_tasks table provisioned."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def session_maker(
    isolated_engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    """Session factory bound to the isolated engine."""
    return async_sessionmaker(
        isolated_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


def _pending(
    *,
    ticker: str = "AAPL",
    start: date = date(2024, 1, 1),
    end: date = date(2024, 1, 31),
    priority: BackfillPriority = BackfillPriority.LOW,
) -> BackfillTask:
    return BackfillTask(
        id=uuid4(),
        ticker=Ticker(ticker),
        start_date=start,
        end_date=end,
        priority=priority,
        status=BackfillTaskStatus.PENDING,
        created_at=datetime.now(UTC),
    )


@pytest.mark.asyncio
class TestRoundtrip:
    async def test_create_persists_pending(
        self,
        session_maker: async_sessionmaker[AsyncSession],
    ) -> None:
        task = _pending()
        async with session_maker() as session:
            repo = SQLModelBackfillTaskRepository(session)
            await repo.create(task)
            await session.commit()

        async with session_maker() as session:
            repo = SQLModelBackfillTaskRepository(session)
            found = await repo.find_existing(
                Ticker("AAPL"),
                task.start_date,
                task.end_date,
                status_in=[BackfillTaskStatus.PENDING],
            )

        assert found is not None
        assert found.id == task.id
        assert found.priority is BackfillPriority.LOW
        assert found.status is BackfillTaskStatus.PENDING
        # tzinfo round-trip
        assert found.created_at.tzinfo is UTC

    async def test_mark_running_flips_status(
        self,
        session_maker: async_sessionmaker[AsyncSession],
    ) -> None:
        task = _pending()
        async with session_maker() as session:
            repo = SQLModelBackfillTaskRepository(session)
            await repo.create(task)
            await session.commit()

        async with session_maker() as session:
            repo = SQLModelBackfillTaskRepository(session)
            running = await repo.mark_running(task.id)
            await session.commit()

        assert running.status is BackfillTaskStatus.RUNNING
        assert running.finished_at is None

    async def test_mark_succeeded_flips_status_and_finished_at(
        self,
        session_maker: async_sessionmaker[AsyncSession],
    ) -> None:
        task = _pending()
        async with session_maker() as session:
            repo = SQLModelBackfillTaskRepository(session)
            await repo.create(task)
            await repo.mark_running(task.id)
            await session.commit()

        async with session_maker() as session:
            repo = SQLModelBackfillTaskRepository(session)
            finished = await repo.mark_succeeded(task.id)
            await session.commit()

        assert finished.status is BackfillTaskStatus.SUCCEEDED
        assert finished.finished_at is not None
        assert finished.finished_at.tzinfo is UTC

    async def test_mark_failed_records_truncated_message(
        self,
        session_maker: async_sessionmaker[AsyncSession],
    ) -> None:
        task = _pending()
        async with session_maker() as session:
            repo = SQLModelBackfillTaskRepository(session)
            await repo.create(task)
            await repo.mark_running(task.id)
            await session.commit()

        async with session_maker() as session:
            repo = SQLModelBackfillTaskRepository(session)
            failed = await repo.mark_failed(task.id, error_message="x" * 700)
            await session.commit()

        assert failed.status is BackfillTaskStatus.FAILED
        assert failed.error_message is not None
        assert len(failed.error_message) == 500


@pytest.mark.asyncio
class TestFindExisting:
    async def test_filters_by_status_set(
        self,
        session_maker: async_sessionmaker[AsyncSession],
    ) -> None:
        """A SUCCEEDED row is invisible when filtering on non-terminal statuses."""
        task = _pending()
        async with session_maker() as session:
            repo = SQLModelBackfillTaskRepository(session)
            await repo.create(task)
            await repo.mark_running(task.id)
            await repo.mark_succeeded(task.id)
            await session.commit()

        async with session_maker() as session:
            repo = SQLModelBackfillTaskRepository(session)
            # Filtering on non-terminal statuses → nothing.
            found = await repo.find_existing(
                Ticker("AAPL"),
                task.start_date,
                task.end_date,
                status_in=[
                    BackfillTaskStatus.PENDING,
                    BackfillTaskStatus.RUNNING,
                ],
            )
            assert found is None

            # Filtering on SUCCEEDED → finds it.
            found_succeeded = await repo.find_existing(
                Ticker("AAPL"),
                task.start_date,
                task.end_date,
                status_in=[BackfillTaskStatus.SUCCEEDED],
            )
            assert found_succeeded is not None

    async def test_empty_status_set_matches_any(
        self,
        session_maker: async_sessionmaker[AsyncSession],
    ) -> None:
        task = _pending()
        async with session_maker() as session:
            repo = SQLModelBackfillTaskRepository(session)
            await repo.create(task)
            await session.commit()

        async with session_maker() as session:
            repo = SQLModelBackfillTaskRepository(session)
            found = await repo.find_existing(
                Ticker("AAPL"),
                task.start_date,
                task.end_date,
                status_in=[],
            )
            assert found is not None


@pytest.mark.asyncio
class TestListPending:
    async def test_returns_only_pending_rows_oldest_first(
        self,
        session_maker: async_sessionmaker[AsyncSession],
    ) -> None:
        import asyncio

        async with session_maker() as session:
            repo = SQLModelBackfillTaskRepository(session)
            ordered_ids: list = []
            for symbol in ["AAPL", "MSFT", "GOOG"]:
                row = _pending(ticker=symbol)
                ordered_ids.append(row.id)
                await repo.create(row)
                await session.commit()
                # Bump the clock so the rows are ordered deterministically.
                await asyncio.sleep(0.001)

            # Mark MSFT as RUNNING so it should NOT come back from list_pending.
            await repo.mark_running(ordered_ids[1])
            await session.commit()

        async with session_maker() as session:
            repo = SQLModelBackfillTaskRepository(session)
            pending = await repo.list_pending(limit=10)

        # The two PENDING rows (AAPL, GOOG) in insertion order.
        assert [t.ticker.symbol for t in pending] == ["AAPL", "GOOG"]
