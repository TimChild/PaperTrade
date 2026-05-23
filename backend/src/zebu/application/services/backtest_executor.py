"""BacktestExecutor - Orchestrates the full backtest simulation pipeline."""

import logging
import math
from collections.abc import Mapping
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import TypedDict
from uuid import UUID, uuid4

from zebu.application.commands.run_backtest import RunBacktestCommand
from zebu.application.exceptions import IncompleteHistoricalDataError
from zebu.application.ports.agent_invocation_port import AgentInvocationResult
from zebu.application.ports.backtest_agent_invocation_factory import (
    BacktestAgentInvocationFactory,
)
from zebu.application.ports.backtest_agent_invocation_repository import (
    BacktestAgentInvocationRepository,
)
from zebu.application.ports.backtest_run_repository import BacktestRunRepository
from zebu.application.ports.portfolio_repository import PortfolioRepository
from zebu.application.ports.snapshot_repository import SnapshotRepository
from zebu.application.ports.strategy_activation_repository import (
    StrategyActivationRepository,
)
from zebu.application.ports.strategy_repository import StrategyRepository
from zebu.application.ports.transaction_repository import TransactionRepository
from zebu.application.ports.trigger_repository import TriggerRepository
from zebu.application.services.backtest_transaction_builder import (
    BacktestTransactionBuilder,
)
from zebu.application.services.historical_data_preparer import HistoricalDataPreparer
from zebu.application.services.snapshot_job import SnapshotJobService
from zebu.application.services.trigger_evaluators.drawdown import (
    DrawdownEvaluationData,
    DrawdownEvaluatorInput,
    PortfolioValuePoint,
    evaluate_drawdown,
)
from zebu.application.services.trigger_evaluators.volatility_spike import (
    TickerClose,
    VolatilityEvaluationData,
    VolatilityEvaluatorInput,
    evaluate_volatility_spike,
)
from zebu.application.services.trigger_invocation_orchestrator import (
    build_system_prompt,
    build_user_prompt,
)
from zebu.domain.entities.backtest_agent_invocation import BacktestAgentInvocation
from zebu.domain.entities.backtest_run import BacktestRun
from zebu.domain.entities.portfolio import Portfolio
from zebu.domain.entities.strategy import Strategy
from zebu.domain.entities.strategy_activation import StrategyActivation
from zebu.domain.entities.strategy_condition_trigger import StrategyConditionTrigger
from zebu.domain.entities.transaction import Transaction, TransactionType
from zebu.domain.exceptions import (
    AgentInvocationError,
    AgentResponseParseError,
    InvalidStrategyError,
)
from zebu.domain.services.strategies.buy_and_hold import BuyAndHoldStrategy
from zebu.domain.services.strategies.dollar_cost_averaging import (
    DollarCostAveragingStrategy,
)
from zebu.domain.services.strategies.moving_average_crossover import (
    MovingAverageCrossoverStrategy,
)
from zebu.domain.services.strategies.protocol import TradingStrategy
from zebu.domain.value_objects.activation_status import ActivationStatus
from zebu.domain.value_objects.agent_decision import AgentDecision
from zebu.domain.value_objects.allocation import Allocation
from zebu.domain.value_objects.backtest_agent_invocation_mode import (
    BacktestAgentInvocationMode,
)
from zebu.domain.value_objects.backtest_status import BacktestStatus
from zebu.domain.value_objects.money import Money
from zebu.domain.value_objects.portfolio_type import PortfolioType
from zebu.domain.value_objects.price_point import PricePoint
from zebu.domain.value_objects.quantity import Quantity
from zebu.domain.value_objects.strategy_parameters import (
    BuyAndHoldParameters,
    DcaParameters,
    MaCrossoverParameters,
)
from zebu.domain.value_objects.strategy_snapshot import StrategySnapshot
from zebu.domain.value_objects.ticker import Ticker
from zebu.domain.value_objects.trade_signal import TradeAction, TradeSignal
from zebu.domain.value_objects.trigger_condition import (
    ConditionType,
    DrawdownMetric,
    DrawdownParams,
    VolatilityParams,
)
from zebu.domain.value_objects.trigger_status import TriggerStatus

logger = logging.getLogger(__name__)

