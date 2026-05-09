"""Tests for InMemoryStrategyActivationRepository.

The in-memory repository is a test helper for higher-level services that
arrive in Phase C1.2 / C1.3 (the scheduler job, execution service, and API
handlers). These tests exercise its behaviour directly so the helper is
trustworthy when downstream tests rely on it.
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from zebu.application.ports.in_memory_strategy_activation_repository import (
    InMemoryStrategyActivationRepository,
)
from zebu.domain.entities.strategy_activation import StrategyActivation
from zebu.domain.value_objects.activation_frequency import ActivationFrequency
from zebu.domain.value_objects.activation_status import ActivationStatus


def _make_activation(
    *,
    user_id: UUID | None = None,
    strategy_id: UUID | None = None,
    portfolio_id: UUID | None = None,
    status: ActivationStatus = ActivationStatus.ACTIVE,
    created_at: datetime | None = None,
) -> StrategyActivation:
    """Factory helper for tests."""
    if created_at is None:
        created_at = datetime.now(UTC) - timedelta(minutes=5)
    return StrategyActivation(
        id=uuid4(),
        user_id=user_id if user_id is not None else uuid4(),
        strategy_id=strategy_id if strategy_id is not None else uuid4(),
        portfolio_id=portfolio_id if portfolio_id is not None else uuid4(),
        status=status,
        frequency=ActivationFrequency.DAILY_MARKET_CLOSE,
        created_at=created_at,
        updated_at=created_at,
    )


@pytest.mark.asyncio
class TestInMemoryStrategyActivationRepository:
    async def test_save_and_get(self) -> None:
        """Saving an activation and getting it should return the same entity."""
        repo = InMemoryStrategyActivationRepository()
        activation = _make_activation()
        await repo.save(activation)
        loaded = await repo.get(activation.id)
        assert loaded is activation

    async def test_get_missing_returns_none(self) -> None:
        """get() returns None for an unknown id."""
        repo = InMemoryStrategyActivationRepository()
        assert await repo.get(uuid4()) is None

    async def test_save_is_idempotent_upsert(self) -> None:
        """Re-saving the same id replaces the previous entity."""
        repo = InMemoryStrategyActivationRepository()
        activation = _make_activation(status=ActivationStatus.ACTIVE)
        await repo.save(activation)

        replacement = StrategyActivation(
            id=activation.id,
            user_id=activation.user_id,
            strategy_id=activation.strategy_id,
            portfolio_id=activation.portfolio_id,
            status=ActivationStatus.PAUSED,
            frequency=activation.frequency,
            created_at=activation.created_at,
            updated_at=datetime.now(UTC),
        )
        await repo.save(replacement)

        loaded = await repo.get(activation.id)
        assert loaded is not None
        assert loaded.status is ActivationStatus.PAUSED

    async def test_delete_removes(self) -> None:
        """delete() removes the entity by id."""
        repo = InMemoryStrategyActivationRepository()
        activation = _make_activation()
        await repo.save(activation)
        await repo.delete(activation.id)
        assert await repo.get(activation.id) is None

    async def test_delete_missing_is_noop(self) -> None:
        """Deleting a missing id is a no-op."""
        repo = InMemoryStrategyActivationRepository()
        await repo.delete(uuid4())  # should not raise

    async def test_list_active_filters_by_status(self) -> None:
        """list_active() returns only ACTIVE entities."""
        repo = InMemoryStrategyActivationRepository()
        active = _make_activation(status=ActivationStatus.ACTIVE)
        paused = _make_activation(status=ActivationStatus.PAUSED)
        stopped = _make_activation(status=ActivationStatus.STOPPED)
        error = _make_activation(status=ActivationStatus.ACTIVE)
        for a in (active, paused, stopped, error):
            await repo.save(a)

        results = await repo.list_active()
        ids = {a.id for a in results}
        assert active.id in ids
        assert error.id in ids
        assert paused.id not in ids
        assert stopped.id not in ids

    async def test_list_active_orders_oldest_first(self) -> None:
        """list_active() returns ACTIVE entities oldest first."""
        repo = InMemoryStrategyActivationRepository()
        now = datetime.now(UTC)
        older = _make_activation(created_at=now - timedelta(hours=2))
        newer = _make_activation(created_at=now - timedelta(hours=1))
        # Save newer first so list ordering is meaningful.
        await repo.save(newer)
        await repo.save(older)

        results = await repo.list_active()
        assert [a.id for a in results] == [older.id, newer.id]

    async def test_list_for_user_scopes_by_user(self) -> None:
        """list_for_user() returns only that user's activations."""
        repo = InMemoryStrategyActivationRepository()
        user_a = uuid4()
        user_b = uuid4()
        own = _make_activation(user_id=user_a)
        other = _make_activation(user_id=user_b)
        await repo.save(own)
        await repo.save(other)

        results = await repo.list_for_user(user_a)
        assert len(results) == 1
        assert results[0].id == own.id

    async def test_list_for_user_empty(self) -> None:
        """A user with no activations returns an empty list."""
        repo = InMemoryStrategyActivationRepository()
        assert await repo.list_for_user(uuid4()) == []

    async def test_list_for_user_includes_all_statuses(self) -> None:
        """list_for_user() does not filter by status."""
        repo = InMemoryStrategyActivationRepository()
        user_id = uuid4()
        active = _make_activation(user_id=user_id, status=ActivationStatus.ACTIVE)
        paused = _make_activation(user_id=user_id, status=ActivationStatus.PAUSED)
        await repo.save(active)
        await repo.save(paused)

        results = await repo.list_for_user(user_id)
        statuses = {a.status for a in results}
        assert statuses == {ActivationStatus.ACTIVE, ActivationStatus.PAUSED}

    async def test_get_by_strategy_returns_match(self) -> None:
        """get_by_strategy() returns the activation linked to a strategy."""
        repo = InMemoryStrategyActivationRepository()
        strategy_id = uuid4()
        activation = _make_activation(strategy_id=strategy_id)
        await repo.save(activation)

        loaded = await repo.get_by_strategy(strategy_id)
        assert loaded is activation

    async def test_get_by_strategy_returns_none_when_missing(self) -> None:
        """get_by_strategy() returns None when no activation matches."""
        repo = InMemoryStrategyActivationRepository()
        assert await repo.get_by_strategy(uuid4()) is None

    async def test_get_by_strategy_returns_latest_when_duplicates(self) -> None:
        """If multiple activations share a strategy_id, return the latest one.

        The repository uniqueness is enforced at the API layer; if the
        invariant is broken, the in-memory repo should still behave
        deterministically.
        """
        repo = InMemoryStrategyActivationRepository()
        strategy_id = uuid4()
        now = datetime.now(UTC)
        older = _make_activation(
            strategy_id=strategy_id, created_at=now - timedelta(hours=2)
        )
        newer = _make_activation(
            strategy_id=strategy_id, created_at=now - timedelta(hours=1)
        )
        await repo.save(older)
        await repo.save(newer)

        loaded = await repo.get_by_strategy(strategy_id)
        assert loaded is not None
        assert loaded.id == newer.id

    async def test_clear(self) -> None:
        """clear() removes all activations (a test helper)."""
        repo = InMemoryStrategyActivationRepository()
        await repo.save(_make_activation())
        await repo.save(_make_activation())
        repo.clear()
        assert await repo.list_active() == []
