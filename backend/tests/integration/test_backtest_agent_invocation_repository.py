"""Integration tests for :class:`SQLModelBacktestAgentInvocationRepository`.

Phase L-1 (Task #217). Tests run against the FK-enabled in-memory SQLite
``engine`` from ``backend/tests/integration/conftest.py``. Coverage:

* Round-trip persistence (save -> get reproduces the entity, including
  JSON columns).
* ``save_all`` bulk insert.
* Duplicate-id raises ``ValueError`` (mapped from IntegrityError).
* Chronological ordering on ``list_for_backtest_run``.
* ``count_for_backtest_run`` matches ``len(list_for_backtest_run(...))``.
* FK cascade: deleting the parent ``BacktestRun`` row removes all
  invocations.
* FK set-null on ``trigger_id``: deleting the parent trigger nulls the
  column; reloading still works (domain entity accepts ``None``).
* Bulk insert with 500 rows completes in < 1s (sanity check).
"""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlmodel import delete
from sqlmodel.ext.asyncio.session import AsyncSession

from zebu.adapters.outbound.database.api_key_model import ApiKeyModel
from zebu.adapters.outbound.database.backtest_agent_invocation_repository import (
    SQLModelBacktestAgentInvocationRepository,
)
from zebu.adapters.outbound.database.models import (
    BacktestRunModel,
    PortfolioModel,
    StrategyActivationModel,
    StrategyConditionTriggerModel,
    StrategyModel,
)
from zebu.domain.entities.api_key import ApiKey
from zebu.domain.entities.backtest_agent_invocation import BacktestAgentInvocation
from zebu.domain.entities.backtest_run import BacktestRun
from zebu.domain.entities.portfolio import Portfolio
from zebu.domain.entities.strategy import Strategy
from zebu.domain.entities.strategy_activation import StrategyActivation
from zebu.domain.entities.strategy_condition_trigger import StrategyConditionTrigger
from zebu.domain.value_objects.activation_frequency import ActivationFrequency
from zebu.domain.value_objects.activation_status import ActivationStatus
from zebu.domain.value_objects.agent_decision import AgentDecision
from zebu.domain.value_objects.api_key_scope import ApiKeyScope
from zebu.domain.value_objects.backtest_agent_invocation_mode import (
    BacktestAgentInvocationMode,
)
from zebu.domain.value_objects.backtest_status import BacktestStatus
from zebu.domain.value_objects.money import Money
from zebu.domain.value_objects.portfolio_type import PortfolioType
from zebu.domain.value_objects.strategy_parameters import BuyAndHoldParameters
from zebu.domain.value_objects.strategy_snapshot import StrategySnapshot
from zebu.domain.value_objects.strategy_type import StrategyType
from zebu.domain.value_objects.trigger_condition import DrawdownParams
from zebu.domain.value_objects.trigger_status import TriggerStatus


class SeedRefs:
    """FK-target IDs the SQL adapter needs to exist."""

    def __init__(
        self,
        *,
        user_id: UUID,
        backtest_run_id: UUID,
        trigger_id: UUID,
    ) -> None:
        self.user_id = user_id
        self.backtest_run_id = backtest_run_id
        self.trigger_id = trigger_id


