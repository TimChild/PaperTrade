"""SQLModel implementation of :class:`JobExecutionRepositoryPort`.

Phase J (Task #212 Layer 1) — job-health observability.

Persists scheduled-job audit rows. Writes go through two methods:

* ``record_start`` — INSERT a fresh row in ``RUNNING`` state, return the
  domain entity (with assigned id + ``started_at``).
* ``record_finish`` — UPDATE the same row in place with terminal status,
  optional error, and merged metadata.

Reads back the row by id between the two write calls. The
``@with_job_audit`` decorator opens its OWN session so the audit row is
not bundled with the wrapped job's unit of work — a job rollback must
not erase the audit.

Indexed on ``(job_name, started_at DESC)`` so the per-job ``latest``
lookup is O(1) at any volume.
"""

from collections.abc import Mapping
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from zebu.adapters.outbound.database.models import JobExecutionModel
from zebu.domain.value_objects.job_execution import JobExecution
from zebu.domain.value_objects.job_execution_status import JobExecutionStatus


class SQLModelJobExecutionRepository:
    """SQLModel implementation of :class:`JobExecutionRepositoryPort`."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialise with an async DB session.

        Args:
            session: Async session for this unit of work. The decorator
                hands in a *fresh* session (not the wrapped job's
                session) so a job-level rollback can't drop the audit.
        """
        self._session = session

    async def record_start(
        self,
        job_name: str,
        *,
        metadata: Mapping[str, str] | None = None,
    ) -> JobExecution:
        """Insert a fresh ``RUNNING`` row and return the domain entity."""
        execution = JobExecution(
            id=uuid4(),
            job_name=job_name,
            started_at=datetime.now(UTC),
            status=JobExecutionStatus.RUNNING,
            metadata=dict(metadata) if metadata is not None else {},
        )
        model = JobExecutionModel.from_domain(execution)
        self._session.add(model)
        # Flush so the row is visible to subsequent reads within this
        # session — the caller commits before returning control to the
        # wrapped job, but record_finish may use a fresh session and
        # rely on the row being persisted.
        await self._session.flush()
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

        Loads the existing row by id and updates it in place. ``metadata``
        is merged with whatever was passed to :meth:`record_start`
        (caller-side keys win on conflict).

        Raises:
            ValueError: If ``status`` is ``RUNNING`` or the underlying
                row is missing.
        """
        if status is JobExecutionStatus.RUNNING:
            raise ValueError("record_finish requires a terminal status; got RUNNING")

        existing = await self._session.get(JobExecutionModel, execution.id)
        if existing is None:
            raise ValueError(
                f"JobExecution with id={execution.id} not found; "
                "record_start must precede record_finish"
            )

        # Merge metadata: existing baseline + caller's additions. The
        # baseline comes from the DB row in case the entity handed to
        # us was a stale copy from an earlier session.
        merged_metadata: dict[str, str] = {
            str(k): str(v) for k, v in existing.metadata_json.items()
        }
        if metadata is not None:
            merged_metadata.update({str(k): str(v) for k, v in metadata.items()})

        finished_at_utc = datetime.now(UTC)
        # PostgreSQL columns are TIMESTAMP WITHOUT TIME ZONE — strip to naive.
        existing.finished_at = finished_at_utc.replace(tzinfo=None)
        existing.status = status.value
        existing.error_message = error_message
        existing.metadata_json = merged_metadata
        self._session.add(existing)
        await self._session.flush()

        return existing.to_domain()

    async def latest(self, job_name: str) -> JobExecution | None:
        """Return the most-recent run of ``job_name``, or ``None`` if never run.

        Backed by the ``(job_name, started_at)`` index — single-row
        seek with no scan.
        """
        statement = (
            select(JobExecutionModel)
            .where(JobExecutionModel.job_name == job_name)
            .order_by(col(JobExecutionModel.started_at).desc())
            .limit(1)
        )
        result = await self._session.exec(statement)
        first = result.first()
        if first is None:
            return None
        return first.to_domain()

    async def list_recent(
        self,
        job_name: str | None = None,
        *,
        limit: int = 50,
    ) -> list[JobExecution]:
        """Return newest-first audit rows, optionally filtered by job."""
        statement = select(JobExecutionModel).order_by(
            col(JobExecutionModel.started_at).desc()
        )
        if job_name is not None:
            statement = statement.where(JobExecutionModel.job_name == job_name)
        statement = statement.limit(limit)
        result = await self._session.exec(statement)
        models = result.all()
        return [model.to_domain() for model in models]


# UUID re-exported for downstream test fixtures that need to build a
# row directly (parity with other adapters in this package).
__all__ = ["SQLModelJobExecutionRepository", "UUID"]
