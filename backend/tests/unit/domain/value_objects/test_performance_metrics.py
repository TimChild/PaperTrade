"""Tests for PerformanceMetrics value object."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from papertrade.domain.entities.portfolio_snapshot import PortfolioSnapshot
from papertrade.domain.exceptions import InvalidPortfolioError
from papertrade.domain.value_objects.performance_metrics import PerformanceMetrics


class TestPerformanceMetricsConstruction:
    """Tests for PerformanceMetrics construction and validation."""

    def test_valid_construction(self) -> None:
        """Should create PerformanceMetrics with valid data."""
        metrics = PerformanceMetrics(
            period_start=date(2024, 1, 1),
            period_end=date(2024, 1, 31),
            starting_value=Decimal("10000.00"),
            ending_value=Decimal("12500.00"),
            absolute_gain=Decimal("2500.00"),
            percentage_gain=Decimal("25.00"),
            highest_value=Decimal("12750.00"),
            lowest_value=Decimal("9800.00"),
        )

        assert metrics.period_start == date(2024, 1, 1)
        assert metrics.period_end == date(2024, 1, 31)
        assert metrics.starting_value == Decimal("10000.00")
        assert metrics.ending_value == Decimal("12500.00")
        assert metrics.absolute_gain == Decimal("2500.00")
        assert metrics.percentage_gain == Decimal("25.00")
        assert metrics.highest_value == Decimal("12750.00")
        assert metrics.lowest_value == Decimal("9800.00")

    def test_invalid_period_end_before_start(self) -> None:
        """Should reject period_end before period_start."""
        with pytest.raises(
            InvalidPortfolioError, match="period_end must be >= period_start"
        ):
            PerformanceMetrics(
                period_start=date(2024, 1, 31),
                period_end=date(2024, 1, 1),  # Before start
                starting_value=Decimal("10000.00"),
                ending_value=Decimal("12500.00"),
                absolute_gain=Decimal("2500.00"),
                percentage_gain=Decimal("25.00"),
                highest_value=Decimal("12500.00"),
                lowest_value=Decimal("10000.00"),
            )

    def test_invalid_absolute_gain_mismatch(self) -> None:
        """Should reject absolute_gain that doesn't match ending - starting."""
        with pytest.raises(InvalidPortfolioError, match="absolute_gain must equal"):
            PerformanceMetrics(
                period_start=date(2024, 1, 1),
                period_end=date(2024, 1, 31),
                starting_value=Decimal("10000.00"),
                ending_value=Decimal("12500.00"),
                absolute_gain=Decimal("3000.00"),  # Should be 2500
                percentage_gain=Decimal("25.00"),
                highest_value=Decimal("12500.00"),
                lowest_value=Decimal("10000.00"),
            )

    def test_invalid_highest_value_too_low(self) -> None:
        """Should reject highest_value below starting or ending value."""
        # highest_value < starting_value
        with pytest.raises(
            InvalidPortfolioError,
            match="highest_value must be >= starting_value",
        ):
            PerformanceMetrics(
                period_start=date(2024, 1, 1),
                period_end=date(2024, 1, 31),
                starting_value=Decimal("10000.00"),
                ending_value=Decimal("12500.00"),
                absolute_gain=Decimal("2500.00"),
                percentage_gain=Decimal("25.00"),
                highest_value=Decimal("9000.00"),  # Too low
                lowest_value=Decimal("9000.00"),
            )

        # highest_value < ending_value
        with pytest.raises(
            InvalidPortfolioError,
            match="highest_value must be >= ending_value",
        ):
            PerformanceMetrics(
                period_start=date(2024, 1, 1),
                period_end=date(2024, 1, 31),
                starting_value=Decimal("10000.00"),
                ending_value=Decimal("12500.00"),
                absolute_gain=Decimal("2500.00"),
                percentage_gain=Decimal("25.00"),
                highest_value=Decimal("12000.00"),  # Below ending
                lowest_value=Decimal("10000.00"),
            )

    def test_invalid_lowest_value_too_high(self) -> None:
        """Should reject lowest_value above starting or ending value."""
        # lowest_value > starting_value
        with pytest.raises(
            InvalidPortfolioError,
            match="lowest_value must be <= starting_value",
        ):
            PerformanceMetrics(
                period_start=date(2024, 1, 1),
                period_end=date(2024, 1, 31),
                starting_value=Decimal("10000.00"),
                ending_value=Decimal("12500.00"),
                absolute_gain=Decimal("2500.00"),
                percentage_gain=Decimal("25.00"),
                highest_value=Decimal("12500.00"),
                lowest_value=Decimal("11000.00"),  # Too high
            )

        # lowest_value > ending_value
        # (with starting_value > ending_value to trigger ending check)
        with pytest.raises(
            InvalidPortfolioError,
            match="lowest_value must be <= ending_value",
        ):
            PerformanceMetrics(
                period_start=date(2024, 1, 1),
                period_end=date(2024, 1, 31),
                starting_value=Decimal("12500.00"),
                ending_value=Decimal("10000.00"),
                absolute_gain=Decimal("-2500.00"),
                percentage_gain=Decimal("-20.00"),
                highest_value=Decimal("12500.00"),
                lowest_value=Decimal("11000.00"),  # Above ending but below starting
            )


