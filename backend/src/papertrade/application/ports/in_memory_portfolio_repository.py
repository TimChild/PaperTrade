"""In-memory implementation of PortfolioRepository for testing.

Provides fast, thread-safe in-memory storage suitable for unit testing.
No persistence between test runs.
"""

from threading import Lock
from uuid import UUID

from papertrade.domain.entities.portfolio import Portfolio


class InMemoryPortfolioRepository:
    """In-memory implementation of PortfolioRepository protocol.

    Uses Python dictionaries for O(1) access. Thread-safe with locks.
    Suitable for unit testing without database setup.
    """

    def __init__(self) -> None:
        """Initialize empty portfolio storage."""
        self._portfolios: dict[UUID, Portfolio] = {}
        self._lock = Lock()

    async def get(self, portfolio_id: UUID) -> Portfolio | None:
        """Retrieve a portfolio by ID."""
        with self._lock:
            return self._portfolios.get(portfolio_id)

    async def get_by_user(self, user_id: UUID) -> list[Portfolio]:
        """Retrieve all portfolios for a user, ordered by creation date."""
        with self._lock:
            user_portfolios = [
                p for p in self._portfolios.values() if p.user_id == user_id
            ]
            return sorted(user_portfolios, key=lambda p: p.created_at)

    async def save(self, portfolio: Portfolio) -> None:
        """Save a portfolio (idempotent upsert)."""
        with self._lock:
            self._portfolios[portfolio.id] = portfolio

    async def exists(self, portfolio_id: UUID) -> bool:
        """Check if a portfolio exists."""
        with self._lock:
            return portfolio_id in self._portfolios

    def clear(self) -> None:
        """Clear all portfolios (for testing)."""
        with self._lock:
            self._portfolios.clear()
