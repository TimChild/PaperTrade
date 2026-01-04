"""SQLModel implementation of PortfolioRepository.

Provides portfolio persistence using SQLModel ORM with SQLite/PostgreSQL.
"""

from datetime import UTC, datetime
from uuid import UUID

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from papertrade.adapters.outbound.database.models import PortfolioModel
from papertrade.domain.entities.portfolio import Portfolio


class SQLModelPortfolioRepository:
    """SQLModel implementation of PortfolioRepository protocol.

    Uses SQLModel ORM for database operations with optimistic locking support.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session.

        Args:
            session: Async database session for this unit of work
        """
        self._session = session

    async def get(self, portfolio_id: UUID) -> Portfolio | None:
        """Retrieve a single portfolio by ID.

        Args:
            portfolio_id: Unique identifier of the portfolio

        Returns:
            Portfolio entity if found, None if not found
        """
        result = await self._session.get(PortfolioModel, portfolio_id)
        if result is None:
            return None
        return result.to_domain()

    async def get_by_user(self, user_id: UUID) -> list[Portfolio]:
        """Retrieve all portfolios owned by a user.

        Portfolios are returned in creation order (oldest first).

        Args:
            user_id: Unique identifier of the user

        Returns:
            List of Portfolio entities (may be empty)
        """
        statement = (
            select(PortfolioModel)
            .where(PortfolioModel.user_id == user_id)
            .order_by(PortfolioModel.created_at.asc())  # type: ignore[attr-defined]  # SQLModel field has SQLAlchemy column methods
        )
        result = await self._session.exec(statement)
        models = result.all()
        return [model.to_domain() for model in models]

    async def save(self, portfolio: Portfolio) -> None:
        """Persist a portfolio (create if new, update if exists).

        Implements upsert behavior with optimistic locking.

        Args:
            portfolio: Portfolio entity to persist
        """
        # Check if portfolio already exists
        existing = await self._session.get(PortfolioModel, portfolio.id)

        if existing is None:
            # Create new portfolio
            model = PortfolioModel.from_domain(portfolio)
            self._session.add(model)
        else:
            # Update existing portfolio (only mutable fields)
            # Strip timezone for PostgreSQL TIMESTAMP WITHOUT TIME ZONE
            # Also ensure created_at is naive (it might have been converted when loaded)
            if existing.created_at.tzinfo is not None:
                existing.created_at = existing.created_at.replace(tzinfo=None)
            existing.name = portfolio.name
            existing.updated_at = datetime.now(UTC).replace(tzinfo=None)
            existing.version += 1
            self._session.add(existing)

    async def exists(self, portfolio_id: UUID) -> bool:
        """Check if a portfolio exists without loading it.

        Args:
            portfolio_id: Unique identifier of the portfolio

        Returns:
            True if portfolio exists, False otherwise
        """
        statement = select(PortfolioModel.id).where(PortfolioModel.id == portfolio_id)
        result = await self._session.exec(statement)
        return result.first() is not None
