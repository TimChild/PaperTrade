"""Integration tests for the trigger / fire repositories (Phase F-1).

Covers both the in-memory and SQLModel adapters via parameterised
fixtures so any behaviour difference between the two surfaces in CI.

Scope:

* Round-trip persistence (save → get reproduces the entity).
* List / count semantics (newest-first, ordering, filtering).
* ``list_evaluable`` ordering: ``(priority DESC, created_at ASC)``.
* Kill-switch helpers (``disable_all_for_user`` / ``disable_all``).
* Append-only ``TriggerFireRecord.save`` raises on duplicate ID.
* JSON column round-trips for the discriminated condition params.
"""

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Protocol
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlmodel.ext.asyncio.session import AsyncSession

from zebu.adapters.outbound.database.api_key_model import ApiKeyModel
from zebu.adapters.outbound.database.models import (
    PortfolioModel,
    StrategyActivationModel,
    StrategyModel,
)
from zebu.adapters.outbound.database.strategy_condition_trigger_repository import (
    SQLModelTriggerRepository,
)
from zebu.adapters.outbound.database.trigger_fire_repository import (
    SQLModelTriggerFireRepository,
)
from zebu.application.ports.in_memory_trigger_fire_repository import (
    InMemoryTriggerFireRepository,
)
from zebu.application.ports.in_memory_trigger_repository import (
    InMemoryTriggerRepository,
)
from zebu.domain.entities.api_key import ApiKey
from zebu.domain.entities.portfolio import Portfolio
from zebu.domain.entities.strategy import Strategy
from zebu.domain.entities.strategy_activation import StrategyActivation
from zebu.domain.entities.strategy_condition_trigger import StrategyConditionTrigger
from zebu.domain.entities.trigger_fire_record import TriggerFireRecord
from zebu.domain.value_objects.activation_frequency import ActivationFrequency
from zebu.domain.value_objects.activation_status import ActivationStatus
from zebu.domain.value_objects.agent_decision import AgentDecision
from zebu.domain.value_objects.api_key_scope import ApiKeyScope
from zebu.domain.value_objects.portfolio_type import PortfolioType
from zebu.domain.value_objects.strategy_parameters import BuyAndHoldParameters
from zebu.domain.value_objects.strategy_type import StrategyType
from zebu.domain.value_objects.trigger_condition import (
    ConditionType,
    DrawdownMetric,
    DrawdownParams,
    EarningsParams,
    VolatilityParams,
)
from zebu.domain.value_objects.trigger_status import TriggerStatus

# ---------------------------------------------------------------------------
# Repository protocol parameterisation
# ---------------------------------------------------------------------------


class _TriggerRepoFactory(Protocol):
    """Async factory that yields a fresh trigger / fire repo pair.

    Implementations either set up an in-memory pair or build SQLModel
    adapters around the integration session (with FK-target rows seeded
    via ``_seed_fk_targets``). Each test gets a fresh instance.
    """

    async def __call__(
        self, session: AsyncSession
    ) -> tuple[
        InMemoryTriggerRepository | SQLModelTriggerRepository,
        InMemoryTriggerFireRepository | SQLModelTriggerFireRepository,
        "SeedRefs",
    ]: ...


class SeedRefs:
    """Foreign-key targets used by the SQL adapter tests.

    For in-memory tests the IDs are still meaningful even though the
    repos don't enforce FKs — keeping the same shape across both
    adapters makes the tests parameterise cleanly.
    """

    def __init__(
        self,
        *,
        user_id: UUID,
        activation_id: UUID,
        api_key_id: UUID,
    ) -> None:
        self.user_id = user_id
        self.activation_id = activation_id
        self.api_key_id = api_key_id


