"""ExplorationTaskRepository port — persistence contract for exploration tasks.

Implementations live in:

* ``adapters/outbound/database/exploration_task_repository.py`` — SQLModel
  backed by Postgres / SQLite.
* ``application/ports/in_memory_exploration_task_repository.py`` — in-memory,
  used by unit / integration tests.

The atomic ``claim_atomic`` method is the load-bearing one for Phase D's
agent claim flow: two agents must never end up working the same task. The
SQLModel adapter uses an ``UPDATE ... WHERE status='OPEN' RETURNING *``
pattern (via SQLAlchemy ``update().returning()`` with row-locking semantics
where the dialect supports it) so the race is resolved at the database
layer; the in-memory adapter uses a ``threading.Lock``.
"""

from datetime import datetime
from typing import Protocol
from uuid import UUID

from zebu.domain.entities.exploration_task import (
    ExplorationTask,
    ExplorationTaskStatus,
)


class ExplorationTaskRepository(Protocol):
    """Persistence contract for ``ExplorationTask`` entities.

    All methods are async to support both database and in-memory
    implementations. The repository is the single way the application layer
    persists exploration tasks; the API layer constructs the entity, the
    repository persists it.
    """

    async def get(self, task_id: UUID) -> ExplorationTask | None:
        """Retrieve a single exploration task by ID.

        Args:
            task_id: Unique identifier of the task.

        Returns:
            The ExplorationTask if found, ``None`` otherwise.
        """
        ...

    async def list_by_status(
        self,
        status: ExplorationTaskStatus,
        *,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[ExplorationTask]:
        """List tasks filtered by status, oldest-first.

        Backs the agent-facing "what's open?" queue query. Ordering is
        ``created_at`` ascending so OLDEST tasks are at the head of the
        page — agents naturally pick up the oldest open task first.

        Args:
            status: Status to filter on.
            limit: Optional cap on rows returned. ``None`` means no cap;
                callers wanting full pages should pass an explicit limit
                from the API's pagination params.
            offset: Number of rows to skip for pagination.

        Returns:
            List of ExplorationTask entities matching ``status``.
        """
        ...

    async def list_for_user(
        self,
        user_id: UUID,
        *,
        status: ExplorationTaskStatus | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[ExplorationTask]:
        """List all tasks created by a user, newest-first.

        Backs the human's "my tasks" view. Ordering is ``created_at``
        descending so the human sees their most recently filed tasks first.

        Args:
            user_id: User whose tasks to return (matches ``created_by``).
            status: Optional status filter — when ``None``, returns tasks in
                every status.
            limit: Optional row cap for paging. ``None`` means no cap.
            offset: Number of rows to skip for pagination.

        Returns:
            List of ExplorationTask entities owned by ``user_id``.
        """
        ...

    async def count_by_status(
        self,
        status: ExplorationTaskStatus,
    ) -> int:
        """Total count of tasks with the given status.

        Used by paginated list endpoints to populate ``PaginatedResponse.total``
        without fetching every row.

        Args:
            status: Status to count.

        Returns:
            Total count of matching rows.
        """
        ...

    async def count_for_user(
        self,
        user_id: UUID,
        *,
        status: ExplorationTaskStatus | None = None,
    ) -> int:
        """Total count of tasks owned by a user, optionally status-filtered.

        Used by paginated list endpoints to populate ``PaginatedResponse.total``.

        Args:
            user_id: User whose tasks to count.
            status: Optional status filter.

        Returns:
            Total count of matching rows.
        """
        ...

    async def save(
        self,
        task: ExplorationTask,
        *,
        api_key_id: UUID | None = None,
    ) -> None:
        """Persist a task (create if new, update if existing).

        Idempotent: calling ``save`` on the same entity twice produces the
        same database state.

        Args:
            task: Entity to persist.
            api_key_id: Phase H2 — ID of the API key that authenticated the
                writing request, or None for Clerk Bearer (human via UI).
                Stamped only on insert.
        """
        ...

    async def delete(self, task_id: UUID) -> None:
        """Delete a task by ID.

        No-op if the task does not exist. Used by the ``DELETE`` endpoint
        as the "abandon and remove" operation; for "abandon but retain
        audit history", callers should call ``ExplorationTask.abandon`` and
        ``save`` instead.

        Args:
            task_id: Identifier of the task to delete.
        """
        ...

    async def claim_atomic(
        self,
        task_id: UUID,
        *,
        agent_id: str,
        claimed_at: datetime,
    ) -> ExplorationTask | None:
        """Atomically transition OPEN -> IN_PROGRESS for one task.

        Race-safe: when two agents call ``claim_atomic(same_id)`` only one
        wins. The losing call returns ``None``. Implementations achieve this
        by issuing a single UPDATE statement that sets ``status``,
        ``claimed_by``, ``claimed_at``, ``updated_at`` only when the row's
        current ``status`` is OPEN — so the database serialises the
        contention, not application code.

        Args:
            task_id: Task to claim.
            agent_id: Identifier of the claiming agent (free-form).
                Must be non-empty.
            claimed_at: Timestamp at which the claim happens.

        Returns:
            The updated ExplorationTask in IN_PROGRESS state if the claim
            succeeded, or ``None`` if the row no longer exists or was not
            OPEN at claim time.
        """
        ...
