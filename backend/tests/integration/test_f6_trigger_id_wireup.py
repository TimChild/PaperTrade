"""End-to-end integration test for the F-5 → F-3 ``trigger_id`` wire-up.

Phase F-6 closes the loop: when the orchestrator executes a BUY/SELL,
the resulting transaction row carries ``trigger_id = trigger.id``.
Earlier phases:

- F-1: schema column + entity field exist.
- F-5: ``transactions.trigger_id`` FK + migration land.
- F-6 (this PR): the orchestrator actually passes ``trigger_id=`` to
  ``transaction_repo.save_all``.

This test exercises the full SQL path: real :class:`SQLModelTransactionRepository`,
real :class:`SQLModelTriggerRepository`, real :class:`SQLModelTriggerFireRepository`,
in-memory market data + agent invocation (the boundary mocks).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from sqlmodel.ext.asyncio.session import AsyncSession

from zebu.adapters.outbound.database.api_key_model import ApiKeyModel
from zebu.adapters.outbound.database.api_key_repository import (
    SQLModelApiKeyRepository,
)
from zebu.adapters.outbound.database.exploration_task_repository import (
    SQLModelExplorationTaskRepository,
)
from zebu.adapters.outbound.database.models import (
    PortfolioModel,
    StrategyActivationModel,
    StrategyConditionTriggerModel,
    StrategyModel,
    TransactionModel,
)
from zebu.adapters.outbound.database.portfolio_repository import (
    SQLModelPortfolioRepository,
)
from zebu.adapters.outbound.database.strategy_activation_repository import (
    SQLModelStrategyActivationRepository,
)
from zebu.adapters.outbound.database.strategy_condition_trigger_repository import (
    SQLModelTriggerRepository,
)
from zebu.adapters.outbound.database.strategy_repository import (
    SQLModelStrategyRepository,
)
from zebu.adapters.outbound.database.transaction_repository import (
    SQLModelTransactionRepository,
)
from zebu.adapters.outbound.database.trigger_fire_repository import (
    SQLModelTriggerFireRepository,
)
from zebu.adapters.outbound.market_data.in_memory_adapter import (
    InMemoryMarketDataAdapter,
)
from zebu.application.ports.in_memory_agent_invocation_port import (
    StaticAgentInvocationPort,
    make_result,
)
from zebu.application.ports.in_memory_portfolio_cap_port import (
    InMemoryPortfolioCapPort,
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
from zebu.domain.value_objects.money import Money
from zebu.domain.value_objects.portfolio_type import PortfolioType
from zebu.domain.value_objects.price_point import PricePoint
from zebu.domain.value_objects.strategy_parameters import BuyAndHoldParameters
from zebu.domain.value_objects.strategy_type import StrategyType
from zebu.domain.value_objects.ticker import Ticker
from zebu.domain.value_objects.trigger_condition import (
    ConditionType,
    DrawdownMetric,
    DrawdownParams,
)
from zebu.domain.value_objects.trigger_status import TriggerStatus


async def _seed_full_fixture(
    session: AsyncSession,
) -> tuple[Portfolio, StrategyConditionTrigger, ApiKey]:
    """Insert portfolio → strategy → activation → trigger → api_key + cash deposit."""
    user_id = uuid4()

    portfolio = Portfolio(
        id=uuid4(),
        user_id=user_id,
        name="F-6 Wire-up Portfolio",
        created_at=datetime.now(UTC) - timedelta(days=30),
        portfolio_type=PortfolioType.PAPER_TRADING,
    )
    session.add(PortfolioModel.from_domain(portfolio))
    await session.flush()

    strategy = Strategy(
        id=uuid4(),
        user_id=user_id,
        name="F-6 Wire-up Strategy",
        strategy_type=StrategyType.BUY_AND_HOLD,
        tickers=["AAPL"],
        parameters=BuyAndHoldParameters(allocation={"AAPL": Decimal("1.0")}),
        created_at=datetime.now(UTC) - timedelta(days=30),
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
        created_at=datetime.now(UTC) - timedelta(days=20),
        updated_at=datetime.now(UTC) - timedelta(days=20),
    )
    session.add(StrategyActivationModel.from_domain(activation))
    await session.flush()

    api_key = ApiKey(
        id=uuid4(),
        user_id=user_id,
        clerk_user_id="user_f6_wireup",
        label="f6-wireup-key",
        key_hash="hash_" + "0" * 60,
        scopes=frozenset({ApiKeyScope.READ, ApiKeyScope.TRADE}),
        created_at=datetime.now(UTC) - timedelta(days=15),
    )
    session.add(ApiKeyModel.from_domain(api_key))
    await session.flush()

    trigger = StrategyConditionTrigger(
        id=uuid4(),
        activation_id=activation.id,
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
        cooldown_seconds=21600,
        created_at=datetime.now(UTC) - timedelta(days=10),
        updated_at=datetime.now(UTC) - timedelta(days=10),
        created_by=user_id,
        default_api_key_id=api_key.id,
    )
    session.add(StrategyConditionTriggerModel.from_domain(trigger))
    await session.flush()

    # Seed cash deposit so the BUY has cash to use.
    deposit = Transaction(
        id=uuid4(),
        portfolio_id=portfolio.id,
        transaction_type=TransactionType.DEPOSIT,
        timestamp=datetime.now(UTC) - timedelta(days=29),
        cash_change=Money(Decimal("10000"), "USD"),
        notes="seed",
    )
    txn_repo = SQLModelTransactionRepository(session)
    await txn_repo.save(deposit)
    await session.flush()

    return portfolio, trigger, api_key


def _build_market_data() -> InMemoryMarketDataAdapter:
    """Seed AAPL prices so price queries succeed."""
    adapter = InMemoryMarketDataAdapter()
    adapter.seed_price(
        PricePoint(
            ticker=Ticker("AAPL"),
            price=Money(Decimal("150"), "USD"),
            timestamp=datetime.now(UTC) - timedelta(minutes=1),
            source="database",
            interval="1day",
            close=Money(Decimal("150"), "USD"),
        )
    )
    return adapter


class TestTriggerIdWireUp:
    """Fire a trigger → orchestrator → resulting transaction has trigger_id set."""

    async def test_buy_decision_persists_transaction_with_trigger_id(
        self,
        session: AsyncSession,
    ) -> None:
        """The full SQL path stamps the trigger id onto the transaction."""
        portfolio, trigger, api_key = await _seed_full_fixture(session)

        orchestrator = TriggerInvocationOrchestrator(
            agent_invocation=StaticAgentInvocationPort(
                result=make_result(
                    decision=AgentDecision.BUY,
                    rationale="Drawdown signal triggered, accumulating modestly.",
                    payload={
                        "ticker": "AAPL",
                        "quantity": "3",
                        "notes": "BUY 3 AAPL on signal",
                    },
                )
            ),
            trigger_repo=SQLModelTriggerRepository(session),
            trigger_fire_repo=SQLModelTriggerFireRepository(session),
            activation_repo=SQLModelStrategyActivationRepository(session),
            strategy_repo=SQLModelStrategyRepository(session),
            portfolio_repo=SQLModelPortfolioRepository(session),
            transaction_repo=SQLModelTransactionRepository(session),
            market_data=_build_market_data(),
            api_key_repo=SQLModelApiKeyRepository(session),
            exploration_task_repo=SQLModelExplorationTaskRepository(session),
            portfolio_cap=InMemoryPortfolioCapPort(
                default_cap_count=10,
                default_cap_value_usd=Decimal("5000"),
            ),
        )

        outcome = await orchestrator.fire(
            trigger=trigger,
            evaluation_data={
                "schema_version": 1,
                "metric": "PORTFOLIO_TOTAL",
                "drawdown_pct": "8.5",
            },
        )
        assert outcome.decision is AgentDecision.BUY
        assert outcome.error is None

        await session.flush()

        # The resulting transaction row should carry ``trigger_id`` set
        # to the firing trigger's id — the F-5 → F-3 wire-up.
        txn_repo = SQLModelTransactionRepository(session)
        all_txns = await txn_repo.get_by_portfolio(portfolio.id)
        buys = [t for t in all_txns if t.transaction_type is TransactionType.BUY]
        assert len(buys) == 1
        buy = buys[0]

        # Re-read at the model level to inspect the audit column directly.
        persisted = await session.get(TransactionModel, buy.id)
        assert persisted is not None
        assert persisted.trigger_id == trigger.id
        # Sanity: api_key_id is also stamped (Phase H2 wire-up).
        assert persisted.api_key_id == api_key.id

    async def test_capped_buy_does_not_persist_transaction(
        self,
        session: AsyncSession,
    ) -> None:
        """A cap-blocked BUY leaves no transaction (and so no trigger_id)."""
        portfolio, trigger, _ = await _seed_full_fixture(session)

        cap_port = InMemoryPortfolioCapPort(
            default_cap_count=10,
            default_cap_value_usd=Decimal("100"),  # tiny cap
        )

        orchestrator = TriggerInvocationOrchestrator(
            agent_invocation=StaticAgentInvocationPort(
                result=make_result(
                    decision=AgentDecision.BUY,
                    rationale="Trying to BUY despite tiny cap.",
                    payload={
                        "ticker": "AAPL",
                        "quantity": "3",
                        "notes": "BUY 3 AAPL — cap should block",
                    },
                )
            ),
            trigger_repo=SQLModelTriggerRepository(session),
            trigger_fire_repo=SQLModelTriggerFireRepository(session),
            activation_repo=SQLModelStrategyActivationRepository(session),
            strategy_repo=SQLModelStrategyRepository(session),
            portfolio_repo=SQLModelPortfolioRepository(session),
            transaction_repo=SQLModelTransactionRepository(session),
            market_data=_build_market_data(),
            api_key_repo=SQLModelApiKeyRepository(session),
            exploration_task_repo=SQLModelExplorationTaskRepository(session),
            portfolio_cap=cap_port,
        )

        outcome = await orchestrator.fire(
            trigger=trigger,
            evaluation_data={"schema_version": 1, "metric": "PORTFOLIO_TOTAL"},
        )
        # Downgraded to HOLD.
        assert outcome.decision is AgentDecision.HOLD
        assert outcome.error is not None
        assert "$100" in outcome.error

        await session.flush()

        # No BUY transaction was persisted — only the seed deposit
        # exists.
        txn_repo = SQLModelTransactionRepository(session)
        all_txns = await txn_repo.get_by_portfolio(portfolio.id)
        buys = [t for t in all_txns if t.transaction_type is TransactionType.BUY]
        assert len(buys) == 0
