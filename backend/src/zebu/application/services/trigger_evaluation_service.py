"""TriggerEvaluationService - evaluates ACTIVE triggers each scheduler tick.

Phase F-2 of the agent platform, extended in F-3 to optionally hand off
to the :class:`TriggerInvocationOrchestrator` when a fire is detected,
and extended in F-4 with the volatility-spike and earnings-proximity
evaluators. Mirrors :class:`StrategyExecutionService` in shape but for
the new trigger-fire path: the service lists evaluable triggers,
computes the condition's required inputs from the ledger + market data,
runs the per-condition evaluator, and on a fire either returns the
"would fire" envelope (F-2 default) or hands off to the orchestrator
(F-3, gated by ``ZEBU_TRIGGER_FIRES_ENABLED``).

**F-3 wiring**: when the orchestrator is supplied at construction
time AND the runtime feature flag is on, the service calls
:meth:`TriggerInvocationOrchestrator.fire` for each fire-eligible
result. The flag exists so this PR is safe to merge with the actual
fire path off in production until Tim opts in. Tests pass an
in-memory orchestrator so coverage is high regardless of the flag.

**F-4 update**: VOLATILITY_SPIKE and EARNINGS_PROXIMITY now dispatch to
their respective evaluators (PR #262). The dispatch is done via ``match``
on :class:`ConditionType` — adding a new condition type is "extend the
match arm and add the evaluator". Only ``CUSTOM_RULE`` still raises
:class:`NotImplementedError` (intentional — see Phase F design Q1).

The service composes the I/O around the per-condition evaluators (which
are pure functions on inputs, except for ``evaluate_earnings_proximity``
which takes the calendar port directly per design §2.1.4). The ledger
walk and price fetching all happen here; the evaluators receive
fully-resolved value series.

References:
- ``docs/architecture/phase-f-agent-in-the-loop.md`` §2.1, §3 (sequence),
  §5 (scheduler runtime), §10 Q5 (stub earnings calendar adapter),
  §10 Q6 (recompute from ledger).
- :class:`StrategyExecutionService` for the structural sibling.
"""

import logging
import os
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import TypedDict
from uuid import UUID

from zebu.application.exceptions import (
    MarketDataUnavailableError,
    TickerNotFoundError,
)
from zebu.application.ports.earnings_calendar_port import EarningsCalendarPort
from zebu.application.ports.market_data_port import MarketDataPort
from zebu.application.ports.portfolio_repository import PortfolioRepository
from zebu.application.ports.strategy_activation_repository import (
    StrategyActivationRepository,
)
from zebu.application.ports.strategy_repository import StrategyRepository
from zebu.application.ports.transaction_repository import TransactionRepository
from zebu.application.ports.trigger_repository import TriggerRepository
from zebu.application.services.trigger_evaluators.drawdown import (
    DrawdownEvaluationData,
    DrawdownEvaluatorInput,
    PortfolioValuePoint,
    evaluate_drawdown,
    lookback_window,
)
from zebu.application.services.trigger_evaluators.earnings_proximity import (
    EarningsEvaluationData,
    EarningsEvaluatorInput,
    evaluate_earnings_proximity,
)
from zebu.application.services.trigger_evaluators.volatility_spike import (
    TickerClose,
    VolatilityEvaluationData,
    VolatilityEvaluatorInput,
    evaluate_volatility_spike,
    volatility_window,
)
from zebu.application.services.trigger_invocation_orchestrator import (
    TriggerInvocationOrchestrator,
)
from zebu.domain.entities.strategy_activation import StrategyActivation
from zebu.domain.entities.strategy_condition_trigger import StrategyConditionTrigger
from zebu.domain.entities.transaction import Transaction
from zebu.domain.services.portfolio_calculator import PortfolioCalculator
from zebu.domain.value_objects.money import Money
from zebu.domain.value_objects.price_point import PricePoint
from zebu.domain.value_objects.ticker import Ticker
from zebu.domain.value_objects.trigger_condition import (
    ConditionType,
    DrawdownMetric,
    DrawdownParams,
    EarningsParams,
    VolatilityParams,
)

# Discriminated-union of the per-condition evaluation-data shapes.
# Used on :class:`TriggerEvaluationResult` so a single result envelope
# can carry the snapshot for any evaluator. Adding a new condition
# type extends this union plus the dispatch arm in ``_evaluate_one``.
type EvaluationData = (
    DrawdownEvaluationData | VolatilityEvaluationData | EarningsEvaluationData
)

logger = logging.getLogger(__name__)


