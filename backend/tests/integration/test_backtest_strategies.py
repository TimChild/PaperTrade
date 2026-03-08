"""Integration tests for the BacktestExecutor pipeline with all strategy types.

These tests exercise the full simulation pipeline end-to-end using in-memory
repositories and a mock market data adapter to avoid external dependencies.
"""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from zebu.adapters.outbound.market_data.in_memory_adapter import (
    InMemoryMarketDataAdapter,
)
from zebu.application.commands.run_backtest import RunBacktestCommand
from zebu.application.dtos.price_point import PricePoint
from zebu.application.ports.in_memory_backtest_run_repository import (
    InMemoryBacktestRunRepository,
)
from zebu.application.ports.in_memory_portfolio_repository import (
    InMemoryPortfolioRepository,
)
from zebu.application.ports.in_memory_snapshot_repository import (
    InMemorySnapshotRepository,
)
from zebu.application.ports.in_memory_strategy_repository import (
    InMemoryStrategyRepository,
)
from zebu.application.ports.in_memory_transaction_repository import (
    InMemoryTransactionRepository,
)
from zebu.application.services.backtest_executor import BacktestExecutor
from zebu.application.services.historical_data_preparer import HistoricalDataPreparer
from zebu.application.services.snapshot_job import SnapshotJobService
from zebu.domain.entities.strategy import Strategy
from zebu.domain.entities.transaction import TransactionType
from zebu.domain.value_objects.backtest_status import BacktestStatus
from zebu.domain.value_objects.money import Money
from zebu.domain.value_objects.portfolio_type import PortfolioType
from zebu.domain.value_objects.strategy_type import StrategyType
from zebu.domain.value_objects.ticker import Ticker


def _seed_daily_prices(
    adapter: InMemoryMarketDataAdapter,
    ticker: str,
    start: date,
    end: date,
    price: Decimal = Decimal("100.00"),
) -> None:
    """Seed constant daily prices for a ticker over a date range."""
    current = start
    while current <= end:
        ts = datetime(current.year, current.month, current.day, 12, 0, 0, tzinfo=UTC)
        adapter.seed_price(
            PricePoint(
                ticker=Ticker(ticker),
                price=Money(price, "USD"),
                timestamp=ts,
                source="database",
                interval="1day",
            )
        )
        current += timedelta(days=1)


def _seed_price_on_date(
    adapter: InMemoryMarketDataAdapter,
    ticker: str,
    d: date,
    price: Decimal,
) -> None:
    """Seed a single price point for a ticker on a specific date."""
    ts = datetime(d.year, d.month, d.day, 12, 0, 0, tzinfo=UTC)
    adapter.seed_price(
        PricePoint(
            ticker=Ticker(ticker),
            price=Money(price, "USD"),
            timestamp=ts,
            source="database",
            interval="1day",
        )
    )


def _build_executor(
    *,
    portfolio_repo: InMemoryPortfolioRepository,
    transaction_repo: InMemoryTransactionRepository,
    strategy_repo: InMemoryStrategyRepository,
    backtest_run_repo: InMemoryBacktestRunRepository,
    snapshot_repo: InMemorySnapshotRepository,
    market_data: InMemoryMarketDataAdapter,
) -> BacktestExecutor:
    """Assemble a BacktestExecutor from in-memory dependencies."""
    snapshot_service = SnapshotJobService(
        portfolio_repo=portfolio_repo,
        transaction_repo=transaction_repo,
        snapshot_repo=snapshot_repo,
        market_data=market_data,
    )
    data_preparer = HistoricalDataPreparer(market_data=market_data)

    return BacktestExecutor(
        portfolio_repo=portfolio_repo,
        transaction_repo=transaction_repo,
        strategy_repo=strategy_repo,
        backtest_run_repo=backtest_run_repo,
        snapshot_service=snapshot_service,
        snapshot_repo=snapshot_repo,
        data_preparer=data_preparer,
    )


