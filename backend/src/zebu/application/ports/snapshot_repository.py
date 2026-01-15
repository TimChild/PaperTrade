"""Snapshot repository port (interface).

Defines the contract for portfolio snapshot persistence operations.
Snapshots are used for analytics and performance tracking.
"""

from datetime import date
from typing import Protocol
from uuid import UUID

from zebu.domain.entities.portfolio_snapshot import PortfolioSnapshot


class SnapshotRepository(Protocol):
    """Interface for portfolio snapshot persistence operations.

    This port follows the Repository pattern, abstracting persistence details
    from the application layer. Snapshots support upsert behavior to handle
    daily recalculations.
    """

    async def save(self, snapshot: PortfolioSnapshot) -> PortfolioSnapshot:
        """Save a snapshot (create if new, update if exists for same portfolio+date).

        Implements upsert behavior - updates existing snapshot for the same
        portfolio and date, or creates a new one if it doesn't exist.

        Args:
            snapshot: PortfolioSnapshot entity to persist

        Returns:
            The saved snapshot with any database-generated values

        Raises:
            RepositoryError: If save fails (constraint violation, connection failure)
        """
        ...

    async def get_by_portfolio_and_date(
        self, portfolio_id: UUID, snapshot_date: date
    ) -> PortfolioSnapshot | None:
        """Get snapshot for a specific portfolio and date.

        Args:
            portfolio_id: Portfolio identifier
            snapshot_date: Date of the snapshot

        Returns:
            PortfolioSnapshot if found, None if not found

        Raises:
            RepositoryError: If database connection or query fails
        """
        ...

    async def get_range(
        self,
        portfolio_id: UUID,
        start_date: date,
        end_date: date,
    ) -> list[PortfolioSnapshot]:
        """Get snapshots for a date range (inclusive).

        Returns snapshots ordered by date ascending (oldest first).

        Args:
            portfolio_id: Portfolio identifier
            start_date: Start of date range (inclusive)
            end_date: End of date range (inclusive)

        Returns:
            List of PortfolioSnapshot entities (may be empty)
            Sorted by snapshot_date ascending

        Raises:
            RepositoryError: If database connection or query fails
        """
        ...

    async def get_latest(self, portfolio_id: UUID) -> PortfolioSnapshot | None:
        """Get the most recent snapshot for a portfolio.

        Args:
            portfolio_id: Portfolio identifier

        Returns:
            Most recent PortfolioSnapshot if any exist, None otherwise

        Raises:
            RepositoryError: If database connection or query fails
        """
        ...

    async def delete_by_portfolio(self, portfolio_id: UUID) -> int:
        """Delete all snapshots for a portfolio.

        Used for cleanup when a portfolio is deleted.

        Args:
            portfolio_id: Portfolio identifier

        Returns:
            Count of snapshots deleted (0 if none existed)

        Raises:
            RepositoryError: If database connection or delete fails
        """
        ...