async def _seed_fk_targets(session: AsyncSession) -> SeedRefs:
    """Insert the rows the FK constraints require: user / portfolio /
    strategy / activation / api_key.

    Returns a :class:`SeedRefs` carrying the IDs the test should use
    when constructing triggers.
    """
    user_id = uuid4()
    portfolio = Portfolio(
        id=uuid4(),
        user_id=user_id,
        name="Test Portfolio",
        created_at=datetime.now(UTC) - timedelta(days=1),
        portfolio_type=PortfolioType.PAPER_TRADING,
    )
    session.add(PortfolioModel.from_domain(portfolio))
    await session.flush()

    strategy = Strategy(
        id=uuid4(),
        user_id=user_id,
        name="Test Strategy",
        strategy_type=StrategyType.BUY_AND_HOLD,
        tickers=["AAPL"],
        parameters=BuyAndHoldParameters(allocation={"AAPL": Decimal("1.0")}),
        created_at=datetime.now(UTC) - timedelta(days=1),
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
        clerk_user_id="clerk_user_test",
        label="test-key",
        key_hash="hash_" + "0" * 60,
        scopes=frozenset({ApiKeyScope.READ, ApiKeyScope.TRADE}),
        created_at=datetime.now(UTC) - timedelta(hours=3),
    )
    session.add(ApiKeyModel.from_domain(api_key))
    await session.flush()

    return SeedRefs(
        user_id=user_id,
        activation_id=activation.id,
        api_key_id=api_key.id,
    )


@pytest_asyncio.fixture
async def in_memory_repos() -> AsyncIterator[
    tuple[
        InMemoryTriggerRepository,
        InMemoryTriggerFireRepository,
        SeedRefs,
    ]
]:
    """In-memory repo pair, plus deterministic IDs for reuse."""
    seed = SeedRefs(
        user_id=uuid4(),
        activation_id=uuid4(),
        api_key_id=uuid4(),
    )
    yield (
        InMemoryTriggerRepository(),
        InMemoryTriggerFireRepository(),
        seed,
    )


