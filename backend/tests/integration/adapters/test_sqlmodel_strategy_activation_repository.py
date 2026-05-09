"""Integration tests for SQLModelStrategyActivationRepository.

Tests the activation repository against a real SQLite database to verify
round-trip persistence, list filters, save-update semantics, and FK cascade
behavior when the parent strategy or portfolio is removed.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from zebu.adapters.outbound.database.models import (
    PortfolioModel,
    StrategyModel,
)
from zebu.adapters.outbound.database.strategy_activation_repository import (
    SQLModelStrategyActivationRepository,
)
from zebu.domain.entities.portfolio import Portfolio
from zebu.domain.entities.strategy import Strategy
from zebu.domain.entities.strategy_activation import StrategyActivation
from zebu.domain.value_objects.activation_frequency import ActivationFrequency
from zebu.domain.value_objects.activation_status import ActivationStatus
from zebu.domain.value_objects.portfolio_type import PortfolioType
from zebu.domain.value_objects.strategy_parameters import BuyAndHoldParameters
from zebu.domain.value_objects.strategy_type import StrategyType


@pytest_asyncio.fixture
async def fk_engine() -> AsyncEngine:
    """SQLite engine with FK enforcement enabled for cascade tests.

    The standard ``engine`` fixture in ``tests/integration/conftest.py`` does
    not enable ``PRAGMA foreign_keys=ON``, which means the cascade test would
    silently no-op. This fixture creates an isolated engine where each
    connection has FK enforcement enabled — matching the behaviour PR #224
    will give us in production.
    """
    test_engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
    )

    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    yield test_engine

    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
    await test_engine.dispose()


@pytest_asyncio.fixture
async def fk_session(fk_engine: AsyncEngine) -> AsyncSession:
    """A session bound to the FK-enabled engine."""
    async_session_maker = async_sessionmaker(
        fk_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session_maker() as session:
        # Enable FK enforcement on the per-connection level. Without this
        # SQLite ignores ON DELETE CASCADE.
        await session.exec(text("PRAGMA foreign_keys = ON"))  # type: ignore[call-overload]
        yield session
        await session.rollback()


def _make_strategy(user_id: UUID) -> Strategy:
    """Build a valid Strategy for FK-required tests."""
    return Strategy(
        id=uuid4(),
        user_id=user_id,
        name="Test Strategy",
        strategy_type=StrategyType.BUY_AND_HOLD,
        tickers=["AAPL"],
        parameters=BuyAndHoldParameters(allocation={"AAPL": Decimal("1")}),
        created_at=datetime.now(UTC) - timedelta(minutes=5),
    )


def _make_portfolio(user_id: UUID) -> Portfolio:
    """Build a valid Portfolio for FK-required tests."""
    return Portfolio(
        id=uuid4(),
        user_id=user_id,
        name="Test Portfolio",
        created_at=datetime.now(UTC) - timedelta(minutes=5),
        portfolio_type=PortfolioType.PAPER_TRADING,
    )


def _make_activation(
    *,
    strategy_id: UUID,
    portfolio_id: UUID,
    user_id: UUID,
    status: ActivationStatus = ActivationStatus.ACTIVE,
    last_executed_at: datetime | None = None,
    last_error: str | None = None,
    created_at: datetime | None = None,
) -> StrategyActivation:
    """Build a valid StrategyActivation for repository tests."""
    now = datetime.now(UTC)
    if created_at is None:
        created_at = now - timedelta(minutes=5)
    return StrategyActivation(
        id=uuid4(),
        user_id=user_id,
        strategy_id=strategy_id,
        portfolio_id=portfolio_id,
        status=status,
        frequency=ActivationFrequency.DAILY_MARKET_CLOSE,
        created_at=created_at,
        updated_at=created_at,
        last_executed_at=last_executed_at,
        last_error=last_error,
    )


async def _insert_strategy_and_portfolio(
    session: AsyncSession, user_id: UUID
) -> tuple[Strategy, Portfolio]:
    """Insert a strategy + portfolio so FK-bound activations can be saved.

    Helper used by every test that creates an activation, since both FKs
    are NOT NULL and the FK-enabled session will reject orphan inserts.
    """
    strategy = _make_strategy(user_id)
    portfolio = _make_portfolio(user_id)
    session.add(StrategyModel.from_domain(strategy))
    session.add(PortfolioModel.from_domain(portfolio))
    await session.commit()
    return strategy, portfolio


class TestSQLModelStrategyActivationRepositoryRoundTrip:
    """Basic save / get round-trip tests."""

    @pytest.mark.asyncio
    async def test_save_and_get_activation(self, fk_session: AsyncSession) -> None:
        """Saving an activation and re-reading it should return an equivalent entity."""
        user_id = uuid4()
        strategy, portfolio = await _insert_strategy_and_portfolio(fk_session, user_id)
        repo = SQLModelStrategyActivationRepository(fk_session)
        activation = _make_activation(
            strategy_id=strategy.id,
            portfolio_id=portfolio.id,
            user_id=user_id,
        )

        await repo.save(activation)
        await fk_session.commit()
        loaded = await repo.get(activation.id)

        assert loaded is not None
        assert loaded.id == activation.id
        assert loaded.user_id == activation.user_id
        assert loaded.strategy_id == strategy.id
        assert loaded.portfolio_id == portfolio.id
        assert loaded.status is ActivationStatus.ACTIVE
        assert loaded.frequency is ActivationFrequency.DAILY_MARKET_CLOSE
        assert loaded.last_executed_at is None
        assert loaded.last_error is None

    @pytest.mark.asyncio
    async def test_get_nonexistent_returns_none(self, fk_session: AsyncSession) -> None:
        """Retrieving a missing id should return None."""
        repo = SQLModelStrategyActivationRepository(fk_session)
        result = await repo.get(uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_save_round_trips_optional_fields(
        self, fk_session: AsyncSession
    ) -> None:
        """``last_executed_at`` and ``last_error`` should round-trip."""
        user_id = uuid4()
        strategy, portfolio = await _insert_strategy_and_portfolio(fk_session, user_id)
        repo = SQLModelStrategyActivationRepository(fk_session)
        last_run = datetime.now(UTC) - timedelta(minutes=1)
        activation = _make_activation(
            strategy_id=strategy.id,
            portfolio_id=portfolio.id,
            user_id=user_id,
            status=ActivationStatus.ERROR,
            last_executed_at=last_run,
            last_error="Connection refused",
        )

        await repo.save(activation)
        await fk_session.commit()
        loaded = await repo.get(activation.id)

        assert loaded is not None
        assert loaded.status is ActivationStatus.ERROR
        assert loaded.last_error == "Connection refused"
        assert loaded.last_executed_at is not None
        # SQLite truncates microseconds inconsistently; compare on the
        # second so the assertion is stable across both sqlite and postgres.
        assert loaded.last_executed_at.replace(microsecond=0) == last_run.replace(
            microsecond=0
        )


class TestSQLModelStrategyActivationRepositorySaveSemantics:
    """Save() upsert semantics."""

    @pytest.mark.asyncio
    async def test_save_updates_existing_activation(
        self, fk_session: AsyncSession
    ) -> None:
        """Re-saving an existing id should update the row, not duplicate it."""
        user_id = uuid4()
        strategy, portfolio = await _insert_strategy_and_portfolio(fk_session, user_id)
        repo = SQLModelStrategyActivationRepository(fk_session)
        original = _make_activation(
            strategy_id=strategy.id,
            portfolio_id=portfolio.id,
            user_id=user_id,
            status=ActivationStatus.ACTIVE,
        )
        await repo.save(original)
        await fk_session.commit()

        # Update: same id, paused now, with an error message.
        updated = StrategyActivation(
            id=original.id,
            user_id=original.user_id,
            strategy_id=original.strategy_id,
            portfolio_id=original.portfolio_id,
            status=ActivationStatus.ERROR,
            frequency=original.frequency,
            created_at=original.created_at,
            updated_at=datetime.now(UTC),
            last_executed_at=datetime.now(UTC) - timedelta(seconds=1),
            last_error="Pricing failure",
        )
        await repo.save(updated)
        await fk_session.commit()

        loaded = await repo.get(original.id)
        assert loaded is not None
        assert loaded.status is ActivationStatus.ERROR
        assert loaded.last_error == "Pricing failure"
        # Verify only one row exists for this id.
        all_for_user = await repo.list_for_user(user_id)
        assert len(all_for_user) == 1


class TestSQLModelStrategyActivationRepositoryListFilters:
    """``list_active``, ``list_for_user``, ``get_by_strategy`` queries."""

    @pytest.mark.asyncio
    async def test_list_active_only_returns_active_activations(
        self, fk_session: AsyncSession
    ) -> None:
        """``list_active`` should filter out PAUSED / STOPPED / ERROR rows."""
        user_id = uuid4()
        strategy_a, portfolio_a = await _insert_strategy_and_portfolio(
            fk_session, user_id
        )
        strategy_b, portfolio_b = await _insert_strategy_and_portfolio(
            fk_session, user_id
        )
        repo = SQLModelStrategyActivationRepository(fk_session)

        active = _make_activation(
            strategy_id=strategy_a.id,
            portfolio_id=portfolio_a.id,
            user_id=user_id,
            status=ActivationStatus.ACTIVE,
        )
        paused = _make_activation(
            strategy_id=strategy_b.id,
            portfolio_id=portfolio_b.id,
            user_id=user_id,
            status=ActivationStatus.PAUSED,
        )
        await repo.save(active)
        await repo.save(paused)
        await fk_session.commit()

        results = await repo.list_active()
        ids = {a.id for a in results}
        assert active.id in ids
        assert paused.id not in ids

    @pytest.mark.asyncio
    async def test_list_active_returns_oldest_first(
        self, fk_session: AsyncSession
    ) -> None:
        """``list_active`` should order by ``created_at`` ascending."""
        user_id = uuid4()
        strategy_a, portfolio_a = await _insert_strategy_and_portfolio(
            fk_session, user_id
        )
        strategy_b, portfolio_b = await _insert_strategy_and_portfolio(
            fk_session, user_id
        )
        repo = SQLModelStrategyActivationRepository(fk_session)

        now = datetime.now(UTC)
        older = _make_activation(
            strategy_id=strategy_a.id,
            portfolio_id=portfolio_a.id,
            user_id=user_id,
            created_at=now - timedelta(hours=2),
        )
        newer = _make_activation(
            strategy_id=strategy_b.id,
            portfolio_id=portfolio_b.id,
            user_id=user_id,
            created_at=now - timedelta(hours=1),
        )
        # Insert newest first so ordering can't be coincidental.
        await repo.save(newer)
        await repo.save(older)
        await fk_session.commit()

        results = await repo.list_active()
        assert len(results) == 2
        assert results[0].id == older.id
        assert results[1].id == newer.id

    @pytest.mark.asyncio
    async def test_list_for_user_scopes_by_user(self, fk_session: AsyncSession) -> None:
        """``list_for_user`` should only return rows for the given user."""
        user_a = uuid4()
        user_b = uuid4()
        strategy_a, portfolio_a = await _insert_strategy_and_portfolio(
            fk_session, user_a
        )
        strategy_b, portfolio_b = await _insert_strategy_and_portfolio(
            fk_session, user_b
        )
        repo = SQLModelStrategyActivationRepository(fk_session)

        own = _make_activation(
            strategy_id=strategy_a.id,
            portfolio_id=portfolio_a.id,
            user_id=user_a,
        )
        other = _make_activation(
            strategy_id=strategy_b.id,
            portfolio_id=portfolio_b.id,
            user_id=user_b,
        )
        await repo.save(own)
        await repo.save(other)
        await fk_session.commit()

        results = await repo.list_for_user(user_a)
        assert len(results) == 1
        assert results[0].id == own.id

    @pytest.mark.asyncio
    async def test_list_for_user_includes_all_statuses(
        self, fk_session: AsyncSession
    ) -> None:
        """``list_for_user`` returns activations regardless of status."""
        user_id = uuid4()
        strategy_a, portfolio_a = await _insert_strategy_and_portfolio(
            fk_session, user_id
        )
        strategy_b, portfolio_b = await _insert_strategy_and_portfolio(
            fk_session, user_id
        )
        repo = SQLModelStrategyActivationRepository(fk_session)

        active = _make_activation(
            strategy_id=strategy_a.id,
            portfolio_id=portfolio_a.id,
            user_id=user_id,
            status=ActivationStatus.ACTIVE,
        )
        stopped = _make_activation(
            strategy_id=strategy_b.id,
            portfolio_id=portfolio_b.id,
            user_id=user_id,
            status=ActivationStatus.STOPPED,
        )
        await repo.save(active)
        await repo.save(stopped)
        await fk_session.commit()

        results = await repo.list_for_user(user_id)
        statuses = {a.status for a in results}
        assert statuses == {ActivationStatus.ACTIVE, ActivationStatus.STOPPED}

    @pytest.mark.asyncio
    async def test_list_for_user_empty(self, fk_session: AsyncSession) -> None:
        """A user with no activations returns an empty list, not None."""
        repo = SQLModelStrategyActivationRepository(fk_session)
        results = await repo.list_for_user(uuid4())
        assert results == []

    @pytest.mark.asyncio
    async def test_get_by_strategy_returns_activation(
        self, fk_session: AsyncSession
    ) -> None:
        """``get_by_strategy`` should locate the activation by strategy id."""
        user_id = uuid4()
        strategy, portfolio = await _insert_strategy_and_portfolio(fk_session, user_id)
        repo = SQLModelStrategyActivationRepository(fk_session)

        activation = _make_activation(
            strategy_id=strategy.id,
            portfolio_id=portfolio.id,
            user_id=user_id,
        )
        await repo.save(activation)
        await fk_session.commit()

        loaded = await repo.get_by_strategy(strategy.id)
        assert loaded is not None
        assert loaded.id == activation.id

    @pytest.mark.asyncio
    async def test_get_by_strategy_returns_none_when_missing(
        self, fk_session: AsyncSession
    ) -> None:
        """``get_by_strategy`` returns ``None`` when no activation exists."""
        repo = SQLModelStrategyActivationRepository(fk_session)
        result = await repo.get_by_strategy(uuid4())
        assert result is None


class TestSQLModelStrategyActivationRepositoryDelete:
    """Direct-delete behaviour."""

    @pytest.mark.asyncio
    async def test_delete_removes_activation(self, fk_session: AsyncSession) -> None:
        """``delete`` should remove the activation row."""
        user_id = uuid4()
        strategy, portfolio = await _insert_strategy_and_portfolio(fk_session, user_id)
        repo = SQLModelStrategyActivationRepository(fk_session)

        activation = _make_activation(
            strategy_id=strategy.id,
            portfolio_id=portfolio.id,
            user_id=user_id,
        )
        await repo.save(activation)
        await fk_session.commit()

        await repo.delete(activation.id)
        await fk_session.commit()

        assert await repo.get(activation.id) is None

    @pytest.mark.asyncio
    async def test_delete_missing_id_is_noop(self, fk_session: AsyncSession) -> None:
        """Deleting a missing id must not raise."""
        repo = SQLModelStrategyActivationRepository(fk_session)
        await repo.delete(uuid4())  # should not raise


class TestSQLModelStrategyActivationRepositoryFkCascade:
    """Foreign-key ``ON DELETE CASCADE`` behaviour."""

    @pytest.mark.asyncio
    async def test_portfolio_delete_cascades_to_activation(
        self, fk_session: AsyncSession
    ) -> None:
        """Deleting the portfolio should remove the activation via FK cascade."""
        user_id = uuid4()
        strategy, portfolio = await _insert_strategy_and_portfolio(fk_session, user_id)
        repo = SQLModelStrategyActivationRepository(fk_session)

        activation = _make_activation(
            strategy_id=strategy.id,
            portfolio_id=portfolio.id,
            user_id=user_id,
        )
        await repo.save(activation)
        await fk_session.commit()

        # Sanity: row exists.
        assert await repo.get(activation.id) is not None

        # Delete the portfolio row directly via the model (the portfolio
        # repository would do the same thing).
        portfolio_model = await fk_session.get(PortfolioModel, portfolio.id)
        assert portfolio_model is not None
        await fk_session.delete(portfolio_model)
        await fk_session.commit()

        # Activation should be gone via cascade.
        assert await repo.get(activation.id) is None

    @pytest.mark.asyncio
    async def test_strategy_delete_cascades_to_activation(
        self, fk_session: AsyncSession
    ) -> None:
        """Deleting the strategy should remove the activation via FK cascade."""
        user_id = uuid4()
        strategy, portfolio = await _insert_strategy_and_portfolio(fk_session, user_id)
        repo = SQLModelStrategyActivationRepository(fk_session)

        activation = _make_activation(
            strategy_id=strategy.id,
            portfolio_id=portfolio.id,
            user_id=user_id,
        )
        await repo.save(activation)
        await fk_session.commit()

        strategy_model = await fk_session.get(StrategyModel, strategy.id)
        assert strategy_model is not None
        await fk_session.delete(strategy_model)
        await fk_session.commit()

        assert await repo.get(activation.id) is None
