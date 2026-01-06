"""SQLModel implementation of SnapshotRepository.

Provides portfolio snapshot persistence using SQLModel ORM with SQLite/PostgreSQL.
"""

from datetime import date
from uuid import UUID

from sqlmodel import delete, select
from sqlmodel.ext.asyncio.session import AsyncSession

from papertrade.adapters.outbound.database.models import PortfolioSnapshotModel
from papertrade.domain.entities.portfolio_snapshot import PortfolioSnapshot


class SQLModelSnapshotRepository:
    """SQLModel implementation of SnapshotRepository protocol.

    Uses SQLModel ORM for database operations with upsert support for snapshots.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session.

        Args:
            session: Async database session for this unit of work
        """
        self._session = session

    async def save(self, snapshot: PortfolioSnapshot) -> PortfolioSnapshot:
        """Save a snapshot (create if new, update if exists for same portfolio+date).

        Implements upsert behavior - updates existing snapshot for the same
        portfolio and date, or creates a new one if it doesn't exist.

        Args:
            snapshot: PortfolioSnapshot entity to persist

        Returns:
            The saved snapshot with any database-generated values
        """
        # Check if snapshot exists for this portfolio and date
        existing = await self.get_by_portfolio_and_date(
            snapshot.portfolio_id, snapshot.snapshot_date
        )

        if existing:
            # Update existing snapshot
            statement = select(PortfolioSnapshotModel).where(
                PortfolioSnapshotModel.id == existing.id
            )
            result = await self._session.exec(statement)
            model = result.one()

            # Update mutable fields
            model.total_value = snapshot.total_value
            model.cash_balance = snapshot.cash_balance
            model.holdings_value = snapshot.holdings_value
            model.holdings_count = snapshot.holdings_count

            self._session.add(model)
        else:
            # Create new snapshot
            model = PortfolioSnapshotModel.from_domain(snapshot)
            self._session.add(model)

        # The session will be committed by the caller (Unit of Work pattern)
        # Refresh to get any database-generated values
        await self._session.flush()
        await self._session.refresh(model)

        return model.to_domain()

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
        statement = select(PortfolioSnapshotModel).where(
            PortfolioSnapshotModel.portfolio_id == portfolio_id,
            PortfolioSnapshotModel.snapshot_date == snapshot_date,
        )
        result = await self._session.exec(statement)
        model = result.first()
        return model.to_domain() if model else None

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
            List of PortfolioSnapshot entities (may be empty), sorted by date
        """
        statement = (
            select(PortfolioSnapshotModel)
            .where(
                PortfolioSnapshotModel.portfolio_id == portfolio_id,
                PortfolioSnapshotModel.snapshot_date >= start_date,
                PortfolioSnapshotModel.snapshot_date <= end_date,
            )
            .order_by(PortfolioSnapshotModel.snapshot_date.asc())  # type: ignore[attr-defined]  # SQLModel field has SQLAlchemy column methods
        )
        result = await self._session.exec(statement)
        models = result.all()
        return [model.to_domain() for model in models]

    async def get_latest(self, portfolio_id: UUID) -> PortfolioSnapshot | None:
        """Get the most recent snapshot for a portfolio.

        Args:
            portfolio_id: Portfolio identifier

        Returns:
            Most recent PortfolioSnapshot if any exist, None otherwise
        """
        statement = (
            select(PortfolioSnapshotModel)
            .where(PortfolioSnapshotModel.portfolio_id == portfolio_id)
            .order_by(PortfolioSnapshotModel.snapshot_date.desc())  # type: ignore[attr-defined]  # SQLModel field has SQLAlchemy column methods
            .limit(1)
        )
        result = await self._session.exec(statement)
        model = result.first()
        return model.to_domain() if model else None

    async def delete_by_portfolio(self, portfolio_id: UUID) -> int:
        """Delete all snapshots for a portfolio.

        Used for cleanup when a portfolio is deleted.

        Args:
            portfolio_id: Portfolio identifier

        Returns:
            Count of snapshots deleted (0 if none existed)
        """
        # Count snapshots before deleting (using scalar query for efficiency)
        from sqlmodel import func

        count_statement = (
            select(func.count())
            .select_from(PortfolioSnapshotModel)
            .where(PortfolioSnapshotModel.portfolio_id == portfolio_id)
        )
        count_result = await self._session.exec(count_statement)
        count = count_result.one()

        # Now delete them
        statement = delete(PortfolioSnapshotModel).where(
            PortfolioSnapshotModel.portfolio_id == portfolio_id  # type: ignore[arg-type]  # SQLModel field comparison returns bool-like column expression
        )
        await self._session.exec(statement)

        return count
