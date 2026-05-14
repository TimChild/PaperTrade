"""Wire schemas for the trigger CRUD + fire-log API (Phase F-5).

These Pydantic models are the on-the-wire request / response envelopes
for the routes in :mod:`zebu.adapters.inbound.api.triggers` and
:mod:`zebu.adapters.inbound.api.admin_triggers`. They mirror the domain
entity and value-object shapes from
:mod:`zebu.domain.entities.strategy_condition_trigger` and
:mod:`zebu.domain.entities.trigger_fire_record` but live at the API
boundary so the domain stays pure.

Design references:

* ``docs/architecture/phase-f-agent-in-the-loop.md`` §7 (API surface) for
  the endpoint list and the response shapes.
* ``docs/architecture/phase-f-agent-in-the-loop.md`` §1 for the entity
  field semantics (status, condition_type, etc.).
"""

from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Common schema-version constant (carried on serialised condition params)
# ---------------------------------------------------------------------------

# Re-exported so route handlers don't have to import from the domain VO
# module just for the constant. The discriminator + factory live in the
# domain layer; this file is purely the wire envelope.

# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class CreateTriggerRequest(BaseModel):
    """Request body for ``POST /activations/{activation_id}/triggers``.

    Field constraints match the domain entity (`StrategyConditionTrigger`)
    and value objects (`ConditionParams` discriminated union). The full
    entity-level invariants are enforced at the domain layer; FastAPI's
    Pydantic-driven validation only catches obvious shape errors at the
    wire boundary.

    Per Phase-F design Q3, ``status`` is *not* in the create payload —
    new triggers always start ``ACTIVE`` (the entity's default).

    Per Phase-F design §1.2, the ``CUSTOM_RULE`` discriminator is
    rejected at construction time by the domain VO with a 422.

    Attributes:
        condition_type: One of ``DRAWDOWN_THRESHOLD``,
            ``VOLATILITY_SPIKE``, ``EARNINGS_PROXIMITY``, ``CUSTOM_RULE``.
            ``CUSTOM_RULE`` is intentionally rejected per Phase-F design Q1.
        condition_params: Decision-type-specific params. The domain
            ``params_from_dict(condition_type, raw)`` factory validates
            and reconstructs the typed VO.
        agent_prompt: Free-form instruction the agent receives on fire.
            10–4000 chars after stripping outer whitespace.
        cooldown_seconds: Minimum seconds between successive fires.
            Defaults to 6 hours (21600).
        priority: Evaluation order tie-breaker. Range -100..100, default 0.
        default_api_key_id: Optional FK to ``api_keys.id`` — the key the
            woken agent should act under for trade attribution.
        expires_at: Optional natural expiry. ISO-8601 timestamp.
    """

    condition_type: str = Field(
        ...,
        description=(
            "Discriminator for the condition. One of DRAWDOWN_THRESHOLD, "
            "VOLATILITY_SPIKE, EARNINGS_PROXIMITY, or CUSTOM_RULE. "
            "CUSTOM_RULE is rejected at construction time (Phase-F design Q1)."
        ),
    )
    condition_params: dict[str, object] = Field(
        ...,
        description=(
            "Per-condition parameter mapping. Shape depends on "
            "``condition_type`` — see Phase-F design §1.2."
        ),
    )
    agent_prompt: Annotated[str, Field(min_length=1, max_length=4000)] = Field(
        ...,
        description=(
            "Free-form instruction the agent receives when the trigger "
            "fires. 10–4000 chars after stripping whitespace (the domain "
            "entity validates the trimmed length)."
        ),
    )
    cooldown_seconds: int = Field(
        default=21600,
        ge=0,
        description=(
            "Minimum seconds between successive fires. Defaults to 6 hours (21600)."
        ),
    )
    priority: int = Field(
        default=0,
        ge=-100,
        le=100,
        description="Evaluation tie-breaker. Higher first. Range -100..100.",
    )
    default_api_key_id: UUID | None = Field(
        default=None,
        description=(
            "Optional FK to api_keys.id — the trade-scoped key the woken "
            "agent should act under. ``None`` means 'fall back to the "
            "owner's most-recently-used trade-scoped key'."
        ),
    )
    expires_at: str | None = Field(
        default=None,
        description=(
            "Optional ISO-8601 expiry timestamp. When set + lapsed, the "
            "evaluator transitions the trigger to EXPIRED."
        ),
    )
    mode: str = Field(
        default="direct",
        description=(
            "How the trigger reaches an agent when it fires. ``direct`` "
            "(the default) keeps the existing inline-Anthropic path; "
            "``queue`` opts into Pattern B — the platform files an "
            "URGENT ExplorationTask for an out-of-band agent (Claude "
            "Desktop / Gemini CLI / etc.) to claim and process. "
            "See ``docs/agents/operating-manual.md`` §3.5.1."
        ),
    )


