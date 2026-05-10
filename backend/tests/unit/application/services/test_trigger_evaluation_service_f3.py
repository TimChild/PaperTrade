"""Tests for the F-3 wiring of :class:`TriggerEvaluationService`.

Verifies that when the orchestrator is supplied AND the feature flag
is on, ``evaluate_all`` hands off fire-eligible results to the
orchestrator. When the flag is off (or no orchestrator), behaviour
stays at F-2 "would fire" parity.

Also covers the kill-switch / disabled-trigger path: a
MANUALLY_DISABLED trigger doesn't reach the orchestrator at all
(the repo's ``list_evaluable`` filters by status).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from zebu.adapters.outbound.market_data.in_memory_adapter import (
    InMemoryMarketDataAdapter,
)
from zebu.application.ports.in_memory_agent_invocation_port import (
    StaticAgentInvocationPort,
    make_result,
)
from zebu.application.ports.in_memory_api_key_repository import (
    InMemoryApiKeyRepository,
)
from zebu.application.ports.in_memory_exploration_task_repository import (
    InMemoryExplorationTaskRepository,
)
from zebu.application.ports.in_memory_portfolio_repository import (
    InMemoryPortfolioRepository,
)
from zebu.application.ports.in_memory_strategy_activation_repository import (
    InMemoryStrategyActivationRepository,
)
from zebu.application.ports.in_memory_strategy_repository import (
    InMemoryStrategyRepository,
)
from zebu.application.ports.in_memory_transaction_repository import (
    InMemoryTransactionRepository,
)
from zebu.application.ports.in_memory_trigger_fire_repository import (
    InMemoryTriggerFireRepository,
)
from zebu.application.ports.in_memory_trigger_repository import (
    InMemoryTriggerRepository,
)
from zebu.application.services.trigger_evaluation_service import (
    TriggerEvaluationService,
)
from zebu.application.services.trigger_invocation_orchestrator import (
    TriggerInvocationOrchestrator,
)
from zebu.domain.entities.api_key import ApiKey
from zebu.domain.entities.portfolio import Portfolio
from zebu.domain.entities.strategy import Strategy
from zebu.domain.entities.strategy_activation import StrategyActivation
from zebu.domain.entities.strategy_condition_trigger import (
    StrategyConditionTrigger,
)
from zebu.domain.entities.transaction import Transaction, TransactionType
from zebu.domain.value_objects.activation_frequency import ActivationFrequency
from zebu.domain.value_objects.activation_status import ActivationStatus
from zebu.domain.value_objects.agent_decision import AgentDecision
from zebu.domain.value_objects.api_key_scope import ApiKeyScope
from zebu.domain.value_objects.money import Money
from zebu.domain.value_objects.portfolio_type import PortfolioType
from zebu.domain.value_objects.price_point import PricePoint
from zebu.domain.value_objects.quantity import Quantity
from zebu.domain.value_objects.strategy_parameters import BuyAndHoldParameters
from zebu.domain.value_objects.strategy_type import StrategyType
from zebu.domain.value_objects.ticker import Ticker
from zebu.domain.value_objects.trigger_condition import (
    ConditionType,
    DrawdownMetric,
    DrawdownParams,
)
from zebu.domain.value_objects.trigger_status import TriggerStatus

# ---------------------------------------------------------------------------
# Helpers (replicated from sibling test file — keeps each file self-contained)
# ---------------------------------------------------------------------------


def _now() -> datetime:
    return datetime.now(UTC)


def _make_api_key(*, user_id: UUID) -> ApiKey:
    return ApiKey(
        id=uuid4(),
        user_id=user_id,
        clerk_user_id="user_test_clerk",
        label="trigger-fire-test-key",
        key_hash="hash_" + "0" * 60,
        scopes=frozenset({ApiKeyScope.READ, ApiKeyScope.TRADE}),
        created_at=_now() - timedelta(days=20),
    )


def _make_strategy(*, user_id: UUID, ticker: str = "AAPL") -> Strategy:
    return Strategy(
        id=uuid4(),
        user_id=user_id,
        name="Test Strategy",
        strategy_type=StrategyType.BUY_AND_HOLD,
        tickers=[ticker],
        parameters=BuyAndHoldParameters(allocation={ticker: Decimal("1.0")}),
        created_at=_now() - timedelta(days=60),
    )


def _make_portfolio(*, user_id: UUID) -> Portfolio:
    return Portfolio(
        id=uuid4(),
        user_id=user_id,
        name="Test Portfolio",
        created_at=_now() - timedelta(days=60),
        portfolio_type=PortfolioType.PAPER_TRADING,
    )


def _make_activation(
    *, user_id: UUID, strategy_id: UUID, portfolio_id: UUID
) -> StrategyActivation:
    when = _now() - timedelta(days=45)
    return StrategyActivation(
        id=uuid4(),
        user_id=user_id,
        strategy_id=strategy_id,
        portfolio_id=portfolio_id,
        status=ActivationStatus.ACTIVE,
        frequency=ActivationFrequency.DAILY_MARKET_CLOSE,
        created_at=when,
        updated_at=when,
    )


def _make_trigger(
    *,
    user_id: UUID,
    activation_id: UUID,
    api_key_id: UUID,
    status: TriggerStatus = TriggerStatus.ACTIVE,
) -> StrategyConditionTrigger:
    when = _now() - timedelta(days=10)
    return StrategyConditionTrigger(
        id=uuid4(),
        activation_id=activation_id,
        user_id=user_id,
        condition_type=ConditionType.DRAWDOWN_THRESHOLD,
        condition_params=DrawdownParams(
            threshold_pct=Decimal("5"),
            lookback_days=30,
            metric=DrawdownMetric.PORTFOLIO_TOTAL,
        ),
        agent_prompt="Decide whether to hold the position based on context.",
        status=status,
        cooldown_seconds=21600,
        created_at=when,
        updated_at=when,
        created_by=user_id,
        default_api_key_id=api_key_id,
    )


async def _seed_drawdown_state(
    *,
    txn_repo: InMemoryTransactionRepository,
    portfolio_id: UUID,
    market_data: InMemoryMarketDataAdapter,
    ticker: str = "AAPL",
) -> None:
    """Seed: deposit + buy at $100; current price $80 (~20% drawdown)."""
    deposit = Transaction(
        id=uuid4(),
        portfolio_id=portfolio_id,
        transaction_type=TransactionType.DEPOSIT,
        timestamp=_now() - timedelta(days=29),
        cash_change=Money(Decimal("10000"), "USD"),
    )
    await txn_repo.save(deposit)

    buy_price = Money(Decimal("100"), "USD")
    buy_qty = Quantity(Decimal("50"))
    buy = Transaction(
        id=uuid4(),
        portfolio_id=portfolio_id,
        transaction_type=TransactionType.BUY,
        timestamp=_now() - timedelta(days=28),
        cash_change=Money(-(buy_price.amount * buy_qty.shares), "USD"),
        ticker=Ticker(ticker),
        quantity=buy_qty,
        price_per_share=buy_price,
    )
    await txn_repo.save(buy)

    # Price history: started at $100, fell to $80
    for days_ago, price in (
        (28, "100"),
        (15, "100"),
        (5, "85"),
        (1, "80"),
        (0, "80"),
    ):
        market_data.seed_price(
            PricePoint(
                ticker=Ticker(ticker),
                price=Money(Decimal(price), "USD"),
                timestamp=_now() - timedelta(days=days_ago),
                source="database",
                interval="1day",
                close=Money(Decimal(price), "USD"),
            )
        )


def _build_orchestrator(
    *,
    agent_port: object,
    trigger_repo: InMemoryTriggerRepository,
    fire_repo: InMemoryTriggerFireRepository,
    activation_repo: InMemoryStrategyActivationRepository,
    strategy_repo: InMemoryStrategyRepository,
    portfolio_repo: InMemoryPortfolioRepository,
    txn_repo: InMemoryTransactionRepository,
    market_data: InMemoryMarketDataAdapter,
    api_key_repo: InMemoryApiKeyRepository,
    task_repo: InMemoryExplorationTaskRepository,
) -> TriggerInvocationOrchestrator:
    return TriggerInvocationOrchestrator(
        agent_invocation=agent_port,  # type: ignore[arg-type]
        trigger_repo=trigger_repo,
        trigger_fire_repo=fire_repo,
        activation_repo=activation_repo,
        strategy_repo=strategy_repo,
        portfolio_repo=portfolio_repo,
        transaction_repo=txn_repo,
        market_data=market_data,
        api_key_repo=api_key_repo,
        exploration_task_repo=task_repo,
    )


# ---------------------------------------------------------------------------
# F-3 wired tests
# ---------------------------------------------------------------------------


class TestF3Wiring:
    """Service hands off to the orchestrator when the flag is on."""

    async def test_fire_eligible_trigger_invokes_orchestrator_when_enabled(
        self,
    ) -> None:
        user_id = uuid4()
        api_key = _make_api_key(user_id=user_id)
        api_key_repo = InMemoryApiKeyRepository()
        await api_key_repo.save(api_key)

        strategy = _make_strategy(user_id=user_id)
        portfolio = _make_portfolio(user_id=user_id)
        activation = _make_activation(
            user_id=user_id,
            strategy_id=strategy.id,
            portfolio_id=portfolio.id,
        )
        strategy_repo = InMemoryStrategyRepository()
        await strategy_repo.save(strategy)
        portfolio_repo = InMemoryPortfolioRepository()
        await portfolio_repo.save(portfolio)
        activation_repo = InMemoryStrategyActivationRepository()
        await activation_repo.save(activation)

        txn_repo = InMemoryTransactionRepository()
        market_data = InMemoryMarketDataAdapter()
        await _seed_drawdown_state(
            txn_repo=txn_repo,
            portfolio_id=portfolio.id,
            market_data=market_data,
        )

        trigger = _make_trigger(
            user_id=user_id,
            activation_id=activation.id,
            api_key_id=api_key.id,
        )
        trigger_repo = InMemoryTriggerRepository()
        await trigger_repo.save(trigger)

        agent_port = StaticAgentInvocationPort(
            result=make_result(
                decision=AgentDecision.HOLD,
                rationale="Drawdown noted, no action",
            )
        )
        fire_repo = InMemoryTriggerFireRepository()
        orchestrator = _build_orchestrator(
            agent_port=agent_port,
            trigger_repo=trigger_repo,
            fire_repo=fire_repo,
            activation_repo=activation_repo,
            strategy_repo=strategy_repo,
            portfolio_repo=portfolio_repo,
            txn_repo=txn_repo,
            market_data=market_data,
            api_key_repo=api_key_repo,
            task_repo=InMemoryExplorationTaskRepository(),
        )

        service = TriggerEvaluationService(
            trigger_repo=trigger_repo,
            activation_repo=activation_repo,
            strategy_repo=strategy_repo,
            portfolio_repo=portfolio_repo,
            transaction_repo=txn_repo,
            market_data=market_data,
            orchestrator=orchestrator,
            fires_enabled_override=True,
        )

        summary = await service.evaluate_all()

        assert summary["fired"] == 1
        result = summary["results"][0]
        assert result["fired"] is True
        assert result["fire_record_id"] is not None
        assert result["decision"] == "HOLD"

        # Audit row written
        record = await fire_repo.get(result["fire_record_id"])
        assert record is not None
        assert record.agent_response is AgentDecision.HOLD

        # Agent was invoked
        assert len(agent_port.invocations) == 1

    async def test_orchestrator_not_invoked_when_flag_off(self) -> None:
        """Even with orchestrator wired, flag-off keeps F-2 behavior."""
        user_id = uuid4()
        api_key = _make_api_key(user_id=user_id)
        api_key_repo = InMemoryApiKeyRepository()
        await api_key_repo.save(api_key)

        strategy = _make_strategy(user_id=user_id)
        portfolio = _make_portfolio(user_id=user_id)
        activation = _make_activation(
            user_id=user_id,
            strategy_id=strategy.id,
            portfolio_id=portfolio.id,
        )
        strategy_repo = InMemoryStrategyRepository()
        await strategy_repo.save(strategy)
        portfolio_repo = InMemoryPortfolioRepository()
        await portfolio_repo.save(portfolio)
        activation_repo = InMemoryStrategyActivationRepository()
        await activation_repo.save(activation)

        txn_repo = InMemoryTransactionRepository()
        market_data = InMemoryMarketDataAdapter()
        await _seed_drawdown_state(
            txn_repo=txn_repo,
            portfolio_id=portfolio.id,
            market_data=market_data,
        )

        trigger = _make_trigger(
            user_id=user_id,
            activation_id=activation.id,
            api_key_id=api_key.id,
        )
        trigger_repo = InMemoryTriggerRepository()
        await trigger_repo.save(trigger)

        agent_port = StaticAgentInvocationPort(
            result=make_result(decision=AgentDecision.HOLD)
        )
        fire_repo = InMemoryTriggerFireRepository()
        orchestrator = _build_orchestrator(
            agent_port=agent_port,
            trigger_repo=trigger_repo,
            fire_repo=fire_repo,
            activation_repo=activation_repo,
            strategy_repo=strategy_repo,
            portfolio_repo=portfolio_repo,
            txn_repo=txn_repo,
            market_data=market_data,
            api_key_repo=api_key_repo,
            task_repo=InMemoryExplorationTaskRepository(),
        )

        service = TriggerEvaluationService(
            trigger_repo=trigger_repo,
            activation_repo=activation_repo,
            strategy_repo=strategy_repo,
            portfolio_repo=portfolio_repo,
            transaction_repo=txn_repo,
            market_data=market_data,
            orchestrator=orchestrator,
            fires_enabled_override=False,  # explicit off
        )

        summary = await service.evaluate_all()

        assert summary["fired"] == 1  # F-2 "would fire" still counted
        result = summary["results"][0]
        assert result["fired"] is True
        assert result["fire_record_id"] is None
        assert result["decision"] is None

        # No audit row, no agent call
        assert len(agent_port.invocations) == 0

    async def test_no_orchestrator_means_f2_behavior(self) -> None:
        """Service constructed without an orchestrator stays F-2 only."""
        user_id = uuid4()
        api_key = _make_api_key(user_id=user_id)
        api_key_repo = InMemoryApiKeyRepository()
        await api_key_repo.save(api_key)

        strategy = _make_strategy(user_id=user_id)
        portfolio = _make_portfolio(user_id=user_id)
        activation = _make_activation(
            user_id=user_id,
            strategy_id=strategy.id,
            portfolio_id=portfolio.id,
        )
        strategy_repo = InMemoryStrategyRepository()
        await strategy_repo.save(strategy)
        portfolio_repo = InMemoryPortfolioRepository()
        await portfolio_repo.save(portfolio)
        activation_repo = InMemoryStrategyActivationRepository()
        await activation_repo.save(activation)

        txn_repo = InMemoryTransactionRepository()
        market_data = InMemoryMarketDataAdapter()
        await _seed_drawdown_state(
            txn_repo=txn_repo,
            portfolio_id=portfolio.id,
            market_data=market_data,
        )

        trigger = _make_trigger(
            user_id=user_id,
            activation_id=activation.id,
            api_key_id=api_key.id,
        )
        trigger_repo = InMemoryTriggerRepository()
        await trigger_repo.save(trigger)

        # Even with override=True, no orchestrator means no fire path.
        service = TriggerEvaluationService(
            trigger_repo=trigger_repo,
            activation_repo=activation_repo,
            strategy_repo=strategy_repo,
            portfolio_repo=portfolio_repo,
            transaction_repo=txn_repo,
            market_data=market_data,
            orchestrator=None,
            fires_enabled_override=True,
        )

        summary = await service.evaluate_all()
        assert summary["fired"] == 1
        assert summary["results"][0]["fire_record_id"] is None

    async def test_paused_trigger_does_not_invoke_orchestrator(self) -> None:
        """A PAUSED trigger is filtered by list_evaluable; never reaches the agent."""
        user_id = uuid4()
        api_key = _make_api_key(user_id=user_id)
        api_key_repo = InMemoryApiKeyRepository()
        await api_key_repo.save(api_key)

        strategy = _make_strategy(user_id=user_id)
        portfolio = _make_portfolio(user_id=user_id)
        activation = _make_activation(
            user_id=user_id,
            strategy_id=strategy.id,
            portfolio_id=portfolio.id,
        )
        strategy_repo = InMemoryStrategyRepository()
        await strategy_repo.save(strategy)
        portfolio_repo = InMemoryPortfolioRepository()
        await portfolio_repo.save(portfolio)
        activation_repo = InMemoryStrategyActivationRepository()
        await activation_repo.save(activation)

        txn_repo = InMemoryTransactionRepository()
        market_data = InMemoryMarketDataAdapter()
        await _seed_drawdown_state(
            txn_repo=txn_repo,
            portfolio_id=portfolio.id,
            market_data=market_data,
        )

        # Trigger is paused — should never fire.
        trigger = _make_trigger(
            user_id=user_id,
            activation_id=activation.id,
            api_key_id=api_key.id,
            status=TriggerStatus.PAUSED,
        )
        trigger_repo = InMemoryTriggerRepository()
        await trigger_repo.save(trigger)

        agent_port = StaticAgentInvocationPort(
            result=make_result(decision=AgentDecision.HOLD)
        )
        fire_repo = InMemoryTriggerFireRepository()
        orchestrator = _build_orchestrator(
            agent_port=agent_port,
            trigger_repo=trigger_repo,
            fire_repo=fire_repo,
            activation_repo=activation_repo,
            strategy_repo=strategy_repo,
            portfolio_repo=portfolio_repo,
            txn_repo=txn_repo,
            market_data=market_data,
            api_key_repo=api_key_repo,
            task_repo=InMemoryExplorationTaskRepository(),
        )

        service = TriggerEvaluationService(
            trigger_repo=trigger_repo,
            activation_repo=activation_repo,
            strategy_repo=strategy_repo,
            portfolio_repo=portfolio_repo,
            transaction_repo=txn_repo,
            market_data=market_data,
            orchestrator=orchestrator,
            fires_enabled_override=True,
        )

        summary = await service.evaluate_all()
        # Repo's list_evaluable filters by status=ACTIVE, so paused
        # triggers don't even appear in the candidate list.
        assert summary["processed"] == 0
        assert summary["fired"] == 0
        assert len(agent_port.invocations) == 0

    async def test_manually_disabled_trigger_does_not_invoke_orchestrator(
        self,
    ) -> None:
        """Kill-switch path: MANUALLY_DISABLED triggers never reach the agent."""
        user_id = uuid4()
        api_key = _make_api_key(user_id=user_id)
        api_key_repo = InMemoryApiKeyRepository()
        await api_key_repo.save(api_key)

        strategy = _make_strategy(user_id=user_id)
        portfolio = _make_portfolio(user_id=user_id)
        activation = _make_activation(
            user_id=user_id,
            strategy_id=strategy.id,
            portfolio_id=portfolio.id,
        )
        strategy_repo = InMemoryStrategyRepository()
        await strategy_repo.save(strategy)
        portfolio_repo = InMemoryPortfolioRepository()
        await portfolio_repo.save(portfolio)
        activation_repo = InMemoryStrategyActivationRepository()
        await activation_repo.save(activation)

        txn_repo = InMemoryTransactionRepository()
        market_data = InMemoryMarketDataAdapter()
        await _seed_drawdown_state(
            txn_repo=txn_repo,
            portfolio_id=portfolio.id,
            market_data=market_data,
        )

        trigger = _make_trigger(
            user_id=user_id,
            activation_id=activation.id,
            api_key_id=api_key.id,
            status=TriggerStatus.MANUALLY_DISABLED,
        )
        trigger_repo = InMemoryTriggerRepository()
        await trigger_repo.save(trigger)

        agent_port = StaticAgentInvocationPort(
            result=make_result(decision=AgentDecision.HOLD)
        )
        fire_repo = InMemoryTriggerFireRepository()
        orchestrator = _build_orchestrator(
            agent_port=agent_port,
            trigger_repo=trigger_repo,
            fire_repo=fire_repo,
            activation_repo=activation_repo,
            strategy_repo=strategy_repo,
            portfolio_repo=portfolio_repo,
            txn_repo=txn_repo,
            market_data=market_data,
            api_key_repo=api_key_repo,
            task_repo=InMemoryExplorationTaskRepository(),
        )

        service = TriggerEvaluationService(
            trigger_repo=trigger_repo,
            activation_repo=activation_repo,
            strategy_repo=strategy_repo,
            portfolio_repo=portfolio_repo,
            transaction_repo=txn_repo,
            market_data=market_data,
            orchestrator=orchestrator,
            fires_enabled_override=True,
        )

        summary = await service.evaluate_all()
        assert summary["processed"] == 0
        assert summary["fired"] == 0
        assert len(agent_port.invocations) == 0
        # No audit rows for disabled triggers
        assert await fire_repo.count_for_trigger(trigger.id) == 0
