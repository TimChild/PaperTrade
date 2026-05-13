"""Trigger invocation orchestrator — Phase F-3.

The orchestrator turns a fired-trigger evaluation result into:

1. An :class:`AgentInvocationPort` call (the agent decides what to do).
2. A side effect (paper trade, strategy modification, exploration task,
   or a no-op for HOLD / failure).
3. A :class:`TriggerFireRecord` audit row capturing the full chain.

This is the load-bearing class of Phase F-3. The trigger evaluator
hands off to the orchestrator on every fire-eligible trigger, and the
orchestrator owns the agent prompt construction, the decision parsing,
the per-decision execution, and the audit record write.

References:
- ``docs/architecture/phase-f-agent-in-the-loop.md`` §3 (agent-decision
  flow with mermaid sequence), §3.4 (prompt assembly), §3.5
  (decision execution), §4 (auth + identity).
- :class:`AgentInvocationPort` for the agent boundary.
- :class:`TriggerEvaluationService` for the upstream caller.

Domain rules enforced here (vs in the entity):
- Decision-execution side effects (BUY/SELL → trade, MODIFY → strategy
  update, NEEDS_HUMAN → ExplorationTask) — these are I/O-bound use
  cases, hence application-layer.
- Prompt assembly — the deterministic "system + user" message
  construction that goes to Anthropic. Tests assert structural
  properties (sections present, agent_prompt verbatim) rather than
  fixture-matching exact text (which would drift).
- API-key resolution for trade attribution — see §4.1: priority list
  is `default_api_key_id` → most-recently-used trade-scoped key for
  the activation owner. F-3 does NOT auto-pause when no key is
  available — the orchestrator records INVOCATION_FAILED so the
  activity feed shows the failure; auto-pause is F-5.
"""

import logging
import time
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import TypedDict
from uuid import UUID, uuid4

from zebu.application.ports.agent_invocation_port import (
    AgentInvocationPort,
    AgentInvocationResult,
)
from zebu.application.ports.api_key_repository import ApiKeyRepository
from zebu.application.ports.exploration_task_repository import (
    ExplorationTaskRepository,
)
from zebu.application.ports.market_data_port import MarketDataPort
from zebu.application.ports.portfolio_cap_port import PortfolioCapPort
from zebu.application.ports.portfolio_repository import PortfolioRepository
from zebu.application.ports.strategy_activation_repository import (
    StrategyActivationRepository,
)
from zebu.application.ports.strategy_repository import StrategyRepository
from zebu.application.ports.transaction_repository import TransactionRepository
from zebu.application.ports.trigger_fire_repository import TriggerFireRepository
from zebu.application.ports.trigger_repository import TriggerRepository
from zebu.application.services.backtest_transaction_builder import (
    BacktestTransactionBuilder,
)
from zebu.application.services.trigger_evaluators.drawdown import (
    DrawdownEvaluationData,
)
from zebu.domain.entities.api_key import ApiKey
from zebu.domain.entities.exploration_task import (
    ExplorationTask,
    ExplorationTaskStatus,
)
from zebu.domain.entities.strategy import Strategy
from zebu.domain.entities.strategy_activation import StrategyActivation
from zebu.domain.entities.strategy_condition_trigger import StrategyConditionTrigger
from zebu.domain.entities.trigger_fire_record import TriggerFireRecord
from zebu.domain.exceptions import (
    AgentInvocationError,
    AgentResponseParseError,
    InvalidStrategyError,
)
from zebu.domain.services.portfolio_calculator import PortfolioCalculator
from zebu.domain.value_objects.agent_decision import AgentDecision
from zebu.domain.value_objects.api_key_scope import ApiKeyScope
from zebu.domain.value_objects.money import Money
from zebu.domain.value_objects.quantity import Quantity
from zebu.domain.value_objects.strategy_parameters import (
    BuyAndHoldParameters,
    DcaParameters,
    MaCrossoverParameters,
    StrategyParameters,
    parameters_from_dict,
)
from zebu.domain.value_objects.strategy_type import StrategyType
from zebu.domain.value_objects.ticker import Ticker
from zebu.domain.value_objects.trade_signal import TradeAction, TradeSignal
from zebu.domain.value_objects.trigger_invocation_mode import TriggerInvocationMode

logger = logging.getLogger(__name__)


# Truncation cap for agent_response_raw on the audit row. Matches the
# entity-level limit in :class:`TriggerFireRecord`.
_AGENT_RAW_TRUNCATE: int = 8000

# Forbidden keys in MODIFY_STRATEGY parameter overrides (§3.5 of the
# design — the asset universe is a security boundary).
_MODIFY_FORBIDDEN_KEYS: frozenset[str] = frozenset({"tickers"})


@dataclass(frozen=True)
class FireOutcome:
    """The result of running the orchestrator over one trigger fire.

    Returned to :class:`TriggerEvaluationService.evaluate_all` so the
    cycle summary can report what each fire ended up doing. The audit
    row is the durable record; this is the in-memory reply.

    Attributes:
        trigger_id: The trigger that fired.
        fire_record_id: The :class:`TriggerFireRecord` written for this
            fire. Always populated — every fire writes an audit row,
            even on INVOCATION_FAILED.
        decision: The post-guardrail decision recorded.
        latency_ms: End-to-end latency from "evaluator handed off" to
            "fire record persisted".
        error: Human-readable error if the path took the
            INVOCATION_FAILED branch. ``None`` on the happy path.
    """

    trigger_id: UUID
    fire_record_id: UUID
    decision: AgentDecision
    latency_ms: int
    error: str | None


class _DecisionExecutionResult(TypedDict):
    """Internal envelope returned by the per-decision execution helper.

    All fields are required so the orchestrator can access them
    unconditionally — every helper builds the full envelope.
    """

    decision: AgentDecision
    resulting_trade_id: UUID | None
    resulting_modify_payload: Mapping[str, object] | None
    resulting_exploration_task_id: UUID | None
    notes: str
    error: str | None


