"""BacktestAgentInvocationRepository port — persistence for backtest audit rows.

Phase L (Task #217). Append-only repository for
:class:`BacktestAgentInvocation`. There are no update or delete paths
exposed — the table is the canonical "what the agent decided during this
backtest" log; corrections are made by writing new rows or via direct
SQL in pathological cases (audit-trail integrity over flexibility).

Implementations live in:

* ``adapters/outbound/database/backtest_agent_invocation_repository.py``
  — SQLModel adapter backed by Postgres / SQLite.
* ``application/ports/in_memory_backtest_agent_invocation_repository.py``
  — in-memory adapter used by unit / integration tests.

Ordering on :meth:`list_for_backtest_run` is **chronological** —
``simulated_date`` ascending, then ``created_at`` ascending. The activity
feed / fire-log UI renders backtests as a timeline; chronological order
matches user mental model.

The :meth:`save_all` method MUST batch into a single DB round-trip so a
2-year daily-fire backtest with 500 rows is not 500 round-trips. The L-3
executor will accumulate in-memory and flush at the end of
``_run_pipeline``, mirroring the existing ``transaction_repo.save_all``
pattern.
"""

from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from zebu.domain.entities.backtest_agent_invocation import BacktestAgentInvocation


class BacktestAgentInvocationRepository(Protocol):
    """Persistence contract for :class:`BacktestAgentInvocation` entities.

    Append-only. ``save`` / ``save_all`` (write) and ``get`` /
    ``list_for_backtest_run`` / ``count_for_backtest_run`` (read) are the
    only methods exposed; no update / delete.
    """

    async def get(self, invocation_id: UUID) -> BacktestAgentInvocation | None:
        """Retrieve a single invocation by ID.

        Args:
            invocation_id: Unique invocation identifier.

        Returns:
            The :class:`BacktestAgentInvocation` if found, ``None``
            otherwise.
        """
        ...

    async def list_for_backtest_run(
        self,
        backtest_run_id: UUID,
        *,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[BacktestAgentInvocation]:
        """List invocation rows for one backtest run, chronologically.

        Ordering is ``simulated_date`` ascending, then ``created_at``
        ascending (ties broken by wall-clock insert order, stable across
        runs).

        Args:
            backtest_run_id: Backtest run whose invocations to fetch.
            limit: Optional row cap. ``None`` means no cap.
            offset: Number of rows to skip for pagination.

        Returns:
            List of rows ordered chronologically in simulation time.
        """
        ...

    async def count_for_backtest_run(self, backtest_run_id: UUID) -> int:
        """Total invocations for one backtest run.

        Args:
            backtest_run_id: Backtest run whose count to compute.

        Returns:
            Count of invocation rows for the run.
        """
        ...

    async def save(self, invocation: BacktestAgentInvocation) -> None:
        """Insert one invocation row. Duplicate ``id`` raises.

        Implementations MUST treat this as insert-only — the row is
        immutable, and a duplicate ID indicates a programming error.

        Args:
            invocation: Entity to persist.

        Raises:
            ValueError: If a row with the same ``id`` already exists.
                Mapped to whichever exception the underlying engine
                raises (e.g. ``IntegrityError`` for SQL implementations);
                the in-memory implementation raises this directly.
        """
        ...

    async def save_all(
        self,
        invocations: Sequence[BacktestAgentInvocation],
    ) -> None:
        """Bulk-insert invocation rows in a single round-trip.

        Performance-critical: a 2-year daily-fire backtest can produce
        500+ rows. Implementations MUST batch into a single SQL INSERT
        / flush, NOT loop ``save`` per row.

        Args:
            invocations: Sequence of entities to persist.

        Raises:
            ValueError: If any row shares an ``id`` with an existing
                row or with another row in the same batch.
        """
        ...
