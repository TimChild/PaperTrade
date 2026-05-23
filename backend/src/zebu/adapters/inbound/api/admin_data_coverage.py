"""Admin data-coverage endpoints (Phase J — Task #212 Layer 4 / Task #215).

Mounted under ``/admin/data-coverage``. Two endpoints:

* ``GET /admin/data-coverage`` — per-ticker coverage summary (range,
  last refresh, gap count, active flag, backfill task status).
  Backed by :class:`DataCoverageQueryHandler`.
* ``POST /admin/data-coverage/backfill`` — operator-driven "catch up"
  backfill of a ticker over the canonical
  ``[ZEBU_HISTORY_EPOCH, today]`` range. Idempotent on
  ``(ticker, start_date, end_date)`` — if a non-terminal
  :class:`BackfillTask` already exists for the same window we return
  the existing task ID rather than creating a duplicate.

Task #215: the operator no longer picks a date range — Alpha Vantage's
``TIME_SERIES_DAILY`` is binary (compact vs full) so a date window was a
knob with no real effect. The endpoint computes
``[ZEBU_HISTORY_EPOCH, today_utc()]`` from the env at request time and
hands that to the task entity.

Authentication: Clerk admin user only — uses :data:`AdminUserDep` from
:mod:`zebu.adapters.inbound.api.dependencies`. Matches the pattern used
by ``/admin/jobs`` and ``/admin/triggers``.
"""

from datetime import UTC, date, datetime
from uuid import UUID, uuid4

import structlog
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from zebu.adapters.inbound.api.dependencies import AdminUserDep, HistoryEpochDep
from zebu.adapters.outbound.database.backfill_task_repository import (
    SQLModelBackfillTaskRepository,
)
from zebu.application.queries.data_coverage import (
    DataCoverageQuery,
    DataCoverageQueryHandler,
)
from zebu.domain.entities.backfill_task import (
    BackfillTask,
    InvalidBackfillTaskError,
)
from zebu.domain.value_objects.backfill_priority import BackfillPriority
from zebu.domain.value_objects.backfill_task_status import (
    NON_TERMINAL_STATUSES,
    BackfillTaskStatus,
)
from zebu.domain.value_objects.ticker import Ticker
from zebu.infrastructure.database import SessionDep

router = APIRouter(prefix="/admin/data-coverage", tags=["admin-data-coverage"])

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Response / request models
# ---------------------------------------------------------------------------


class BackfillStatusPayload(BaseModel):
    """Status of the most-recent surfaceable backfill task for a ticker."""

    task_id: UUID = Field(description="ID of the :class:`BackfillTask`.")
    status: BackfillTaskStatus = Field(
        description="Current lifecycle state of the task.",
    )
    enqueued_at: str = Field(
        description="ISO 8601 UTC timestamp when the task was enqueued.",
    )
    error_message: str | None = Field(
        default=None,
        description=(
            "Truncated reason when ``status == failed``; ``null`` for other states."
        ),
    )


class TickerCoverageEntry(BaseModel):
    """Per-ticker entry in the data-coverage response."""

    ticker: str = Field(description="Stock ticker symbol (uppercase).")
    coverage_start: str | None = Field(
        description=(
            "ISO 8601 date of the earliest daily bar in price_history "
            "for this ticker. ``null`` when we have zero bars for it "
            "but the ticker is otherwise known (e.g. in the watchlist)."
        ),
    )
    coverage_end: str | None = Field(
        description=(
            "ISO 8601 date of the latest daily bar in price_history "
            "for this ticker. ``null`` when we have zero bars."
        ),
    )
    last_refresh: str | None = Field(
        description=(
            "ISO 8601 timestamp (UTC) of the most-recent ``created_at`` "
            "across daily price-history rows for this ticker. ``null`` "
            "when we have zero bars."
        ),
    )
    gap_days_count: int = Field(
        description=(
            "Number of NYSE/NASDAQ trading days inside "
            "``[target_epoch, today_utc()]`` that have NO daily bar. "
            "Always ``>= 0``. Moves to 0 once a successful catch-up "
            "backfill has landed every expected trading day."
        ),
    )
    target_epoch: str = Field(
        description=(
            "ISO 8601 date of ``ZEBU_HISTORY_EPOCH`` — the canonical "
            "earliest target date for a 'catch up' backfill."
        ),
    )
    is_active: bool = Field(
        description=(
            "``True`` when the ticker is in the watchlist OR has been "
            "traded within the active-tickers window (default 30 days)."
        ),
    )
    backfill_status: BackfillStatusPayload | None = Field(
        default=None,
        description=(
            "Most-recent surfaceable backfill task for this ticker. "
            "``null`` when no recent task exists. Non-terminal tasks "
            "(pending / running) are always surfaced; succeeded tasks "
            "surface only for ~60s after completion; failed tasks "
            "surface for ~24h so the operator can act."
        ),
    )


