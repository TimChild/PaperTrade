"""Analytics API routes.

Provides REST endpoints for portfolio analytics:
- Performance data over time
- Portfolio composition (asset allocation)
- Snapshot job management (admin)
"""

import logging
from datetime import date
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from papertrade.adapters.inbound.api.dependencies import (
    CurrentUserDep,
    MarketDataDep,
    PortfolioRepositoryDep,
    SnapshotRepositoryDep,
    TransactionRepositoryDep,
    get_snapshot_job,
)
from papertrade.application.queries.get_portfolio_composition import (
    GetPortfolioCompositionHandler,
    GetPortfolioCompositionQuery,
    GetPortfolioCompositionResult,
)
from papertrade.application.queries.get_portfolio_performance import (
    GetPortfolioPerformanceHandler,
    GetPortfolioPerformanceQuery,
    GetPortfolioPerformanceResult,
    TimeRange,
)
from papertrade.application.services.snapshot_job import SnapshotJobService
from papertrade.domain.exceptions import InvalidPortfolioError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/portfolios", tags=["analytics"])


# Response Models


class DataPointSchema(BaseModel):
    """Snapshot data point for performance chart."""

    date: date
    total_value: Decimal
    cash_balance: Decimal
    holdings_value: Decimal


class MetricsSchema(BaseModel):
    """Performance metrics for a time period."""

    starting_value: Decimal
    ending_value: Decimal
    absolute_gain: Decimal
    percentage_gain: Decimal
    highest_value: Decimal
    lowest_value: Decimal


class PerformanceResponse(BaseModel):
    """Portfolio performance response."""

    portfolio_id: UUID
    range: str
    data_points: list[DataPointSchema]
    metrics: MetricsSchema | None

    @classmethod
    def from_result(
        cls, result: GetPortfolioPerformanceResult
    ) -> "PerformanceResponse":
        """Convert query result to API response.

        Args:
            result: Query result from GetPortfolioPerformanceHandler

        Returns:
            API response model
        """
        return cls(
            portfolio_id=result.portfolio_id,
            range=result.time_range.value,
            data_points=[
                DataPointSchema(
                    date=snapshot.snapshot_date,
                    total_value=snapshot.total_value,
                    cash_balance=snapshot.cash_balance,
                    holdings_value=snapshot.holdings_value,
                )
                for snapshot in result.data_points
            ],
            metrics=MetricsSchema(
                starting_value=result.metrics.starting_value,
                ending_value=result.metrics.ending_value,
                absolute_gain=result.metrics.absolute_gain,
                percentage_gain=result.metrics.percentage_gain,
                highest_value=result.metrics.highest_value,
                lowest_value=result.metrics.lowest_value,
            )
            if result.metrics
            else None,
        )


class CompositionItemSchema(BaseModel):
    """Portfolio composition item (holding or cash)."""

    ticker: str
    value: Decimal
    percentage: Decimal
    quantity: int | None


class CompositionResponse(BaseModel):
    """Portfolio composition response."""

    portfolio_id: UUID
    total_value: Decimal
    composition: list[CompositionItemSchema]

    @classmethod
    def from_result(
        cls, result: GetPortfolioCompositionResult
    ) -> "CompositionResponse":
        """Convert query result to API response.

        Args:
            result: Query result from GetPortfolioCompositionHandler

        Returns:
            API response model
        """
        return cls(
            portfolio_id=result.portfolio_id,
            total_value=result.total_value,
            composition=[
                CompositionItemSchema(
                    ticker=item.ticker,
                    value=item.value,
                    percentage=item.percentage,
                    quantity=item.quantity,
                )
                for item in result.composition
            ],
        )


# Route Handlers


@router.get("/{portfolio_id}/performance", response_model=PerformanceResponse)
async def get_performance(
    portfolio_id: UUID,
    current_user_id: CurrentUserDep,
    portfolio_repo: PortfolioRepositoryDep,
    snapshot_repo: SnapshotRepositoryDep,
    range: Annotated[TimeRange, Query(alias="range")] = TimeRange.ONE_MONTH,
) -> PerformanceResponse:
    """Get portfolio performance data for charts.

    Returns historical snapshots and performance metrics for the specified time range.

    Args:
        portfolio_id: Portfolio UUID
        current_user_id: Authenticated user ID (from Bearer token)
        portfolio_repo: Portfolio repository dependency
        snapshot_repo: Snapshot repository dependency
        range: Time range filter (1W, 1M, 3M, 1Y, ALL)

    Returns:
        Performance data with snapshots and metrics

    Raises:
        404: Portfolio not found or user doesn't own it
    """
    # Verify portfolio exists and belongs to user
    portfolio = await portfolio_repo.get(portfolio_id)
    if portfolio is None or portfolio.user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Portfolio not found: {portfolio_id}",
        )

    # Execute query
    handler = GetPortfolioPerformanceHandler(snapshot_repo)
    query = GetPortfolioPerformanceQuery(
        portfolio_id=portfolio_id,
        time_range=range,
    )
    result = await handler.execute(query)

    return PerformanceResponse.from_result(result)