class TriggerInvocationOrchestrator:
    """Wakes the agent on a trigger fire and acts on the decision.

    The orchestrator is the second half of the trigger-fire flow:

    1. :class:`TriggerEvaluationService` decides "this trigger fired".
    2. Orchestrator builds a prompt, calls the agent, parses the
       decision, executes the side effect, writes the audit row, and
       updates the trigger's ``last_fired_at``.

    All I/O is funnelled through ports (no direct DB / HTTP access).
    Error handling: any exception inside :meth:`fire` is caught and
    surfaced as an INVOCATION_FAILED audit row + a non-empty
    :attr:`FireOutcome.error` — the orchestrator never raises out to
    the evaluator (which would crash the cycle for one bad trigger).
    """

    def __init__(
        self,
        *,
        agent_invocation: AgentInvocationPort,
        trigger_repo: TriggerRepository,
        trigger_fire_repo: TriggerFireRepository,
        activation_repo: StrategyActivationRepository,
        strategy_repo: StrategyRepository,
        portfolio_repo: PortfolioRepository,
        transaction_repo: TransactionRepository,
        market_data: MarketDataPort,
        api_key_repo: ApiKeyRepository,
        exploration_task_repo: ExplorationTaskRepository,
        portfolio_cap: PortfolioCapPort | None = None,
    ) -> None:
        """Initialise the orchestrator with required ports.

        Args:
            agent_invocation: The :class:`AgentInvocationPort` (Anthropic
                adapter in production, in-memory in tests).
            trigger_repo: Mutates the trigger to record ``last_fired_at``.
            trigger_fire_repo: Append-only audit table.
            activation_repo: Resolve activation from trigger.
            strategy_repo: Resolve + persist (for MODIFY) the strategy.
            portfolio_repo: Resolve portfolio for the activation.
            transaction_repo: Append BUY/SELL transactions.
            market_data: Current price for trade execution.
            api_key_repo: Resolve the API key for trade attribution.
            exploration_task_repo: File NEEDS_HUMAN escalations.
            portfolio_cap: Phase F-6 — optional cap port; when supplied,
                BUY/SELL decisions are gated on the per-portfolio
                per-UTC-day caps before execution. ``None`` disables the
                guardrail (used in legacy tests / dev environments where
                the cap isn't configured). Production deployments wire
                this in.
        """
        self._agent = agent_invocation
        self._trigger_repo = trigger_repo
        self._fire_repo = trigger_fire_repo
        self._activation_repo = activation_repo
        self._strategy_repo = strategy_repo
        self._portfolio_repo = portfolio_repo
        self._transaction_repo = transaction_repo
        self._market_data = market_data
        self._api_key_repo = api_key_repo
        self._task_repo = exploration_task_repo
        self._portfolio_cap = portfolio_cap

    async def fire(
        self,
        *,
        trigger: StrategyConditionTrigger,
        evaluation_data: Mapping[str, object],
    ) -> FireOutcome:
        """Wake the agent and execute its decision.

        See module docstring for the full flow. Single ``try/except`` at
        the top so any failure (resolution, agent call, side effect)
        results in an INVOCATION_FAILED audit row rather than a raise.

        Args:
            trigger: The fire-eligible trigger.
            evaluation_data: Per-condition snapshot (from the F-2
                evaluator). Goes onto the audit row verbatim.

        Returns:
            :class:`FireOutcome` with the audit-record id and decision
            taken.
        """
        start = time.perf_counter()
        fire_id = uuid4()
        fired_at = datetime.now(UTC)

        try:
            return await self._fire_inner(
                trigger=trigger,
                evaluation_data=evaluation_data,
                fire_id=fire_id,
                fired_at=fired_at,
                start=start,
            )
        except Exception as exc:
            # Catch-all: convert any unhandled error into an
            # INVOCATION_FAILED audit row. This is broad-by-design — the
            # orchestrator is the boundary between "evaluator can keep
            # going" and "fire-and-forget side effect path". Logging
            # captures the stack trace.
            logger.exception(
                "Trigger orchestrator failed",
                extra={
                    "trigger_id": str(trigger.id),
                    "activation_id": str(trigger.activation_id),
                },
            )
            latency_ms = int((time.perf_counter() - start) * 1000)
            error_message = f"Orchestrator error: {exc}"
            api_key = await self._resolve_api_key_safe(trigger=trigger)
            if api_key is None:
                # Without an API key we cannot satisfy the audit row's
                # NOT-NULL on api_key_id_used. Surface failure in the
                # outcome only — no audit row.
                return FireOutcome(
                    trigger_id=trigger.id,
                    fire_record_id=fire_id,  # synthetic; row was not written
                    decision=AgentDecision.INVOCATION_FAILED,
                    latency_ms=latency_ms,
                    error=(
                        "No eligible API key for trade attribution; "
                        "audit row could not be persisted. "
                        f"Original error: {error_message}"
                    ),
                )
            await self._write_failure_record(
                trigger=trigger,
                evaluation_data=evaluation_data,
                fire_id=fire_id,
                fired_at=fired_at,
                api_key_id=api_key.id,
                latency_ms=latency_ms,
                error_message=error_message,
                rationale_raw="",
            )
            return FireOutcome(
                trigger_id=trigger.id,
                fire_record_id=fire_id,
                decision=AgentDecision.INVOCATION_FAILED,
                latency_ms=latency_ms,
                error=error_message,
            )

    # ------------------------------------------------------------------ #
    # Inner flow                                                         #
    # ------------------------------------------------------------------ #

    async def _fire_inner(
        self,
        *,
        trigger: StrategyConditionTrigger,
        evaluation_data: Mapping[str, object],
        fire_id: UUID,
        fired_at: datetime,
        start: float,
    ) -> FireOutcome:
        """Resolve, prompt, invoke, execute, persist."""
        # 1. Resolve all referenced entities. Every miss here is a hard
        # failure for this trigger — surface as INVOCATION_FAILED.
        activation = await self._activation_repo.get(trigger.activation_id)
        if activation is None:
            return await self._fail_with_audit(
                trigger=trigger,
                evaluation_data=evaluation_data,
                fire_id=fire_id,
                fired_at=fired_at,
                start=start,
                error_message=(f"Activation {trigger.activation_id} not found"),
            )

        strategy = await self._strategy_repo.get(activation.strategy_id)
        if strategy is None:
            return await self._fail_with_audit(
                trigger=trigger,
                evaluation_data=evaluation_data,
                fire_id=fire_id,
                fired_at=fired_at,
                start=start,
                error_message=(f"Strategy {activation.strategy_id} not found"),
            )

        portfolio = await self._portfolio_repo.get(activation.portfolio_id)
        if portfolio is None:
            return await self._fail_with_audit(
                trigger=trigger,
                evaluation_data=evaluation_data,
                fire_id=fire_id,
                fired_at=fired_at,
                start=start,
                error_message=(f"Portfolio {activation.portfolio_id} not found"),
            )

        # 2. Resolve API key for trade attribution (§4.1).
        api_key = await self._resolve_api_key(trigger=trigger)
        if api_key is None:
            # Per §4.1 fallback (3): no eligible key. F-3 records
            # INVOCATION_FAILED; F-5 may auto-pause the trigger.
            return await self._fail_with_audit(
                trigger=trigger,
                evaluation_data=evaluation_data,
                fire_id=fire_id,
                fired_at=fired_at,
                start=start,
                error_message=(
                    "No eligible trade-scoped API key for the activation "
                    "owner; cannot attribute resulting trade. "
                    "Configure default_api_key_id on the trigger or mint "
                    "a trade-scoped API key."
                ),
            )

        # 2a. Phase J / Task #213 — Pattern B (QUEUE mode).
        #
        # If the trigger is configured for QUEUE invocation, skip the
        # inline Anthropic call entirely and file an URGENT
        # ExplorationTask. The user's desktop Claude / Gemini CLI / any
        # MCP-aware client polls the queue and processes the task with
        # whichever tools and connectors that client already has wired.
        #
        # The audit row is still written (so the activity feed stays
        # coherent) — its ``agent_response`` is NEEDS_HUMAN (the closest
        # AgentDecision value for "the platform handed this off to a
        # human-driven agent loop") and ``resulting_exploration_task_id``
        # points at the queued task. ``agent_response_raw`` carries a
        # short JSON-shaped marker so downstream consumers can detect the
        # queue path without re-reading the trigger row.
        if trigger.mode is TriggerInvocationMode.QUEUE:
            return await self._fire_queue_mode(
                trigger=trigger,
                activation=activation,
                strategy=strategy,
                portfolio_id=portfolio.id,
                evaluation_data=evaluation_data,
                fire_id=fire_id,
                fired_at=fired_at,
                start=start,
                api_key=api_key,
            )

        # 3. Build prompts (deterministic so test assertions are stable).
        transactions = await self._transaction_repo.get_by_portfolio(portfolio.id)
        cash_balance = PortfolioCalculator.calculate_cash_balance(transactions)
        holdings = PortfolioCalculator.calculate_holdings(transactions)

        system_prompt = build_system_prompt()
        user_prompt = build_user_prompt(
            trigger=trigger,
            activation=activation,
            strategy=strategy,
            portfolio_id=portfolio.id,
            cash_balance=cash_balance.amount,
            holdings_summary=[(h.ticker.symbol, h.quantity.shares) for h in holdings],
            evaluation_data=evaluation_data,
        )

        # 4. Invoke the agent.
        try:
            result = await self._agent.invoke(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )
        except (AgentInvocationError, AgentResponseParseError) as exc:
            return await self._fail_with_audit(
                trigger=trigger,
                evaluation_data=evaluation_data,
                fire_id=fire_id,
                fired_at=fired_at,
                start=start,
                error_message=f"Agent invocation failed: {exc}",
                rationale_raw=getattr(exc, "message", str(exc)),
                api_key_override=api_key,
                invocation_id=None,
            )

        # 5. Execute the decision.
        execution = await self._execute_decision(
            result=result,
            trigger=trigger,
            activation=activation,
            strategy=strategy,
            portfolio_id=portfolio.id,
            api_key=api_key,
            fired_at=fired_at,
        )

        # 6. Write the audit row + record_fire on the trigger.
        latency_ms = int((time.perf_counter() - start) * 1000)
        record = TriggerFireRecord(
            id=fire_id,
            trigger_id=trigger.id,
            activation_id=trigger.activation_id,
            fired_at=fired_at,
            condition_evaluation_data=dict(evaluation_data),
            agent_response=execution["decision"],
            agent_response_raw=_truncate(result.rationale),
            latency_ms=latency_ms,
            api_key_id_used=api_key.id,
            agent_invocation_id=result.invocation_id,
            resulting_trade_id=execution.get("resulting_trade_id"),
            resulting_modify_payload=execution.get("resulting_modify_payload"),
            resulting_exploration_task_id=execution.get(
                "resulting_exploration_task_id"
            ),
        )
        await self._fire_repo.save(record)
        await self._trigger_repo.save(trigger.record_fire(fired_at=fired_at))

        logger.info(
            "Trigger fire complete",
            extra={
                "trigger_id": str(trigger.id),
                "activation_id": str(trigger.activation_id),
                "decision": execution["decision"].value,
                "fire_record_id": str(fire_id),
                "latency_ms": latency_ms,
                "model": result.model,
            },
        )

        return FireOutcome(
            trigger_id=trigger.id,
            fire_record_id=fire_id,
            decision=execution["decision"],
            latency_ms=latency_ms,
            error=execution.get("error"),
        )

    # ------------------------------------------------------------------ #
    # Queue-mode (Pattern B) — file an URGENT ExplorationTask            #
    # ------------------------------------------------------------------ #

    async def _fire_queue_mode(
        self,
        *,
        trigger: StrategyConditionTrigger,
        activation: StrategyActivation,
        strategy: Strategy,
        portfolio_id: UUID,
        evaluation_data: Mapping[str, object],
        fire_id: UUID,
        fired_at: datetime,
        start: float,
        api_key: ApiKey,
    ) -> FireOutcome:
        """Queue-mode fire path — file an URGENT ExplorationTask.

        Skips the inline Anthropic invocation entirely. The platform
        writes an :class:`ExplorationTask` row whose prompt begins with
        the :literal:`[URGENT]` marker convention (per
        ``docs/agents/operating-manual.md`` §3.5) so polling agents can
        prioritise it. A :class:`TriggerFireRecord` audit row is still
        appended — its ``resulting_exploration_task_id`` points at the
        queued task so the activity feed renders coherently and the
        trigger's cooldown applies.
        """
        task = await self._file_urgent_exploration_task(
            trigger=trigger,
            activation=activation,
            strategy=strategy,
            portfolio_id=portfolio_id,
            evaluation_data=evaluation_data,
            api_key_id=api_key.id,
            fired_at=fired_at,
        )

        latency_ms = int((time.perf_counter() - start) * 1000)
        # Compact marker in agent_response_raw so consumers (UI, logs)
        # can detect that this fire took the queue path without
        # re-reading the trigger row. The trigger's ``mode`` field on
        # ``TriggerResponse`` is the canonical source — this is the
        # convenience copy on the audit row.
        rationale_raw = f'{{"queued_task_id":"{task.id}","mode":"queue"}}'
        record = TriggerFireRecord(
            id=fire_id,
            trigger_id=trigger.id,
            activation_id=trigger.activation_id,
            fired_at=fired_at,
            condition_evaluation_data=dict(evaluation_data),
            # NEEDS_HUMAN is the AgentDecision that semantically maps to
            # "platform deferred this fire to a human-driven agent." The
            # entity invariants require ``resulting_exploration_task_id``
            # to be set (and the others to be null) for this decision —
            # the queue path satisfies that contract.
            agent_response=AgentDecision.NEEDS_HUMAN,
            agent_response_raw=_truncate(rationale_raw),
            latency_ms=latency_ms,
            api_key_id_used=api_key.id,
            agent_invocation_id=None,
            resulting_exploration_task_id=task.id,
        )
        await self._fire_repo.save(record)
        await self._trigger_repo.save(trigger.record_fire(fired_at=fired_at))

        logger.info(
            "Trigger fire complete (queue mode)",
            extra={
                "trigger_id": str(trigger.id),
                "activation_id": str(trigger.activation_id),
                "fire_record_id": str(fire_id),
                "queued_task_id": str(task.id),
                "latency_ms": latency_ms,
                "mode": trigger.mode.value,
            },
        )

        return FireOutcome(
            trigger_id=trigger.id,
            fire_record_id=fire_id,
            decision=AgentDecision.NEEDS_HUMAN,
            latency_ms=latency_ms,
            error=None,
        )

    async def _file_urgent_exploration_task(
        self,
        *,
        trigger: StrategyConditionTrigger,
        activation: StrategyActivation,
        strategy: Strategy,
        portfolio_id: UUID,
        evaluation_data: Mapping[str, object],
        api_key_id: UUID,
        fired_at: datetime,
    ) -> ExplorationTask:
        """Build + persist an URGENT :class:`ExplorationTask` for a queued fire.

        The task's prompt begins with the ``[URGENT]`` prefix convention
        documented in ``docs/agents/operating-manual.md`` §3.5 so polling
        agents (Claude Desktop / Code / Gemini CLI / etc.) can recognise
        and prioritise it. The body composes the trigger's
        ``agent_prompt`` with the condition's evaluation snapshot so the
        consumer has the full context without round-tripping back to the
        trigger row.

        Returns the persisted task so the caller can stash its id on the
        audit row.
        """
        lines = [
            (
                "[URGENT] [TRIGGER FIRE] Queue-mode trigger fired — "
                "agent action requested."
            ),
            "",
            f"Trigger ID: {trigger.id}",
            f"Activation ID: {trigger.activation_id}",
            f"Strategy: {strategy.name} ({strategy.strategy_type.value})",
            f"Portfolio ID: {portfolio_id}",
            f"Condition type: {trigger.condition_type.value}",
            f"Fired at: {fired_at.isoformat()}",
            "",
            "## Condition snapshot",
        ]
        for key, value in sorted(evaluation_data.items()):
            lines.append(f"- {key}: {value}")
        lines.extend(
            [
                "",
                "## Operator instruction",
                trigger.agent_prompt,
            ]
        )
        prompt = "\n".join(lines)
        # The ExplorationTask entity caps prompt at 4000 chars — truncate
        # defensively so a verbose snapshot doesn't reject the task.
        if len(prompt) > 4000:
            prompt = prompt[:4000]

        task_id = uuid4()
        now = datetime.now(UTC)
        task = ExplorationTask(
            id=task_id,
            created_by=trigger.user_id,
            prompt=prompt,
            status=ExplorationTaskStatus.OPEN,
            created_at=now,
            updated_at=now,
            target_portfolio_id=activation.portfolio_id,
        )
        await self._task_repo.save(task, api_key_id=api_key_id)
        return task

    # ------------------------------------------------------------------ #
    # Decision execution                                                 #
    # ------------------------------------------------------------------ #

    async def _execute_decision(
        self,
        *,
        result: AgentInvocationResult,
        trigger: StrategyConditionTrigger,
        activation: StrategyActivation,
        strategy: Strategy,
        portfolio_id: UUID,
        api_key: ApiKey,
        fired_at: datetime,
    ) -> _DecisionExecutionResult:
        """Apply the agent's decision and return the resulting pointers.

        Each branch may downgrade to HOLD on a guardrail / validation
        failure (e.g. insufficient funds, forbidden parameter override).
        Downgrades record the original decision's notes in the rationale
        so investigators can see what the agent originally wanted.
        """
        match result.decision:
            case AgentDecision.BUY | AgentDecision.SELL:
                return await self._execute_trade(
                    decision=result.decision,
                    payload=result.payload,
                    trigger=trigger,
                    strategy=strategy,
                    portfolio_id=portfolio_id,
                    api_key_id=api_key.id,
                    fired_at=fired_at,
                )
            case AgentDecision.HOLD:
                return {
                    "decision": AgentDecision.HOLD,
                    "resulting_trade_id": None,
                    "resulting_modify_payload": None,
                    "resulting_exploration_task_id": None,
                    "notes": _payload_str(result.payload, "notes"),
                    "error": None,
                }
            case AgentDecision.MODIFY_STRATEGY:
                return await self._execute_modify(
                    payload=result.payload,
                    strategy=strategy,
                    api_key_id=api_key.id,
                )
            case AgentDecision.NEEDS_HUMAN:
                return await self._execute_needs_human(
                    payload=result.payload,
                    rationale=result.rationale,
                    trigger=trigger,
                    activation=activation,
                    api_key_id=api_key.id,
                )
            case (
                AgentDecision.INVOCATION_FAILED
            ):  # pragma: no cover  -- adapter rejects
                return {
                    "decision": AgentDecision.INVOCATION_FAILED,
                    "resulting_trade_id": None,
                    "resulting_modify_payload": None,
                    "resulting_exploration_task_id": None,
                    "notes": "",
                    "error": "Agent emitted INVOCATION_FAILED (system-only)",
                }

    async def _execute_trade(
        self,
        *,
        decision: AgentDecision,
        payload: Mapping[str, object],
        trigger: StrategyConditionTrigger,
        strategy: Strategy,
        portfolio_id: UUID,
        api_key_id: UUID,
        fired_at: datetime,
    ) -> _DecisionExecutionResult:
        """BUY / SELL → build TradeSignal, execute via the live path.

        Mirrors the strategy execution service's signal application so
        the same trade-factory / quantity-resolution invariants apply.
        On any rejection (insufficient funds, missing price, invalid
        ticker, per-portfolio cap exceeded), the decision is downgraded
        to HOLD and the rationale captures the reason.

        Phase F-6:

        - Per-portfolio per-UTC-day cap is checked AFTER the signal has
          built a candidate transaction but BEFORE it's persisted. The
          cap operates on the absolute ``cash_change`` of the candidate
          so the rationale carries an accurate "$X exceeded $Y" message.
        - The resulting transaction is persisted with ``trigger_id`` set
          so the activity feed can join trade back to the fire that
          produced it.
        """
        ticker_str = _payload_str(payload, "ticker")
        if not ticker_str:
            return self._downgrade_to_hold(
                f"{decision.value} missing ticker in payload"
            )

        # Validate ticker is in the strategy universe (security
        # boundary — agent can only trade what the strategy authorises).
        if ticker_str not in strategy.tickers:
            return self._downgrade_to_hold(
                f"{decision.value} {ticker_str} not in strategy ticker "
                f"universe {strategy.tickers}"
            )

        try:
            ticker = Ticker(ticker_str)
        except Exception as exc:
            return self._downgrade_to_hold(
                f"{decision.value} invalid ticker {ticker_str!r}: {exc}"
            )

        # Resolve quantity. None / "" / missing means "default sizing".
        # F-3 default sizing for an agent-driven trade is "let the
        # invest_fraction decide" — but with no signal-generation pass
        # available we need *some* concrete number. Use a sensible
        # baseline: 1 share. The orchestrator is intentionally
        # conservative; the agent can specify quantity if it wants more.
        quantity_str = _payload_str(payload, "quantity")
        try:
            quantity = self._resolve_quantity(quantity_str)
        except (ValueError, InvalidOperation) as exc:
            return self._downgrade_to_hold(
                f"{decision.value} invalid quantity {quantity_str!r}: {exc}"
            )

        try:
            price_point = await self._market_data.get_current_price(ticker)
        except Exception as exc:
            return self._downgrade_to_hold(
                f"{decision.value} could not fetch current price for "
                f"{ticker_str}: {exc}"
            )

        # Build a single-trade transaction via the same
        # BacktestTransactionBuilder the live executor uses (so the
        # invariants are identical).
        builder = BacktestTransactionBuilder(
            portfolio_id=portfolio_id,
            initial_cash=Money(Decimal("0"), "USD"),  # placeholder
        )
        # Seed the builder with the real cash + holdings so signal
        # validation runs against the actual book.
        all_txns = await self._transaction_repo.get_by_portfolio(portfolio_id)
        cash_balance = PortfolioCalculator.calculate_cash_balance(all_txns)
        holdings_list = PortfolioCalculator.calculate_holdings(all_txns)

        builder = BacktestTransactionBuilder(
            portfolio_id=portfolio_id,
            initial_cash=cash_balance,
        )
        seed = {h.ticker: h.quantity for h in holdings_list if h.quantity.shares > 0}
        if seed:
            builder.seed_holdings(seed)

        action = TradeAction.BUY if decision is AgentDecision.BUY else TradeAction.SELL
        signal = TradeSignal(
            action=action,
            ticker=ticker,
            signal_date=fired_at.date(),
            quantity=quantity,
        )
        try:
            applied = builder.apply_signal(
                signal=signal,
                price_per_share=price_point.price,
                timestamp=fired_at,
            )
        except Exception as exc:
            return self._downgrade_to_hold(
                f"{decision.value} signal application raised: {exc}"
            )

        if applied is None:
            return self._downgrade_to_hold(
                f"{decision.value} {ticker_str} qty={quantity.shares} "
                f"rejected by trade rules (insufficient funds/shares "
                f"or zero quantity after sizing)"
            )

        # Phase F-6 — per-portfolio per-UTC-day cap. The candidate
        # transaction's |cash_change| is the impact; check against the
        # cap before persistence. A denied cap downgrades to HOLD with
        # the cap's reason captured in the audit-row rationale.
        if self._portfolio_cap is not None:
            attempted_value = abs(applied.cash_change.amount)
            cap_result = await self._portfolio_cap.check(
                portfolio_id=portfolio_id,
                attempted_decision=decision,
                attempted_value_usd=attempted_value,
            )
            if not cap_result.allowed:
                return self._downgrade_to_hold(
                    f"{decision.value} {ticker_str} qty={quantity.shares} "
                    f"downgraded to HOLD by per-portfolio daily cap: "
                    f"{cap_result.reason}"
                )

        await self._transaction_repo.save_all(
            [applied],
            api_key_id=api_key_id,
            trigger_id=trigger.id,
        )
        return {
            "decision": decision,
            "resulting_trade_id": applied.id,
            "resulting_modify_payload": None,
            "resulting_exploration_task_id": None,
            "notes": _payload_str(payload, "notes"),
            "error": None,
        }

    async def _execute_modify(
        self,
        *,
        payload: Mapping[str, object],
        strategy: Strategy,
        api_key_id: UUID,
    ) -> _DecisionExecutionResult:
        """MODIFY_STRATEGY → validate, persist, audit.

        The forbidden-keys check (§3.5) is enforced here: the agent
        can never change the asset universe (`tickers`). Other invalid
        payloads (wrong type, out-of-range value) downgrade to HOLD
        with the validator's error message captured in the rationale.
        """
        overrides_obj = payload.get("parameter_overrides")
        if not isinstance(overrides_obj, Mapping):
            return self._downgrade_to_hold(
                "MODIFY_STRATEGY missing parameter_overrides mapping"
            )
        overrides: dict[str, object] = dict(overrides_obj)

        forbidden_present = _MODIFY_FORBIDDEN_KEYS & overrides.keys()
        if forbidden_present:
            return self._downgrade_to_hold(
                "MODIFY_STRATEGY rejected: forbidden parameter overrides "
                f"{sorted(forbidden_present)} (asset universe is a "
                "security boundary)"
            )

        try:
            updated_params = _apply_parameter_overrides(
                base_params=strategy.parameters,
                overrides=overrides,
            )
        except (ValueError, InvalidStrategyError) as exc:
            return self._downgrade_to_hold(f"MODIFY_STRATEGY rejected: {exc}")

        updated_strategy = Strategy(
            id=strategy.id,
            user_id=strategy.user_id,
            name=strategy.name,
            strategy_type=strategy.strategy_type,
            tickers=list(strategy.tickers),
            parameters=updated_params,
            created_at=strategy.created_at,
        )
        await self._strategy_repo.save(updated_strategy, api_key_id=api_key_id)
        return {
            "decision": AgentDecision.MODIFY_STRATEGY,
            "resulting_trade_id": None,
            "resulting_modify_payload": overrides,
            "resulting_exploration_task_id": None,
            "notes": _payload_str(payload, "notes"),
            "error": None,
        }

    async def _execute_needs_human(
        self,
        *,
        payload: Mapping[str, object],
        rationale: str,
        trigger: StrategyConditionTrigger,
        activation: StrategyActivation,
        api_key_id: UUID,
    ) -> _DecisionExecutionResult:
        """NEEDS_HUMAN → file an :class:`ExplorationTask`.

        The task title is prefixed with both ``[TRIGGER FIRE]`` and
        ``[NEEDS HUMAN]`` per the design (§3.5). The prompt embeds the
        agent's summary + the trigger's metadata so a human can act
        without round-tripping back to the trigger.
        """
        summary = _payload_str(payload, "summary") or rationale
        urgency = _payload_str(payload, "urgency") or "medium"
        prompt_lines = [
            "[TRIGGER FIRE] [NEEDS HUMAN] Trigger requested human review.",
            "",
            f"Trigger ID: {trigger.id}",
            f"Activation ID: {trigger.activation_id}",
            f"Condition type: {trigger.condition_type.value}",
            f"Urgency: {urgency}",
            "",
            "Agent summary:",
            summary or "(no summary provided)",
            "",
            "Original trigger prompt:",
            trigger.agent_prompt,
        ]
        prompt = "\n".join(prompt_lines)

        task_id = uuid4()
        now = datetime.now(UTC)
        task = ExplorationTask(
            id=task_id,
            created_by=trigger.user_id,
            prompt=prompt[:4000],  # entity caps prompt at 4000 chars
            status=ExplorationTaskStatus.OPEN,
            created_at=now,
            updated_at=now,
            target_portfolio_id=activation.portfolio_id,
        )
        await self._task_repo.save(task, api_key_id=api_key_id)
        return {
            "decision": AgentDecision.NEEDS_HUMAN,
            "resulting_trade_id": None,
            "resulting_modify_payload": None,
            "resulting_exploration_task_id": task_id,
            "notes": summary,
            "error": None,
        }

    # ------------------------------------------------------------------ #
    # API-key resolution                                                 #
    # ------------------------------------------------------------------ #

    async def _resolve_api_key(
        self, *, trigger: StrategyConditionTrigger
    ) -> ApiKey | None:
        """Resolve the API key per §4.1 priority order.

        1. ``trigger.default_api_key_id`` (if set + active + trade-scoped).
        2. Most-recently-used trade-scoped key for the activation owner.
        3. ``None`` (caller writes INVOCATION_FAILED).

        "Most recently used" is defined as the key with the latest
        ``last_used_at`` (None last). Ties broken by ``created_at``
        descending (newest mint wins).
        """
        if trigger.default_api_key_id is not None:
            key = await self._api_key_repo.get(trigger.default_api_key_id)
            if key is not None and self._is_eligible(key):
                return key

        # Fallback: scan all keys for the user.
        candidates = await self._api_key_repo.get_by_user(trigger.user_id)
        eligible = [k for k in candidates if self._is_eligible(k)]
        if not eligible:
            return None

        # Sort by last_used_at desc (None last), then created_at desc.
        eligible.sort(
            key=lambda k: (
                k.last_used_at is not None,
                k.last_used_at or datetime.min.replace(tzinfo=UTC),
                k.created_at,
            ),
            reverse=True,
        )
        return eligible[0]

    async def _resolve_api_key_safe(
        self, *, trigger: StrategyConditionTrigger
    ) -> ApiKey | None:
        """Resolve API key without raising — used by the catch-all path."""
        try:
            return await self._resolve_api_key(trigger=trigger)
        except Exception:
            logger.exception(
                "API-key resolution raised in catch-all path",
                extra={"trigger_id": str(trigger.id)},
            )
            return None

    @staticmethod
    def _is_eligible(api_key: ApiKey) -> bool:
        """True if the key is active and has the trade scope."""
        return api_key.is_active() and api_key.has_scope(ApiKeyScope.TRADE)

    # ------------------------------------------------------------------ #
    # Failure helpers                                                    #
    # ------------------------------------------------------------------ #

    async def _fail_with_audit(
        self,
        *,
        trigger: StrategyConditionTrigger,
        evaluation_data: Mapping[str, object],
        fire_id: UUID,
        fired_at: datetime,
        start: float,
        error_message: str,
        rationale_raw: str = "",
        api_key_override: ApiKey | None = None,
        invocation_id: str | None = None,
    ) -> FireOutcome:
        """Write an INVOCATION_FAILED audit row and return the outcome.

        Used when the failure happened mid-flow but we have an API key
        for attribution. When no API key is available, the catch-all
        path in :meth:`fire` returns a failure outcome without an audit
        row (the api_key_id_used FK is NOT NULL on the row).
        """
        latency_ms = int((time.perf_counter() - start) * 1000)
        api_key = api_key_override
        if api_key is None:
            api_key = await self._resolve_api_key_safe(trigger=trigger)
        if api_key is None:
            # Cannot satisfy NOT NULL on api_key_id_used; surface
            # failure without audit row.
            logger.error(
                "Trigger failed and no API key available for audit row",
                extra={
                    "trigger_id": str(trigger.id),
                    "error": error_message,
                },
            )
            return FireOutcome(
                trigger_id=trigger.id,
                fire_record_id=fire_id,
                decision=AgentDecision.INVOCATION_FAILED,
                latency_ms=latency_ms,
                error=error_message,
            )

        await self._write_failure_record(
            trigger=trigger,
            evaluation_data=evaluation_data,
            fire_id=fire_id,
            fired_at=fired_at,
            api_key_id=api_key.id,
            latency_ms=latency_ms,
            error_message=error_message,
            rationale_raw=rationale_raw,
            invocation_id=invocation_id,
        )
        return FireOutcome(
            trigger_id=trigger.id,
            fire_record_id=fire_id,
            decision=AgentDecision.INVOCATION_FAILED,
            latency_ms=latency_ms,
            error=error_message,
        )

    async def _write_failure_record(
        self,
        *,
        trigger: StrategyConditionTrigger,
        evaluation_data: Mapping[str, object],
        fire_id: UUID,
        fired_at: datetime,
        api_key_id: UUID,
        latency_ms: int,
        error_message: str,
        rationale_raw: str,
        invocation_id: str | None = None,
    ) -> None:
        """Persist an INVOCATION_FAILED audit row.

        Helper for both the catch-all path and the fail-fast paths.
        ``rationale_raw`` is the agent's free-text body (if any) plus
        the failure message. Truncated to satisfy the entity's 8000
        char cap.
        """
        body = (
            error_message
            if not rationale_raw
            else (f"{rationale_raw}\n---\n{error_message}")
        )
        record = TriggerFireRecord(
            id=fire_id,
            trigger_id=trigger.id,
            activation_id=trigger.activation_id,
            fired_at=fired_at,
            condition_evaluation_data=dict(evaluation_data),
            agent_response=AgentDecision.INVOCATION_FAILED,
            agent_response_raw=_truncate(body),
            latency_ms=latency_ms,
            api_key_id_used=api_key_id,
            agent_invocation_id=invocation_id,
        )
        await self._fire_repo.save(record)
        # Also record the fire on the trigger so cooldown applies.
        # Even an INVOCATION_FAILED counts as a fire — the next eval
        # tick should respect the cooldown rather than retry immediately.
        await self._trigger_repo.save(trigger.record_fire(fired_at=fired_at))

    # ------------------------------------------------------------------ #
    # Tiny helpers                                                       #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _downgrade_to_hold(reason: str) -> _DecisionExecutionResult:
        """Build a guardrail-downgrade result for a BUY/SELL/MODIFY rejection.

        The audit row records this as ``HOLD`` so the activity feed
        shows "trigger fired but no action taken"; the rationale carries
        the original decision plus the downgrade reason.
        """
        return {
            "decision": AgentDecision.HOLD,
            "resulting_trade_id": None,
            "resulting_modify_payload": None,
            "resulting_exploration_task_id": None,
            "notes": reason,
            "error": reason,
        }

    @staticmethod
    def _resolve_quantity(quantity_str: str) -> Quantity:
        """Coerce the agent's quantity payload to a :class:`Quantity`.

        Empty / missing / null values default to one share — a
        conservative baseline that the agent can override by passing
        a positive decimal string.
        """
        if not quantity_str.strip():
            return Quantity(Decimal("1"))
        return Quantity(Decimal(quantity_str))


