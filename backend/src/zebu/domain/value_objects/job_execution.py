"""JobExecution value object - audit row for a single scheduled-job run.

Phase J (Task #212 Layer 1) — job-health observability.

Each time the scheduler invokes one of its handlers (price refresh, daily
snapshot, strategy execution, trigger evaluation), the
``@with_job_audit`` decorator writes one :class:`JobExecution` row to the
DB. The first row is in ``RUNNING`` state; a follow-up update flips it to
``SUCCEEDED`` or ``FAILED`` with optional error / metadata.

Operators read the latest row per job via ``GET /admin/jobs/health`` to
know whether the daily cron is still healthy.

The entity is fully immutable — there is no in-place transition method.
The decorator constructs a fresh dataclass for each lifecycle stage and
hands it to the repository.

Invariants:

* ``started_at`` is timezone-aware UTC.
* ``finished_at`` (when set) is timezone-aware UTC and ``>= started_at``.
* ``status == RUNNING`` requires ``finished_at is None``.
* ``status in {SUCCEEDED, FAILED}`` requires ``finished_at is not None``.
* ``error_message`` length capped at 500 chars (matches the task spec).
* ``metadata`` is a JSON-object-like mapping — schema is per-job and
  treated as opaque by the entity.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from zebu.domain.value_objects.job_execution_status import JobExecutionStatus

# Cap error_message at the task-spec value. Anything longer is truncated at
# write time in the decorator; the entity rejects over-long messages so we
# don't silently swallow long payloads at construction.
_ERROR_MESSAGE_MAX_LENGTH: int = 500


@dataclass(frozen=True)
class JobExecution:
    """Audit row for one scheduled-job invocation.

    See module docstring for full context.

    Attributes:
        id: Unique invocation identifier.
        job_name: Stable identifier for the scheduled job. One of the
            scheduler handler names: ``refresh_active_stocks``,
            ``calculate_daily_snapshots``, ``execute_active_strategies``,
            ``evaluate_triggers``.
        started_at: UTC timestamp when the decorator opened the
            ``record_start`` session.
        finished_at: UTC timestamp when the decorator wrote the
            terminal record. ``None`` while ``status=RUNNING``.
        status: Lifecycle stage.
        error_message: Truncated exception message when ``status=FAILED``.
            ``None`` otherwise.
        metadata: Free-form JSON-object-like payload — per-job schema,
            opaque to the entity. Typical fields include
            ``duration_seconds``, ``tickers_refreshed``, etc.

    Raises:
        ValueError: If any invariant is violated.
    """

    id: UUID
    job_name: str
    started_at: datetime
    status: JobExecutionStatus
    metadata: Mapping[str, str]
    finished_at: datetime | None = None
    error_message: str | None = None

    def __post_init__(self) -> None:
        """Validate invariants and normalise opaque fields."""
        if not self.job_name:
            raise ValueError("job_name must be non-empty")

        if self.started_at.tzinfo is None:
            raise ValueError("started_at must be timezone-aware UTC")

        if self.finished_at is not None:
            if self.finished_at.tzinfo is None:
                raise ValueError("finished_at must be timezone-aware UTC")
            if self.finished_at < self.started_at:
                raise ValueError(
                    "finished_at must be >= started_at "
                    f"(got finished_at={self.finished_at}, "
                    f"started_at={self.started_at})"
                )

        # Status / finished_at coherence
        if self.status is JobExecutionStatus.RUNNING and self.finished_at is not None:
            raise ValueError(
                "status=RUNNING requires finished_at to be None; "
                f"got finished_at={self.finished_at}"
            )
        if (
            self.status in {JobExecutionStatus.SUCCEEDED, JobExecutionStatus.FAILED}
            and self.finished_at is None
        ):
            raise ValueError(
                f"status={self.status.value} requires finished_at to be set"
            )

        # Error message length cap.
        if (
            self.error_message is not None
            and len(self.error_message) > _ERROR_MESSAGE_MAX_LENGTH
        ):
            raise ValueError(
                f"error_message must be at most {_ERROR_MESSAGE_MAX_LENGTH} "
                f"characters; truncate at write time, got "
                f"{len(self.error_message)}"
            )

        # Metadata shape check (defensive — the type system already
        # constrains this, but a caller passing list/str surfaces loudly).
        if not isinstance(self.metadata, Mapping):  # type: ignore[unreachable]  # defensive
            raise ValueError(
                "metadata must be a JSON-object-like mapping of str -> str"
            )

        # Freeze the metadata into a fresh dict to insulate the entity from
        # caller-side mutation of the input.
        object.__setattr__(self, "metadata", dict(self.metadata))

    def __eq__(self, other: object) -> bool:
        """Equality based on ID only — entity identity, not contents."""
        if not isinstance(other, JobExecution):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        """Hash based on ID for use in dicts/sets."""
        return hash(self.id)

    def __repr__(self) -> str:
        """Return repr for debugging."""
        return (
            f"JobExecution(id={self.id}, job_name={self.job_name!r}, "
            f"status={self.status.value}, started_at={self.started_at.isoformat()})"
        )


__all__ = ["JobExecution"]