@router.get("/{portfolio_id}/composition", response_model=CompositionResponse)
async def get_composition(
    portfolio_id: UUID,
    current_user_id: CurrentUserDep,
    portfolio_repo: PortfolioRepositoryDep,
    transaction_repo: TransactionRepositoryDep,
    market_data: MarketDataDep,
) -> CompositionResponse:
    """Get portfolio holdings composition for pie chart.

    Returns current asset allocation with live market prices.

    Args:
        portfolio_id: Portfolio UUID
        current_user_id: Authenticated user ID (from Bearer token)
        portfolio_repo: Portfolio repository dependency
        transaction_repo: Transaction repository dependency
        market_data: Market data port dependency

    Returns:
        Portfolio composition with percentages

    Raises:
        404: Portfolio not found or user doesn't own it
    """
    # Verify portfolio exists and belongs to user
    portfolio = await portfolio_repo.get(portfolio_id)
    if portfolio is None or portfolio.user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Portfolio not found: {portfolio_id}",
        )

    # Execute query
    handler = GetPortfolioCompositionHandler(
        portfolio_repo, transaction_repo, market_data
    )
    query = GetPortfolioCompositionQuery(portfolio_id=portfolio_id)

    try:
        result = await handler.execute(query)
        return CompositionResponse.from_result(result)
    except InvalidPortfolioError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


# Route Handlers - Snapshot Job Admin Endpoints


@router.post("/{portfolio_id}/snapshots/backfill", status_code=201)
async def backfill_portfolio_snapshots(
    portfolio_id: UUID,
    start_date: date,
    end_date: date,
    snapshot_job: SnapshotJobService = Depends(get_snapshot_job),
    current_user_id: UUID = Depends(CurrentUserDep),
) -> dict[str, int | str]:
    """Backfill historical snapshots for a portfolio.

    Generates snapshots for each day in the specified date range.
    Useful for new portfolios or fixing gaps in snapshot history.

    **Admin only** (TODO: Add admin authentication)

    Args:
        portfolio_id: Portfolio to backfill
        start_date: Start of date range (inclusive)
        end_date: End of date range (inclusive)
        snapshot_job: Snapshot job service (injected)
        current_user_id: Current user ID (injected, for future admin check)

    Returns:
        dict with results: {"status": "completed", "results": {...}}

    Raises:
        HTTPException: 404 if portfolio not found
        HTTPException: 400 if date range is invalid
        HTTPException: 501 if service not configured
    """
    # Validate date range
    if start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"start_date ({start_date}) must be <= end_date ({end_date})",
        )

    # TODO: Add admin authentication check
    # TODO: Verify user owns the portfolio

    logger.info(
        f"Backfill requested for portfolio {portfolio_id} "
        f"from {start_date} to {end_date}"
    )

    try:
        results = await snapshot_job.backfill_snapshots(
            portfolio_id=portfolio_id,
            start_date=start_date,
            end_date=end_date,
        )
        return {"status": "completed", "results": results}
    except ValueError as e:
        # Portfolio not found
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(f"Backfill failed for portfolio {portfolio_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Backfill failed: {str(e)}",
        ) from e


# Separate router for admin-level snapshot operations
admin_router = APIRouter(prefix="/analytics", tags=["analytics-admin"])


@admin_router.post("/snapshots/daily", status_code=201)
async def trigger_daily_snapshots(
    snapshot_job: SnapshotJobService = Depends(get_snapshot_job),
    current_user_id: UUID = Depends(CurrentUserDep),
) -> dict[str, int | str]:
    """Manually trigger daily snapshot job for all portfolios.

    Calculates snapshots for all portfolios for today's date.
    Snapshots are upserted (updated if already exist).

    **Admin only** (TODO: Add admin authentication)

    Args:
        snapshot_job: Snapshot job service (injected)
        current_user_id: Current user ID (injected, for future admin check)

    Returns:
        dict with results: {"status": "completed", "results": {...}}

    Raises:
        HTTPException: 501 if service not configured
    """
    # TODO: Add admin authentication check

    logger.info("Manual daily snapshot triggered")

    try:
        results = await snapshot_job.run_daily_snapshot()
        return {"status": "completed", "results": results}
    except Exception as e:
        logger.error(f"Daily snapshot failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Daily snapshot failed: {str(e)}",
        ) from e

