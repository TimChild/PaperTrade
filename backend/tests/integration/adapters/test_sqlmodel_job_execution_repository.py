"""Integration tests for :class:`SQLModelJobExecutionRepository`.

Phase J (Task #212 Layer 1) — verifies round-trip persistence against a
real SQLite engine and pins the merging-metadata semantics of
``record_finish``.
"""

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

# Import all SQL models so their tables register.
from zebu.adapters.outbound.database.api_key_model import ApiKeyModel  # noqa: F401
from zebu.adapters.outbound.database.job_execution_repository import (
    SQLModelJobExecutionRepository,
)
from zebu.adapters.outbound.database.models import (  # noqa: F401
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
from zebu.domain.value_objects.job_execution_status import JobExecutionStatus


@pytest_asyncio.fixture
async def isolated_engine() -> AsyncGenerator[AsyncEngine, None]:
    """In-memory SQLite engine with the job_executions table provisioned."""
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
    """A session factory bound to the isolated engine."""
    return async_sessionmaker(
        isolated_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


@pytest.mark.asyncio
class TestRoundtrip:
    async def test_record_start_persists(
        self,
        session_maker: async_sessionmaker[AsyncSession],
    ) -> None:
        async with session_maker() as session:
            repo = SQLModelJobExecutionRepository(session)
            execution = await repo.record_start("refresh_active_stocks")
            await session.commit()

        # New session: read it back via latest()
        async with session_maker() as session:
            repo = SQLModelJobExecutionRepository(session)
            loaded = await repo.latest("refresh_active_stocks")

        assert loaded is not None
        assert loaded.id == execution.id
        assert loaded.status is JobExecutionStatus.RUNNING
        assert loaded.finished_at is None
        # tzinfo round-trip — model strips, adapter re-attaches
        assert loaded.started_at.tzinfo is not None

    async def test_record_finish_flips_status(
        self,
        session_maker: async_sessionmaker[AsyncSession],
    ) -> None:
        async with session_maker() as session:
            repo = SQLModelJobExecutionRepository(session)
            start = await repo.record_start("evaluate_triggers")
            await session.commit()

        async with session_maker() as session:
            repo = SQLModelJobExecutionRepository(session)
            finished = await repo.record_finish(
                start,
                status=JobExecutionStatus.SUCCEEDED,
                metadata={"duration_seconds": "1.23"},
            )
            await session.commit()

        assert finished.status is JobExecutionStatus.SUCCEEDED
        assert finished.finished_at is not None
        assert finished.metadata["duration_seconds"] == "1.23"

    async def test_failed_path_persists_error_message(
        self,
        session_maker: async_sessionmaker[AsyncSession],
    ) -> None:
        async with session_maker() as session:
            repo = SQLModelJobExecutionRepository(session)
            start = await repo.record_start("evaluate_triggers")
            await session.commit()

        async with session_maker() as session:
            repo = SQLModelJobExecutionRepository(session)
            finished = await repo.record_finish(
                start,
                status=JobExecutionStatus.FAILED,
                error_message="ConnectionError: timeout",
                metadata={"duration_seconds": "30.0"},
            )
            await session.commit()

        assert finished.status is JobExecutionStatus.FAILED
        assert finished.error_message == "ConnectionError: timeout"

    async def test_metadata_merges_across_sessions(
        self,
        session_maker: async_sessionmaker[AsyncSession],
    ) -> None:
        """Starter metadata (from session A) merges with terminal (session B)."""
        async with session_maker() as session:
            repo = SQLModelJobExecutionRepository(session)
            start = await repo.record_start(
                "refresh_active_stocks",
                metadata={"started_by": "scheduler"},
            )
            await session.commit()

        async with session_maker() as session:
            repo = SQLModelJobExecutionRepository(session)
            finished = await repo.record_finish(
                start,
                status=JobExecutionStatus.SUCCEEDED,
                metadata={"duration_seconds": "1.0"},
            )
            await session.commit()

        assert finished.metadata == {
            "started_by": "scheduler",
            "duration_seconds": "1.0",
        }


@pytest.mark.asyncio
class TestLatestAndListRecent:
    async def test_latest_returns_most_recent(
        self,
        session_maker: async_sessionmaker[AsyncSession],
    ) -> None:
        import asyncio

        async with session_maker() as session:
            repo = SQLModelJobExecutionRepository(session)
            await repo.record_start("refresh_active_stocks")
            await session.commit()
            await asyncio.sleep(0.001)
            second = await repo.record_start("refresh_active_stocks")
            await session.commit()

        async with session_maker() as session:
            repo = SQLModelJobExecutionRepository(session)
            latest = await repo.latest("refresh_active_stocks")

        assert latest is not None
        assert latest.id == second.id

    async def test_list_recent_newest_first(
        self,
        session_maker: async_sessionmaker[AsyncSession],
    ) -> None:
        import asyncio

        async with session_maker() as session:
            repo = SQLModelJobExecutionRepository(session)
            ids = []
            for _ in range(3):
                row = await repo.record_start("refresh_active_stocks")
                ids.append(row.id)
                await session.commit()
                await asyncio.sleep(0.001)

        async with session_maker() as session:
            repo = SQLModelJobExecutionRepository(session)
            rows = await repo.list_recent("refresh_active_stocks")

        # newest-first → reversed of insertion order
        assert [r.id for r in rows] == list(reversed(ids))
