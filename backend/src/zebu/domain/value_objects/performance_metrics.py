"""Performance metrics value object.

Calculated performance metrics for a time period.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from zebu.domain.exceptions import InvalidPortfolioError

if TYPE_CHECKING:
    from zebu.domain.entities.portfolio_snapshot import PortfolioSnapshot


@dataclass(frozen=True)
class PerformanceMetrics:
    """Calculated performance metrics for a time period.

    PerformanceMetrics is an immutable value object that encapsulates
    portfolio performance calculations over a specific time period.
    It is typically calculated from a series of PortfolioSnapshot instances.

    Attributes:
        period_start: First date in the measurement period
        period_end: Last date in the measurement period
        starting_value: Portfolio value at period start
        ending_value: Portfolio value at period end
        absolute_gain: Total profit/loss (ending - starting)
        percentage_gain: ROI percentage ((ending/starting - 1) * 100)
        highest_value: Peak portfolio value in period
        lowest_value: Trough portfolio value in period

    Example:
        >>> metrics = PerformanceMetrics.calculate(snapshots)
        >>> print(f"Gain: {metrics.percentage_gain}%")
        Gain: 25.00%
    """

    period_start: date
    period_end: date
    starting_value: Decimal
    ending_value: Decimal
    absolute_gain: Decimal
    percentage_gain: Decimal
    highest_value: Decimal
    lowest_value: Decimal

    def __post_init__(self) -> None:
        """Validate PerformanceMetrics invariants after initialization."""
        # Validate period_end >= period_start
        if self.period_end < self.period_start:
            raise InvalidPortfolioError(
                f"period_end must be >= period_start. "
                f"Got start={self.period_start}, end={self.period_end}"
            )

        # Validate absolute_gain = ending_value - starting_value
        expected_gain = self.ending_value - self.starting_value
        if self.absolute_gain != expected_gain:
            raise InvalidPortfolioError(
                f"absolute_gain must equal ending_value - starting_value. "
                f"Expected {expected_gain}, got {self.absolute_gain}"
            )

        # Validate highest_value >= ending_value and starting_value
        if self.highest_value < self.starting_value:
            raise InvalidPortfolioError(
                f"highest_value must be >= starting_value. "
                f"Got highest={self.highest_value}, starting={self.starting_value}"
            )
        if self.highest_value < self.ending_value:
            raise InvalidPortfolioError(
                f"highest_value must be >= ending_value. "
                f"Got highest={self.highest_value}, ending={self.ending_value}"
            )

        # Validate lowest_value <= ending_value and starting_value
        if self.lowest_value > self.starting_value:
            raise InvalidPortfolioError(
                f"lowest_value must be <= starting_value. "
                f"Got lowest={self.lowest_value}, starting={self.starting_value}"
            )
        if self.lowest_value > self.ending_value:
            raise InvalidPortfolioError(
                f"lowest_value must be <= ending_value. "
                f"Got lowest={self.lowest_value}, ending={self.ending_value}"
            )

    @classmethod
    def calculate(cls, snapshots: list[PortfolioSnapshot]) -> PerformanceMetrics:
        """Calculate metrics from a list of PortfolioSnapshot instances.

        Args:
            snapshots: List of PortfolioSnapshot instances (order doesn't matter)

        Returns:
            PerformanceMetrics calculated from the snapshots

        Raises:
            InvalidPortfolioError: If snapshots list is empty
        """
        if not snapshots:
            raise InvalidPortfolioError("Cannot calculate metrics from empty snapshots")

        # Sort snapshots by date to find first and last
        sorted_snapshots = sorted(snapshots, key=lambda s: s.snapshot_date)
        first = sorted_snapshots[0]
        last = sorted_snapshots[-1]

        # Calculate absolute gain
        absolute_gain = last.total_value - first.total_value

        # Calculate percentage gain, handling division by zero
        if first.total_value > 0:
            percentage_gain = (last.total_value / first.total_value - 1) * 100
            # Round to 2 decimal places
            percentage_gain = percentage_gain.quantize(Decimal("0.01"))
        else:
            # If starting value is zero, percentage gain is not meaningful
            percentage_gain = Decimal("0.00")

        # Find highest and lowest values in the period
        highest_value = max(s.total_value for s in snapshots)
        lowest_value = min(s.total_value for s in snapshots)

        return cls(
            period_start=first.snapshot_date,
            period_end=last.snapshot_date,
            starting_value=first.total_value,
            ending_value=last.total_value,
            absolute_gain=absolute_gain,
            percentage_gain=percentage_gain,
            highest_value=highest_value,
            lowest_value=lowest_value,
        )

    def __repr__(self) -> str:
        """Return repr for debugging.

        Returns:
            String representation of metrics
        """
        return (
            f"PerformanceMetrics("
            f"period={self.period_start} to {self.period_end}, "
            f"gain={self.percentage_gain}%)"
        )
