"""BacktestExecutor - Orchestrates the full backtest simulation pipeline."""

import logging
import math
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import TypedDict
from uuid import UUID, uuid4

from zebu.application.commands.run_backtest import RunBacktestCommand
from zebu.application.ports.backtest_run_repository import BacktestRunRepository
from zebu.application.ports.portfolio_repository import PortfolioRepository
from zebu.application.ports.snapshot_repository import SnapshotRepository
from zebu.application.ports.strategy_repository import StrategyRepository
from zebu.application.ports.transaction_repository import TransactionRepository
from zebu.application.services.backtest_transaction_builder import (
    BacktestTransactionBuilder,
)
from zebu.application.services.historical_data_preparer import HistoricalDataPreparer
from zebu.application.services.snapshot_job import SnapshotJobService
from zebu.domain.entities.backtest_run import BacktestRun
from zebu.domain.entities.portfolio import Portfolio
from zebu.domain.entities.strategy import Strategy
from zebu.domain.entities.transaction import Transaction, TransactionType
from zebu.domain.exceptions import InvalidStrategyError
from zebu.domain.services.strategies.buy_and_hold import BuyAndHoldStrategy
from zebu.domain.services.strategies.dollar_cost_averaging import (
    DollarCostAveragingStrategy,
)
from zebu.domain.services.strategies.moving_average_crossover import (
    MovingAverageCrossoverStrategy,
)
from zebu.domain.services.strategies.protocol import TradingStrategy
from zebu.domain.value_objects.backtest_status import BacktestStatus
from zebu.domain.value_objects.money import Money
from zebu.domain.value_objects.portfolio_type import PortfolioType
from zebu.domain.value_objects.strategy_type import StrategyType

logger = logging.getLogger(__name__)


class _BacktestMetrics(TypedDict):
    total_return_pct: Decimal
    max_drawdown_pct: Decimal
    annualized_return_pct: Decimal
    total_trades: int


