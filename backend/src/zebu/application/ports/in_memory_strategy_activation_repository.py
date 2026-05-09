"""In-memory implementation of StrategyActivationRepository for testing.

Provides fast, thread-safe in-memory storage suitable for unit testing
higher-level services (scheduler job, execution service, API handlers) that
arrive in Phase C1.2/C1.3. No persistence between test runs.
"""

from threading import Lock
from uuid import UUID

from zebu.domain.entities.strategy_activation import StrategyActivation
from zebu.domain.value_objects.activation_status import ActivationStatus


class InMemoryStrategyActivationRepository:
    """In-memory implementation of StrategyActivationRepository protocol.

    Uses a Python dictionary for O(1) access by ID. Thread-safe with locks.
    Suitable for unit testing without database setup.
    """

    def __init__(self) -> None:
        """Initialize empty activation storage."""
        self._activations: dict[UUID, StrategyActivation] = {}
        self._lock = Lock()

    async def get(self, activation_id: UUID) -> StrategyActivation | None:
        """Retrieve an activation by ID."""
        with self._lock:
            return self._activations.get(activation_id)

    async def get_by_strategy(self, strategy_id: UUID) -> StrategyActivation | None:
        """Retrieve the activation linked to a strategy, or None if missing.

        If multiple activations exist for the same strategy (which shouldn't
        happen — the API enforces uniqueness — but is technically possible
        in a misconfigured test), return the one with the latest
        ``created_at`` so callers don't see arbitrary ordering surprises.
        """
        with self._lock:
            matches = [
                a for a in self._activations.values() if a.strategy_id == strategy_id
            ]
            if not matches:
                return None
            return max(matches, key=lambda a: a.created_at)

    async def list_active(self) -> list[StrategyActivation]:
        """Retrieve all activations in ACTIVE status, oldest first."""
        with self._lock:
            active = [
                a
                for a in self._activations.values()
                if a.status is ActivationStatus.ACTIVE
            ]
            return sorted(active, key=lambda a: a.created_at)

    async def list_for_user(self, user_id: UUID) -> list[StrategyActivation]:
        """Retrieve all activations owned by a user, oldest first."""
        with self._lock:
            user_activations = [
                a for a in self._activations.values() if a.user_id == user_id
            ]
            return sorted(user_activations, key=lambda a: a.created_at)

    async def save(self, activation: StrategyActivation) -> None:
        """Save an activation (idempotent upsert)."""
        with self._lock:
            self._activations[activation.id] = activation

    async def delete(self, activation_id: UUID) -> None:
        """Delete an activation by ID."""
        with self._lock:
            self._activations.pop(activation_id, None)

    def clear(self) -> None:
        """Clear all activations (for testing)."""
        with self._lock:
            self._activations.clear()
