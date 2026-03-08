"""SnapshotCalculator service - Calculate portfolio snapshots from portfolio state."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from zebu.domain.entities.portfolio_snapshot import HoldingBreakdown, PortfolioSnapshot


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
            PortfolioSnapshot with calculated values and per-holding breakdown

        Example:
            >>> holdings = [
            ...     ("AAPL", 10, Decimal("150.00")),
            ...     ("IBM", 5, Decimal("180.00"))
            ... ]
            >>> snapshot = SnapshotCalculator.calculate_snapshot(
            ...     portfolio_id=uuid4(),
            ...     snapshot_date=date.today(),
            ...     cash_balance=Decimal("5000.00"),
            ...     holdings=holdings,
            ... )
            >>> snapshot.total_value
            Decimal('7400.00')  # 5000 cash + 1500 AAPL + 900 IBM
        """
        # Build per-holding breakdown objects
        holdings_breakdown: list[HoldingBreakdown] = [
            HoldingBreakdown(
                ticker=ticker,
                quantity=quantity,
                price_per_share=price,
                value=Decimal(quantity) * price,
            )
            for ticker, quantity, price in holdings
        ]

        # Calculate total value of all holdings
        holdings_value = sum(h.value for h in holdings_breakdown)

        return PortfolioSnapshot.create(
            portfolio_id=portfolio_id,
            snapshot_date=snapshot_date,
            cash_balance=cash_balance,
            holdings_value=holdings_value if holdings_value else Decimal("0"),
            holdings_count=len(holdings),
            holdings_breakdown=holdings_breakdown,
        )
