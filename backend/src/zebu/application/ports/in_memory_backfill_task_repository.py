"""In-memory implementation of :class:`BackfillTaskRepositoryPort`.

Phase J (Task #212 Layer 2).

Thread-safe. Mirrors the SQL adapter's semantics exactly so unit and
integration tests can use it interchangeably with the production
:class:`SQLModelBackfillTaskRepository`. Used by:

* Prewarmer unit tests (in-memory port + in-memory market data).
* Tests that need to assert the task queue's state without spinning up
  a SQL session.
"""

from collections.abc import Collection
from datetime import UTC, date, datetime
from threading import Lock
from uuid import UUID

from zebu.domain.entities.backfill_task import BackfillTask
from zebu.domain.value_objects.backfill_task_status import BackfillTaskStatus
from zebu.domain.value_objects.ticker import Ticker

# Mirrors the entity-level cap in :mod:`zebu.domain.entities.backfill_task`.
_ERROR_MESSAGE_MAX_LENGTH: int = 500


class InMemoryBackfillTaskRepository:
    """In-memory implementation of :class:`BackfillTaskRepositoryPort`."""

    def __init__(self) -> None:
        """Initialise empty storage."""
        self._rows: dict[UUID, BackfillTask] = {}
        self._lock = Lock()

    async def create(self, task: BackfillTask) -> BackfillTask:
        """Insert a fresh row and return the persisted entity."""
        with self._lock:
            if task.id in self._rows:
                raise ValueError(f"BackfillTask with id={task.id} already exists")
            self._rows[task.id] = task
        return task

    async def find_existing(
        self,
        ticker: Ticker,
        start_date: date,
        end_date: date,
        *,
        status_in: Collection[BackfillTaskStatus],
    ) -> BackfillTask | None:
        """Return the newest matching row, or ``None`` if none."""
        status_set = set(status_in)
        with self._lock:
            matches = [
                row
                for row in self._rows.values()
                if row.ticker == ticker
                and row.start_date == start_date
                and row.end_date == end_date
                and (not status_set or row.status in status_set)
            ]
        if not matches:
            return None
        # Newest first so callers reasoning about "currently queued"
        # see the latest row.
        return max(matches, key=lambda r: r.created_at)

    async def mark_running(self, task_id: UUID) -> BackfillTask:
        """Flip PENDING -> RUNNING."""
        with self._lock:
            existing = self._rows.get(task_id)
            if existing is None:
                raise ValueError(f"BackfillTask not found: {task_id}")
            updated = existing.start_running()
            self._rows[task_id] = updated
            return updated

    async def mark_succeeded(self, task_id: UUID) -> BackfillTask:
        """Flip RUNNING -> SUCCEEDED."""
        with self._lock:
            existing = self._rows.get(task_id)
            if existing is None:
                raise ValueError(f"BackfillTask not found: {task_id}")
            updated = existing.mark_succeeded(at=datetime.now(UTC))
            self._rows[task_id] = updated
            return updated

    async def mark_failed(
        self,
        task_id: UUID,
        *,
        error_message: str,
    ) -> BackfillTask:
        """Flip PENDING/RUNNING -> FAILED with a truncated reason."""
        truncated = error_message[:_ERROR_MESSAGE_MAX_LENGTH] if error_message else ""
        with self._lock:
            existing = self._rows.get(task_id)
            if existing is None:
                raise ValueError(f"BackfillTask not found: {task_id}")
            updated = existing.mark_failed(
                error_message=truncated, at=datetime.now(UTC)
            )
            self._rows[task_id] = updated
            return updated

    async def list_pending(self, *, limit: int) -> list[BackfillTask]:
        """Return up to ``limit`` PENDING tasks, oldest-first."""
        if limit <= 0:
            raise ValueError(f"limit must be > 0, got {limit}")
        with self._lock:
            pending = [
                row
                for row in self._rows.values()
                if row.status is BackfillTaskStatus.PENDING
            ]
        ordered = sorted(pending, key=lambda r: r.created_at)
        return ordered[:limit]

    def clear(self) -> None:
        """Clear all rows (test helper)."""
        with self._lock:
            self._rows.clear()
