"""In-memory implementation of TriggerRepository for testing.

Thread-safe. Suitable for unit / integration tests that don't need
database persistence. Mirrors the patterns used by
``in_memory_strategy_activation_repository`` and
``in_memory_exploration_task_repository``.
"""

from datetime import datetime
from threading import Lock
from uuid import UUID

from zebu.domain.entities.strategy_condition_trigger import StrategyConditionTrigger
from zebu.domain.value_objects.trigger_status import TriggerStatus

_TERMINAL_STATUSES: frozenset[TriggerStatus] = frozenset(
    {TriggerStatus.EXPIRED, TriggerStatus.MANUALLY_DISABLED}
)


class InMemoryTriggerRepository:
    """In-memory implementation of :class:`TriggerRepository` protocol."""

    def __init__(self) -> None:
        """Initialise empty trigger storage."""
        self._triggers: dict[UUID, StrategyConditionTrigger] = {}
        self._lock = Lock()

    async def get(self, trigger_id: UUID) -> StrategyConditionTrigger | None:
        """Retrieve a trigger by ID."""
        with self._lock:
            return self._triggers.get(trigger_id)

    async def list_evaluable(self) -> list[StrategyConditionTrigger]:
        """Retrieve ACTIVE triggers, ordered ``(priority DESC, created_at ASC)``.

        Cooldown / expiry checks are the caller's responsibility.
        """
        with self._lock:
            active = [
                t for t in self._triggers.values() if t.status is TriggerStatus.ACTIVE
            ]
            # Sort by created_at ascending first (stable sort), then by
            # priority descending — Python's sort is stable, so combining
            # the two passes preserves the (priority DESC, created_at ASC)
            # tie-break ordering.
            active.sort(key=lambda t: t.created_at)
            active.sort(key=lambda t: t.priority, reverse=True)
            return active

    async def list_for_activation(
        self, activation_id: UUID
    ) -> list[StrategyConditionTrigger]:
        """List all triggers for one activation, newest-first."""
        with self._lock:
            matching = [
                t for t in self._triggers.values() if t.activation_id == activation_id
            ]
            return sorted(matching, key=lambda t: t.created_at, reverse=True)

    async def list_for_user(
        self,
        user_id: UUID,
        *,
        status: TriggerStatus | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[StrategyConditionTrigger]:
        """List triggers for one user, newest-first, optionally status-filtered."""
        with self._lock:
            matching = [t for t in self._triggers.values() if t.user_id == user_id]
            if status is not None:
                matching = [t for t in matching if t.status is status]
            ordered = sorted(matching, key=lambda t: t.created_at, reverse=True)
            if limit is None:
                return ordered[offset:]
            return ordered[offset : offset + limit]

    async def count_for_user(
        self,
        user_id: UUID,
        *,
        status: TriggerStatus | None = None,
    ) -> int:
        """Count triggers for one user, optionally status-filtered."""
        with self._lock:
            count = 0
            for t in self._triggers.values():
                if t.user_id != user_id:
                    continue
                if status is not None and t.status is not status:
                    continue
                count += 1
            return count

    async def save(
        self,
        trigger: StrategyConditionTrigger,
        *,
        api_key_id: UUID | None = None,
    ) -> None:
        """Save a trigger (idempotent upsert).

        ``api_key_id`` is accepted for protocol compatibility but ignored
        in this in-memory implementation (mirrors the pattern used by
        the other in-memory repos).
        """
        del api_key_id
        with self._lock:
            self._triggers[trigger.id] = trigger

    async def delete(self, trigger_id: UUID) -> None:
        """Hard-delete a trigger by ID (no-op if missing)."""
        with self._lock:
            self._triggers.pop(trigger_id, None)

    async def disable_all_for_user(self, user_id: UUID, *, at: datetime) -> int:
        """Bulk-disable every non-terminal trigger owned by ``user_id``."""
        with self._lock:
            disabled_count = 0
            for trigger_id, trigger in list(self._triggers.items()):
                if trigger.user_id != user_id:
                    continue
                if trigger.status in _TERMINAL_STATUSES:
                    continue
                self._triggers[trigger_id] = trigger.disable(at=at)
                disabled_count += 1
            return disabled_count

    async def disable_all(self, *, at: datetime) -> int:
        """Bulk-disable every non-terminal trigger across all users."""
        with self._lock:
            disabled_count = 0
            for trigger_id, trigger in list(self._triggers.items()):
                if trigger.status in _TERMINAL_STATUSES:
                    continue
                self._triggers[trigger_id] = trigger.disable(at=at)
                disabled_count += 1
            return disabled_count

    def clear(self) -> None:
        """Clear all triggers (for testing)."""
        with self._lock:
            self._triggers.clear()
