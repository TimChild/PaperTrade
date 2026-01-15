"""In-memory implementation of SnapshotRepository for testing.

Provides fast, thread-safe in-memory storage suitable for unit testing.
No persistence between test runs.
"""

from datetime import date
from threading import Lock
from uuid import UUID

from zebu.application.ports.snapshot_repository import SnapshotRepository
from zebu.domain.entities.portfolio_snapshot import PortfolioSnapshot


class InMemorySnapshotRepository(SnapshotRepository):
    """In-memory implementation of SnapshotRepository protocol.

    Uses Python dictionaries for O(1) access. Thread-safe with locks.
    Suitable for unit testing without database setup.
    """

    def __init__(self) -> None:
        """Initialize empty snapshot storage."""
        self._snapshots: dict[UUID, PortfolioSnapshot] = {}
        self._lock = Lock()

    async def save(self, snapshot: PortfolioSnapshot) -> PortfolioSnapshot:
        """Save a snapshot (upsert behavior).

        Args:
            snapshot: PortfolioSnapshot entity to persist

        Returns:
            The saved snapshot
        """
        with self._lock:
            # Check for existing snapshot with same portfolio_id and date
            existing_key = None
            for key, snap in self._snapshots.items():
                if (
                    snap.portfolio_id == snapshot.portfolio_id
                    and snap.snapshot_date == snapshot.snapshot_date
                ):
                    existing_key = key
                    break

            if existing_key:
                # Update existing snapshot (keep same ID)
                self._snapshots[existing_key] = snapshot
            else:
                # Create new snapshot
                self._snapshots[snapshot.id] = snapshot

            return snapshot

    async def get_by_portfolio_and_date(
        self, portfolio_id: UUID, snapshot_date: date
    ) -> PortfolioSnapshot | None:
        """Get snapshot for a specific portfolio and date.

        Args:
            portfolio_id: Portfolio identifier
            snapshot_date: Date of the snapshot

        Returns:
            PortfolioSnapshot if found, None if not found
        """
        with self._lock:
            for snapshot in self._snapshots.values():
                if (
                    snapshot.portfolio_id == portfolio_id
                    and snapshot.snapshot_date == snapshot_date
                ):
                    return snapshot
            return None

    async def get_range(
        self,
        portfolio_id: UUID,
        start_date: date,
        end_date: date,
    ) -> list[PortfolioSnapshot]:
        """Get snapshots for a date range (inclusive).

        Args:
            portfolio_id: Portfolio identifier
            start_date: Start of date range (inclusive)
            end_date: End of date range (inclusive)

        Returns:
            List of PortfolioSnapshot entities, sorted by date
        """
        with self._lock:
            matching = [
                snap
                for snap in self._snapshots.values()
                if snap.portfolio_id == portfolio_id
                and start_date <= snap.snapshot_date <= end_date
            ]
            return sorted(matching, key=lambda s: s.snapshot_date)

    async def get_latest(self, portfolio_id: UUID) -> PortfolioSnapshot | None:
        """Get the most recent snapshot for a portfolio.

        Args:
            portfolio_id: Portfolio identifier

        Returns:
            Most recent PortfolioSnapshot if any exist, None otherwise
        """
        with self._lock:
            portfolio_snapshots = [
                snap
                for snap in self._snapshots.values()
                if snap.portfolio_id == portfolio_id
            ]
            if not portfolio_snapshots:
                return None
            return max(portfolio_snapshots, key=lambda s: s.snapshot_date)

    async def delete_by_portfolio(self, portfolio_id: UUID) -> int:
        """Delete all snapshots for a portfolio.

        Args:
            portfolio_id: Portfolio identifier

        Returns:
            Count of snapshots deleted
        """
        with self._lock:
            to_delete = [
                sid
                for sid, snap in self._snapshots.items()
                if snap.portfolio_id == portfolio_id
            ]
            for sid in to_delete:
                del self._snapshots[sid]
            return len(to_delete)

    def clear(self) -> None:
        """Clear all snapshots (for testing)."""
        with self._lock:
            self._snapshots.clear()
