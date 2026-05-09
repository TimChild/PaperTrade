"""SQLModel implementation of StrategyActivationRepository.

Provides activation persistence using SQLModel ORM with SQLite/PostgreSQL.
"""

from datetime import UTC, datetime
from uuid import UUID

from sqlmodel import delete, select
from sqlmodel.ext.asyncio.session import AsyncSession

from zebu.adapters.outbound.database.models import StrategyActivationModel
from zebu.domain.entities.strategy_activation import StrategyActivation
from zebu.domain.value_objects.activation_status import ActivationStatus


class SQLModelStrategyActivationRepository:
    """SQLModel implementation of StrategyActivationRepository protocol.

    Uses SQLModel ORM for database operations.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session.

        Args:
            session: Async database session for this unit of work.
        """
        self._session = session

    async def get(self, activation_id: UUID) -> StrategyActivation | None:
        """Retrieve a single activation by ID.

        Args:
            activation_id: Unique identifier of the activation.

        Returns:
            StrategyActivation entity if found, None if not found.
        """
        result = await self._session.get(StrategyActivationModel, activation_id)
        if result is None:
            return None
        return result.to_domain()

    async def get_by_strategy(self, strategy_id: UUID) -> StrategyActivation | None:
        """Retrieve the activation linked to a strategy, if any.

        At most one activation should exist per strategy at a time. If the
        invariant is broken at the data level, this method returns the
        most-recently-created one (deterministic, predictable behavior for
        callers).

        Args:
            strategy_id: Unique identifier of the strategy.

        Returns:
            StrategyActivation linked to the strategy, or ``None``.
        """
        statement = (
            select(StrategyActivationModel)
            .where(StrategyActivationModel.strategy_id == strategy_id)
            .order_by(StrategyActivationModel.created_at.desc())  # type: ignore[attr-defined]
        )
        result = await self._session.exec(statement)
        first = result.first()
        if first is None:
            return None
        return first.to_domain()

    async def list_active(self) -> list[StrategyActivation]:
        """Retrieve all activations in ``ACTIVE`` status.

        Used by the live-execution scheduler each cycle. Activations are
        returned in creation order (oldest first) so behaviour is stable
        across runs.

        Returns:
            List of ``ACTIVE`` StrategyActivation entities (may be empty).
        """
        statement = (
            select(StrategyActivationModel)
            .where(StrategyActivationModel.status == ActivationStatus.ACTIVE.value)
            .order_by(StrategyActivationModel.created_at.asc())  # type: ignore[attr-defined]
        )
        result = await self._session.exec(statement)
        models = result.all()
        return [model.to_domain() for model in models]

    async def list_for_user(self, user_id: UUID) -> list[StrategyActivation]:
        """Retrieve all activations owned by a user.

        Returned in creation order (oldest first) regardless of status.

        Args:
            user_id: Unique identifier of the user.

        Returns:
            List of StrategyActivation entities (may be empty).
        """
        statement = (
            select(StrategyActivationModel)
            .where(StrategyActivationModel.user_id == user_id)
            .order_by(StrategyActivationModel.created_at.asc())  # type: ignore[attr-defined]
        )
        result = await self._session.exec(statement)
        models = result.all()
        return [model.to_domain() for model in models]

    async def save(self, activation: StrategyActivation) -> None:
        """Persist an activation (create if new, update if exists).

        Args:
            activation: StrategyActivation entity to persist.
        """
        existing = await self._session.get(StrategyActivationModel, activation.id)

        if existing is None:
            model = StrategyActivationModel.from_domain(activation)
            self._session.add(model)
            return

        # Update existing row in place. Strip timezone for PostgreSQL
        # TIMESTAMP WITHOUT TIME ZONE columns. ``created_at`` is reloaded
        # from the DB so it may already be naive — guard against double-strip.
        if existing.created_at.tzinfo is not None:
            existing.created_at = existing.created_at.replace(tzinfo=None)

        existing.user_id = activation.user_id
        existing.strategy_id = activation.strategy_id
        existing.portfolio_id = activation.portfolio_id
        existing.status = activation.status.value
        existing.frequency = activation.frequency.value
        existing.last_error = activation.last_error

        if activation.last_executed_at is not None:
            if activation.last_executed_at.tzinfo:
                existing.last_executed_at = activation.last_executed_at.astimezone(
                    UTC
                ).replace(tzinfo=None)
            else:
                existing.last_executed_at = activation.last_executed_at
        else:
            existing.last_executed_at = None

        # Always bump updated_at to "now" so callers don't have to thread it
        # through. The domain entity carries an updated_at field for read
        # paths, but the source of truth for write-time is the DB clock.
        existing.updated_at = datetime.now(UTC).replace(tzinfo=None)

        self._session.add(existing)

    async def delete(self, activation_id: UUID) -> None:
        """Delete an activation by ID.

        Args:
            activation_id: Unique identifier of the activation to delete.
        """
        statement = delete(StrategyActivationModel).where(
            StrategyActivationModel.id == activation_id  # type: ignore[arg-type]
        )
        await self._session.exec(statement)
