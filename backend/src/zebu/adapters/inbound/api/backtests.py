"""Backtest API routes.

Provides REST endpoints for backtest operations:
- Run a backtest (synchronous)
- List user's backtest runs
- Get backtest run details
- Delete backtest + associated portfolio
"""

from datetime import date
from decimal import Decimal
from typing import Self
from uuid import UUID

import structlog
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator, model_validator

from zebu.adapters.inbound.api.dependencies import (
    ActiveApiKeyIdDep,
    BacktestRateLimiterDep,
    CurrentUserDep,
    MarketDataDep,
)
from zebu.adapters.inbound.api.schemas import (
    DEFAULT_PAGE_LIMIT,
    MAX_PAGE_LIMIT,
    PaginatedResponse,
)
from zebu.adapters.inbound.api.schemas.errors import ErrorCode, ErrorResponse
from zebu.adapters.inbound.api.schemas.pagination import build_paginated_response
from zebu.adapters.outbound.database.backtest_run_repository import (
    SQLModelBacktestRunRepository,
)
from zebu.adapters.outbound.database.portfolio_repository import (
    SQLModelPortfolioRepository,
)
from zebu.adapters.outbound.database.snapshot_repository import (
    SQLModelSnapshotRepository,
)
from zebu.adapters.outbound.database.strategy_repository import (
    SQLModelStrategyRepository,
)
from zebu.adapters.outbound.database.transaction_repository import (
    SQLModelTransactionRepository,
)
from zebu.application.commands.run_backtest import RunBacktestCommand
from zebu.application.exceptions import TickerNotFoundError
from zebu.application.services.backtest_executor import BacktestExecutor
from zebu.application.services.historical_data_preparer import HistoricalDataPreparer
from zebu.application.services.snapshot_job import SnapshotJobService
from zebu.domain.entities.backtest_run import BacktestRun
from zebu.domain.exceptions import InsufficientHistoricalDataError, InvalidStrategyError
from zebu.infrastructure.database import SessionDep

router = APIRouter(prefix="/backtests", tags=["backtests"])

# Module-level structlog logger. Picks up the actor identity bound by
# get_current_user (auth_method, clerk_user_id, api_key_id, api_key_label)
# automatically via structlog.contextvars — Phase H5.
logger = structlog.get_logger(__name__)

_MAX_DATE_RANGE_DAYS = 3 * 365


# Request/Response Models


class RunBacktestRequest(BaseModel):
    """Request to run a backtest."""

    strategy_id: UUID
    backtest_name: str = Field(..., min_length=1, max_length=100)
    start_date: date
    end_date: date
    initial_cash: Decimal = Field(..., gt=0, decimal_places=2)

    @field_validator("end_date")
    @classmethod
    def validate_end_date_not_future(cls, v: date) -> date:
        """Validate end_date is not in the future."""
        if v > date.today():
            raise ValueError("end_date cannot be in the future")
        return v

    @model_validator(mode="after")
    def validate_date_range(self) -> "Self":
        """Validate start_date < end_date and range <= 3 years."""
        if self.end_date <= self.start_date:
            raise ValueError("end_date must be after start_date")
        if (self.end_date - self.start_date).days > _MAX_DATE_RANGE_DAYS:
            raise ValueError(
                f"Date range cannot exceed {_MAX_DATE_RANGE_DAYS} days (3 years)"
            )
        return self


class BacktestRunResponse(BaseModel):
    """Backtest run details response."""

    id: UUID
    user_id: UUID
    strategy_id: UUID | None
    portfolio_id: UUID
    backtest_name: str
    start_date: str
    end_date: str
    initial_cash: str
    status: str
    created_at: str
    completed_at: str | None
    error_message: str | None
    total_return_pct: str | None
    max_drawdown_pct: str | None
    annualized_return_pct: str | None
    total_trades: int | None


def _to_backtest_response(run: BacktestRun) -> BacktestRunResponse:
    return BacktestRunResponse(
        id=run.id,
        user_id=run.user_id,
        strategy_id=run.strategy_id,
        portfolio_id=run.portfolio_id,
        backtest_name=run.backtest_name,
        start_date=run.start_date.isoformat(),
        end_date=run.end_date.isoformat(),
        initial_cash=f"{run.initial_cash.amount:.2f}",
        status=run.status.value,
        created_at=run.created_at.isoformat(),
        completed_at=run.completed_at.isoformat() if run.completed_at else None,
        error_message=run.error_message,
        total_return_pct=f"{run.total_return_pct:.4f}"
        if run.total_return_pct is not None
        else None,
        max_drawdown_pct=f"{run.max_drawdown_pct:.4f}"
        if run.max_drawdown_pct is not None
        else None,
        annualized_return_pct=f"{run.annualized_return_pct:.4f}"
        if run.annualized_return_pct is not None
        else None,
        total_trades=run.total_trades,
    )


