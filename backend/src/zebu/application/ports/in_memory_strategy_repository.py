"""In-memory implementation of StrategyRepository for testing.

Provides fast, thread-safe in-memory storage suitable for unit testing.
No persistence between test runs.
"""

from threading import Lock
from uuid import UUID

from zebu.domain.entities.strategy import Strategy


class InMemoryStrategyRepository:
    """In-memory implementation of StrategyRepository protocol.

    Uses Python dictionaries for O(1) access. Thread-safe with locks.
    Suitable for unit testing without database setup.
    """

    def __init__(self) -> None:
        """Initialize empty strategy storage."""
        self._strategies: dict[UUID, Strategy] = {}
        self._lock = Lock()

    async def get(self, strategy_id: UUID) -> Strategy | None:
        """Retrieve a strategy by ID."""
        with self._lock:
            return self._strategies.get(strategy_id)

    async def get_by_user(self, user_id: UUID) -> list[Strategy]:
        """Retrieve all strategies for a user, ordered by creation date."""
        with self._lock:
            user_strategies = [
                s for s in self._strategies.values() if s.user_id == user_id
            ]
            return sorted(user_strategies, key=lambda s: s.created_at)

    async def save(self, strategy: Strategy) -> None:
        """Save a strategy (idempotent upsert)."""
        with self._lock:
            self._strategies[strategy.id] = strategy

    async def delete(self, strategy_id: UUID) -> None:
        """Delete a strategy by ID."""
        with self._lock:
            self._strategies.pop(strategy_id, None)

    def clear(self) -> None:
        """Clear all strategies (for testing)."""
        with self._lock:
            self._strategies.clear()
