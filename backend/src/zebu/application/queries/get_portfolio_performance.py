"""GetPortfolioPerformance query - Retrieve portfolio performance data over time."""

from dataclasses import dataclass
from datetime import date, timedelta
from enum import Enum
from uuid import UUID

from zebu.application.ports.snapshot_repository import SnapshotRepository
from zebu.domain.entities.portfolio_snapshot import PortfolioSnapshot
from zebu.domain.value_objects.performance_metrics import PerformanceMetrics


class TimeRange(str, Enum):
    """Time range for performance data.

    Defines standard time periods for portfolio performance analysis.
    """

    ONE_WEEK = "1W"
    ONE_MONTH = "1M"
    THREE_MONTHS = "3M"
    ONE_YEAR = "1Y"
    ALL = "ALL"


@dataclass(frozen=True)
class GetPortfolioPerformanceQuery:
    """Input data for retrieving portfolio performance.

    Attributes:
        portfolio_id: Portfolio to get performance for
        time_range: Time period to analyze
    """

    portfolio_id: UUID
    time_range: TimeRange


@dataclass(frozen=True)
class GetPortfolioPerformanceResult:
    """Result of retrieving portfolio performance.

    Attributes:
        portfolio_id: Same as query input
        time_range: Same as query input
        data_points: Snapshots in the time range (ordered by date)
        metrics: Performance metrics (None if insufficient data)
    """

    portfolio_id: UUID
    time_range: TimeRange
    data_points: list[PortfolioSnapshot]
    metrics: PerformanceMetrics | None


class GetPortfolioPerformanceHandler:
    """Handler for GetPortfolioPerformance query.

    Retrieves portfolio snapshots for a time range and calculates performance metrics.
    """

    def __init__(self, snapshot_repository: SnapshotRepository) -> None:
        """Initialize handler with repository dependency.

        Args:
            snapshot_repository: Repository for snapshot persistence
        """
        self._snapshot_repository = snapshot_repository

    async def execute(
        self, query: GetPortfolioPerformanceQuery
    ) -> GetPortfolioPerformanceResult:
        """Execute the GetPortfolioPerformance query.

        Args:
            query: Query with portfolio_id and time_range

        Returns:
            Result containing snapshots and metrics (if available)
        """
        today = date.today()
        start_date = self._calculate_start_date(today, query.time_range)

        # Get snapshots in range
        snapshots = await self._snapshot_repository.get_range(
            portfolio_id=query.portfolio_id,
            start_date=start_date,
            end_date=today,
        )

        # Calculate metrics if we have enough data (at least 2 snapshots)
        metrics = None
        if len(snapshots) >= 2:
            metrics = PerformanceMetrics.calculate(snapshots)

        return GetPortfolioPerformanceResult(
            portfolio_id=query.portfolio_id,
            time_range=query.time_range,
            data_points=snapshots,
            metrics=metrics,
        )

    def _calculate_start_date(self, end_date: date, time_range: TimeRange) -> date:
        """Calculate the start date for a given time range.

        Args:
            end_date: End date (typically today)
            time_range: Time range to calculate from

        Returns:
            Start date for the time range
        """
        match time_range:
            case TimeRange.ONE_WEEK:
                return end_date - timedelta(days=7)
            case TimeRange.ONE_MONTH:
                return end_date - timedelta(days=30)
            case TimeRange.THREE_MONTHS:
                return end_date - timedelta(days=90)
            case TimeRange.ONE_YEAR:
                return end_date - timedelta(days=365)
            case TimeRange.ALL:
                # Return far past date to get all snapshots
                return date(2000, 1, 1)
