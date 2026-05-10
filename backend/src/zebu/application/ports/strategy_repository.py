"""Strategy repository port - defines the persistence contract for strategies."""

from typing import Protocol
from uuid import UUID

from zebu.domain.entities.strategy import Strategy


class StrategyRepository(Protocol):
    """Protocol defining the repository contract for Strategy entities.

    Implementations must be provided by adapters (e.g. SQLModel, in-memory).
    All methods are async to support both database and in-memory implementations.
    """

    async def get(self, strategy_id: UUID) -> Strategy | None:
        """Retrieve a single strategy by ID.

        Args:
            strategy_id: Unique identifier of the strategy

        Returns:
            Strategy entity if found, None otherwise
        """
        ...

    async def get_by_user(self, user_id: UUID) -> list[Strategy]:
        """Retrieve all strategies owned by a user, ordered by creation date.

        Args:
            user_id: Unique identifier of the user

        Returns:
            List of Strategy entities (may be empty)
        """
        ...

    async def save(
        self,
        strategy: Strategy,
        *,
        api_key_id: UUID | None = None,
    ) -> None:
        """Persist a strategy (create if new, update if exists).

        Args:
            strategy: Strategy entity to persist.
            api_key_id: Phase H2 — ID of the API key that authenticated the
                writing request, or None for Clerk Bearer (human via UI).
                Production adapters stamp it onto the row only on insert so
                the activity feed can resolve the originating credential.
        """
        ...

    async def delete(self, strategy_id: UUID) -> None:
        """Delete a strategy by ID.

        Args:
            strategy_id: Unique identifier of the strategy to delete
        """
        ...