async def _seed_fk_targets(session: AsyncSession) -> SeedRefs:
    """Insert the rows needed to satisfy the FK constraints on
    ``backtest_agent_invocations``: user / portfolio / strategy /
    activation / api_key / backtest_run / trigger.
    """
    user_id = uuid4()
    portfolio = Portfolio(
        id=uuid4(),
        user_id=user_id,
        name="Backtest Portfolio",
        created_at=datetime.now(UTC) - timedelta(days=2),
        portfolio_type=PortfolioType.BACKTEST,
    )
    session.add(PortfolioModel.from_domain(portfolio))
    await session.flush()

    strategy = Strategy(
        id=uuid4(),
        user_id=user_id,
        name="Backtest Strategy",
        strategy_type=StrategyType.BUY_AND_HOLD,
        tickers=["AAPL"],
        parameters=BuyAndHoldParameters(allocation={"AAPL": Decimal("1.0")}),
        created_at=datetime.now(UTC) - timedelta(days=2),
    )
    session.add(StrategyModel.from_domain(strategy))
    await session.flush()

    activation = StrategyActivation(
        id=uuid4(),
        user_id=user_id,
        strategy_id=strategy.id,
        portfolio_id=portfolio.id,
        status=ActivationStatus.ACTIVE,
        frequency=ActivationFrequency.DAILY_MARKET_CLOSE,
        created_at=datetime.now(UTC) - timedelta(hours=2),
        updated_at=datetime.now(UTC) - timedelta(hours=2),
    )
    session.add(StrategyActivationModel.from_domain(activation))
    await session.flush()

    api_key = ApiKey(
        id=uuid4(),
        user_id=user_id,
        clerk_user_id="test-clerk",
        label="test-key",
        key_hash="h" + "0" * 60,
        scopes=frozenset({ApiKeyScope.READ, ApiKeyScope.TRADE}),
        created_at=datetime.now(UTC) - timedelta(hours=3),
    )
    session.add(ApiKeyModel.from_domain(api_key))
    await session.flush()

    snapshot = StrategySnapshot(
        strategy_id=strategy.id,
        name=strategy.name,
        strategy_type=strategy.strategy_type,
        tickers=tuple(strategy.tickers),
        parameters=strategy.parameters,
    )
    backtest_run = BacktestRun(
        id=uuid4(),
        user_id=user_id,
        strategy_id=strategy.id,
        portfolio_id=portfolio.id,
        strategy_snapshot=snapshot,
        backtest_name="Test Run",
        start_date=date(2024, 6, 1),
        end_date=date(2024, 6, 30),
        initial_cash=Money(Decimal("10000.00"), "USD"),
        status=BacktestStatus.COMPLETED,
        created_at=datetime.now(UTC) - timedelta(hours=1),
        agent_invocation_mode=BacktestAgentInvocationMode.LIVE,
    )
    run_model = BacktestRunModel.from_domain(backtest_run)
    run_model.api_key_id = api_key.id
    session.add(run_model)
    await session.flush()

    when = datetime.now(UTC) - timedelta(seconds=30)
    trigger = StrategyConditionTrigger(
        id=uuid4(),
        activation_id=activation.id,
        user_id=user_id,
        condition_type=trigger_condition_type(),
        condition_params=DrawdownParams(
            threshold_pct=Decimal("5"),
            lookback_days=30,
        ),  # type: ignore[arg-type]
        agent_prompt="Decide whether to hold the position.",
        status=TriggerStatus.ACTIVE,
        priority=0,
        cooldown_seconds=21600,
        last_fired_at=None,
        default_api_key_id=None,
        expires_at=None,
        created_at=when,
        updated_at=when,
        created_by=user_id,
    )
    session.add(StrategyConditionTriggerModel.from_domain(trigger))
    await session.flush()

    return SeedRefs(
        user_id=user_id,
        backtest_run_id=backtest_run.id,
        trigger_id=trigger.id,
    )


def trigger_condition_type() -> Any:
    """Resolve at call time so the import order doesn't matter."""
    from zebu.domain.value_objects.trigger_condition import ConditionType

    return ConditionType.DRAWDOWN_THRESHOLD


@pytest_asyncio.fixture
async def sql_repo(
    session: AsyncSession,
) -> AsyncIterator[tuple[SQLModelBacktestAgentInvocationRepository, SeedRefs]]:
    seed = await _seed_fk_targets(session)
    yield (SQLModelBacktestAgentInvocationRepository(session), seed)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock(seed: SeedRefs, **overrides: Any) -> BacktestAgentInvocation:
    defaults: dict[str, Any] = {
        "id": uuid4(),
        "backtest_run_id": seed.backtest_run_id,
        "simulated_date": date(2024, 6, 1),
        "trigger_id": seed.trigger_id,
        "condition_evaluation_data": {"schema_version": 1, "metric": "PRICE"},
        "rationale": "",
        "latency_ms": 0,
        "model": "",
        "invocation_mode": BacktestAgentInvocationMode.MOCK,
        "created_at": datetime.now(UTC) - timedelta(seconds=5),
    }
    defaults.update(overrides)
    return BacktestAgentInvocation(**defaults)


def _make_live_buy(seed: SeedRefs, **overrides: Any) -> BacktestAgentInvocation:
    defaults: dict[str, Any] = {
        "id": uuid4(),
        "backtest_run_id": seed.backtest_run_id,
        "simulated_date": date(2024, 6, 2),
        "trigger_id": seed.trigger_id,
        "condition_evaluation_data": {"schema_version": 1, "metric": "DRAWDOWN"},
        "agent_decision": AgentDecision.BUY,
        "rationale": "Strong dip catalyst — buying back in.",
        "decision_payload": {"ticker": "AAPL", "notes": "scale-in"},
        "decision_executed": True,
        "simulated_trade_id": None,
        "invocation_mode": BacktestAgentInvocationMode.LIVE,
        "agent_invocation_id": "msg_01xyz",
        "latency_ms": 980,
        "model": "claude-haiku-4-5-20251001",
        "created_at": datetime.now(UTC) - timedelta(seconds=2),
    }
    defaults.update(overrides)
    return BacktestAgentInvocation(**defaults)