class TestBuyAndHoldIntegration:
    """Integration tests for the Buy & Hold strategy pipeline."""

    async def test_full_pipeline_completes_with_metrics(self) -> None:
        """Full Buy & Hold pipeline completes with metrics and transactions."""
        user_id = uuid4()
        start = date(2024, 1, 2)
        end = date(2024, 1, 10)

        adapter = InMemoryMarketDataAdapter()
        _seed_daily_prices(adapter, "AAPL", start, end, Decimal("150.00"))

        strategy = Strategy(
            id=uuid4(),
            user_id=user_id,
            name="Buy and Hold Test",
            strategy_type=StrategyType.BUY_AND_HOLD,
            tickers=["AAPL"],
            parameters={"allocation": {"AAPL": 1.0}},
            created_at=datetime.now(UTC),
        )

        portfolio_repo = InMemoryPortfolioRepository()
        transaction_repo = InMemoryTransactionRepository()
        strategy_repo = InMemoryStrategyRepository()
        backtest_run_repo = InMemoryBacktestRunRepository()
        snapshot_repo = InMemorySnapshotRepository()

        await strategy_repo.save(strategy)

        executor = _build_executor(
            portfolio_repo=portfolio_repo,
            transaction_repo=transaction_repo,
            strategy_repo=strategy_repo,
            backtest_run_repo=backtest_run_repo,
            snapshot_repo=snapshot_repo,
            market_data=adapter,
        )

        command = RunBacktestCommand(
            user_id=user_id,
            strategy_id=strategy.id,
            backtest_name="Buy and Hold Integration",
            start_date=start,
            end_date=end,
            initial_cash=Decimal("10000.00"),
        )

        result = await executor.execute(command)

        # Status should be COMPLETED
        assert result.status == BacktestStatus.COMPLETED
        assert result.completed_at is not None

        # Metrics should be computed
        assert result.total_return_pct is not None
        assert result.max_drawdown_pct is not None
        assert result.annualized_return_pct is not None
        assert result.total_trades is not None
        assert result.total_trades >= 1

        # Portfolio should exist with BACKTEST type
        portfolio = await portfolio_repo.get(result.portfolio_id)
        assert portfolio is not None
        assert portfolio.portfolio_type == PortfolioType.BACKTEST

        # At least one BUY transaction should be created
        transactions = await transaction_repo.get_by_portfolio(result.portfolio_id)
        assert len(transactions) >= 1
        buy_txns = [
            t for t in transactions if t.transaction_type == TransactionType.BUY
        ]
        assert len(buy_txns) >= 1


class TestDCAIntegration:
    """Integration tests for the Dollar Cost Averaging strategy pipeline."""

    async def test_full_pipeline_with_periodic_purchases(self) -> None:
        """Full DCA pipeline completes with multiple periodic purchases."""
        user_id = uuid4()
        # Use 20 days so at least 2 purchases occur (frequency_days=7)
        start = date(2024, 1, 2)
        end = date(2024, 1, 22)

        adapter = InMemoryMarketDataAdapter()
        _seed_daily_prices(adapter, "MSFT", start, end, Decimal("300.00"))

        strategy = Strategy(
            id=uuid4(),
            user_id=user_id,
            name="DCA Test",
            strategy_type=StrategyType.DOLLAR_COST_AVERAGING,
            tickers=["MSFT"],
            parameters={
                "frequency_days": 7,
                "amount_per_period": Decimal("1000"),
                "allocation": {"MSFT": 1.0},
            },
            created_at=datetime.now(UTC),
        )

        portfolio_repo = InMemoryPortfolioRepository()
        transaction_repo = InMemoryTransactionRepository()
        strategy_repo = InMemoryStrategyRepository()
        backtest_run_repo = InMemoryBacktestRunRepository()
        snapshot_repo = InMemorySnapshotRepository()

        await strategy_repo.save(strategy)

        executor = _build_executor(
            portfolio_repo=portfolio_repo,
            transaction_repo=transaction_repo,
            strategy_repo=strategy_repo,
            backtest_run_repo=backtest_run_repo,
            snapshot_repo=snapshot_repo,
            market_data=adapter,
        )

        command = RunBacktestCommand(
            user_id=user_id,
            strategy_id=strategy.id,
            backtest_name="DCA Integration",
            start_date=start,
            end_date=end,
            initial_cash=Decimal("10000.00"),
        )

        result = await executor.execute(command)

        # Status should be COMPLETED
        assert result.status == BacktestStatus.COMPLETED
        assert result.completed_at is not None

        # Metrics should be computed
        assert result.total_return_pct is not None
        assert result.max_drawdown_pct is not None
        assert result.total_trades is not None

        # Portfolio should exist with BACKTEST type
        portfolio = await portfolio_repo.get(result.portfolio_id)
        assert portfolio is not None
        assert portfolio.portfolio_type == PortfolioType.BACKTEST

        # Multiple purchases should have occurred over the 20-day window
        transactions = await transaction_repo.get_by_portfolio(result.portfolio_id)
        buy_txns = [
            t for t in transactions if t.transaction_type == TransactionType.BUY
        ]
        assert len(buy_txns) >= 2


