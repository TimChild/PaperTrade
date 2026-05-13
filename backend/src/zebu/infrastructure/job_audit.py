"""``@with_job_audit`` decorator — wires scheduler handlers into the
:class:`JobExecution` audit log.

Phase J (Task #212 Layer 1) — job-health observability.

Wrap any async scheduler handler with ``@with_job_audit("job_name")``
and every invocation will write a ``RUNNING`` row, run the handler, and
write a terminal ``SUCCEEDED`` / ``FAILED`` row when it returns or
raises. The endpoint ``GET /api/v1/admin/jobs/health`` reads the latest
row per job to surface "is the daily cron still healthy?".

Critical design rule
--------------------

The decorator opens its OWN DB session — it does *not* share with the
wrapped handler's session. The wrapped handler typically opens
``async_session_maker()`` itself; if that session rolls back (e.g.
because the handler raised), any audit row inside it would be lost.
Auditing rolling-back jobs is the *only* reason this subsystem exists,
so the audit row must persist in a separate transaction.

This means:

1. Decorator opens session A → ``record_start(...)`` → commit A.
2. Decorator runs the wrapped handler (which uses its own session B).
3. Decorator opens session C → ``record_finish(...)`` → commit C.
4. Decorator re-raises any exception the handler raised.

Steps 1 and 3 each use a fresh ``async_session_maker()`` context. The
JobExecution row's id threads through the closure.

The decorator never raises from its own bookkeeping — a DB error in the
audit path is logged but never overrides the exception (or success) of
the wrapped handler. The audit log is best-effort by design.
"""

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from functools import wraps
from typing import ParamSpec, TypeVar

import structlog

from zebu.adapters.outbound.database.job_execution_repository import (
    SQLModelJobExecutionRepository,
)
from zebu.domain.value_objects.job_execution_status import JobExecutionStatus
from zebu.infrastructure.database import async_session_maker

# Module-level structlog logger. Job lifecycle events land on this
# logger so they appear in the same JSON stream as the rest of the
# scheduler's logging.
logger = structlog.get_logger(__name__)

# Max length for the captured error string. Matches the entity's cap so
# we truncate at write time rather than letting the dataclass raise.
_ERROR_MESSAGE_MAX_LENGTH: int = 500


_P = ParamSpec("_P")
_R = TypeVar("_R")


def with_job_audit(
    job_name: str,
) -> Callable[[Callable[_P, Awaitable[_R]]], Callable[_P, Awaitable[_R]]]:
    """Decorator factory that wires a scheduler handler into the audit log.

    Usage::

        @with_job_audit("refresh_active_stocks")
        async def refresh_active_stocks(config: SchedulerConfig) -> None: ...

    Args:
        job_name: Stable identifier for the wrapped job. Mirrors the
            scheduler handler's function name by convention but is
            decoupled so renames don't break the audit log's history.

    Returns:
        A decorator that, when applied to an async function, wraps every
        invocation in a record_start / record_finish pair.
    """

    def decorator(
        func: Callable[_P, Awaitable[_R]],
    ) -> Callable[_P, Awaitable[_R]]:
        @wraps(func)
        async def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> _R:
            # Phase 1 — record_start in its own session. If the audit
            # write itself fails, log + proceed without an id so the
            # wrapped handler still runs (best-effort posture).
            execution_id_str: str | None = None
            started_at = datetime.now(UTC)
            try:
                async with async_session_maker() as session:
                    repo = SQLModelJobExecutionRepository(session)
                    execution = await repo.record_start(job_name)
                    await session.commit()
                    execution_id_str = str(execution.id)
                    started_at = execution.started_at
                    logger.info(
                        "job_audit_started",
                        job_name=job_name,
                        execution_id=execution_id_str,
                    )
            except Exception as audit_exc:
                logger.warning(
                    "job_audit_record_start_failed",
                    job_name=job_name,
                    error=str(audit_exc)[:_ERROR_MESSAGE_MAX_LENGTH],
                )

            # Phase 2 — run the wrapped handler. Capture success / failure
            # so we can write the terminal audit row before re-raising.
            handler_exc: BaseException | None = None
            handler_result: _R | None = None
            try:
                handler_result = await func(*args, **kwargs)
            except BaseException as exc:
                handler_exc = exc

            # Phase 3 — record_finish in its own (fresh) session. Skip
            # if the start write failed — we have no row to update.
            if execution_id_str is not None:
                duration_seconds = (datetime.now(UTC) - started_at).total_seconds()
                terminal_metadata: dict[str, str] = {
                    "duration_seconds": f"{duration_seconds:.3f}",
                }
                if handler_exc is None:
                    terminal_status = JobExecutionStatus.SUCCEEDED
                    error_message: str | None = None
                else:
                    terminal_status = JobExecutionStatus.FAILED
                    error_message = str(handler_exc)[:_ERROR_MESSAGE_MAX_LENGTH]

                try:
                    async with async_session_maker() as session:
                        repo = SQLModelJobExecutionRepository(session)
                        # Reload the row's id-bound handle from the
                        # session so the merge metadata logic in
                        # record_finish has the persisted baseline.
                        # We construct a fresh entity carrying just the
                        # id + minimum fields the entity requires; the
                        # adapter looks up the row by id and merges
                        # metadata from the DB.
                        await _record_terminal(
                            repo=repo,
                            execution_id_str=execution_id_str,
                            job_name=job_name,
                            started_at=started_at,
                            status=terminal_status,
                            error_message=error_message,
                            metadata=terminal_metadata,
                        )
                        await session.commit()
                        logger.info(
                            "job_audit_finished",
                            job_name=job_name,
                            execution_id=execution_id_str,
                            status=terminal_status.value,
                            duration_seconds=terminal_metadata["duration_seconds"],
                        )
                except Exception as audit_exc:
                    logger.warning(
                        "job_audit_record_finish_failed",
                        job_name=job_name,
                        execution_id=execution_id_str,
                        error=str(audit_exc)[:_ERROR_MESSAGE_MAX_LENGTH],
                    )

            if handler_exc is not None:
                raise handler_exc
            # When handler_exc is None, the handler returned normally —
            # handler_result holds whatever it returned (including None
            # for ``-> None`` handlers).
            return handler_result  # type: ignore[return-value]  # mypy can't reason about the exception-or-result invariant

        return wrapper

    return decorator


async def _record_terminal(
    *,
    repo: SQLModelJobExecutionRepository,
    execution_id_str: str,
    job_name: str,
    started_at: datetime,
    status: JobExecutionStatus,
    error_message: str | None,
    metadata: dict[str, str],
) -> None:
    """Look up a row by id and write its terminal state.

    Pulled out so the decorator stays readable. The adapter's
    ``record_finish`` does the heavy lifting — this helper just
    constructs a minimal entity stub carrying the id the adapter needs
    to find the persisted row.
    """
    from uuid import UUID

    from zebu.domain.value_objects.job_execution import JobExecution

    # The entity's invariants require started_at + status. We pass
    # RUNNING here because that's the state of the row before the
    # update; the adapter ignores the status and metadata on the input
    # handle and uses the kwargs to compute the terminal write.
    stub = JobExecution(
        id=UUID(execution_id_str),
        job_name=job_name,
        started_at=started_at,
        status=JobExecutionStatus.RUNNING,
        metadata={},
    )
    await repo.record_finish(
        stub,
        status=status,
        error_message=error_message,
        metadata=metadata,
    )


__all__ = ["with_job_audit"]