def _build_executor(
    session: SessionDep,
    market_data: MarketDataDep,
) -> BacktestExecutor:
    """Build a BacktestExecutor with all required dependencies."""
    portfolio_repo = SQLModelPortfolioRepository(session)
    transaction_repo = SQLModelTransactionRepository(session)
    strategy_repo = SQLModelStrategyRepository(session)
    backtest_run_repo = SQLModelBacktestRunRepository(session)
    snapshot_repo = SQLModelSnapshotRepository(session)

    snapshot_service = SnapshotJobService(
        portfolio_repo=portfolio_repo,
        transaction_repo=transaction_repo,
        snapshot_repo=snapshot_repo,
        market_data=market_data,
    )
    data_preparer = HistoricalDataPreparer(market_data=market_data)

    return BacktestExecutor(
        portfolio_repo=portfolio_repo,
        transaction_repo=transaction_repo,
        strategy_repo=strategy_repo,
        backtest_run_repo=backtest_run_repo,
        snapshot_service=snapshot_service,
        snapshot_repo=snapshot_repo,
        data_preparer=data_preparer,
    )


# Routes


@router.post(
    "",
    response_model=BacktestRunResponse,
    status_code=status.HTTP_201_CREATED,
)
async def run_backtest(
    request: RunBacktestRequest,
    current_user: CurrentUserDep,
    api_key_id: ActiveApiKeyIdDep,
    session: SessionDep,
    market_data: MarketDataDep,
    rate_limiter: BacktestRateLimiterDep,
) -> BacktestRunResponse:
    """Run a backtest synchronously.

    Validates the request, runs the full simulation pipeline, and returns
    the completed BacktestRun with performance metrics.

    Phase H2: ``api_key_id`` is captured at command construction so every
    write the pipeline performs (BacktestRun, synthetic portfolio's deposit,
    trade transactions) is stamped with the originating credential.

    Phase F-6: per-API-key inbound rate limit (5/min, 100/day by default;
    configurable via ``ZEBU_BACKTEST_RATE_LIMIT_MIN`` /
    ``ZEBU_BACKTEST_RATE_LIMIT_DAY``). Clerk Bearer requests bypass the
    limiter — the cap exists to bound machine-identity throughput so a
    misbehaving agent can't drown the backtest engine. Limit-exceeded
    responses are 429 with the standard error envelope, a ``Retry-After``
    header, and an explanatory ``fields`` block.

    Raises:
        HTTPException: 404 if strategy not found
        HTTPException: 422 if validation fails
        HTTPException: 429 if the per-API-key rate limit is exhausted
    """
    rl_result = await rate_limiter.check_and_consume(api_key_id=api_key_id)
    if not rl_result.allowed:
        retry_after_seconds = max(1, int(rl_result.retry_after_seconds + 0.999))
        envelope = ErrorResponse(
            detail=(
                "Backtest rate limit exceeded — "
                f"{rl_result.minute_used}/{rl_result.minute_limit} per minute "
                f"and {rl_result.day_used}/{rl_result.day_limit} per day. "
                f"Retry after {retry_after_seconds}s."
            ),
            code=ErrorCode.RATE_LIMIT_EXCEEDED.value,
            fields={
                "minute_limit": str(rl_result.minute_limit),
                "minute_used": str(rl_result.minute_used),
                "day_limit": str(rl_result.day_limit),
                "day_used": str(rl_result.day_used),
                "retry_after_seconds": str(retry_after_seconds),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=envelope.model_dump(),
            headers={"Retry-After": str(retry_after_seconds)},
        )

    command = RunBacktestCommand(
        user_id=current_user,
        strategy_id=request.strategy_id,
        backtest_name=request.backtest_name,
        start_date=request.start_date,
        end_date=request.end_date,
        initial_cash=request.initial_cash,
        api_key_id=api_key_id,
    )

    executor = _build_executor(session=session, market_data=market_data)

    logger.info(
        "Backtest run requested",
        strategy_id=str(request.strategy_id),
        start_date=request.start_date.isoformat(),
        end_date=request.end_date.isoformat(),
        initial_cash=str(request.initial_cash),
    )

    try:
        backtest_run = await executor.execute(command)
    except InvalidStrategyError as exc:
        # Strategy lookup failed — request never reached the engine.
        # Refund the rate-limit token so a corrected retry isn't penalised.
        await rate_limiter.refund(api_key_id=api_key_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except (InsufficientHistoricalDataError, TickerNotFoundError) as exc:
        # Market-data gap — neither error is the agent's fault; refund
        # the rate-limit token. ``TickerNotFoundError`` was previously
        # propagating to FastAPI's default handler → 500 with empty
        # body, which is what the smoke-test agent observed against
        # AAPL 2024 on prod. Surface it as 503 with a clear message
        # so agents can backoff intelligently.
        await rate_limiter.refund(api_key_id=api_key_id)
        logger.info(
            "Backtest rejected — historical data unavailable",
            strategy_id=str(request.strategy_id),
            start_date=request.start_date.isoformat(),
            end_date=request.end_date.isoformat(),
            reason=str(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        # Catch-all: refund the rate-limit token AND log the stack
        # before re-raising. Without this, unhandled errors silently
        # consumed tokens *and* presented as 500 with no body — the
        # agent had no way to diagnose what was happening.
        await rate_limiter.refund(api_key_id=api_key_id)
        logger.exception(
            "Backtest run failed unexpectedly",
            strategy_id=str(request.strategy_id),
            start_date=request.start_date.isoformat(),
            end_date=request.end_date.isoformat(),
        )
        raise

    logger.info(
        "Backtest run completed",
        backtest_id=str(backtest_run.id),
        status=backtest_run.status.value,
        total_trades=backtest_run.total_trades,
    )

    return _to_backtest_response(backtest_run)


@router.get("", response_model=PaginatedResponse[BacktestRunResponse])
async def list_backtests(
    current_user: CurrentUserDep,
    session: SessionDep,
    limit: int = Query(
        default=DEFAULT_PAGE_LIMIT,
        ge=1,
        le=MAX_PAGE_LIMIT,
        description="Maximum number of backtest runs to return (1-100, default 20).",
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Number of backtest runs to skip for pagination (default 0).",
    ),
) -> PaginatedResponse[BacktestRunResponse]:
    """List backtest runs for the current user with pagination."""
    repo = SQLModelBacktestRunRepository(session)
    # Repo returns owner-scoped runs in creation order. Pagination is applied
    # in Python; SQL push-down is tracked in the perf audit cross-cut and
    # will matter once Phase C/D agents start scheduling backtests.
    runs = await repo.get_by_user(current_user)
    total = len(runs)
    page = runs[offset : offset + limit]
    items = [_to_backtest_response(r) for r in page]
    return build_paginated_response(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{backtest_id}", response_model=BacktestRunResponse)
async def get_backtest(
    backtest_id: UUID,
    current_user: CurrentUserDep,
    session: SessionDep,
) -> BacktestRunResponse:
    """Get a backtest run by ID."""
    repo = SQLModelBacktestRunRepository(session)
    run = await repo.get(backtest_id)

    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Backtest run not found: {backtest_id}",
        )

    if run.user_id != current_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this backtest run",
        )

    return _to_backtest_response(run)


@router.delete("/{backtest_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_backtest(
    backtest_id: UUID,
    current_user: CurrentUserDep,
    session: SessionDep,
) -> None:
    """Delete a backtest run and its associated portfolio.

    Deletes the BacktestRun entity along with the associated BACKTEST portfolio,
    its transactions, and portfolio snapshots.
    """
    backtest_repo = SQLModelBacktestRunRepository(session)
    run = await backtest_repo.get(backtest_id)

    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Backtest run not found: {backtest_id}",
        )

    if run.user_id != current_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete this backtest run",
        )

    # Delete associated data
    transaction_repo = SQLModelTransactionRepository(session)
    snapshot_repo = SQLModelSnapshotRepository(session)
    portfolio_repo = SQLModelPortfolioRepository(session)

    await transaction_repo.delete_by_portfolio(run.portfolio_id)
    await snapshot_repo.delete_by_portfolio(run.portfolio_id)
    await portfolio_repo.delete(run.portfolio_id)
    await backtest_repo.delete(backtest_id)