# Truncation cap for the audit-row rationale (matches L-1 entity limit).
_RATIONALE_MAX_LENGTH: int = 8000


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
      2. Simulate: Loop over trading days; on each day evaluate any
         attached triggers (Phase L-3), then apply strategy signals
      3. Persist: Bulk-save all transactions
      3a. Persist agent-invocation audit rows (Phase L-3)
      4. Snapshot: Generate daily portfolio snapshots via backfill
      5. Metrics: Compute summary metrics and mark COMPLETED

    On any failure, the BacktestRun is saved with FAILED status and
    the error message.

    Phase L-3 (Task #219) wired the agent-invocation path into the
    simulated-day loop. When ``command.agent_invocation_mode`` is
    ``NONE`` (default) the executor short-circuits the trigger /
    agent path entirely, matching pre-Phase-L behaviour exactly. When
    ``MOCK`` or ``LIVE``, triggers attached to the user's active
    activations of the strategy are evaluated against simulated state
    each day; on fire, the agent is invoked via the L-2 wrapper (LIVE)
    or the deterministic mock port (MOCK); decisions are applied to
    the simulated trade book; audit rows are accumulated and persisted
    at end-of-run.
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
        *,
        activation_repo: StrategyActivationRepository,
        trigger_repo: TriggerRepository,
        backtest_agent_invocation_repo: BacktestAgentInvocationRepository,
        agent_invocation_factory: BacktestAgentInvocationFactory,
    ) -> None:
        """Initialize executor with all required dependencies.

        Args:
            portfolio_repo: Portfolio persistence.
            transaction_repo: Transaction persistence.
            strategy_repo: Strategy persistence.
            backtest_run_repo: BacktestRun persistence.
            snapshot_service: Service for generating portfolio snapshots.
            snapshot_repo: Repository for querying snapshots during
                metric computation.
            data_preparer: Service for pre-fetching historical price data.
            activation_repo: Phase L-3 — resolves the user's
                activations of the backtested strategy so the trigger
                universe can be loaded.
            trigger_repo: Phase L-3 — read-only access to triggers
                attached to those activations.
            backtest_agent_invocation_repo: Phase L-3 — appends one
                :class:`BacktestAgentInvocation` per simulated trigger
                fire. Flushed once at the end of the run via
                :meth:`save_all` (per L-1's bulk-insert contract).
            agent_invocation_factory: Phase L-3 — builds the
                :class:`AgentInvocationPort` for each simulated fire
                day. Production wires
                :class:`AnthropicBacktestAgentInvocationFactory`;
                tests use the in-memory equivalent.
        """
        self._portfolio_repo = portfolio_repo
        self._transaction_repo = transaction_repo
        self._strategy_repo = strategy_repo
        self._backtest_run_repo = backtest_run_repo
        self._snapshot_service = snapshot_service
        self._snapshot_repo = snapshot_repo
        self._data_preparer = data_preparer
        self._activation_repo = activation_repo
        self._trigger_repo = trigger_repo
        self._backtest_agent_invocation_repo = backtest_agent_invocation_repo
        self._agent_invocation_factory = agent_invocation_factory

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

        # Build typed strategy snapshot — captured once and reused across
        # the lifecycle (RUNNING → COMPLETED/FAILED) so the same immutable
        # value object is on every persisted version of the run.
        strategy_snapshot = StrategySnapshot(
            strategy_id=strategy.id,
            name=strategy.name,
            strategy_type=strategy.strategy_type,
            tickers=tuple(strategy.tickers),
            parameters=strategy.parameters,
        )

        initial_cash_money = Money(command.initial_cash, "USD")

        # Create + persist the synthetic backtest portfolio FIRST. The
        # BacktestRun row below has a FK on ``backtest_runs.portfolio_id
        # → portfolios.id``; staging the run before its portfolio exists
        # leaves a pending INSERT that fails the FK constraint as soon as
        # any subsequent ``session.get`` (or other autoflush trigger)
        # fires inside the pipeline. Saving the portfolio up-front
        # ensures the FK target row is present in the DB before the run
        # row references it.
        portfolio = Portfolio(
            id=portfolio_id,
            user_id=command.user_id,
            name=f"[Backtest] {command.backtest_name}",
            created_at=now,
            portfolio_type=PortfolioType.BACKTEST,
        )
        await self._portfolio_repo.save(portfolio)

        # Create the initial RUNNING BacktestRun. Phase L-1 (Task #217):
        # stamp the agent invocation mode from the command onto the run
        # row so downstream readers can label the run without scanning
        # the audit table.
        backtest_run = BacktestRun(
            id=backtest_run_id,
            user_id=command.user_id,
            strategy_id=command.strategy_id,
            portfolio_id=portfolio_id,
            strategy_snapshot=strategy_snapshot,
            backtest_name=command.backtest_name,
            start_date=command.start_date,
            end_date=command.end_date,
            initial_cash=initial_cash_money,
            status=BacktestStatus.RUNNING,
            created_at=now,
            agent_invocation_mode=command.agent_invocation_mode,
        )
        # Phase H2: stamp the originating credential on the run row so the
        # activity feed can resolve the actor for backtest events. Lifecycle
        # transitions (RUNNING -> COMPLETED/FAILED) leave the original
        # api_key_id intact via the repository's save semantics.
        await self._backtest_run_repo.save(backtest_run, api_key_id=command.api_key_id)

        try:
            result = await self._run_pipeline(
                command=command,
                backtest_run=backtest_run,
                portfolio_id=portfolio_id,
                strategy=strategy,
                strategy_snapshot=strategy_snapshot,
                initial_cash=initial_cash_money,
            )
        except IncompleteHistoricalDataError as exc:
            # Phase J / Task #212 Layer 3 — partial-coverage is not a
            # failed backtest, it's "data isn't ready yet; please retry".
            # Mark the run row as FAILED (so the user sees a record of
            # the attempt) but re-raise so the API surface returns a
            # structured 503 instead of a 201 with status=FAILED.
            logger.info(
                "Backtest %s deferred — incomplete historical data for %s",
                backtest_run_id,
                exc.ticker.symbol,
            )
            failed_run = BacktestRun(
                id=backtest_run_id,
                user_id=command.user_id,
                strategy_id=command.strategy_id,
                portfolio_id=portfolio_id,
                strategy_snapshot=strategy_snapshot,
                backtest_name=command.backtest_name,
                start_date=command.start_date,
                end_date=command.end_date,
                initial_cash=initial_cash_money,
                status=BacktestStatus.FAILED,
                created_at=now,
                completed_at=datetime.now(UTC),
                error_message=str(exc),
                agent_invocation_mode=command.agent_invocation_mode,
            )
            await self._backtest_run_repo.save(
                failed_run, api_key_id=command.api_key_id
            )
            raise
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
                initial_cash=initial_cash_money,
                status=BacktestStatus.FAILED,
                created_at=now,
                completed_at=datetime.now(UTC),
                error_message=str(exc),
                agent_invocation_mode=command.agent_invocation_mode,
            )
            await self._backtest_run_repo.save(
                failed_run, api_key_id=command.api_key_id
            )
            return failed_run

        return result

    async def _run_pipeline(
        self,
        command: RunBacktestCommand,
        backtest_run: BacktestRun,
        portfolio_id: UUID,
        strategy: Strategy,
        strategy_snapshot: StrategySnapshot,
        initial_cash: Money,
    ) -> BacktestRun:
        """Internal pipeline.

        Phases: setup → prefetch → simulate (signals + L-3 agent fires)
        → persist transactions → persist agent invocations → snapshot
        → metrics.

        Args:
            command: The original run command
            backtest_run: The initial RUNNING BacktestRun entity
            portfolio_id: UUID for the new backtest portfolio
            strategy: The loaded strategy entity
            strategy_snapshot: Typed snapshot of the strategy at run time.
            initial_cash: Starting cash balance (Money)

        Returns:
            COMPLETED BacktestRun with metrics
        """
        # ── Phase 0: Setup ────────────────────────────────────────────────────
        # The synthetic portfolio is created + saved by ``execute()``
        # before this pipeline runs, so the BacktestRun's FK to
        # ``portfolios.id`` is satisfied before any pending INSERT is
        # flushed. Re-loading is unnecessary here.

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
        await self._transaction_repo.save(deposit, api_key_id=command.api_key_id)

        # ── Phase 1: Pre-fetch price data ─────────────────────────────────────
        trading_strategy = self._build_strategy(strategy)
        warm_up_days = 0
        if isinstance(strategy.parameters, MaCrossoverParameters):
            warm_up_days = strategy.parameters.slow_window * 2

        price_map = await self._data_preparer.prepare(
            tickers=strategy.tickers,
            start_date=command.start_date,
            end_date=command.end_date,
            warm_up_days=warm_up_days,
        )

        # ── Phase L-3 setup: trigger universe + per-sim cooldown / accum ──────
        # Resolve the trigger universe once before the day loop — re-running
        # this every iteration would be O(days × triggers) for no gain.
        # When ``agent_invocation_mode == NONE``, skip the resolve entirely
        # so the no-agent path costs zero extra reads.
        agent_mode = command.agent_invocation_mode
        triggers: list[StrategyConditionTrigger]
        if agent_mode is BacktestAgentInvocationMode.NONE:
            triggers = []
        else:
            triggers = await self._resolve_trigger_universe(command)

        agent_invocations: list[BacktestAgentInvocation] = []
        simulated_last_fired_at: dict[UUID, datetime] = {}

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

            # ── Phase 2a (L-3): evaluate triggers + dispatch agent ────────
            # Runs before strategy signals on the same day so the
            # strategy's signal generator sees post-agent cash + holdings.
            if triggers and agent_mode is not BacktestAgentInvocationMode.NONE:
                simulated_now = _end_of_utc_day(current_date)
                for trigger in triggers:
                    fire_record = await self._maybe_fire_trigger(
                        trigger=trigger,
                        simulated_date=current_date,
                        simulated_now=simulated_now,
                        simulated_last_fired_at=simulated_last_fired_at,
                        builder=builder,
                        price_map=price_map,
                        strategy=strategy,
                        backtest_run_id=backtest_run.id,
                        portfolio_id=portfolio_id,
                        command=command,
                    )
                    if fire_record is not None:
                        agent_invocations.append(fire_record)
                        simulated_last_fired_at[trigger.id] = simulated_now

            # ── Phase 2b: strategy signals ────────────────────────────────
            holdings_dec = {k.symbol: v.shares for k, v in builder.holdings.items()}

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
                ticker_prices = price_map.get(signal.ticker.symbol, {})
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
        # Single bulk insert — DO NOT introduce per-iteration save() calls here.
        # See agent_docs/audits/2026-05-09/database.md (P1-db-1): a per-trade
        # save() loop drove ~3 DB round-trips per transaction (SELECT + INSERT
        # + flush), turning a 100-trade backtest into 300+ round-trips.
        await self._transaction_repo.save_all(
            builder.transactions, api_key_id=command.api_key_id
        )

        # ── Phase 3a (L-3): Persist agent-invocation audit rows ───────────────
        # Single bulk insert per L-1's port contract. Skipped when no
        # rows accumulated (NONE mode, or no triggers in universe, or
        # triggers in universe but none fired).
        if agent_invocations:
            await self._backtest_agent_invocation_repo.save_all(agent_invocations)

        # ── Phase 4: Generate snapshots ───────────────────────────────────────
        await self._snapshot_service.backfill_snapshots(
            portfolio_id=portfolio_id,
            start_date=command.start_date,
            end_date=command.end_date,
        )

        # ── Phase 5: Compute metrics ──────────────────────────────────────────
        metrics = await self._compute_metrics(
            portfolio_id=portfolio_id,
            initial_cash=initial_cash.amount,
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
            initial_cash=initial_cash,
            status=BacktestStatus.COMPLETED,
            created_at=backtest_run.created_at,
            completed_at=datetime.now(UTC),
            total_return_pct=metrics["total_return_pct"],
            max_drawdown_pct=metrics["max_drawdown_pct"],
            annualized_return_pct=metrics["annualized_return_pct"],
            total_trades=metrics["total_trades"],
            agent_invocation_mode=command.agent_invocation_mode,
        )
        await self._backtest_run_repo.save(completed_run, api_key_id=command.api_key_id)

        return completed_run

    # ------------------------------------------------------------------ #
    # Phase L-3 helpers                                                  #
    # ------------------------------------------------------------------ #

    async def _resolve_trigger_universe(
        self, command: RunBacktestCommand
    ) -> list[StrategyConditionTrigger]:
        """Load triggers attached to the user's active activations of the strategy.

        Implements the "trigger universe = live triggers on the user's
        activations of this strategy" decision (task spec §3.2). The
        :class:`StrategyActivationRepository` doesn't ship a per-strategy
        list method, so we filter ``list_for_user`` in-Python — that
        call is owner-scoped and bounded by the typical "handful of
        activations per user" cardinality.

        Args:
            command: The originating backtest command (carries
                ``user_id`` + ``strategy_id``).

        Returns:
            ACTIVE triggers on ACTIVE activations of the strategy for
            this user. Order: trigger ``priority DESC, created_at ASC``
            within each activation (matches the live trigger evaluator's
            shape). Empty list if there are no eligible triggers.
        """
        activations = await self._activation_repo.list_for_user(command.user_id)
        eligible_activations = [
            a
            for a in activations
            if a.strategy_id == command.strategy_id
            and a.status is ActivationStatus.ACTIVE
        ]
        if not eligible_activations:
            return []

        combined: list[StrategyConditionTrigger] = []
        for activation in eligible_activations:
            triggers = await self._trigger_repo.list_for_activation(activation.id)
            for trigger in triggers:
                if trigger.status is TriggerStatus.ACTIVE:
                    combined.append(trigger)

        # Match the live evaluator's "priority DESC, created_at ASC"
        # so the per-fire ordering inside one simulated day is the same
        # as the production trigger sweep — apples-to-apples.
        combined.sort(key=lambda t: t.created_at)
        combined.sort(key=lambda t: t.priority, reverse=True)
        return combined

    async def _maybe_fire_trigger(
        self,
        *,
        trigger: StrategyConditionTrigger,
        simulated_date: date,
        simulated_now: datetime,
        simulated_last_fired_at: dict[UUID, datetime],
        builder: BacktestTransactionBuilder,
        price_map: Mapping[str, Mapping[date, PricePoint]],
        strategy: Strategy,
        backtest_run_id: UUID,
        portfolio_id: UUID,
        command: RunBacktestCommand,
    ) -> BacktestAgentInvocation | None:
        """Evaluate one trigger on one simulated day; on fire, dispatch the agent.

        Returns the resulting audit-row entity when the trigger fired,
        or ``None`` when it didn't (cooldown, expiry, evaluator said
        no-fire, earnings-proximity skipped). Per the spec, fire
        attempts always produce an audit row — including invocation
        failures and safety violations.

        Per-trigger / per-day errors are caught here and converted to
        ``INVOCATION_FAILED`` audit rows so one bad fire doesn't crash
        the backtest. Trigger-universe-level failures are not caught
        here (they happen before this method is called) and DO halt
        the backtest, matching the existing executor's resilience
        pattern.
        """
        # In-simulation cooldown / expiry / status gate.
        if not _is_simulated_evaluable(
            trigger=trigger,
            at=simulated_now,
            simulated_last_fired_at=simulated_last_fired_at,
        ):
            return None

        try:
            fired, evaluation_data = self._evaluate_simulated_trigger(
                trigger=trigger,
                simulated_now=simulated_now,
                simulated_date=simulated_date,
                builder=builder,
                price_map=price_map,
                strategy=strategy,
            )
        except Exception as exc:
            # Evaluator threw — record an INVOCATION_FAILED row with the
            # exception message so the backtest continues but the failure
            # is visible. Logged at exception level for debugging.
            logger.exception(
                "Trigger evaluator failed during backtest",
                extra={
                    "backtest_run_id": str(backtest_run_id),
                    "trigger_id": str(trigger.id),
                    "simulated_date": simulated_date.isoformat(),
                },
            )
            return _build_invocation_failed_row(
                backtest_run_id=backtest_run_id,
                trigger=trigger,
                simulated_date=simulated_date,
                evaluation_data={},
                mode=command.agent_invocation_mode,
                reason=f"Trigger evaluator failed: {exc}",
            )

        if not fired or evaluation_data is None:
            return None

        return await self._fire_simulated_trigger(
            trigger=trigger,
            simulated_date=simulated_date,
            simulated_now=simulated_now,
            evaluation_data=evaluation_data,
            builder=builder,
            price_map=price_map,
            strategy=strategy,
            backtest_run_id=backtest_run_id,
            portfolio_id=portfolio_id,
            command=command,
        )

    def _evaluate_simulated_trigger(
        self,
        *,
        trigger: StrategyConditionTrigger,
        simulated_now: datetime,
        simulated_date: date,
        builder: BacktestTransactionBuilder,
        price_map: Mapping[str, Mapping[date, PricePoint]],
        strategy: Strategy,
    ) -> tuple[bool, Mapping[str, object] | None]:
        """Evaluate one trigger's condition against simulated state.

        Pure dispatcher onto the per-condition evaluators. The
        evaluator returns ``(fired, evaluation_data)`` — ``False, None``
        means no fire; ``True, {...}`` means fire with the snapshot.

        Earnings-proximity triggers are explicitly skipped here with a
        logged warning (see spec §"Design decisions" §5 — the live
        :class:`EarningsCalendarPort` is a stub; a backtest invocation
        on stub data would test nothing). Custom-rule triggers are
        unsupported in both live and backtest paths.

        Returns:
            ``(fired, evaluation_data)``. ``evaluation_data`` is a
            JSON-shaped dict when ``fired`` is ``True``, otherwise
            ``None``.
        """
        condition_type = trigger.condition_type

        if condition_type is ConditionType.DRAWDOWN_THRESHOLD:
            return _evaluate_drawdown_simulated(
                trigger=trigger,
                simulated_now=simulated_now,
                simulated_date=simulated_date,
                builder=builder,
                price_map=price_map,
                strategy=strategy,
            )
        if condition_type is ConditionType.VOLATILITY_SPIKE:
            return _evaluate_volatility_simulated(
                trigger=trigger,
                simulated_now=simulated_now,
                price_map=price_map,
                strategy=strategy,
            )
        if condition_type is ConditionType.EARNINGS_PROXIMITY:
            logger.warning(
                "Earnings-proximity trigger skipped in backtest; "
                "EarningsCalendarPort is a stub and would produce no "
                "events. Trigger=%s",
                trigger.id,
            )
            return False, None
        # CUSTOM_RULE — unsupported in both live and backtest.
        logger.warning(
            "Custom-rule trigger skipped in backtest (unsupported). Trigger=%s",
            trigger.id,
        )
        return False, None

    async def _fire_simulated_trigger(
        self,
        *,
        trigger: StrategyConditionTrigger,
        simulated_date: date,
        simulated_now: datetime,
        evaluation_data: Mapping[str, object],
        builder: BacktestTransactionBuilder,
        price_map: Mapping[str, Mapping[date, PricePoint]],
        strategy: Strategy,
        backtest_run_id: UUID,
        portfolio_id: UUID,
        command: RunBacktestCommand,
    ) -> BacktestAgentInvocation:
        """Invoke the agent for one fired trigger and apply the decision.

        Always returns an audit-row entity. The exact shape depends on
        the mode and the agent's response:

        * MOCK — every call goes through the mock port; every row is
          MOCK-mode (``decision=HOLD``, no rationale, no model).
        * LIVE — wrapper invokes the real adapter (or scripted test
          port). On success, builds a LIVE row with the agent's
          rationale + decision + payload. On
          :class:`BacktestSafetyViolationError` /
          :class:`AgentInvocationError`, builds an INVOCATION_FAILED
          LIVE row.

        On BUY / SELL, the simulated builder is mutated. On
        MODIFY_STRATEGY (LIVE only — MOCK never emits it), the row is
        recorded but the strategy is NOT mutated (spec §"Design
        decisions" §3). HOLD / NEEDS_HUMAN are audit-only.
        """
        mode = command.agent_invocation_mode

        # Build per-fire port. Production wires
        # :class:`AnthropicBacktestAgentInvocationFactory`; tests wire
        # the in-memory factory.
        try:
            port = self._agent_invocation_factory.for_simulated_date(
                simulated_date=simulated_date,
                mode=mode,
                agent_temperature=command.agent_temperature,
            )
        except Exception as exc:
            logger.exception(
                "Agent invocation factory raised during backtest",
                extra={
                    "backtest_run_id": str(backtest_run_id),
                    "trigger_id": str(trigger.id),
                    "simulated_date": simulated_date.isoformat(),
                },
            )
            return _build_invocation_failed_row(
                backtest_run_id=backtest_run_id,
                trigger=trigger,
                simulated_date=simulated_date,
                evaluation_data=evaluation_data,
                mode=mode,
                reason=f"Agent invocation factory error: {exc}",
            )

        # Build prompts — reuse the live builders so live and backtest
        # see byte-for-byte identical prompts on the same inputs (apples-
        # to-apples comparison). The user prompt is parameterised with
        # the SIMULATED cash + holdings, not the durable portfolio state.
        # ``activation`` is not available at backtest time, but
        # ``build_user_prompt`` only uses a handful of its fields and
        # they map naturally onto the simulated state.
        system_prompt = build_system_prompt()
        try:
            user_prompt = self._build_simulated_user_prompt(
                trigger=trigger,
                strategy=strategy,
                evaluation_data=evaluation_data,
                builder=builder,
                portfolio_id=portfolio_id,
            )
        except Exception as exc:
            logger.exception(
                "User-prompt construction failed during backtest",
                extra={
                    "backtest_run_id": str(backtest_run_id),
                    "trigger_id": str(trigger.id),
                },
            )
            return _build_invocation_failed_row(
                backtest_run_id=backtest_run_id,
                trigger=trigger,
                simulated_date=simulated_date,
                evaluation_data=evaluation_data,
                mode=mode,
                reason=f"User-prompt construction failed: {exc}",
            )

        # Invoke the agent. Both AgentInvocationError and its
        # BacktestSafetyViolationError subclass surface here.
        try:
            result = await port.invoke(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                agent_temperature=command.agent_temperature,
            )
        except (AgentInvocationError, AgentResponseParseError) as exc:
            # Includes BacktestSafetyViolationError (subclass of
            # AgentInvocationError). Build an INVOCATION_FAILED audit row.
            logger.info(
                "Backtest agent invocation failed",
                extra={
                    "backtest_run_id": str(backtest_run_id),
                    "trigger_id": str(trigger.id),
                    "simulated_date": simulated_date.isoformat(),
                    "exception_type": type(exc).__name__,
                    "exception_message": str(exc),
                },
            )
            return _build_invocation_failed_row(
                backtest_run_id=backtest_run_id,
                trigger=trigger,
                simulated_date=simulated_date,
                evaluation_data=evaluation_data,
                mode=mode,
                reason=f"{type(exc).__name__}: {exc}",
            )
        except Exception as exc:
            # Unexpected — catch-all so one bad fire can't crash the run.
            logger.exception(
                "Backtest agent invocation raised an unexpected exception",
                extra={
                    "backtest_run_id": str(backtest_run_id),
                    "trigger_id": str(trigger.id),
                },
            )
            return _build_invocation_failed_row(
                backtest_run_id=backtest_run_id,
                trigger=trigger,
                simulated_date=simulated_date,
                evaluation_data=evaluation_data,
                mode=mode,
                reason=f"Unexpected error: {exc}",
            )

        # Apply the decision to the simulated trade book. The function
        # returns the resulting audit-row entity (always — even on
        # downgrade-to-HOLD or rejection).
        return _apply_simulated_decision(
            backtest_run_id=backtest_run_id,
            trigger=trigger,
            simulated_date=simulated_date,
            simulated_now=simulated_now,
            evaluation_data=evaluation_data,
            mode=mode,
            result=result,
            builder=builder,
            price_map=price_map,
            strategy=strategy,
        )

    def _build_simulated_user_prompt(
        self,
        *,
        trigger: StrategyConditionTrigger,
        strategy: Strategy,
        evaluation_data: Mapping[str, object],
        builder: BacktestTransactionBuilder,
        portfolio_id: UUID,
    ) -> str:
        """Construct the user prompt with simulated portfolio state.

        Reuses :func:`build_user_prompt` from the live orchestrator so
        prompt shape is identical — only the parameter values differ
        (simulated cash / holdings instead of durable DB state). The
        live builder takes an ``activation`` argument we don't have at
        backtest time, so we synthesise the bits it actually reads from
        a lightweight :class:`StrategyActivation` shim.

        The shim isn't persisted; it's a transient object used only
        for prompt construction.
        """
        # Synthesise an activation for the prompt — the live builder
        # only reads ``id``, ``status``, ``frequency``, ``last_executed_at``,
        # ``last_error``. None of these are meaningful in backtest, so
        # we lean on the strategy's already-resolved fields and the
        # builder's portfolio_id for the activation_id slot.
        from zebu.domain.value_objects.activation_frequency import (
            ActivationFrequency,
        )

        now = datetime.now(UTC)
        activation_shim = StrategyActivation(
            # Synthetic id — the activation is transient (not persisted).
            # The prompt only echoes this for context; reusing the
            # portfolio_id slot was a copy-paste mistake.
            id=uuid4(),
            user_id=strategy.user_id,
            strategy_id=strategy.id,
            portfolio_id=portfolio_id,
            status=ActivationStatus.ACTIVE,
            frequency=ActivationFrequency.DAILY_MARKET_CLOSE,
            created_at=now,
            updated_at=now,
        )
        holdings_summary = [
            (ticker.symbol, qty.shares) for ticker, qty in builder.holdings.items()
        ]
        return build_user_prompt(
            trigger=trigger,
            activation=activation_shim,
            strategy=strategy,
            portfolio_id=portfolio_id,
            cash_balance=builder.cash_balance.amount,
            holdings_summary=holdings_summary,
            evaluation_data=evaluation_data,
        )

    def _build_strategy(self, strategy: Strategy) -> TradingStrategy:
        """Resolve the strategy entity to its TradingStrategy implementation.

        With typed parameters, the per-type runtime ``isinstance`` /
        ``dict.get`` validation that used to live here is gone — the
        ``Strategy`` constructor enforces shape, and we just pattern-match
        on the parameter type.

        Args:
            strategy: The strategy domain entity

        Returns:
            TradingStrategy implementation

        Raises:
            InvalidStrategyError: If strategy parameters do not match a
                known concrete type (defensive — should be unreachable).
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


# --------------------------------------------------------------------------- #
# Module-private helpers (no executor state — kept module-level for testability)
# --------------------------------------------------------------------------- #


def _end_of_utc_day(simulated_date: date) -> datetime:
    """End-of-UTC-day timestamp for a simulated date.

    Mirrors the L-2 wrapper's convention so the agent's simulated_date
    cap and the executor's "now" reference agree.
    """
    return datetime(
        simulated_date.year,
        simulated_date.month,
        simulated_date.day,
        hour=23,
        minute=59,
        second=59,
        tzinfo=UTC,
    )


def _noon_utc(simulated_date: date) -> datetime:
    """Noon-UTC timestamp for a simulated date.

    Matches the strategy-signal timestamp convention (line 328 in the
    pre-L-3 executor). Used for simulated agent-fired trades so they
    interleave consistently with strategy signals on the same day.
    """
    return datetime(
        simulated_date.year,
        simulated_date.month,
        simulated_date.day,
        12,
        0,
        0,
        tzinfo=UTC,
    )


def _is_simulated_evaluable(
    *,
    trigger: StrategyConditionTrigger,
    at: datetime,
    simulated_last_fired_at: dict[UUID, datetime],
) -> bool:
    """Per-simulation evaluability check.

    Combines the trigger's own ``is_evaluable`` (which handles status,
    expiry, durable cooldown) with the per-simulation cooldown dict
    we maintain in-memory. The durable ``last_fired_at`` on the entity
    is NOT mutated by backtest — it tracks live cooldown only.
    """
    # Re-use the entity's status / expiry check by stripping the
    # durable cooldown component: if the trigger is in durable cooldown
    # at ``at`` (which only happens when the trigger has live-fired
    # recently and the backtest is testing a near-present window) we
    # SHOULD still let it fire in simulation — the durable cooldown is
    # a live-only concern. So we read status + expiry directly.
    if trigger.status is not TriggerStatus.ACTIVE:
        return False
    if trigger.expires_at is not None:
        expires_at_utc = (
            trigger.expires_at
            if trigger.expires_at.tzinfo is not None
            else trigger.expires_at.replace(tzinfo=UTC)
        )
        if expires_at_utc <= at:
            return False

    # Per-simulation cooldown check.
    sim_last_fired = simulated_last_fired_at.get(trigger.id)
    if sim_last_fired is None:
        return True
    elapsed = at - sim_last_fired
    return elapsed >= timedelta(seconds=trigger.cooldown_seconds)


def _build_invocation_failed_row(
    *,
    backtest_run_id: UUID,
    trigger: StrategyConditionTrigger,
    simulated_date: date,
    evaluation_data: Mapping[str, object],
    mode: BacktestAgentInvocationMode,
    reason: str,
) -> BacktestAgentInvocation:
    """Build an INVOCATION_FAILED audit row.

    INVOCATION_FAILED rows are LIVE-mode only — MOCK never fails by
    construction (the mock port returns HOLD synchronously). When the
    caller's ``mode`` is MOCK and we ended up here, that's a wiring
    bug; we still build a LIVE-mode row so the entity invariants
    accept it (the row's existence is the bug-signal — operators can
    tell from the rationale).
    """
    # The L-1 entity rejects ``invocation_mode=NONE`` outright (no row
    # should ever be persisted for NONE-mode runs). Map any non-LIVE
    # mode to LIVE for the row so the entity invariants are satisfied
    # — the rationale carries the wiring-bug context.
    row_mode = (
        BacktestAgentInvocationMode.LIVE
        if mode is not BacktestAgentInvocationMode.LIVE
        else mode
    )
    rationale = _truncate_rationale(reason)
    return BacktestAgentInvocation(
        id=uuid4(),
        backtest_run_id=backtest_run_id,
        simulated_date=simulated_date,
        trigger_id=trigger.id,
        condition_evaluation_data=dict(evaluation_data),
        rationale=rationale,
        latency_ms=0,
        model="(invocation failed)",
        invocation_mode=row_mode,
        created_at=datetime.now(UTC),
        agent_decision=AgentDecision.INVOCATION_FAILED,
        decision_payload=None,
        decision_executed=False,
        simulated_trade_id=None,
        agent_invocation_id=None,
    )


def _truncate_rationale(value: str) -> str:
    """Cap a rationale at the L-1 entity's 8000-char limit."""
    if len(value) <= _RATIONALE_MAX_LENGTH:
        return value
    return value[:_RATIONALE_MAX_LENGTH]


