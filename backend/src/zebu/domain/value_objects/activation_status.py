"""ActivationStatus value object - lifecycle state of a strategy activation."""

from enum import Enum


class ActivationStatus(Enum):
    """Represents the execution status of a strategy activation.

    State transitions (informational — enforced by service layer, not the entity):

    - ``ACTIVE`` — Activation is enabled and will be executed by the scheduler.
    - ``PAUSED`` — Temporarily disabled by the user; can resume to ``ACTIVE``.
    - ``STOPPED`` — Permanently terminated; should not transition back to
      ``ACTIVE`` (a fresh activation is required).
    - ``ERROR`` — Last execution failed; ``last_error`` should describe why.
      The scheduler may auto-pause activations in this state pending operator
      review.
    """

    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    STOPPED = "STOPPED"
    ERROR = "ERROR"
