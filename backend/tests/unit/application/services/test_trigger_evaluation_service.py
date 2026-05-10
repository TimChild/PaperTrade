"""Tests for :class:`TriggerEvaluationService` (Phase F-2).

In-memory adapters end-to-end. Covers:

* Empty trigger list ⇒ zero summary, no errors.
* Trigger with crashing portfolio fires; evaluation data is populated.
* Trigger in cooldown is skipped (counted as ``skipped``, not ``fired``).
* Two ACTIVE triggers; one in cooldown ⇒ one returns a fire result.
* Trigger whose activation is missing ⇒ failed (counted, not fatal).
* Per-ticker drawdown using strategy ticker history.

The service composes the I/O around the pure :func:`evaluate_drawdown`
function — these tests verify the I/O wiring (not the evaluator
arithmetic, which has its own unit tests).
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from zebu.adapters.outbound.market_data.in_memory_adapter import (
    InMemoryMarketDataAdapter,
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
from zebu.application.ports.in_memory_trigger_repository import (
    InMemoryTriggerRepository,
)
from zebu.application.services.trigger_evaluation_service import (
    TriggerEvaluationService,
)
from zebu.domain.entities.portfolio import Portfolio
from zebu.domain.entities.strategy import Strategy
from zebu.domain.entities.strategy_activation import StrategyActivation
from zebu.domain.entities.strategy_condition_trigger import StrategyConditionTrigger
from zebu.domain.entities.transaction import Transaction, TransactionType
from zebu.domain.value_objects.activation_frequency import ActivationFrequency
from zebu.domain.value_objects.activation_status import ActivationStatus
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
# Builders
# ---------------------------------------------------------------------------

_AGENT_PROMPT = "Decide whether to hold the position based on news + earnings context."


def _make_strategy(
    *,
    user_id: UUID,
    tickers: list[str] | None = None,
) -> Strategy:
    tickers = tickers or ["AAPL"]
    return Strategy(
        id=uuid4(),
        user_id=user_id,
        name="Test Strategy",
        strategy_type=StrategyType.BUY_AND_HOLD,
        tickers=tickers,
        parameters=BuyAndHoldParameters(
            allocation={t: Decimal("1") / Decimal(len(tickers)) for t in tickers}
        ),
        created_at=datetime.now(UTC) - timedelta(days=60),
    )


def _make_portfolio(*, user_id: UUID, name: str = "Trigger Portfolio") -> Portfolio:
    return Portfolio(
        id=uuid4(),
        user_id=user_id,
        name=name,
        created_at=datetime.now(UTC) - timedelta(days=60),
        portfolio_type=PortfolioType.PAPER_TRADING,
    )


def _make_activation(
    *,
    user_id: UUID,
    strategy_id: UUID,
    portfolio_id: UUID,
) -> StrategyActivation:
    when = datetime.now(UTC) - timedelta(days=45)
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
    threshold_pct: str = "5",
    metric: DrawdownMetric = DrawdownMetric.PORTFOLIO_TOTAL,
    lookback_days: int = 30,
    cooldown_seconds: int = 21600,
    last_fired_at: datetime | None = None,
    status: TriggerStatus = TriggerStatus.ACTIVE,
    priority: int = 0,
    created_at: datetime | None = None,
) -> StrategyConditionTrigger:
    when = created_at or (datetime.now(UTC) - timedelta(days=10))
    return StrategyConditionTrigger(
        id=uuid4(),
        activation_id=activation_id,
        user_id=user_id,
        condition_type=ConditionType.DRAWDOWN_THRESHOLD,
        condition_params=DrawdownParams(
            threshold_pct=Decimal(threshold_pct),
            lookback_days=lookback_days,
            metric=metric,
        ),
        agent_prompt=_AGENT_PROMPT,
        status=status,
        priority=priority,
        cooldown_seconds=cooldown_seconds,
        last_fired_at=last_fired_at,
        created_at=when,
        updated_at=when,
        created_by=user_id,
    )


async def _seed_initial_deposit(
    *,
    txn_repo: InMemoryTransactionRepository,
    portfolio_id: UUID,
    when: datetime,
    amount: str = "10000",
) -> Transaction:
    transaction = Transaction(
        id=uuid4(),
        portfolio_id=portfolio_id,
        transaction_type=TransactionType.DEPOSIT,
        timestamp=when,
        cash_change=Money(Decimal(amount), "USD"),
    )
    await txn_repo.save(transaction)
    return transaction


async def _seed_buy(
    *,
    txn_repo: InMemoryTransactionRepository,
    portfolio_id: UUID,
    ticker: str,
    when: datetime,
    quantity: str,
    price: str,
) -> Transaction:
    qty = Quantity(Decimal(quantity))
    price_money = Money(Decimal(price), "USD")
    cost = price_money.multiply(qty.shares)
    transaction = Transaction(
        id=uuid4(),
        portfolio_id=portfolio_id,
        transaction_type=TransactionType.BUY,
        timestamp=when,
        cash_change=Money(-cost.amount, "USD"),
        ticker=Ticker(ticker),
        quantity=qty,
        price_per_share=price_money,
    )
    await txn_repo.save(transaction)
    return transaction


def _seed_price_history(
    market_data: InMemoryMarketDataAdapter,
    *,
    ticker: str,
    days_to_prices: list[tuple[int, str]],
) -> None:
    """Seed price history. ``days_to_prices`` is [(days_ago, price_str)]."""
    for days_ago, price in days_to_prices:
        timestamp = datetime.now(UTC) - timedelta(days=days_ago)
        market_data.seed_price(
            PricePoint(
                ticker=Ticker(ticker),
                price=Money(Decimal(price), "USD"),
                timestamp=timestamp,
                source="database",
                interval="1day",
                close=Money(Decimal(price), "USD"),
            )
        )


def _build_service(
    *,
    trigger_repo: InMemoryTriggerRepository,
    activation_repo: InMemoryStrategyActivationRepository,
    strategy_repo: InMemoryStrategyRepository,
    portfolio_repo: InMemoryPortfolioRepository,
    transaction_repo: InMemoryTransactionRepository,
    market_data: InMemoryMarketDataAdapter,
) -> TriggerEvaluationService:
    return TriggerEvaluationService(
        trigger_repo=trigger_repo,
        activation_repo=activation_repo,
        strategy_repo=strategy_repo,
        portfolio_repo=portfolio_repo,
        transaction_repo=transaction_repo,
        market_data=market_data,
    )


# ---------------------------------------------------------------------------
# evaluate_all
# ---------------------------------------------------------------------------


class TestEvaluateAll:
    """Service orchestration of trigger evaluations."""

    async def test_no_triggers_is_a_noop(self) -> None:
        """Empty repository ⇒ zero summary."""
        trigger_repo = InMemoryTriggerRepository()
        service = _build_service(
            trigger_repo=trigger_repo,
            activation_repo=InMemoryStrategyActivationRepository(),
            strategy_repo=InMemoryStrategyRepository(),
            portfolio_repo=InMemoryPortfolioRepository(),
            transaction_repo=InMemoryTransactionRepository(),
            market_data=InMemoryMarketDataAdapter(),
        )

        summary = await service.evaluate_all()

        assert summary["processed"] == 0
        assert summary["fired"] == 0
        assert summary["failed"] == 0
        assert summary["skipped"] == 0
        assert summary["results"] == []

    async def test_trigger_in_cooldown_is_skipped(self) -> None:
        """A trigger that fired 1 minute ago with 1h cooldown is skipped."""
        user_id = uuid4()
        trigger_repo = InMemoryTriggerRepository()
        activation_repo = InMemoryStrategyActivationRepository()

        strategy = _make_strategy(user_id=user_id)
        portfolio = _make_portfolio(user_id=user_id)
        activation = _make_activation(
            user_id=user_id, strategy_id=strategy.id, portfolio_id=portfolio.id
        )
        await activation_repo.save(activation)

        # last_fired_at one minute ago, cooldown 1 hour ⇒ in cooldown.
        trigger = _make_trigger(
            user_id=user_id,
            activation_id=activation.id,
            cooldown_seconds=3600,
            last_fired_at=datetime.now(UTC) - timedelta(minutes=1),
        )
        await trigger_repo.save(trigger)

        # The repo's ``list_evaluable`` only filters by status, so the
        # trigger is returned. The service then filters by cooldown.
        service = _build_service(
            trigger_repo=trigger_repo,
            activation_repo=activation_repo,
            strategy_repo=InMemoryStrategyRepository(),
            portfolio_repo=InMemoryPortfolioRepository(),
            transaction_repo=InMemoryTransactionRepository(),
            market_data=InMemoryMarketDataAdapter(),
        )

        summary = await service.evaluate_all()

        # Cooldown'd trigger is counted as skipped, not processed.
        assert summary["processed"] == 0
        assert summary["fired"] == 0
        assert summary["skipped"] == 1
        assert summary["results"] == []

    async def test_two_triggers_one_in_cooldown_returns_one_evaluation(self) -> None:
        """Mix: one fire-eligible + one in cooldown ⇒ one entry in results."""
        user_id = uuid4()
        trigger_repo = InMemoryTriggerRepository()
        activation_repo = InMemoryStrategyActivationRepository()
        strategy_repo = InMemoryStrategyRepository()
        portfolio_repo = InMemoryPortfolioRepository()
        txn_repo = InMemoryTransactionRepository()
        market_data = InMemoryMarketDataAdapter()

        strategy = _make_strategy(user_id=user_id, tickers=["AAPL"])
        await strategy_repo.save(strategy)
        portfolio = _make_portfolio(user_id=user_id)
        await portfolio_repo.save(portfolio)
        activation = _make_activation(
            user_id=user_id, strategy_id=strategy.id, portfolio_id=portfolio.id
        )
        await activation_repo.save(activation)

        # Seed a portfolio with a clear drawdown: bought AAPL high, prices
        # have crashed.
        await _seed_initial_deposit(
            txn_repo=txn_repo,
            portfolio_id=portfolio.id,
            when=datetime.now(UTC) - timedelta(days=29),
            amount="10000",
        )
        await _seed_buy(
            txn_repo=txn_repo,
            portfolio_id=portfolio.id,
            ticker="AAPL",
            when=datetime.now(UTC) - timedelta(days=28),
            quantity="50",
            price="100",
        )
        # Prices: 28d ago $100; today $80. Portfolio went from
        # $5000 cash + $5000 holdings ($100 * 50 = $5000) = $10000 to
        # $5000 cash + $4000 holdings ($80 * 50 = $4000) = $9000.
        # 10% drawdown, well above 5% threshold.
        _seed_price_history(
            market_data,
            ticker="AAPL",
            days_to_prices=[
                (28, "100"),
                (20, "100"),
                (15, "95"),
                (10, "90"),
                (5, "85"),
                (1, "80"),
                (0, "80"),
            ],
        )

        # Eligible trigger ⇒ should fire.
        eligible = _make_trigger(
            user_id=user_id,
            activation_id=activation.id,
            threshold_pct="5",
            cooldown_seconds=3600,
            last_fired_at=None,
        )
        # Cooldown'd trigger ⇒ should be skipped.
        cooled = _make_trigger(
            user_id=user_id,
            activation_id=activation.id,
            threshold_pct="5",
            cooldown_seconds=3600,
            last_fired_at=datetime.now(UTC) - timedelta(minutes=1),
        )
        await trigger_repo.save(eligible)
        await trigger_repo.save(cooled)

        service = _build_service(
            trigger_repo=trigger_repo,
            activation_repo=activation_repo,
            strategy_repo=strategy_repo,
            portfolio_repo=portfolio_repo,
            transaction_repo=txn_repo,
            market_data=market_data,
        )

        summary = await service.evaluate_all()

        assert summary["processed"] == 1
        assert summary["fired"] == 1
        assert summary["skipped"] == 1
        assert summary["failed"] == 0
        # The result is for the eligible trigger only.
        assert len(summary["results"]) == 1
        result = summary["results"][0]
        assert result["trigger_id"] == eligible.id
        assert result["fired"] is True
        assert result["evaluation_data"] is not None
        assert result["evaluation_data"]["metric"] == "PORTFOLIO_TOTAL"
        assert result["error"] is None

    async def test_trigger_with_missing_activation_is_failed_not_fatal(
        self,
    ) -> None:
        """Activation deleted but trigger left dangling ⇒ counts as failed."""
        user_id = uuid4()
        trigger_repo = InMemoryTriggerRepository()
        activation_repo = InMemoryStrategyActivationRepository()  # empty

        # Trigger with a never-saved activation_id.
        trigger = _make_trigger(
            user_id=user_id,
            activation_id=uuid4(),  # no matching activation
        )
        await trigger_repo.save(trigger)

        service = _build_service(
            trigger_repo=trigger_repo,
            activation_repo=activation_repo,
            strategy_repo=InMemoryStrategyRepository(),
            portfolio_repo=InMemoryPortfolioRepository(),
            transaction_repo=InMemoryTransactionRepository(),
            market_data=InMemoryMarketDataAdapter(),
        )

        summary = await service.evaluate_all()

        assert summary["processed"] == 1
        assert summary["fired"] == 0
        assert summary["failed"] == 1
        assert len(summary["results"]) == 1
        assert summary["results"][0]["error"] is not None
        assert summary["results"][0]["fired"] is False

    async def test_pure_cash_portfolio_does_not_fire(self) -> None:
        """Portfolio with only cash (never bought anything) ⇒ no drawdown."""
        user_id = uuid4()
        trigger_repo = InMemoryTriggerRepository()
        activation_repo = InMemoryStrategyActivationRepository()
        strategy_repo = InMemoryStrategyRepository()
        portfolio_repo = InMemoryPortfolioRepository()
        txn_repo = InMemoryTransactionRepository()
        market_data = InMemoryMarketDataAdapter()

        strategy = _make_strategy(user_id=user_id)
        await strategy_repo.save(strategy)
        portfolio = _make_portfolio(user_id=user_id)
        await portfolio_repo.save(portfolio)
        activation = _make_activation(
            user_id=user_id, strategy_id=strategy.id, portfolio_id=portfolio.id
        )
        await activation_repo.save(activation)

        # Just one deposit, no holdings, no price changes ⇒ portfolio
        # value is constant cash. No drawdown.
        await _seed_initial_deposit(
            txn_repo=txn_repo,
            portfolio_id=portfolio.id,
            when=datetime.now(UTC) - timedelta(days=29),
            amount="10000",
        )
        # Price history is irrelevant for a pure-cash portfolio.
        _seed_price_history(
            market_data,
            ticker="AAPL",
            days_to_prices=[(28, "100"), (1, "100")],
        )

        trigger = _make_trigger(
            user_id=user_id, activation_id=activation.id, threshold_pct="5"
        )
        await trigger_repo.save(trigger)

        service = _build_service(
            trigger_repo=trigger_repo,
            activation_repo=activation_repo,
            strategy_repo=strategy_repo,
            portfolio_repo=portfolio_repo,
            transaction_repo=txn_repo,
            market_data=market_data,
        )

        summary = await service.evaluate_all()

        assert summary["processed"] == 1
        # No drawdown on a pure-cash portfolio (value is flat).
        assert summary["fired"] == 0
        assert summary["skipped"] == 1
        assert summary["failed"] == 0

    async def test_per_ticker_metric_uses_strategy_tickers(self) -> None:
        """PER_TICKER drawdown reads price history per ticker, not portfolio."""
        user_id = uuid4()
        trigger_repo = InMemoryTriggerRepository()
        activation_repo = InMemoryStrategyActivationRepository()
        strategy_repo = InMemoryStrategyRepository()
        portfolio_repo = InMemoryPortfolioRepository()
        txn_repo = InMemoryTransactionRepository()
        market_data = InMemoryMarketDataAdapter()

        strategy = _make_strategy(user_id=user_id, tickers=["NVDA"])
        await strategy_repo.save(strategy)
        portfolio = _make_portfolio(user_id=user_id)
        await portfolio_repo.save(portfolio)
        activation = _make_activation(
            user_id=user_id, strategy_id=strategy.id, portfolio_id=portfolio.id
        )
        await activation_repo.save(activation)

        # NVDA crashes 20% from peak — well above the 5% threshold.
        _seed_price_history(
            market_data,
            ticker="NVDA",
            days_to_prices=[
                (28, "1000"),
                (20, "1100"),
                (15, "1200"),  # peak
                (10, "1100"),
                (5, "1000"),
                (1, "960"),  # 20% off peak
            ],
        )

        trigger = _make_trigger(
            user_id=user_id,
            activation_id=activation.id,
            threshold_pct="5",
            metric=DrawdownMetric.PER_TICKER,
        )
        await trigger_repo.save(trigger)

        service = _build_service(
            trigger_repo=trigger_repo,
            activation_repo=activation_repo,
            strategy_repo=strategy_repo,
            portfolio_repo=portfolio_repo,
            transaction_repo=txn_repo,
            market_data=market_data,
        )

        summary = await service.evaluate_all()

        assert summary["processed"] == 1
        assert summary["fired"] == 1
        result = summary["results"][0]
        assert result["evaluation_data"] is not None
        assert result["evaluation_data"]["metric"] == "PER_TICKER"
        assert result["evaluation_data"]["ticker"] == "NVDA"

    async def test_paused_trigger_is_not_evaluated(self) -> None:
        """``list_evaluable`` already filters PAUSED ⇒ paused trigger absent."""
        user_id = uuid4()
        trigger_repo = InMemoryTriggerRepository()

        trigger = _make_trigger(
            user_id=user_id,
            activation_id=uuid4(),  # activation absent — would otherwise fail
            status=TriggerStatus.PAUSED,
        )
        await trigger_repo.save(trigger)

        service = _build_service(
            trigger_repo=trigger_repo,
            activation_repo=InMemoryStrategyActivationRepository(),
            strategy_repo=InMemoryStrategyRepository(),
            portfolio_repo=InMemoryPortfolioRepository(),
            transaction_repo=InMemoryTransactionRepository(),
            market_data=InMemoryMarketDataAdapter(),
        )

        summary = await service.evaluate_all()

        # PAUSED trigger isn't returned by ``list_evaluable``, so it's
        # not counted in any of the buckets — it never enters the
        # service.
        assert summary["processed"] == 0
        assert summary["fired"] == 0
        assert summary["failed"] == 0
        assert summary["skipped"] == 0
