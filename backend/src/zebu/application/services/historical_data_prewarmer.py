"""HistoricalDataPrewarmer — activation-time pre-warm of price history.

Phase J (Task #212 Layer 2) — activation-time pre-warm.

The prewarmer is fired in two contexts:

* **Activation** — ``POST /strategies/{id}/activate`` schedules a
  background prewarm so the first run of the strategy doesn't 404 on
  missing OHLC bars.
* **Scheduler pickup** — ``refresh_active_stocks`` drains any
  ``PENDING`` :class:`BackfillTask` rows after its primary refresh loop.
  This handles two cases: (a) activation prewarms that failed
  transiently and were left ``PENDING`` (the entity is created in
  PENDING before the fetch runs), and (b) in L4, operator-triggered
  backfills queued through the admin endpoint.

For each ticker we:

1. Check the :class:`BackfillTaskRepositoryPort` for an existing
   ``PENDING`` / ``RUNNING`` task with the same ``(ticker, range)`` —
   if found, skip (idempotent).
2. Insert a fresh ``PENDING`` row.
3. Flip it to ``RUNNING`` and call
   :meth:`MarketDataPort.get_price_history` (which goes through the
   existing rate limiter — we do not bypass).
4. On success: flip the row to ``SUCCEEDED``.
5. On failure: flip the row to ``FAILED`` with a truncated reason.

The service returns a :class:`PrewarmResult` summarising the per-ticker
outcome so the caller (the activation route, or the scheduler) can log
a sensible summary line.

Failures of individual tickers do NOT abort the batch — one bad ticker
shouldn't poison a multi-ticker activation. Batch-level failures
(network down, rate-limit storm) bubble up to the caller.
"""

import logging
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from uuid import uuid4

from zebu.application.ports.backfill_task_repository import (
    BackfillTaskRepositoryPort,
)
from zebu.application.ports.market_data_port import MarketDataPort
from zebu.domain.entities.backfill_task import BackfillTask
from zebu.domain.value_objects.backfill_priority import BackfillPriority
from zebu.domain.value_objects.backfill_task_status import (
    NON_TERMINAL_STATUSES,
    BackfillTaskStatus,
)
from zebu.domain.value_objects.ticker import Ticker

logger = logging.getLogger(__name__)

# Cap the per-failure error message at the entity-level limit so the
# adapter never has to truncate at write time.
_ERROR_MESSAGE_MAX_LENGTH: int = 500


@dataclass(frozen=True)
class PrewarmResult:
    """Summary returned by :meth:`HistoricalDataPrewarmer.prewarm`.

    Attributes:
        succeeded: Tickers that were fetched and persisted as SUCCEEDED.
        failed: Tickers that errored, paired with the truncated
            error string.
        skipped: Tickers we did not enqueue because a non-terminal task
            for the same ``(ticker, range)`` already exists.
    """

    succeeded: list[Ticker] = field(default_factory=list)
    failed: list[tuple[Ticker, str]] = field(default_factory=list)
    skipped: list[Ticker] = field(default_factory=list)


