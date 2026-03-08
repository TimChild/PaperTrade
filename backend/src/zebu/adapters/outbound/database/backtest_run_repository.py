"""SQLModel implementation of BacktestRunRepository.

Provides backtest run persistence using SQLModel ORM with SQLite/PostgreSQL.
"""

from uuid import UUID

from sqlmodel import delete, select
from sqlmodel.ext.asyncio.session import AsyncSession

from zebu.adapters.outbound.database.models import BacktestRunModel
from zebu.domain.entities.backtest_run import BacktestRun


class SQLModelBacktestRunRepository:
    """SQLModel implementation of BacktestRunRepository protocol.

    Uses SQLModel ORM for database operations.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session.

        Args:
            session: Async database session for this unit of work
        """
        self._session = session

    async def get(self, backtest_id: UUID) -> BacktestRun | None:
        """Retrieve a single backtest run by ID.

        Args:
            backtest_id: Unique identifier of the backtest run

        Returns:
            BacktestRun entity if found, None if not found
        """
        result = await self._session.get(BacktestRunModel, backtest_id)
        if result is None:
            return None
        return result.to_domain()

    async def get_by_user(self, user_id: UUID) -> list[BacktestRun]:
        """Retrieve all backtest runs owned by a user.

        Runs are returned in creation order (oldest first).

        Args:
            user_id: Unique identifier of the user

        Returns:
            List of BacktestRun entities (may be empty)
        """
        statement = (
            select(BacktestRunModel)
            .where(BacktestRunModel.user_id == user_id)
            .order_by(BacktestRunModel.created_at.asc())  # type: ignore[attr-defined]
        )
        result = await self._session.exec(statement)
        models = result.all()
        return [model.to_domain() for model in models]

    async def get_by_strategy(self, strategy_id: UUID) -> list[BacktestRun]:
        """Retrieve all backtest runs for a given strategy.

        Runs are returned in creation order (oldest first).

        Args:
            strategy_id: Unique identifier of the strategy

        Returns:
            List of BacktestRun entities (may be empty)
        """
        statement = (
            select(BacktestRunModel)
            .where(BacktestRunModel.strategy_id == strategy_id)
            .order_by(BacktestRunModel.created_at.asc())  # type: ignore[attr-defined]
        )
        result = await self._session.exec(statement)
        models = result.all()
        return [model.to_domain() for model in models]

    async def save(self, backtest_run: BacktestRun) -> None:
        """Persist a backtest run (create if new, update if exists).

        Args:
            backtest_run: BacktestRun entity to persist
        """
        existing = await self._session.get(BacktestRunModel, backtest_run.id)

        if existing is None:
            model = BacktestRunModel.from_domain(backtest_run)
            self._session.add(model)
        else:
            existing.status = backtest_run.status.value
            existing.strategy_snapshot = backtest_run.strategy_snapshot  # type: ignore[assignment]
            existing.error_message = backtest_run.error_message
            existing.total_return_pct = backtest_run.total_return_pct
            existing.max_drawdown_pct = backtest_run.max_drawdown_pct
            existing.annualized_return_pct = backtest_run.annualized_return_pct
            existing.total_trades = backtest_run.total_trades
            if backtest_run.completed_at is not None:
                if backtest_run.completed_at.tzinfo:
                    from datetime import UTC

                    existing.completed_at = backtest_run.completed_at.astimezone(
                        UTC
                    ).replace(tzinfo=None)
                else:
                    existing.completed_at = backtest_run.completed_at
            self._session.add(existing)

    async def delete(self, backtest_id: UUID) -> None:
        """Delete a backtest run by ID.

        Args:
            backtest_id: Unique identifier of the backtest run to delete
        """
        statement = delete(BacktestRunModel).where(
            BacktestRunModel.id == backtest_id  # type: ignore[arg-type]
        )
        await self._session.exec(statement)
