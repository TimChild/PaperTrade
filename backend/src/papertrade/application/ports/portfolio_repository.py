"""Portfolio repository port (interface).

Defines the contract for portfolio persistence operations. Adapters implement
this interface to provide actual storage mechanisms (SQLModel, InMemory, etc.).
"""

from typing import Protocol
from uuid import UUID

from papertrade.domain.entities.portfolio import Portfolio


class PortfolioRepository(Protocol):
    """Interface for portfolio persistence operations.

    This port follows the Repository pattern, abstracting persistence details
    from the application layer. Implementations can use any storage mechanism.
    """

    def get(self, portfolio_id: UUID) -> Portfolio | None:
        """Retrieve a single portfolio by ID.

        Args:
            portfolio_id: Unique identifier of the portfolio

        Returns:
            Portfolio entity if found, None if not found

        Raises:
            RepositoryError: If database connection or query fails
        """
        ...

    def get_by_user(self, user_id: UUID) -> list[Portfolio]:
        """Retrieve all portfolios owned by a user.

        Args:
            user_id: Unique identifier of the user

        Returns:
            List of Portfolio entities (may be empty)
            Portfolios are returned in creation order (oldest first)

        Raises:
            RepositoryError: If database connection or query fails
        """
        ...

    def save(self, portfolio: Portfolio) -> None:
        """Persist a portfolio (create if new, update if exists).

        This method implements upsert behavior - it creates a new record if
        the portfolio doesn't exist, or updates the existing record if it does.

        Args:
            portfolio: Portfolio entity to persist

        Raises:
            RepositoryError: If save fails (constraint violation, connection failure)
        """
        ...

    def exists(self, portfolio_id: UUID) -> bool:
        """Check if a portfolio exists without loading it.

        This is more efficient than calling get() when you only need to verify
        existence and don't need the actual portfolio data.

        Args:
            portfolio_id: Unique identifier of the portfolio

        Returns:
            True if portfolio exists, False otherwise

        Raises:
            RepositoryError: If database connection fails
        """
        ...
