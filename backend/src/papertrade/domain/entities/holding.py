"""Holding entity - Represents a position in a specific asset."""

from __future__ import annotations

from dataclasses import dataclass

from papertrade.domain.value_objects import Money, Quantity, Ticker


@dataclass(frozen=True)
class Holding:
    """Immutable derived/computed entity representing a position in a stock.

    Holdings are computed from transaction history and represent
    the current position in a specific ticker.
    """

    ticker: Ticker
    quantity: Quantity
    average_cost: Money

    @property
    def total_cost(self) -> Money:
        """Calculate the total cost basis for this holding.

        Returns:
            Money representing the total amount paid for all shares.
        """
        # Multiply average cost by quantity
        return self.average_cost * self.quantity.value

    def __str__(self) -> str:
        """String representation."""
        return (
            f"{self.quantity} shares of {self.ticker} "
            f"(avg cost: {self.average_cost}, total: {self.total_cost})"
        )

    def __repr__(self) -> str:
        """Developer-friendly representation."""
        return (
            f"Holding(ticker={self.ticker!r}, quantity={self.quantity!r}, "
            f"average_cost={self.average_cost!r})"
        )
