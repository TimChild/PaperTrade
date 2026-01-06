"""Tests for SnapshotCalculator service."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

from papertrade.domain.services.snapshot_calculator import SnapshotCalculator


class TestSnapshotCalculator:
    """Tests for SnapshotCalculator service."""

    def test_calculate_snapshot_cash_only(self) -> None:
        """Should calculate snapshot with only cash, no holdings."""
        portfolio_id = uuid4()
        snapshot_date = date.today()
        cash_balance = Decimal("10000.00")
        holdings: list[tuple[str, int, Decimal]] = []

        snapshot = SnapshotCalculator.calculate_snapshot(
            portfolio_id=portfolio_id,
            snapshot_date=snapshot_date,
            cash_balance=cash_balance,
            holdings=holdings,
        )

        assert snapshot.portfolio_id == portfolio_id
        assert snapshot.snapshot_date == snapshot_date
        assert snapshot.cash_balance == Decimal("10000.00")
        assert snapshot.holdings_value == Decimal("0.00")
        assert snapshot.total_value == Decimal("10000.00")
        assert snapshot.holdings_count == 0

    def test_calculate_snapshot_with_multiple_holdings(self) -> None:
        """Should calculate snapshot with multiple stock holdings."""
        portfolio_id = uuid4()
        snapshot_date = date.today()
        cash_balance = Decimal("5000.00")

        holdings = [
            ("AAPL", 10, Decimal("150.00")),  # $1,500
            ("IBM", 5, Decimal("180.00")),    # $900
            ("MSFT", 8, Decimal("250.00")),   # $2,000
        ]

        snapshot = SnapshotCalculator.calculate_snapshot(
            portfolio_id=portfolio_id,
            snapshot_date=snapshot_date,
            cash_balance=cash_balance,
            holdings=holdings,
        )

        assert snapshot.cash_balance == Decimal("5000.00")
        assert snapshot.holdings_value == Decimal("4400.00")  # 1500 + 900 + 2000
        assert snapshot.total_value == Decimal("9400.00")  # 5000 + 4400
        assert snapshot.holdings_count == 3

    def test_calculate_snapshot_empty_holdings(self) -> None:
        """Should handle empty holdings list (all sold scenario)."""
        portfolio_id = uuid4()
        snapshot_date = date.today()
        cash_balance = Decimal("15000.00")

        snapshot = SnapshotCalculator.calculate_snapshot(
            portfolio_id=portfolio_id,
            snapshot_date=snapshot_date,
            cash_balance=cash_balance,
            holdings=[],
        )

        assert snapshot.cash_balance == Decimal("15000.00")
        assert snapshot.holdings_value == Decimal("0.00")
        assert snapshot.total_value == Decimal("15000.00")
        assert snapshot.holdings_count == 0

    def test_calculate_snapshot_single_holding(self) -> None:
        """Should calculate snapshot with single holding."""
        portfolio_id = uuid4()
        snapshot_date = date.today()
        cash_balance = Decimal("8000.00")

        holdings = [
            ("AAPL", 20, Decimal("175.50")),  # $3,510
        ]

        snapshot = SnapshotCalculator.calculate_snapshot(
            portfolio_id=portfolio_id,
            snapshot_date=snapshot_date,
            cash_balance=cash_balance,
            holdings=holdings,
        )

        assert snapshot.cash_balance == Decimal("8000.00")
        assert snapshot.holdings_value == Decimal("3510.00")
        assert snapshot.total_value == Decimal("11510.00")
        assert snapshot.holdings_count == 1

    def test_calculate_snapshot_with_fractional_prices(self) -> None:
        """Should handle holdings with fractional prices correctly."""
        portfolio_id = uuid4()
        snapshot_date = date.today()
        cash_balance = Decimal("1000.00")

        holdings = [
            ("AAPL", 7, Decimal("123.45")),   # $864.15
            ("GOOGL", 3, Decimal("2567.89")), # $7,703.67
        ]

        snapshot = SnapshotCalculator.calculate_snapshot(
            portfolio_id=portfolio_id,
            snapshot_date=snapshot_date,
            cash_balance=cash_balance,
            holdings=holdings,
        )

        expected_holdings_value = Decimal("864.15") + Decimal("7703.67")
        assert snapshot.holdings_value == expected_holdings_value
        assert snapshot.total_value == cash_balance + expected_holdings_value
        assert snapshot.holdings_count == 2

    def test_calculate_snapshot_with_zero_cash(self) -> None:
        """Should handle zero cash balance (fully invested)."""
        portfolio_id = uuid4()
        snapshot_date = date.today()
        cash_balance = Decimal("0.00")

        holdings = [
            ("AAPL", 10, Decimal("150.00")),  # $1,500
        ]

        snapshot = SnapshotCalculator.calculate_snapshot(
            portfolio_id=portfolio_id,
            snapshot_date=snapshot_date,
            cash_balance=cash_balance,
            holdings=holdings,
        )

        assert snapshot.cash_balance == Decimal("0.00")
        assert snapshot.holdings_value == Decimal("1500.00")
        assert snapshot.total_value == Decimal("1500.00")

    def test_calculate_snapshot_large_quantities(self) -> None:
        """Should handle large quantities correctly."""
        portfolio_id = uuid4()
        snapshot_date = date.today()
        cash_balance = Decimal("50000.00")

        holdings = [
            ("PENNY", 10000, Decimal("0.50")),  # $5,000
            ("IBM", 500, Decimal("180.00")),    # $90,000
        ]

        snapshot = SnapshotCalculator.calculate_snapshot(
            portfolio_id=portfolio_id,
            snapshot_date=snapshot_date,
            cash_balance=cash_balance,
            holdings=holdings,
        )

        assert snapshot.holdings_value == Decimal("95000.00")
        assert snapshot.total_value == Decimal("145000.00")
        assert snapshot.holdings_count == 2

    def test_calculate_snapshot_preserves_portfolio_id(self) -> None:
        """Should preserve portfolio_id in created snapshot."""
        portfolio_id = uuid4()
        snapshot_date = date.today()

        snapshot = SnapshotCalculator.calculate_snapshot(
            portfolio_id=portfolio_id,
            snapshot_date=snapshot_date,
            cash_balance=Decimal("10000.00"),
            holdings=[],
        )

        assert snapshot.portfolio_id == portfolio_id

    def test_calculate_snapshot_preserves_snapshot_date(self) -> None:
        """Should preserve snapshot_date in created snapshot."""
        portfolio_id = uuid4()
        snapshot_date = date(2024, 1, 15)

        snapshot = SnapshotCalculator.calculate_snapshot(
            portfolio_id=portfolio_id,
            snapshot_date=snapshot_date,
            cash_balance=Decimal("10000.00"),
            holdings=[],
        )

        assert snapshot.snapshot_date == snapshot_date

    def test_calculate_snapshot_generates_unique_ids(self) -> None:
        """Should generate unique IDs for different snapshots."""
        portfolio_id = uuid4()
        snapshot_date = date.today()
        cash_balance = Decimal("10000.00")

        snapshot1 = SnapshotCalculator.calculate_snapshot(
            portfolio_id=portfolio_id,
            snapshot_date=snapshot_date,
            cash_balance=cash_balance,
            holdings=[],
        )

        snapshot2 = SnapshotCalculator.calculate_snapshot(
            portfolio_id=portfolio_id,
            snapshot_date=snapshot_date,
            cash_balance=cash_balance,
            holdings=[],
        )

        # Different snapshots should have different IDs
        assert snapshot1.id != snapshot2.id