# Feature flag — when False, the evaluator stops at "would fire" and
# does NOT hand off to the orchestrator (matches F-2 behaviour). When
# True (and an orchestrator is supplied), the orchestrator fires for
# real, the agent is invoked, and a TriggerFireRecord is written.
#
# Default False so this PR is safe to merge in production. Flip on when
# Tim is ready (env var `ZEBU_TRIGGER_FIRES_ENABLED=true` on the API
# container).
_FIRES_ENABLED_ENV: str = "ZEBU_TRIGGER_FIRES_ENABLED"


def _fires_enabled() -> bool:
    """Read the feature flag from env. Defaults to False if unset.

    Truthy values: ``true``, ``1``, ``yes`` (case-insensitive).
    Anything else is false.
    """
    value = os.environ.get(_FIRES_ENABLED_ENV, "").strip().lower()
    return value in {"true", "1", "yes"}


class TriggerEvaluationResult(TypedDict):
    """Per-trigger result returned by :meth:`TriggerEvaluationService.evaluate_all`.

    F-2 returned these for any trigger that *would* fire. F-3 extends
    the envelope: when the orchestrator is wired and the feature flag
    is on, ``fire_record_id`` and ``decision`` carry the audit-row
    pointer + the agent's post-guardrail decision.

    Attributes:
        trigger_id: The trigger that was evaluated.
        activation_id: The activation the trigger is attached to.
        fired: True if the condition fired.
        evaluation_data: The condition snapshot (the JSON the eventual
            ``TriggerFireRecord.condition_evaluation_data`` column will
            carry). ``None`` when ``fired`` is False or the evaluator
            could not produce data (insufficient history, etc.).
        error: Per-trigger error message when evaluation raised. The
            service catches and logs; the trigger is reported as
            ``fired=False, error=...`` so a single broken trigger never
            blocks the cycle.
        fire_record_id: F-3 — the :class:`TriggerFireRecord` ID written
            by the orchestrator for this fire. ``None`` when the fire
            path is disabled (feature flag off / no orchestrator) or the
            condition didn't fire.
        decision: F-3 — the post-guardrail decision the orchestrator
            recorded. ``None`` when the orchestrator was not invoked.
            String form (e.g. ``"BUY"``, ``"INVOCATION_FAILED"``) so the
            envelope is JSON-friendly without a custom serialiser.
    """

    trigger_id: UUID
    activation_id: UUID
    fired: bool
    evaluation_data: EvaluationData | None
    error: str | None
    fire_record_id: UUID | None
    decision: str | None


class EvaluationSummary(TypedDict):
    """Aggregate envelope returned by :meth:`evaluate_all`.

    Attributes:
        processed: Number of triggers dispatched (regardless of outcome).
        fired: Triggers whose condition fired.
        failed: Triggers whose evaluation raised.
        skipped: Triggers that were not evaluable at the tick (in
            cooldown, expired, etc.) or whose condition did not fire.
        results: Per-trigger results in evaluation order.
    """

    processed: int
    fired: int
    failed: int
    skipped: int
    results: list[TriggerEvaluationResult]


