"""SnapshotCalculator service - Calculate portfolio snapshots from portfolio state."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from papertrade.domain.entities.portfolio_snapshot import PortfolioSnapshot


class SnapshotCalculator:
    """Service for calculating portfolio snapshots.

    This is a pure domain service with no I/O dependencies. It calculates
    snapshot data from the current state of a portfolio.

    All methods are static and side-effect free.
    """

    @staticmethod
    def calculate_snapshot(
        portfolio_id: UUID,
        snapshot_date: date,
        cash_balance: Decimal,
        holdings: list[tuple[str, int, Decimal]],
    ) -> PortfolioSnapshot:
        """Calculate a snapshot for the given portfolio state.

        Args:
            portfolio_id: Portfolio identifier
            snapshot_date: Date of the snapshot
            cash_balance: Available cash in portfolio
            holdings: List of (ticker, quantity, price_per_share) tuples

        Returns:
            PortfolioSnapshot with calculated values

        Example:
            >>> calculator = SnapshotCalculator()
            >>> holdings = [("AAPL", 10, Decimal("150.00")), ("IBM", 5, Decimal("180.00"))]
            >>> snapshot = calculator.calculate_snapshot(
            ...     portfolio_id=uuid4(),
            ...     snapshot_date=date.today(),
            ...     cash_balance=Decimal("5000.00"),
            ...     holdings=holdings,
            ... )
            >>> snapshot.total_value
            Decimal('7400.00')  # 5000 cash + 1500 AAPL + 900 IBM
        """
        # Calculate total value of all holdings
        holdings_value = sum(
            Decimal(quantity) * price for _, quantity, price in holdings
        )

        return PortfolioSnapshot.create(
            portfolio_id=portfolio_id,
            snapshot_date=snapshot_date,
            cash_balance=cash_balance,
            holdings_value=holdings_value,
            holdings_count=len(holdings),
        )