class DataCoverageResponse(BaseModel):
    """Response body for ``GET /admin/data-coverage``."""

    tickers: list[TickerCoverageEntry]


class BackfillRequest(BaseModel):
    """Request body for ``POST /admin/data-coverage/backfill``.

    Task #215: the endpoint computes the date range from the
    ``ZEBU_HISTORY_EPOCH`` env (epoch through today), so the body only
    carries the ticker. Requests that include ``start_date`` /
    ``end_date`` (the pre-Task-215 shape) are rejected with 422 — we
    fail loud rather than silently ignoring the fields.
    """

    # ``extra="forbid"`` so a body with the old ``start_date`` /
    # ``end_date`` fields fails with the standard 422 Pydantic envelope
    # instead of silently dropping the fields and running a backfill
    # over an unexpected range.
    model_config = ConfigDict(extra="forbid")

    ticker: str = Field(
        description="Stock ticker symbol to catch up (uppercase recommended).",
    )


class BackfillResponse(BaseModel):
    """Response body for ``POST /admin/data-coverage/backfill``."""

    task_id: UUID = Field(description="ID of the :class:`BackfillTask`.")
    status: BackfillTaskStatus = Field(
        description=(
            "Current status of the task. ``pending`` for a freshly "
            "created task; ``pending``/``running`` for a returned-"
            "existing task per idempotency."
        ),
    )
    existing: bool = Field(
        description=(
            "``True`` when a non-terminal task already existed for the "
            "same ``(ticker, target_epoch, today)`` window and the "
            "endpoint returned that one instead of creating a new task."
        ),
    )
    start_date: str = Field(
        description=("ISO date of the computed range start (``ZEBU_HISTORY_EPOCH``)."),
    )
    end_date: str = Field(
        description="ISO date of the computed range end (today, UTC).",
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=DataCoverageResponse,
)
async def admin_data_coverage(
    admin_user_id: AdminUserDep,
    history_epoch: HistoryEpochDep,
    session: SessionDep,
) -> DataCoverageResponse:
    """Per-ticker price-history coverage summary.

    Operator UI polls this endpoint every ~30 seconds while the
    coverage page is open to monitor backfill progress. The handler is
    read-only and pure SQL aggregates — performance scales with the
    number of distinct tickers, not the total ``price_history`` row
    count.

    Auth: Clerk admin only (``AdminUserDep`` reads the env-driven
    ``ADMIN_USER_IDS`` allowlist).

    Returns one entry per ticker, sorted by symbol ascending. See
    :class:`TickerCoverageEntry` for the per-entry shape.
    """
    handler = DataCoverageQueryHandler(session)
    result = await handler.execute(DataCoverageQuery(target_epoch=history_epoch))

    entries = [
        TickerCoverageEntry(
            ticker=row.ticker.symbol,
            coverage_start=row.coverage_start.isoformat()
            if row.coverage_start is not None
            else None,
            coverage_end=row.coverage_end.isoformat()
            if row.coverage_end is not None
            else None,
            last_refresh=row.last_refresh.isoformat()
            if row.last_refresh is not None
            else None,
            gap_days_count=row.gap_days_count,
            target_epoch=row.target_epoch.isoformat(),
            is_active=row.is_active,
            backfill_status=(
                BackfillStatusPayload(
                    task_id=row.backfill_status.task_id,
                    status=row.backfill_status.status,
                    enqueued_at=row.backfill_status.enqueued_at.isoformat(),
                    error_message=row.backfill_status.error_message,
                )
                if row.backfill_status is not None
                else None
            ),
        )
        for row in result.tickers
    ]

    logger.info(
        "admin_data_coverage_polled",
        admin_user_id=str(admin_user_id),
        tickers_total=len(entries),
        tickers_with_gaps=sum(1 for e in entries if e.gap_days_count > 0),
        target_epoch=history_epoch.isoformat(),
    )
    return DataCoverageResponse(tickers=entries)


