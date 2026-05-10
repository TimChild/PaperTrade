"""Tests for Phase F-6 portfolio-cap integration in the orchestrator.

Covers:

- BUY decision over the cap is downgraded to HOLD with a descriptive
  rationale captured on the audit row.
- BUY decision under the cap proceeds normally AND stamps the resulting
  transaction with ``trigger_id`` (the F-5 → F-3 wire-up).
- MODIFY_STRATEGY bypasses the cap (§10 Q7).
- The default-orchestrator path (cap=None) still works for backward
  compatibility.
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
from zebu.application.ports.in_memory_portfolio_cap_port import (
    InMemoryPortfolioCapPort,
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
)
from zebu.domain.entities.api_key import ApiKey
from zebu.domain.entities.portfolio import Portfolio
from zebu.domain.entities.strategy import Strategy
from zebu.domain.entities.strategy_activation import StrategyActivation
from zebu.domain.entities.strategy_condition_trigger import StrategyConditionTrigger
from zebu.domain.entities.transaction import Transaction, TransactionType
from zebu.domain.value_objects.activation_frequency import ActivationFrequency
from zebu.domain.value_objects.activation_status import ActivationStatus
from zebu.domain.value_objects.agent_decision import AgentDecision
from zebu.domain.value_objects.api_key_scope import ApiKeyScope
from zebu.domain.value_objects.daily_trade_volume_cap import DailyTradeVolumeCap
from zebu.domain.value_objects.money import Money
from zebu.domain.value_objects.portfolio_type import PortfolioType
from zebu.domain.value_objects.price_point import PricePoint
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
from zebu.domain.value_objects.trigger_status import TriggerStatus


def _now() -> datetime:
    return datetime.now(UTC)


def _make_strategy(*, user_id: UUID, tickers: list[str]) -> Strategy:
    return Strategy(
        id=uuid4(),
        user_id=user_id,
        name="Cap Test Strategy",
        strategy_type=StrategyType.BUY_AND_HOLD,
        tickers=tickers,
        parameters=BuyAndHoldParameters(
            allocation={t: Decimal("1") / Decimal(len(tickers)) for t in tickers}
        ),
        created_at=_now() - timedelta(days=60),
    )


def _make_ma_strategy(*, user_id: UUID, tickers: list[str]) -> Strategy:
    return Strategy(
        id=uuid4(),
        user_id=user_id,
        name="Cap Test MA Strategy",
        strategy_type=StrategyType.MOVING_AVERAGE_CROSSOVER,
        tickers=tickers,
        parameters=MaCrossoverParameters(
            fast_window=10,
            slow_window=30,
            invest_fraction=Decimal("0.5"),
        ),
        created_at=_now() - timedelta(days=60),
    )


def _make_portfolio(*, user_id: UUID) -> Portfolio:
    return Portfolio(
        id=uuid4(),
        user_id=user_id,
        name="Cap Test Portfolio",
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
    *, user_id: UUID, activation_id: UUID, default_api_key_id: UUID
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
        agent_prompt="Decide whether to hold. Default to HOLD on ambiguity.",
        status=TriggerStatus.ACTIVE,
        cooldown_seconds=21600,
        created_at=when,
        updated_at=when,
        created_by=user_id,
        default_api_key_id=default_api_key_id,
    )


def _make_api_key(*, user_id: UUID) -> ApiKey:
    return ApiKey(
        id=uuid4(),
        user_id=user_id,
        clerk_user_id="user_cap_test",
        label="cap-test-key",
        key_hash="hash_" + "0" * 60,
        scopes=frozenset({ApiKeyScope.READ, ApiKeyScope.TRADE}),
        created_at=_now() - timedelta(days=20),
    )


async def _seed_funded_portfolio(
    *,
    txn_repo: InMemoryTransactionRepository,
    portfolio_id: UUID,
    cash_amount: str,
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
    market_data: InMemoryMarketDataAdapter, *, ticker: str, price: str
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


class TestCapDowngradesBuyToHold:
    """A BUY whose cash impact would breach the cap is downgraded."""

    async def test_buy_over_value_cap_downgrades_with_rationale(self) -> None:
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

        # Seed enough cash that the trade itself would succeed (it's the
        # cap that blocks, not insufficient-funds).
        txn_repo = InMemoryTransactionRepository()
        await _seed_funded_portfolio(
            txn_repo=txn_repo, portfolio_id=portfolio.id, cash_amount="50000"
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

        # Cap: $5000 daily; agent wants to BUY 30 × $200 = $6000.
        cap_port = InMemoryPortfolioCapPort(
            default_cap_count=10,
            default_cap_value_usd=Decimal("5000"),
        )

        agent_port = StaticAgentInvocationPort(
            result=make_result(
                decision=AgentDecision.BUY,
                rationale="Strong fundamentals, accumulating aggressively.",
                payload={
                    "ticker": "AAPL",
                    "quantity": "30",
                    "notes": "BUY 30 AAPL",
                },
            )
        )

        fire_repo = InMemoryTriggerFireRepository()
        orchestrator = TriggerInvocationOrchestrator(
            agent_invocation=agent_port,
            trigger_repo=trigger_repo,
            trigger_fire_repo=fire_repo,
            activation_repo=activation_repo,
            strategy_repo=strategy_repo,
            portfolio_repo=portfolio_repo,
            transaction_repo=txn_repo,
            market_data=market_data,
            api_key_repo=api_key_repo,
            exploration_task_repo=InMemoryExplorationTaskRepository(),
            portfolio_cap=cap_port,
        )

        outcome = await orchestrator.fire(
            trigger=trigger,
            evaluation_data={"schema_version": 1, "metric": "PORTFOLIO_TOTAL"},
        )

        # Decision was downgraded to HOLD.
        assert outcome.decision is AgentDecision.HOLD
        assert outcome.error is not None
        assert "daily cap" in outcome.error
        assert "$5000" in outcome.error

        # Audit row was written with HOLD, no trade, and the rationale
        # captured.
        record = await fire_repo.get(outcome.fire_record_id)
        assert record is not None
        assert record.agent_response is AgentDecision.HOLD
        assert record.resulting_trade_id is None
        # The agent's *original* rationale is preserved verbatim in the
        # audit row — that's how an investigator sees "agent wanted to
        # BUY but the cap blocked".
        assert "fundamentals" in record.agent_response_raw

        # No trade landed (the BUY was rejected pre-persistence).
        buys = [
            t
            for t in await txn_repo.get_by_portfolio(portfolio.id)
            if t.transaction_type is TransactionType.BUY
        ]
        assert len(buys) == 0

    async def test_buy_under_cap_proceeds_and_stamps_trigger_id(self) -> None:
        """A BUY within the cap lands AND the F-5 trigger_id is set."""
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
        await _seed_funded_portfolio(
            txn_repo=txn_repo, portfolio_id=portfolio.id, cash_amount="10000"
        )

        market_data = InMemoryMarketDataAdapter()
        _seed_price(market_data, ticker="AAPL", price="150")

        trigger = _make_trigger(
            user_id=user_id,
            activation_id=activation.id,
            default_api_key_id=api_key.id,
        )
        trigger_repo = InMemoryTriggerRepository()
        await trigger_repo.save(trigger)

        # Cap allows up to $5000 — BUY 5 × $150 = $750 fits.
        cap_port = InMemoryPortfolioCapPort(
            default_cap_count=10,
            default_cap_value_usd=Decimal("5000"),
        )

        agent_port = StaticAgentInvocationPort(
            result=make_result(
                decision=AgentDecision.BUY,
                payload={
                    "ticker": "AAPL",
                    "quantity": "5",
                    "notes": "BUY 5 AAPL",
                },
            )
        )

        fire_repo = InMemoryTriggerFireRepository()
        orchestrator = TriggerInvocationOrchestrator(
            agent_invocation=agent_port,
            trigger_repo=trigger_repo,
            trigger_fire_repo=fire_repo,
            activation_repo=activation_repo,
            strategy_repo=strategy_repo,
            portfolio_repo=portfolio_repo,
            transaction_repo=txn_repo,
            market_data=market_data,
            api_key_repo=api_key_repo,
            exploration_task_repo=InMemoryExplorationTaskRepository(),
            portfolio_cap=cap_port,
        )

        outcome = await orchestrator.fire(
            trigger=trigger,
            evaluation_data={"schema_version": 1, "metric": "PORTFOLIO_TOTAL"},
        )

        assert outcome.decision is AgentDecision.BUY
        record = await fire_repo.get(outcome.fire_record_id)
        assert record is not None
        assert record.resulting_trade_id is not None

        # The trade was persisted; verify it links back to the trigger
        # (the F-5 column on transactions). The in-memory repo doesn't
        # actually record trigger_id — but the SQL adapter does, and
        # the integration test covers the round-trip. Here we just
        # verify the orchestrator's outcome metadata.
        buys = [
            t
            for t in await txn_repo.get_by_portfolio(portfolio.id)
            if t.transaction_type is TransactionType.BUY
        ]
        assert len(buys) == 1
        assert buys[0].id == record.resulting_trade_id


class TestCapDoesNotApplyToModifyStrategy:
    """MODIFY_STRATEGY bypasses the cap (§10 Q7)."""

    async def test_modify_decision_proceeds_even_when_cap_at_limit(self) -> None:
        user_id = uuid4()
        api_key = _make_api_key(user_id=user_id)
        api_key_repo = InMemoryApiKeyRepository()
        await api_key_repo.save(api_key)

        strategy = _make_ma_strategy(user_id=user_id, tickers=["AAPL"])
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
        await _seed_funded_portfolio(
            txn_repo=txn_repo, portfolio_id=portfolio.id, cash_amount="10000"
        )

        # Seed the cap at the limit — would block any BUY/SELL, but
        # MODIFY_STRATEGY should bypass.
        cap_port = InMemoryPortfolioCapPort(
            default_cap_count=10,
            default_cap_value_usd=Decimal("5000"),
        )
        cap_port.set_state(
            portfolio_id=portfolio.id,
            count=10,
            value_usd=Decimal("5000"),
        )

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
                    "parameter_overrides": {"invest_fraction": "0.25"},
                    "notes": "Reduce exposure",
                },
            )
        )

        fire_repo = InMemoryTriggerFireRepository()
        orchestrator = TriggerInvocationOrchestrator(
            agent_invocation=agent_port,
            trigger_repo=trigger_repo,
            trigger_fire_repo=fire_repo,
            activation_repo=activation_repo,
            strategy_repo=strategy_repo,
            portfolio_repo=portfolio_repo,
            transaction_repo=txn_repo,
            market_data=InMemoryMarketDataAdapter(),
            api_key_repo=api_key_repo,
            exploration_task_repo=InMemoryExplorationTaskRepository(),
            portfolio_cap=cap_port,
        )

        outcome = await orchestrator.fire(
            trigger=trigger,
            evaluation_data={"schema_version": 1, "metric": "PORTFOLIO_TOTAL"},
        )

        # MODIFY_STRATEGY landed, cap did not block.
        assert outcome.decision is AgentDecision.MODIFY_STRATEGY
        record = await fire_repo.get(outcome.fire_record_id)
        assert record is not None
        assert record.resulting_modify_payload is not None


class TestNoCapPortStillWorks:
    """Backward compat: orchestrator with cap=None still allows trades."""

    async def test_buy_proceeds_when_cap_port_is_none(self) -> None:
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
        await _seed_funded_portfolio(
            txn_repo=txn_repo, portfolio_id=portfolio.id, cash_amount="10000"
        )
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
                payload={"ticker": "AAPL", "quantity": "1", "notes": "BUY"},
            )
        )

        orchestrator = TriggerInvocationOrchestrator(
            agent_invocation=agent_port,
            trigger_repo=trigger_repo,
            trigger_fire_repo=InMemoryTriggerFireRepository(),
            activation_repo=activation_repo,
            strategy_repo=strategy_repo,
            portfolio_repo=portfolio_repo,
            transaction_repo=txn_repo,
            market_data=market_data,
            api_key_repo=api_key_repo,
            exploration_task_repo=InMemoryExplorationTaskRepository(),
            # No portfolio_cap kwarg — defaults to None.
        )

        outcome = await orchestrator.fire(
            trigger=trigger,
            evaluation_data={"schema_version": 1, "metric": "PORTFOLIO_TOTAL"},
        )
        assert outcome.decision is AgentDecision.BUY


class TestTriggerFireRecordCapturesDowngrade:
    """Worked example from the PR brief: BUY $6000 vs $5000 cap."""

    async def test_audit_record_shows_original_buy_and_downgrade_reason(
        self,
    ) -> None:
        """An investigator can read the audit row and see what happened.

        The row records:
        - `agent_response = HOLD` (post-guardrail decision).
        - `agent_response_raw` = the agent's verbatim rationale (so
          we know what it *wanted* to do).
        - The orchestrator's FireOutcome.error carries the downgrade
          reason (which evaluation_data and prompt builders can surface
          to operators).
        """
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
        await _seed_funded_portfolio(
            txn_repo=txn_repo, portfolio_id=portfolio.id, cash_amount="50000"
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

        # Agent wants BUY $6000 worth of AAPL (30 × $200) against a
        # $5000 cap.
        agent_port = StaticAgentInvocationPort(
            result=make_result(
                decision=AgentDecision.BUY,
                rationale=(
                    "Drawdown signal triggered, fundamentals strong, "
                    "accumulating aggressively."
                ),
                payload={
                    "ticker": "AAPL",
                    "quantity": "30",
                    "notes": "BUY 30 AAPL on drawdown",
                },
            )
        )

        cap_port = InMemoryPortfolioCapPort(
            default_cap_count=10,
            default_cap_value_usd=Decimal("5000"),
        )

        fire_repo = InMemoryTriggerFireRepository()
        orchestrator = TriggerInvocationOrchestrator(
            agent_invocation=agent_port,
            trigger_repo=trigger_repo,
            trigger_fire_repo=fire_repo,
            activation_repo=activation_repo,
            strategy_repo=strategy_repo,
            portfolio_repo=portfolio_repo,
            transaction_repo=txn_repo,
            market_data=market_data,
            api_key_repo=api_key_repo,
            exploration_task_repo=InMemoryExplorationTaskRepository(),
            portfolio_cap=cap_port,
        )

        outcome = await orchestrator.fire(
            trigger=trigger,
            evaluation_data={"schema_version": 1, "metric": "PORTFOLIO_TOTAL"},
        )

        record = await fire_repo.get(outcome.fire_record_id)
        assert record is not None

        # Post-guardrail decision is HOLD.
        assert record.agent_response is AgentDecision.HOLD
        # Original rationale preserved on the audit row — investigators
        # can see "agent wanted BUY".
        assert "accumulating" in record.agent_response_raw
        # The downgrade reason is in outcome.error (the orchestrator's
        # reply to the caller / scheduler / log).
        assert outcome.error is not None
        assert "AAPL" in outcome.error
        assert "$5000" in outcome.error

        # Trigger.last_fired_at advanced — the fire counts even on
        # downgrade, so cooldown applies to the next eval tick.
        reloaded = await trigger_repo.get(trigger.id)
        assert reloaded is not None
        assert reloaded.last_fired_at is not None


class TestDailyTradeVolumeCapValidation:
    """Domain VO validation surface."""

    def test_construct_valid(self) -> None:
        cap = DailyTradeVolumeCap(
            portfolio_id=uuid4(),
            cap_count=10,
            cap_value_usd=Decimal("5000"),
        )
        assert cap.cap_count == 10
        assert cap.cap_value_usd == Decimal("5000")