# --------------------------------------------------------------------------- #
# Prompt builders (pure — testable without I/O)                               #
# --------------------------------------------------------------------------- #


def build_system_prompt() -> str:
    """The static system prompt sent on every trigger fire.

    Identical bytes across invocations so prompt caching gets a 100%
    hit rate on this block. The tone is operational, not chatty —
    the agent's job is to make a structured decision fast.

    See ``docs/agents/operating-manual.md`` §3.5.1 for the
    human-readable description of this contract.
    """
    return (
        "You are a Zebu trigger-fire decision agent.\n"
        "\n"
        "## Role\n"
        "A condition trigger has fired on an active paper-trading "
        "strategy. You will receive the trigger's context "
        "(condition snapshot, strategy state, portfolio state, and the "
        "operator's free-form prompt) and must return a structured "
        "decision via the `record_decision` tool.\n"
        "\n"
        "## Hard rules\n"
        "1. **Paper-trading only.** Zebu is paper money.\n"
        "2. **Terminate by calling `record_decision` exactly once.** "
        "The conversation ends when you call it.\n"
        "3. **Be conservative.** When in doubt, prefer HOLD or "
        "NEEDS_HUMAN over a forced trade.\n"
        "4. **Decisions:**\n"
        "   - `BUY` / `SELL` — paper trade on the activation's portfolio. "
        "Provide `ticker` (must be in the strategy's universe), "
        "optional `quantity` (decimal string), and `notes`.\n"
        "   - `HOLD` — no action; just record. Provide `notes`.\n"
        "   - `MODIFY_STRATEGY` — update strategy parameters. Provide "
        "`parameter_overrides` (dict) and `notes`. The `tickers` "
        "field is forbidden — that would change the asset universe.\n"
        "   - `NEEDS_HUMAN` — escalate via an ExplorationTask. Provide "
        "`summary` and `urgency` (low | medium | high).\n"
        "5. **Trades on tickers outside the strategy universe are "
        "rejected automatically; do not attempt them.**\n"
        "6. **Respect the operator's instructions in the user prompt** "
        "— they were configured by a human who knew the strategy "
        "context.\n"
        "\n"
        "## Output format\n"
        "Always call the `record_decision` tool. The `rationale` "
        "field should be 1-2 sentences explaining your reasoning; this "
        "is persisted on the audit row for review.\n"
    )