@pytest_asyncio.fixture
async def sql_repos(
    session: AsyncSession,
) -> AsyncIterator[
    tuple[
        SQLModelTriggerRepository,
        SQLModelTriggerFireRepository,
        SeedRefs,
    ]
]:
    """SQL repo pair with FK-target rows already seeded."""
    seed = await _seed_fk_targets(session)
    yield (
        SQLModelTriggerRepository(session),
        SQLModelTriggerFireRepository(session),
        seed,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_trigger(
    seed: SeedRefs,
    *,
    trigger_id: UUID | None = None,
    condition_params: object | None = None,
    condition_type: ConditionType = ConditionType.DRAWDOWN_THRESHOLD,
    status: TriggerStatus = TriggerStatus.ACTIVE,
    priority: int = 0,
    cooldown_seconds: int = 21600,
    created_at: datetime | None = None,
    expires_at: datetime | None = None,
    last_fired_at: datetime | None = None,
    default_api_key_id: UUID | None = None,
) -> StrategyConditionTrigger:
    """Build a valid StrategyConditionTrigger for tests.

    Defaults to a DRAWDOWN_THRESHOLD trigger with the seeded user /
    activation. Tests override what they care about.
    """
    if condition_params is None:
        condition_params = DrawdownParams(
            threshold_pct=Decimal("5"),
            lookback_days=30,
        )
    when = created_at or (datetime.now(UTC) - timedelta(seconds=30))
    return StrategyConditionTrigger(
        id=trigger_id or uuid4(),
        activation_id=seed.activation_id,
        user_id=seed.user_id,
        condition_type=condition_type,
        condition_params=condition_params,  # type: ignore[arg-type]
        agent_prompt=(
            "Decide whether to hold the position based on context. "
            "Use the read tools to gather news and earnings data."
        ),
        status=status,
        priority=priority,
        cooldown_seconds=cooldown_seconds,
        last_fired_at=last_fired_at,
        default_api_key_id=default_api_key_id,
        expires_at=expires_at,
        created_at=when,
        updated_at=when,
        created_by=seed.user_id,
    )


def _make_fire_record(
    *,
    trigger_id: UUID,
    activation_id: UUID,
    api_key_id_used: UUID,
    record_id: UUID | None = None,
    fired_at: datetime | None = None,
    decision: AgentDecision = AgentDecision.HOLD,
    resulting_trade_id: UUID | None = None,
    resulting_modify_payload: dict[str, object] | None = None,
    resulting_exploration_task_id: UUID | None = None,
    latency_ms: int = 1000,
) -> TriggerFireRecord:
    """Build a valid fire record for tests."""
    return TriggerFireRecord(
        id=record_id or uuid4(),
        trigger_id=trigger_id,
        activation_id=activation_id,
        fired_at=fired_at or (datetime.now(UTC) - timedelta(seconds=10)),
        condition_evaluation_data={
            "schema_version": 1,
            "drawdown_pct": "5.5",
            "metric": "PORTFOLIO_TOTAL",
        },
        agent_response=decision,
        agent_response_raw="Decision rationale here.",
        latency_ms=latency_ms,
        api_key_id_used=api_key_id_used,
        resulting_trade_id=resulting_trade_id,
        resulting_modify_payload=resulting_modify_payload,
        resulting_exploration_task_id=resulting_exploration_task_id,
    )


# ---------------------------------------------------------------------------
# In-memory repository tests
# ---------------------------------------------------------------------------


class TestInMemoryTriggerRepository:
    """Behaviour tests for the in-memory TriggerRepository."""

    @pytest.mark.asyncio
    async def test_save_and_get(
        self,
        in_memory_repos: tuple[
            InMemoryTriggerRepository,
            InMemoryTriggerFireRepository,
            SeedRefs,
        ],
    ) -> None:
        repo, _, seed = in_memory_repos
        trigger = _make_trigger(seed)
        await repo.save(trigger)

        loaded = await repo.get(trigger.id)
        assert loaded == trigger

    @pytest.mark.asyncio
    async def test_get_missing_returns_none(
        self,
        in_memory_repos: tuple[
            InMemoryTriggerRepository,
            InMemoryTriggerFireRepository,
            SeedRefs,
        ],
    ) -> None:
        repo, _, _ = in_memory_repos
        result = await repo.get(uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_save_is_idempotent_upsert(
        self,
        in_memory_repos: tuple[
            InMemoryTriggerRepository,
            InMemoryTriggerFireRepository,
            SeedRefs,
        ],
    ) -> None:
        repo, _, seed = in_memory_repos
        trigger = _make_trigger(seed)
        await repo.save(trigger)
        await repo.save(trigger)
        loaded = await repo.get(trigger.id)
        assert loaded is not None

    @pytest.mark.asyncio
    async def test_list_evaluable_orders_by_priority_desc_then_created_asc(
        self,
        in_memory_repos: tuple[
            InMemoryTriggerRepository,
            InMemoryTriggerFireRepository,
            SeedRefs,
        ],
    ) -> None:
        repo, _, seed = in_memory_repos
        # Three triggers — high+old, low+new, mid+oldest.
        old_old = datetime.now(UTC) - timedelta(hours=10)
        old = datetime.now(UTC) - timedelta(hours=5)
        new = datetime.now(UTC) - timedelta(hours=1)

        # Build factory args carefully so created_at != updated_at would
        # raise; we use _make_trigger which sets both.
        t_high_old = _make_trigger(
            seed, priority=50, created_at=old, trigger_id=uuid4()
        )
        t_low_new = _make_trigger(
            seed, priority=-10, created_at=new, trigger_id=uuid4()
        )
        t_mid_oldest = _make_trigger(
            seed, priority=10, created_at=old_old, trigger_id=uuid4()
        )
        for t in (t_high_old, t_low_new, t_mid_oldest):
            await repo.save(t)

        result = await repo.list_evaluable()
        ids = [t.id for t in result]
        # priority order: 50 > 10 > -10
        assert ids == [t_high_old.id, t_mid_oldest.id, t_low_new.id]

    @pytest.mark.asyncio
    async def test_list_evaluable_excludes_non_active(
        self,
        in_memory_repos: tuple[
            InMemoryTriggerRepository,
            InMemoryTriggerFireRepository,
            SeedRefs,
        ],
    ) -> None:
        repo, _, seed = in_memory_repos
        active = _make_trigger(seed)
        paused = _make_trigger(seed, status=TriggerStatus.PAUSED)
        disabled = _make_trigger(
            seed,
            status=TriggerStatus.MANUALLY_DISABLED,
        )
        for t in (active, paused, disabled):
            await repo.save(t)

        result = await repo.list_evaluable()
        assert [t.id for t in result] == [active.id]

    @pytest.mark.asyncio
    async def test_list_for_activation_includes_terminal(
        self,
        in_memory_repos: tuple[
            InMemoryTriggerRepository,
            InMemoryTriggerFireRepository,
            SeedRefs,
        ],
    ) -> None:
        """list_for_activation returns history (terminal-status rows)."""
        repo, _, seed = in_memory_repos
        active = _make_trigger(seed)
        disabled = _make_trigger(seed, status=TriggerStatus.MANUALLY_DISABLED)
        for t in (active, disabled):
            await repo.save(t)

        result = await repo.list_for_activation(seed.activation_id)
        ids = {t.id for t in result}
        assert ids == {active.id, disabled.id}

    @pytest.mark.asyncio
    async def test_list_for_user_status_filter_and_pagination(
        self,
        in_memory_repos: tuple[
            InMemoryTriggerRepository,
            InMemoryTriggerFireRepository,
            SeedRefs,
        ],
    ) -> None:
        repo, _, seed = in_memory_repos
        # Create 3 active + 2 paused triggers; verify status filter.
        actives: list[StrategyConditionTrigger] = []
        for i in range(3):
            t = _make_trigger(
                seed,
                created_at=datetime.now(UTC) - timedelta(minutes=10 - i),
            )
            actives.append(t)
            await repo.save(t)
        for _ in range(2):
            t = _make_trigger(seed, status=TriggerStatus.PAUSED)
            await repo.save(t)

        active_only = await repo.list_for_user(
            seed.user_id, status=TriggerStatus.ACTIVE
        )
        assert len(active_only) == 3
        # Pagination
        page = await repo.list_for_user(
            seed.user_id, status=TriggerStatus.ACTIVE, limit=2, offset=0
        )
        assert len(page) == 2

    @pytest.mark.asyncio
    async def test_count_for_user_with_status_filter(
        self,
        in_memory_repos: tuple[
            InMemoryTriggerRepository,
            InMemoryTriggerFireRepository,
            SeedRefs,
        ],
    ) -> None:
        repo, _, seed = in_memory_repos
        for _ in range(3):
            await repo.save(_make_trigger(seed))
        for _ in range(2):
            await repo.save(_make_trigger(seed, status=TriggerStatus.PAUSED))

        total = await repo.count_for_user(seed.user_id)
        active = await repo.count_for_user(seed.user_id, status=TriggerStatus.ACTIVE)
        assert total == 5
        assert active == 3

    @pytest.mark.asyncio
    async def test_disable_all_for_user(
        self,
        in_memory_repos: tuple[
            InMemoryTriggerRepository,
            InMemoryTriggerFireRepository,
            SeedRefs,
        ],
    ) -> None:
        """Per-user kill switch transitions all non-terminal triggers."""
        repo, _, seed = in_memory_repos
        active = _make_trigger(seed)
        paused = _make_trigger(seed, status=TriggerStatus.PAUSED)
        already_disabled = _make_trigger(seed, status=TriggerStatus.MANUALLY_DISABLED)
        for t in (active, paused, already_disabled):
            await repo.save(t)

        count = await repo.disable_all_for_user(seed.user_id, at=datetime.now(UTC))
        # active + paused get disabled; already_disabled is left alone.
        assert count == 2

        # Verify all three are now MANUALLY_DISABLED.
        for t in (active, paused, already_disabled):
            current = await repo.get(t.id)
            assert current is not None
            assert current.status is TriggerStatus.MANUALLY_DISABLED

    @pytest.mark.asyncio
    async def test_disable_all_for_other_user_does_not_affect(
        self,
        in_memory_repos: tuple[
            InMemoryTriggerRepository,
            InMemoryTriggerFireRepository,
            SeedRefs,
        ],
    ) -> None:
        """disable_all_for_user is scoped to one user."""
        repo, _, seed = in_memory_repos
        # Create a trigger for a different user.
        other_seed = SeedRefs(
            user_id=uuid4(),
            activation_id=uuid4(),
            api_key_id=uuid4(),
        )
        other_trigger = _make_trigger(other_seed)
        await repo.save(other_trigger)

        own_trigger = _make_trigger(seed)
        await repo.save(own_trigger)

        count = await repo.disable_all_for_user(seed.user_id, at=datetime.now(UTC))
        assert count == 1

        # Other user's trigger is untouched.
        other_loaded = await repo.get(other_trigger.id)
        assert other_loaded is not None
        assert other_loaded.status is TriggerStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_disable_all_admin_wide(
        self,
        in_memory_repos: tuple[
            InMemoryTriggerRepository,
            InMemoryTriggerFireRepository,
            SeedRefs,
        ],
    ) -> None:
        """disable_all transitions every non-terminal trigger across users."""
        repo, _, seed = in_memory_repos
        other_seed = SeedRefs(
            user_id=uuid4(),
            activation_id=uuid4(),
            api_key_id=uuid4(),
        )
        await repo.save(_make_trigger(seed))
        await repo.save(_make_trigger(other_seed))

        count = await repo.disable_all(at=datetime.now(UTC))
        assert count == 2

    @pytest.mark.asyncio
    async def test_delete(
        self,
        in_memory_repos: tuple[
            InMemoryTriggerRepository,
            InMemoryTriggerFireRepository,
            SeedRefs,
        ],
    ) -> None:
        repo, _, seed = in_memory_repos
        trigger = _make_trigger(seed)
        await repo.save(trigger)
        await repo.delete(trigger.id)
        assert await repo.get(trigger.id) is None
        # Idempotent — deleting an unknown id is a no-op.
        await repo.delete(uuid4())


class TestInMemoryTriggerFireRepository:
    """Behaviour tests for the in-memory TriggerFireRepository."""

    @pytest.mark.asyncio
    async def test_save_and_get(
        self,
        in_memory_repos: tuple[
            InMemoryTriggerRepository,
            InMemoryTriggerFireRepository,
            SeedRefs,
        ],
    ) -> None:
        _, fire_repo, seed = in_memory_repos
        record = _make_fire_record(
            trigger_id=uuid4(),
            activation_id=seed.activation_id,
            api_key_id_used=seed.api_key_id,
        )
        await fire_repo.save(record)
        loaded = await fire_repo.get(record.id)
        assert loaded == record

    @pytest.mark.asyncio
    async def test_save_duplicate_id_raises(
        self,
        in_memory_repos: tuple[
            InMemoryTriggerRepository,
            InMemoryTriggerFireRepository,
            SeedRefs,
        ],
    ) -> None:
        _, fire_repo, seed = in_memory_repos
        record = _make_fire_record(
            trigger_id=uuid4(),
            activation_id=seed.activation_id,
            api_key_id_used=seed.api_key_id,
        )
        await fire_repo.save(record)
        with pytest.raises(ValueError, match="already exists"):
            await fire_repo.save(record)

    @pytest.mark.asyncio
    async def test_list_for_trigger_newest_first(
        self,
        in_memory_repos: tuple[
            InMemoryTriggerRepository,
            InMemoryTriggerFireRepository,
            SeedRefs,
        ],
    ) -> None:
        _, fire_repo, seed = in_memory_repos
        trigger_id = uuid4()
        oldest = _make_fire_record(
            trigger_id=trigger_id,
            activation_id=seed.activation_id,
            api_key_id_used=seed.api_key_id,
            fired_at=datetime.now(UTC) - timedelta(minutes=10),
        )
        newest = _make_fire_record(
            trigger_id=trigger_id,
            activation_id=seed.activation_id,
            api_key_id_used=seed.api_key_id,
            fired_at=datetime.now(UTC) - timedelta(seconds=30),
        )
        # Save in reverse order to make the test less trivial.
        await fire_repo.save(newest)
        await fire_repo.save(oldest)

        result = await fire_repo.list_for_trigger(trigger_id)
        assert [r.id for r in result] == [newest.id, oldest.id]

    @pytest.mark.asyncio
    async def test_list_for_activation_only_returns_matching(
        self,
        in_memory_repos: tuple[
            InMemoryTriggerRepository,
            InMemoryTriggerFireRepository,
            SeedRefs,
        ],
    ) -> None:
        _, fire_repo, seed = in_memory_repos
        other_activation_id = uuid4()
        own = _make_fire_record(
            trigger_id=uuid4(),
            activation_id=seed.activation_id,
            api_key_id_used=seed.api_key_id,
        )
        other = _make_fire_record(
            trigger_id=uuid4(),
            activation_id=other_activation_id,
            api_key_id_used=seed.api_key_id,
        )
        await fire_repo.save(own)
        await fire_repo.save(other)

        result = await fire_repo.list_for_activation(seed.activation_id)
        assert [r.id for r in result] == [own.id]

    @pytest.mark.asyncio
    async def test_count_for_trigger(
        self,
        in_memory_repos: tuple[
            InMemoryTriggerRepository,
            InMemoryTriggerFireRepository,
            SeedRefs,
        ],
    ) -> None:
        _, fire_repo, seed = in_memory_repos
        trigger_id = uuid4()
        for _ in range(3):
            await fire_repo.save(
                _make_fire_record(
                    trigger_id=trigger_id,
                    activation_id=seed.activation_id,
                    api_key_id_used=seed.api_key_id,
                )
            )
        assert await fire_repo.count_for_trigger(trigger_id) == 3

    @pytest.mark.asyncio
    async def test_pagination(
        self,
        in_memory_repos: tuple[
            InMemoryTriggerRepository,
            InMemoryTriggerFireRepository,
            SeedRefs,
        ],
    ) -> None:
        _, fire_repo, seed = in_memory_repos
        trigger_id = uuid4()
        # Make 5 records with distinct fired_at so ordering is stable.
        records: list[TriggerFireRecord] = []
        for i in range(5):
            r = _make_fire_record(
                trigger_id=trigger_id,
                activation_id=seed.activation_id,
                api_key_id_used=seed.api_key_id,
                fired_at=datetime.now(UTC) - timedelta(seconds=10 + i),
            )
            await fire_repo.save(r)
            records.append(r)
        # Newest-first means records[0] (smallest age delta) is first.
        page1 = await fire_repo.list_for_trigger(trigger_id, limit=2, offset=0)
        page2 = await fire_repo.list_for_trigger(trigger_id, limit=2, offset=2)
        assert len(page1) == 2
        assert len(page2) == 2
        # Page boundaries don't overlap.
        assert {r.id for r in page1}.isdisjoint({r.id for r in page2})


# ---------------------------------------------------------------------------
# SQL repository tests — round-trip + JSON column behaviour
# ---------------------------------------------------------------------------


class TestSQLModelTriggerRepository:
    """Behaviour tests for the SQL adapter — through the in-memory SQLite engine."""

    @pytest.mark.asyncio
    async def test_save_and_get_drawdown_round_trip(
        self,
        sql_repos: tuple[
            SQLModelTriggerRepository,
            SQLModelTriggerFireRepository,
            SeedRefs,
        ],
    ) -> None:
        """JSON column round-trips a typed DrawdownParams cleanly."""
        repo, _, seed = sql_repos
        params = DrawdownParams(
            threshold_pct=Decimal("7.5"),
            lookback_days=21,
            metric=DrawdownMetric.PER_TICKER,
        )
        trigger = _make_trigger(
            seed,
            condition_params=params,
            default_api_key_id=seed.api_key_id,
        )
        await repo.save(trigger)
        loaded = await repo.get(trigger.id)
        assert loaded is not None
        assert loaded.condition_type is ConditionType.DRAWDOWN_THRESHOLD
        assert isinstance(loaded.condition_params, DrawdownParams)
        assert loaded.condition_params.threshold_pct == Decimal("7.5")
        assert loaded.condition_params.metric is DrawdownMetric.PER_TICKER
        assert loaded.default_api_key_id == seed.api_key_id

    @pytest.mark.asyncio
    async def test_save_and_get_volatility_round_trip(
        self,
        sql_repos: tuple[
            SQLModelTriggerRepository,
            SQLModelTriggerFireRepository,
            SeedRefs,
        ],
    ) -> None:
        """VolatilityParams (with tickers) round-trips."""
        from zebu.domain.value_objects.ticker import Ticker

        repo, _, seed = sql_repos
        params = VolatilityParams(
            threshold_pct=Decimal("40"),
            over_days=20,
            tickers=[Ticker("AAPL"), Ticker("NVDA")],
        )
        trigger = _make_trigger(
            seed,
            condition_type=ConditionType.VOLATILITY_SPIKE,
            condition_params=params,
        )
        await repo.save(trigger)
        loaded = await repo.get(trigger.id)
        assert loaded is not None
        assert isinstance(loaded.condition_params, VolatilityParams)
        assert loaded.condition_params.tickers is not None
        symbols = [t.symbol for t in loaded.condition_params.tickers]
        assert symbols == ["AAPL", "NVDA"]

    @pytest.mark.asyncio
    async def test_save_and_get_earnings_round_trip(
        self,
        sql_repos: tuple[
            SQLModelTriggerRepository,
            SQLModelTriggerFireRepository,
            SeedRefs,
        ],
    ) -> None:
        """EarningsParams round-trip — placeholder for full evaluation in F-4."""
        repo, _, seed = sql_repos
        params = EarningsParams(days_before=5)
        trigger = _make_trigger(
            seed,
            condition_type=ConditionType.EARNINGS_PROXIMITY,
            condition_params=params,
        )
        await repo.save(trigger)
        loaded = await repo.get(trigger.id)
        assert loaded is not None
        assert isinstance(loaded.condition_params, EarningsParams)
        assert loaded.condition_params.days_before == 5

    @pytest.mark.asyncio
    async def test_save_updates_existing_row_in_place(
        self,
        sql_repos: tuple[
            SQLModelTriggerRepository,
            SQLModelTriggerFireRepository,
            SeedRefs,
        ],
    ) -> None:
        """Re-saving the same trigger ID updates fields rather than inserting twice."""
        repo, _, seed = sql_repos
        trigger = _make_trigger(seed)
        await repo.save(trigger)

        # Pause via the entity transition and save again.
        paused = trigger.pause(at=datetime.now(UTC))
        await repo.save(paused)

        loaded = await repo.get(trigger.id)
        assert loaded is not None
        assert loaded.status is TriggerStatus.PAUSED

        # Only one row total.
        results = await repo.list_for_user(seed.user_id)
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_list_evaluable_priority_order(
        self,
        sql_repos: tuple[
            SQLModelTriggerRepository,
            SQLModelTriggerFireRepository,
            SeedRefs,
        ],
    ) -> None:
        """SQL adapter returns ACTIVE triggers ordered priority DESC + created ASC."""
        repo, _, seed = sql_repos
        oldest = datetime.now(UTC) - timedelta(hours=10)
        old = datetime.now(UTC) - timedelta(hours=5)
        new = datetime.now(UTC) - timedelta(hours=1)
        t_high_old = _make_trigger(seed, priority=50, created_at=old)
        t_low_new = _make_trigger(seed, priority=-10, created_at=new)
        t_mid_oldest = _make_trigger(seed, priority=10, created_at=oldest)
        for t in (t_high_old, t_low_new, t_mid_oldest):
            await repo.save(t)

        result = await repo.list_evaluable()
        assert [t.id for t in result] == [
            t_high_old.id,
            t_mid_oldest.id,
            t_low_new.id,
        ]

    @pytest.mark.asyncio
    async def test_disable_all_for_user_round_trip(
        self,
        sql_repos: tuple[
            SQLModelTriggerRepository,
            SQLModelTriggerFireRepository,
            SeedRefs,
        ],
    ) -> None:
        """Per-user kill switch persists the MANUALLY_DISABLED status."""
        repo, _, seed = sql_repos
        active = _make_trigger(seed)
        paused = _make_trigger(seed, status=TriggerStatus.PAUSED)
        for t in (active, paused):
            await repo.save(t)

        count = await repo.disable_all_for_user(seed.user_id, at=datetime.now(UTC))
        assert count == 2

        for t in (active, paused):
            loaded = await repo.get(t.id)
            assert loaded is not None
            assert loaded.status is TriggerStatus.MANUALLY_DISABLED

    @pytest.mark.asyncio
    async def test_delete_via_cascade_on_activation(
        self,
        session: AsyncSession,
        sql_repos: tuple[
            SQLModelTriggerRepository,
            SQLModelTriggerFireRepository,
            SeedRefs,
        ],
    ) -> None:
        """Deleting the parent activation cascades to triggers (FK ON DELETE CASCADE).

        Verifies the migration's FK constraints hold via SQLite's
        in-memory engine (which we configure with PRAGMA
        foreign_keys=ON in the integration conftest).
        """
        repo, _, seed = sql_repos
        trigger = _make_trigger(seed)
        await repo.save(trigger)
        await session.flush()

        # Sanity — trigger is there.
        assert (await repo.get(trigger.id)) is not None

        # Delete the activation row directly to test the cascade.
        from sqlmodel import delete

        await session.exec(  # type: ignore[call-overload]
            delete(StrategyActivationModel).where(
                StrategyActivationModel.id == seed.activation_id  # type: ignore[arg-type]
            )
        )
        await session.flush()

        # Trigger should be gone via CASCADE.
        assert (await repo.get(trigger.id)) is None


class TestSQLModelTriggerFireRepository:
    """Behaviour tests for the SQL fire-record adapter."""

    @pytest.mark.asyncio
    async def test_save_and_get(
        self,
        sql_repos: tuple[
            SQLModelTriggerRepository,
            SQLModelTriggerFireRepository,
            SeedRefs,
        ],
    ) -> None:
        repo, fire_repo, seed = sql_repos
        trigger = _make_trigger(seed)
        await repo.save(trigger)
        record = _make_fire_record(
            trigger_id=trigger.id,
            activation_id=seed.activation_id,
            api_key_id_used=seed.api_key_id,
        )
        await fire_repo.save(record)
        loaded = await fire_repo.get(record.id)
        assert loaded == record
        assert loaded is not None
        # JSON columns round-trip.
        assert loaded.condition_evaluation_data["drawdown_pct"] == "5.5"

    @pytest.mark.asyncio
    async def test_save_with_modify_payload_round_trip(
        self,
        sql_repos: tuple[
            SQLModelTriggerRepository,
            SQLModelTriggerFireRepository,
            SeedRefs,
        ],
    ) -> None:
        """MODIFY_STRATEGY records persist the JSON payload."""
        repo, fire_repo, seed = sql_repos
        trigger = _make_trigger(seed)
        await repo.save(trigger)
        record = _make_fire_record(
            trigger_id=trigger.id,
            activation_id=seed.activation_id,
            api_key_id_used=seed.api_key_id,
            decision=AgentDecision.MODIFY_STRATEGY,
            resulting_modify_payload={"invest_fraction": "0.25"},
        )
        await fire_repo.save(record)
        loaded = await fire_repo.get(record.id)
        assert loaded is not None
        assert loaded.resulting_modify_payload == {"invest_fraction": "0.25"}

    @pytest.mark.asyncio
    async def test_save_duplicate_id_raises(
        self,
        sql_repos: tuple[
            SQLModelTriggerRepository,
            SQLModelTriggerFireRepository,
            SeedRefs,
        ],
    ) -> None:
        """Duplicate fire-record ID raises ValueError (append-only contract)."""
        repo, fire_repo, seed = sql_repos
        trigger = _make_trigger(seed)
        await repo.save(trigger)
        record = _make_fire_record(
            trigger_id=trigger.id,
            activation_id=seed.activation_id,
            api_key_id_used=seed.api_key_id,
        )
        await fire_repo.save(record)
        with pytest.raises(ValueError, match="already exists"):
            await fire_repo.save(record)

    @pytest.mark.asyncio
    async def test_list_and_count_for_trigger(
        self,
        sql_repos: tuple[
            SQLModelTriggerRepository,
            SQLModelTriggerFireRepository,
            SeedRefs,
        ],
    ) -> None:
        repo, fire_repo, seed = sql_repos
        trigger = _make_trigger(seed)
        await repo.save(trigger)
        for i in range(3):
            await fire_repo.save(
                _make_fire_record(
                    trigger_id=trigger.id,
                    activation_id=seed.activation_id,
                    api_key_id_used=seed.api_key_id,
                    fired_at=datetime.now(UTC) - timedelta(seconds=10 + i),
                )
            )
        assert await fire_repo.count_for_trigger(trigger.id) == 3
        records = await fire_repo.list_for_trigger(trigger.id)
        assert len(records) == 3
        # Newest-first: monotonically decreasing fired_at.
        for prev, nxt in zip(records, records[1:], strict=False):
            assert prev.fired_at >= nxt.fired_at

    @pytest.mark.asyncio
    async def test_cascade_delete_when_trigger_deleted(
        self,
        session: AsyncSession,
        sql_repos: tuple[
            SQLModelTriggerRepository,
            SQLModelTriggerFireRepository,
            SeedRefs,
        ],
    ) -> None:
        """Deleting the trigger cascades to its fire records."""
        repo, fire_repo, seed = sql_repos
        trigger = _make_trigger(seed)
        await repo.save(trigger)
        record = _make_fire_record(
            trigger_id=trigger.id,
            activation_id=seed.activation_id,
            api_key_id_used=seed.api_key_id,
        )
        await fire_repo.save(record)
        await session.flush()

        await repo.delete(trigger.id)
        await session.flush()

        assert (await fire_repo.get(record.id)) is None
