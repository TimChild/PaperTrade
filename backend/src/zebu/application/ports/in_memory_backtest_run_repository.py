"""In-memory implementation of BacktestRunRepository for testing.

Provides fast, thread-safe in-memory storage suitable for unit testing.
No persistence between test runs.
"""

from threading import Lock
from uuid import UUID

from zebu.domain.entities.backtest_run import BacktestRun


class InMemoryBacktestRunRepository:
    """In-memory implementation of BacktestRunRepository protocol.

    Uses Python dictionaries for O(1) access. Thread-safe with locks.
    Suitable for unit testing without database setup.
    """

    def __init__(self) -> None:
        """Initialize empty backtest run storage."""
        self._runs: dict[UUID, BacktestRun] = {}
        self._lock = Lock()

    async def get(self, backtest_id: UUID) -> BacktestRun | None:
        """Retrieve a backtest run by ID."""
        with self._lock:
            return self._runs.get(backtest_id)

    async def get_by_user(self, user_id: UUID) -> list[BacktestRun]:
        """Retrieve all backtest runs for a user, ordered by creation date."""
        with self._lock:
            user_runs = [r for r in self._runs.values() if r.user_id == user_id]
            return sorted(user_runs, key=lambda r: r.created_at)

    async def get_by_strategy(self, strategy_id: UUID) -> list[BacktestRun]:
        """Retrieve all backtest runs for a strategy, ordered by creation date."""
        with self._lock:
            strategy_runs = [
                r for r in self._runs.values() if r.strategy_id == strategy_id
            ]
            return sorted(strategy_runs, key=lambda r: r.created_at)

    async def save(self, backtest_run: BacktestRun) -> None:
        """Save a backtest run (idempotent upsert)."""
        with self._lock:
            self._runs[backtest_run.id] = backtest_run

    async def delete(self, backtest_id: UUID) -> None:
        """Delete a backtest run by ID."""
        with self._lock:
            self._runs.pop(backtest_id, None)

    def clear(self) -> None:
        """Clear all backtest runs (for testing)."""
        with self._lock:
            self._runs.clear()
