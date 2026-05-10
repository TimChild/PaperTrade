"""Integration test for :class:`TriggerEvaluationService` (Phase F-2).

Verifies the service composes correctly against the **SQL** repository
adapters (not the in-memory ones used by the unit suite). Catches
SQL-side wiring bugs — wrong session handling, missing joins, dialect
quirks — that wouldn't show up against in-memory.

Scope:

* One ACTIVE trigger eligible to evaluate (out of cooldown, not expired)
  fires when the portfolio is down >= threshold from peak.
* One ACTIVE trigger in cooldown is skipped.
* The cycle returns the correct EvaluationSummary counts.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from sqlmodel.ext.asyncio.session import AsyncSession

from zebu.adapters.outbound.database.api_key_model import ApiKeyModel
from zebu.adapters.outbound.database.models import (
    PortfolioModel,
    StrategyActivationModel,
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
from zebu.adapters.outbound.earnings.stub_calendar_adapter import (
    StubEarningsCalendarAdapter,
)
from zebu.adapters.outbound.market_data.in_memory_adapter import (
    InMemoryMarketDataAdapter,
)
from zebu.application.services.trigger_evaluation_service import (
    TriggerEvaluationService,
)
from zebu.domain.entities.api_key import ApiKey
from zebu.domain.entities.portfolio import Portfolio
from zebu.domain.entities.strategy import Strategy
from zebu.domain.entities.strategy_activation import StrategyActivation
from zebu.domain.entities.strategy_condition_trigger import StrategyConditionTrigger
from zebu.domain.entities.transaction import Transaction, TransactionType
from zebu.domain.value_objects.activation_frequency import ActivationFrequency
from zebu.domain.value_objects.activation_status import ActivationStatus
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


async def _seed_portfolio_with_drawdown(
    session: AsyncSession,
    *,
    user_id: object,
    ticker: str = "AAPL",
) -> tuple[Portfolio, Strategy, StrategyActivation, ApiKey]:
    """Seed: cash deposit + buy at $100; today's price will be $80 (20% loss)."""
    portfolio = Portfolio(
        id=uuid4(),
        user_id=user_id,  # type: ignore[arg-type]
        name="Test Portfolio",
        created_at=datetime.now(UTC) - timedelta(days=60),
        portfolio_type=PortfolioType.PAPER_TRADING,
    )
    session.add(PortfolioModel.from_domain(portfolio))
    await session.flush()

    strategy = Strategy(
        id=uuid4(),
        user_id=user_id,  # type: ignore[arg-type]
        name="Test Strategy",
        strategy_type=StrategyType.BUY_AND_HOLD,
        tickers=[ticker],
        parameters=BuyAndHoldParameters(allocation={ticker: Decimal("1.0")}),
        created_at=datetime.now(UTC) - timedelta(days=60),
    )
    session.add(StrategyModel.from_domain(strategy))
    await session.flush()

    activation = StrategyActivation(
        id=uuid4(),
        user_id=user_id,  # type: ignore[arg-type]
        strategy_id=strategy.id,
        portfolio_id=portfolio.id,
        status=ActivationStatus.ACTIVE,
        frequency=ActivationFrequency.DAILY_MARKET_CLOSE,
        created_at=datetime.now(UTC) - timedelta(days=45),
        updated_at=datetime.now(UTC) - timedelta(days=45),
    )
    session.add(StrategyActivationModel.from_domain(activation))
    await session.flush()

    api_key = ApiKey(
        id=uuid4(),
        user_id=user_id,  # type: ignore[arg-type]
        clerk_user_id="clerk_user_test",
        label="test-key",
        key_hash="hash_" + "0" * 60,
        scopes=frozenset({ApiKeyScope.READ, ApiKeyScope.TRADE}),
        created_at=datetime.now(UTC) - timedelta(days=60),
    )
    session.add(ApiKeyModel.from_domain(api_key))
    await session.flush()

    # Seed transactions: deposit + buy. Transactions only depend on
    # portfolio (already flushed) so a single flush at the end suffices.
    deposit = Transaction(
        id=uuid4(),
        portfolio_id=portfolio.id,
        transaction_type=TransactionType.DEPOSIT,
        timestamp=datetime.now(UTC) - timedelta(days=29),
        cash_change=Money(Decimal("10000"), "USD"),
    )
    session.add(TransactionModel.from_domain(deposit))

    buy_price = Money(Decimal("100"), "USD")
    buy_qty = Quantity(Decimal("50"))
    buy = Transaction(
        id=uuid4(),
        portfolio_id=portfolio.id,
        transaction_type=TransactionType.BUY,
        timestamp=datetime.now(UTC) - timedelta(days=28),
        cash_change=Money(-(buy_price.amount * buy_qty.shares), "USD"),
        ticker=Ticker(ticker),
        quantity=buy_qty,
        price_per_share=buy_price,
    )
    session.add(TransactionModel.from_domain(buy))
    await session.flush()

    return portfolio, strategy, activation, api_key