@router.post(
    "/backfill",
    response_model=BackfillResponse,
    status_code=status.HTTP_201_CREATED,
)
async def admin_data_coverage_backfill(
    payload: BackfillRequest,
    admin_user_id: AdminUserDep,
    history_epoch: HistoryEpochDep,
    session: SessionDep,
) -> BackfillResponse:
    """Enqueue a "catch up" backfill task for the specified ticker.

    The range is computed server-side as
    ``[ZEBU_HISTORY_EPOCH, today_utc()]`` — the operator no longer
    chooses dates. Alpha Vantage's daily endpoint is binary
    (``compact``: ~100 bars, 1 call; ``full``: ~20 years, 1 call) and
    auto-picks ``full`` for any span > 90 days, so a user-tunable
    window was friction with no benefit.

    Idempotent on ``(ticker, ZEBU_HISTORY_EPOCH, today_utc())``:
    if a non-terminal :class:`BackfillTask` already exists for the same
    window we return that one rather than creating a duplicate. This
    protects against accidental double-submits from the UI while still
    letting the operator re-enqueue a previously-FAILED window
    (terminal tasks don't block new ones).

    The created task always uses :attr:`BackfillPriority.HIGH` — admin
    catch-ups pre-empt scheduled refreshes on paid AV tiers and defer
    when the cap is hit. Range computation happens at request time, so
    a Sunday catch-up will set ``end_date`` to that Sunday; the AV
    adapter's calendar-aware fetch handles weekends without complaint.

    Auth: Clerk admin only.

    Returns:
        ``BackfillResponse`` with ``task_id``, current ``status``, the
        ``existing`` flag (true when deduped), and the resolved
        ``start_date`` / ``end_date`` so the operator sees the exact
        window that was used.

    Raises:
        HTTPException 400: On ticker validation errors (the domain
            raises :class:`InvalidTickerError`, mapped via the
            registered exception handler).
        HTTPException 422: On invariant violations from
            :class:`BackfillTask` construction (e.g. ``end_date <
            start_date`` if ``ZEBU_HISTORY_EPOCH`` was set to a
            date in the future).
    """
    # Normalise the ticker through the value object so invalid input
    # surfaces as the standard InvalidTickerError -> 400 via the
    # registered exception handler.
    ticker = Ticker(payload.ticker)

    start_date: date = history_epoch
    end_date: date = datetime.now(UTC).date()

    repo = SQLModelBackfillTaskRepository(session)

    existing = await repo.find_existing(
        ticker=ticker,
        start_date=start_date,
        end_date=end_date,
        status_in=NON_TERMINAL_STATUSES,
    )
    if existing is not None:
        logger.info(
            "admin_data_coverage_backfill_deduped",
            admin_user_id=str(admin_user_id),
            ticker=ticker.symbol,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            existing_task_id=str(existing.id),
            existing_status=existing.status.value,
        )
        return BackfillResponse(
            task_id=existing.id,
            status=existing.status,
            existing=True,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
        )

    now = datetime.now(UTC)
    try:
        task = BackfillTask(
            id=uuid4(),
            ticker=ticker,
            start_date=start_date,
            end_date=end_date,
            priority=BackfillPriority.HIGH,
            status=BackfillTaskStatus.PENDING,
            created_at=now,
        )
    except InvalidBackfillTaskError as exc:
        # Surface domain-level invariants (e.g. ``end_date <
        # start_date`` when ZEBU_HISTORY_EPOCH is misconfigured to a
        # future date) as a 422 with the structured envelope.
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    persisted = await repo.create(task)

    logger.info(
        "admin_data_coverage_backfill_created",
        admin_user_id=str(admin_user_id),
        ticker=ticker.symbol,
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat(),
        priority=BackfillPriority.HIGH.value,
        task_id=str(persisted.id),
    )

    return BackfillResponse(
        task_id=persisted.id,
        status=persisted.status,
        existing=False,
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat(),
    )
