"""StrategyConditionTrigger entity — wakes the agent when a condition fires.

A trigger attaches to exactly one :class:`StrategyActivation`. Each
scheduler tick the trigger evaluator (Phase F-2) walks the evaluable
triggers, checks each one's condition against fresh inputs, and on fire
invokes the Anthropic Messages API with a structured prompt. The agent
returns a :class:`AgentDecision` which is executed as a paper trade or
escalated.

This entity is **F-1 scope only**: the type encodes the persisted shape
+ lifecycle rules; the evaluator service, agent invocation port, and
decision-execution layer all land in F-2 / F-3.

See ``docs/architecture/phase-f-agent-in-the-loop.md`` §1.1 for the
contract this entity implements.

Lifecycle:

    [*] -> ACTIVE on construction
    ACTIVE  <-> PAUSED                  via .pause() / .resume()
    ACTIVE / PAUSED -> EXPIRED          via .expire() (evaluator-driven)
    ACTIVE / PAUSED -> MANUALLY_DISABLED via .disable() (kill-switch)

``EXPIRED`` and ``MANUALLY_DISABLED`` are terminal — no transition out.
The entity is ``frozen=True``; transitions return new instances.
"""

from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from uuid import UUID

from zebu.domain.exceptions import InvalidTriggerError
from zebu.domain.value_objects.trigger_condition import (
    ConditionParams,
    ConditionType,
    params_match_type,
)
from zebu.domain.value_objects.trigger_invocation_mode import TriggerInvocationMode
from zebu.domain.value_objects.trigger_status import TriggerStatus

# Trigger-level limits that match the Phase-F design §1.1.
_AGENT_PROMPT_MIN_LENGTH: int = 10
_AGENT_PROMPT_MAX_LENGTH: int = 4000
_PRIORITY_MIN: int = -100
_PRIORITY_MAX: int = 100
_DEFAULT_COOLDOWN_SECONDS: int = 21600  # 6 hours

_TERMINAL_STATUSES: frozenset[TriggerStatus] = frozenset(
    {TriggerStatus.EXPIRED, TriggerStatus.MANUALLY_DISABLED}
)


