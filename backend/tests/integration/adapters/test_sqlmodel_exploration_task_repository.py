"""Integration tests for SQLModelExplorationTaskRepository.

Phase C4 — exercises:

* CRUD round-trip (create / read / update / delete) with the in-memory
  SQLite engine.
* The state-machine helpers when persisted via ``save``.
* The atomic ``claim_atomic`` UPDATE-with-WHERE-status pattern, including
  the loser path (a second claim returns ``None``).
* FK behaviour for ``target_portfolio_id`` -> ``portfolios``: a portfolio
  delete should set the column to ``NULL`` once #224's FK migration lands;
  for the moment we just verify the column tracking is correct.
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from zebu.adapters.outbound.database.exploration_task_repository import (
    SQLModelExplorationTaskRepository,
)
from zebu.domain.entities.exploration_task import (
    ExplorationConstraints,
    ExplorationFindings,
    ExplorationTask,
    ExplorationTaskStatus,
    InvalidExplorationTaskError,
)
from zebu.domain.value_objects.strategy_type import StrategyType
from zebu.domain.value_objects.ticker import Ticker


def _make_task(
    *,
    user_id: object | None = None,
    prompt: str = "Investigate AAPL",
    portfolio_id: object | None = None,
    tickers: list[Ticker] | None = None,
    constraints: ExplorationConstraints | None = None,
) -> ExplorationTask:
    """Factory helper for valid OPEN tasks."""
    now = datetime.now(UTC) - timedelta(seconds=5)
    return ExplorationTask(
        id=uuid4(),
        created_by=user_id if user_id is not None else uuid4(),  # type: ignore[arg-type]
        prompt=prompt,
        status=ExplorationTaskStatus.OPEN,
        created_at=now,
        updated_at=now,
        target_portfolio_id=portfolio_id,  # type: ignore[arg-type]
        tickers=tickers,
        constraints=constraints,
    )


class TestRoundTrip:
    @pytest.mark.asyncio
    async def test_save_and_get_minimal_task(self, session):
        repo = SQLModelExplorationTaskRepository(session)
        task = _make_task()
        await repo.save(task)
        await session.commit()

        loaded = await repo.get(task.id)
        assert loaded is not None
        assert loaded.id == task.id
        assert loaded.created_by == task.created_by
        assert loaded.prompt == task.prompt
        assert loaded.status is ExplorationTaskStatus.OPEN
        assert loaded.target_portfolio_id is None
        assert loaded.tickers is None
        assert loaded.constraints is None
        assert loaded.findings is None
        assert loaded.claimed_by is None
        assert loaded.claimed_at is None

    @pytest.mark.asyncio
    async def test_save_and_get_task_with_full_payload(self, session):
        repo = SQLModelExplorationTaskRepository(session)
        portfolio_id = uuid4()
        task = _make_task(
            portfolio_id=portfolio_id,
            tickers=[Ticker("AAPL"), Ticker("MSFT")],
            constraints=ExplorationConstraints(
                max_backtests=10,
                allow_live_activation=False,
                strategy_type_whitelist=[
                    StrategyType.MOVING_AVERAGE_CROSSOVER,
                    StrategyType.DOLLAR_COST_AVERAGING,
                ],
            ),
        )
        await repo.save(task)
        await session.commit()

        loaded = await repo.get(task.id)
        assert loaded is not None
        assert loaded.target_portfolio_id == portfolio_id
        assert loaded.tickers is not None
        assert [t.symbol for t in loaded.tickers] == ["AAPL", "MSFT"]
        assert loaded.constraints is not None
        assert loaded.constraints.max_backtests == 10
        assert loaded.constraints.allow_live_activation is False
        assert loaded.constraints.strategy_type_whitelist == [
            StrategyType.MOVING_AVERAGE_CROSSOVER,
            StrategyType.DOLLAR_COST_AVERAGING,
        ]

    @pytest.mark.asyncio
    async def test_get_nonexistent_returns_none(self, session):
        repo = SQLModelExplorationTaskRepository(session)
        result = await repo.get(uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_save_updates_existing(self, session):
        repo = SQLModelExplorationTaskRepository(session)
        task = _make_task()
        await repo.save(task)
        await session.commit()

        # Transition to IN_PROGRESS via the entity helper, then save.
        claimed = task.claim(agent_id="agent-a", claimed_at=datetime.now(UTC))
        await repo.save(claimed)
        await session.commit()

        loaded = await repo.get(task.id)
        assert loaded is not None
        assert loaded.status is ExplorationTaskStatus.IN_PROGRESS
        assert loaded.claimed_by == "agent-a"

    @pytest.mark.asyncio
    async def test_delete_removes_task(self, session):
        repo = SQLModelExplorationTaskRepository(session)
        task = _make_task()
        await repo.save(task)
        await session.commit()

        await repo.delete(task.id)
        await session.commit()

        assert await repo.get(task.id) is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_is_noop(self, session):
        repo = SQLModelExplorationTaskRepository(session)
        # Should not raise.
        await repo.delete(uuid4())
        await session.commit()

    @pytest.mark.asyncio
    async def test_done_with_findings_round_trip(self, session):
        repo = SQLModelExplorationTaskRepository(session)
        task = _make_task()
        await repo.save(task)
        await session.commit()

        run_id = uuid4()
        strategy_id = uuid4()
        completed = task.claim(
            agent_id="agent-a", claimed_at=datetime.now(UTC)
        ).complete(
            findings=ExplorationFindings(
                summary="ran 3 backtests, #2 won",
                backtest_run_ids=[run_id],
                strategy_ids=[strategy_id],
                notes=["volatility was unusual on day 5"],
            ),
            completed_at=datetime.now(UTC),
        )
        await repo.save(completed)
        await session.commit()

        loaded = await repo.get(task.id)
        assert loaded is not None
        assert loaded.status is ExplorationTaskStatus.DONE
        assert loaded.findings is not None
        assert loaded.findings.summary == "ran 3 backtests, #2 won"
        assert loaded.findings.backtest_run_ids == [run_id]
        assert loaded.findings.strategy_ids == [strategy_id]
        assert loaded.findings.notes == ["volatility was unusual on day 5"]


class TestListAndCount:
    @pytest.mark.asyncio
    async def test_list_by_status_oldest_first(self, session):
        repo = SQLModelExplorationTaskRepository(session)
        # Three OPEN tasks with monotonically increasing created_at.
        base = datetime.now(UTC) - timedelta(minutes=10)
        for i in range(3):
            ts = base + timedelta(minutes=i)
            task = ExplorationTask(
                id=uuid4(),
                created_by=uuid4(),
                prompt=f"task {i}",
                status=ExplorationTaskStatus.OPEN,
                created_at=ts,
                updated_at=ts,
            )
            await repo.save(task)
        await session.commit()

        results = await repo.list_by_status(ExplorationTaskStatus.OPEN)
        assert len(results) == 3
        assert results[0].prompt == "task 0"
        assert results[2].prompt == "task 2"

    @pytest.mark.asyncio
    async def test_list_by_status_filters(self, session):
        repo = SQLModelExplorationTaskRepository(session)
        open_task = _make_task()
        await repo.save(open_task)
        claimed_task = _make_task().claim(
            agent_id="agent-a", claimed_at=datetime.now(UTC)
        )
        await repo.save(claimed_task)
        await session.commit()

        opens = await repo.list_by_status(ExplorationTaskStatus.OPEN)
        in_progress = await repo.list_by_status(ExplorationTaskStatus.IN_PROGRESS)
        assert len(opens) == 1
        assert len(in_progress) == 1
        assert opens[0].id == open_task.id
        assert in_progress[0].id == claimed_task.id

    @pytest.mark.asyncio
    async def test_list_by_status_paginates(self, session):
        repo = SQLModelExplorationTaskRepository(session)
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
        await session.commit()

        page = await repo.list_by_status(ExplorationTaskStatus.OPEN, limit=2, offset=2)
        assert len(page) == 2
        assert page[0].prompt == "task 2"
        assert page[1].prompt == "task 3"

    @pytest.mark.asyncio
    async def test_list_for_user_newest_first(self, session):
        repo = SQLModelExplorationTaskRepository(session)
        user_id = uuid4()
        base = datetime.now(UTC) - timedelta(minutes=10)
        for i in range(3):
            ts = base + timedelta(minutes=i)
            await repo.save(
                ExplorationTask(
                    id=uuid4(),
                    created_by=user_id,
                    prompt=f"task {i}",
                    status=ExplorationTaskStatus.OPEN,
                    created_at=ts,
                    updated_at=ts,
                )
            )
        # Add a task by another user so the filter is exercised.
        await repo.save(_make_task())
        await session.commit()

        results = await repo.list_for_user(user_id)
        assert len(results) == 3
        assert results[0].prompt == "task 2"  # Newest first
        assert results[2].prompt == "task 0"

    @pytest.mark.asyncio
    async def test_count_by_status(self, session):
        repo = SQLModelExplorationTaskRepository(session)
        await repo.save(_make_task())
        await repo.save(_make_task())
        await repo.save(
            _make_task().claim(agent_id="agent-a", claimed_at=datetime.now(UTC))
        )
        await session.commit()

        assert await repo.count_by_status(ExplorationTaskStatus.OPEN) == 2
        assert await repo.count_by_status(ExplorationTaskStatus.IN_PROGRESS) == 1
        assert await repo.count_by_status(ExplorationTaskStatus.DONE) == 0

    @pytest.mark.asyncio
    async def test_count_for_user(self, session):
        repo = SQLModelExplorationTaskRepository(session)
        user_id = uuid4()
        await repo.save(_make_task(user_id=user_id))
        await repo.save(_make_task(user_id=user_id))
        await repo.save(_make_task())  # Different user.
        await session.commit()

        assert await repo.count_for_user(user_id) == 2
        # Filtered by status — both are still OPEN.
        assert (
            await repo.count_for_user(user_id, status=ExplorationTaskStatus.OPEN) == 2
        )
        assert (
            await repo.count_for_user(user_id, status=ExplorationTaskStatus.DONE) == 0
        )


class TestClaimAtomic:
    @pytest.mark.asyncio
    async def test_claim_open_succeeds(self, session):
        repo = SQLModelExplorationTaskRepository(session)
        task = _make_task()
        await repo.save(task)
        await session.commit()

        claimed = await repo.claim_atomic(
            task.id, agent_id="agent-a", claimed_at=datetime.now(UTC)
        )
        assert claimed is not None
        assert claimed.status is ExplorationTaskStatus.IN_PROGRESS
        assert claimed.claimed_by == "agent-a"
        assert claimed.claimed_at is not None

    @pytest.mark.asyncio
    async def test_double_claim_returns_none(self, session):
        """The "race-loser" path — second claim returns None.

        Both claims happen sequentially in this test, but the same UPDATE
        path is what serialises concurrent callers in production. The
        contract that matters is: only one claim ever succeeds.
        """
        repo = SQLModelExplorationTaskRepository(session)
        task = _make_task()
        await repo.save(task)
        await session.commit()

        first = await repo.claim_atomic(
            task.id, agent_id="agent-a", claimed_at=datetime.now(UTC)
        )
        await session.commit()
        assert first is not None

        second = await repo.claim_atomic(
            task.id, agent_id="agent-b", claimed_at=datetime.now(UTC)
        )
        assert second is None

        loaded = await repo.get(task.id)
        assert loaded is not None
        # Only the first agent's claim sticks.
        assert loaded.claimed_by == "agent-a"

    @pytest.mark.asyncio
    async def test_claim_nonexistent_returns_none(self, session):
        repo = SQLModelExplorationTaskRepository(session)
        result = await repo.claim_atomic(
            uuid4(), agent_id="agent-a", claimed_at=datetime.now(UTC)
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_claim_already_done_returns_none(self, session):
        repo = SQLModelExplorationTaskRepository(session)
        task = _make_task()
        await repo.save(task)
        completed = task.claim(
            agent_id="agent-a", claimed_at=datetime.now(UTC)
        ).complete(
            findings=ExplorationFindings(summary="x"),
            completed_at=datetime.now(UTC),
        )
        await repo.save(completed)
        await session.commit()

        result = await repo.claim_atomic(
            task.id, agent_id="agent-b", claimed_at=datetime.now(UTC)
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_claim_empty_agent_id_raises(self, session):
        repo = SQLModelExplorationTaskRepository(session)
        with pytest.raises(InvalidExplorationTaskError):
            await repo.claim_atomic(uuid4(), agent_id="", claimed_at=datetime.now(UTC))