class TriggerEvaluationService:
    """Live trigger evaluator.

    The scheduler-facing entry point is :meth:`evaluate_all`. Mirrors
    :class:`StrategyExecutionService` (each per-trigger call is wrapped
    in ``try/except`` so one fault never blocks the others; batch-level
    errors propagate so APScheduler logs them).

    Per-trigger flow:

    1. Re-read the trigger and confirm it's still evaluable at ``now()``
       (race with pause / disable mid-tick).
    2. Resolve the activation (used to scope the portfolio + strategy).
    3. Resolve portfolio + transactions for the activation.
    4. Build the per-condition inputs (currently only DRAWDOWN).
    5. Run the pure evaluator function.
    6. Return a result envelope.

    F-2 explicitly does NOT:

    - Invoke an agent (no :class:`AgentInvocationPort` yet — F-3).
    - Persist :class:`TriggerFireRecord` rows (F-3).
    - Call :meth:`StrategyConditionTrigger.record_fire` (F-3).

    The service is testable end-to-end with in-memory adapters — no
    scheduler / DB / network is required for unit tests.
    """

    def __init__(
        self,
        *,
        trigger_repo: TriggerRepository,
        activation_repo: StrategyActivationRepository,
        strategy_repo: StrategyRepository,
        portfolio_repo: PortfolioRepository,
        transaction_repo: TransactionRepository,
        market_data: MarketDataPort,
        earnings_calendar: EarningsCalendarPort,
        earnings_calendar_label: str = "stub",
        orchestrator: TriggerInvocationOrchestrator | None = None,
        fires_enabled_override: bool | None = None,
    ) -> None:
        """Initialise the service with required ports.

        Args:
            trigger_repo: Persistence for :class:`StrategyConditionTrigger`.
                F-2 used this read-only; F-3 mutates it via
                ``record_fire`` after a successful orchestrator invocation
                (the orchestrator owns that write).
            activation_repo: Read-only resolution from the trigger's
                activation_id to the activation entity.
            strategy_repo: Read-only resolution from the activation's
                strategy_id to the strategy entity. Used by both the
                volatility evaluator (resolves the ticker universe) and
                the drawdown evaluator (PER_TICKER mode).
            portfolio_repo: Read-only resolution from the activation's
                portfolio_id to the portfolio entity.
            transaction_repo: Read-only access to the portfolio's
                transaction ledger (drawdown is recomputed from this
                per design Q6).
            market_data: Port for fetching price history (drawdown +
                volatility evaluators).
            earnings_calendar: Port for fetching upcoming earnings
                events. F-4 default is the
                :class:`StubEarningsCalendarAdapter` (always returns
                empty) — real source attaches via a third-party MCP at
                runtime per design Q5.
            earnings_calendar_label: String identifier for the
                earnings calendar source. Echoed into
                :class:`EarningsEvaluationData.source` for the audit
                row. Defaults to ``"stub"``; production wiring should
                pass a more specific label (e.g. ``"brave_mcp"``).
            orchestrator: F-3 — the
                :class:`TriggerInvocationOrchestrator`. When ``None``,
                the service stops at "would fire" results (F-2 behavior;
                useful for tests or when fires are disabled by ops).
                When provided AND the feature flag is on, the service
                hands off every fire-eligible result to the orchestrator.
            fires_enabled_override: F-3 — explicit override for the
                ``ZEBU_TRIGGER_FIRES_ENABLED`` env var. Tests pass
                ``True`` to exercise the orchestrator path without
                touching env state. Production leaves this ``None`` so
                the env var controls behavior.
        """
        self._trigger_repo = trigger_repo
        self._activation_repo = activation_repo
        self._strategy_repo = strategy_repo
        self._portfolio_repo = portfolio_repo
        self._transaction_repo = transaction_repo
        self._market_data = market_data
        self._earnings_calendar = earnings_calendar
        self._earnings_calendar_label = earnings_calendar_label
        self._orchestrator = orchestrator
        self._fires_enabled_override = fires_enabled_override

    async def evaluate_all(self) -> EvaluationSummary:
        """Run one evaluation cycle for every evaluable trigger.

        Each trigger is processed independently. Any exception inside a
        single trigger evaluation is captured on the result envelope as
        ``error=str(exc)`` and the loop moves on. The summary returned
        here is what the scheduler logs.

        Returns:
            :class:`EvaluationSummary` with per-trigger results and
            roll-up counts.
        """
        candidates = await self._trigger_repo.list_evaluable()
        now = datetime.now(UTC)

        # Re-check ``is_evaluable`` here — the repo only filters by
        # status; the cooldown / expiry check requires ``now()``.
        evaluable = [t for t in candidates if t.is_evaluable(at=now)]
        skipped_for_cooldown = len(candidates) - len(evaluable)

        logger.info(
            "Trigger evaluation cycle starting",
            extra={
                "candidates": len(candidates),
                "evaluable": len(evaluable),
                "in_cooldown_or_expired": skipped_for_cooldown,
            },
        )

        results: list[TriggerEvaluationResult] = []
        fired = 0
        failed = 0
        skipped = skipped_for_cooldown

        for trigger in evaluable:
            result = await self._safe_evaluate_one(trigger, now=now)
            results.append(result)
            if result["error"] is not None:
                failed += 1
            elif result["fired"]:
                fired += 1
            else:
                skipped += 1

        summary: EvaluationSummary = {
            "processed": len(evaluable),
            "fired": fired,
            "failed": failed,
            "skipped": skipped,
            "results": results,
        }
        logger.info(
            "Trigger evaluation cycle complete",
            extra={
                "processed": summary["processed"],
                "fired": summary["fired"],
                "failed": summary["failed"],
                "skipped": summary["skipped"],
            },
        )
        return summary

    async def _safe_evaluate_one(
        self,
        trigger: StrategyConditionTrigger,
        *,
        now: datetime,
    ) -> TriggerEvaluationResult:
        """Evaluate one trigger, capturing any exception on the result.

        On a fire-eligible result, hand off to the orchestrator if
        present and the feature flag is on. The handoff is wrapped in
        its own try/except: an orchestrator failure must NOT crash the
        evaluation cycle (the orchestrator already turns its own
        failures into INVOCATION_FAILED audit rows, but defense in
        depth here keeps the service contract intact even if the
        orchestrator raises unexpectedly).

        Args:
            trigger: The trigger to evaluate.
            now: Reference timestamp for window construction.

        Returns:
            Per-trigger result envelope.
        """
        try:
            fired, data = await self._evaluate_one(trigger, now=now)
        except Exception as exc:
            # Broad except is intentional: one bad trigger must never
            # crash the cycle. The error is logged with a stack trace
            # and recorded on the result envelope. F-3 layers an
            # additional ``INVOCATION_FAILED`` audit row when the
            # failure happens after the fire decision; pre-fire failures
            # (resolution issues) stop here without an audit row since
            # the upstream evaluator path didn't claim a fire.
            logger.exception(
                "Trigger evaluation failed",
                extra={
                    "trigger_id": str(trigger.id),
                    "activation_id": str(trigger.activation_id),
                    "condition_type": trigger.condition_type.value,
                },
            )
            return {
                "trigger_id": trigger.id,
                "activation_id": trigger.activation_id,
                "fired": False,
                "evaluation_data": None,
                "error": str(exc),
                "fire_record_id": None,
                "decision": None,
            }

        if not fired:
            return {
                "trigger_id": trigger.id,
                "activation_id": trigger.activation_id,
                "fired": False,
                "evaluation_data": None,
                "error": None,
                "fire_record_id": None,
                "decision": None,
            }

        # Fire path: optionally hand off to the orchestrator.
        fire_record_id, decision_str, error = await self._maybe_orchestrate(
            trigger=trigger, evaluation_data=data
        )
        return {
            "trigger_id": trigger.id,
            "activation_id": trigger.activation_id,
            "fired": True,
            "evaluation_data": data,
            "error": error,
            "fire_record_id": fire_record_id,
            "decision": decision_str,
        }

    async def _maybe_orchestrate(
        self,
        *,
        trigger: StrategyConditionTrigger,
        evaluation_data: EvaluationData | None,
    ) -> tuple[UUID | None, str | None, str | None]:
        """Optionally delegate to the orchestrator on a fire.

        Returns ``(fire_record_id, decision_str, error)``. When the
        orchestrator is not wired or the feature flag is off, returns
        ``(None, None, None)`` — F-2-compatible behavior.

        Args:
            trigger: The trigger that fired.
            evaluation_data: The condition snapshot (becomes
                ``TriggerFireRecord.condition_evaluation_data``).
        """
        if self._orchestrator is None:
            return None, None, None

        # Defensive: even if the orchestrator is wired, respect the
        # feature flag. Override (for tests) wins over env var.
        enabled = (
            self._fires_enabled_override
            if self._fires_enabled_override is not None
            else _fires_enabled()
        )
        if not enabled:
            return None, None, None

        if evaluation_data is None:
            # Should not happen on a fire — defensive only.
            return None, None, "fire reported without evaluation_data"

        try:
            outcome = await self._orchestrator.fire(
                trigger=trigger,
                evaluation_data=evaluation_data,
            )
        except Exception as exc:
            # Defense-in-depth: the orchestrator should already catch
            # everything, but if it raises, we don't crash the cycle.
            logger.exception(
                "Trigger orchestrator raised unexpectedly",
                extra={
                    "trigger_id": str(trigger.id),
                    "activation_id": str(trigger.activation_id),
                },
            )
            return None, None, f"orchestrator raised: {exc}"

        return outcome.fire_record_id, outcome.decision.value, outcome.error

    async def _evaluate_one(
        self,
        trigger: StrategyConditionTrigger,
        *,
        now: datetime,
    ) -> tuple[bool, EvaluationData | None]:
        """Resolve inputs and dispatch to the right per-condition evaluator.

        F-4 handles all three concrete condition types (DRAWDOWN_THRESHOLD,
        VOLATILITY_SPIKE, EARNINGS_PROXIMITY). ``CUSTOM_RULE`` raises
        :class:`NotImplementedError` — caller catches and surfaces it
        as a per-trigger error so the cycle keeps moving. Per design
        Q1, CUSTOM_RULE is deferred indefinitely (predicate evaluation
        is its own design problem).

        Args:
            trigger: The trigger to evaluate.
            now: Reference timestamp for window construction.

        Returns:
            ``(fired, evaluation_data)`` from the per-condition evaluator.

        Raises:
            ValueError: When the activation / portfolio referenced by
                the trigger no longer exists (caught by
                :meth:`_safe_evaluate_one`).
            NotImplementedError: When the trigger's condition type is
                ``CUSTOM_RULE`` (intentionally unimplemented per
                Phase F design Q1).
        """
        activation = await self._activation_repo.get(trigger.activation_id)
        if activation is None:
            raise ValueError(
                f"Activation not found for trigger {trigger.id}: "
                f"{trigger.activation_id}"
            )

        match trigger.condition_type:
            case ConditionType.DRAWDOWN_THRESHOLD:
                # The condition_params discriminator-match invariant on
                # the entity guarantees this isinstance check.
                if not isinstance(trigger.condition_params, DrawdownParams):
                    raise ValueError(
                        f"Trigger {trigger.id} has DRAWDOWN_THRESHOLD type "
                        f"but condition_params is "
                        f"{type(trigger.condition_params).__name__}"
                    )
                return await self._evaluate_drawdown(
                    trigger=trigger,
                    activation=activation,
                    params=trigger.condition_params,
                    now=now,
                )
            case ConditionType.VOLATILITY_SPIKE:
                if not isinstance(trigger.condition_params, VolatilityParams):
                    raise ValueError(
                        f"Trigger {trigger.id} has VOLATILITY_SPIKE type "
                        f"but condition_params is "
                        f"{type(trigger.condition_params).__name__}"
                    )
                return await self._evaluate_volatility_spike(
                    trigger=trigger,
                    activation=activation,
                    params=trigger.condition_params,
                    now=now,
                )
            case ConditionType.EARNINGS_PROXIMITY:
                if not isinstance(trigger.condition_params, EarningsParams):
                    raise ValueError(
                        f"Trigger {trigger.id} has EARNINGS_PROXIMITY type "
                        f"but condition_params is "
                        f"{type(trigger.condition_params).__name__}"
                    )
                return await self._evaluate_earnings_proximity(
                    trigger=trigger,
                    activation=activation,
                    params=trigger.condition_params,
                    now=now,
                )
            case ConditionType.CUSTOM_RULE:
                raise NotImplementedError(
                    f"Condition type {trigger.condition_type.value} is not "
                    "supported (CUSTOM_RULE is deferred per Phase F "
                    "design Q1 — predicate evaluation needs its own "
                    "design pass)."
                )

    async def _evaluate_drawdown(
        self,
        *,
        trigger: StrategyConditionTrigger,
        activation: StrategyActivation,
        params: DrawdownParams,
        now: datetime,
    ) -> tuple[bool, DrawdownEvaluationData | None]:
        """Build the drawdown inputs from the ledger + market data.

        Branches on :attr:`DrawdownParams.metric`:

        - ``PORTFOLIO_TOTAL`` — walks the ledger to compute end-of-day
          portfolio value (cash + holdings * close price) for every day
          inside the lookback window, then a final "now" point using
          current prices.
        - ``PER_TICKER`` — fetches one price-history series per ticker
          (the ticker's drawdown from its window peak is the natural
          per-ticker drawdown definition; holdings don't enter the
          computation since the user wants "tell me if any ticker
          cracks N% from peak" regardless of position size).
        """
        portfolio = await self._portfolio_repo.get(activation.portfolio_id)
        if portfolio is None:
            raise ValueError(
                f"Portfolio not found for trigger {trigger.id}: "
                f"{activation.portfolio_id}"
            )

        window_start, window_end = lookback_window(
            now=now, lookback_days=params.lookback_days
        )

        if params.metric is DrawdownMetric.PORTFOLIO_TOTAL:
            evaluator_input = await self._build_portfolio_total_input(
                portfolio_id=portfolio.id,
                strategy_id=activation.strategy_id,
                window_start=window_start,
                window_end=window_end,
                now=now,
            )
            inputs: list[DrawdownEvaluatorInput] = (
                [evaluator_input] if evaluator_input is not None else []
            )
        else:
            inputs = await self._build_per_ticker_inputs(
                strategy_id=activation.strategy_id,
                window_start=window_start,
                window_end=window_end,
            )

        return evaluate_drawdown(params=params, inputs=inputs)

    async def _evaluate_volatility_spike(
        self,
        *,
        trigger: StrategyConditionTrigger,
        activation: StrategyActivation,
        params: VolatilityParams,
        now: datetime,
    ) -> tuple[bool, VolatilityEvaluationData | None]:
        """Build volatility inputs from market data + dispatch the evaluator.

        Resolves the ticker universe (the ``params.tickers`` subset
        when set, otherwise the strategy's ticker list), fetches each
        ticker's daily-close history for ``params.over_days``, and
        forwards to :func:`evaluate_volatility_spike`.

        The evaluator's "fire if any ticker exceeds threshold"
        semantics short-circuit on the first hit; the composer's
        ordering is the strategy's ticker list (or the explicit subset)
        in user-supplied order, with ``Ticker`` symbols sorted to keep
        the choice deterministic across runs.
        """
        del trigger  # accepted for symmetry with sibling methods
        tickers = await self._resolve_universe_tickers(
            strategy_id=activation.strategy_id,
            params_tickers=params.tickers,
        )
        if not tickers:
            return False, None

        window_start, window_end = volatility_window(
            now=now, over_days=params.over_days
        )
        history_by_ticker = await self._fetch_price_history_for_window(
            tickers=tickers, start=window_start, end=window_end
        )

        inputs: list[VolatilityEvaluatorInput] = []
        for ticker in tickers:
            history = history_by_ticker.get(ticker.symbol, [])
            if not history:
                continue
            closes = tuple(
                TickerClose(
                    observed_at=point.timestamp,
                    close=(
                        point.close.amount
                        if point.close is not None
                        else point.price.amount
                    ),
                )
                for point in history
            )
            inputs.append(
                VolatilityEvaluatorInput(
                    ticker=ticker.symbol,
                    closes=closes,
                    window_start=window_start,
                    window_end=window_end,
                )
            )

        return evaluate_volatility_spike(params=params, inputs=inputs)

    async def _evaluate_earnings_proximity(
        self,
        *,
        trigger: StrategyConditionTrigger,
        activation: StrategyActivation,
        params: EarningsParams,
        now: datetime,
    ) -> tuple[bool, EarningsEvaluationData | None]:
        """Resolve the ticker universe and dispatch the earnings evaluator.

        With the F-4 default :class:`StubEarningsCalendarAdapter` the
        evaluator never fires (the adapter returns ``[]``); attaching
        a real source via DI flips this on without touching the
        evaluator. Per design Q5 the upstream-source decision (Brave /
        Tavily / dedicated feed) is deferred to a follow-up.
        """
        del trigger  # accepted for symmetry with sibling methods
        tickers = await self._resolve_universe_tickers(
            strategy_id=activation.strategy_id,
            params_tickers=params.tickers,
        )
        if not tickers:
            return False, None

        ticker_symbols = [t.symbol for t in tickers]
        evaluator_input = EarningsEvaluatorInput(
            tickers=ticker_symbols,
            now=now,
        )
        return await evaluate_earnings_proximity(
            params=params,
            inputs=evaluator_input,
            earnings_calendar=self._earnings_calendar,
            source_label=self._earnings_calendar_label,
        )

    async def _resolve_universe_tickers(
        self,
        *,
        strategy_id: UUID,
        params_tickers: list[Ticker] | None,
    ) -> list[Ticker]:
        """Resolve the ticker universe to evaluate against.

        - When ``params_tickers`` is set: use it verbatim. The API
          layer is responsible for ensuring it's a subset of the
          strategy's tickers; here we trust the persisted entity.
        - When ``params_tickers`` is None: resolve from the strategy.
          A missing strategy returns ``[]`` — the evaluator will
          short-circuit to no-fire, which is the safe default for a
          stale activation pointing at a deleted strategy.

        Tickers are sorted alphabetically so the "first hit"
        short-circuit is deterministic across runs.
        """
        if params_tickers is not None:
            return sorted(params_tickers, key=lambda t: t.symbol)

        strategy = await self._strategy_repo.get(strategy_id)
        if strategy is None:
            return []
        return [Ticker(symbol) for symbol in sorted(strategy.tickers)]

    async def _build_portfolio_total_input(
        self,
        *,
        portfolio_id: UUID,
        strategy_id: UUID,
        window_start: datetime,
        window_end: datetime,
        now: datetime,
    ) -> DrawdownEvaluatorInput | None:
        """Construct a single PortfolioValuePoint series for PORTFOLIO_TOTAL.

        Walks the transaction ledger and computes end-of-day portfolio
        value at every day in the window where the ledger has data, plus
        a final intraday point at ``now``. Returns ``None`` if the
        ledger is empty (a portfolio that's never traded has no
        meaningful drawdown).

        Args:
            portfolio_id: Portfolio whose value series to build.
            strategy_id: Strategy used to constrain the ticker universe
                we need historical prices for.
            window_start: Earliest observation timestamp.
            window_end: Latest observation timestamp.
            now: Reference timestamp for the final "current" point.

        Returns:
            :class:`DrawdownEvaluatorInput` or ``None`` if no value
            points could be computed.
        """
        transactions = await self._transaction_repo.get_by_portfolio(portfolio_id)
        if not transactions:
            return None

        strategy = await self._strategy_repo.get(strategy_id)
        if strategy is None:
            # Without a strategy we can't resolve which tickers to
            # price — drop this input and let the evaluator return
            # (False, None).
            return None

        relevant_tickers = self._collect_relevant_tickers(
            transactions, strategy.tickers
        )
        price_history_by_ticker = await self._fetch_price_history_for_window(
            tickers=relevant_tickers,
            start=window_start,
            end=window_end,
        )

        # Daily series. Walk one day at a time across the window — at
        # each step compute end-of-day cash + holdings * close-price.
        value_points: list[PortfolioValuePoint] = []
        cursor = window_start
        one_day = timedelta(days=1)
        while cursor <= window_end:
            day_end_value = self._compute_value_at(
                transactions=transactions,
                cutoff=cursor,
                price_history_by_ticker=price_history_by_ticker,
            )
            if day_end_value is not None:
                value_points.append(
                    PortfolioValuePoint(
                        observed_at=cursor,
                        value=day_end_value,
                    )
                )
            cursor += one_day

        # Final intraday point — uses current prices per ticker, not
        # historical. The drawdown spec calls for "intraday-fresh"
        # state; the current price is the freshest signal we have.
        current_value = await self._compute_current_value(
            transactions=transactions,
            tickers=relevant_tickers,
            now=now,
        )
        if current_value is not None:
            value_points.append(
                PortfolioValuePoint(
                    observed_at=now,
                    value=current_value,
                )
            )

        if not value_points:
            return None

        return DrawdownEvaluatorInput(
            ticker=None,
            value_points=tuple(value_points),
            lookback_window_start=window_start,
            lookback_window_end=window_end,
        )

    async def _build_per_ticker_inputs(
        self,
        *,
        strategy_id: UUID,
        window_start: datetime,
        window_end: datetime,
    ) -> list[DrawdownEvaluatorInput]:
        """Construct one DrawdownEvaluatorInput per strategy ticker.

        Each input is the ticker's price history; "value" in the
        :class:`PortfolioValuePoint` is the closing price for that day
        (or ``price_point.price`` when the historical row has no
        ``close``).

        Args:
            strategy_id: Strategy whose ticker universe to evaluate.
            window_start: Earliest observation timestamp.
            window_end: Latest observation timestamp.

        Returns:
            List of inputs, one per ticker whose history could be
            fetched. Tickers with no historical data are silently
            dropped (the trigger wouldn't fire on them anyway —
            insufficient history).
        """
        strategy = await self._strategy_repo.get(strategy_id)
        if strategy is None:
            return []

        tickers = [Ticker(symbol) for symbol in strategy.tickers]
        history_by_ticker = await self._fetch_price_history_for_window(
            tickers=tickers,
            start=window_start,
            end=window_end,
        )

        inputs: list[DrawdownEvaluatorInput] = []
        for ticker in tickers:
            history = history_by_ticker.get(ticker.symbol, [])
            if not history:
                continue
            value_points = tuple(
                PortfolioValuePoint(
                    observed_at=point.timestamp,
                    value=(
                        point.close.amount
                        if point.close is not None
                        else point.price.amount
                    ),
                )
                for point in history
            )
            inputs.append(
                DrawdownEvaluatorInput(
                    ticker=ticker.symbol,
                    value_points=value_points,
                    lookback_window_start=window_start,
                    lookback_window_end=window_end,
                )
            )

        return inputs

    def _collect_relevant_tickers(
        self,
        transactions: list[Transaction],
        strategy_tickers: list[str],
    ) -> list[Ticker]:
        """Tickers we need historical prices for to compute portfolio value.

        Includes every strategy ticker plus every ticker in the
        transaction ledger (a portfolio may hold positions in tickers
        that aren't part of the *current* strategy because the strategy
        was edited mid-flight).
        """
        ticker_set: set[str] = set(strategy_tickers)
        for transaction in transactions:
            if transaction.ticker is not None:
                ticker_set.add(transaction.ticker.symbol)
        return [Ticker(symbol) for symbol in sorted(ticker_set)]

    async def _fetch_price_history_for_window(
        self,
        *,
        tickers: list[Ticker],
        start: datetime,
        end: datetime,
    ) -> dict[str, list[PricePoint]]:
        """Fetch each ticker's price history once for the window.

        Returns a dict keyed by ticker symbol so callers can index
        by symbol without re-importing :class:`Ticker`. Missing /
        unavailable tickers are silently dropped (logged at WARNING) —
        the same semantics :class:`StrategyExecutionService` uses for
        live prices.

        Args:
            tickers: Tickers whose history to fetch.
            start: Earliest timestamp (UTC).
            end: Latest timestamp (UTC).

        Returns:
            Dict mapping ticker symbol -> chronological list of
            :class:`PricePoint`. Tickers without any data are absent.
        """
        history: dict[str, list[PricePoint]] = {}
        for ticker in tickers:
            try:
                points = await self._market_data.get_price_history(
                    ticker, start=start, end=end, interval="1day"
                )
            except (TickerNotFoundError, MarketDataUnavailableError) as exc:
                logger.warning(
                    "No price history available for ticker — skipping",
                    extra={"ticker": ticker.symbol, "reason": str(exc)},
                )
                continue
            history[ticker.symbol] = points
        return history

    def _compute_value_at(
        self,
        *,
        transactions: list[Transaction],
        cutoff: datetime,
        price_history_by_ticker: dict[str, list[PricePoint]],
    ) -> Decimal | None:
        """End-of-day portfolio value at ``cutoff``.

        Walks the ledger, keeps only transactions ``<= cutoff``, and
        computes cash + holdings * day-close-price. Returns ``None``
        when the ledger has no entries up to that point (the portfolio
        didn't exist as a position-holding entity yet).
        """
        prior_txns = [t for t in transactions if t.timestamp <= cutoff]
        if not prior_txns:
            return None

        cash = PortfolioCalculator.calculate_cash_balance(prior_txns)
        holdings = PortfolioCalculator.calculate_holdings(prior_txns)

        # Build a single-day price map: ticker -> Money(close on cutoff).
        cutoff_date = cutoff.date()
        price_for_day: dict[Ticker, Money] = {}
        for holding in holdings:
            symbol = holding.ticker.symbol
            history = price_history_by_ticker.get(symbol, [])
            close = self._closest_close_on_or_before(
                points=history, cutoff_date=cutoff_date
            )
            if close is not None:
                price_for_day[holding.ticker] = close

        # If no holdings have prices but holdings exist, the value is
        # incomplete — return None so the day is skipped (better than
        # mis-stating the value as cash-only).
        if holdings and not price_for_day:
            return None

        priced_holdings = [h for h in holdings if h.ticker in price_for_day]
        holdings_value = PortfolioCalculator.calculate_portfolio_value(
            holdings=priced_holdings, prices=price_for_day
        )
        return PortfolioCalculator.calculate_total_value(
            cash_balance=cash, holdings_value=holdings_value
        ).amount

    @staticmethod
    def _closest_close_on_or_before(
        *,
        points: list[PricePoint],
        cutoff_date: date,
    ) -> Money | None:
        """Pick the close price of the most recent day at or before cutoff."""
        best: PricePoint | None = None
        for point in points:
            if point.timestamp.date() > cutoff_date:
                continue
            if best is None or point.timestamp > best.timestamp:
                best = point
        if best is None:
            return None
        return best.close if best.close is not None else best.price

    async def _compute_current_value(
        self,
        *,
        transactions: list[Transaction],
        tickers: list[Ticker],
        now: datetime,
    ) -> Decimal | None:
        """Intraday portfolio value at ``now`` using fresh prices.

        Mirrors :meth:`StrategyExecutionService._fetch_price_map` —
        each ticker's current price (``get_current_price``) is the
        freshest available signal.

        Args:
            transactions: Full ledger.
            tickers: Tickers to fetch current prices for.
            now: Reference timestamp (used in caller to label the
                resulting :class:`PortfolioValuePoint`; not used here
                for any computation).

        Returns:
            Total portfolio value (cash + holdings * current price), or
            ``None`` when the ledger is empty.
        """
        del now  # accepted for caller-readability symmetry only
        if not transactions:
            return None

        cash = PortfolioCalculator.calculate_cash_balance(transactions)
        holdings = PortfolioCalculator.calculate_holdings(transactions)

        prices: dict[Ticker, Money] = {}
        for ticker in tickers:
            try:
                price_point = await self._market_data.get_current_price(ticker)
            except (TickerNotFoundError, MarketDataUnavailableError) as exc:
                logger.debug(
                    "No current price available — excluding ticker from now-value",
                    extra={"ticker": ticker.symbol, "reason": str(exc)},
                )
                continue
            prices[ticker] = price_point.price

        if holdings and not prices:
            # Same logic as ``_compute_value_at``: don't mis-state value.
            return None

        priced_holdings = [h for h in holdings if h.ticker in prices]
        holdings_value = PortfolioCalculator.calculate_portfolio_value(
            holdings=priced_holdings, prices=prices
        )
        return PortfolioCalculator.calculate_total_value(
            cash_balance=cash, holdings_value=holdings_value
        ).amount


__all__ = [
    "EvaluationSummary",
    "TriggerEvaluationResult",
    "TriggerEvaluationService",
]
