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

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, field_validator, model_validator

from zebu.adapters.inbound.api.dependencies import (
    CurrentUserDep,
    MarketDataDep,
)
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
from zebu.application.services.backtest_executor import BacktestExecutor
from zebu.application.services.historical_data_preparer import HistoricalDataPreparer
from zebu.application.services.snapshot_job import SnapshotJobService
from zebu.domain.entities.backtest_run import BacktestRun
from zebu.domain.exceptions import InvalidStrategyError
from zebu.infrastructure.database import SessionDep

router = APIRouter(prefix="/backtests", tags=["backtests"])

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
        initial_cash=f"{run.initial_cash:.2f}",
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
    session: SessionDep,
    market_data: MarketDataDep,
) -> BacktestRunResponse:
    """Run a backtest synchronously.

    Validates the request, runs the full simulation pipeline, and returns
    the completed BacktestRun with performance metrics.

    Raises:
        HTTPException: 404 if strategy not found
        HTTPException: 422 if validation fails
    """
    command = RunBacktestCommand(
        user_id=current_user,
        strategy_id=request.strategy_id,
        backtest_name=request.backtest_name,
        start_date=request.start_date,
        end_date=request.end_date,
        initial_cash=request.initial_cash,
    )

    executor = _build_executor(session=session, market_data=market_data)

    try:
        backtest_run = await executor.execute(command)
    except InvalidStrategyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return _to_backtest_response(backtest_run)


@router.get("", response_model=list[BacktestRunResponse])
async def list_backtests(
    current_user: CurrentUserDep,
    session: SessionDep,
) -> list[BacktestRunResponse]:
    """List all backtest runs for the current user."""
    repo = SQLModelBacktestRunRepository(session)
    runs = await repo.get_by_user(current_user)
    return [_to_backtest_response(r) for r in runs]


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
