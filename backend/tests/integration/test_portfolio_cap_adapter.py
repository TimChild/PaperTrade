"""Integration tests for :class:`PortfolioCapRepositoryAdapter` (Phase F-6).

The SQL adapter reads ``transactions`` rows where ``api_key_id IS NOT
NULL`` for the portfolio within today's UTC window and applies the
configured caps. These tests seed real transactions via the SQL repo and
verify the adapter's count/sum logic.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from sqlmodel.ext.asyncio.session import AsyncSession

from zebu.adapters.outbound.database.api_key_model import ApiKeyModel
from zebu.adapters.outbound.database.models import (
    PortfolioModel,
    StrategyActivationModel,
    StrategyConditionTriggerModel,
    StrategyModel,
)
from zebu.adapters.outbound.database.portfolio_cap_adapter import (
    PortfolioCapRepositoryAdapter,
)
from zebu.adapters.outbound.database.transaction_repository import (
    SQLModelTransactionRepository,
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


async def _seed_chain(
    session: AsyncSession,
) -> tuple[Portfolio, ApiKey, StrategyConditionTrigger]:
    """Seed the FK chain: portfolio → strategy → activation → key → trigger."""
    user_id = uuid4()

    portfolio = Portfolio(
        id=uuid4(),
        user_id=user_id,
        name="Cap Adapter Portfolio",
        created_at=datetime.now(UTC) - timedelta(days=30),
        portfolio_type=PortfolioType.PAPER_TRADING,
    )
    session.add(PortfolioModel.from_domain(portfolio))
    await session.flush()

    strategy = Strategy(
        id=uuid4(),
        user_id=user_id,
        name="Cap Adapter Strategy",
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
        clerk_user_id="user_cap_adapter",
        label="cap-adapter-key",
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
        agent_prompt="Decide whether to hold.",
        status=TriggerStatus.ACTIVE,
        created_at=datetime.now(UTC) - timedelta(days=10),
        updated_at=datetime.now(UTC) - timedelta(days=10),
        created_by=user_id,
        default_api_key_id=api_key.id,
    )
    session.add(StrategyConditionTriggerModel.from_domain(trigger))
    await session.flush()

    return portfolio, api_key, trigger


def _make_buy(
    *,
    portfolio_id: UUID,
    cash_change: str,
    timestamp: datetime,
) -> Transaction:
    """Build a BUY transaction with the given cash impact."""
    return Transaction(
        id=uuid4(),
        portfolio_id=portfolio_id,
        transaction_type=TransactionType.BUY,
        timestamp=timestamp,
        cash_change=Money(Decimal(cash_change), "USD"),
        ticker=Ticker("AAPL"),
        quantity=Quantity(Decimal("1")),
        price_per_share=Money(abs(Decimal(cash_change)), "USD"),
        notes="agent-driven BUY",
    )


class TestPortfolioCapAdapter:
    """SQL adapter reads today's agent-trade volume correctly."""

    async def test_no_prior_agent_trades_allows_first_buy(
        self,
        session: AsyncSession,
    ) -> None:
        """Empty state: BUY $500 against $5000 cap → allowed."""
        portfolio, _, _ = await _seed_chain(session)
        cap_adapter = PortfolioCapRepositoryAdapter(
            session,
            cap_count=10,
            cap_value_usd=Decimal("5000"),
        )

        result = await cap_adapter.check(
            portfolio_id=portfolio.id,
            attempted_decision=AgentDecision.BUY,
            attempted_value_usd=Decimal("500"),
        )
        assert result.allowed is True
        assert result.current_count == 0
        assert result.current_value_usd == Decimal("0")

    async def test_excludes_human_trades_from_cap(
        self,
        session: AsyncSession,
    ) -> None:
        """Trades without ``api_key_id`` (Clerk Bearer) don't consume the cap."""
        portfolio, _, _ = await _seed_chain(session)
        txn_repo = SQLModelTransactionRepository(session)

        # Human-driven trade (api_key_id=None) — should NOT count toward cap.
        human_buy = _make_buy(
            portfolio_id=portfolio.id,
            cash_change="-3000",
            timestamp=datetime.now(UTC) - timedelta(hours=2),
        )
        await txn_repo.save(human_buy)
        await session.flush()

        cap_adapter = PortfolioCapRepositoryAdapter(
            session,
            cap_count=10,
            cap_value_usd=Decimal("5000"),
        )
        result = await cap_adapter.check(
            portfolio_id=portfolio.id,
            attempted_decision=AgentDecision.BUY,
            attempted_value_usd=Decimal("4000"),
        )
        # current_value_usd is 0 because the human trade was excluded.
        assert result.allowed is True
        assert result.current_count == 0
        assert result.current_value_usd == Decimal("0")

    async def test_sums_agent_trade_volume_for_today(
        self,
        session: AsyncSession,
    ) -> None:
        """Multiple agent-driven trades today sum into the binding metric."""
        portfolio, api_key, _ = await _seed_chain(session)
        txn_repo = SQLModelTransactionRepository(session)

        # Anchor trade timestamps to today's UTC midnight + 12h so the
        # test is deterministic regardless of the wall-clock hour (a
        # bare ``datetime.now(UTC) - timedelta(hours=3)`` lands in
        # yesterday's UTC window when CI runs between 00:00 and 04:00).
        today_noon_utc = datetime.now(UTC).replace(
            hour=12, minute=0, second=0, microsecond=0
        )

        # Two agent-driven trades earlier today, $1500 + $2000 = $3500
        # consumed.
        for cash, hours_ago in ((-1500, 3), (-2000, 1)):
            buy = _make_buy(
                portfolio_id=portfolio.id,
                cash_change=str(cash),
                timestamp=today_noon_utc - timedelta(hours=hours_ago),
            )
            await txn_repo.save(buy, api_key_id=api_key.id)
        await session.flush()

        cap_adapter = PortfolioCapRepositoryAdapter(
            session,
            cap_count=10,
            cap_value_usd=Decimal("5000"),
        )

        # Attempted $1000 — fits ($3500 + $1000 = $4500 <= $5000).
        result = await cap_adapter.check(
            portfolio_id=portfolio.id,
            attempted_decision=AgentDecision.BUY,
            attempted_value_usd=Decimal("1000"),
        )
        assert result.allowed is True
        assert result.current_count == 2
        assert result.current_value_usd == Decimal("3500")

    async def test_over_value_cap_denies(
        self,
        session: AsyncSession,
    ) -> None:
        """Attempted trade that would push over the value cap is denied."""
        portfolio, api_key, _ = await _seed_chain(session)
        txn_repo = SQLModelTransactionRepository(session)

        # See test_sums_agent_trade_volume_for_today — anchor to today's
        # UTC noon so the timestamps stay inside today's window regardless
        # of when CI runs.
        today_noon_utc = datetime.now(UTC).replace(
            hour=12, minute=0, second=0, microsecond=0
        )

        # Existing $4500 spent today.
        for cash, hours_ago in ((-2500, 4), (-2000, 2)):
            buy = _make_buy(
                portfolio_id=portfolio.id,
                cash_change=str(cash),
                timestamp=today_noon_utc - timedelta(hours=hours_ago),
            )
            await txn_repo.save(buy, api_key_id=api_key.id)
        await session.flush()

        cap_adapter = PortfolioCapRepositoryAdapter(
            session,
            cap_count=10,
            cap_value_usd=Decimal("5000"),
        )
        # Attempted $1000 → would total $5500, over the cap.
        result = await cap_adapter.check(
            portfolio_id=portfolio.id,
            attempted_decision=AgentDecision.BUY,
            attempted_value_usd=Decimal("1000"),
        )
        assert result.allowed is False
        assert result.reason is not None
        assert "$5000" in result.reason
        assert "$4500" in result.reason

    async def test_yesterday_trades_excluded_from_today_window(
        self,
        session: AsyncSession,
    ) -> None:
        """Trades from a previous UTC day don't contribute to today's cap."""
        portfolio, api_key, _ = await _seed_chain(session)
        txn_repo = SQLModelTransactionRepository(session)

        # Trade from yesterday (well outside the UTC day window).
        old_buy = _make_buy(
            portfolio_id=portfolio.id,
            cash_change="-4900",
            timestamp=datetime.now(UTC) - timedelta(days=2),
        )
        await txn_repo.save(old_buy, api_key_id=api_key.id)
        await session.flush()

        cap_adapter = PortfolioCapRepositoryAdapter(
            session,
            cap_count=10,
            cap_value_usd=Decimal("5000"),
        )
        # Today the cap should be fully available.
        result = await cap_adapter.check(
            portfolio_id=portfolio.id,
            attempted_decision=AgentDecision.BUY,
            attempted_value_usd=Decimal("1000"),
        )
        assert result.allowed is True
        assert result.current_count == 0
        assert result.current_value_usd == Decimal("0")
