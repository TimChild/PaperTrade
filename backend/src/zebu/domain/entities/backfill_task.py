"""BackfillTask entity — queued historical-data fetch for a single ticker.

Phase J (Task #212 Layer 2) — activation-time pre-warm.

A ``BackfillTask`` is the auditable record of "this ticker's historical
bars need to be fetched over this date range" — created either by the
:class:`HistoricalDataPrewarmer` (post-activation) or, in L4, by the
operator-facing admin endpoint. The scheduler's ``refresh_active_stocks``
pickup loop drains any ``PENDING`` tasks each cycle so transient
failures are auto-retried.

Lifecycle:

    [*] -> PENDING                 on construction (via the prewarmer)
    PENDING -> RUNNING             via ``.start_running()``
    RUNNING -> SUCCEEDED           via ``.mark_succeeded()``
    RUNNING -> FAILED              via ``.mark_failed(error_message)``
    PENDING -> FAILED              (allowed — e.g. caller short-circuits
                                    before fetching; the scheduler picks
                                    up tasks straight from PENDING, but
                                    a synchronous prewarm-then-fail does
                                    PENDING -> FAILED in one cycle)

``SUCCEEDED`` and ``FAILED`` are terminal. The entity is
``frozen=True``; transitions return new instances. Identity is by
``id`` only — equality and hashing follow the same pattern as
:class:`StrategyConditionTrigger`.

Invariants:

* ``start_date <= end_date`` (single-day ranges are allowed).
* ``created_at`` is timezone-aware UTC and not in the future.
* ``finished_at`` (when set) is timezone-aware UTC and ``>= created_at``.
* ``status in {SUCCEEDED, FAILED}`` requires ``finished_at`` set.
* ``status == FAILED`` requires ``error_message`` set.
* ``status in {PENDING, RUNNING}`` requires ``finished_at is None``.
* ``error_message`` length capped at 500 chars (truncate at write time).
"""

from dataclasses import dataclass, replace
from datetime import UTC, date, datetime
from uuid import UUID

from zebu.domain.value_objects.backfill_priority import BackfillPriority
from zebu.domain.value_objects.backfill_task_status import (
    NON_TERMINAL_STATUSES,
    TERMINAL_STATUSES,
    BackfillTaskStatus,
)
from zebu.domain.value_objects.ticker import Ticker

# Mirrors :class:`JobExecution`'s cap (Layer 1) — truncate-at-write so the
# entity itself rejects oversize payloads instead of silently swallowing.
_ERROR_MESSAGE_MAX_LENGTH: int = 500


class InvalidBackfillTaskError(ValueError):
    """Raised when a :class:`BackfillTask` invariant is violated.

    Subclass of ``ValueError`` so generic exception handlers (e.g.
    FastAPI's 422 mapping) catch it, while domain-specific tests can
    filter on the precise type.
    """