def _apply_simulated_decision(
    *,
    backtest_run_id: UUID,
    trigger: StrategyConditionTrigger,
    simulated_date: date,
    simulated_now: datetime,
    evaluation_data: Mapping[str, object],
    mode: BacktestAgentInvocationMode,
    result: AgentInvocationResult,
    builder: BacktestTransactionBuilder,
    price_map: Mapping[str, Mapping[date, PricePoint]],
    strategy: Strategy,
) -> BacktestAgentInvocation:
    """Apply a successful agent invocation result to the simulated state.

    Always returns a :class:`BacktestAgentInvocation` audit row.

    Decision branches:

    * MOCK rows: the mock port returns ``decision=HOLD`` with
      ``model=""``. The audit row is MOCK-mode (entity invariants
      require ``decision_payload=None``, empty rationale, etc.).
    * LIVE BUY / SELL: apply via the builder. On success the row
      points at the resulting transaction id. On rejection (no price,
      ticker outside universe, insufficient funds) the row is recorded
      with the rejection captured in the rationale and
      ``decision_executed=False``.
    * LIVE MODIFY_STRATEGY: record-only in backtest (spec §"Design
      decisions" §3). The row carries the agent's payload but the
      strategy is NOT mutated; ``decision_executed=False`` and the
      rationale notes the no-op.
    * LIVE HOLD / NEEDS_HUMAN: audit-only; no trade.
    """

    # MOCK rows are byte-stable — the mock port always returns HOLD with
    # ``model=""``. Build the MOCK-shaped row regardless of the
    # decision the port emitted (defence — a misbehaving mock port that
    # emits BUY would otherwise smuggle a trade through).
    if mode is BacktestAgentInvocationMode.MOCK:
        return BacktestAgentInvocation(
            id=uuid4(),
            backtest_run_id=backtest_run_id,
            simulated_date=simulated_date,
            trigger_id=trigger.id,
            condition_evaluation_data=dict(evaluation_data),
            rationale="",
            latency_ms=0,
            model="",
            invocation_mode=BacktestAgentInvocationMode.MOCK,
            created_at=datetime.now(UTC),
            agent_decision=AgentDecision.HOLD,
            decision_payload=None,
            decision_executed=False,
            simulated_trade_id=None,
            agent_invocation_id=None,
        )

    # LIVE branch. Per L-1 entity invariants, LIVE rows whose decision
    # is not INVOCATION_FAILED MUST have a non-empty rationale. Pad with
    # a decision-stamp when the upstream port returned an empty one
    # (production Anthropic never does, but test fakes / mis-behaving
    # transports might).
    decision = result.decision
    rationale_raw = result.rationale or f"({decision.value} — no rationale provided)"

    if decision is AgentDecision.BUY or decision is AgentDecision.SELL:
        applied_trade_id, downgraded_reason = _try_apply_trade(
            decision=decision,
            payload=result.payload,
            simulated_date=simulated_date,
            simulated_now=simulated_now,
            builder=builder,
            price_map=price_map,
            strategy=strategy,
        )
        if applied_trade_id is not None:
            return BacktestAgentInvocation(
                id=uuid4(),
                backtest_run_id=backtest_run_id,
                simulated_date=simulated_date,
                trigger_id=trigger.id,
                condition_evaluation_data=dict(evaluation_data),
                rationale=_truncate_rationale(rationale_raw),
                latency_ms=result.latency_ms,
                model=result.model,
                invocation_mode=BacktestAgentInvocationMode.LIVE,
                created_at=datetime.now(UTC),
                agent_decision=decision,
                decision_payload=dict(result.payload),
                decision_executed=True,
                simulated_trade_id=applied_trade_id,
                agent_invocation_id=result.invocation_id,
            )
        # Downgrade-to-HOLD path. The audit row keeps the original
        # decision intent in the rationale so a reviewer sees what
        # the agent wanted — but ``agent_decision`` is HOLD and
        # ``decision_executed=False`` so the entity invariant ("only
        # actionable decisions execute") holds.
        downgrade_message = (
            f"{decision.value} downgraded to HOLD in backtest: {downgraded_reason}"
        )
        composed = (
            f"{rationale_raw}\n---\n{downgrade_message}"
            if rationale_raw
            else downgrade_message
        )
        return BacktestAgentInvocation(
            id=uuid4(),
            backtest_run_id=backtest_run_id,
            simulated_date=simulated_date,
            trigger_id=trigger.id,
            condition_evaluation_data=dict(evaluation_data),
            rationale=_truncate_rationale(composed),
            latency_ms=result.latency_ms,
            model=result.model,
            invocation_mode=BacktestAgentInvocationMode.LIVE,
            created_at=datetime.now(UTC),
            agent_decision=AgentDecision.HOLD,
            decision_payload=dict(result.payload),
            decision_executed=False,
            simulated_trade_id=None,
            agent_invocation_id=result.invocation_id,
        )

    if decision is AgentDecision.MODIFY_STRATEGY:
        # Record-only in backtest. The strategy is NOT mutated.
        notice = (
            "MODIFY_STRATEGY decisions are not applied in backtest mode "
            "(spec §Design decisions §3): row recorded for audit only."
        )
        composed = f"{rationale_raw}\n---\n{notice}" if rationale_raw else notice
        return BacktestAgentInvocation(
            id=uuid4(),
            backtest_run_id=backtest_run_id,
            simulated_date=simulated_date,
            trigger_id=trigger.id,
            condition_evaluation_data=dict(evaluation_data),
            rationale=_truncate_rationale(composed),
            latency_ms=result.latency_ms,
            model=result.model,
            invocation_mode=BacktestAgentInvocationMode.LIVE,
            created_at=datetime.now(UTC),
            agent_decision=AgentDecision.MODIFY_STRATEGY,
            decision_payload=dict(result.payload),
            decision_executed=False,
            simulated_trade_id=None,
            agent_invocation_id=result.invocation_id,
        )

    if decision is AgentDecision.HOLD:
        return BacktestAgentInvocation(
            id=uuid4(),
            backtest_run_id=backtest_run_id,
            simulated_date=simulated_date,
            trigger_id=trigger.id,
            condition_evaluation_data=dict(evaluation_data),
            rationale=_truncate_rationale(rationale_raw or "HOLD"),
            latency_ms=result.latency_ms,
            model=result.model,
            invocation_mode=BacktestAgentInvocationMode.LIVE,
            created_at=datetime.now(UTC),
            agent_decision=AgentDecision.HOLD,
            decision_payload=dict(result.payload),
            decision_executed=False,
            simulated_trade_id=None,
            agent_invocation_id=result.invocation_id,
        )

    if decision is AgentDecision.NEEDS_HUMAN:
        notice = (
            "NEEDS_HUMAN escalations don't create an ExplorationTask in "
            "backtest (spec §Design decisions): row recorded for audit "
            "only."
        )
        composed = f"{rationale_raw}\n---\n{notice}" if rationale_raw else notice
        return BacktestAgentInvocation(
            id=uuid4(),
            backtest_run_id=backtest_run_id,
            simulated_date=simulated_date,
            trigger_id=trigger.id,
            condition_evaluation_data=dict(evaluation_data),
            rationale=_truncate_rationale(composed),
            latency_ms=result.latency_ms,
            model=result.model,
            invocation_mode=BacktestAgentInvocationMode.LIVE,
            created_at=datetime.now(UTC),
            agent_decision=AgentDecision.NEEDS_HUMAN,
            decision_payload=dict(result.payload),
            decision_executed=False,
            simulated_trade_id=None,
            agent_invocation_id=result.invocation_id,
        )

    # INVOCATION_FAILED emitted by the port (rare — the agent never
    # picks it, but a misbehaving fake might).
    return BacktestAgentInvocation(
        id=uuid4(),
        backtest_run_id=backtest_run_id,
        simulated_date=simulated_date,
        trigger_id=trigger.id,
        condition_evaluation_data=dict(evaluation_data),
        rationale=_truncate_rationale(rationale_raw),
        latency_ms=result.latency_ms,
        model=result.model,
        invocation_mode=BacktestAgentInvocationMode.LIVE,
        created_at=datetime.now(UTC),
        agent_decision=AgentDecision.INVOCATION_FAILED,
        decision_payload=None,
        decision_executed=False,
        simulated_trade_id=None,
        agent_invocation_id=result.invocation_id,
    )


