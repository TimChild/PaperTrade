"""BackfillTaskRepository port — persistence contract for the backfill queue.

Phase J (Task #212 Layer 2) — activation-time pre-warm.

Models the lifecycle of one :class:`BackfillTask` row as a small set of
focused methods. The split between ``create`` and the ``mark_*``
transitions matches the entity's state machine — callers can't
accidentally insert a row in a terminal status or skip past
``RUNNING``.

* ``create(task)`` — INSERT a fresh row (typically PENDING).
* ``find_existing(...)`` — idempotency check used by the prewarmer to
  avoid duplicating an already-queued range for the same ticker.
* ``mark_running(task_id)`` — flip PENDING -> RUNNING.
* ``mark_succeeded(task_id)`` — flip RUNNING -> SUCCEEDED.
* ``mark_failed(task_id, error_message)`` — flip PENDING/RUNNING -> FAILED.
* ``list_pending(limit)`` — newest-first pending tasks for the scheduler's
  pickup loop.

Implementations live in:

* ``adapters/outbound/database/backfill_task_repository.py`` — SQLModel
  backed by Postgres / SQLite (the production path).
* ``application/ports/in_memory_backfill_task_repository.py`` — in-memory
  variant for unit / integration tests.
"""

from collections.abc import Collection
from datetime import date
from typing import Protocol
from uuid import UUID

from zebu.domain.entities.backfill_task import BackfillTask
from zebu.domain.value_objects.backfill_task_status import BackfillTaskStatus
from zebu.domain.value_objects.ticker import Ticker


class BackfillTaskRepositoryPort(Protocol):
    """Persistence contract for :class:`BackfillTask` entities.

    Reads are global (the table has no per-user partitioning — backfills
    serve the shared price-history feed); writes go through narrow
    transition methods so the entity's state machine is honoured.
    """

    async def create(self, task: BackfillTask) -> BackfillTask:
        """Insert a fresh row and return the persisted entity.

        The caller is responsible for assigning ``id`` and ``created_at``
        on the entity — the adapter persists it verbatim. Returning the
        entity (rather than ``None``) keeps callsites symmetrical with
        the ``mark_*`` helpers below.

        Args:
            task: The :class:`BackfillTask` to persist.

        Returns:
            The persisted entity.
        """
        ...

    async def find_existing(
        self,
        ticker: Ticker,
        start_date: date,
        end_date: date,
        *,
        status_in: Collection[BackfillTaskStatus],
    ) -> BackfillTask | None:
        """Return a task matching the exact ``(ticker, range)`` for idempotency.

        Used by the prewarmer to short-circuit when a non-terminal task
        already exists for the same window — e.g. a previous activation
        kicked off a prewarm that's still ``PENDING`` or ``RUNNING``.

        Args:
            ticker: Ticker to match.
            start_date: Exact start of the queued range.
            end_date: Exact end of the queued range.
            status_in: Match if the task's status is in this set. Empty
                set means "match any status" (kept explicit so callers
                think about it; the prewarmer always filters to
                non-terminal statuses).

        Returns:
            The matching task, or ``None`` if none exists.
        """
        ...

    async def mark_running(self, task_id: UUID) -> BackfillTask:
        """Flip PENDING -> RUNNING.

        Args:
            task_id: ID of the task to update.

        Returns:
            The updated task in ``RUNNING`` state.

        Raises:
            ValueError: If the task is missing or not in ``PENDING``.
        """
        ...

    async def mark_succeeded(self, task_id: UUID) -> BackfillTask:
        """Flip RUNNING -> SUCCEEDED.

        Args:
            task_id: ID of the task to update.

        Returns:
            The updated task in ``SUCCEEDED`` state.

        Raises:
            ValueError: If the task is missing or already terminal.
        """
        ...

    async def mark_failed(
        self,
        task_id: UUID,
        *,
        error_message: str,
    ) -> BackfillTask:
        """Flip PENDING/RUNNING -> FAILED with a truncated reason.

        Args:
            task_id: ID of the task to update.
            error_message: Reason for failure. The adapter truncates to
                the entity's 500-char limit before persisting.

        Returns:
            The updated task in ``FAILED`` state.

        Raises:
            ValueError: If the task is missing or already terminal.
        """
        ...

    async def list_pending(self, *, limit: int) -> list[BackfillTask]:
        """Return up to ``limit`` PENDING tasks, oldest-first.

        Drives the scheduler's pickup loop — older PENDING rows get
        processed first so retries don't starve new arrivals
        indefinitely.

        Args:
            limit: Maximum rows to return. Must be ``> 0``.

        Returns:
            Oldest-first list of PENDING tasks.
        """
        ...
