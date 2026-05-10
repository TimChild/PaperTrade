"""SQLModel implementation of TriggerFireRepository.

Append-only persistence for :class:`TriggerFireRecord`. Insert is the
only write path; duplicate IDs surface via SQLAlchemy's IntegrityError.
The list / count read paths use the
``idx_trigger_fire_trigger_fired_at`` and
``idx_trigger_fire_activation_fired_at`` indexes for newest-first
pagination.
"""

from uuid import UUID

from sqlmodel import col, func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from zebu.adapters.outbound.database.models import TriggerFireRecordModel
from zebu.domain.entities.trigger_fire_record import TriggerFireRecord


class SQLModelTriggerFireRepository:
    """SQLModel implementation of :class:`TriggerFireRepository`."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialise with an async DB session.

        Args:
            session: Async session for this unit of work.
        """
        self._session = session

    async def get(self, record_id: UUID) -> TriggerFireRecord | None:
        """Retrieve a single fire record by ID."""
        result = await self._session.get(TriggerFireRecordModel, record_id)
        if result is None:
            return None
        return result.to_domain()

    async def list_for_trigger(
        self,
        trigger_id: UUID,
        *,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[TriggerFireRecord]:
        """List fire records for one trigger, newest-first."""
        statement = (
            select(TriggerFireRecordModel)
            .where(TriggerFireRecordModel.trigger_id == trigger_id)
            .order_by(col(TriggerFireRecordModel.fired_at).desc())
            .offset(offset)
        )
        if limit is not None:
            statement = statement.limit(limit)
        result = await self._session.exec(statement)
        models = result.all()
        return [model.to_domain() for model in models]

    async def list_for_activation(
        self,
        activation_id: UUID,
        *,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[TriggerFireRecord]:
        """List fire records for one activation, newest-first."""
        statement = (
            select(TriggerFireRecordModel)
            .where(TriggerFireRecordModel.activation_id == activation_id)
            .order_by(col(TriggerFireRecordModel.fired_at).desc())
            .offset(offset)
        )
        if limit is not None:
            statement = statement.limit(limit)
        result = await self._session.exec(statement)
        models = result.all()
        return [model.to_domain() for model in models]

    async def count_for_trigger(self, trigger_id: UUID) -> int:
        """Count fire records for one trigger."""
        statement = select(func.count()).where(  # type: ignore[arg-type]
            TriggerFireRecordModel.trigger_id == trigger_id
        )
        result = await self._session.exec(statement)
        value = result.one()
        return int(value)

    async def count_for_activation(self, activation_id: UUID) -> int:
        """Count fire records for one activation."""
        statement = select(func.count()).where(  # type: ignore[arg-type]
            TriggerFireRecordModel.activation_id == activation_id
        )
        result = await self._session.exec(statement)
        value = result.one()
        return int(value)

    async def save(self, record: TriggerFireRecord) -> None:
        """Insert a fire record. Duplicate ``id`` raises ``IntegrityError``.

        The repository is append-only — there is no upsert path. A
        duplicate ID indicates the caller is retrying a write that
        already landed; surface the integrity error rather than silently
        overwriting.
        """
        # Check identity to surface the duplicate case as a clear error
        # before SQLAlchemy emits the INSERT and the underlying engine
        # raises IntegrityError. The caller-facing contract is the same;
        # we just produce a more readable error message.
        existing = await self._session.get(TriggerFireRecordModel, record.id)
        if existing is not None:
            raise ValueError(
                f"TriggerFireRecord with id={record.id} already exists; "
                "the audit log is append-only"
            )
        model = TriggerFireRecordModel.from_domain(record)
        self._session.add(model)
