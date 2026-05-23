"""BacktestAgentInvocation entity — append-only audit row for one simulated fire.

Phase L (Task #217) — Foundation entity for the agent-driven backtest
pipeline. One row per simulated trigger fire during a backtest, recording
the agent decision (or absence thereof) in simulated time.

This mirrors :class:`TriggerFireRecord` (the live-mode audit row) in
overall shape but differs in lifecycle and invariants:

* Lives alongside a :class:`BacktestRun`; cascades on parent deletion.
* Records ``simulated_date`` (the in-simulation calendar day on which the
  fire happened) — distinct from any wall-clock timestamp.
* Does not need an ``api_key_id`` column — backtests run against the
  synthetic backtest portfolio; the originating credential is captured
  on the parent ``BacktestRun`` row via its existing ``api_key_id``
  column.
* Carries a per-row ``invocation_mode`` (``MOCK`` / ``LIVE``) so a single
  backtest could in principle mix modes (e.g. fall back to MOCK after a
  budget cap).

The record is fully immutable — there is no update path. Corrections
happen by writing a new row, not by mutating an existing one.

Invariants (per task #217 spec):

* ``latency_ms >= 0``.
* ``len(rationale) <= 8000`` — matches :class:`TriggerFireRecord.agent_response_raw`.
* ``len(model) <= 100`` — matches the ``agent_invocation_id`` column
  width for consistency.
* ``condition_evaluation_data`` must be a :class:`Mapping`; normalised to
  a fresh ``dict`` to defend against caller-side mutation.
* ``decision_payload``, if not ``None``, must be a :class:`Mapping`;
  same normalisation.
* MOCK-mode rows: ``decision_payload is None``, ``rationale == ""``,
  ``model == ""``, ``latency_ms == 0``, ``agent_invocation_id is None``,
  ``decision_executed is False``. ``agent_decision`` may be either
  ``None`` or :class:`AgentDecision.HOLD` (the entity is permissive; the
  L-2 adapter will pick one shape and write consistently).
* LIVE-mode rows: ``agent_decision is not None``, ``model != ""``,
  ``rationale`` may be empty only when ``agent_decision == INVOCATION_FAILED``,
  ``agent_invocation_id`` may be ``None`` (transport error before the
  SDK assigned one).
* ``decision_executed == True`` is only allowed for LIVE rows whose
  decision is in ``{BUY, SELL, MODIFY_STRATEGY}``.
* ``created_at`` must be timezone-aware UTC (raised as
  :class:`InvalidBacktestAgentInvocationError` on naive datetimes).
* ``simulated_date`` is a :class:`datetime.date` (no intraday component).
"""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

from zebu.domain.exceptions import InvalidBacktestAgentInvocationError
from zebu.domain.value_objects.agent_decision import AgentDecision
from zebu.domain.value_objects.backtest_agent_invocation_mode import (
    BacktestAgentInvocationMode,
)

# Decisions that may set ``decision_executed = True``. HOLD / NEEDS_HUMAN /
# INVOCATION_FAILED never mutate the simulated trade book.
_DECISIONS_EXECUTABLE: frozenset[AgentDecision] = frozenset(
    {AgentDecision.BUY, AgentDecision.SELL, AgentDecision.MODIFY_STRATEGY}
)

_RATIONALE_MAX_LENGTH: int = 8000
_MODEL_MAX_LENGTH: int = 100