class UpdateTriggerRequest(BaseModel):
    """Request body for ``PATCH /triggers/{trigger_id}``.

    All fields are optional — only the supplied ones are mutated. Per
    Phase-F design Q3, ``status`` accepts only ``ACTIVE`` (resume) or
    ``PAUSED`` (pause); attempting to lift ``MANUALLY_DISABLED`` via PATCH
    is rejected with 422 ("delete and recreate" is the documented lift path).

    The ``condition_params`` field, when present, replaces the typed
    parameter VO entirely (the domain VOs are frozen and never mutated
    in-place).

    Attributes:
        agent_prompt: New free-form instruction. Same constraints as
            create (10–4000 chars after trimming).
        cooldown_seconds: New cooldown. ``>= 0``.
        priority: New evaluation priority. ``[-100, 100]``.
        condition_params: New decision-type-specific params (same shape
            as create — must validate against the existing
            ``condition_type``).
        status: Lifecycle transition request — ``ACTIVE`` or ``PAUSED``
            only. Rejected with 422 when caller attempts to leave a
            terminal state (``EXPIRED`` / ``MANUALLY_DISABLED``).
    """

    agent_prompt: str | None = Field(default=None, min_length=1, max_length=4000)
    cooldown_seconds: int | None = Field(default=None, ge=0)
    priority: int | None = Field(default=None, ge=-100, le=100)
    condition_params: dict[str, object] | None = Field(default=None)
    status: str | None = Field(
        default=None,
        description=(
            "Requested lifecycle transition. Allowed values are ACTIVE "
            "(resume) and PAUSED (pause). Lifting MANUALLY_DISABLED via "
            "this field is intentionally rejected — delete and recreate "
            "instead (Phase-F design Q3)."
        ),
    )
    mode: str | None = Field(
        default=None,
        description=(
            "Optional invocation-mode update. ``direct`` keeps the "
            "inline-Anthropic path; ``queue`` switches the trigger to "
            "Pattern B (URGENT ExplorationTask filing). See "
            "``docs/agents/operating-manual.md`` §3.5.1."
        ),
    )


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class TriggerResponse(BaseModel):
    """Wire shape for a :class:`StrategyConditionTrigger`.

    Mirrors :data:`docs/architecture/phase-f-agent-in-the-loop.md` §7.3.

    Timestamps are emitted as ISO-8601 strings (matching the existing
    activation / exploration-task response shapes).
    """

    id: UUID
    activation_id: UUID
    user_id: UUID
    condition_type: str
    condition_params: dict[str, object]
    agent_prompt: str
    cooldown_seconds: int
    last_fired_at: str | None
    status: str
    priority: int
    default_api_key_id: UUID | None
    expires_at: str | None
    created_at: str
    created_by: UUID
    updated_at: str
    mode: str


class TriggerFireResponse(BaseModel):
    """Wire shape for a :class:`TriggerFireRecord`.

    Mirrors :data:`docs/architecture/phase-f-agent-in-the-loop.md` §7.4.

    All timestamps are ISO-8601 strings. JSON columns
    (``condition_evaluation_data``, ``resulting_modify_payload``) are
    passed through unchanged — the per-condition evaluator's snapshot
    schema lives there, with a top-level ``schema_version`` int.
    """

    id: UUID
    trigger_id: UUID
    activation_id: UUID
    fired_at: str
    condition_evaluation_data: dict[str, object]
    invocation_mode: str
    agent_invocation_id: str | None
    agent_response: str | None
    agent_response_raw: str
    resulting_trade_id: UUID | None
    resulting_modify_payload: dict[str, object] | None
    resulting_exploration_task_id: UUID | None
    latency_ms: int
    api_key_id_used: UUID


class DisableAllResponse(BaseModel):
    """Wire shape for ``POST /triggers/disable-all`` and its admin twin.

    Attributes:
        disabled_count: How many triggers transitioned to
            ``MANUALLY_DISABLED`` as a result of this call. Idempotent —
            zero is a legitimate result when the user has no
            non-terminal triggers.
    """

    disabled_count: int


__all__ = [
    "CreateTriggerRequest",
    "DisableAllResponse",
    "TriggerFireResponse",
    "TriggerResponse",
    "UpdateTriggerRequest",
]