def _build_market_data(*, ticker: str = "AAPL") -> InMemoryMarketDataAdapter:
    """Seed the in-memory market data adapter with a price crash.

    28 days ago the ticker was at $100; today it's at $80. A 5%
    drawdown trigger should fire.
    """
    adapter = InMemoryMarketDataAdapter()
    days_to_prices = [
        (28, "100"),
        (20, "100"),
        (15, "95"),
        (10, "90"),
        (5, "85"),
        (1, "80"),
        (0, "80"),
    ]
    for days_ago, price in days_to_prices:
        timestamp = datetime.now(UTC) - timedelta(days=days_ago)
        adapter.seed_price(
            PricePoint(
                ticker=Ticker(ticker),
                price=Money(Decimal(price), "USD"),
                timestamp=timestamp,
                source="database",
                interval="1day",
                close=Money(Decimal(price), "USD"),
            )
        )
    return adapter


class TestTriggerEvaluationServiceSQL:
    """End-to-end integration of the service against SQL adapters."""

    async def test_eligible_trigger_fires_with_real_db(
        self,
        session: AsyncSession,
    ) -> None:
        """Real Postgres-flavour SQL adapters: eligible trigger fires."""
        user_id = uuid4()
        _, _, activation, api_key = await _seed_portfolio_with_drawdown(
            session, user_id=user_id
        )

        # Persist an ACTIVE trigger with no cooldown elapsed.
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
        trigger_repo = SQLModelTriggerRepository(session)
        await trigger_repo.save(trigger)
        await session.flush()

        service = TriggerEvaluationService(
            trigger_repo=trigger_repo,
            activation_repo=SQLModelStrategyActivationRepository(session),
            strategy_repo=SQLModelStrategyRepository(session),
            portfolio_repo=SQLModelPortfolioRepository(session),
            transaction_repo=SQLModelTransactionRepository(session),
            market_data=_build_market_data(),
            earnings_calendar=StubEarningsCalendarAdapter(),
        )

        summary = await service.evaluate_all()

        assert summary["processed"] == 1
        assert summary["fired"] == 1
        assert summary["failed"] == 0
        assert summary["skipped"] == 0
        result = summary["results"][0]
        assert result["trigger_id"] == trigger.id
        assert result["fired"] is True
        evaluation_data = result["evaluation_data"]
        assert evaluation_data is not None
        # Narrow to the drawdown shape — for a DRAWDOWN_THRESHOLD trigger
        # the union ``EvaluationData`` is always populated with the
        # drawdown variant. A ``"metric"`` key only exists on that
        # variant.
        assert "metric" in evaluation_data
        assert evaluation_data["metric"] == "PORTFOLIO_TOTAL"

        # Test note: F-2 doesn't yet write a TriggerFireRecord — that
        # comes in F-3 alongside the agent invocation. The trigger's
        # ``last_fired_at`` is also unchanged for the same reason.
        reloaded = await trigger_repo.get(trigger.id)
        assert reloaded is not None
        assert reloaded.last_fired_at is None

    async def test_one_eligible_one_in_cooldown_returns_one_fire(
        self,
        session: AsyncSession,
    ) -> None:
        """Mix in cooldown + eligible triggers ⇒ only the eligible runs."""
        user_id = uuid4()
        _, _, activation, api_key = await _seed_portfolio_with_drawdown(
            session, user_id=user_id
        )

        eligible = StrategyConditionTrigger(
            id=uuid4(),
            activation_id=activation.id,
            user_id=user_id,
            condition_type=ConditionType.DRAWDOWN_THRESHOLD,
            condition_params=DrawdownParams(
                threshold_pct=Decimal("5"),
                lookback_days=30,
            ),
            agent_prompt="Decide whether to hold based on the latest context.",
            status=TriggerStatus.ACTIVE,
            cooldown_seconds=21600,
            created_at=datetime.now(UTC) - timedelta(days=10),
            updated_at=datetime.now(UTC) - timedelta(days=10),
            created_by=user_id,
            default_api_key_id=api_key.id,
        )
        cooled = StrategyConditionTrigger(
            id=uuid4(),
            activation_id=activation.id,
            user_id=user_id,
            condition_type=ConditionType.DRAWDOWN_THRESHOLD,
            condition_params=DrawdownParams(
                threshold_pct=Decimal("5"),
                lookback_days=30,
            ),
            agent_prompt="Same condition, but in cooldown — must be skipped.",
            status=TriggerStatus.ACTIVE,
            cooldown_seconds=3600,
            last_fired_at=datetime.now(UTC) - timedelta(minutes=1),
            created_at=datetime.now(UTC) - timedelta(days=10),
            updated_at=datetime.now(UTC) - timedelta(minutes=1),
            created_by=user_id,
            default_api_key_id=api_key.id,
        )

        trigger_repo = SQLModelTriggerRepository(session)
        await trigger_repo.save(eligible)
        await trigger_repo.save(cooled)
        await session.flush()

        service = TriggerEvaluationService(
            trigger_repo=trigger_repo,
            activation_repo=SQLModelStrategyActivationRepository(session),
            strategy_repo=SQLModelStrategyRepository(session),
            portfolio_repo=SQLModelPortfolioRepository(session),
            transaction_repo=SQLModelTransactionRepository(session),
            market_data=_build_market_data(),
            earnings_calendar=StubEarningsCalendarAdapter(),
        )

        summary = await service.evaluate_all()

        # 2 candidates from list_evaluable; 1 filtered out by cooldown
        # check; 1 actually evaluated.
        assert summary["processed"] == 1
        assert summary["fired"] == 1
        assert summary["skipped"] == 1
        assert summary["failed"] == 0
        # Only the eligible trigger appears in results.
        assert len(summary["results"]) == 1
        assert summary["results"][0]["trigger_id"] == eligible.id
