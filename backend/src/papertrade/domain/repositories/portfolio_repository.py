"""Portfolio repository interface (Port)."""

from typing import Protocol
from uuid import UUID

from papertrade.domain.entities import Portfolio


class PortfolioRepository(Protocol):
    """Protocol defining the interface for portfolio persistence.

    This is a Port in Clean Architecture - adapters will implement this interface.
    """

    async def get(self, portfolio_id: UUID) -> Portfolio | None:
        """Get a portfolio by ID.

        Args:
            portfolio_id: The unique identifier of the portfolio.

        Returns:
            The portfolio if found, None otherwise.
        """
        ...

    async def get_by_user(self, user_id: UUID) -> list[Portfolio]:
        """Get all portfolios for a user.

        Args:
            user_id: The unique identifier of the user.

        Returns:
            List of portfolios owned by the user.
        """
        ...

    async def save(self, portfolio: Portfolio) -> None:
        """Save a portfolio (create or update).

        Args:
            portfolio: The portfolio to save.
        """
        ...

    async def delete(self, portfolio_id: UUID) -> None:
        """Delete a portfolio.

        Args:
            portfolio_id: The unique identifier of the portfolio to delete.
        """
        ...
