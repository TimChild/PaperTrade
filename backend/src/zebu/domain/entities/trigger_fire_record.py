"""TriggerFireRecord entity — append-only audit row for one trigger fire.

Each time the trigger evaluator fires a trigger and dispatches the agent,
a :class:`TriggerFireRecord` row is appended. This is the join table that
connects "the trigger fired with these inputs" to "the agent decided X"
to "this trade / modify / exploration task happened as a result". The
activity feed in Phase G renders this table; the trigger fire log API
in F-5 paginates it.

The record is fully immutable — there is no update path. Corrections
happen by writing a new row referencing the original via
``agent_response_raw`` text or by manual SQL fix in pathological cases
(audit-trail integrity over flexibility).

Invariants (per Phase-F design §1.4):

* ``latency_ms >= 0``.
* Exactly one of (``resulting_trade_id``, ``resulting_modify_payload``,
  ``resulting_exploration_task_id``) is set, OR ``agent_response`` is
  ``HOLD`` / ``INVOCATION_FAILED`` (in which case all three are null).
* ``fired_at >= now-anchor`` checks happen in the service layer; the
  entity only checks self-consistency.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from zebu.domain.exceptions import InvalidTriggerFireError
from zebu.domain.value_objects.agent_decision import AgentDecision
from zebu.domain.value_objects.trigger_invocation_mode import TriggerInvocationMode

# Truncate the raw agent body to 8000 chars at write time. Matches the
# Phase-F design §1.4 — full body lives in observability, this column
# is for fast log rendering.
_AGENT_RESPONSE_RAW_MAX_LENGTH: int = 8000

# Decisions that have NO resulting side-effect — the three "resulting_*"
# pointers must all be null when the response is one of these.
_DECISIONS_WITHOUT_RESULTING_POINTER: frozenset[AgentDecision] = frozenset(
    {AgentDecision.HOLD, AgentDecision.INVOCATION_FAILED}
)


@dataclass(frozen=True)
class TriggerFireRecord:
    """Audit row for a single trigger fire and its outcome.

    See module docstring for full context.

    Attributes:
        id: Unique fire-record identifier.
        trigger_id: FK to ``strategy_condition_triggers.id``. Cascade
            deletes with the trigger.
        activation_id: FK to ``strategy_activations.id``. Denormalised
            for fast filtering by activation.
        fired_at: UTC timestamp when the evaluator decided to fire.
        condition_evaluation_data: JSON snapshot of the inputs that made
            the condition fire (per :class:`ConditionType`). The schema
            is per-type and includes a ``schema_version`` field. The
            entity treats it as opaque — the per-type evaluators populate
            it.
        invocation_mode: How the trigger fire reached the agent. Mirrors
            the trigger's own ``mode`` at fire time. ``DIRECT`` means the
            orchestrator invoked the inline agent and a structured
            decision is in ``agent_response``. ``QUEUE`` means the
            platform deferred to an out-of-band agent via an
            :class:`ExplorationTask` — ``agent_response`` is ``None`` and
            ``resulting_exploration_task_id`` points at the queued task.
            Defaults to ``DIRECT`` so existing rows + the inline path
            remain unchanged.
        agent_invocation_id: Identifier from the Anthropic Messages API
            response (e.g. message ID). ``None`` when the call failed
            before producing an ID — or always ``None`` for queue-mode
            rows (no inline invocation happened).
        agent_response: Post-guardrail decision the executor acted on
            (or ``HOLD`` / ``INVOCATION_FAILED`` for no-action / failure).
            ``None`` only when ``invocation_mode == QUEUE`` — the platform
            did not invoke an agent, so no decision exists.
        agent_response_raw: Truncated free-text agent body (≤8000 chars
            at write time). Captures the original content even when the
            decision was downgraded by guardrails. May be the empty
            string for queue-mode fires (no rationale was generated).
        resulting_trade_id: FK to ``transactions.id`` when the response
            was BUY / SELL and the trade landed. ``None`` otherwise.
        resulting_modify_payload: Decision-execution payload when the
            response was ``MODIFY_STRATEGY``. ``None`` otherwise.
        resulting_exploration_task_id: FK to ``exploration_tasks.id``
            when the response was ``NEEDS_HUMAN`` or the fire was
            queue-mode. ``None`` otherwise.
        latency_ms: End-to-end latency from "evaluator decided to fire"
            to "decision executed (or rejected)". ``>= 0``.
        api_key_id_used: FK to ``api_keys.id``. Records the key the agent
            acted under for the resulting trade. ON DELETE RESTRICT in
            the migration so attribution can never be lost.

    Raises:
        InvalidTriggerFireError: If any invariant is violated.
    """

    id: UUID
    trigger_id: UUID
    activation_id: UUID
    fired_at: datetime
    condition_evaluation_data: Mapping[str, object]
    agent_response_raw: str
    latency_ms: int
    api_key_id_used: UUID
    agent_response: AgentDecision | None = None
    invocation_mode: TriggerInvocationMode = TriggerInvocationMode.DIRECT
    agent_invocation_id: str | None = None
    resulting_trade_id: UUID | None = None
    resulting_modify_payload: Mapping[str, object] | None = None
    resulting_exploration_task_id: UUID | None = None

    def __post_init__(self) -> None:
        """Validate invariants and normalise opaque fields."""
        # Defensive: ensure condition_evaluation_data is a dict-like
        # mapping. We don't enforce schema here — that's the per-type
        # evaluator's job — but we do reject obvious shape errors so a
        # caller that passes a list / string surfaces it loudly.
        if not isinstance(self.condition_evaluation_data, Mapping):  # type: ignore[unreachable]  # defensive
            raise InvalidTriggerFireError(
                "condition_evaluation_data must be a JSON-object-like mapping"
            )

        # Make the field independent of caller-side mutation by
        # rebinding to a fresh dict. Frozen dataclass — go via
        # object.__setattr__.
        object.__setattr__(
            self,
            "condition_evaluation_data",
            dict(self.condition_evaluation_data),
        )

        if self.resulting_modify_payload is not None:
            if not isinstance(self.resulting_modify_payload, Mapping):  # type: ignore[unreachable]
                raise InvalidTriggerFireError(
                    "resulting_modify_payload must be a JSON-object-like mapping"
                )
            object.__setattr__(
                self,
                "resulting_modify_payload",
                dict(self.resulting_modify_payload),
            )

        # latency_ms: non-negative.
        if isinstance(self.latency_ms, bool):
            raise InvalidTriggerFireError("latency_ms must be a non-negative integer")
        if self.latency_ms < 0:
            raise InvalidTriggerFireError(
                f"latency_ms must be non-negative, got {self.latency_ms}"
            )

        # agent_response_raw length cap.
        if len(self.agent_response_raw) > _AGENT_RESPONSE_RAW_MAX_LENGTH:
            raise InvalidTriggerFireError(
                f"agent_response_raw must be at most "
                f"{_AGENT_RESPONSE_RAW_MAX_LENGTH} characters; truncate at "
                f"write time, got {len(self.agent_response_raw)}"
            )

        # fired_at not in the future.
        now = datetime.now(UTC)
        fired_at_utc = (
            self.fired_at
            if self.fired_at.tzinfo is not None
            else self.fired_at.replace(tzinfo=UTC)
        )
        if fired_at_utc > now:
            raise InvalidTriggerFireError("fired_at cannot be in the future")

        # Resulting-pointer cardinality. Two regimes:
        #
        # * ``invocation_mode == QUEUE`` — no agent decision was made by
        #   the platform; the row records that the trigger fired and the
        #   platform handed off to an out-of-band agent via an
        #   ExplorationTask. ``agent_response`` must be ``None`` and
        #   ``resulting_exploration_task_id`` must be set (the others
        #   must be null).
        # * ``invocation_mode == DIRECT`` — the platform invoked an agent
        #   inline and acted on its structured decision. The existing
        #   per-decision invariants apply: exactly one resulting pointer
        #   unless the decision is HOLD / INVOCATION_FAILED.
        populated = [
            self.resulting_trade_id is not None,
            self.resulting_modify_payload is not None,
            self.resulting_exploration_task_id is not None,
        ]
        populated_count = sum(populated)

        if self.invocation_mode is TriggerInvocationMode.QUEUE:
            if self.agent_response is not None:
                raise InvalidTriggerFireError(
                    "invocation_mode=queue requires agent_response to be "
                    f"None; got {self.agent_response.value}"
                )
            if self.resulting_exploration_task_id is None:
                raise InvalidTriggerFireError(
                    "invocation_mode=queue requires "
                    "resulting_exploration_task_id to be set"
                )
            if self.resulting_trade_id is not None:
                raise InvalidTriggerFireError(
                    "invocation_mode=queue forbids resulting_trade_id"
                )
            if self.resulting_modify_payload is not None:
                raise InvalidTriggerFireError(
                    "invocation_mode=queue forbids resulting_modify_payload"
                )
            return

        # DIRECT mode below — agent_response must be set; existing
        # per-decision invariants apply.
        if self.agent_response is None:
            raise InvalidTriggerFireError(
                "invocation_mode=direct requires agent_response to be set"
            )

        if self.agent_response in _DECISIONS_WITHOUT_RESULTING_POINTER:
            if populated_count != 0:
                raise InvalidTriggerFireError(
                    f"agent_response={self.agent_response.value} requires "
                    "all resulting_* pointers to be null; "
                    f"got {populated_count} populated"
                )
        else:
            if populated_count != 1:
                raise InvalidTriggerFireError(
                    f"agent_response={self.agent_response.value} requires "
                    "exactly one of resulting_trade_id / "
                    "resulting_modify_payload / resulting_exploration_task_id "
                    f"to be set; got {populated_count}"
                )

        # Decision-specific cross-checks: BUY / SELL must point at a
        # trade, MODIFY_STRATEGY at a payload, NEEDS_HUMAN at an
        # exploration task. This catches caller-side wiring mistakes.
        if (
            self.agent_response in {AgentDecision.BUY, AgentDecision.SELL}
            and self.resulting_trade_id is None
        ):
            raise InvalidTriggerFireError(
                f"agent_response={self.agent_response.value} requires "
                "resulting_trade_id to be set"
            )
        if (
            self.agent_response is AgentDecision.MODIFY_STRATEGY
            and self.resulting_modify_payload is None
        ):
            raise InvalidTriggerFireError(
                "agent_response=MODIFY_STRATEGY requires "
                "resulting_modify_payload to be set"
            )
        if (
            self.agent_response is AgentDecision.NEEDS_HUMAN
            and self.resulting_exploration_task_id is None
        ):
            raise InvalidTriggerFireError(
                "agent_response=NEEDS_HUMAN requires "
                "resulting_exploration_task_id to be set"
            )

    # ------------------------------------------------------------------
    # Identity, hashing, repr
    # ------------------------------------------------------------------

    def __eq__(self, other: object) -> bool:
        """Equality based on ID only — entity identity, not contents."""
        if not isinstance(other, TriggerFireRecord):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        """Hash based on ID for use in dicts/sets."""
        return hash(self.id)

    def __repr__(self) -> str:
        """Return repr for debugging."""
        response_str = (
            self.agent_response.value if self.agent_response is not None else "None"
        )
        return (
            f"TriggerFireRecord(id={self.id}, trigger_id={self.trigger_id}, "
            f"invocation_mode={self.invocation_mode.value}, "
            f"agent_response={response_str}, "
            f"latency_ms={self.latency_ms})"
        )


__all__ = ["TriggerFireRecord"]