class TestPerformanceMetricsCalculation:
    """Tests for calculating metrics from snapshots."""

    def test_calculate_metrics_from_snapshots(self) -> None:
        """Should calculate correct metrics from multiple snapshots."""
        portfolio_id = uuid4()

        snapshots = [
            PortfolioSnapshot.create(
                portfolio_id=portfolio_id,
                snapshot_date=date(2024, 1, 1),
                cash_balance=Decimal("10000.00"),
                holdings_value=Decimal("0.00"),
                holdings_count=0,
            ),
            PortfolioSnapshot.create(
                portfolio_id=portfolio_id,
                snapshot_date=date(2024, 1, 15),
                cash_balance=Decimal("5000.00"),
                holdings_value=Decimal("6000.00"),
                holdings_count=2,
            ),
            PortfolioSnapshot.create(
                portfolio_id=portfolio_id,
                snapshot_date=date(2024, 1, 31),
                cash_balance=Decimal("5000.00"),
                holdings_value=Decimal("7500.00"),
                holdings_count=2,
            ),
        ]

        metrics = PerformanceMetrics.calculate(snapshots)

        assert metrics.period_start == date(2024, 1, 1)
        assert metrics.period_end == date(2024, 1, 31)
        assert metrics.starting_value == Decimal("10000.00")
        assert metrics.ending_value == Decimal("12500.00")
        assert metrics.absolute_gain == Decimal("2500.00")
        assert metrics.percentage_gain == Decimal("25.00")
        assert metrics.highest_value == Decimal("12500.00")
        assert metrics.lowest_value == Decimal("10000.00")

    def test_calculate_metrics_positive_gain(self) -> None:
        """Should calculate positive gain correctly."""
        portfolio_id = uuid4()

        snapshots = [
            PortfolioSnapshot.create(
                portfolio_id=portfolio_id,
                snapshot_date=date(2024, 1, 1),
                cash_balance=Decimal("5000.00"),
                holdings_value=Decimal("5000.00"),
                holdings_count=1,
            ),
            PortfolioSnapshot.create(
                portfolio_id=portfolio_id,
                snapshot_date=date(2024, 1, 31),
                cash_balance=Decimal("5000.00"),
                holdings_value=Decimal("6000.00"),
                holdings_count=1,
            ),
        ]

        metrics = PerformanceMetrics.calculate(snapshots)

        assert metrics.absolute_gain == Decimal("1000.00")
        assert metrics.percentage_gain == Decimal("10.00")

    def test_calculate_metrics_negative_gain(self) -> None:
        """Should calculate negative gain (loss) correctly."""
        portfolio_id = uuid4()

        snapshots = [
            PortfolioSnapshot.create(
                portfolio_id=portfolio_id,
                snapshot_date=date(2024, 1, 1),
                cash_balance=Decimal("10000.00"),
                holdings_value=Decimal("0.00"),
                holdings_count=0,
            ),
            PortfolioSnapshot.create(
                portfolio_id=portfolio_id,
                snapshot_date=date(2024, 1, 31),
                cash_balance=Decimal("5000.00"),
                holdings_value=Decimal("3000.00"),
                holdings_count=1,
            ),
        ]

        metrics = PerformanceMetrics.calculate(snapshots)

        assert metrics.absolute_gain == Decimal("-2000.00")
        assert metrics.percentage_gain == Decimal("-20.00")

    def test_calculate_metrics_empty_snapshots_raises(self) -> None:
        """Should raise error when calculating from empty snapshots."""
        with pytest.raises(
            InvalidPortfolioError, match="Cannot calculate metrics from empty"
        ):
            PerformanceMetrics.calculate([])

    def test_calculate_metrics_single_snapshot(self) -> None:
        """Should handle single snapshot (no change)."""
        portfolio_id = uuid4()

        snapshots = [
            PortfolioSnapshot.create(
                portfolio_id=portfolio_id,
                snapshot_date=date(2024, 1, 1),
                cash_balance=Decimal("10000.00"),
                holdings_value=Decimal("0.00"),
                holdings_count=0,
            ),
        ]

        metrics = PerformanceMetrics.calculate(snapshots)

        assert metrics.period_start == date(2024, 1, 1)
        assert metrics.period_end == date(2024, 1, 1)
        assert metrics.starting_value == Decimal("10000.00")
        assert metrics.ending_value == Decimal("10000.00")
        assert metrics.absolute_gain == Decimal("0.00")
        assert metrics.percentage_gain == Decimal("0.00")
        assert metrics.highest_value == Decimal("10000.00")
        assert metrics.lowest_value == Decimal("10000.00")

    def test_highest_lowest_values(self) -> None:
        """Should correctly identify highest and lowest values in period."""
        portfolio_id = uuid4()

        snapshots = [
            PortfolioSnapshot.create(
                portfolio_id=portfolio_id,
                snapshot_date=date(2024, 1, 1),
                cash_balance=Decimal("10000.00"),
                holdings_value=Decimal("0.00"),
                holdings_count=0,
            ),
            PortfolioSnapshot.create(
                portfolio_id=portfolio_id,
                snapshot_date=date(2024, 1, 10),
                cash_balance=Decimal("5000.00"),
                holdings_value=Decimal("10000.00"),  # Peak
                holdings_count=2,
            ),
            PortfolioSnapshot.create(
                portfolio_id=portfolio_id,
                snapshot_date=date(2024, 1, 20),
                cash_balance=Decimal("5000.00"),
                holdings_value=Decimal("3000.00"),  # Trough
                holdings_count=2,
            ),
            PortfolioSnapshot.create(
                portfolio_id=portfolio_id,
                snapshot_date=date(2024, 1, 31),
                cash_balance=Decimal("5000.00"),
                holdings_value=Decimal("5000.00"),
                holdings_count=2,
            ),
        ]

        metrics = PerformanceMetrics.calculate(snapshots)

        assert metrics.highest_value == Decimal("15000.00")  # Jan 10
        assert metrics.lowest_value == Decimal("8000.00")  # Jan 20

    def test_percentage_gain_calculation(self) -> None:
        """Should calculate percentage gain with correct precision."""
        portfolio_id = uuid4()

        snapshots = [
            PortfolioSnapshot.create(
                portfolio_id=portfolio_id,
                snapshot_date=date(2024, 1, 1),
                cash_balance=Decimal("10000.00"),
                holdings_value=Decimal("0.00"),
                holdings_count=0,
            ),
            PortfolioSnapshot.create(
                portfolio_id=portfolio_id,
                snapshot_date=date(2024, 1, 31),
                cash_balance=Decimal("5000.00"),
                holdings_value=Decimal("5333.33"),
                holdings_count=1,
            ),
        ]

        metrics = PerformanceMetrics.calculate(snapshots)

        # (10333.33 / 10000 - 1) * 100 = 3.3333...
        # Should be rounded to 2 decimal places
        assert metrics.percentage_gain == Decimal("3.33")

    def test_percentage_gain_with_zero_starting_value(self) -> None:
        """Should handle zero starting value gracefully."""
        portfolio_id = uuid4()

        snapshots = [
            PortfolioSnapshot.create(
                portfolio_id=portfolio_id,
                snapshot_date=date(2024, 1, 1),
                cash_balance=Decimal("0.00"),
                holdings_value=Decimal("0.00"),
                holdings_count=0,
            ),
            PortfolioSnapshot.create(
                portfolio_id=portfolio_id,
                snapshot_date=date(2024, 1, 31),
                cash_balance=Decimal("10000.00"),
                holdings_value=Decimal("0.00"),
                holdings_count=0,
            ),
        ]

        metrics = PerformanceMetrics.calculate(snapshots)

        # Cannot divide by zero, should default to 0%
        assert metrics.percentage_gain == Decimal("0.00")

    def test_calculate_with_unsorted_snapshots(self) -> None:
        """Should handle snapshots in any order."""
        portfolio_id = uuid4()

        # Create snapshots out of order
        snapshots = [
            PortfolioSnapshot.create(
                portfolio_id=portfolio_id,
                snapshot_date=date(2024, 1, 31),  # Last
                cash_balance=Decimal("12500.00"),
                holdings_value=Decimal("0.00"),
                holdings_count=0,
            ),
            PortfolioSnapshot.create(
                portfolio_id=portfolio_id,
                snapshot_date=date(2024, 1, 1),  # First
                cash_balance=Decimal("10000.00"),
                holdings_value=Decimal("0.00"),
                holdings_count=0,
            ),
            PortfolioSnapshot.create(
                portfolio_id=portfolio_id,
                snapshot_date=date(2024, 1, 15),  # Middle
                cash_balance=Decimal("11000.00"),
                holdings_value=Decimal("0.00"),
                holdings_count=0,
            ),
        ]

        metrics = PerformanceMetrics.calculate(snapshots)

        # Should correctly identify first and last by date, not list order
        assert metrics.period_start == date(2024, 1, 1)
        assert metrics.period_end == date(2024, 1, 31)
        assert metrics.starting_value == Decimal("10000.00")
        assert metrics.ending_value == Decimal("12500.00")


class TestPerformanceMetricsRepresentation:
    """Tests for PerformanceMetrics string representation."""

    def test_repr(self) -> None:
        """Should have meaningful repr for debugging."""
        metrics = PerformanceMetrics(
            period_start=date(2024, 1, 1),
            period_end=date(2024, 1, 31),
            starting_value=Decimal("10000.00"),
            ending_value=Decimal("12500.00"),
            absolute_gain=Decimal("2500.00"),
            percentage_gain=Decimal("25.00"),
            highest_value=Decimal("12500.00"),
            lowest_value=Decimal("10000.00"),
        )

        repr_str = repr(metrics)
        assert "PerformanceMetrics" in repr_str
        assert "2024-01-01" in repr_str
        assert "2024-01-31" in repr_str
        assert "25.00" in repr_str
