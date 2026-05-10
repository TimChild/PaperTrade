"""TriggerRepository port — persistence contract for StrategyConditionTrigger.

Implementations live in:

* ``adapters/outbound/database/strategy_condition_trigger_repository.py`` —
  SQLModel backed by Postgres / SQLite.
* ``application/ports/in_memory_trigger_repository.py`` — in-memory adapter
  used by unit / integration tests.

The repository surface mirrors :class:`StrategyActivationRepository`'s shape
with extras for the trigger evaluator's read pattern (``list_evaluable``)
and the kill-switch (``disable_all_for_user``, ``disable_all``).

The cooldown / expiry checks happen in the service layer (which has a
``now()`` reference), not here — the repository returns "candidate"
triggers in ACTIVE status and the caller filters by
:meth:`StrategyConditionTrigger.is_evaluable`.
"""

from datetime import datetime
from typing import Protocol
from uuid import UUID

from zebu.domain.entities.strategy_condition_trigger import StrategyConditionTrigger
from zebu.domain.value_objects.trigger_status import TriggerStatus


class TriggerRepository(Protocol):
    """Persistence contract for :class:`StrategyConditionTrigger` entities.

    All methods are async to support both database and in-memory
    implementations. Read methods that return collections specify their
    ordering so callers can rely on it.
    """

    async def get(self, trigger_id: UUID) -> StrategyConditionTrigger | None:
        """Retrieve a single trigger by ID.

        Args:
            trigger_id: Unique trigger identifier.

        Returns:
            The :class:`StrategyConditionTrigger` if found, ``None``
            otherwise.
        """
        ...

    async def list_evaluable(self) -> list[StrategyConditionTrigger]:
        """Retrieve all triggers in ACTIVE status, ordered for evaluation.

        Ordering: ``(priority DESC, created_at ASC)`` — higher-priority
        triggers go first; ties broken by oldest creation. The cooldown
        / expires_at check is the caller's responsibility (depends on
        ``now()``); this method only filters by status.

        Returns:
            List of ACTIVE :class:`StrategyConditionTrigger` entities.
        """
        ...

    async def list_for_activation(
        self, activation_id: UUID
    ) -> list[StrategyConditionTrigger]:
        """List all triggers for one activation, including terminal-status.

        Newest-first by ``created_at`` so the UI can render history with
        the most recent attachment at the top.

        Args:
            activation_id: Activation whose triggers to fetch.

        Returns:
            List of triggers attached to ``activation_id``.
        """
        ...

    async def list_for_user(
        self,
        user_id: UUID,
        *,
        status: TriggerStatus | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[StrategyConditionTrigger]:
        """List triggers owned by a user, optionally status-filtered.

        Newest-first by ``created_at`` (matches the existing exploration-task
        / activation user-view ordering).

        Args:
            user_id: Owner UUID.
            status: Optional :class:`TriggerStatus` filter — when ``None``,
                returns triggers in any status.
            limit: Optional row cap. ``None`` means no cap; callers
                wanting full pages should pass an explicit limit from the
                API's pagination params.
            offset: Number of rows to skip for pagination.

        Returns:
            List of triggers matching the filter.
        """
        ...

    async def count_for_user(
        self,
        user_id: UUID,
        *,
        status: TriggerStatus | None = None,
    ) -> int:
        """Count triggers owned by a user, optionally status-filtered.

        Used by paginated list endpoints to populate
        ``PaginatedResponse.total`` without fetching every row.

        Args:
            user_id: Owner UUID.
            status: Optional status filter.

        Returns:
            Total count of matching rows.
        """
        ...

    async def save(
        self,
        trigger: StrategyConditionTrigger,
        *,
        api_key_id: UUID | None = None,
    ) -> None:
        """Persist a trigger (idempotent upsert keyed on ``trigger.id``).

        Args:
            trigger: Entity to persist.
            api_key_id: ID of the API key that authenticated the request,
                or ``None`` for Clerk Bearer (human via UI). Stamped only
                on insert; subsequent transitions leave the original
                creator's credential reference intact.
        """
        ...

    async def delete(self, trigger_id: UUID) -> None:
        """Hard-delete a trigger by ID.

        Soft-delete should be done via :meth:`StrategyConditionTrigger.expire`
        / :meth:`disable` and then ``save``. ``delete`` is provided for
        tests that need to reset state and for cascading from the API's
        DELETE endpoint when "expire and forget" is intended.

        Args:
            trigger_id: Identifier of the trigger to delete.
        """
        ...

    async def disable_all_for_user(self, user_id: UUID, *, at: datetime) -> int:
        """Bulk-disable every non-terminal trigger owned by a user.

        Backs the per-user kill switch (``POST /triggers/disable-all`` —
        wired in F-5). Atomically transitions every non-terminal trigger
        to :class:`TriggerStatus.MANUALLY_DISABLED` and updates
        ``updated_at`` to ``at``.

        Args:
            user_id: Owner UUID whose triggers to disable.
            at: Timestamp recorded as the new ``updated_at``.

        Returns:
            Count of triggers transitioned (zero if the user already had
            no non-terminal triggers).
        """
        ...

    async def disable_all(self, *, at: datetime) -> int:
        """Bulk-disable every non-terminal trigger across all users.

        Backs the admin-wide kill switch (``POST /admin/triggers/disable-all``
        — wired in F-5). Logged at WARN level by the API layer.

        Args:
            at: Timestamp recorded as the new ``updated_at``.

        Returns:
            Count of triggers transitioned across all users.
        """
        ...
