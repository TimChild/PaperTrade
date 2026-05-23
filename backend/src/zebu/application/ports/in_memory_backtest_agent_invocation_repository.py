"""In-memory implementation of BacktestAgentInvocationRepository for testing.

Thread-safe. Append-only — duplicate IDs raise ``ValueError`` (mirrors
the SQL adapter's IntegrityError contract).
"""

from collections.abc import Sequence
from threading import Lock
from uuid import UUID

from zebu.domain.entities.backtest_agent_invocation import BacktestAgentInvocation


class InMemoryBacktestAgentInvocationRepository:
    """In-memory implementation of :class:`BacktestAgentInvocationRepository`."""

    def __init__(self) -> None:
        """Initialise empty invocation storage."""
        self._records: dict[UUID, BacktestAgentInvocation] = {}
        self._lock = Lock()

    async def get(self, invocation_id: UUID) -> BacktestAgentInvocation | None:
        """Retrieve an invocation by ID."""
        with self._lock:
            return self._records.get(invocation_id)

    async def list_for_backtest_run(
        self,
        backtest_run_id: UUID,
        *,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[BacktestAgentInvocation]:
        """List invocations for one backtest run, chronologically."""
        with self._lock:
            matching = [
                r
                for r in self._records.values()
                if r.backtest_run_id == backtest_run_id
            ]
            # Ordering: simulated_date asc, then created_at asc.
            ordered = sorted(
                matching,
                key=lambda r: (r.simulated_date, r.created_at),
            )
            if limit is None:
                return ordered[offset:]
            return ordered[offset : offset + limit]

    async def count_for_backtest_run(self, backtest_run_id: UUID) -> int:
        """Count invocations for one backtest run."""
        with self._lock:
            return sum(
                1
                for r in self._records.values()
                if r.backtest_run_id == backtest_run_id
            )

    async def save(self, invocation: BacktestAgentInvocation) -> None:
        """Insert an invocation row. Duplicate ``id`` raises ``ValueError``."""
        with self._lock:
            if invocation.id in self._records:
                raise ValueError(
                    f"BacktestAgentInvocation with id={invocation.id} already "
                    "exists; the audit log is append-only"
                )
            self._records[invocation.id] = invocation

    async def save_all(
        self,
        invocations: Sequence[BacktestAgentInvocation],
    ) -> None:
        """Bulk-insert invocation rows.

        For the in-memory adapter this is the same shape as ``save`` in a
        loop — there is no batching benefit, but we still enforce the
        same "duplicate id raises" semantics and we check the batch for
        internal duplicates up front so the failure mode matches the SQL
        adapter (which raises the IntegrityError before any row commits).
        """
        # Up-front check for duplicates within the batch and against
        # existing records — match the SQL adapter's "fail before any row
        # lands" semantics so call-site error handling generalises.
        with self._lock:
            seen: set[UUID] = set()
            for invocation in invocations:
                if invocation.id in self._records:
                    raise ValueError(
                        f"BacktestAgentInvocation with id={invocation.id} "
                        "already exists; the audit log is append-only"
                    )
                if invocation.id in seen:
                    raise ValueError(
                        f"Duplicate id={invocation.id} within the same save_all batch"
                    )
                seen.add(invocation.id)
            for invocation in invocations:
                self._records[invocation.id] = invocation

    def clear(self) -> None:
        """Clear all records (for testing)."""
        with self._lock:
            self._records.clear()
