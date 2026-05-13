"""SQLModel implementation of :class:`BackfillTaskRepositoryPort`.

Phase J (Task #212 Layer 2) — activation-time pre-warm.

Persists :class:`BackfillTask` rows. Each transition method
(``mark_running`` / ``mark_succeeded`` / ``mark_failed``) loads the row
by id, applies the entity's state-machine transition, and UPDATEs in
place. This keeps the state machine in the domain layer while the
adapter handles ORM bookkeeping.

The ``find_existing`` and ``list_pending`` queries are both backed by
the ``idx_backfill_tasks_status_created_at`` index so the scheduler's
hot pickup loop stays O(log N) at any volume.
"""

from collections.abc import Collection
from datetime import UTC, date, datetime
from uuid import UUID

from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from zebu.adapters.outbound.database.models import BackfillTaskModel
from zebu.application.ports.backfill_task_repository import (
    BackfillTaskRepositoryPort,
)
from zebu.domain.entities.backfill_task import BackfillTask
from zebu.domain.value_objects.backfill_task_status import BackfillTaskStatus
from zebu.domain.value_objects.ticker import Ticker

# Mirrors the entity-level cap so we truncate consistently at write time.
_ERROR_MESSAGE_MAX_LENGTH: int = 500


class SQLModelBackfillTaskRepository(BackfillTaskRepositoryPort):
    """SQLModel implementation of :class:`BackfillTaskRepositoryPort`."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialise with an async DB session.

        Args:
            session: Async session bound to the current unit of work.
        """
        self._session = session

    async def create(self, task: BackfillTask) -> BackfillTask:
        """Insert a fresh row and return the persisted entity."""
        model = BackfillTaskModel.from_domain(task)
        self._session.add(model)
        await self._session.flush()
        return task

    async def find_existing(
        self,
        ticker: Ticker,
        start_date: date,
        end_date: date,
        *,
        status_in: Collection[BackfillTaskStatus],
    ) -> BackfillTask | None:
        """Return the newest matching task, or ``None`` if none."""
        statement = (
            select(BackfillTaskModel)
            .where(BackfillTaskModel.ticker == ticker.symbol)
            .where(BackfillTaskModel.start_date == start_date)
            .where(BackfillTaskModel.end_date == end_date)
            .order_by(col(BackfillTaskModel.created_at).desc())
        )
        status_values = [s.value for s in status_in]
        if status_values:
            statement = statement.where(
                col(BackfillTaskModel.status).in_(status_values)
            )
        statement = statement.limit(1)
        result = await self._session.exec(statement)
        first = result.first()
        if first is None:
            return None
        return first.to_domain()

    async def mark_running(self, task_id: UUID) -> BackfillTask:
        """Flip PENDING -> RUNNING.

        Raises:
            ValueError: If the task is missing or not in PENDING.
        """
        existing_model = await self._session.get(BackfillTaskModel, task_id)
        if existing_model is None:
            raise ValueError(f"BackfillTask not found: {task_id}")
        domain = existing_model.to_domain()
        updated = domain.start_running()
        existing_model.status = updated.status.value
        self._session.add(existing_model)
        await self._session.flush()
        return updated

    async def mark_succeeded(self, task_id: UUID) -> BackfillTask:
        """Flip RUNNING -> SUCCEEDED.

        Raises:
            ValueError: If the task is missing or already terminal.
        """
        existing_model = await self._session.get(BackfillTaskModel, task_id)
        if existing_model is None:
            raise ValueError(f"BackfillTask not found: {task_id}")
        domain = existing_model.to_domain()
        updated = domain.mark_succeeded(at=datetime.now(UTC))
        existing_model.status = updated.status.value
        existing_model.finished_at = (
            updated.finished_at.astimezone(UTC).replace(tzinfo=None)
            if updated.finished_at is not None
            else None
        )
        existing_model.error_message = None
        self._session.add(existing_model)
        await self._session.flush()
        return updated

    async def mark_failed(
        self,
        task_id: UUID,
        *,
        error_message: str,
    ) -> BackfillTask:
        """Flip PENDING/RUNNING -> FAILED with a truncated reason.

        Raises:
            ValueError: If the task is missing or already terminal.
        """
        existing_model = await self._session.get(BackfillTaskModel, task_id)
        if existing_model is None:
            raise ValueError(f"BackfillTask not found: {task_id}")
        domain = existing_model.to_domain()
        truncated = error_message[:_ERROR_MESSAGE_MAX_LENGTH] if error_message else ""
        if not truncated.strip():
            # Provide a stable fallback so the entity's invariant
            # (non-empty error_message) is satisfied without leaking
            # an empty-string failure into the audit log.
            truncated = "Unknown error"
        updated = domain.mark_failed(error_message=truncated, at=datetime.now(UTC))
        existing_model.status = updated.status.value
        existing_model.finished_at = (
            updated.finished_at.astimezone(UTC).replace(tzinfo=None)
            if updated.finished_at is not None
            else None
        )
        existing_model.error_message = updated.error_message
        self._session.add(existing_model)
        await self._session.flush()
        return updated

    async def list_pending(self, *, limit: int) -> list[BackfillTask]:
        """Return up to ``limit`` PENDING tasks, oldest-first."""
        if limit <= 0:
            raise ValueError(f"limit must be > 0, got {limit}")
        statement = (
            select(BackfillTaskModel)
            .where(BackfillTaskModel.status == BackfillTaskStatus.PENDING.value)
            .order_by(col(BackfillTaskModel.created_at).asc())
            .limit(limit)
        )
        result = await self._session.exec(statement)
        models = result.all()
        return [model.to_domain() for model in models]


__all__ = ["SQLModelBackfillTaskRepository"]