def build_user_prompt(
    *,
    trigger: StrategyConditionTrigger,
    activation: StrategyActivation,
    strategy: Strategy,
    portfolio_id: UUID,
    cash_balance: Decimal,
    holdings_summary: list[tuple[str, Decimal]],
    evaluation_data: Mapping[str, object],
) -> str:
    """Assemble the per-fire user message.

    Deterministic — same inputs produce the same bytes. Tests assert
    structural properties (section headers present, agent_prompt
    verbatim) rather than fixture-matching exact text (which drifts).

    Section order is fixed:

    1. Trigger metadata
    2. Condition snapshot (the `evaluation_data`)
    3. Strategy + activation state
    4. Portfolio state (cash + holdings)
    5. Operator instruction (the trigger's `agent_prompt`, verbatim)
    6. Closing directive
    """
    lines: list[str] = []

    lines.append("## Trigger")
    lines.append(f"- id: {trigger.id}")
    lines.append(f"- condition_type: {trigger.condition_type.value}")
    lines.append(f"- cooldown_seconds: {trigger.cooldown_seconds}")
    if trigger.last_fired_at is not None:
        lines.append(f"- last_fired_at: {trigger.last_fired_at.isoformat()}")
    lines.append(f"- priority: {trigger.priority}")
    lines.append("")

    lines.append("## Condition snapshot")
    for key, value in sorted(evaluation_data.items()):
        lines.append(f"- {key}: {value}")
    lines.append("")

    lines.append("## Strategy")
    lines.append(f"- id: {strategy.id}")
    lines.append(f"- type: {strategy.strategy_type.value}")
    lines.append(f"- tickers: {strategy.tickers}")
    lines.append(f"- name: {strategy.name}")
    lines.append("")

    lines.append("## Activation")
    lines.append(f"- id: {activation.id}")
    lines.append(f"- status: {activation.status.value}")
    lines.append(f"- frequency: {activation.frequency.value}")
    if activation.last_executed_at is not None:
        lines.append(f"- last_executed_at: {activation.last_executed_at.isoformat()}")
    if activation.last_error:
        lines.append(f"- last_error: {activation.last_error}")
    lines.append("")

    lines.append("## Portfolio")
    lines.append(f"- id: {portfolio_id}")
    lines.append(f"- cash_balance: {cash_balance}")
    if holdings_summary:
        lines.append("- holdings:")
        for symbol, shares in sorted(holdings_summary):
            lines.append(f"  - {symbol}: {shares}")
    else:
        lines.append("- holdings: (none)")
    lines.append("")

    lines.append("## Operator instruction")
    lines.append(trigger.agent_prompt)
    lines.append("")

    lines.append("## Directive")
    lines.append(
        "Decide what to do and call `record_decision`. Be conservative — "
        "prefer HOLD or NEEDS_HUMAN over forced trades when the right "
        "answer is unclear."
    )

    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Module-private helpers                                                      #
