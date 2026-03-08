"""BacktestRun repository port - defines the persistence contract for backtest runs."""

from typing import Protocol
from uuid import UUID

from zebu.domain.entities.backtest_run import BacktestRun


class BacktestRunRepository(Protocol):
    """Protocol defining the repository contract for BacktestRun entities.

    Implementations must be provided by adapters (e.g. SQLModel, in-memory).
    All methods are async to support both database and in-memory implementations.
    """

    async def get(self, backtest_id: UUID) -> BacktestRun | None:
        """Retrieve a single backtest run by ID.

        Args:
            backtest_id: Unique identifier of the backtest run

        Returns:
            BacktestRun entity if found, None otherwise
        """
        ...

    async def get_by_user(self, user_id: UUID) -> list[BacktestRun]:
        """Retrieve all backtest runs owned by a user, ordered by creation date.

        Args:
            user_id: Unique identifier of the user

        Returns:
            List of BacktestRun entities (may be empty)
        """
        ...

    async def get_by_strategy(self, strategy_id: UUID) -> list[BacktestRun]:
        """Retrieve all backtest runs for a given strategy, ordered by creation date.

        Args:
            strategy_id: Unique identifier of the strategy

        Returns:
            List of BacktestRun entities (may be empty)
        """
        ...

    async def save(self, backtest_run: BacktestRun) -> None:
        """Persist a backtest run (create if new, update if exists).

        Args:
            backtest_run: BacktestRun entity to persist
        """
        ...

    async def delete(self, backtest_id: UUID) -> None:
        """Delete a backtest run by ID.

        Args:
            backtest_id: Unique identifier of the backtest run to delete
        """
        ...