@dataclass(frozen=True)
class StrategyConditionTrigger:
    """Persistent record of "wake the agent when this condition fires".

    A trigger attaches to a single :class:`StrategyActivation`. An
    activation may carry zero or more triggers; pausing a trigger does
    not deactivate the underlying activation.

    Attributes:
        id: Unique trigger identifier.
        activation_id: FK to ``strategy_activations.id``. Cascade-deletes
            with the activation.
        user_id: Owner of the trigger; matches ``activation.user_id``.
            The match is enforced at the API / service layer (which has
            access to the activation entity) rather than here, since the
            domain doesn't load other entities.
        condition_type: Discriminator for which kind of condition this
            trigger evaluates. See :class:`ConditionType`.
        condition_params: Typed parameter VO for the chosen
            ``condition_type``. Must match (validated at construction).
        agent_prompt: Free-form instruction the agent receives when the
            trigger fires. Must be 10–4000 chars after stripping outer
            whitespace.
        cooldown_seconds: Minimum seconds between successive fires. Must
            be ``>= 0``. Defaults to 6 hours.
        last_fired_at: UTC timestamp of the most recent fire. ``None``
            until the first fire.
        status: Current :class:`TriggerStatus` lifecycle state.
        priority: Evaluation order tie-breaker when multiple triggers are
            eligible in one tick. Higher first. Range -100..100. Default 0.
        default_api_key_id: Optional FK to ``api_keys.id`` — the key the
            woken agent should act under. ``None`` means "fall back to the
            activation owner's most-recently-used trade-scoped key".
        expires_at: Optional natural expiry. When set + lapsed, the
            evaluator transitions the trigger to ``EXPIRED``.
        mode: How the trigger reaches an agent when it fires. Defaults to
            :attr:`TriggerInvocationMode.DIRECT` for backwards
            compatibility — pre-Phase-J rows behave exactly as they did
            before. ``QUEUE`` opts into Pattern B (file an URGENT
            :class:`ExplorationTask` for an out-of-band agent to claim).
        created_at: Creation timestamp (UTC; not in the future).
        created_by: User or API-key-derived UUID that created the trigger.
        updated_at: Last-mutation timestamp (UTC; ``>= created_at``).

    Raises:
        InvalidTriggerError: If any invariant is violated.
    """

    id: UUID
    activation_id: UUID
    user_id: UUID
    condition_type: ConditionType
    condition_params: ConditionParams
    agent_prompt: str
    status: TriggerStatus
    created_at: datetime
    updated_at: datetime
    created_by: UUID
    cooldown_seconds: int = _DEFAULT_COOLDOWN_SECONDS
    priority: int = 0
    last_fired_at: datetime | None = None
    default_api_key_id: UUID | None = None
    expires_at: datetime | None = None
    # Phase J / Task #213 — DIRECT keeps the F-3 inline-Anthropic
    # behaviour; QUEUE causes the orchestrator to file an URGENT
    # ExplorationTask instead. Default DIRECT so existing rows behave
    # exactly as they did pre-Phase-J.
    mode: TriggerInvocationMode = TriggerInvocationMode.DIRECT

    def __post_init__(self) -> None:
        """Validate all invariants after initialisation."""
        # condition_type / condition_params consistency.
        if not params_match_type(self.condition_type, self.condition_params):
            raise InvalidTriggerError(
                f"condition_params type does not match condition_type "
                f"{self.condition_type.value}: got "
                f"{type(self.condition_params).__name__}"
            )

        # agent_prompt: trimmed length must be 10–4000.
        prompt = self.agent_prompt
        if not isinstance(prompt, str):  # type: ignore[unreachable]  # defence in depth — strict typing should already enforce this
            raise InvalidTriggerError("agent_prompt must be a string")
        stripped_len = len(prompt.strip())
        if stripped_len < _AGENT_PROMPT_MIN_LENGTH:
            raise InvalidTriggerError(
                f"agent_prompt must be at least {_AGENT_PROMPT_MIN_LENGTH} "
                f"characters after trimming whitespace, got {stripped_len}"
            )
        if len(prompt) > _AGENT_PROMPT_MAX_LENGTH:
            raise InvalidTriggerError(
                f"agent_prompt must be at most {_AGENT_PROMPT_MAX_LENGTH} "
                f"characters, got {len(prompt)}"
            )

        # cooldown_seconds: non-negative.
        if isinstance(self.cooldown_seconds, bool):
            raise InvalidTriggerError("cooldown_seconds must be a non-negative integer")
        if self.cooldown_seconds < 0:
            raise InvalidTriggerError(
                f"cooldown_seconds must be non-negative, got {self.cooldown_seconds}"
            )

        # priority: in [-100, 100].
        if isinstance(self.priority, bool):
            raise InvalidTriggerError(
                f"priority must be an integer in [{_PRIORITY_MIN}, {_PRIORITY_MAX}]"
            )
        if not (_PRIORITY_MIN <= self.priority <= _PRIORITY_MAX):
            raise InvalidTriggerError(
                f"priority must be in [{_PRIORITY_MIN}, {_PRIORITY_MAX}], "
                f"got {self.priority}"
            )

        # Timestamp invariants: created_at not in future; updated_at >=
        # created_at; last_fired_at (if set) within the activation's
        # lifetime; expires_at (if set) > created_at.
        now = datetime.now(UTC)
        created_at_utc = (
            self.created_at
            if self.created_at.tzinfo is not None
            else self.created_at.replace(tzinfo=UTC)
        )
        if created_at_utc > now:
            raise InvalidTriggerError("created_at cannot be in the future")

        updated_at_utc = (
            self.updated_at
            if self.updated_at.tzinfo is not None
            else self.updated_at.replace(tzinfo=UTC)
        )
        if updated_at_utc < created_at_utc:
            raise InvalidTriggerError("updated_at cannot be before created_at")

        if self.last_fired_at is not None:
            last_fired_utc = (
                self.last_fired_at
                if self.last_fired_at.tzinfo is not None
                else self.last_fired_at.replace(tzinfo=UTC)
            )
            if last_fired_utc < created_at_utc:
                raise InvalidTriggerError("last_fired_at cannot be before created_at")
            if last_fired_utc > now:
                raise InvalidTriggerError("last_fired_at cannot be in the future")

        if self.expires_at is not None:
            expires_at_utc = (
                self.expires_at
                if self.expires_at.tzinfo is not None
                else self.expires_at.replace(tzinfo=UTC)
            )
            if expires_at_utc <= created_at_utc:
                raise InvalidTriggerError(
                    "expires_at must be strictly after created_at"
                )

        # EXPIRED status invariant: expires_at must be set and lapsed.
        if self.status is TriggerStatus.EXPIRED:
            if self.expires_at is None:
                raise InvalidTriggerError("EXPIRED trigger must have expires_at set")
            expires_at_utc = (
                self.expires_at
                if self.expires_at.tzinfo is not None
                else self.expires_at.replace(tzinfo=UTC)
            )
            if expires_at_utc > now:
                raise InvalidTriggerError("EXPIRED trigger must have expires_at <= now")

    # ------------------------------------------------------------------
    # Identity, hashing, repr
    # ------------------------------------------------------------------

    def __eq__(self, other: object) -> bool:
        """Equality based on ID only — entity identity, not contents."""
        if not isinstance(other, StrategyConditionTrigger):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        """Hash based on ID for use in dicts/sets."""
        return hash(self.id)

    def __repr__(self) -> str:
        """Return repr for debugging.

        Returns:
            String like
            ``StrategyConditionTrigger(id=..., condition=DRAWDOWN_THRESHOLD,
            status=ACTIVE)``.
        """
        return (
            f"StrategyConditionTrigger(id={self.id}, "
            f"activation_id={self.activation_id}, "
            f"condition={self.condition_type.value}, status={self.status.value})"
        )

    # ------------------------------------------------------------------
    # Derived predicates
    # ------------------------------------------------------------------

    @property
    def is_terminal(self) -> bool:
        """Whether the trigger has reached a terminal state."""
        return self.status in _TERMINAL_STATUSES

    def is_in_cooldown(self, *, at: datetime) -> bool:
        """Return True if cooldown is still active at ``at``.

        Args:
            at: Reference timestamp (typically the current scheduler tick).

        Returns:
            ``True`` when ``last_fired_at`` is set and the elapsed time is
            less than ``cooldown_seconds``.
        """
        if self.last_fired_at is None:
            return False
        last_fired_utc = (
            self.last_fired_at
            if self.last_fired_at.tzinfo is not None
            else self.last_fired_at.replace(tzinfo=UTC)
        )
        at_utc = at if at.tzinfo is not None else at.replace(tzinfo=UTC)
        elapsed = at_utc - last_fired_utc
        return elapsed < timedelta(seconds=self.cooldown_seconds)

    def is_evaluable(self, *, at: datetime) -> bool:
        """Return True if the trigger should be evaluated at ``at``.

        A trigger is evaluable when:

        * status is ACTIVE,
        * not in cooldown, and
        * ``expires_at`` (if set) is still in the future.

        The evaluator (F-2) calls this before pulling condition inputs;
        when ``expires_at`` has lapsed, the evaluator transitions the
        trigger to EXPIRED via :meth:`expire` instead of evaluating.

        Args:
            at: Reference timestamp.

        Returns:
            ``True`` when the trigger is eligible for evaluation.
        """
        if self.status is not TriggerStatus.ACTIVE:
            return False
        if self.is_in_cooldown(at=at):
            return False
        if self.expires_at is not None:
            expires_at_utc = (
                self.expires_at
                if self.expires_at.tzinfo is not None
                else self.expires_at.replace(tzinfo=UTC)
            )
            at_utc = at if at.tzinfo is not None else at.replace(tzinfo=UTC)
            if expires_at_utc <= at_utc:
                return False
        return True

    # ------------------------------------------------------------------
    # State-machine transitions (immutable — return new instances)
    # ------------------------------------------------------------------

    def pause(self, *, at: datetime) -> "StrategyConditionTrigger":
        """Transition ACTIVE -> PAUSED.

        Args:
            at: Timestamp at which the pause is requested. Becomes the new
                ``updated_at``.

        Returns:
            New trigger instance with ``status=PAUSED``.

        Raises:
            InvalidTriggerError: If the current status is not ACTIVE.
        """
        if self.status is not TriggerStatus.ACTIVE:
            raise InvalidTriggerError(
                f"Cannot pause trigger in {self.status.value} status; "
                "only ACTIVE triggers can be paused"
            )
        return replace(self, status=TriggerStatus.PAUSED, updated_at=at)

    def resume(self, *, at: datetime) -> "StrategyConditionTrigger":
        """Transition PAUSED -> ACTIVE.

        Args:
            at: Timestamp at which the resume is requested.

        Returns:
            New trigger instance with ``status=ACTIVE``.

        Raises:
            InvalidTriggerError: If the current status is not PAUSED.
        """
        if self.status is not TriggerStatus.PAUSED:
            raise InvalidTriggerError(
                f"Cannot resume trigger in {self.status.value} status; "
                "only PAUSED triggers can be resumed"
            )
        return replace(self, status=TriggerStatus.ACTIVE, updated_at=at)

    def disable(self, *, at: datetime) -> "StrategyConditionTrigger":
        """Transition ACTIVE / PAUSED -> MANUALLY_DISABLED (terminal).

        Used by the kill-switch (per-user and admin-wide). The state
        machine intentionally does not expose a transition out of
        MANUALLY_DISABLED — per Phase-F design Q3, the lift path is
        "delete and recreate" for v1 (simpler audit story).

        Args:
            at: Timestamp of the disable.

        Returns:
            New trigger instance with ``status=MANUALLY_DISABLED``.

        Raises:
            InvalidTriggerError: If the trigger is already terminal.
        """
        if self.is_terminal:
            raise InvalidTriggerError(
                f"Cannot disable trigger in {self.status.value} status; "
                "trigger is already terminal"
            )
        return replace(self, status=TriggerStatus.MANUALLY_DISABLED, updated_at=at)

    def expire(self, *, at: datetime) -> "StrategyConditionTrigger":
        """Transition ACTIVE / PAUSED -> EXPIRED (terminal).

        Called by the evaluator when ``expires_at`` lapses. Requires
        ``expires_at`` to be set and ``<= at``.

        Args:
            at: Timestamp at which the expiry is recorded.

        Returns:
            New trigger instance with ``status=EXPIRED``.

        Raises:
            InvalidTriggerError: If the trigger is already terminal,
                ``expires_at`` is unset, or ``expires_at > at``.
        """
        if self.is_terminal:
            raise InvalidTriggerError(
                f"Cannot expire trigger in {self.status.value} status; "
                "trigger is already terminal"
            )
        if self.expires_at is None:
            raise InvalidTriggerError("Cannot expire trigger without an expires_at set")
        expires_at_utc = (
            self.expires_at
            if self.expires_at.tzinfo is not None
            else self.expires_at.replace(tzinfo=UTC)
        )
        at_utc = at if at.tzinfo is not None else at.replace(tzinfo=UTC)
        if expires_at_utc > at_utc:
            raise InvalidTriggerError(
                f"Cannot expire trigger before expires_at "
                f"({self.expires_at!r}); requested at {at!r}"
            )
        return replace(self, status=TriggerStatus.EXPIRED, updated_at=at)

    def record_fire(self, *, fired_at: datetime) -> "StrategyConditionTrigger":
        """Update ``last_fired_at`` and ``updated_at`` after a fire.

        Does not change ``status`` — a trigger that fires stays ACTIVE
        (subject to its cooldown). The evaluator calls this after writing
        the audit row.

        Args:
            fired_at: Timestamp of the fire.

        Returns:
            New trigger instance with ``last_fired_at = fired_at`` and
            ``updated_at = fired_at``.

        Raises:
            InvalidTriggerError: If ``fired_at`` is in the future or
                precedes ``created_at`` (the entity-level invariants on
                ``last_fired_at`` are also enforced after replacement).
        """
        return replace(
            self,
            last_fired_at=fired_at,
            updated_at=fired_at,
        )
