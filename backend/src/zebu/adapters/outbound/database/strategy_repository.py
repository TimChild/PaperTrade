"""SQLModel implementation of StrategyRepository.

Provides strategy persistence using SQLModel ORM with SQLite/PostgreSQL.
"""

from uuid import UUID

from sqlmodel import delete, select
from sqlmodel.ext.asyncio.session import AsyncSession

from zebu.adapters.outbound.database.models import StrategyModel
from zebu.domain.entities.strategy import Strategy


class SQLModelStrategyRepository:
    """SQLModel implementation of StrategyRepository protocol.

    Uses SQLModel ORM for database operations.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session.

        Args:
            session: Async database session for this unit of work
        """
        self._session = session

    async def get(self, strategy_id: UUID) -> Strategy | None:
        """Retrieve a single strategy by ID.

        Args:
            strategy_id: Unique identifier of the strategy

        Returns:
            Strategy entity if found, None if not found
        """
        result = await self._session.get(StrategyModel, strategy_id)
        if result is None:
            return None
        return result.to_domain()

    async def get_by_user(self, user_id: UUID) -> list[Strategy]:
        """Retrieve all strategies owned by a user.

        Strategies are returned in creation order (oldest first).

        Args:
            user_id: Unique identifier of the user

        Returns:
            List of Strategy entities (may be empty)
        """
        statement = (
            select(StrategyModel)
            .where(StrategyModel.user_id == user_id)
            .order_by(StrategyModel.created_at.asc())  # type: ignore[attr-defined]
        )
        result = await self._session.exec(statement)
        models = result.all()
        return [model.to_domain() for model in models]

    async def save(self, strategy: Strategy) -> None:
        """Persist a strategy (create if new, update if exists).

        Args:
            strategy: Strategy entity to persist
        """
        existing = await self._session.get(StrategyModel, strategy.id)

        if existing is None:
            model = StrategyModel.from_domain(strategy)
            self._session.add(model)
        else:
            existing.name = strategy.name
            existing.strategy_type = strategy.strategy_type.value
            existing.tickers = strategy.tickers  # type: ignore[assignment]
            existing.parameters = strategy.parameters  # type: ignore[assignment]
            if existing.created_at.tzinfo is not None:
                existing.created_at = existing.created_at.replace(tzinfo=None)
            self._session.add(existing)

    async def delete(self, strategy_id: UUID) -> None:
        """Delete a strategy by ID.

        Args:
            strategy_id: Unique identifier of the strategy to delete
        """
        statement = delete(StrategyModel).where(
            StrategyModel.id == strategy_id  # type: ignore[arg-type]
        )
        await self._session.exec(statement)