@dataclass(frozen=True)
class BackfillTask:
    """Queued historical-data fetch for one ticker over one date range.

    See module docstring for the state machine + invariants.

    Attributes:
        id: Unique task identifier.
        ticker: Stock ticker whose history we're fetching.
        start_date: First trading day of the requested range (inclusive).
        end_date: Last trading day of the requested range (inclusive).
        priority: Priority ladder — see :class:`BackfillPriority`.
        status: Current lifecycle stage.
        created_at: UTC timestamp when the task was enqueued.
        finished_at: UTC timestamp when the task reached a terminal
            status. ``None`` while ``PENDING`` / ``RUNNING``.
        error_message: Truncated reason when ``status=FAILED``. ``None``
            otherwise.

    Raises:
        InvalidBackfillTaskError: If any invariant is violated.
    """

    id: UUID
    ticker: Ticker
    start_date: date
    end_date: date
    priority: BackfillPriority
    status: BackfillTaskStatus
    created_at: datetime
    finished_at: datetime | None = None
    error_message: str | None = None

    def __post_init__(self) -> None:
        """Validate invariants after initialisation."""
        # Date range — single-day windows allowed.
        if self.end_date < self.start_date:
            raise InvalidBackfillTaskError(
                "end_date must be >= start_date "
                f"(got start_date={self.start_date}, end_date={self.end_date})"
            )

        # Timestamps: created_at must be tz-aware, not in the future.
        if self.created_at.tzinfo is None:
            raise InvalidBackfillTaskError("created_at must be timezone-aware UTC")
        now = datetime.now(UTC)
        created_at_utc = self.created_at.astimezone(UTC)
        if created_at_utc > now:
            raise InvalidBackfillTaskError("created_at cannot be in the future")

        # finished_at: tz-aware, >= created_at; required iff terminal.
        if self.finished_at is not None:
            if self.finished_at.tzinfo is None:
                raise InvalidBackfillTaskError("finished_at must be timezone-aware UTC")
            finished_at_utc = self.finished_at.astimezone(UTC)
            if finished_at_utc < created_at_utc:
                raise InvalidBackfillTaskError(
                    "finished_at must be >= created_at "
                    f"(got finished_at={self.finished_at}, "
                    f"created_at={self.created_at})"
                )

        # Status / finished_at / error_message coherence.
        if self.status in NON_TERMINAL_STATUSES and self.finished_at is not None:
            raise InvalidBackfillTaskError(
                f"status={self.status.value} requires finished_at to be None; "
                f"got finished_at={self.finished_at}"
            )
        if self.status in TERMINAL_STATUSES and self.finished_at is None:
            raise InvalidBackfillTaskError(
                f"status={self.status.value} requires finished_at to be set"
            )
        if self.status is BackfillTaskStatus.FAILED and not (
            self.error_message and self.error_message.strip()
        ):
            raise InvalidBackfillTaskError(
                "status=FAILED requires a non-empty error_message"
            )
        if (
            self.status is not BackfillTaskStatus.FAILED
            and self.error_message is not None
        ):
            raise InvalidBackfillTaskError(
                f"status={self.status.value} must not carry an error_message"
            )

        # Error message length cap. Truncate at write time; the entity
        # rejects oversize payloads.
        if (
            self.error_message is not None
            and len(self.error_message) > _ERROR_MESSAGE_MAX_LENGTH
        ):
            raise InvalidBackfillTaskError(
                "error_message must be at most "
                f"{_ERROR_MESSAGE_MAX_LENGTH} characters; truncate at write "
                f"time, got {len(self.error_message)}"
            )

    # ------------------------------------------------------------------
    # Identity, hashing, repr
    # ------------------------------------------------------------------

    def __eq__(self, other: object) -> bool:
        """Equality based on ID only — entity identity, not contents."""
        if not isinstance(other, BackfillTask):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        """Hash based on ID for use in dicts/sets."""
        return hash(self.id)

    def __repr__(self) -> str:
        """Return a debugging-friendly representation."""
        return (
            f"BackfillTask(id={self.id}, ticker={self.ticker.symbol!r}, "
            f"start_date={self.start_date}, end_date={self.end_date}, "
            f"priority={self.priority.value}, status={self.status.value})"
        )

    # ------------------------------------------------------------------
    # Derived predicates
    # ------------------------------------------------------------------

    @property
    def is_terminal(self) -> bool:
        """Whether the task has reached a terminal state."""
        return self.status in TERMINAL_STATUSES

    # ------------------------------------------------------------------
    # State-machine transitions (immutable — return new instances)
    # ------------------------------------------------------------------

    def start_running(self) -> "BackfillTask":
        """Transition PENDING -> RUNNING.

        Returns:
            New task instance with ``status=RUNNING``.

        Raises:
            InvalidBackfillTaskError: If the current status is not
                ``PENDING``.
        """
        if self.status is not BackfillTaskStatus.PENDING:
            raise InvalidBackfillTaskError(
                f"Cannot start a task in {self.status.value} status; "
                "only PENDING tasks can transition to RUNNING"
            )
        return replace(self, status=BackfillTaskStatus.RUNNING)

    def mark_succeeded(self, *, at: datetime) -> "BackfillTask":
        """Transition RUNNING -> SUCCEEDED.

        Args:
            at: Timestamp of completion (becomes ``finished_at``).

        Returns:
            New task instance in ``SUCCEEDED`` state.

        Raises:
            InvalidBackfillTaskError: If the task is already terminal.
        """
        if self.is_terminal:
            raise InvalidBackfillTaskError(
                f"Cannot succeed a task in {self.status.value} status; "
                "task is already terminal"
            )
        return replace(
            self,
            status=BackfillTaskStatus.SUCCEEDED,
            finished_at=at,
            error_message=None,
        )

    def mark_failed(self, *, error_message: str, at: datetime) -> "BackfillTask":
        """Transition PENDING / RUNNING -> FAILED.

        Args:
            error_message: Reason for failure. Truncated to 500 chars.
            at: Timestamp of failure (becomes ``finished_at``).

        Returns:
            New task instance in ``FAILED`` state.

        Raises:
            InvalidBackfillTaskError: If the task is already terminal, or
                ``error_message`` is empty after stripping.
        """
        if self.is_terminal:
            raise InvalidBackfillTaskError(
                f"Cannot fail a task in {self.status.value} status; "
                "task is already terminal"
            )
        if not error_message or not error_message.strip():
            raise InvalidBackfillTaskError(
                "mark_failed requires a non-empty error_message"
            )
        truncated = error_message[:_ERROR_MESSAGE_MAX_LENGTH]
        return replace(
            self,
            status=BackfillTaskStatus.FAILED,
            finished_at=at,
            error_message=truncated,
        )


__all__ = ["BackfillTask", "InvalidBackfillTaskError"]
