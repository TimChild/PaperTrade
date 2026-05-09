"""SQLModel implementation of ExplorationTaskRepository.

Provides persistence for the agent-platform task queue. The atomic
``claim_atomic`` method uses a single ``UPDATE ... WHERE status='OPEN'``
statement with a ``RETURNING *`` clause: if two agents call it
simultaneously, only the first sees a row come back; the loser sees
``None`` and retries. This avoids holding a row lock across application
code and works on both PostgreSQL and SQLite (SQLite supports ``RETURNING``
as of 3.35).
"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import update
from sqlmodel import col, delete, func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from zebu.adapters.outbound.database.models import ExplorationTaskModel
from zebu.domain.entities.exploration_task import (
    ExplorationTask,
    ExplorationTaskStatus,
)


class SQLModelExplorationTaskRepository:
    """SQLModel implementation of ExplorationTaskRepository protocol."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session.

        Args:
            session: Async database session for this unit of work.
        """
        self._session = session

    async def get(self, task_id: UUID) -> ExplorationTask | None:
        """Retrieve a single task by ID."""
        result = await self._session.get(ExplorationTaskModel, task_id)
        if result is None:
            return None
        return result.to_domain()

    async def list_by_status(
        self,
        status: ExplorationTaskStatus,
        *,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[ExplorationTask]:
        """List tasks filtered by status, oldest-first."""
        statement = (
            select(ExplorationTaskModel)
            .where(ExplorationTaskModel.status == status.value)
            .order_by(col(ExplorationTaskModel.created_at).asc())
            .offset(offset)
        )
        if limit is not None:
            statement = statement.limit(limit)
        result = await self._session.exec(statement)
        models = result.all()
        return [model.to_domain() for model in models]

    async def list_for_user(
        self,
        user_id: UUID,
        *,
        status: ExplorationTaskStatus | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[ExplorationTask]:
        """List tasks owned by a user, newest-first."""
        statement = (
            select(ExplorationTaskModel)
            .where(ExplorationTaskModel.created_by == user_id)
            .order_by(col(ExplorationTaskModel.created_at).desc())
            .offset(offset)
        )
        if status is not None:
            statement = statement.where(ExplorationTaskModel.status == status.value)
        if limit is not None:
            statement = statement.limit(limit)
        result = await self._session.exec(statement)
        models = result.all()
        return [model.to_domain() for model in models]

    async def count_by_status(
        self,
        status: ExplorationTaskStatus,
    ) -> int:
        """Count tasks with the given status."""
        statement = select(func.count()).where(  # type: ignore[arg-type]
            ExplorationTaskModel.status == status.value
        )
        result = await self._session.exec(statement)
        value = result.one()
        return int(value)

    async def count_for_user(
        self,
        user_id: UUID,
        *,
        status: ExplorationTaskStatus | None = None,
    ) -> int:
        """Count tasks owned by a user, optionally status-filtered."""
        statement = select(func.count()).where(  # type: ignore[arg-type]
            ExplorationTaskModel.created_by == user_id
        )
        if status is not None:
            statement = statement.where(ExplorationTaskModel.status == status.value)
        result = await self._session.exec(statement)
        value = result.one()
        return int(value)

    async def save(self, task: ExplorationTask) -> None:
        """Persist a task (create if new, update if exists)."""
        existing = await self._session.get(ExplorationTaskModel, task.id)

        if existing is None:
            model = ExplorationTaskModel.from_domain(task)
            self._session.add(model)
            return

        # Update in-place so SQLAlchemy tracks the change correctly under
        # `expire_on_commit=False` sessions used in tests.
        replacement = ExplorationTaskModel.from_domain(task)
        existing.prompt = replacement.prompt
        existing.status = replacement.status
        existing.target_portfolio_id = replacement.target_portfolio_id
        existing.tickers = replacement.tickers  # type: ignore[assignment]
        existing.constraints = replacement.constraints  # type: ignore[assignment]
        existing.claimed_by = replacement.claimed_by
        existing.claimed_at = replacement.claimed_at
        existing.findings = replacement.findings  # type: ignore[assignment]
        existing.updated_at = replacement.updated_at
        self._session.add(existing)

    async def delete(self, task_id: UUID) -> None:
        """Delete a task by ID (no-op if missing)."""
        statement = delete(ExplorationTaskModel).where(
            ExplorationTaskModel.id == task_id  # type: ignore[arg-type]
        )
        await self._session.exec(statement)  # type: ignore[call-overload]

    async def claim_atomic(
        self,
        task_id: UUID,
        *,
        agent_id: str,
        claimed_at: datetime,
    ) -> ExplorationTask | None:
        """Atomically transition OPEN -> IN_PROGRESS for one task.

        Issues a single ``UPDATE`` that targets only rows whose current
        ``status`` is ``OPEN``. If the row does not exist or has already
        been claimed (status != OPEN), the update affects zero rows and
        we return ``None``.

        The session is flushed (not committed) so the caller controls the
        outer transaction; commits happen on session close in the FastAPI
        dependency. Concurrent callers contending for the same row are
        serialised by the database's row-locking on the UPDATE.
        """
        if not agent_id or not agent_id.strip():
            # Mirror the entity-level invariant so callers don't end up
            # writing an empty agent_id into the DB. Returning None here
            # would be misleading — this is a programming error.
            from zebu.domain.entities.exploration_task import (
                InvalidExplorationTaskError,
            )

            raise InvalidExplorationTaskError(
                "claim_atomic requires a non-empty agent_id"
            )

        # Strip timezone for PostgreSQL TIMESTAMP WITHOUT TIME ZONE columns
        if claimed_at.tzinfo is not None:
            claimed_at_naive = claimed_at.astimezone(UTC).replace(tzinfo=None)
        else:
            claimed_at_naive = claimed_at

        # Single UPDATE with WHERE status=OPEN — race-safe.
        # We update updated_at to claimed_at to keep the timestamp invariant
        # the entity enforces (updated_at >= created_at). Use ``col()`` so
        # Pyright treats the comparison as a SQL clause rather than a Python
        # bool check.
        statement = (
            update(ExplorationTaskModel)
            .where(
                col(ExplorationTaskModel.id) == task_id,
                col(ExplorationTaskModel.status) == ExplorationTaskStatus.OPEN.value,
            )
            .values(
                status=ExplorationTaskStatus.IN_PROGRESS.value,
                claimed_by=agent_id,
                claimed_at=claimed_at_naive,
                updated_at=claimed_at_naive,
            )
        )
        result = await self._session.exec(statement)  # type: ignore[call-overload]
        # Whether the UPDATE matched a row. SQLAlchemy core result for
        # UPDATE exposes rowcount on the underlying cursor result.
        rowcount = getattr(result, "rowcount", 0)
        if rowcount == 0:
            return None

        # Reload the row in domain form. Using session.get keeps the
        # identity map consistent.
        await self._session.flush()
        # Force a refresh in case the row was already in the identity map
        # under a previous status snapshot.
        existing = await self._session.get(ExplorationTaskModel, task_id)
        if existing is None:
            # Should not happen — UPDATE just confirmed the row exists —
            # but defend against transient session weirdness.
            return None
        await self._session.refresh(existing)
        return existing.to_domain()
