"""TriggerStatus value object — lifecycle state of a strategy-condition trigger.

The trigger's lifecycle is described in
``docs/architecture/phase-f-agent-in-the-loop.md`` §1.3:

    [*] -> ACTIVE on construction
    ACTIVE  <-> PAUSED                   (pause / resume)
    ACTIVE / PAUSED -> EXPIRED           (evaluator sees expires_at <= now)
    ACTIVE / PAUSED -> MANUALLY_DISABLED (kill-switch / admin disable)

``EXPIRED`` and ``MANUALLY_DISABLED`` are terminal — the entity does not
expose a transition out of them. ``MANUALLY_DISABLED`` exists as a
distinct value (rather than reusing ``PAUSED``) so the audit trail can
distinguish "the user asked us to stop" from "an admin / kill switch
stopped it" — important for "why did all my triggers stop" debugging.

Stored as a string in the DB (matches the existing pattern used by
:class:`ActivationStatus`, :class:`ExplorationTaskStatus`, etc.).
"""

from enum import StrEnum


class TriggerStatus(StrEnum):
    """Represents the lifecycle status of a strategy-condition trigger.

    Values:
        ACTIVE: Trigger is enabled and will be evaluated each scheduler tick.
        PAUSED: Temporarily disabled by the user. Can resume to ACTIVE.
        EXPIRED: ``expires_at`` has lapsed; the evaluator transitioned the
            trigger to this state. Terminal.
        MANUALLY_DISABLED: Kill-switch or admin-disabled. Terminal — leaves
            a different audit signal from ``PAUSED`` so operators can tell
            "user paused" from "admin stopped".
    """

    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    EXPIRED = "EXPIRED"
    MANUALLY_DISABLED = "MANUALLY_DISABLED"
