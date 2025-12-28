"""Holding entity - Derived entity representing current stock position."""

from dataclasses import dataclass
from decimal import Decimal

from papertrade.domain.value_objects.money import Money
from papertrade.domain.value_objects.quantity import Quantity
from papertrade.domain.value_objects.ticker import Ticker


@dataclass(frozen=True)
class Holding:
    """Represents the current position in a specific stock within a portfolio.

    Holding is a **derived entity** - it is calculated from transactions, not stored
    in the database. Holdings represent aggregated buy/sell activity for a ticker.

    Attributes:
        ticker: Stock symbol
        quantity: Current number of shares held (non-negative)
        cost_basis: Total amount paid for shares (non-negative)

    Note:
        This entity is derived from transaction history and should not be persisted
        directly. Use PortfolioCalculator.calculate_holdings() to create Holdings.
    """

    ticker: Ticker
    quantity: Quantity
    cost_basis: Money

    @property
    def average_cost_per_share(self) -> Money | None:
        """Calculate average cost per share.

        Returns:
            Cost basis divided by quantity, or None if quantity is zero
        """
        if self.quantity.is_zero():
            return None

        # Calculate: cost_basis / quantity
        avg_amount = self.cost_basis.amount / self.quantity.shares
        # Round to 2 decimal places
        rounded = avg_amount.quantize(Decimal("0.01"))
        return Money(rounded, self.cost_basis.currency)

    def __eq__(self, other: object) -> bool:
        """Equality based on ticker only (one holding per ticker per portfolio).

        Args:
            other: Object to compare

        Returns:
            True if other is Holding with same ticker
        """
        if not isinstance(other, Holding):
            return False
        return self.ticker == other.ticker

    def __hash__(self) -> int:
        """Hash based on ticker for use in dicts/sets.

        Returns:
            Hash of ticker
        """
        return hash(self.ticker)

    def __repr__(self) -> str:
        """Return repr for debugging.

        Returns:
            String like "Holding(ticker=AAPL, quantity=10.0000, cost_basis=$1,500.00)"
        """
        return (
            f"Holding(ticker={self.ticker.symbol}, "
            f"quantity={self.quantity.shares}, "
            f"cost_basis={self.cost_basis})"
        )
