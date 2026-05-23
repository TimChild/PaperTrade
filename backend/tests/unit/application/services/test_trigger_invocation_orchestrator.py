"""Tests for :class:`TriggerInvocationOrchestrator` (Phase F-3).

Behavior-focused — uses the in-memory :class:`AgentInvocationPort`
fake to drive each decision branch and verifies the side effects + the
written :class:`TriggerFireRecord`.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from zebu.adapters.outbound.market_data.in_memory_adapter import (
    InMemoryMarketDataAdapter,
)
from zebu.application.ports.in_memory_agent_invocation_port import (
    FailingAgentInvocationPort,
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
from zebu.application.services.trigger_invocation_orchestrator import (
    TriggerInvocationOrchestrator,
    build_system_prompt,
    build_user_prompt,
)
from zebu.domain.entities.api_key import ApiKey
from zebu.domain.entities.exploration_task import ExplorationTaskStatus
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
from zebu.domain.value_objects.strategy_parameters import (
    BuyAndHoldParameters,
    MaCrossoverParameters,
)
from zebu.domain.value_objects.strategy_type import StrategyType
from zebu.domain.value_objects.ticker import Ticker
from zebu.domain.value_objects.trigger_condition import (
    ConditionType,
    DrawdownMetric,
    DrawdownParams,
)
from zebu.domain.value_objects.trigger_invocation_mode import TriggerInvocationMode
from zebu.domain.value_objects.trigger_status import TriggerStatus

# ---------------------------------------------------------------------------
# Builders & fixtures
# ---------------------------------------------------------------------------


def _now() -> datetime:
    return datetime.now(UTC)


def _make_strategy(
    *,
    user_id: UUID,
    tickers: list[str] | None = None,
    strategy_type: StrategyType = StrategyType.BUY_AND_HOLD,
) -> Strategy:
    tickers = tickers or ["AAPL"]
    if strategy_type is StrategyType.BUY_AND_HOLD:
        params = BuyAndHoldParameters(
            allocation={t: Decimal("1") / Decimal(len(tickers)) for t in tickers}
        )
    elif strategy_type is StrategyType.MOVING_AVERAGE_CROSSOVER:
        params = MaCrossoverParameters(  # type: ignore[assignment]
            fast_window=10,
            slow_window=30,
            invest_fraction=Decimal("0.5"),
        )
    else:  # pragma: no cover  -- not exercised here
        raise ValueError(f"Unsupported strategy_type for fixture: {strategy_type}")
    return Strategy(
        id=uuid4(),
        user_id=user_id,
        name="Test Strategy",
        strategy_type=strategy_type,
        tickers=tickers,
        parameters=params,
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
    default_api_key_id: UUID | None = None,
    cooldown_seconds: int = 21600,
    mode: TriggerInvocationMode = TriggerInvocationMode.DIRECT,
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
        agent_prompt=(
            "Decide whether to hold the position based on context. "
            "Use the read tools to gather news and earnings data."
        ),
        status=TriggerStatus.ACTIVE,
        cooldown_seconds=cooldown_seconds,
        created_at=when,
        updated_at=when,
        created_by=user_id,
        default_api_key_id=default_api_key_id,
        mode=mode,
    )


def _make_api_key(
    *, user_id: UUID, scopes: frozenset[ApiKeyScope] | None = None
) -> ApiKey:
    return ApiKey(
        id=uuid4(),
        user_id=user_id,
        clerk_user_id="user_test_clerk",
        label="trigger-fire-test-key",
        key_hash="hash_" + "0" * 60,
        scopes=scopes
        if scopes is not None
        else frozenset({ApiKeyScope.READ, ApiKeyScope.TRADE}),
        created_at=_now() - timedelta(days=20),
    )


async def _seed_funded_portfolio(
    *,
    txn_repo: InMemoryTransactionRepository,
    portfolio_id: UUID,
    cash_amount: str = "10000",
) -> None:
    deposit = Transaction(
        id=uuid4(),
        portfolio_id=portfolio_id,
        transaction_type=TransactionType.DEPOSIT,
        timestamp=_now() - timedelta(days=29),
        cash_change=Money(Decimal(cash_amount), "USD"),
    )
    await txn_repo.save(deposit)


def _seed_price(
    market_data: InMemoryMarketDataAdapter,
    *,
    ticker: str,
    price: str,
) -> None:
    market_data.seed_price(
        PricePoint(
            ticker=Ticker(ticker),
            price=Money(Decimal(price), "USD"),
            timestamp=_now(),
            source="database",
            interval="1day",
            close=Money(Decimal(price), "USD"),
        )
    )


def _evaluation_data() -> dict[str, object]:
    return {
        "schema_version": 1,
        "metric": "PORTFOLIO_TOTAL",
        "ticker": None,
        "threshold_pct": "5",
        "drawdown_pct": "10.5",
        "peak_value": "10000",
        "current_value": "8950",
        "peak_at": (_now() - timedelta(days=15)).isoformat(),
        "lookback_window_start": (_now() - timedelta(days=30)).date().isoformat(),
        "lookback_window_end": _now().date().isoformat(),
    }


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
# Decision execution
# ---------------------------------------------------------------------------


class TestBuyDecision:
    """BUY decision → trade is persisted, audit row written, trigger fires."""

    async def test_successful_buy_records_trade_and_audit_row(self) -> None:
        user_id = uuid4()
        api_key = _make_api_key(user_id=user_id)
        api_key_repo = InMemoryApiKeyRepository()
        await api_key_repo.save(api_key)

        strategy = _make_strategy(user_id=user_id, tickers=["AAPL"])
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
        await _seed_funded_portfolio(txn_repo=txn_repo, portfolio_id=portfolio.id)

        market_data = InMemoryMarketDataAdapter()
        _seed_price(market_data, ticker="AAPL", price="150")

        trigger = _make_trigger(
            user_id=user_id,
            activation_id=activation.id,
            default_api_key_id=api_key.id,
        )
        trigger_repo = InMemoryTriggerRepository()
        await trigger_repo.save(trigger)

        agent_port = StaticAgentInvocationPort(
            result=make_result(
                decision=AgentDecision.BUY,
                rationale="Drawdown detected, fundamentals strong, accumulating.",
                payload={
                    "ticker": "AAPL",
                    "quantity": "5",
                    "notes": "BUY 5 AAPL on drawdown",
                },
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

        outcome = await orchestrator.fire(
            trigger=trigger, evaluation_data=_evaluation_data()
        )

        # Decision recorded
        assert outcome.decision is AgentDecision.BUY
        assert outcome.error is None

        # Audit row persisted
        record = await fire_repo.get(outcome.fire_record_id)
        assert record is not None
        assert record.agent_response is AgentDecision.BUY
        assert record.resulting_trade_id is not None
        assert record.api_key_id_used == api_key.id

        # Trade landed
        all_txns = await txn_repo.get_by_portfolio(portfolio.id)
        buys = [t for t in all_txns if t.transaction_type is TransactionType.BUY]
        assert len(buys) == 1
        assert buys[0].id == record.resulting_trade_id
        assert buys[0].ticker is not None
        assert buys[0].ticker.symbol == "AAPL"
        assert buys[0].quantity is not None
        assert buys[0].quantity.shares == Decimal("5")

        # Trigger's last_fired_at updated
        reloaded = await trigger_repo.get(trigger.id)
        assert reloaded is not None
        assert reloaded.last_fired_at is not None

        # Agent was given a system + user prompt
        assert len(agent_port.invocations) == 1
        system_prompt, user_prompt, _, _, _ = agent_port.invocations[0]
        assert "Zebu trigger-fire decision agent" in system_prompt
        assert "record_decision" in system_prompt.lower()
        assert "Drawdown" not in user_prompt  # the eval data has condition_type
        assert trigger.agent_prompt in user_prompt
        assert "AAPL" in user_prompt

    async def test_buy_outside_strategy_universe_downgrades_to_hold(self) -> None:
        """Agent attempt to trade NVDA when strategy only has AAPL → HOLD."""
        user_id = uuid4()
        api_key = _make_api_key(user_id=user_id)
        api_key_repo = InMemoryApiKeyRepository()
        await api_key_repo.save(api_key)

        strategy = _make_strategy(user_id=user_id, tickers=["AAPL"])
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
        await _seed_funded_portfolio(txn_repo=txn_repo, portfolio_id=portfolio.id)
        market_data = InMemoryMarketDataAdapter()
        _seed_price(market_data, ticker="NVDA", price="500")

        trigger = _make_trigger(
            user_id=user_id,
            activation_id=activation.id,
            default_api_key_id=api_key.id,
        )
        trigger_repo = InMemoryTriggerRepository()
        await trigger_repo.save(trigger)

        agent_port = StaticAgentInvocationPort(
            result=make_result(
                decision=AgentDecision.BUY,
                payload={
                    "ticker": "NVDA",
                    "quantity": "1",
                    "notes": "Going off-piste",
                },
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

        outcome = await orchestrator.fire(
            trigger=trigger, evaluation_data=_evaluation_data()
        )

        assert outcome.decision is AgentDecision.HOLD
        assert outcome.error is not None
        assert "not in strategy ticker" in outcome.error

        # No trade landed
        record = await fire_repo.get(outcome.fire_record_id)
        assert record is not None
        assert record.agent_response is AgentDecision.HOLD
        assert record.resulting_trade_id is None

    async def test_buy_with_insufficient_funds_downgrades_to_hold(self) -> None:
        user_id = uuid4()
        api_key = _make_api_key(user_id=user_id)
        api_key_repo = InMemoryApiKeyRepository()
        await api_key_repo.save(api_key)

        strategy = _make_strategy(user_id=user_id, tickers=["AAPL"])
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

        # Tiny cash deposit — buying 100 @ $200 won't fit.
        txn_repo = InMemoryTransactionRepository()
        await _seed_funded_portfolio(
            txn_repo=txn_repo, portfolio_id=portfolio.id, cash_amount="50"
        )
        market_data = InMemoryMarketDataAdapter()
        _seed_price(market_data, ticker="AAPL", price="200")

        trigger = _make_trigger(
            user_id=user_id,
            activation_id=activation.id,
            default_api_key_id=api_key.id,
        )
        trigger_repo = InMemoryTriggerRepository()
        await trigger_repo.save(trigger)

        agent_port = StaticAgentInvocationPort(
            result=make_result(
                decision=AgentDecision.BUY,
                payload={
                    "ticker": "AAPL",
                    "quantity": "100",
                    "notes": "BUY 100 AAPL",
                },
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

        outcome = await orchestrator.fire(
            trigger=trigger, evaluation_data=_evaluation_data()
        )

        assert outcome.decision is AgentDecision.HOLD
        record = await fire_repo.get(outcome.fire_record_id)
        assert record is not None
        assert record.resulting_trade_id is None


class TestSellDecision:
    async def test_successful_sell_records_trade(self) -> None:
        user_id = uuid4()
        api_key = _make_api_key(user_id=user_id)
        api_key_repo = InMemoryApiKeyRepository()
        await api_key_repo.save(api_key)

        strategy = _make_strategy(user_id=user_id, tickers=["AAPL"])
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

        # Seed a buy so the portfolio has shares to sell.
        txn_repo = InMemoryTransactionRepository()
        await _seed_funded_portfolio(txn_repo=txn_repo, portfolio_id=portfolio.id)
        buy_txn = Transaction(
            id=uuid4(),
            portfolio_id=portfolio.id,
            transaction_type=TransactionType.BUY,
            timestamp=_now() - timedelta(days=20),
            cash_change=Money(Decimal("-1500"), "USD"),
            ticker=Ticker("AAPL"),
            quantity=Quantity(Decimal("10")),
            price_per_share=Money(Decimal("150"), "USD"),
        )
        await txn_repo.save(buy_txn)

        market_data = InMemoryMarketDataAdapter()
        _seed_price(market_data, ticker="AAPL", price="160")

        trigger = _make_trigger(
            user_id=user_id,
            activation_id=activation.id,
            default_api_key_id=api_key.id,
        )
        trigger_repo = InMemoryTriggerRepository()
        await trigger_repo.save(trigger)

        agent_port = StaticAgentInvocationPort(
            result=make_result(
                decision=AgentDecision.SELL,
                payload={
                    "ticker": "AAPL",
                    "quantity": "5",
                    "notes": "Take partial profit",
                },
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

        outcome = await orchestrator.fire(
            trigger=trigger, evaluation_data=_evaluation_data()
        )

        assert outcome.decision is AgentDecision.SELL
        record = await fire_repo.get(outcome.fire_record_id)
        assert record is not None
        assert record.resulting_trade_id is not None

        all_txns = await txn_repo.get_by_portfolio(portfolio.id)
        sells = [t for t in all_txns if t.transaction_type is TransactionType.SELL]
        assert len(sells) == 1
        assert sells[0].quantity is not None
        assert sells[0].quantity.shares == Decimal("5")


class TestHoldDecision:
    async def test_hold_writes_audit_row_no_side_effects(self) -> None:
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
        await _seed_funded_portfolio(txn_repo=txn_repo, portfolio_id=portfolio.id)

        trigger = _make_trigger(
            user_id=user_id,
            activation_id=activation.id,
            default_api_key_id=api_key.id,
        )
        trigger_repo = InMemoryTriggerRepository()
        await trigger_repo.save(trigger)

        agent_port = StaticAgentInvocationPort(
            result=make_result(
                decision=AgentDecision.HOLD,
                payload={"notes": "Volatility within expected range, no action"},
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
            market_data=InMemoryMarketDataAdapter(),
            api_key_repo=api_key_repo,
            task_repo=InMemoryExplorationTaskRepository(),
        )

        outcome = await orchestrator.fire(
            trigger=trigger, evaluation_data=_evaluation_data()
        )

        assert outcome.decision is AgentDecision.HOLD
        record = await fire_repo.get(outcome.fire_record_id)
        assert record is not None
        assert record.agent_response is AgentDecision.HOLD
        assert record.resulting_trade_id is None
        assert record.resulting_modify_payload is None
        assert record.resulting_exploration_task_id is None

        # No trades persisted
        all_txns = await txn_repo.get_by_portfolio(portfolio.id)
        # only the deposit
        assert len(all_txns) == 1
        assert all_txns[0].transaction_type is TransactionType.DEPOSIT


class TestModifyStrategyDecision:
    async def test_valid_modify_updates_strategy_parameters(self) -> None:
        user_id = uuid4()
        api_key = _make_api_key(user_id=user_id)
        api_key_repo = InMemoryApiKeyRepository()
        await api_key_repo.save(api_key)

        strategy = _make_strategy(
            user_id=user_id,
            tickers=["AAPL"],
            strategy_type=StrategyType.MOVING_AVERAGE_CROSSOVER,
        )
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

        trigger = _make_trigger(
            user_id=user_id,
            activation_id=activation.id,
            default_api_key_id=api_key.id,
        )
        trigger_repo = InMemoryTriggerRepository()
        await trigger_repo.save(trigger)

        # Reduce invest_fraction from 0.5 to 0.25.
        agent_port = StaticAgentInvocationPort(
            result=make_result(
                decision=AgentDecision.MODIFY_STRATEGY,
                payload={
                    "parameter_overrides": {"invest_fraction": "0.25"},
                    "notes": "De-risk on drawdown",
                },
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
            txn_repo=InMemoryTransactionRepository(),
            market_data=InMemoryMarketDataAdapter(),
            api_key_repo=api_key_repo,
            task_repo=InMemoryExplorationTaskRepository(),
        )

        outcome = await orchestrator.fire(
            trigger=trigger, evaluation_data=_evaluation_data()
        )

        assert outcome.decision is AgentDecision.MODIFY_STRATEGY
        record = await fire_repo.get(outcome.fire_record_id)
        assert record is not None
        assert record.resulting_modify_payload == {"invest_fraction": "0.25"}

        reloaded = await strategy_repo.get(strategy.id)
        assert reloaded is not None
        assert isinstance(reloaded.parameters, MaCrossoverParameters)
        assert reloaded.parameters.invest_fraction == Decimal("0.25")

    async def test_modify_with_forbidden_tickers_key_downgrades_to_hold(
        self,
    ) -> None:
        """Asset universe is a security boundary — `tickers` is forbidden."""
        user_id = uuid4()
        api_key = _make_api_key(user_id=user_id)
        api_key_repo = InMemoryApiKeyRepository()
        await api_key_repo.save(api_key)

        strategy = _make_strategy(user_id=user_id, tickers=["AAPL"])
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

        trigger = _make_trigger(
            user_id=user_id,
            activation_id=activation.id,
            default_api_key_id=api_key.id,
        )
        trigger_repo = InMemoryTriggerRepository()
        await trigger_repo.save(trigger)

        agent_port = StaticAgentInvocationPort(
            result=make_result(
                decision=AgentDecision.MODIFY_STRATEGY,
                payload={
                    "parameter_overrides": {
                        "tickers": ["NVDA"],
                    },
                    "notes": "Switching ticker",
                },
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
            txn_repo=InMemoryTransactionRepository(),
            market_data=InMemoryMarketDataAdapter(),
            api_key_repo=api_key_repo,
            task_repo=InMemoryExplorationTaskRepository(),
        )

        outcome = await orchestrator.fire(
            trigger=trigger, evaluation_data=_evaluation_data()
        )

        assert outcome.decision is AgentDecision.HOLD
        assert outcome.error is not None
        assert "forbidden parameter overrides" in outcome.error

        # Strategy untouched
        reloaded = await strategy_repo.get(strategy.id)
        assert reloaded is not None
        assert reloaded.tickers == ["AAPL"]


class TestNeedsHumanDecision:
    async def test_needs_human_files_exploration_task(self) -> None:
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

        trigger = _make_trigger(
            user_id=user_id,
            activation_id=activation.id,
            default_api_key_id=api_key.id,
        )
        trigger_repo = InMemoryTriggerRepository()
        await trigger_repo.save(trigger)

        task_repo = InMemoryExplorationTaskRepository()

        agent_port = StaticAgentInvocationPort(
            result=make_result(
                decision=AgentDecision.NEEDS_HUMAN,
                rationale="Earnings tomorrow + drawdown — hard to call.",
                payload={
                    "summary": "Pre-earnings drawdown — please review",
                    "urgency": "high",
                },
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
            txn_repo=InMemoryTransactionRepository(),
            market_data=InMemoryMarketDataAdapter(),
            api_key_repo=api_key_repo,
            task_repo=task_repo,
        )

        outcome = await orchestrator.fire(
            trigger=trigger, evaluation_data=_evaluation_data()
        )

        assert outcome.decision is AgentDecision.NEEDS_HUMAN
        record = await fire_repo.get(outcome.fire_record_id)
        assert record is not None
        assert record.resulting_exploration_task_id is not None

        # ExplorationTask was filed
        task = await task_repo.get(record.resulting_exploration_task_id)
        assert task is not None
        assert task.created_by == user_id
        assert task.target_portfolio_id == portfolio.id
        assert "[TRIGGER FIRE]" in task.prompt
        assert "[NEEDS HUMAN]" in task.prompt
        assert "Pre-earnings drawdown" in task.prompt


class TestInvocationFailed:
    async def test_agent_call_failure_records_invocation_failed(self) -> None:
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

        trigger = _make_trigger(
            user_id=user_id,
            activation_id=activation.id,
            default_api_key_id=api_key.id,
        )
        trigger_repo = InMemoryTriggerRepository()
        await trigger_repo.save(trigger)

        agent_port = FailingAgentInvocationPort(
            message="Network error: connection reset"
        )

        fire_repo = InMemoryTriggerFireRepository()
        orchestrator = _build_orchestrator(
            agent_port=agent_port,
            trigger_repo=trigger_repo,
            fire_repo=fire_repo,
            activation_repo=activation_repo,
            strategy_repo=strategy_repo,
            portfolio_repo=portfolio_repo,
            txn_repo=InMemoryTransactionRepository(),
            market_data=InMemoryMarketDataAdapter(),
            api_key_repo=api_key_repo,
            task_repo=InMemoryExplorationTaskRepository(),
        )

        outcome = await orchestrator.fire(
            trigger=trigger, evaluation_data=_evaluation_data()
        )

        assert outcome.decision is AgentDecision.INVOCATION_FAILED
        assert outcome.error is not None
        assert "Network error" in outcome.error

        record = await fire_repo.get(outcome.fire_record_id)
        assert record is not None
        assert record.agent_response is AgentDecision.INVOCATION_FAILED
        # last_fired_at still set so cooldown applies
        reloaded = await trigger_repo.get(trigger.id)
        assert reloaded is not None
        assert reloaded.last_fired_at is not None


class TestApiKeyResolution:
    async def test_default_api_key_used_when_active(self) -> None:
        """default_api_key_id wins over fallback when active."""
        user_id = uuid4()
        active_key = _make_api_key(user_id=user_id)
        api_key_repo = InMemoryApiKeyRepository()
        await api_key_repo.save(active_key)

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

        trigger = _make_trigger(
            user_id=user_id,
            activation_id=activation.id,
            default_api_key_id=active_key.id,
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
            txn_repo=InMemoryTransactionRepository(),
            market_data=InMemoryMarketDataAdapter(),
            api_key_repo=api_key_repo,
            task_repo=InMemoryExplorationTaskRepository(),
        )

        outcome = await orchestrator.fire(
            trigger=trigger, evaluation_data=_evaluation_data()
        )
        record = await fire_repo.get(outcome.fire_record_id)
        assert record is not None
        assert record.api_key_id_used == active_key.id

    async def test_fallback_to_user_key_when_default_missing(self) -> None:
        user_id = uuid4()
        # default_api_key_id is None → fall back to user's keys
        fallback_key = _make_api_key(user_id=user_id)
        api_key_repo = InMemoryApiKeyRepository()
        await api_key_repo.save(fallback_key)

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

        trigger = _make_trigger(
            user_id=user_id,
            activation_id=activation.id,
            default_api_key_id=None,
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
            txn_repo=InMemoryTransactionRepository(),
            market_data=InMemoryMarketDataAdapter(),
            api_key_repo=api_key_repo,
            task_repo=InMemoryExplorationTaskRepository(),
        )

        outcome = await orchestrator.fire(
            trigger=trigger, evaluation_data=_evaluation_data()
        )
        record = await fire_repo.get(outcome.fire_record_id)
        assert record is not None
        assert record.api_key_id_used == fallback_key.id

    async def test_no_eligible_key_yields_invocation_failed_no_audit_row(
        self,
    ) -> None:
        """No trade-scoped key → INVOCATION_FAILED + outcome.error."""
        user_id = uuid4()
        # Read-only key — not eligible
        read_only = _make_api_key(user_id=user_id, scopes=frozenset({ApiKeyScope.READ}))
        api_key_repo = InMemoryApiKeyRepository()
        await api_key_repo.save(read_only)

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

        trigger = _make_trigger(
            user_id=user_id,
            activation_id=activation.id,
            default_api_key_id=None,
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
            txn_repo=InMemoryTransactionRepository(),
            market_data=InMemoryMarketDataAdapter(),
            api_key_repo=api_key_repo,
            task_repo=InMemoryExplorationTaskRepository(),
        )

        outcome = await orchestrator.fire(
            trigger=trigger, evaluation_data=_evaluation_data()
        )
        assert outcome.decision is AgentDecision.INVOCATION_FAILED
        assert outcome.error is not None
        assert "API key" in outcome.error


# ---------------------------------------------------------------------------
# Prompt builders (pure)
# ---------------------------------------------------------------------------


class TestPromptBuilders:
    def test_system_prompt_contains_required_sections(self) -> None:
        prompt = build_system_prompt()
        assert "trigger-fire decision agent" in prompt
        assert "record_decision" in prompt
        assert "Paper-trading" in prompt
        assert "BUY" in prompt and "SELL" in prompt
        assert "HOLD" in prompt
        assert "MODIFY_STRATEGY" in prompt
        assert "NEEDS_HUMAN" in prompt
        assert "tickers" in prompt  # forbidden-keys note

    def test_user_prompt_contains_structural_sections_and_agent_prompt(
        self,
    ) -> None:
        user_id = uuid4()
        strategy = _make_strategy(user_id=user_id, tickers=["AAPL", "MSFT"])
        portfolio = _make_portfolio(user_id=user_id)
        activation = _make_activation(
            user_id=user_id,
            strategy_id=strategy.id,
            portfolio_id=portfolio.id,
        )
        trigger = _make_trigger(user_id=user_id, activation_id=activation.id)

        prompt = build_user_prompt(
            trigger=trigger,
            activation=activation,
            strategy=strategy,
            portfolio_id=portfolio.id,
            cash_balance=Decimal("9500.00"),
            holdings_summary=[("AAPL", Decimal("10"))],
            evaluation_data=_evaluation_data(),
        )

        # Section headers present
        assert "## Trigger" in prompt
        assert "## Condition snapshot" in prompt
        assert "## Strategy" in prompt
        assert "## Activation" in prompt
        assert "## Portfolio" in prompt
        assert "## Operator instruction" in prompt
        assert "## Directive" in prompt

        # Agent prompt verbatim
        assert trigger.agent_prompt in prompt

        # Portfolio state appears
        assert "9500.00" in prompt
        assert "AAPL: 10" in prompt


# ---------------------------------------------------------------------------
# Phase J / Task #213 — Pattern B queue-mode triggers
# ---------------------------------------------------------------------------


class TestQueueModeInvocation:
    """A QUEUE-mode trigger files an URGENT ExplorationTask, no Anthropic call."""

    async def test_queue_mode_files_urgent_task_and_skips_agent_call(
        self,
    ) -> None:
        """Mode branch: agent_invocation NOT called; exploration_task_repo IS called."""
        user_id = uuid4()
        api_key = _make_api_key(user_id=user_id)
        api_key_repo = InMemoryApiKeyRepository()
        await api_key_repo.save(api_key)

        strategy = _make_strategy(user_id=user_id, tickers=["AAPL"])
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

        trigger = _make_trigger(
            user_id=user_id,
            activation_id=activation.id,
            default_api_key_id=api_key.id,
            mode=TriggerInvocationMode.QUEUE,
        )
        trigger_repo = InMemoryTriggerRepository()
        await trigger_repo.save(trigger)

        task_repo = InMemoryExplorationTaskRepository()
        # Use a FailingAgentInvocationPort to prove the queue branch
        # never reaches the Anthropic invocation step — if it did, the
        # test would surface as INVOCATION_FAILED rather than NEEDS_HUMAN.
        agent_port = FailingAgentInvocationPort(
            message="Queue mode must not call agent invocation"
        )

        fire_repo = InMemoryTriggerFireRepository()
        orchestrator = _build_orchestrator(
            agent_port=agent_port,
            trigger_repo=trigger_repo,
            fire_repo=fire_repo,
            activation_repo=activation_repo,
            strategy_repo=strategy_repo,
            portfolio_repo=portfolio_repo,
            txn_repo=InMemoryTransactionRepository(),
            market_data=InMemoryMarketDataAdapter(),
            api_key_repo=api_key_repo,
            task_repo=task_repo,
        )

        outcome = await orchestrator.fire(
            trigger=trigger, evaluation_data=_evaluation_data()
        )

        # No inline Anthropic invocation happened
        assert len(agent_port.invocations) == 0

        # ExplorationTask was written with the [URGENT] prefix
        open_tasks = await task_repo.list_by_status(ExplorationTaskStatus.OPEN)
        assert len(open_tasks) == 1
        task = open_tasks[0]
        assert task.prompt.startswith("[URGENT]")
        assert "[TRIGGER FIRE]" in task.prompt
        assert task.created_by == user_id
        assert task.target_portfolio_id == portfolio.id
        # Trigger's agent_prompt is composed into the task body
        assert trigger.agent_prompt in task.prompt
        # Condition snapshot is composed too (one field from _evaluation_data)
        assert "drawdown_pct" in task.prompt

        # Audit row landed and points at the queued task.
        # Issue #278 — queue-mode fires no longer overload NEEDS_HUMAN.
        # The outcome carries `decision=None`; the record carries
        # `invocation_mode=QUEUE` and `agent_response=None`.
        assert outcome.decision is None
        assert outcome.error is None
        record = await fire_repo.get(outcome.fire_record_id)
        assert record is not None
        assert record.invocation_mode is TriggerInvocationMode.QUEUE
        assert record.agent_response is None
        assert record.resulting_exploration_task_id == task.id
        assert record.resulting_trade_id is None
        assert record.resulting_modify_payload is None
        assert record.api_key_id_used == api_key.id
        # The raw rationale is empty on queue-mode rows — the queue
        # marker that used to be stashed there is replaced by the
        # dedicated invocation_mode column.
        assert record.agent_response_raw == ""

        # Trigger's last_fired_at advanced so cooldown applies
        reloaded = await trigger_repo.get(trigger.id)
        assert reloaded is not None
        assert reloaded.last_fired_at is not None

    async def test_direct_mode_still_calls_agent_invocation(self) -> None:
        """A DIRECT trigger continues to invoke the agent and skips the queue."""
        user_id = uuid4()
        api_key = _make_api_key(user_id=user_id)
        api_key_repo = InMemoryApiKeyRepository()
        await api_key_repo.save(api_key)

        strategy = _make_strategy(user_id=user_id, tickers=["AAPL"])
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

        trigger = _make_trigger(
            user_id=user_id,
            activation_id=activation.id,
            default_api_key_id=api_key.id,
            mode=TriggerInvocationMode.DIRECT,
        )
        trigger_repo = InMemoryTriggerRepository()
        await trigger_repo.save(trigger)

        task_repo = InMemoryExplorationTaskRepository()
        agent_port = StaticAgentInvocationPort(
            result=make_result(
                decision=AgentDecision.HOLD,
                rationale="Drawdown within tolerance — staying the course.",
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
            txn_repo=InMemoryTransactionRepository(),
            market_data=InMemoryMarketDataAdapter(),
            api_key_repo=api_key_repo,
            task_repo=task_repo,
        )

        outcome = await orchestrator.fire(
            trigger=trigger, evaluation_data=_evaluation_data()
        )

        # Agent WAS called
        assert len(agent_port.invocations) == 1

        # No queue-mode exploration task was filed by the orchestrator
        open_tasks = await task_repo.list_by_status(ExplorationTaskStatus.OPEN)
        assert open_tasks == []

        # Audit row reflects HOLD (the agent's decision), not NEEDS_HUMAN
        record = await fire_repo.get(outcome.fire_record_id)
        assert record is not None
        assert record.invocation_mode is TriggerInvocationMode.DIRECT
        assert record.agent_response is AgentDecision.HOLD
        assert record.resulting_exploration_task_id is None

    async def test_queue_mode_audit_row_is_well_formed(self) -> None:
        """The audit row written in queue mode satisfies the entity invariants."""
        user_id = uuid4()
        api_key = _make_api_key(user_id=user_id)
        api_key_repo = InMemoryApiKeyRepository()
        await api_key_repo.save(api_key)

        strategy = _make_strategy(user_id=user_id, tickers=["AAPL"])
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

        trigger = _make_trigger(
            user_id=user_id,
            activation_id=activation.id,
            default_api_key_id=api_key.id,
            mode=TriggerInvocationMode.QUEUE,
        )
        trigger_repo = InMemoryTriggerRepository()
        await trigger_repo.save(trigger)

        task_repo = InMemoryExplorationTaskRepository()
        agent_port = StaticAgentInvocationPort(
            result=make_result(decision=AgentDecision.HOLD),
        )

        fire_repo = InMemoryTriggerFireRepository()
        orchestrator = _build_orchestrator(
            agent_port=agent_port,
            trigger_repo=trigger_repo,
            fire_repo=fire_repo,
            activation_repo=activation_repo,
            strategy_repo=strategy_repo,
            portfolio_repo=portfolio_repo,
            txn_repo=InMemoryTransactionRepository(),
            market_data=InMemoryMarketDataAdapter(),
            api_key_repo=api_key_repo,
            task_repo=task_repo,
        )

        outcome = await orchestrator.fire(
            trigger=trigger, evaluation_data=_evaluation_data()
        )

        record = await fire_repo.get(outcome.fire_record_id)
        assert record is not None
        # Issue #278 — queue-mode rows: invocation_mode=QUEUE,
        # agent_response=None, resulting_exploration_task_id set,
        # the other resulting_* pointers null.
        assert record.invocation_mode is TriggerInvocationMode.QUEUE
        assert record.agent_response is None
        assert record.resulting_exploration_task_id is not None
        assert record.resulting_trade_id is None
        assert record.resulting_modify_payload is None
        # Latency is non-negative
        assert record.latency_ms >= 0
        # Condition evaluation data round-trips
        assert record.condition_evaluation_data["schema_version"] == 1
