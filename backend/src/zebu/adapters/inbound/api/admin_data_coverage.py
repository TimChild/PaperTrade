"""Admin data-coverage endpoints (Phase J — Task #212 Layer 4).

Mounted under ``/admin/data-coverage``. Two endpoints:

* ``GET /admin/data-coverage`` — per-ticker coverage summary (range,
  last refresh, gap count, active flag). Backed by
  :class:`DataCoverageQueryHandler`.
* ``POST /admin/data-coverage/backfill`` — operator-driven backfill of
  a ticker over a date range. Idempotent on
  ``(ticker, start_date, end_date)`` — if a non-terminal
  :class:`BackfillTask` already exists for the same window we return
  the existing task ID rather than creating a duplicate.

Authentication: Clerk admin user only — uses :data:`AdminUserDep` from
:mod:`zebu.adapters.inbound.api.dependencies`. Matches the pattern used
by ``/admin/jobs`` and ``/admin/triggers``.
"""

from datetime import UTC, date, datetime
from uuid import UUID, uuid4

import structlog
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from zebu.adapters.inbound.api.dependencies import AdminUserDep
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
            "``[coverage_start, coverage_end]`` that have NO daily bar. "
            "Pre-``coverage_start`` data is not counted as a gap. "
            "Always ``>= 0``; ``0`` when there are no bars."
        ),
    )
    is_active: bool = Field(
        description=(
            "``True`` when the ticker is in the watchlist OR has been "
            "traded within the active-tickers window (default 30 days)."
        ),
    )


class DataCoverageResponse(BaseModel):
    """Response body for ``GET /admin/data-coverage``."""

    tickers: list[TickerCoverageEntry]


class BackfillRequest(BaseModel):
    """Request body for ``POST /admin/data-coverage/backfill``.

    The endpoint creates a :class:`BackfillTask` in ``PENDING`` state.
    The scheduler's pickup loop drains pending tasks each refresh cycle.
    """

    ticker: str = Field(
        description="Stock ticker symbol to backfill (uppercase recommended).",
    )
    start_date: date = Field(
        description="First trading day of the backfill range (inclusive).",
    )
    end_date: date = Field(
        description="Last trading day of the backfill range (inclusive).",
    )
    priority: BackfillPriority = Field(
        default=BackfillPriority.HIGH,
        description=(
            "Priority ladder — ``high`` is the default for operator-"
            "triggered backfills (pre-empts the AV daily cap on paid "
            "tiers); ``low`` defers when the cap is hit."
        ),
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
            "same ``(ticker, start_date, end_date)`` and the endpoint "
            "returned that one instead of creating a new task."
        ),
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
    result = await handler.execute(DataCoverageQuery())

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
            is_active=row.is_active,
        )
        for row in result.tickers
    ]

    logger.info(
        "admin_data_coverage_polled",
        admin_user_id=str(admin_user_id),
        tickers_total=len(entries),
        tickers_with_gaps=sum(1 for e in entries if e.gap_days_count > 0),
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
    session: SessionDep,
) -> BackfillResponse:
    """Enqueue a backfill task for the specified ticker and range.

    Idempotent on ``(ticker, start_date, end_date)``: if a non-terminal
    :class:`BackfillTask` already exists for the same window we return
    that one rather than creating a duplicate. This protects against
    accidental double-submits from the UI while still letting the
    operator re-enqueue a previously-FAILED window (terminal tasks
    don't block new ones).

    The created task starts in ``PENDING``. The scheduler's
    ``refresh_active_stocks`` cron drains pending tasks each cycle.

    Auth: Clerk admin only.

    Returns:
        ``BackfillResponse`` with ``task_id``, current ``status``, and
        an ``existing: bool`` flag the UI uses to differentiate a fresh
        enqueue from a deduped one.

    Raises:
        HTTPException 400: On ticker / range validation errors. The
            domain raises :class:`InvalidTickerError` or
            :class:`InvalidBackfillTaskError`; both are mapped via the
            registered exception handlers.
    """
    # Normalise the ticker through the value object so invalid input
    # surfaces as the standard InvalidTickerError -> 400 via the
    # registered exception handler.
    ticker = Ticker(payload.ticker)

    repo = SQLModelBackfillTaskRepository(session)

    existing = await repo.find_existing(
        ticker=ticker,
        start_date=payload.start_date,
        end_date=payload.end_date,
        status_in=NON_TERMINAL_STATUSES,
    )
    if existing is not None:
        logger.info(
            "admin_data_coverage_backfill_deduped",
            admin_user_id=str(admin_user_id),
            ticker=ticker.symbol,
            start_date=payload.start_date.isoformat(),
            end_date=payload.end_date.isoformat(),
            existing_task_id=str(existing.id),
            existing_status=existing.status.value,
        )
        return BackfillResponse(
            task_id=existing.id,
            status=existing.status,
            existing=True,
        )

    now = datetime.now(UTC)
    try:
        task = BackfillTask(
            id=uuid4(),
            ticker=ticker,
            start_date=payload.start_date,
            end_date=payload.end_date,
            priority=payload.priority,
            status=BackfillTaskStatus.PENDING,
            created_at=now,
        )
    except InvalidBackfillTaskError as exc:
        # Surface domain-level invariants (e.g. ``end_date <
        # start_date``) as a 422 with the structured envelope. The
        # exception handler module doesn't have a dedicated route for
        # this class yet — raise an explicit HTTPException so the
        # uniform handler emits the standard ErrorResponse shape.
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    persisted = await repo.create(task)

    logger.info(
        "admin_data_coverage_backfill_created",
        admin_user_id=str(admin_user_id),
        ticker=ticker.symbol,
        start_date=payload.start_date.isoformat(),
        end_date=payload.end_date.isoformat(),
        priority=payload.priority.value,
        task_id=str(persisted.id),
    )

    return BackfillResponse(
        task_id=persisted.id,
        status=persisted.status,
        existing=False,
    )