@dataclass(frozen=True)
class BacktestAgentInvocation:
    """Audit row for a single simulated trigger fire inside a backtest.

    See module docstring for full context.

    Attributes:
        id: Unique invocation-record identifier.
        backtest_run_id: FK to ``backtest_runs.id``. Cascade-deletes with
            the run.
        simulated_date: The in-simulation calendar day this fire happened
            on. Must be within ``[backtest_run.start_date,
            backtest_run.end_date]`` — that range check is enforced at the
            service layer (the entity has no access to the run).
        trigger_id: FK to ``strategy_condition_triggers.id``. ``ON DELETE
            SET NULL`` so deleting a trigger doesn't break the audit row.
            ``None`` for the recovered-orphan state.
        condition_evaluation_data: Per-condition snapshot of the inputs
            that fired the trigger. Same opaque-JSON contract as
            :class:`TriggerFireRecord.condition_evaluation_data`.
        agent_decision: Post-guardrail decision the simulated executor
            acted on. ``None`` only when ``invocation_mode == MOCK`` and
            the platform recorded a synthetic no-op invocation. For LIVE
            rows must be set (including ``INVOCATION_FAILED`` on transport
            or parse error).
        rationale: Free-text agent rationale. Truncated to 8000 chars at
            write time. Empty string for MOCK rows and for LIVE rows
            whose decision is ``INVOCATION_FAILED``.
        decision_payload: Decision-specific payload as emitted by the
            agent (the :class:`AgentInvocationResult.payload` mapping).
            ``None`` for MOCK rows; set for LIVE rows (including ``HOLD``).
        decision_executed: Whether the decision actually mutated the
            simulated trade book. ``True`` only for LIVE rows whose
            decision is in ``{BUY, SELL, MODIFY_STRATEGY}``.
        simulated_trade_id: FK to ``transactions.id``. When the decision
            produced a simulated transaction, the resulting transaction
            id. ``None`` otherwise. ``ON DELETE SET NULL`` so deleting an
            orphan transaction doesn't erase the rationale.
        invocation_mode: How this row was invoked. One of ``MOCK`` /
            ``LIVE`` — ``NONE`` is a run-level concept; no audit rows are
            written for NONE-mode runs.
        agent_invocation_id: Anthropic message ID for LIVE rows. ``None``
            for MOCK rows or for LIVE transport errors before the SDK
            assigned one.
        latency_ms: Round-trip latency for the agent invocation. ``>= 0``.
            ``0`` for MOCK rows.
        model: Anthropic model identifier used (e.g.
            ``"claude-haiku-4-5-20251001"``). Empty string for MOCK rows.
        created_at: UTC wall-clock when the row was written. Timezone-
            aware; distinct from ``simulated_date``.

    Raises:
        InvalidBacktestAgentInvocationError: If any invariant is violated.
    """

    id: UUID
    backtest_run_id: UUID
    simulated_date: date
    trigger_id: UUID | None
    condition_evaluation_data: Mapping[str, object]
    rationale: str
    latency_ms: int
    model: str
    invocation_mode: BacktestAgentInvocationMode
    created_at: datetime
    agent_decision: AgentDecision | None = None
    decision_payload: Mapping[str, object] | None = None
    decision_executed: bool = False
    simulated_trade_id: UUID | None = None
    agent_invocation_id: str | None = None

    def __post_init__(self) -> None:
        """Validate invariants and normalise opaque JSON fields."""
        # condition_evaluation_data must be a Mapping. Normalise into a
        # fresh dict to defend against caller-side mutation.
        if not isinstance(self.condition_evaluation_data, Mapping):  # type: ignore[unreachable]  # defensive
            raise InvalidBacktestAgentInvocationError(
                "condition_evaluation_data must be a JSON-object-like mapping"
            )
        object.__setattr__(
            self,
            "condition_evaluation_data",
            dict(self.condition_evaluation_data),
        )

        if self.decision_payload is not None:
            if not isinstance(self.decision_payload, Mapping):  # type: ignore[unreachable]  # defensive
                raise InvalidBacktestAgentInvocationError(
                    "decision_payload must be a JSON-object-like mapping"
                )
            object.__setattr__(
                self,
                "decision_payload",
                dict(self.decision_payload),
            )

        # Reject bool-as-int — Python lets ``True`` slip past ``int``
        # type checks but it is almost always a caller-side mistake here.
        if isinstance(self.latency_ms, bool):
            raise InvalidBacktestAgentInvocationError(
                "latency_ms must be a non-negative integer"
            )
        if self.latency_ms < 0:
            raise InvalidBacktestAgentInvocationError(
                f"latency_ms must be non-negative, got {self.latency_ms}"
            )

        if len(self.rationale) > _RATIONALE_MAX_LENGTH:
            raise InvalidBacktestAgentInvocationError(
                f"rationale must be at most {_RATIONALE_MAX_LENGTH} characters; "
                f"truncate at write time, got {len(self.rationale)}"
            )

        if len(self.model) > _MODEL_MAX_LENGTH:
            raise InvalidBacktestAgentInvocationError(
                f"model must be at most {_MODEL_MAX_LENGTH} characters, "
                f"got {len(self.model)}"
            )

        if self.created_at.tzinfo is None:
            raise InvalidBacktestAgentInvocationError(
                "created_at must be timezone-aware UTC"
            )

        # decision_executed only valid for LIVE + actionable decisions.
        if self.decision_executed:
            if self.invocation_mode is not BacktestAgentInvocationMode.LIVE:
                raise InvalidBacktestAgentInvocationError(
                    "decision_executed=True requires invocation_mode=LIVE; "
                    f"got {self.invocation_mode.value}"
                )
            if (
                self.agent_decision is None
                or self.agent_decision not in _DECISIONS_EXECUTABLE
            ):
                decision_name = (
                    self.agent_decision.value
                    if self.agent_decision is not None
                    else "None"
                )
                raise InvalidBacktestAgentInvocationError(
                    "decision_executed=True requires agent_decision in "
                    f"{{BUY, SELL, MODIFY_STRATEGY}}; got {decision_name}"
                )

        # Per-mode invariants.
        if self.invocation_mode is BacktestAgentInvocationMode.MOCK:
            self._check_mock_invariants()
        elif self.invocation_mode is BacktestAgentInvocationMode.LIVE:
            self._check_live_invariants()
        else:
            # NONE is a run-level concept. The audit table never writes a
            # row in NONE mode — surface this loudly so a caller can't
            # accidentally persist one.
            raise InvalidBacktestAgentInvocationError(
                "invocation_mode=NONE is run-level only; no audit row "
                "should be created with this mode"
            )

    def _check_mock_invariants(self) -> None:
        """Validate the MOCK-mode field combinations."""
        # agent_decision: permissive — None or HOLD both accepted.
        if (
            self.agent_decision is not None
            and self.agent_decision is not AgentDecision.HOLD
        ):
            raise InvalidBacktestAgentInvocationError(
                "invocation_mode=MOCK requires agent_decision to be None or "
                f"HOLD; got {self.agent_decision.value}"
            )
        if self.decision_payload is not None:
            raise InvalidBacktestAgentInvocationError(
                "invocation_mode=MOCK requires decision_payload to be None"
            )
        if self.rationale != "":
            raise InvalidBacktestAgentInvocationError(
                "invocation_mode=MOCK requires rationale to be the empty string"
            )
        if self.model != "":
            raise InvalidBacktestAgentInvocationError(
                "invocation_mode=MOCK requires model to be the empty string"
            )
        if self.latency_ms != 0:
            raise InvalidBacktestAgentInvocationError(
                f"invocation_mode=MOCK requires latency_ms == 0, got {self.latency_ms}"
            )
        if self.agent_invocation_id is not None:
            raise InvalidBacktestAgentInvocationError(
                "invocation_mode=MOCK requires agent_invocation_id to be None"
            )
        # NB: ``decision_executed=True`` for MOCK is already rejected by
        # the global cross-check in ``__post_init__`` (which raises before
        # this method runs), so we don't repeat it here.

    def _check_live_invariants(self) -> None:
        """Validate the LIVE-mode field combinations."""
        if self.agent_decision is None:
            raise InvalidBacktestAgentInvocationError(
                "invocation_mode=LIVE requires agent_decision to be set"
            )
        if self.model == "":
            raise InvalidBacktestAgentInvocationError(
                "invocation_mode=LIVE requires model to be a non-empty string"
            )
        # rationale may be empty only when the decision is INVOCATION_FAILED
        # (matches the TriggerFireRecord truncation semantics).
        if (
            self.rationale == ""
            and self.agent_decision is not AgentDecision.INVOCATION_FAILED
        ):
            raise InvalidBacktestAgentInvocationError(
                "invocation_mode=LIVE requires rationale to be non-empty "
                "unless agent_decision is INVOCATION_FAILED"
            )

    # ------------------------------------------------------------------
    # Identity, hashing, repr
    # ------------------------------------------------------------------

    def __eq__(self, other: object) -> bool:
        """Equality based on ID only — entity identity, not contents."""
        if not isinstance(other, BacktestAgentInvocation):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        """Hash based on ID for use in dicts/sets."""
        return hash(self.id)

    def __repr__(self) -> str:
        """Return repr for debugging."""
        decision_str = (
            self.agent_decision.value if self.agent_decision is not None else "None"
        )
        return (
            f"BacktestAgentInvocation(id={self.id}, "
            f"backtest_run_id={self.backtest_run_id}, "
            f"simulated_date={self.simulated_date.isoformat()}, "
            f"invocation_mode={self.invocation_mode.value}, "
            f"agent_decision={decision_str}, "
            f"latency_ms={self.latency_ms})"
        )


__all__ = ["BacktestAgentInvocation"]
