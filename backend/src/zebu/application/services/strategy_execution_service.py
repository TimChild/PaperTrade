"""StrategyExecutionService - Executes ACTIVE strategies in single-day live mode.

Phase C1.2 of the agent-platform proposal. Mirrors :class:`BacktestExecutor`
in shape but only ever runs *one* trading day per call: today's prices are
fetched, signals are generated, and any resulting trades are persisted
through the same ``trade_factory`` path the backtest uses.

The service is the live-mode counterpart to
:class:`zebu.application.services.backtest_executor.BacktestExecutor`. Both
consume :class:`TradingStrategy` implementations and produce
:class:`Transaction` rows; the difference is that backtests iterate over a
historical window with a pre-fetched price map while live execution
materializes a single-day price map from the current
:class:`MarketDataPort`.

Error handling:

* Per-activation failures are caught and stored on the activation as
  ``status=ERROR`` + ``last_error`` so one broken strategy never blocks the
  others. The scheduler treats this as an alarm channel rather than a
  hard failure path.
* Configuration / repository errors at the *batch* level (e.g. the
  activation list itself can't be loaded) are propagated so the scheduler
  job logs them and fails-loud — this is correct behaviour for an outage
  in a shared dependency.
"""

import logging
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import TypedDict
from uuid import UUID

from zebu.application.exceptions import (
    MarketDataUnavailableError,
    TickerNotFoundError,
)
from zebu.application.ports.market_data_port import MarketDataPort
from zebu.application.ports.portfolio_repository import PortfolioRepository
from zebu.application.ports.strategy_activation_repository import (
    StrategyActivationRepository,
)
from zebu.application.ports.strategy_repository import StrategyRepository
from zebu.application.ports.transaction_repository import TransactionRepository
from zebu.application.services.backtest_transaction_builder import (
    BacktestTransactionBuilder,
)
from zebu.domain.entities.portfolio import Portfolio
from zebu.domain.entities.strategy import Strategy
from zebu.domain.entities.strategy_activation import StrategyActivation
from zebu.domain.entities.transaction import Transaction
from zebu.domain.services.portfolio_calculator import PortfolioCalculator
from zebu.domain.services.strategies.buy_and_hold import BuyAndHoldStrategy
from zebu.domain.services.strategies.dollar_cost_averaging import (
    DollarCostAveragingStrategy,
)
from zebu.domain.services.strategies.moving_average_crossover import (
    MovingAverageCrossoverStrategy,
)
from zebu.domain.services.strategies.protocol import TradingStrategy
from zebu.domain.value_objects.activation_status import ActivationStatus
from zebu.domain.value_objects.allocation import Allocation
from zebu.domain.value_objects.money import Money
from zebu.domain.value_objects.price_point import PricePoint
from zebu.domain.value_objects.quantity import Quantity
from zebu.domain.value_objects.strategy_parameters import (
    BuyAndHoldParameters,
    DcaParameters,
    MaCrossoverParameters,
)
from zebu.domain.value_objects.ticker import Ticker
from zebu.domain.value_objects.trade_signal import TradeSignal

logger = logging.getLogger(__name__)


class ExecutionSummary(TypedDict):
    """Result envelope returned by ``execute_active_strategies``.

    Attributes:
        processed: Number of activations dispatched (regardless of outcome).
        succeeded: Activations whose execution returned without raising.
        failed: Activations whose execution recorded an ERROR status.
        trades: Total number of transactions persisted across all activations.
    """

    processed: int
    succeeded: int
    failed: int
    trades: int


class ExecutionResult(TypedDict):
    """Result envelope returned by ``execute_one``.

    Attributes:
        activation_id: The activation that was processed.
        succeeded: ``True`` if execution completed without raising.
        trades: Number of transactions that were persisted on this run.
        error: Error message captured when ``succeeded`` is False.
    """

    activation_id: UUID
    succeeded: bool
    trades: int
    error: str | None


