"""In-memory implementation of JobExecutionRepository for testing.

Phase J (Task #212 Layer 1).

Thread-safe. Mirrors the contract semantics of the SQL adapter:

* ``record_start`` assigns a fresh UUID + ``started_at`` and inserts a
  ``RUNNING`` row.
* ``record_finish`` replaces the row in place with the terminal entity.
* ``latest`` returns the newest-``started_at`` row for the given job.
* ``list_recent`` returns newest-first.

Used by unit tests for the decorator and the endpoint.
"""

from collections.abc import Mapping
from datetime import UTC, datetime
from threading import Lock
from uuid import UUID, uuid4

from zebu.domain.value_objects.job_execution import JobExecution
from zebu.domain.value_objects.job_execution_status import JobExecutionStatus


class InMemoryJobExecutionRepository:
    """In-memory implementation of :class:`JobExecutionRepositoryPort`."""

    def __init__(self) -> None:
        """Initialise empty audit storage."""
        self._rows: dict[UUID, JobExecution] = {}
        self._lock = Lock()

    async def record_start(
        self,
        job_name: str,
        *,
        metadata: Mapping[str, str] | None = None,
    ) -> JobExecution:
        """Insert a fresh ``RUNNING`` row and return it."""
        execution = JobExecution(
            id=uuid4(),
            job_name=job_name,
            started_at=datetime.now(UTC),
            status=JobExecutionStatus.RUNNING,
            metadata=dict(metadata) if metadata is not None else {},
        )
        with self._lock:
            self._rows[execution.id] = execution
        return execution

    async def record_finish(
        self,
        execution: JobExecution,
        *,
        status: JobExecutionStatus,
        error_message: str | None = None,
        metadata: Mapping[str, str] | None = None,
    ) -> JobExecution:
        """Flip an existing row to its terminal status.

        Raises:
            ValueError: If ``status`` is ``RUNNING`` or the underlying
                row is missing.
        """
        if status is JobExecutionStatus.RUNNING:
            raise ValueError("record_finish requires a terminal status; got RUNNING")
        with self._lock:
            existing = self._rows.get(execution.id)
            if existing is None:
                raise ValueError(
                    f"JobExecution with id={execution.id} not found; "
                    "record_start must precede record_finish"
                )

            merged_metadata: dict[str, str] = dict(existing.metadata)
            if metadata is not None:
                merged_metadata.update(metadata)

            updated = JobExecution(
                id=existing.id,
                job_name=existing.job_name,
                started_at=existing.started_at,
                status=status,
                metadata=merged_metadata,
                finished_at=datetime.now(UTC),
                error_message=error_message,
            )
            self._rows[updated.id] = updated
            return updated

    async def latest(self, job_name: str) -> JobExecution | None:
        """Return the most recent run of ``job_name`` (highest ``started_at``)."""
        with self._lock:
            matching = [r for r in self._rows.values() if r.job_name == job_name]
            if not matching:
                return None
            return max(matching, key=lambda r: r.started_at)

    async def list_recent(
        self,
        job_name: str | None = None,
        *,
        limit: int = 50,
    ) -> list[JobExecution]:
        """Return newest-first audit rows, optionally filtered by job."""
        with self._lock:
            if job_name is None:
                pool = list(self._rows.values())
            else:
                pool = [r for r in self._rows.values() if r.job_name == job_name]
            ordered = sorted(pool, key=lambda r: r.started_at, reverse=True)
            return ordered[:limit]

    def clear(self) -> None:
        """Clear all records (for testing)."""
        with self._lock:
            self._rows.clear()
