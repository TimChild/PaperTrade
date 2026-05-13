"""BackfillTaskStatus value object — lifecycle state of a queued backfill.

Phase J (Task #212 Layer 2) — activation-time pre-warm.

Each :class:`BackfillTask` row walks the following state machine:

* ``PENDING`` — written by the prewarmer (or the operator-driven endpoint
  in L4); waiting for a worker to claim it.
* ``RUNNING`` — claimed by the prewarmer / scheduler pickup loop; the
  Alpha Vantage fetch is in-flight.
* ``SUCCEEDED`` — terminal happy path. ``finished_at`` is populated;
  ``error_message`` is ``None``.
* ``FAILED`` — terminal sad path. ``finished_at`` is populated and
  ``error_message`` carries a truncated reason.

Transitions are enforced at the application layer (the prewarmer and
the repository's ``mark_*`` helpers). The enum itself is a plain
``StrEnum`` so the wire / DB values are stable strings.
"""

from enum import StrEnum


class BackfillTaskStatus(StrEnum):
    """Status of a single :class:`BackfillTask` row.

    See module docstring for state semantics.
    """

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


# Sets of related statuses pinned here so callers stay in sync — used
# by the prewarmer (idempotency) and the scheduler pickup loop.
NON_TERMINAL_STATUSES: frozenset[BackfillTaskStatus] = frozenset(
    {BackfillTaskStatus.PENDING, BackfillTaskStatus.RUNNING}
)
TERMINAL_STATUSES: frozenset[BackfillTaskStatus] = frozenset(
    {BackfillTaskStatus.SUCCEEDED, BackfillTaskStatus.FAILED}
)


__all__ = [
    "BackfillTaskStatus",
    "NON_TERMINAL_STATUSES",
    "TERMINAL_STATUSES",
]