# --------------------------------------------------------------------------- #


def _payload_str(payload: Mapping[str, object], key: str) -> str:
    """Extract a string field from the payload, defaulting to ''."""
    value = payload.get(key)
    return value if isinstance(value, str) else ""


def _truncate(value: str) -> str:
    """Cap a raw agent body at the entity's 8000-char limit."""
    if len(value) <= _AGENT_RAW_TRUNCATE:
        return value
    return value[:_AGENT_RAW_TRUNCATE]


def _apply_parameter_overrides(
    *,
    base_params: StrategyParameters,
    overrides: Mapping[str, object],
) -> StrategyParameters:
    """Merge ``overrides`` onto ``base_params`` and re-validate via the VO factory.

    The factory (:func:`parameters_from_dict`) re-runs the typed
    parameter validation so out-of-range values raise. This is also the
    only sanctioned way to mutate strategy parameters — it preserves
    the ``StrategyType``-discriminator invariant on the entity.
    """
    base_dict = base_params.to_dict()
    merged: dict[str, object] = {}
    # Merge known fields from base; let overrides win on conflict.
    for k, v in base_dict.items():
        merged[k] = v
    for k, v in overrides.items():
        merged[k] = v

    # Resolve the strategy_type from the base params' type.
    strategy_type = _strategy_type_for_params(base_params)
    return parameters_from_dict(strategy_type, merged)


def _strategy_type_for_params(
    params: StrategyParameters,
) -> StrategyType:
    """Map a parameter VO instance to its :class:`StrategyType`.

    The mapping is fixed (one parameter VO per strategy type). Done
    here rather than on the VO so the orchestrator owns the mapping
    knowledge — the domain VOs intentionally don't know about the
    discriminator enum.
    """
    match params:
        case BuyAndHoldParameters():
            return StrategyType.BUY_AND_HOLD
        case DcaParameters():
            return StrategyType.DOLLAR_COST_AVERAGING
        case MaCrossoverParameters():
            return StrategyType.MOVING_AVERAGE_CROSSOVER


__all__ = [
    "FireOutcome",
    "TriggerInvocationOrchestrator",
    "build_system_prompt",
    "build_user_prompt",
]


# Re-export for the caller's convenience — the F-2 evaluator emits
# ``DrawdownEvaluationData`` mappings, which are JSON-shaped and pass
# straight into ``evaluation_data``. Re-export here so callers don't
# have to import from the evaluator submodule.
__doc_extra__ = (DrawdownEvaluationData,)