# ---------------------------------------------------------------------------
# Round-trip persistence
# ---------------------------------------------------------------------------


class TestRoundTrip:
    @pytest.mark.asyncio
    async def test_save_and_get_preserves_all_fields(
        self,
        sql_repo: tuple[SQLModelBacktestAgentInvocationRepository, SeedRefs],
    ) -> None:
        repo, seed = sql_repo
        record = _make_live_buy(seed)
        await repo.save(record)

        loaded = await repo.get(record.id)
        assert loaded is not None
        # Identity-based equality only proves the IDs match — go deeper.
        assert loaded.id == record.id
        assert loaded.backtest_run_id == record.backtest_run_id
        assert loaded.simulated_date == record.simulated_date
        assert loaded.trigger_id == record.trigger_id
        assert loaded.agent_decision == record.agent_decision
        assert loaded.rationale == record.rationale
        assert loaded.invocation_mode is record.invocation_mode
        assert loaded.agent_invocation_id == record.agent_invocation_id
        assert loaded.latency_ms == record.latency_ms
        assert loaded.model == record.model
        assert loaded.decision_executed is True
        assert loaded.decision_payload == record.decision_payload
        assert loaded.condition_evaluation_data == record.condition_evaluation_data

    @pytest.mark.asyncio
    async def test_mock_row_round_trips(
        self,
        sql_repo: tuple[SQLModelBacktestAgentInvocationRepository, SeedRefs],
    ) -> None:
        repo, seed = sql_repo
        record = _make_mock(seed)
        await repo.save(record)
        loaded = await repo.get(record.id)
        assert loaded is not None
        assert loaded.invocation_mode is BacktestAgentInvocationMode.MOCK
        assert loaded.agent_decision is None
        assert loaded.decision_payload is None
        assert loaded.rationale == ""
        assert loaded.model == ""

    @pytest.mark.asyncio
    async def test_get_missing_returns_none(
        self,
        sql_repo: tuple[SQLModelBacktestAgentInvocationRepository, SeedRefs],
    ) -> None:
        repo, _ = sql_repo
        result = await repo.get(uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_save_duplicate_id_raises(
        self,
        sql_repo: tuple[SQLModelBacktestAgentInvocationRepository, SeedRefs],
    ) -> None:
        repo, seed = sql_repo
        record = _make_mock(seed)
        await repo.save(record)
        with pytest.raises(ValueError, match="already exists"):
            await repo.save(record)


# ---------------------------------------------------------------------------
# save_all bulk insert
# ---------------------------------------------------------------------------


class TestSaveAll:
    @pytest.mark.asyncio
    async def test_save_all_round_trips(
        self,
        sql_repo: tuple[SQLModelBacktestAgentInvocationRepository, SeedRefs],
    ) -> None:
        repo, seed = sql_repo
        rows = [
            _make_mock(seed, simulated_date=date(2024, 6, 1)),
            _make_live_buy(seed, simulated_date=date(2024, 6, 2)),
            _make_mock(seed, simulated_date=date(2024, 6, 3)),
        ]
        await repo.save_all(rows)
        for row in rows:
            loaded = await repo.get(row.id)
            assert loaded is not None
            assert loaded.invocation_mode is row.invocation_mode

    @pytest.mark.asyncio
    async def test_save_all_empty_is_noop(
        self,
        sql_repo: tuple[SQLModelBacktestAgentInvocationRepository, SeedRefs],
    ) -> None:
        repo, _ = sql_repo
        await repo.save_all([])

    @pytest.mark.asyncio
    async def test_save_all_duplicate_within_batch_raises(
        self,
        sql_repo: tuple[SQLModelBacktestAgentInvocationRepository, SeedRefs],
    ) -> None:
        repo, seed = sql_repo
        shared = _make_mock(seed)
        twin = _make_mock(seed, id=shared.id)
        with pytest.raises(ValueError, match="Duplicate id"):
            await repo.save_all([shared, twin])

    @pytest.mark.asyncio
    async def test_save_all_500_rows_under_a_second(
        self,
        sql_repo: tuple[SQLModelBacktestAgentInvocationRepository, SeedRefs],
    ) -> None:
        """Sanity check — not a strict perf gate but flags a per-row loop."""
        repo, seed = sql_repo
        rows = [
            _make_mock(
                seed,
                simulated_date=date(2024, 6, 1) + timedelta(days=i % 30),
            )
            for i in range(500)
        ]
        start = time.perf_counter()
        await repo.save_all(rows)
        elapsed = time.perf_counter() - start
        # 500 rows in under 1s — generous on SQLite in-memory.
        assert elapsed < 1.0, f"save_all of 500 rows took {elapsed:.2f}s"
        count = await repo.count_for_backtest_run(seed.backtest_run_id)
        assert count == 500


# ---------------------------------------------------------------------------
# list / count semantics
# ---------------------------------------------------------------------------


class TestListAndCount:
    @pytest.mark.asyncio
    async def test_list_chronological(
        self,
        sql_repo: tuple[SQLModelBacktestAgentInvocationRepository, SeedRefs],
    ) -> None:
        repo, seed = sql_repo
        first = _make_mock(seed, simulated_date=date(2024, 6, 1))
        second = _make_mock(seed, simulated_date=date(2024, 6, 2))
        third = _make_mock(seed, simulated_date=date(2024, 6, 3))
        await repo.save_all([third, first, second])

        result = await repo.list_for_backtest_run(seed.backtest_run_id)
        assert [r.id for r in result] == [first.id, second.id, third.id]

    @pytest.mark.asyncio
    async def test_count_matches_list(
        self,
        sql_repo: tuple[SQLModelBacktestAgentInvocationRepository, SeedRefs],
    ) -> None:
        repo, seed = sql_repo
        await repo.save_all(
            [
                _make_mock(seed, simulated_date=date(2024, 6, 1) + timedelta(days=i))
                for i in range(4)
            ]
        )
        count = await repo.count_for_backtest_run(seed.backtest_run_id)
        rows = await repo.list_for_backtest_run(seed.backtest_run_id)
        assert count == len(rows) == 4

    @pytest.mark.asyncio
    async def test_pagination(
        self,
        sql_repo: tuple[SQLModelBacktestAgentInvocationRepository, SeedRefs],
    ) -> None:
        repo, seed = sql_repo
        await repo.save_all(
            [
                _make_mock(seed, simulated_date=date(2024, 6, 1) + timedelta(days=i))
                for i in range(5)
            ]
        )
        page_1 = await repo.list_for_backtest_run(
            seed.backtest_run_id, limit=2, offset=0
        )
        page_2 = await repo.list_for_backtest_run(
            seed.backtest_run_id, limit=2, offset=2
        )
        assert len(page_1) == 2
        assert len(page_2) == 2
        # Pages are non-overlapping.
        assert {r.id for r in page_1}.isdisjoint({r.id for r in page_2})


# ---------------------------------------------------------------------------
# FK behaviour
# ---------------------------------------------------------------------------


class TestForeignKeyBehavior:
    @pytest.mark.asyncio
    async def test_cascade_on_backtest_run_delete(
        self,
        sql_repo: tuple[SQLModelBacktestAgentInvocationRepository, SeedRefs],
        session: AsyncSession,
    ) -> None:
        """Deleting the parent BacktestRun row removes all invocations."""
        repo, seed = sql_repo
        await repo.save(_make_mock(seed))
        assert await repo.count_for_backtest_run(seed.backtest_run_id) == 1

        await session.exec(
            delete(BacktestRunModel).where(
                BacktestRunModel.id == seed.backtest_run_id  # type: ignore[arg-type]
            )
        )
        await session.flush()

        assert await repo.count_for_backtest_run(seed.backtest_run_id) == 0

    @pytest.mark.asyncio
    async def test_set_null_on_trigger_delete(
        self,
        sql_repo: tuple[SQLModelBacktestAgentInvocationRepository, SeedRefs],
        session: AsyncSession,
    ) -> None:
        """Deleting the parent Trigger sets ``trigger_id`` on the row to NULL.

        Reloading the entity reflects the null — the domain class allows
        ``trigger_id is None`` for this recovered state.
        """
        repo, seed = sql_repo
        record = _make_mock(seed)
        await repo.save(record)

        await session.exec(
            delete(StrategyConditionTriggerModel).where(
                StrategyConditionTriggerModel.id == seed.trigger_id  # type: ignore[arg-type]
            )
        )
        await session.flush()
        # The session may have stale in-memory state — expire the
        # cached identity-map row so the next get() re-reads from DB.
        session.expire_all()

        loaded = await repo.get(record.id)
        assert loaded is not None
        assert loaded.trigger_id is None