class TestMovingAverageCrossoverIntegration:
    """Integration tests for the Moving Average Crossover strategy pipeline."""

    async def test_full_pipeline_with_crossover_signals(self) -> None:
        """Full MA Crossover pipeline with golden cross BUY and death cross SELL.

        Price sequence designed to trigger both a golden cross and a death cross:
        - Days 1-5 (Jan 2–6):  price = 100  (flat baseline)
        - Day  6   (Jan 7):    price = 200  (spike → golden cross → BUY)
        - Days 7-11 (Jan 8–12): price = 200  (flat at new level)
        - Day 12  (Jan 13):    price = 10   (crash → death cross → SELL)

        With fast_window=3 and slow_window=5:
          Golden cross on Jan 7:
            fast_sma = (100+100+200)/3 ≈ 133.3 > slow_sma = (100*4+200)/5 = 120
            prev_fast (100) <= prev_slow (100) → crossover confirmed → BUY
          Death cross on Jan 13:
            fast_sma = (200+200+10)/3 ≈ 136.7 < slow_sma = (200*4+10)/5 = 162
            prev_fast (200) >= prev_slow (200) → crossover confirmed → SELL
        """
        user_id = uuid4()
        ticker = "GOOGL"
        start = date(2024, 1, 2)
        end = date(2024, 1, 13)

        adapter = InMemoryMarketDataAdapter()

        # Seed price sequence to trigger golden cross then death cross
        flat_low_start = date(2024, 1, 2)
        flat_low_end = date(2024, 1, 6)
        _seed_daily_prices(
            adapter, ticker, flat_low_start, flat_low_end, Decimal("100.00")
        )

        # Spike on Jan 7 → golden cross
        _seed_price_on_date(adapter, ticker, date(2024, 1, 7), Decimal("200.00"))

        # Flat at high Jan 8–12
        _seed_daily_prices(
            adapter, ticker, date(2024, 1, 8), date(2024, 1, 12), Decimal("200.00")
        )

        # Crash on Jan 13 → death cross
        _seed_price_on_date(adapter, ticker, date(2024, 1, 13), Decimal("10.00"))

        strategy = Strategy(
            id=uuid4(),
            user_id=user_id,
            name="MA Crossover Test",
            strategy_type=StrategyType.MOVING_AVERAGE_CROSSOVER,
            tickers=[ticker],
            parameters={
                "fast_window": 3,
                "slow_window": 5,
                "invest_fraction": 1.0,
            },
            created_at=datetime.now(UTC),
        )

        portfolio_repo = InMemoryPortfolioRepository()
        transaction_repo = InMemoryTransactionRepository()
        strategy_repo = InMemoryStrategyRepository()
        backtest_run_repo = InMemoryBacktestRunRepository()
        snapshot_repo = InMemorySnapshotRepository()

        await strategy_repo.save(strategy)

        executor = _build_executor(
            portfolio_repo=portfolio_repo,
            transaction_repo=transaction_repo,
            strategy_repo=strategy_repo,
            backtest_run_repo=backtest_run_repo,
            snapshot_repo=snapshot_repo,
            market_data=adapter,
        )

        command = RunBacktestCommand(
            user_id=user_id,
            strategy_id=strategy.id,
            backtest_name="MA Crossover Integration",
            start_date=start,
            end_date=end,
            initial_cash=Decimal("10000.00"),
        )

        result = await executor.execute(command)

        # Status should be COMPLETED
        assert result.status == BacktestStatus.COMPLETED
        assert result.completed_at is not None

        # Metrics should be computed
        assert result.total_return_pct is not None
        assert result.max_drawdown_pct is not None
        assert result.total_trades is not None

        # Portfolio should exist with BACKTEST type
        portfolio = await portfolio_repo.get(result.portfolio_id)
        assert portfolio is not None
        assert portfolio.portfolio_type == PortfolioType.BACKTEST

        # Both BUY and SELL transactions should have been generated
        transactions = await transaction_repo.get_by_portfolio(result.portfolio_id)
        transaction_types = {t.transaction_type for t in transactions}
        assert TransactionType.BUY in transaction_types
        assert TransactionType.SELL in transaction_types