class HistoricalDataPrewarmer:
    """Eagerly fetch historical bars for a set of tickers.

    Constructor wires the two ports the service uses; ``prewarm`` is the
    only entry point. Stateless across calls — the same instance can be
    reused across activations.
    """

    def __init__(
        self,
        *,
        market_data: MarketDataPort,
        repository: BackfillTaskRepositoryPort,
    ) -> None:
        """Initialise with the two collaborating ports.

        Args:
            market_data: Source of historical bars. The adapter is
                expected to lazy-fetch + cache so successive calls for
                the same range are cheap.
            repository: Queue persistence for audit + retry.
        """
        self._market_data = market_data
        self._repository = repository

    async def prewarm(
        self,
        tickers: Iterable[Ticker],
        start_date: date,
        end_date: date,
        *,
        priority: BackfillPriority,
    ) -> PrewarmResult:
        """Pre-warm historical bars for the given tickers + range.

        Args:
            tickers: Tickers to fetch. Iterated once; duplicates are
                de-duplicated by symbol so the same ticker isn't queued
                twice.
            start_date: First trading day of the requested range
                (inclusive).
            end_date: Last trading day of the requested range
                (inclusive). Must be ``>= start_date``.
            priority: ``LOW`` for activation-driven prewarms,
                ``HIGH`` for operator-triggered backfills.

        Returns:
            :class:`PrewarmResult` summarising the per-ticker outcomes.

        Raises:
            ValueError: If ``end_date < start_date``.
        """
        if end_date < start_date:
            raise ValueError(
                f"end_date ({end_date}) must be >= start_date ({start_date})"
            )

        # De-duplicate by Ticker (its __eq__/__hash__ are by symbol).
        unique_tickers = list(dict.fromkeys(tickers))

        result = PrewarmResult()
        for ticker in unique_tickers:
            await self._prewarm_one(
                ticker=ticker,
                start_date=start_date,
                end_date=end_date,
                priority=priority,
                result=result,
            )

        logger.info(
            "prewarm_complete",
            extra={
                "succeeded": len(result.succeeded),
                "failed": len(result.failed),
                "skipped": len(result.skipped),
            },
        )
        return result

    async def _prewarm_one(
        self,
        *,
        ticker: Ticker,
        start_date: date,
        end_date: date,
        priority: BackfillPriority,
        result: PrewarmResult,
    ) -> None:
        """Prewarm a single ticker and append to ``result``."""
        # Step 1 — idempotency.
        try:
            existing = await self._repository.find_existing(
                ticker,
                start_date,
                end_date,
                status_in=NON_TERMINAL_STATUSES,
            )
        except Exception as exc:  # noqa: BLE001 — log + treat as failure
            message = _truncate(str(exc))
            logger.warning(
                "prewarm_idempotency_check_failed",
                extra={"ticker": ticker.symbol, "error": message},
            )
            result.failed.append((ticker, message))
            return
        if existing is not None:
            logger.debug(
                "prewarm_skipped_existing",
                extra={"ticker": ticker.symbol, "existing_id": str(existing.id)},
            )
            result.skipped.append(ticker)
            return

        # Step 2 — insert PENDING row.
        task = BackfillTask(
            id=uuid4(),
            ticker=ticker,
            start_date=start_date,
            end_date=end_date,
            priority=priority,
            status=BackfillTaskStatus.PENDING,
            created_at=datetime.now(UTC),
        )
        try:
            await self._repository.create(task)
        except Exception as exc:  # noqa: BLE001
            message = _truncate(str(exc))
            logger.warning(
                "prewarm_create_failed",
                extra={"ticker": ticker.symbol, "error": message},
            )
            result.failed.append((ticker, message))
            return

        # Step 3 — flip to RUNNING and fetch.
        try:
            await self._repository.mark_running(task.id)
        except Exception as exc:  # noqa: BLE001
            message = _truncate(str(exc))
            logger.warning(
                "prewarm_mark_running_failed",
                extra={
                    "ticker": ticker.symbol,
                    "task_id": str(task.id),
                    "error": message,
                },
            )
            # Try to flip to FAILED so the row doesn't sit in PENDING
            # forever — best-effort; ignore secondary failures.
            await _safe_mark_failed(self._repository, task.id, message)
            result.failed.append((ticker, message))
            return

        try:
            await self._market_data.get_price_history(
                ticker,
                _to_utc_datetime(start_date, end_of_day=False),
                _to_utc_datetime(end_date, end_of_day=True),
                interval="1day",
            )
        except Exception as exc:  # noqa: BLE001
            message = _truncate(str(exc))
            logger.warning(
                "prewarm_fetch_failed",
                extra={
                    "ticker": ticker.symbol,
                    "task_id": str(task.id),
                    "error": message,
                },
            )
            await _safe_mark_failed(self._repository, task.id, message)
            result.failed.append((ticker, message))
            return

        # Step 4 — flip to SUCCEEDED.
        try:
            await self._repository.mark_succeeded(task.id)
        except Exception as exc:  # noqa: BLE001
            message = _truncate(str(exc))
            logger.warning(
                "prewarm_mark_succeeded_failed",
                extra={
                    "ticker": ticker.symbol,
                    "task_id": str(task.id),
                    "error": message,
                },
            )
            # Bookkeeping failure after a successful fetch — log + count
            # as failed so the scheduler retries (the row stays RUNNING;
            # it will be reaped manually on the next prewarm or by an
            # operator). We don't move it to FAILED because the data
            # IS present in price_history.
            result.failed.append((ticker, message))
            return

        result.succeeded.append(ticker)


def _truncate(message: str) -> str:
    """Truncate an error string to the entity-level cap."""
    return message[:_ERROR_MESSAGE_MAX_LENGTH]


def _to_utc_datetime(value: date, *, end_of_day: bool) -> datetime:
    """Convert a ``date`` to a UTC ``datetime`` at start/end of day.

    Args:
        value: Date to convert.
        end_of_day: When True, return 23:59:59 UTC; else 00:00:00 UTC.

    Returns:
        Timezone-aware ``datetime`` in UTC.
    """
    if end_of_day:
        return datetime(value.year, value.month, value.day, 23, 59, 59, tzinfo=UTC)
    return datetime(value.year, value.month, value.day, 0, 0, 0, tzinfo=UTC)


async def _safe_mark_failed(
    repository: BackfillTaskRepositoryPort,
    task_id: "object",
    error_message: str,
) -> None:
    """Flip a task to FAILED, swallowing any secondary error.

    Used in error paths where we want to record the failure but must not
    raise — the primary error already has the caller's attention.
    """
    from uuid import UUID

    if not isinstance(task_id, UUID):  # type: ignore[unreachable]  # defensive
        return
    try:
        await repository.mark_failed(task_id, error_message=error_message)
    except Exception as exc:  # noqa: BLE001
        truncated = str(exc)[:_ERROR_MESSAGE_MAX_LENGTH]
        logger.debug(
            "prewarm_safe_mark_failed_secondary_error",
            extra={"task_id": str(task_id), "error": truncated},
        )


__all__ = ["HistoricalDataPrewarmer", "PrewarmResult"]