def _try_apply_trade(
    *,
    decision: AgentDecision,
    payload: Mapping[str, object],
    simulated_date: date,
    simulated_now: datetime,
    builder: BacktestTransactionBuilder,
    price_map: Mapping[str, Mapping[date, PricePoint]],
    strategy: Strategy,
) -> tuple[UUID | None, str]:
    """Try to apply a BUY / SELL decision to the simulated builder.

    Returns ``(trade_id_or_none, rejection_reason)``. On success the
    trade id is non-None and the reason is empty. On any rejection
    the trade id is None and the reason describes why.
    """
    ticker_obj = payload.get("ticker")
    ticker_str = ticker_obj if isinstance(ticker_obj, str) else ""
    if not ticker_str:
        return None, f"{decision.value} payload missing 'ticker'"

    if ticker_str not in strategy.tickers:
        return (
            None,
            f"{decision.value} {ticker_str} not in strategy ticker "
            f"universe {strategy.tickers}",
        )

    try:
        ticker = Ticker(ticker_str)
    except Exception as exc:
        return None, f"{decision.value} invalid ticker {ticker_str!r}: {exc}"

    quantity_raw = payload.get("quantity")
    quantity_str = quantity_raw if isinstance(quantity_raw, str) else ""
    try:
        quantity = _resolve_quantity(quantity_str)
    except Exception as exc:
        return None, f"{decision.value} invalid quantity {quantity_str!r}: {exc}"

    ticker_prices = price_map.get(ticker.symbol, {})
    price_point = ticker_prices.get(simulated_date)
    if price_point is None:
        return (
            None,
            f"{decision.value} {ticker_str} no simulated price for "
            f"{simulated_date.isoformat()}",
        )

    # Sim time matches strategy-signal timestamp convention so trades
    # interleave cleanly on the same simulated day.
    del simulated_now  # currently unused — _noon is what the builder gets
    trade_ts = _noon_utc(simulated_date)
    action = TradeAction.BUY if decision is AgentDecision.BUY else TradeAction.SELL
    signal = TradeSignal(
        action=action,
        ticker=ticker,
        signal_date=simulated_date,
        quantity=quantity,
    )
    try:
        applied = builder.apply_signal(
            signal=signal,
            price_per_share=price_point.price,
            timestamp=trade_ts,
        )
    except Exception as exc:
        return None, f"{decision.value} signal application raised: {exc}"
    if applied is None:
        return (
            None,
            f"{decision.value} {ticker_str} qty={quantity.shares} "
            "rejected by builder (insufficient funds/shares or zero "
            "quantity after sizing)",
        )
    return applied.id, ""


