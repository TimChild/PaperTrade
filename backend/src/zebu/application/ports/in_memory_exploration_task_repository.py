"""In-memory implementation of ExplorationTaskRepository for testing.

Thread-safe; suitable for unit / integration tests that don't need
database persistence. The atomic ``claim_atomic`` method holds the lock
across the read-and-update so two concurrent claim attempts cannot both
succeed.
"""

from datetime import datetime
from threading import Lock
from uuid import UUID

from zebu.domain.entities.exploration_task import (
    ExplorationTask,
    ExplorationTaskStatus,
)


class InMemoryExplorationTaskRepository:
    """In-memory implementation of ExplorationTaskRepository protocol."""

    def __init__(self) -> None:
        """Initialize empty task storage."""
        self._tasks: dict[UUID, ExplorationTask] = {}
        self._lock = Lock()

    async def get(self, task_id: UUID) -> ExplorationTask | None:
        """Retrieve a single task by ID."""
        with self._lock:
            return self._tasks.get(task_id)

    async def list_by_status(
        self,
        status: ExplorationTaskStatus,
        *,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[ExplorationTask]:
        """List tasks filtered by status, oldest-first."""
        with self._lock:
            matching = [t for t in self._tasks.values() if t.status is status]
            ordered = sorted(matching, key=lambda t: t.created_at)
            if limit is None:
                return ordered[offset:]
            return ordered[offset : offset + limit]

    async def list_for_user(
        self,
        user_id: UUID,
        *,
        status: ExplorationTaskStatus | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[ExplorationTask]:
        """List tasks owned by a user, newest-first."""
        with self._lock:
            matching = [t for t in self._tasks.values() if t.created_by == user_id]
            if status is not None:
                matching = [t for t in matching if t.status is status]
            # Newest first
            ordered = sorted(matching, key=lambda t: t.created_at, reverse=True)
            if limit is None:
                return ordered[offset:]
            return ordered[offset : offset + limit]

    async def count_by_status(
        self,
        status: ExplorationTaskStatus,
    ) -> int:
        """Count tasks with the given status."""
        with self._lock:
            return sum(1 for t in self._tasks.values() if t.status is status)

    async def count_for_user(
        self,
        user_id: UUID,
        *,
        status: ExplorationTaskStatus | None = None,
    ) -> int:
        """Count tasks owned by a user, optionally status-filtered."""
        with self._lock:
            count = 0
            for t in self._tasks.values():
                if t.created_by != user_id:
                    continue
                if status is not None and t.status is not status:
                    continue
                count += 1
            return count

    async def save(self, task: ExplorationTask) -> None:
        """Persist a task (idempotent upsert)."""
        with self._lock:
            self._tasks[task.id] = task

    async def delete(self, task_id: UUID) -> None:
        """Delete a task by ID (no-op if missing)."""
        with self._lock:
            self._tasks.pop(task_id, None)

    async def claim_atomic(
        self,
        task_id: UUID,
        *,
        agent_id: str,
        claimed_at: datetime,
    ) -> ExplorationTask | None:
        """Atomically claim a task — race-safe under concurrent callers.

        Holds the repository lock for the duration of the
        read-current-status / write-claimed-state sequence so two
        simultaneous claim attempts cannot both succeed.
        """
        with self._lock:
            current = self._tasks.get(task_id)
            if current is None:
                return None
            if current.status is not ExplorationTaskStatus.OPEN:
                return None

            # Use the entity's claim() helper to keep invariant logic in
            # one place (the entity).
            claimed = current.claim(agent_id=agent_id, claimed_at=claimed_at)
            self._tasks[task_id] = claimed
            return claimed

    def clear(self) -> None:
        """Clear all tasks (for testing)."""
        with self._lock:
            self._tasks.clear()
