"""SQLModel implementation of BacktestAgentInvocationRepository.

Phase L-1 (Task #217). Append-only persistence for
:class:`BacktestAgentInvocation`. Mirrors
:class:`SQLModelTriggerFireRepository` in shape — single-row ``save`` +
bulk ``save_all`` (single round-trip) for the executor's end-of-run
flush. List read paths use the ``idx_bt_agent_invocation_run_date``
index for chronological ordering.

Duplicate IDs are surfaced as ``ValueError`` with a clear message,
matching the in-memory adapter's contract; the underlying
SQLAlchemy ``IntegrityError`` would otherwise leak as a confusing
implementation detail to the caller.
"""

from collections.abc import Sequence
from uuid import UUID

from sqlmodel import col, func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from zebu.adapters.outbound.database.models import BacktestAgentInvocationModel
from zebu.domain.entities.backtest_agent_invocation import BacktestAgentInvocation


class SQLModelBacktestAgentInvocationRepository:
    """SQLModel implementation of :class:`BacktestAgentInvocationRepository`."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialise with an async DB session.

        Args:
            session: Async session for this unit of work.
        """
        self._session = session

    async def get(self, invocation_id: UUID) -> BacktestAgentInvocation | None:
        """Retrieve a single invocation by ID."""
        result = await self._session.get(BacktestAgentInvocationModel, invocation_id)
        if result is None:
            return None
        return result.to_domain()

    async def list_for_backtest_run(
        self,
        backtest_run_id: UUID,
        *,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[BacktestAgentInvocation]:
        """List invocations for one backtest run, chronologically.

        Ordered by ``simulated_date`` ascending, then ``created_at``
        ascending. Ties on ``simulated_date`` are broken deterministically
        by insert order so the listing is stable across calls.
        """
        statement = (
            select(BacktestAgentInvocationModel)
            .where(BacktestAgentInvocationModel.backtest_run_id == backtest_run_id)
            .order_by(
                col(BacktestAgentInvocationModel.simulated_date).asc(),
                col(BacktestAgentInvocationModel.created_at).asc(),
            )
            .offset(offset)
        )
        if limit is not None:
            statement = statement.limit(limit)
        result = await self._session.exec(statement)
        models = result.all()
        return [model.to_domain() for model in models]

    async def count_for_backtest_run(self, backtest_run_id: UUID) -> int:
        """Count invocations for one backtest run."""
        statement = select(func.count()).where(  # type: ignore[arg-type]
            BacktestAgentInvocationModel.backtest_run_id == backtest_run_id
        )
        result = await self._session.exec(statement)
        value = result.one()
        return int(value)

    async def save(self, invocation: BacktestAgentInvocation) -> None:
        """Insert an invocation row. Duplicate ``id`` surfaces as ``ValueError``."""
        existing = await self._session.get(BacktestAgentInvocationModel, invocation.id)
        if existing is not None:
            raise ValueError(
                f"BacktestAgentInvocation with id={invocation.id} already "
                "exists; the audit log is append-only"
            )
        model = BacktestAgentInvocationModel.from_domain(invocation)
        self._session.add(model)

    async def save_all(
        self,
        invocations: Sequence[BacktestAgentInvocation],
    ) -> None:
        """Bulk-insert invocation rows in a single ``flush``.

        Does NOT loop per-row ``save`` calls — the executor accumulates
        in memory and flushes at end of run; 500 rows must be one
        round-trip.

        Raises:
            ValueError: If the batch contains a duplicate id within
                itself, or any id already exists in the DB.
        """
        if not invocations:
            return

        # Check for batch-internal duplicates up front so the caller
        # gets a clean ValueError before SQLAlchemy raises an
        # IntegrityError mid-flush (which would leave the session in a
        # rollback-required state).
        seen: set[UUID] = set()
        for invocation in invocations:
            if invocation.id in seen:
                raise ValueError(
                    f"Duplicate id={invocation.id} within the same save_all batch"
                )
            seen.add(invocation.id)

        # Check for pre-existing rows in the DB. A bulk ``add_all`` would
        # otherwise raise IntegrityError on flush — we want a clear
        # ValueError before any rows enter the unit of work.
        for invocation in invocations:
            existing = await self._session.get(
                BacktestAgentInvocationModel, invocation.id
            )
            if existing is not None:
                raise ValueError(
                    f"BacktestAgentInvocation with id={invocation.id} "
                    "already exists; the audit log is append-only"
                )

        models = [
            BacktestAgentInvocationModel.from_domain(invocation)
            for invocation in invocations
        ]
        self._session.add_all(models)
        await self._session.flush()
