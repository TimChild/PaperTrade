"""Tests for StrategyExecutionService.

Phase C1.2 — covers the live single-day execution pipeline:

* Successful execution emits transactions and bumps ``last_executed_at``.
* A failure on one activation does not block other activations.
* Empty signal list is a no-op (no transactions, no error).
* Missing portfolio / strategy flips the activation to ERROR.
* Manual ``execute_one`` returns a structured per-activation result.

All tests use in-memory adapters — no DB / scheduler is required.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import cast
from uuid import uuid4

import pytest

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
from zebu.application.ports.market_data_port import MarketDataPort
from zebu.application.services.strategy_execution_service import (
    StrategyExecutionService,
)
from zebu.domain.entities.portfolio import Portfolio
from zebu.domain.entities.strategy import Strategy
from zebu.domain.entities.strategy_activation import StrategyActivation
from zebu.domain.entities.transaction import Transaction, TransactionType
from zebu.domain.value_objects.activation_frequency import ActivationFrequency
from zebu.domain.value_objects.activation_status import ActivationStatus
from zebu.domain.value_objects.money import Money
from zebu.domain.value_objects.portfolio_type import PortfolioType
from zebu.domain.value_objects.price_point import PricePoint
from zebu.domain.value_objects.strategy_parameters import (
    BuyAndHoldParameters,
    DcaParameters,
    MaCrossoverParameters,
)
from zebu.domain.value_objects.strategy_type import StrategyType
from zebu.domain.value_objects.ticker import Ticker

# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _make_strategy(
    *,
    user_id: object,
    tickers: list[str] | None = None,
    allocation: dict[str, str] | None = None,
) -> Strategy:
    """Build a BUY_AND_HOLD strategy. Defaults to 100% AAPL."""
    tickers = tickers or ["AAPL"]
    raw_allocation = allocation or {"AAPL": "1.0"}
    return Strategy(
        id=uuid4(),
        user_id=cast(object, user_id),  # type: ignore[arg-type]
        name="Test Strategy",
        strategy_type=StrategyType.BUY_AND_HOLD,
        tickers=tickers,
        parameters=BuyAndHoldParameters(
            allocation={k: Decimal(v) for k, v in raw_allocation.items()}
        ),
        created_at=datetime.now(UTC),
    )


def _make_portfolio(*, user_id: object, name: str = "Live Portfolio") -> Portfolio:
    """Build a PAPER_TRADING portfolio."""
    return Portfolio(
        id=uuid4(),
        user_id=cast(object, user_id),  # type: ignore[arg-type]
        name=name,
        created_at=datetime.now(UTC) - timedelta(seconds=1),
        portfolio_type=PortfolioType.PAPER_TRADING,
    )


def _make_activation(
    *,
    user_id: object,
    strategy_id: object,
    portfolio_id: object,
    status: ActivationStatus = ActivationStatus.ACTIVE,
) -> StrategyActivation:
    """Build a StrategyActivation in the requested status."""
    now = datetime.now(UTC) - timedelta(seconds=1)
    return StrategyActivation(
        id=uuid4(),
        user_id=cast(object, user_id),  # type: ignore[arg-type]
        strategy_id=cast(object, strategy_id),  # type: ignore[arg-type]
        portfolio_id=cast(object, portfolio_id),  # type: ignore[arg-type]
        status=status,
        frequency=ActivationFrequency.DAILY_MARKET_CLOSE,
        created_at=now,
        updated_at=now,
        last_error=("previous failure" if status is ActivationStatus.ERROR else None),
    )


async def _seed_initial_deposit(
    *,
    txn_repo: InMemoryTransactionRepository,
    portfolio_id: object,
    amount: str = "10000",
) -> None:
    """Seed a portfolio with an initial cash deposit."""
    transaction = Transaction(
        id=uuid4(),
        portfolio_id=cast(object, portfolio_id),  # type: ignore[arg-type]
        transaction_type=TransactionType.DEPOSIT,
        timestamp=datetime.now(UTC) - timedelta(minutes=1),
        cash_change=Money(Decimal(amount), "USD"),
        ticker=None,
        quantity=None,
        price_per_share=None,
        notes="Seed",
    )
    await txn_repo.save(transaction)


def _seed_price(
    market_data: InMemoryMarketDataAdapter,
    symbol: str,
    *,
    price: str = "100.00",
) -> None:
    """Seed a single most-recent price for a ticker."""
    market_data.seed_price(
        PricePoint(
            ticker=Ticker(symbol),
            price=Money(Decimal(price), "USD"),
            timestamp=datetime.now(UTC) - timedelta(minutes=1),
            source="database",
            interval="real-time",
        )
    )


def _build_service(
    *,
    activation_repo: InMemoryStrategyActivationRepository,
    strategy_repo: InMemoryStrategyRepository,
    portfolio_repo: InMemoryPortfolioRepository,
    transaction_repo: InMemoryTransactionRepository,
    market_data: MarketDataPort,
) -> StrategyExecutionService:
    """Construct the SUT with the supplied fakes."""
    return StrategyExecutionService(
        activation_repo=activation_repo,
        strategy_repo=strategy_repo,
        portfolio_repo=portfolio_repo,
        transaction_repo=transaction_repo,
        market_data=market_data,
    )


# ---------------------------------------------------------------------------
# execute_active_strategies
# ---------------------------------------------------------------------------


class TestExecuteActiveStrategies:
    """Behaviour of the scheduler-facing batch entry point."""

    async def test_no_active_activations_is_a_noop(self) -> None:
        """An empty active list returns a zero summary, no errors raised."""
        activation_repo = InMemoryStrategyActivationRepository()
        strategy_repo = InMemoryStrategyRepository()
        portfolio_repo = InMemoryPortfolioRepository()
        txn_repo = InMemoryTransactionRepository()
        market_data = InMemoryMarketDataAdapter()

        service = _build_service(
            activation_repo=activation_repo,
            strategy_repo=strategy_repo,
            portfolio_repo=portfolio_repo,
            transaction_repo=txn_repo,
            market_data=market_data,
        )

        summary = await service.execute_active_strategies()

        assert summary == {
            "processed": 0,
            "succeeded": 0,
            "failed": 0,
            "trades": 0,
        }

    async def test_successful_execution_persists_trades(self) -> None:
        """A BUY_AND_HOLD activation produces a single BUY transaction."""
        user_id = uuid4()
        activation_repo = InMemoryStrategyActivationRepository()
        strategy_repo = InMemoryStrategyRepository()
        portfolio_repo = InMemoryPortfolioRepository()
        txn_repo = InMemoryTransactionRepository()
        market_data = InMemoryMarketDataAdapter()

        portfolio = _make_portfolio(user_id=user_id)
        await portfolio_repo.save(portfolio)
        await _seed_initial_deposit(
            txn_repo=txn_repo, portfolio_id=portfolio.id, amount="10000"
        )

        strategy = _make_strategy(user_id=user_id, tickers=["AAPL"])
        await strategy_repo.save(strategy)

        activation = _make_activation(
            user_id=user_id,
            strategy_id=strategy.id,
            portfolio_id=portfolio.id,
        )
        await activation_repo.save(activation)

        _seed_price(market_data, "AAPL", price="100.00")

        service = _build_service(
            activation_repo=activation_repo,
            strategy_repo=strategy_repo,
            portfolio_repo=portfolio_repo,
            transaction_repo=txn_repo,
            market_data=market_data,
        )

        summary = await service.execute_active_strategies()

        assert summary["processed"] == 1
        assert summary["succeeded"] == 1
        assert summary["failed"] == 0
        # 100% allocation of $10,000 at $100/sh = 100 BUY shares.
        assert summary["trades"] == 1
        all_txns = await txn_repo.get_by_portfolio(portfolio.id)
        buy_txns = [t for t in all_txns if t.transaction_type is TransactionType.BUY]
        assert len(buy_txns) == 1
        assert buy_txns[0].ticker == Ticker("AAPL")

        # last_executed_at was bumped, status is still ACTIVE.
        reloaded = await activation_repo.get(activation.id)
        assert reloaded is not None
        assert reloaded.status is ActivationStatus.ACTIVE
        assert reloaded.last_executed_at is not None
        assert reloaded.last_error is None

    async def test_one_failing_activation_does_not_block_others(self) -> None:
        """A broken activation is captured as ERROR; healthy ones still run."""
        user_id = uuid4()
        activation_repo = InMemoryStrategyActivationRepository()
        strategy_repo = InMemoryStrategyRepository()
        portfolio_repo = InMemoryPortfolioRepository()
        txn_repo = InMemoryTransactionRepository()
        market_data = InMemoryMarketDataAdapter()

        # Healthy activation
        good_portfolio = _make_portfolio(user_id=user_id, name="Good")
        await portfolio_repo.save(good_portfolio)
        await _seed_initial_deposit(
            txn_repo=txn_repo, portfolio_id=good_portfolio.id, amount="10000"
        )
        good_strategy = _make_strategy(user_id=user_id, tickers=["AAPL"])
        await strategy_repo.save(good_strategy)
        good_activation = _make_activation(
            user_id=user_id,
            strategy_id=good_strategy.id,
            portfolio_id=good_portfolio.id,
        )
        await activation_repo.save(good_activation)

        # Broken activation: strategy_id is dangling so loading fails.
        bad_activation = _make_activation(
            user_id=user_id,
            strategy_id=uuid4(),  # not in strategy_repo
            portfolio_id=good_portfolio.id,
        )
        await activation_repo.save(bad_activation)

        _seed_price(market_data, "AAPL", price="50.00")

        service = _build_service(
            activation_repo=activation_repo,
            strategy_repo=strategy_repo,
            portfolio_repo=portfolio_repo,
            transaction_repo=txn_repo,
            market_data=market_data,
        )

        summary = await service.execute_active_strategies()

        assert summary["processed"] == 2
        assert summary["succeeded"] == 1
        assert summary["failed"] == 1
        assert summary["trades"] >= 1

        bad_reloaded = await activation_repo.get(bad_activation.id)
        good_reloaded = await activation_repo.get(good_activation.id)
        assert bad_reloaded is not None
        assert good_reloaded is not None
        assert bad_reloaded.status is ActivationStatus.ERROR
        assert bad_reloaded.last_error is not None
        assert good_reloaded.status is ActivationStatus.ACTIVE

    async def test_paused_activations_are_skipped(self) -> None:
        """Only ACTIVE activations are pulled from the repo."""
        user_id = uuid4()
        activation_repo = InMemoryStrategyActivationRepository()
        strategy_repo = InMemoryStrategyRepository()
        portfolio_repo = InMemoryPortfolioRepository()
        txn_repo = InMemoryTransactionRepository()
        market_data = InMemoryMarketDataAdapter()

        portfolio = _make_portfolio(user_id=user_id)
        await portfolio_repo.save(portfolio)
        strategy = _make_strategy(user_id=user_id)
        await strategy_repo.save(strategy)

        # Only PAUSED — must not run.
        activation = _make_activation(
            user_id=user_id,
            strategy_id=strategy.id,
            portfolio_id=portfolio.id,
            status=ActivationStatus.PAUSED,
        )
        await activation_repo.save(activation)

        service = _build_service(
            activation_repo=activation_repo,
            strategy_repo=strategy_repo,
            portfolio_repo=portfolio_repo,
            transaction_repo=txn_repo,
            market_data=market_data,
        )

        summary = await service.execute_active_strategies()
        assert summary["processed"] == 0

    async def test_missing_portfolio_marks_activation_error(self) -> None:
        """If the portfolio is gone, the activation flips to ERROR."""
        user_id = uuid4()
        activation_repo = InMemoryStrategyActivationRepository()
        strategy_repo = InMemoryStrategyRepository()
        portfolio_repo = InMemoryPortfolioRepository()
        txn_repo = InMemoryTransactionRepository()
        market_data = InMemoryMarketDataAdapter()

        strategy = _make_strategy(user_id=user_id)
        await strategy_repo.save(strategy)

        activation = _make_activation(
            user_id=user_id,
            strategy_id=strategy.id,
            portfolio_id=uuid4(),  # never saved
        )
        await activation_repo.save(activation)

        service = _build_service(
            activation_repo=activation_repo,
            strategy_repo=strategy_repo,
            portfolio_repo=portfolio_repo,
            transaction_repo=txn_repo,
            market_data=market_data,
        )

        summary = await service.execute_active_strategies()
        assert summary["processed"] == 1
        assert summary["failed"] == 1

        reloaded = await activation_repo.get(activation.id)
        assert reloaded is not None
        assert reloaded.status is ActivationStatus.ERROR
        assert reloaded.last_error is not None
        assert "Portfolio" in reloaded.last_error

    async def test_zero_signals_is_a_noop_for_activation(self) -> None:
        """A second BUY_AND_HOLD run yields no signals (already bought)."""
        user_id = uuid4()
        activation_repo = InMemoryStrategyActivationRepository()
        strategy_repo = InMemoryStrategyRepository()
        portfolio_repo = InMemoryPortfolioRepository()
        txn_repo = InMemoryTransactionRepository()
        market_data = InMemoryMarketDataAdapter()

        portfolio = _make_portfolio(user_id=user_id)
        await portfolio_repo.save(portfolio)
        await _seed_initial_deposit(
            txn_repo=txn_repo, portfolio_id=portfolio.id, amount="10000"
        )
        strategy = _make_strategy(user_id=user_id, tickers=["AAPL"])
        await strategy_repo.save(strategy)
        activation = _make_activation(
            user_id=user_id,
            strategy_id=strategy.id,
            portfolio_id=portfolio.id,
        )
        await activation_repo.save(activation)
        _seed_price(market_data, "AAPL", price="100.00")

        service = _build_service(
            activation_repo=activation_repo,
            strategy_repo=strategy_repo,
            portfolio_repo=portfolio_repo,
            transaction_repo=txn_repo,
            market_data=market_data,
        )

        first = await service.execute_active_strategies()
        assert first["trades"] == 1
        # Second cycle: BuyAndHoldStrategy is constructed fresh each cycle
        # so it would technically buy again — but the cash is gone (used in
        # the first run) so we expect 0 trades, succeeded.
        second = await service.execute_active_strategies()
        assert second["processed"] == 1
        assert second["succeeded"] == 1
        assert second["trades"] == 0

    async def test_missing_price_does_not_fail_activation(self) -> None:
        """A ticker without a price is silently skipped — activation succeeds."""
        user_id = uuid4()
        activation_repo = InMemoryStrategyActivationRepository()
        strategy_repo = InMemoryStrategyRepository()
        portfolio_repo = InMemoryPortfolioRepository()
        txn_repo = InMemoryTransactionRepository()
        market_data = InMemoryMarketDataAdapter()

        portfolio = _make_portfolio(user_id=user_id)
        await portfolio_repo.save(portfolio)
        await _seed_initial_deposit(
            txn_repo=txn_repo, portfolio_id=portfolio.id, amount="10000"
        )
        strategy = _make_strategy(user_id=user_id, tickers=["AAPL"])
        await strategy_repo.save(strategy)
        activation = _make_activation(
            user_id=user_id,
            strategy_id=strategy.id,
            portfolio_id=portfolio.id,
        )
        await activation_repo.save(activation)
        # No price seeded for AAPL.

        service = _build_service(
            activation_repo=activation_repo,
            strategy_repo=strategy_repo,
            portfolio_repo=portfolio_repo,
            transaction_repo=txn_repo,
            market_data=market_data,
        )

        summary = await service.execute_active_strategies()
        # Strategy still ran, but no trades happened (price missing).
        assert summary["processed"] == 1
        assert summary["succeeded"] == 1
        assert summary["trades"] == 0


# ---------------------------------------------------------------------------
# execute_one
# ---------------------------------------------------------------------------


class TestExecuteOne:
    """Behaviour of the manual single-activation entry point."""

    async def test_unknown_activation_id_returns_failure(self) -> None:
        """A missing activation id returns a structured failure result."""
        service = _build_service(
            activation_repo=InMemoryStrategyActivationRepository(),
            strategy_repo=InMemoryStrategyRepository(),
            portfolio_repo=InMemoryPortfolioRepository(),
            transaction_repo=InMemoryTransactionRepository(),
            market_data=InMemoryMarketDataAdapter(),
        )
        unknown_id = uuid4()

        result = await service.execute_one(unknown_id)
        assert result["activation_id"] == unknown_id
        assert result["succeeded"] is False
        assert result["error"] is not None
        assert "not found" in result["error"].lower()

    async def test_runs_paused_activation_via_run_now(self) -> None:
        """``execute_one`` runs the activation regardless of its status.

        ``run-now`` semantics: a user that paused an activation can still
        ask for an ad-hoc execution. Status reflects the *configured*
        cadence; the manual button overrides it.
        """
        user_id = uuid4()
        activation_repo = InMemoryStrategyActivationRepository()
        strategy_repo = InMemoryStrategyRepository()
        portfolio_repo = InMemoryPortfolioRepository()
        txn_repo = InMemoryTransactionRepository()
        market_data = InMemoryMarketDataAdapter()

        portfolio = _make_portfolio(user_id=user_id)
        await portfolio_repo.save(portfolio)
        await _seed_initial_deposit(
            txn_repo=txn_repo, portfolio_id=portfolio.id, amount="10000"
        )
        strategy = _make_strategy(user_id=user_id, tickers=["AAPL"])
        await strategy_repo.save(strategy)
        activation = _make_activation(
            user_id=user_id,
            strategy_id=strategy.id,
            portfolio_id=portfolio.id,
            status=ActivationStatus.PAUSED,
        )
        await activation_repo.save(activation)
        _seed_price(market_data, "AAPL", price="100.00")

        service = _build_service(
            activation_repo=activation_repo,
            strategy_repo=strategy_repo,
            portfolio_repo=portfolio_repo,
            transaction_repo=txn_repo,
            market_data=market_data,
        )
        result = await service.execute_one(activation.id)

        assert result["succeeded"] is True
        assert result["trades"] == 1


# ---------------------------------------------------------------------------
# Strategy-type coverage — DCA and MA Crossover routes through the service
# ---------------------------------------------------------------------------


class TestStrategyTypeRouting:
    """Pin down ``_build_trading_strategy`` for every strategy type."""

    async def test_dca_strategy_runs_through_service(self) -> None:
        """DcaParameters resolves to DollarCostAveragingStrategy."""
        user_id = uuid4()
        activation_repo = InMemoryStrategyActivationRepository()
        strategy_repo = InMemoryStrategyRepository()
        portfolio_repo = InMemoryPortfolioRepository()
        txn_repo = InMemoryTransactionRepository()
        market_data = InMemoryMarketDataAdapter()

        portfolio = _make_portfolio(user_id=user_id)
        await portfolio_repo.save(portfolio)
        await _seed_initial_deposit(
            txn_repo=txn_repo, portfolio_id=portfolio.id, amount="10000"
        )

        strategy = Strategy(
            id=uuid4(),
            user_id=user_id,
            name="DCA AAPL",
            strategy_type=StrategyType.DOLLAR_COST_AVERAGING,
            tickers=["AAPL"],
            parameters=DcaParameters(
                frequency_days=30,
                amount_per_period=Decimal("500"),
                allocation={"AAPL": Decimal("1.0")},
            ),
            created_at=datetime.now(UTC),
        )
        await strategy_repo.save(strategy)

        activation = _make_activation(
            user_id=user_id,
            strategy_id=strategy.id,
            portfolio_id=portfolio.id,
        )
        await activation_repo.save(activation)
        _seed_price(market_data, "AAPL", price="100.00")

        service = _build_service(
            activation_repo=activation_repo,
            strategy_repo=strategy_repo,
            portfolio_repo=portfolio_repo,
            transaction_repo=txn_repo,
            market_data=market_data,
        )
        summary = await service.execute_active_strategies()
        assert summary["succeeded"] == 1
        # DCA on day 1 buys $500 / $100 = 5 shares.
        assert summary["trades"] == 1

    async def test_ma_crossover_strategy_runs_through_service(self) -> None:
        """MaCrossoverParameters resolves to MovingAverageCrossoverStrategy.

        With only one day of price data, the SMA windows can't be
        computed — the strategy should run cleanly with zero signals.
        We're proving the type routing here, not the algorithm.
        """
        user_id = uuid4()
        activation_repo = InMemoryStrategyActivationRepository()
        strategy_repo = InMemoryStrategyRepository()
        portfolio_repo = InMemoryPortfolioRepository()
        txn_repo = InMemoryTransactionRepository()
        market_data = InMemoryMarketDataAdapter()

        portfolio = _make_portfolio(user_id=user_id)
        await portfolio_repo.save(portfolio)
        await _seed_initial_deposit(
            txn_repo=txn_repo, portfolio_id=portfolio.id, amount="10000"
        )

        strategy = Strategy(
            id=uuid4(),
            user_id=user_id,
            name="MA Crossover",
            strategy_type=StrategyType.MOVING_AVERAGE_CROSSOVER,
            tickers=["AAPL"],
            parameters=MaCrossoverParameters(
                fast_window=5,
                slow_window=20,
                invest_fraction=Decimal("0.5"),
            ),
            created_at=datetime.now(UTC),
        )
        await strategy_repo.save(strategy)

        activation = _make_activation(
            user_id=user_id,
            strategy_id=strategy.id,
            portfolio_id=portfolio.id,
        )
        await activation_repo.save(activation)
        _seed_price(market_data, "AAPL", price="100.00")

        service = _build_service(
            activation_repo=activation_repo,
            strategy_repo=strategy_repo,
            portfolio_repo=portfolio_repo,
            transaction_repo=txn_repo,
            market_data=market_data,
        )
        summary = await service.execute_active_strategies()
        # No SMA windows → no signals; activation succeeds with zero trades.
        assert summary["succeeded"] == 1
        assert summary["trades"] == 0


# ---------------------------------------------------------------------------
# Holdings seeding — SELL signals validate against current positions
# ---------------------------------------------------------------------------


class TestHoldingsSeeding:
    """A live activation must see the portfolio's existing holdings."""

    async def test_existing_holdings_are_passed_to_strategy(self) -> None:
        """The strategy's holdings dict reflects the ledger-derived state.

        We use a stub TradingStrategy so we can capture the exact dict
        ``generate_signals`` is called with — that's the contract we
        care about, not what BuyAndHold does.
        """
        from datetime import date as date_type
        from decimal import Decimal

        from zebu.domain.value_objects.price_point import PricePoint

        user_id = uuid4()
        activation_repo = InMemoryStrategyActivationRepository()
        strategy_repo = InMemoryStrategyRepository()
        portfolio_repo = InMemoryPortfolioRepository()
        txn_repo = InMemoryTransactionRepository()
        market_data = InMemoryMarketDataAdapter()

        portfolio = _make_portfolio(user_id=user_id)
        await portfolio_repo.save(portfolio)
        await _seed_initial_deposit(
            txn_repo=txn_repo, portfolio_id=portfolio.id, amount="10000"
        )

        # Pre-existing BUY transaction so the portfolio has 5 AAPL shares.
        prior_buy = Transaction(
            id=uuid4(),
            portfolio_id=portfolio.id,
            transaction_type=TransactionType.BUY,
            timestamp=datetime.now(UTC) - timedelta(minutes=10),
            cash_change=Money(Decimal("-500"), "USD"),
            ticker=Ticker("AAPL"),
            quantity=__import__(
                "zebu.domain.value_objects.quantity", fromlist=["Quantity"]
            ).Quantity(Decimal("5")),
            price_per_share=Money(Decimal("100"), "USD"),
            notes="prior position",
        )
        await txn_repo.save(prior_buy)

        strategy = _make_strategy(user_id=user_id, tickers=["AAPL"])
        await strategy_repo.save(strategy)
        activation = _make_activation(
            user_id=user_id,
            strategy_id=strategy.id,
            portfolio_id=portfolio.id,
        )
        await activation_repo.save(activation)
        _seed_price(market_data, "AAPL", price="100.00")

        service = _build_service(
            activation_repo=activation_repo,
            strategy_repo=strategy_repo,
            portfolio_repo=portfolio_repo,
            transaction_repo=txn_repo,
            market_data=market_data,
        )

        captured: dict[str, dict[str, Decimal]] = {}

        class _CapturingStrategy:
            """Records the holdings dict the service hands it."""

            def generate_signals(
                self,
                current_date: date_type,
                price_map: dict[str, dict[date_type, PricePoint]],
                cash_balance: Decimal,
                holdings: dict[str, Decimal],
            ) -> list[object]:
                captured["holdings"] = dict(holdings)
                return []

        # Patch the strategy build path to swap in our capturing stub.
        service._build_trading_strategy = (  # type: ignore[method-assign]
            lambda strat: _CapturingStrategy()  # noqa: ARG005
        )

        await service.execute_one(activation.id)

        assert captured["holdings"] == {"AAPL": Decimal("5")}

    async def test_sell_signal_with_prior_holdings_executes(self) -> None:
        """SELL signals validate against the seeded position, not zero.

        We inject a stub strategy that emits a SELL signal for the
        existing AAPL position. Without holdings seeding, the trade
        factory would reject it as ``InsufficientShares`` (0 held vs
        5 requested). With seeding (via ``BacktestTransactionBuilder``)
        the SELL succeeds.
        """
        from datetime import date as date_type
        from decimal import Decimal

        from zebu.domain.value_objects.price_point import PricePoint
        from zebu.domain.value_objects.quantity import Quantity
        from zebu.domain.value_objects.trade_signal import (
            TradeAction,
            TradeSignal,
        )

        user_id = uuid4()
        activation_repo = InMemoryStrategyActivationRepository()
        strategy_repo = InMemoryStrategyRepository()
        portfolio_repo = InMemoryPortfolioRepository()
        txn_repo = InMemoryTransactionRepository()
        market_data = InMemoryMarketDataAdapter()

        portfolio = _make_portfolio(user_id=user_id)
        await portfolio_repo.save(portfolio)
        await _seed_initial_deposit(
            txn_repo=txn_repo, portfolio_id=portfolio.id, amount="10000"
        )
        prior_buy = Transaction(
            id=uuid4(),
            portfolio_id=portfolio.id,
            transaction_type=TransactionType.BUY,
            timestamp=datetime.now(UTC) - timedelta(minutes=10),
            cash_change=Money(Decimal("-500"), "USD"),
            ticker=Ticker("AAPL"),
            quantity=Quantity(Decimal("5")),
            price_per_share=Money(Decimal("100"), "USD"),
            notes="prior",
        )
        await txn_repo.save(prior_buy)

        strategy = _make_strategy(user_id=user_id, tickers=["AAPL"])
        await strategy_repo.save(strategy)
        activation = _make_activation(
            user_id=user_id,
            strategy_id=strategy.id,
            portfolio_id=portfolio.id,
        )
        await activation_repo.save(activation)
        _seed_price(market_data, "AAPL", price="110.00")

        service = _build_service(
            activation_repo=activation_repo,
            strategy_repo=strategy_repo,
            portfolio_repo=portfolio_repo,
            transaction_repo=txn_repo,
            market_data=market_data,
        )

        class _SellAllStub:
            def generate_signals(
                self,
                current_date: date_type,
                price_map: dict[str, dict[date_type, PricePoint]],
                cash_balance: Decimal,
                holdings: dict[str, Decimal],
            ) -> list[TradeSignal]:
                return [
                    TradeSignal(
                        action=TradeAction.SELL,
                        ticker=Ticker("AAPL"),
                        signal_date=current_date,
                        quantity=Quantity(holdings["AAPL"]),
                    )
                ]

        service._build_trading_strategy = (  # type: ignore[method-assign]
            lambda strat: _SellAllStub()  # noqa: ARG005
        )

        result = await service.execute_one(activation.id)
        assert result["succeeded"] is True
        assert result["trades"] == 1


# ---------------------------------------------------------------------------
# Boundary: pytest-asyncio mode
# ---------------------------------------------------------------------------


pytestmark = pytest.mark.asyncio
