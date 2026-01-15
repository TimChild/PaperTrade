"""Holding DTO for transferring holding data across layers."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from zebu.domain.entities.holding import Holding


@dataclass(frozen=True)
class HoldingDTO:
    """Data transfer object for Holding entity.

    Provides a flat, serialization-friendly representation of a stock position,
    converting value objects to primitive types for API responses.

    Attributes:
        ticker_symbol: Stock symbol (e.g., "AAPL")
        quantity_shares: Number of shares held
        cost_basis_amount: Total cost paid for shares
        cost_basis_currency: Currency code (e.g., "USD")
        average_cost_per_share_amount: Average cost per share (None if zero)
        average_cost_per_share_currency: Currency for average cost (None if zero)
        current_price_amount: Current market price per share (None if unavailable)
        current_price_currency: Currency for current price (None if unavailable)
        market_value_amount: Current market value (quantity * current_price,
            None if unavailable)
        market_value_currency: Currency for market value (None if unavailable)
        unrealized_gain_loss_amount: Unrealized gain/loss
            (market_value - cost_basis, None if unavailable)
        unrealized_gain_loss_currency: Currency for gain/loss (None if unavailable)
        unrealized_gain_loss_percent: Gain/loss as percentage (None if unavailable)
        price_timestamp: When price was observed (None if unavailable)
        price_source: Data source for price (None if unavailable)
    """

    ticker_symbol: str
    quantity_shares: Decimal
    cost_basis_amount: Decimal
    cost_basis_currency: str
    average_cost_per_share_amount: Decimal | None = None
    average_cost_per_share_currency: str | None = None
    # Market data fields (None if price unavailable)
    current_price_amount: Decimal | None = None
    current_price_currency: str | None = None
    market_value_amount: Decimal | None = None
    market_value_currency: str | None = None
    unrealized_gain_loss_amount: Decimal | None = None
    unrealized_gain_loss_currency: str | None = None
    unrealized_gain_loss_percent: Decimal | None = None
    price_timestamp: datetime | None = None
    price_source: str | None = None

    @staticmethod
    def from_entity(holding: Holding) -> "HoldingDTO":
        """Convert a Holding entity to DTO.

        Args:
            holding: Domain Holding entity

        Returns:
            HoldingDTO with value objects converted to primitives
        """
        avg_cost = holding.average_cost_per_share
        return HoldingDTO(
            ticker_symbol=holding.ticker.symbol,
            quantity_shares=holding.quantity.shares,
            cost_basis_amount=holding.cost_basis.amount,
            cost_basis_currency=holding.cost_basis.currency,
            average_cost_per_share_amount=avg_cost.amount
            if avg_cost is not None
            else None,
            average_cost_per_share_currency=(
                avg_cost.currency if avg_cost is not None else None
            ),
        )
