"""StrategyActivation repository port - persistence contract for activations."""

from typing import Protocol
from uuid import UUID

from zebu.domain.entities.strategy_activation import StrategyActivation


class StrategyActivationRepository(Protocol):
    """Protocol defining the repository contract for StrategyActivation entities.

    Implementations must be provided by adapters (e.g. SQLModel, in-memory).
    All methods are async to support both database and in-memory implementations.

    See ``agent_docs/tasks/210_live_strategy_execution.md`` (Phase C1) for the
    use cases this port supports — the scheduler uses ``list_active`` each
    cycle, the API surfaces use ``get_by_strategy`` / ``list_for_user``, and
    activate / deactivate / status-update flows all funnel through ``save``.
    """

    async def get(self, activation_id: UUID) -> StrategyActivation | None:
        """Retrieve a single activation by ID.

        Args:
            activation_id: Unique identifier of the activation.

        Returns:
            StrategyActivation entity if found, ``None`` otherwise.
        """
        ...

    async def get_by_strategy(self, strategy_id: UUID) -> StrategyActivation | None:
        """Retrieve the activation linked to a strategy, if any.

        At most one activation may exist per strategy at a time — the API layer
        is responsible for enforcing this. The repository returns the single
        activation if one exists, or ``None`` if the strategy has never been
        activated (or the prior activation was deleted).

        Args:
            strategy_id: Unique identifier of the strategy.

        Returns:
            The activation linked to the strategy, or ``None`` if none exists.
        """
        ...

    async def list_active(self) -> list[StrategyActivation]:
        """Retrieve all activations currently in ``ACTIVE`` status.

        This is the scheduler's primary read — it runs each cycle and feeds
        every returned activation into ``StrategyExecutionService``.

        Returns:
            List of ``ACTIVE`` StrategyActivation entities, ordered by
            ``created_at`` ascending. May be empty.
        """
        ...

    async def list_for_user(self, user_id: UUID) -> list[StrategyActivation]:
        """Retrieve all activations owned by a user.

        The API uses this to power the user's "my active strategies" view.
        Returns activations in any status — callers can filter client-side
        when they want only ACTIVE ones.

        Args:
            user_id: Unique identifier of the user.

        Returns:
            List of StrategyActivation entities for the user, ordered by
            ``created_at`` ascending. May be empty.
        """
        ...

    async def save(self, activation: StrategyActivation) -> None:
        """Persist an activation (create if new, update if exists).

        Implementations MUST treat this as an idempotent upsert keyed on
        ``activation.id``.

        Args:
            activation: StrategyActivation entity to persist.
        """
        ...

    async def delete(self, activation_id: UUID) -> None:
        """Delete an activation by ID.

        Deleting an activation does NOT touch the linked strategy or portfolio
        — those remain. To delete the underlying strategy or portfolio, use
        their respective repositories (which will cascade-remove this
        activation via the FK constraints declared in the migration).

        Args:
            activation_id: Unique identifier of the activation to delete.
        """
        ...
