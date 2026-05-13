"""JobExecutionRepository port — persistence contract for the job-health audit log.

Phase J (Task #212 Layer 1).

Models the lifecycle of one scheduled-job invocation as two writes:

1. ``record_start`` — writes a fresh row in ``RUNNING`` state when the
   ``@with_job_audit`` decorator wraps a scheduler handler.
2. ``record_finish`` — flips the same row to ``SUCCEEDED`` / ``FAILED``
   with optional duration / error metadata.

Read methods support the ``GET /admin/jobs/health`` endpoint:

* ``latest(job_name)`` — most-recent row for a single job (drives the
  "is stale?" computation).
* ``list_recent(job_name, limit)`` — newest-first window for diagnostics.

Implementations live in:

* ``adapters/outbound/database/job_execution_repository.py`` — SQLModel
  backed by Postgres / SQLite.
* ``application/ports/in_memory_job_execution_repository.py`` — in-memory
  variant for unit / integration tests.
"""

from collections.abc import Mapping
from typing import Protocol

from zebu.domain.value_objects.job_execution import JobExecution


class JobExecutionRepositoryPort(Protocol):
    """Persistence contract for :class:`JobExecution` entities.

    The contract treats inserts and lifecycle updates as separate methods
    (``record_start`` / ``record_finish``) so callers can't accidentally
    re-open a terminal row. Reads are owner-scoped on ``job_name`` since
    the table is global (one feed across all users).
    """

    async def record_start(
        self,
        job_name: str,
        *,
        metadata: Mapping[str, str] | None = None,
    ) -> JobExecution:
        """Insert a fresh ``RUNNING`` row for the job and return it.

        The repository assigns the ``id`` and ``started_at`` so the
        decorator never has to thread them through. The returned entity
        is the canonical handle the caller hands back to
        :meth:`record_finish`.

        Args:
            job_name: Stable scheduler-handler name (e.g.
                ``"refresh_active_stocks"``).
            metadata: Optional starter metadata. Empty dict if omitted.

        Returns:
            The newly persisted :class:`JobExecution` in ``RUNNING`` state.
        """
        ...

    async def record_finish(
        self,
        execution: JobExecution,
        *,
        status: "JobExecutionStatusLike",
        error_message: str | None = None,
        metadata: Mapping[str, str] | None = None,
    ) -> JobExecution:
        """Flip a ``RUNNING`` row to its terminal status.

        ``status`` must be ``SUCCEEDED`` or ``FAILED``; passing
        ``RUNNING`` is a programming error and raises ``ValueError``.

        ``metadata`` is *merged* with whatever was passed to
        ``record_start`` (caller-side keys win on conflict). ``None``
        means "no additional metadata".

        Args:
            execution: The handle returned from :meth:`record_start`.
            status: Terminal status (``SUCCEEDED`` or ``FAILED``).
            error_message: Truncated exception message for ``FAILED``.
            metadata: Additional metadata to merge with the starter set.

        Returns:
            The updated :class:`JobExecution` row (with
            ``finished_at`` populated and ``status`` set).

        Raises:
            ValueError: If ``status`` is ``RUNNING`` or the underlying
                row is missing.
        """
        ...

    async def latest(self, job_name: str) -> JobExecution | None:
        """Return the most recent run of ``job_name``, or ``None`` if never run.

        "Most recent" means highest ``started_at``. A row left in
        ``RUNNING`` is still the most recent — callers (the health
        endpoint) decide whether to treat it as stale based on the
        run's duration.

        Args:
            job_name: Stable scheduler-handler name.

        Returns:
            The latest :class:`JobExecution` or ``None``.
        """
        ...

    async def list_recent(
        self,
        job_name: str | None = None,
        *,
        limit: int = 50,
    ) -> list[JobExecution]:
        """Return newest-first audit rows, optionally filtered by job.

        Args:
            job_name: When set, only return runs of that job. ``None``
                returns runs across every job.
            limit: Maximum rows to return (default 50).

        Returns:
            List of :class:`JobExecution` ordered by ``started_at``
            descending.
        """
        ...


# Forward-reference shim — the JobExecutionStatus enum is in the domain
# layer; importing it here would create no real coupling (ports may
# depend on domain), but documenting it via a string-typed alias keeps
# the file readable for the protocol-only reader. The actual import is
# made by implementations.
from zebu.domain.value_objects.job_execution_status import (  # noqa: E402
    JobExecutionStatus as JobExecutionStatusLike,
)