class BacktestExecutor:
    """Orchestrates the full backtest simulation pipeline.

    Executes backtests synchronously following a 6-phase pipeline:
      0. Setup: Create BACKTEST portfolio, deposit initial cash
      1. Pre-fetch: Retrieve all required historical price data
      2. Simulate: Loop over trading days, apply strategy signals
      3. Persist: Bulk-save all transactions
      4. Snapshot: Generate daily portfolio snapshots via backfill
      5. Metrics: Compute summary metrics and mark COMPLETED

    On any failure, the BacktestRun is saved with FAILED status and
    the error message.
    """

    def __init__(
        self,
        portfolio_repo: PortfolioRepository,
        transaction_repo: TransactionRepository,
        strategy_repo: StrategyRepository,
        backtest_run_repo: BacktestRunRepository,
        snapshot_service: SnapshotJobService,
        snapshot_repo: SnapshotRepository,
        data_preparer: HistoricalDataPreparer,
    ) -> None:
        """Initialize executor with all required dependencies.

        Args:
            portfolio_repo: Portfolio persistence
            transaction_repo: Transaction persistence
            strategy_repo: Strategy persistence
            backtest_run_repo: BacktestRun persistence
            snapshot_service: Service for generating portfolio snapshots
            snapshot_repo: Repository for querying snapshots during metric computation
            data_preparer: Service for pre-fetching historical price data
        """
        self._portfolio_repo = portfolio_repo
        self._transaction_repo = transaction_repo
        self._strategy_repo = strategy_repo
        self._backtest_run_repo = backtest_run_repo
        self._snapshot_service = snapshot_service
        self._snapshot_repo = snapshot_repo
        self._data_preparer = data_preparer

    async def execute(self, command: RunBacktestCommand) -> BacktestRun:
        """Run a complete backtest synchronously.

        Args:
            command: Backtest run parameters

        Returns:
            Completed (or failed) BacktestRun entity
        """
        now = datetime.now(UTC)
        portfolio_id = uuid4()
        backtest_run_id = uuid4()

        # Fetch the strategy
        strategy = await self._strategy_repo.get(command.strategy_id)
        if strategy is None:
            raise InvalidStrategyError(f"Strategy not found: {command.strategy_id}")

        # Build strategy snapshot
        strategy_snapshot: dict[str, object] = {
            "id": str(strategy.id),
            "name": strategy.name,
            "strategy_type": strategy.strategy_type.value,
            "tickers": strategy.tickers,
            "parameters": strategy.parameters,
        }

        # Create the initial RUNNING BacktestRun
        backtest_run = BacktestRun(
            id=backtest_run_id,
            user_id=command.user_id,
            strategy_id=command.strategy_id,
            portfolio_id=portfolio_id,
            strategy_snapshot=strategy_snapshot,
            backtest_name=command.backtest_name,
            start_date=command.start_date,
            end_date=command.end_date,
            initial_cash=command.initial_cash,
            status=BacktestStatus.RUNNING,
            created_at=now,
        )
        await self._backtest_run_repo.save(backtest_run)

        try:
            result = await self._run_pipeline(
                command=command,
                backtest_run=backtest_run,
                portfolio_id=portfolio_id,
                strategy=strategy,
                strategy_snapshot=strategy_snapshot,
            )
        except Exception as exc:
            logger.exception("Backtest %s failed: %s", backtest_run_id, exc)
            failed_run = BacktestRun(
                id=backtest_run_id,
                user_id=command.user_id,
                strategy_id=command.strategy_id,
                portfolio_id=portfolio_id,
                strategy_snapshot=strategy_snapshot,
                backtest_name=command.backtest_name,
                start_date=command.start_date,
                end_date=command.end_date,
                initial_cash=command.initial_cash,
                status=BacktestStatus.FAILED,
                created_at=now,
                completed_at=datetime.now(UTC),
                error_message=str(exc),
            )
            await self._backtest_run_repo.save(failed_run)
            return failed_run

        return result

    async def _run_pipeline(
        self,
        command: RunBacktestCommand,
        backtest_run: BacktestRun,
        portfolio_id: UUID,
        strategy: Strategy,
        strategy_snapshot: dict[str, object],
    ) -> BacktestRun:
        """Internal pipeline.

        Phases: setup → prefetch → simulate → persist → snapshot → metrics.

        Args:
            command: The original run command
            backtest_run: The initial RUNNING BacktestRun entity
            portfolio_id: UUID for the new backtest portfolio
            strategy: The loaded strategy entity
            strategy_snapshot: Serialized strategy at time of run

        Returns:
            COMPLETED BacktestRun with metrics
        """
        now_utc = backtest_run.created_at

        # ── Phase 0: Setup ────────────────────────────────────────────────────
        portfolio = Portfolio(
            id=portfolio_id,
            user_id=command.user_id,
            name=f"[Backtest] {command.backtest_name}",
            created_at=now_utc,
            portfolio_type=PortfolioType.BACKTEST,
        )
        await self._portfolio_repo.save(portfolio)

        initial_cash = Money(command.initial_cash, "USD")
        start_ts = datetime(
            command.start_date.year,
            command.start_date.month,
            command.start_date.day,
            0,
            0,
            0,
            tzinfo=UTC,
        )

        deposit = Transaction(
            id=uuid4(),
            portfolio_id=portfolio_id,
            transaction_type=TransactionType.DEPOSIT,
            timestamp=start_ts,
            cash_change=initial_cash,
            ticker=None,
            quantity=None,
            price_per_share=None,
            notes="Initial backtest deposit",
        )
        await self._transaction_repo.save(deposit)

        # ── Phase 1: Pre-fetch price data ─────────────────────────────────────
        trading_strategy = self._build_strategy(strategy)
        warm_up_days = 0
        if strategy.strategy_type == StrategyType.MOVING_AVERAGE_CROSSOVER:
            slow_window = int(strategy.parameters.get("slow_window", 50))
            warm_up_days = slow_window * 2

        price_map = await self._data_preparer.prepare(
            tickers=strategy.tickers,
            start_date=command.start_date,
            end_date=command.end_date,
            warm_up_days=warm_up_days,
        )

        # ── Phase 2: Simulate ─────────────────────────────────────────────────
        builder = BacktestTransactionBuilder(
            portfolio_id=portfolio_id,
            initial_cash=initial_cash,
        )

        current_date = command.start_date
        while current_date <= command.end_date:
            # Skip dates with no price data (weekends/holidays)
            has_data = any(
                current_date in price_map.get(t, {}) for t in strategy.tickers
            )
            if not has_data:
                current_date += timedelta(days=1)
                continue

            holdings_dec = {k: v.shares for k, v in builder.holdings.items()}

            signals = trading_strategy.generate_signals(
                current_date=current_date,
                price_map=price_map,
                cash_balance=builder.cash_balance.amount,
                holdings=holdings_dec,
            )

            trade_ts = datetime(
                current_date.year,
                current_date.month,
                current_date.day,
                12,
                0,
                0,
                tzinfo=UTC,
            )

            for signal in signals:
                ticker_prices = price_map.get(signal.ticker, {})
                price_point = ticker_prices.get(current_date)
                if price_point is None:
                    continue
                builder.apply_signal(
                    signal=signal,
                    price_per_share=price_point.price,
                    timestamp=trade_ts,
                )

            current_date += timedelta(days=1)

        # ── Phase 3: Persist transactions ─────────────────────────────────────
        for transaction in builder.transactions:
            await self._transaction_repo.save(transaction)

        # ── Phase 4: Generate snapshots ───────────────────────────────────────
        await self._snapshot_service.backfill_snapshots(
            portfolio_id=portfolio_id,
            start_date=command.start_date,
            end_date=command.end_date,
        )

        # ── Phase 5: Compute metrics ──────────────────────────────────────────
        metrics = await self._compute_metrics(
            portfolio_id=portfolio_id,
            initial_cash=command.initial_cash,
            start_date=command.start_date,
            end_date=command.end_date,
            total_trades=builder.count_trades(),
        )

        completed_run = BacktestRun(
            id=backtest_run.id,
            user_id=command.user_id,
            strategy_id=command.strategy_id,
            portfolio_id=portfolio_id,
            strategy_snapshot=strategy_snapshot,
            backtest_name=command.backtest_name,
            start_date=command.start_date,
            end_date=command.end_date,
            initial_cash=command.initial_cash,
            status=BacktestStatus.COMPLETED,
            created_at=backtest_run.created_at,
            completed_at=datetime.now(UTC),
            total_return_pct=metrics["total_return_pct"],
            max_drawdown_pct=metrics["max_drawdown_pct"],
            annualized_return_pct=metrics["annualized_return_pct"],
            total_trades=metrics["total_trades"],
        )
        await self._backtest_run_repo.save(completed_run)

        return completed_run

    def _build_strategy(self, strategy: Strategy) -> TradingStrategy:
        """Resolve the strategy entity to its TradingStrategy implementation.

        Args:
            strategy: The strategy domain entity

        Returns:
            TradingStrategy implementation

        Raises:
            InvalidStrategyError: If strategy type is not supported
        """
        if strategy.strategy_type == StrategyType.BUY_AND_HOLD:
            allocation = strategy.parameters.get("allocation", {})
            if not isinstance(allocation, dict):
                raise InvalidStrategyError(
                    "BUY_AND_HOLD strategy requires 'allocation' dict parameter"
                )
            return BuyAndHoldStrategy(
                tickers=strategy.tickers,
                allocation={k: float(v) for k, v in allocation.items()},
            )

        if strategy.strategy_type == StrategyType.DOLLAR_COST_AVERAGING:
            frequency_days = strategy.parameters.get("frequency_days")
            amount_per_period = strategy.parameters.get("amount_per_period")
            allocation = strategy.parameters.get("allocation", {})
            if not isinstance(frequency_days, int):
                raise InvalidStrategyError(
                    "DOLLAR_COST_AVERAGING requires integer 'frequency_days' parameter"
                )
            if amount_per_period is None:
                raise InvalidStrategyError(
                    "DOLLAR_COST_AVERAGING requires 'amount_per_period' parameter"
                )
            if not isinstance(allocation, dict):
                raise InvalidStrategyError(
                    "DOLLAR_COST_AVERAGING requires 'allocation' dict parameter"
                )
            return DollarCostAveragingStrategy(
                tickers=strategy.tickers,
                frequency_days=frequency_days,
                amount_per_period=Decimal(str(amount_per_period)),
                allocation={k: float(v) for k, v in allocation.items()},
            )

        if strategy.strategy_type == StrategyType.MOVING_AVERAGE_CROSSOVER:
            fast_window = strategy.parameters.get("fast_window")
            slow_window = strategy.parameters.get("slow_window")
            invest_fraction = strategy.parameters.get("invest_fraction")
            if not isinstance(fast_window, int) or not isinstance(slow_window, int):
                raise InvalidStrategyError(
                    "MOVING_AVERAGE_CROSSOVER requires integer 'fast_window' "
                    "and 'slow_window' parameters"
                )
            if invest_fraction is None:
                raise InvalidStrategyError(
                    "MOVING_AVERAGE_CROSSOVER requires 'invest_fraction' parameter"
                )
            return MovingAverageCrossoverStrategy(
                tickers=strategy.tickers,
                fast_window=fast_window,
                slow_window=slow_window,
                invest_fraction=float(invest_fraction),
            )

        raise InvalidStrategyError(
            f"Strategy type not supported: {strategy.strategy_type.value}"
        )

    async def _compute_metrics(
        self,
        portfolio_id: UUID,
        initial_cash: Decimal,
        start_date: date,
        end_date: date,
        total_trades: int,
    ) -> _BacktestMetrics:
        """Compute summary performance metrics from snapshots.

        Args:
            portfolio_id: ID of the backtest portfolio
            initial_cash: Starting cash
            start_date: Simulation start
            end_date: Simulation end
            total_trades: Number of executed trades

        Returns:
            Dict with total_return_pct, max_drawdown_pct,
            annualized_return_pct, total_trades
        """
        # Access snapshot repo directly (injected dependency)
        snapshots = await self._snapshot_repo.get_range(
            portfolio_id=portfolio_id,
            start_date=start_date,
            end_date=end_date,
        )

        if not snapshots:
            return {
                "total_return_pct": Decimal("0"),
                "max_drawdown_pct": Decimal("0"),
                "annualized_return_pct": Decimal("0"),
                "total_trades": total_trades,
            }

        # Snapshots are already sorted ascending by get_range
        final_value = snapshots[-1].total_value

        # Total return %
        if initial_cash > Decimal("0"):
            total_return_pct = (
                (final_value - initial_cash) / initial_cash * Decimal("100")
            )
        else:
            total_return_pct = Decimal("0")

        # Max drawdown %
        peak = Decimal("0")
        max_drawdown_pct = Decimal("0")
        for snap in snapshots:
            if snap.total_value > peak:
                peak = snap.total_value
            if peak > Decimal("0"):
                drawdown = (peak - snap.total_value) / peak * Decimal("100")
                if drawdown > max_drawdown_pct:
                    max_drawdown_pct = drawdown

        # Annualized return %
        days = (end_date - start_date).days
        if days > 0 and initial_cash > Decimal("0") and final_value > Decimal("0"):
            try:
                total_return_ratio = float(final_value) / float(initial_cash)
                exponent = 365.0 / days
                annualized_factor = math.pow(total_return_ratio, exponent) - 1.0
                annualized_return_pct = Decimal(str(annualized_factor * 100))
            except (ValueError, OverflowError):
                annualized_return_pct = Decimal("0")
        else:
            annualized_return_pct = Decimal("0")

        return {
            "total_return_pct": total_return_pct.quantize(Decimal("0.0001")),
            "max_drawdown_pct": max_drawdown_pct.quantize(Decimal("0.0001")),
            "annualized_return_pct": annualized_return_pct.quantize(Decimal("0.0001")),
            "total_trades": total_trades,
        }
