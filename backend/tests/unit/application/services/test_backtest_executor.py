"""Tests for BacktestExecutor."""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

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
from zebu.domain.value_objects.backtest_status import BacktestStatus
from zebu.domain.value_objects.money import Money
from zebu.domain.value_objects.strategy_type import StrategyType
from zebu.domain.value_objects.ticker import Ticker


def _make_strategy(user_id, tickers=None, allocation=None):
    tickers = tickers or ["AAPL"]
    allocation = allocation or {"AAPL": 1.0}
    return Strategy(
        id=uuid4(),
        user_id=user_id,
        name="Test Strategy",
        strategy_type=StrategyType.BUY_AND_HOLD,
        tickers=tickers,
        parameters={"allocation": allocation},
        created_at=datetime.now(UTC),
    )


def _seed_daily_prices(
    adapter: InMemoryMarketDataAdapter,
    ticker: str,
    start: date,
    end: date,
    price: Decimal = Decimal("100.00"),
) -> None:
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


def _build_executor(
    strategy_repo,
    backtest_run_repo,
    portfolio_repo=None,
    transaction_repo=None,
    snapshot_repo=None,
    market_data=None,
):
    portfolio_repo = portfolio_repo or InMemoryPortfolioRepository()
    transaction_repo = transaction_repo or InMemoryTransactionRepository()
    snapshot_repo = snapshot_repo or InMemorySnapshotRepository()
    market_data = market_data or InMemoryMarketDataAdapter()

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
        data_preparer=data_preparer,
    )


class TestBacktestExecutor:
    """Tests for BacktestExecutor.execute()."""

    async def test_completed_backtest_has_completed_status(self) -> None:
        """Successful backtest ends with COMPLETED status."""
        user_id = uuid4()
        strategy_repo = InMemoryStrategyRepository()
        backtest_run_repo = InMemoryBacktestRunRepository()
        adapter = InMemoryMarketDataAdapter()

        start = date(2024, 1, 2)
        end = date(2024, 1, 5)
        _seed_daily_prices(adapter, "AAPL", start, end)

        strategy = _make_strategy(user_id)
        await strategy_repo.save(strategy)

        executor = _build_executor(
            strategy_repo=strategy_repo,
            backtest_run_repo=backtest_run_repo,
            market_data=adapter,
        )

        command = RunBacktestCommand(
            user_id=user_id,
            strategy_id=strategy.id,
            backtest_name="Test Backtest",
            start_date=start,
            end_date=end,
            initial_cash=Decimal("10000"),
        )

        result = await executor.execute(command)

        assert result.status == BacktestStatus.COMPLETED
        assert result.total_trades is not None
        assert result.completed_at is not None

    async def test_missing_strategy_raises_error(self) -> None:
        """Backtest with missing strategy raises InvalidStrategyError."""
        from zebu.domain.exceptions import InvalidStrategyError

        user_id = uuid4()
        strategy_repo = InMemoryStrategyRepository()
        backtest_run_repo = InMemoryBacktestRunRepository()

        executor = _build_executor(
            strategy_repo=strategy_repo,
            backtest_run_repo=backtest_run_repo,
        )

        command = RunBacktestCommand(
            user_id=user_id,
            strategy_id=uuid4(),  # non-existent
            backtest_name="Test",
            start_date=date(2024, 1, 2),
            end_date=date(2024, 1, 5),
            initial_cash=Decimal("10000"),
        )

        with pytest.raises(InvalidStrategyError):
            await executor.execute(command)

    async def test_backtest_creates_portfolio(self) -> None:
        """Backtest creates a BACKTEST-type portfolio."""
        user_id = uuid4()
        strategy_repo = InMemoryStrategyRepository()
        backtest_run_repo = InMemoryBacktestRunRepository()
        portfolio_repo = InMemoryPortfolioRepository()
        adapter = InMemoryMarketDataAdapter()

        start = date(2024, 1, 2)
        end = date(2024, 1, 3)
        _seed_daily_prices(adapter, "AAPL", start, end)

        strategy = _make_strategy(user_id)
        await strategy_repo.save(strategy)

        executor = _build_executor(
            strategy_repo=strategy_repo,
            backtest_run_repo=backtest_run_repo,
            portfolio_repo=portfolio_repo,
            market_data=adapter,
        )

        command = RunBacktestCommand(
            user_id=user_id,
            strategy_id=strategy.id,
            backtest_name="Test",
            start_date=start,
            end_date=end,
            initial_cash=Decimal("5000"),
        )

        result = await executor.execute(command)

        assert result.status == BacktestStatus.COMPLETED
        portfolio = await portfolio_repo.get(result.portfolio_id)
        assert portfolio is not None
        from zebu.domain.value_objects.portfolio_type import PortfolioType

        assert portfolio.portfolio_type == PortfolioType.BACKTEST

    async def test_buy_and_hold_executes_trade_on_day1(self) -> None:
        """Buy and hold strategy executes at least one trade."""
        user_id = uuid4()
        strategy_repo = InMemoryStrategyRepository()
        backtest_run_repo = InMemoryBacktestRunRepository()
        transaction_repo = InMemoryTransactionRepository()
        adapter = InMemoryMarketDataAdapter()

        start = date(2024, 1, 2)
        end = date(2024, 1, 5)
        _seed_daily_prices(adapter, "AAPL", start, end)

        strategy = _make_strategy(user_id)
        await strategy_repo.save(strategy)

        executor = _build_executor(
            strategy_repo=strategy_repo,
            backtest_run_repo=backtest_run_repo,
            transaction_repo=transaction_repo,
            market_data=adapter,
        )

        command = RunBacktestCommand(
            user_id=user_id,
            strategy_id=strategy.id,
            backtest_name="Test",
            start_date=start,
            end_date=end,
            initial_cash=Decimal("10000"),
        )

        result = await executor.execute(command)

        assert result.status == BacktestStatus.COMPLETED
        assert result.total_trades is not None
        assert result.total_trades >= 1