class StrategyExecutionService:
    """Live-mode strategy executor.

    Loads each ``ACTIVE`` :class:`StrategyActivation`, fetches today's
    prices for the strategy's tickers, calls
    :meth:`TradingStrategy.generate_signals`, and persists the resulting
    transactions. Mirrors the backtest path so the *same* domain
    code (``TradingStrategy``, ``trade_factory``, ``BacktestTransactionBuilder``)
    decides what to trade in both modes.

    Per-activation isolation: every activation is wrapped in its own
    try/except. A signal that violates trade invariants (insufficient
    funds, missing portfolio, etc.) flips that one activation to ``ERROR``
    status and the loop continues with the next one. The scheduler reads
    the resulting ``ExecutionSummary`` to decide what to log/alarm on.

    The service is testable end-to-end with in-memory adapters — no
    scheduler / DB / network is required for unit tests.
    """

    def __init__(
        self,
        *,
        activation_repo: StrategyActivationRepository,
        strategy_repo: StrategyRepository,
        portfolio_repo: PortfolioRepository,
        transaction_repo: TransactionRepository,
        market_data: MarketDataPort,
    ) -> None:
        """Initialize service with required dependencies.

        Args:
            activation_repo: Persistence for ``StrategyActivation`` (read +
                write — successful and failed runs both mutate it).
            strategy_repo: Read-only resolution from activation to strategy.
            portfolio_repo: Read-only resolution from activation to portfolio.
            transaction_repo: Append-only sink for the produced trades.
            market_data: Source of "today's price" for each strategy ticker.
        """
        self._activation_repo = activation_repo
        self._strategy_repo = strategy_repo
        self._portfolio_repo = portfolio_repo
        self._transaction_repo = transaction_repo
        self._market_data = market_data

    async def execute_active_strategies(self) -> ExecutionSummary:
        """Run one cycle for every ``ACTIVE`` activation.

        Each activation is processed independently. Any exception inside
        a single activation is captured on that activation's record (status
        flips to ``ERROR``) and the loop moves on. The summary returned
        here is what the scheduler logs.

        Returns:
            ``ExecutionSummary`` with counts of processed / succeeded /
            failed activations and total trades persisted.
        """
        active = await self._activation_repo.list_active()
        logger.info(
            "Strategy execution cycle starting",
            extra={"active_activations": len(active)},
        )

        succeeded = 0
        failed = 0
        trades = 0

        for activation in active:
            result = await self._safe_execute(activation)
            trades += result["trades"]
            if result["succeeded"]:
                succeeded += 1
            else:
                failed += 1

        summary: ExecutionSummary = {
            "processed": len(active),
            "succeeded": succeeded,
            "failed": failed,
            "trades": trades,
        }
        logger.info("Strategy execution cycle complete", extra=dict(summary))
        return summary

    async def execute_one(self, activation_id: UUID) -> ExecutionResult:
        """Run a single activation, by ID. Used by the manual ``run-now`` API.

        Args:
            activation_id: Identifier of the activation to execute.

        Returns:
            ``ExecutionResult`` describing whether the run succeeded and
            how many trades it produced. ``succeeded == False`` carries a
            non-empty ``error`` string. A missing activation is reported
            as a failure, not raised — callers should pre-check existence
            if they need a 404 distinction (the API layer does this).
        """
        activation = await self._activation_repo.get(activation_id)
        if activation is None:
            return {
                "activation_id": activation_id,
                "succeeded": False,
                "trades": 0,
                "error": f"Activation not found: {activation_id}",
            }
        return await self._safe_execute(activation)

    async def _safe_execute(self, activation: StrategyActivation) -> ExecutionResult:
        """Run a single activation, capturing any exception on the entity.

        On error, the activation is persisted with ``status=ERROR`` and
        ``last_error`` set. Successful runs leave the status as
        ``ACTIVE`` and bump ``last_executed_at``.

        Args:
            activation: The activation to run.

        Returns:
            Per-activation ``ExecutionResult``.
        """
        try:
            trades = await self._run_activation(activation)
            await self._mark_success(activation)
        except Exception as exc:
            # ``Exception`` is intentionally broad: a single misbehaving
            # strategy must never crash the scheduler cycle. The error is
            # logged with a stack trace and persisted on the activation.
            logger.exception(
                "Strategy activation execution failed",
                extra={
                    "activation_id": str(activation.id),
                    "strategy_id": str(activation.strategy_id),
                    "portfolio_id": str(activation.portfolio_id),
                },
            )
            await self._mark_error(activation, str(exc))
            return {
                "activation_id": activation.id,
                "succeeded": False,
                "trades": 0,
                "error": str(exc),
            }

        return {
            "activation_id": activation.id,
            "succeeded": True,
            "trades": trades,
            "error": None,
        }

    async def _run_activation(self, activation: StrategyActivation) -> int:
        """Resolve, fetch prices, generate signals, persist transactions.

        Mirrors the backtest pipeline but for a single calendar day:

        1. Load strategy + portfolio.
        2. Build the ``TradingStrategy`` instance from typed parameters.
        3. Compute today's cash + holdings from the transaction ledger.
        4. Fetch current prices for the strategy's tickers.
        5. Drive the strategy through one ``generate_signals`` call.
        6. Apply each signal via ``BacktestTransactionBuilder`` (re-uses
           the trade-factory and quantity-resolution rules already proven
           in backtest).
        7. Bulk-persist the resulting transactions.

        Returns:
            Number of trades persisted.

        Raises:
            ValueError: When the strategy or portfolio referenced by the
                activation no longer exists (caller wraps this in
                ``_safe_execute`` so it surfaces as ``status=ERROR``).
        """
        strategy = await self._strategy_repo.get(activation.strategy_id)
        if strategy is None:
            raise ValueError(f"Strategy not found: {activation.strategy_id}")

        portfolio = await self._portfolio_repo.get(activation.portfolio_id)
        if portfolio is None:
            raise ValueError(f"Portfolio not found: {activation.portfolio_id}")

        trading_strategy = self._build_trading_strategy(strategy)

        # Reconstruct portfolio state from the ledger. This is the same
        # source-of-truth approach the rest of the app uses (cash and
        # holdings are derived, never stored).
        transactions = await self._transaction_repo.get_by_portfolio(portfolio.id)
        cash_balance = PortfolioCalculator.calculate_cash_balance(transactions)
        holdings_list = PortfolioCalculator.calculate_holdings(transactions)
        holdings_decimal: dict[str, Decimal] = {
            holding.ticker.symbol: holding.quantity.shares for holding in holdings_list
        }

        execution_time = datetime.now(UTC)
        today = execution_time.date()

        # Fetch today's prices for every ticker. A missing or unavailable
        # ticker is logged but doesn't kill the cycle — the strategy will
        # simply skip signals for that ticker because it won't appear in
        # the price map.
        price_map = await self._fetch_price_map(strategy.tickers, today)

        signals: list[TradeSignal] = trading_strategy.generate_signals(
            current_date=today,
            price_map=price_map,
            cash_balance=cash_balance.amount,
            holdings=holdings_decimal,
        )
        if not signals:
            logger.info(
                "Strategy generated no signals — no trades to execute",
                extra={
                    "activation_id": str(activation.id),
                    "strategy_id": str(strategy.id),
                },
            )
            return 0

        trades = self._apply_signals(
            signals=signals,
            price_map=price_map,
            today=today,
            execution_time=execution_time,
            portfolio=portfolio,
            cash_balance=cash_balance,
            holdings_decimal=holdings_decimal,
        )

        if trades:
            await self._transaction_repo.save_all(trades)

        return len(trades)

    def _build_trading_strategy(self, strategy: Strategy) -> TradingStrategy:
        """Resolve a domain :class:`Strategy` to its ``TradingStrategy`` impl.

        Mirrors :meth:`BacktestExecutor._build_strategy` — kept duplicated
        rather than shared to avoid an upward dependency from
        ``BacktestExecutor`` (an application service) to a sibling
        application service. If a third call site appears, lift this into
        a free function on the ``strategies`` package.

        Args:
            strategy: Persisted strategy entity.

        Returns:
            The matching ``TradingStrategy`` implementation.

        Raises:
            ValueError: Defensive — the strategy parameters' concrete
                type doesn't match a known TradingStrategy. The
                ``Strategy`` constructor enforces this so it's only
                hit via an invariant breach.
        """
        params = strategy.parameters
        match params:
            case BuyAndHoldParameters():
                return BuyAndHoldStrategy(
                    tickers=strategy.tickers,
                    allocation=Allocation.from_raw(dict(params.allocation)),
                )
            case DcaParameters():
                return DollarCostAveragingStrategy(
                    tickers=strategy.tickers,
                    frequency_days=params.frequency_days,
                    amount_per_period=params.amount_per_period,
                    allocation=Allocation.from_raw(dict(params.allocation)),
                )
            case MaCrossoverParameters():
                return MovingAverageCrossoverStrategy(
                    tickers=strategy.tickers,
                    fast_window=params.fast_window,
                    slow_window=params.slow_window,
                    invest_fraction=float(params.invest_fraction),
                )

    async def _fetch_price_map(
        self, tickers: list[str], today: date
    ) -> dict[str, dict[date, PricePoint]]:
        """Fetch a single-day price map for the strategy's tickers.

        Returns the same shape ``HistoricalDataPreparer`` produces in
        backtest mode — ``{ticker_symbol: {date: PricePoint}}`` — but
        only ever populated for ``today``. Tickers that fail to resolve
        are silently dropped from the map; the strategy's
        ``generate_signals`` ignores tickers without price data.

        Args:
            tickers: Strategy ticker list.
            today: The trading day to anchor each ``PricePoint`` to.

        Returns:
            Price map keyed by ticker symbol, value is a single-entry
            dict mapping ``today`` to its ``PricePoint``.
        """
        price_map: dict[str, dict[date, PricePoint]] = {}
        for symbol in tickers:
            try:
                ticker = Ticker(symbol)
                price_point = await self._market_data.get_current_price(ticker)
            except (TickerNotFoundError, MarketDataUnavailableError) as exc:
                logger.warning(
                    "No current price available for ticker — skipping",
                    extra={"ticker": symbol, "reason": str(exc)},
                )
                continue
            price_map[symbol] = {today: price_point}
        return price_map

    def _apply_signals(
        self,
        *,
        signals: list[TradeSignal],
        price_map: dict[str, dict[date, PricePoint]],
        today: date,
        execution_time: datetime,
        portfolio: Portfolio,
        cash_balance: Money,
        holdings_decimal: dict[str, Decimal],
    ) -> list[Transaction]:
        """Resolve a list of TradeSignals to validated transactions.

        Re-uses ``BacktestTransactionBuilder`` for the signal->transaction
        translation: same trade-factory invariants, same per-signal skip
        behaviour on insufficient funds / shares. A signal whose ticker
        has no price in the map is silently skipped (same as backtest's
        ``builder.apply_signal`` precondition).

        Args:
            signals: Output of ``TradingStrategy.generate_signals``.
            price_map: Today's prices keyed by ticker symbol.
            today: The trading day.
            execution_time: UTC timestamp to stamp on each transaction.
            portfolio: The owning portfolio.
            cash_balance: Pre-execution cash balance (Money VO).
            holdings_decimal: Pre-execution holdings keyed by ticker symbol.

        Returns:
            List of transactions ready to be persisted (may be empty).
        """
        # Seed a transaction builder with the current ledger-derived state.
        # The builder is the same one BacktestExecutor uses so all the
        # signal-resolution invariants (whole-share floor, per-trade fund /
        # share checks) match exactly.
        builder = BacktestTransactionBuilder(
            portfolio_id=portfolio.id,
            initial_cash=cash_balance,
        )
        # Pre-load the builder with the live portfolio's current
        # holdings so SELL signals validate against real positions
        # rather than starting from zero (backtest mode starts fresh,
        # live mode picks up where the ledger left off).
        seed: dict[Ticker, Quantity] = {
            Ticker(symbol): Quantity(shares)
            for symbol, shares in holdings_decimal.items()
            if shares > Decimal("0")
        }
        if seed:
            builder.seed_holdings(seed)

        for signal in signals:
            ticker_prices = price_map.get(signal.ticker.symbol, {})
            price_point = ticker_prices.get(today)
            if price_point is None:
                logger.debug(
                    "Skipping signal — no price for ticker today",
                    extra={"ticker": signal.ticker.symbol},
                )
                continue

            builder.apply_signal(
                signal=signal,
                price_per_share=price_point.price,
                timestamp=execution_time,
            )

        return builder.transactions

    async def _mark_success(self, activation: StrategyActivation) -> None:
        """Persist the activation with bumped ``last_executed_at``.

        Status remains whatever it was (almost always ``ACTIVE``).
        ``last_error`` is cleared so an activation that recovered from a
        prior error returns to a healthy view.
        """
        updated = StrategyActivation(
            id=activation.id,
            user_id=activation.user_id,
            strategy_id=activation.strategy_id,
            portfolio_id=activation.portfolio_id,
            status=activation.status,
            frequency=activation.frequency,
            created_at=activation.created_at,
            updated_at=datetime.now(UTC),
            last_executed_at=datetime.now(UTC),
            last_error=None,
        )
        await self._activation_repo.save(updated)

    async def _mark_error(self, activation: StrategyActivation, message: str) -> None:
        """Persist the activation as ``ERROR`` with a captured message.

        ``last_executed_at`` is still bumped — the run was attempted —
        so the operator UI can show "ran at X, but failed because Y".
        """
        updated = StrategyActivation(
            id=activation.id,
            user_id=activation.user_id,
            strategy_id=activation.strategy_id,
            portfolio_id=activation.portfolio_id,
            status=ActivationStatus.ERROR,
            frequency=activation.frequency,
            created_at=activation.created_at,
            updated_at=datetime.now(UTC),
            last_executed_at=datetime.now(UTC),
            last_error=message,
        )
        await self._activation_repo.save(updated)