def _resolve_quantity(quantity_str: str) -> Quantity:
    """Coerce the agent's quantity payload to a :class:`Quantity`.

    Empty / missing / null values default to one share — a
    conservative baseline that matches the live orchestrator's
    behaviour. The agent can specify a positive decimal to override.
    """
    if not quantity_str.strip():
        return Quantity(Decimal("1"))
    return Quantity(Decimal(quantity_str))


def _evaluate_drawdown_simulated(
    *,
    trigger: StrategyConditionTrigger,
    simulated_now: datetime,
    simulated_date: date,
    builder: BacktestTransactionBuilder,
    price_map: Mapping[str, Mapping[date, PricePoint]],
    strategy: Strategy,
) -> tuple[bool, DrawdownEvaluationData | None]:
    """Build inputs for the pure drawdown evaluator and dispatch.

    Pre-Phase-L the live trigger evaluator built its inputs from the
    durable transaction ledger + DB price reads. Here we build them
    from the simulated builder's in-memory ledger + the pre-fetched
    ``price_map``.

    For ``PORTFOLIO_TOTAL`` metric: compute the simulated portfolio
    total-value series day-by-day across the lookback window.
    For ``PER_TICKER`` metric: emit one input per strategy ticker, each
    carrying that ticker's price series over the window.
    """
    params = trigger.condition_params
    assert isinstance(params, DrawdownParams)

    window_start = simulated_now - timedelta(days=params.lookback_days)
    inputs: list[DrawdownEvaluatorInput] = []

    if params.metric is DrawdownMetric.PORTFOLIO_TOTAL:
        # Walk simulated days from window_start.date() to simulated_date,
        # computing portfolio total value at each day (cash + holdings
        # × that-day's-close). We use the builder's current holdings
        # (a snapshot at simulated_now) — strictly speaking the holdings
        # changed across the window, but the simulated builder only
        # carries the current state. For a backtest where the agent
        # acts on portfolio drawdown, treating the current holdings as
        # constant across the window is a known approximation and is
        # explicitly documented in the spec §"Day-loop integration".
        points: list[PortfolioValuePoint] = []
        cash_now = builder.cash_balance.amount
        holdings_now = builder.holdings
        scan_date = window_start.date()
        while scan_date <= simulated_date:
            ts = datetime(
                scan_date.year, scan_date.month, scan_date.day, 12, 0, 0, tzinfo=UTC
            )
            holdings_value = Decimal("0")
            for ticker, qty in holdings_now.items():
                price_point = price_map.get(ticker.symbol, {}).get(scan_date)
                if price_point is None:
                    # Missing day (weekend / holiday) — skip this point
                    # rather than carry forward, mirroring the price-map's
                    # sparse-day semantics.
                    holdings_value = Decimal("-1")
                    break
                holdings_value += qty.shares * price_point.price.amount
            if holdings_value < Decimal("0"):
                scan_date += timedelta(days=1)
                continue
            points.append(
                PortfolioValuePoint(observed_at=ts, value=cash_now + holdings_value)
            )
            scan_date += timedelta(days=1)
        inputs.append(
            DrawdownEvaluatorInput(
                ticker=None,
                value_points=points,
                lookback_window_start=window_start,
                lookback_window_end=simulated_now,
            )
        )
    else:
        # PER_TICKER — one input per ticker; value series is just the
        # close-price series for that ticker in the window.
        for ticker_symbol in strategy.tickers:
            ticker_points: list[PortfolioValuePoint] = []
            for day, price_point in price_map.get(ticker_symbol, {}).items():
                if window_start.date() <= day <= simulated_date:
                    ts = datetime(day.year, day.month, day.day, 12, 0, 0, tzinfo=UTC)
                    ticker_points.append(
                        PortfolioValuePoint(
                            observed_at=ts, value=price_point.price.amount
                        )
                    )
            ticker_points.sort(key=lambda p: p.observed_at)
            inputs.append(
                DrawdownEvaluatorInput(
                    ticker=ticker_symbol,
                    value_points=ticker_points,
                    lookback_window_start=window_start,
                    lookback_window_end=simulated_now,
                )
            )

    return evaluate_drawdown(params=params, inputs=inputs)


