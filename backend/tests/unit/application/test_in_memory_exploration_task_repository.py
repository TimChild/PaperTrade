"""Unit tests for InMemoryExplorationTaskRepository.

The in-memory adapter is the test double the API and command-handler tests
will reach for. Its behaviour must mirror the SQLModel adapter on the
contract: most importantly, ``claim_atomic`` must serialise concurrent
callers so two agents can never share a claim.
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from zebu.application.ports.in_memory_exploration_task_repository import (
    InMemoryExplorationTaskRepository,
)
from zebu.domain.entities.exploration_task import (
    ExplorationFindings,
    ExplorationTask,
    ExplorationTaskStatus,
)


def _make_task(*, user_id: object | None = None) -> ExplorationTask:
    """Factory helper for valid OPEN tasks."""
    now = datetime.now(UTC) - timedelta(seconds=5)
    return ExplorationTask(
        id=uuid4(),
        created_by=user_id if user_id is not None else uuid4(),  # type: ignore[arg-type]
        prompt="Investigate AAPL",
        status=ExplorationTaskStatus.OPEN,
        created_at=now,
        updated_at=now,
    )


class TestSaveGetDelete:
    @pytest.mark.asyncio
    async def test_save_and_get(self) -> None:
        repo = InMemoryExplorationTaskRepository()
        task = _make_task()
        await repo.save(task)
        loaded = await repo.get(task.id)
        assert loaded is not None
        assert loaded.id == task.id

    @pytest.mark.asyncio
    async def test_get_missing_returns_none(self) -> None:
        repo = InMemoryExplorationTaskRepository()
        assert await repo.get(uuid4()) is None

    @pytest.mark.asyncio
    async def test_save_idempotent_upsert(self) -> None:
        repo = InMemoryExplorationTaskRepository()
        task = _make_task()
        await repo.save(task)
        # Saving again with the same id is a no-op upsert.
        await repo.save(task)
        loaded = await repo.get(task.id)
        assert loaded is not None

    @pytest.mark.asyncio
    async def test_delete_removes(self) -> None:
        repo = InMemoryExplorationTaskRepository()
        task = _make_task()
        await repo.save(task)
        await repo.delete(task.id)
        assert await repo.get(task.id) is None

    @pytest.mark.asyncio
    async def test_delete_missing_is_noop(self) -> None:
        repo = InMemoryExplorationTaskRepository()
        await repo.delete(uuid4())  # Should not raise.

    @pytest.mark.asyncio
    async def test_clear(self) -> None:
        repo = InMemoryExplorationTaskRepository()
        await repo.save(_make_task())
        await repo.save(_make_task())
        repo.clear()
        # All gone.
        assert await repo.count_by_status(ExplorationTaskStatus.OPEN) == 0


class TestListAndCount:
    @pytest.mark.asyncio
    async def test_list_by_status_oldest_first(self) -> None:
        repo = InMemoryExplorationTaskRepository()
        base = datetime.now(UTC) - timedelta(minutes=10)
        for i in range(3):
            ts = base + timedelta(minutes=i)
            await repo.save(
                ExplorationTask(
                    id=uuid4(),
                    created_by=uuid4(),
                    prompt=f"task {i}",
                    status=ExplorationTaskStatus.OPEN,
                    created_at=ts,
                    updated_at=ts,
                )
            )
        results = await repo.list_by_status(ExplorationTaskStatus.OPEN)
        assert [r.prompt for r in results] == ["task 0", "task 1", "task 2"]

    @pytest.mark.asyncio
    async def test_list_by_status_paginates(self) -> None:
        repo = InMemoryExplorationTaskRepository()
        base = datetime.now(UTC) - timedelta(minutes=10)
        for i in range(5):
            ts = base + timedelta(seconds=i)
            await repo.save(
                ExplorationTask(
                    id=uuid4(),
                    created_by=uuid4(),
                    prompt=f"task {i}",
                    status=ExplorationTaskStatus.OPEN,
                    created_at=ts,
                    updated_at=ts,
                )
            )
        page = await repo.list_by_status(ExplorationTaskStatus.OPEN, limit=2, offset=2)
        assert [t.prompt for t in page] == ["task 2", "task 3"]

    @pytest.mark.asyncio
    async def test_list_for_user_newest_first(self) -> None:
        repo = InMemoryExplorationTaskRepository()
        user_id = uuid4()
        base = datetime.now(UTC) - timedelta(minutes=10)
        for i in range(3):
            ts = base + timedelta(minutes=i)
            await repo.save(
                ExplorationTask(
                    id=uuid4(),
                    created_by=user_id,
                    prompt=f"t{i}",
                    status=ExplorationTaskStatus.OPEN,
                    created_at=ts,
                    updated_at=ts,
                )
            )
        results = await repo.list_for_user(user_id)
        assert [r.prompt for r in results] == ["t2", "t1", "t0"]

    @pytest.mark.asyncio
    async def test_list_for_user_filters_status(self) -> None:
        repo = InMemoryExplorationTaskRepository()
        user_id = uuid4()
        await repo.save(_make_task(user_id=user_id))
        claimed = _make_task(user_id=user_id).claim(
            agent_id="agent-a", claimed_at=datetime.now(UTC)
        )
        await repo.save(claimed)

        opens = await repo.list_for_user(user_id, status=ExplorationTaskStatus.OPEN)
        in_progress = await repo.list_for_user(
            user_id, status=ExplorationTaskStatus.IN_PROGRESS
        )
        assert len(opens) == 1
        assert len(in_progress) == 1

    @pytest.mark.asyncio
    async def test_count_by_status(self) -> None:
        repo = InMemoryExplorationTaskRepository()
        await repo.save(_make_task())
        await repo.save(_make_task())
        await repo.save(
            _make_task().claim(agent_id="agent-a", claimed_at=datetime.now(UTC))
        )
        assert await repo.count_by_status(ExplorationTaskStatus.OPEN) == 2
        assert await repo.count_by_status(ExplorationTaskStatus.IN_PROGRESS) == 1

    @pytest.mark.asyncio
    async def test_count_for_user(self) -> None:
        repo = InMemoryExplorationTaskRepository()
        user_id = uuid4()
        await repo.save(_make_task(user_id=user_id))
        await repo.save(_make_task(user_id=user_id))
        await repo.save(_make_task())
        assert await repo.count_for_user(user_id) == 2
        assert (
            await repo.count_for_user(user_id, status=ExplorationTaskStatus.OPEN) == 2
        )
        assert (
            await repo.count_for_user(user_id, status=ExplorationTaskStatus.DONE) == 0
        )


class TestClaimAtomic:
    @pytest.mark.asyncio
    async def test_claim_open_succeeds(self) -> None:
        repo = InMemoryExplorationTaskRepository()
        task = _make_task()
        await repo.save(task)
        result = await repo.claim_atomic(
            task.id, agent_id="agent-a", claimed_at=datetime.now(UTC)
        )
        assert result is not None
        assert result.status is ExplorationTaskStatus.IN_PROGRESS

    @pytest.mark.asyncio
    async def test_double_claim_returns_none(self) -> None:
        repo = InMemoryExplorationTaskRepository()
        task = _make_task()
        await repo.save(task)
        first = await repo.claim_atomic(
            task.id, agent_id="agent-a", claimed_at=datetime.now(UTC)
        )
        second = await repo.claim_atomic(
            task.id, agent_id="agent-b", claimed_at=datetime.now(UTC)
        )
        assert first is not None
        assert second is None
        loaded = await repo.get(task.id)
        assert loaded is not None
        assert loaded.claimed_by == "agent-a"

    @pytest.mark.asyncio
    async def test_claim_nonexistent_returns_none(self) -> None:
        repo = InMemoryExplorationTaskRepository()
        result = await repo.claim_atomic(
            uuid4(), agent_id="agent-a", claimed_at=datetime.now(UTC)
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_claim_done_task_returns_none(self) -> None:
        repo = InMemoryExplorationTaskRepository()
        task = _make_task()
        completed = task.claim(
            agent_id="agent-a", claimed_at=datetime.now(UTC)
        ).complete(
            findings=ExplorationFindings(summary="x"),
            completed_at=datetime.now(UTC),
        )
        await repo.save(completed)
        result = await repo.claim_atomic(
            task.id, agent_id="agent-b", claimed_at=datetime.now(UTC)
        )
        assert result is None
