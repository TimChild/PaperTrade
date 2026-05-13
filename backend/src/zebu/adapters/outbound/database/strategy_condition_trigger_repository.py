"""SQLModel implementation of TriggerRepository.

Persists :class:`StrategyConditionTrigger` records via the SQLModel ORM.
The hot read path (``list_evaluable``) goes through the
``idx_trigger_status_last_fired`` index — filters on ``status='ACTIVE'``
then orders by ``priority DESC, created_at ASC``.

The kill-switch helpers (``disable_all_for_user`` / ``disable_all``) walk
non-terminal rows in a single round-trip and call the entity's
``.disable()`` transition. The bulk path is a hot path during a real
admin incident, so it batches rather than issuing N updates.
"""

from datetime import UTC, datetime
from uuid import UUID

from sqlmodel import col, delete, func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from zebu.adapters.outbound.database.models import StrategyConditionTriggerModel
from zebu.domain.entities.strategy_condition_trigger import StrategyConditionTrigger
from zebu.domain.value_objects.trigger_status import TriggerStatus

_TERMINAL_STATUS_VALUES: frozenset[str] = frozenset(
    {TriggerStatus.EXPIRED.value, TriggerStatus.MANUALLY_DISABLED.value}
)


class SQLModelTriggerRepository:
    """SQLModel implementation of :class:`TriggerRepository`."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialise with an async DB session.

        Args:
            session: Async session for this unit of work.
        """
        self._session = session

    async def get(self, trigger_id: UUID) -> StrategyConditionTrigger | None:
        """Retrieve a single trigger by ID."""
        result = await self._session.get(StrategyConditionTriggerModel, trigger_id)
        if result is None:
            return None
        return result.to_domain()

    async def list_evaluable(self) -> list[StrategyConditionTrigger]:
        """List ACTIVE triggers ordered ``(priority DESC, created_at ASC)``.

        Cooldown / expiry filtering is the caller's responsibility.
        """
        statement = (
            select(StrategyConditionTriggerModel)
            .where(StrategyConditionTriggerModel.status == TriggerStatus.ACTIVE.value)
            .order_by(
                col(StrategyConditionTriggerModel.priority).desc(),
                col(StrategyConditionTriggerModel.created_at).asc(),
            )
        )
        result = await self._session.exec(statement)
        models = result.all()
        return [model.to_domain() for model in models]

    async def list_for_activation(
        self, activation_id: UUID
    ) -> list[StrategyConditionTrigger]:
        """List all triggers for one activation, newest-first."""
        statement = (
            select(StrategyConditionTriggerModel)
            .where(StrategyConditionTriggerModel.activation_id == activation_id)
            .order_by(col(StrategyConditionTriggerModel.created_at).desc())
        )
        result = await self._session.exec(statement)
        models = result.all()
        return [model.to_domain() for model in models]

    async def list_for_user(
        self,
        user_id: UUID,
        *,
        status: TriggerStatus | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[StrategyConditionTrigger]:
        """List triggers for one user, newest-first."""
        statement = (
            select(StrategyConditionTriggerModel)
            .where(StrategyConditionTriggerModel.user_id == user_id)
            .order_by(col(StrategyConditionTriggerModel.created_at).desc())
            .offset(offset)
        )
        if status is not None:
            statement = statement.where(
                StrategyConditionTriggerModel.status == status.value
            )
        if limit is not None:
            statement = statement.limit(limit)
        result = await self._session.exec(statement)
        models = result.all()
        return [model.to_domain() for model in models]

    async def count_for_user(
        self,
        user_id: UUID,
        *,
        status: TriggerStatus | None = None,
    ) -> int:
        """Count triggers for one user, optionally status-filtered."""
        statement = select(func.count()).where(  # type: ignore[arg-type]
            StrategyConditionTriggerModel.user_id == user_id
        )
        if status is not None:
            statement = statement.where(
                StrategyConditionTriggerModel.status == status.value
            )
        result = await self._session.exec(statement)
        value = result.one()
        return int(value)

    async def save(
        self,
        trigger: StrategyConditionTrigger,
        *,
        api_key_id: UUID | None = None,
    ) -> None:
        """Persist a trigger (idempotent upsert).

        ``api_key_id`` is accepted for protocol compatibility with the
        broader Phase H2 actor-binding pattern, but the trigger row's
        own ``default_api_key_id`` column captures the key the woken
        agent should act under, so we don't stamp a separate creator
        column here. Mirrors the in-memory adapter's behaviour.
        """
        del api_key_id

        existing = await self._session.get(StrategyConditionTriggerModel, trigger.id)

        if existing is None:
            model = StrategyConditionTriggerModel.from_domain(trigger)
            self._session.add(model)
            return

        replacement = StrategyConditionTriggerModel.from_domain(trigger)
        existing.activation_id = replacement.activation_id
        existing.user_id = replacement.user_id
        existing.condition_type = replacement.condition_type
        existing.condition_params = replacement.condition_params  # type: ignore[assignment]
        existing.agent_prompt = replacement.agent_prompt
        existing.cooldown_seconds = replacement.cooldown_seconds
        existing.last_fired_at = replacement.last_fired_at
        existing.status = replacement.status
        existing.priority = replacement.priority
        existing.default_api_key_id = replacement.default_api_key_id
        existing.expires_at = replacement.expires_at
        existing.mode = replacement.mode
        # ``created_at`` and ``created_by`` are immutable by convention;
        # we don't overwrite them on update so accidental clock drift in
        # the entity doesn't rewrite history.
        existing.updated_at = replacement.updated_at
        self._session.add(existing)

    async def delete(self, trigger_id: UUID) -> None:
        """Hard-delete a trigger by ID (no-op if missing)."""
        statement = delete(StrategyConditionTriggerModel).where(
            StrategyConditionTriggerModel.id == trigger_id  # type: ignore[arg-type]
        )
        await self._session.exec(statement)  # type: ignore[call-overload]

    async def disable_all_for_user(self, user_id: UUID, *, at: datetime) -> int:
        """Bulk-disable every non-terminal trigger owned by ``user_id``.

        Loads each non-terminal row, calls the entity's ``.disable()``
        transition (so audit-log invariants are respected), and persists
        the new status. Issued in a single session round-trip; the SQL
        adapter does not require a single bulk UPDATE because the
        kill-switch is a low-frequency operation.
        """
        statement = select(StrategyConditionTriggerModel).where(
            StrategyConditionTriggerModel.user_id == user_id,
            col(StrategyConditionTriggerModel.status).not_in(_TERMINAL_STATUS_VALUES),
        )
        result = await self._session.exec(statement)
        models = result.all()

        # Strip timezone for naive PostgreSQL columns.
        if at.tzinfo is not None:
            at_naive = at.astimezone(UTC).replace(tzinfo=None)
        else:
            at_naive = at

        disabled_count = 0
        for model in models:
            # Run through the entity's transition to keep state-machine
            # logic in one place. We don't actually need the new entity
            # — we just need the resulting status / updated_at — so we
            # update the model in-place.
            domain = model.to_domain()
            domain.disable(at=at)  # raises if terminal — defensive
            model.status = TriggerStatus.MANUALLY_DISABLED.value
            model.updated_at = at_naive
            self._session.add(model)
            disabled_count += 1
        return disabled_count

    async def disable_all(self, *, at: datetime) -> int:
        """Bulk-disable every non-terminal trigger across all users.

        Same approach as ``disable_all_for_user`` minus the user filter.
        Logged at WARN by the API layer.
        """
        statement = select(StrategyConditionTriggerModel).where(
            col(StrategyConditionTriggerModel.status).not_in(_TERMINAL_STATUS_VALUES),
        )
        result = await self._session.exec(statement)
        models = result.all()

        if at.tzinfo is not None:
            at_naive = at.astimezone(UTC).replace(tzinfo=None)
        else:
            at_naive = at

        disabled_count = 0
        for model in models:
            domain = model.to_domain()
            domain.disable(at=at)
            model.status = TriggerStatus.MANUALLY_DISABLED.value
            model.updated_at = at_naive
            self._session.add(model)
            disabled_count += 1
        return disabled_count