def _evaluate_volatility_simulated(
    *,
    trigger: StrategyConditionTrigger,
    simulated_now: datetime,
    price_map: Mapping[str, Mapping[date, PricePoint]],
    strategy: Strategy,
) -> tuple[bool, VolatilityEvaluationData | None]:
    """Build inputs for the pure volatility evaluator and dispatch.

    The evaluator's "fire on first ticker over threshold" semantics are
    inherited as-is. Inputs honour ``params.tickers`` (the subset) when
    set, else fall back to the strategy's full ticker universe.
    """
    params = trigger.condition_params
    assert isinstance(params, VolatilityParams)

    window_start = simulated_now - timedelta(days=params.over_days)

    if params.tickers is not None:
        ticker_universe = [t.symbol for t in params.tickers]
    else:
        ticker_universe = list(strategy.tickers)

    inputs: list[VolatilityEvaluatorInput] = []
    for ticker_symbol in ticker_universe:
        closes: list[TickerClose] = []
        for day, price_point in price_map.get(ticker_symbol, {}).items():
            if window_start.date() <= day <= simulated_now.date():
                ts = datetime(day.year, day.month, day.day, 12, 0, 0, tzinfo=UTC)
                closes.append(
                    TickerClose(observed_at=ts, close=price_point.price.amount)
                )
        closes.sort(key=lambda c: c.observed_at)
        inputs.append(
            VolatilityEvaluatorInput(
                ticker=ticker_symbol,
                closes=closes,
                window_start=window_start,
                window_end=simulated_now,
            )
        )

    return evaluate_volatility_spike(params=params, inputs=inputs)
