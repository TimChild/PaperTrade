"""TradeSignal value object - represents a buy/sell signal from a strategy."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import Enum


class TradeAction(Enum):
    """Direction of a trade signal."""

    BUY = "BUY"
    SELL = "SELL"


@dataclass(frozen=True)
class TradeSignal:
    """Represents a buy or sell signal produced by a trading strategy.

    Exactly one of ``quantity`` (shares) or ``amount`` (USD) must be set.

    Attributes:
        action: Whether to buy or sell
        ticker: Stock ticker symbol
        signal_date: Date on which the signal is generated
        quantity: Number of shares to trade (mutually exclusive with amount)
        amount: USD value to trade (mutually exclusive with quantity)

    Raises:
        ValueError: If both or neither of quantity/amount are set, or if either
            value is non-positive.
    """

    action: TradeAction
    ticker: str
    signal_date: date
    quantity: Decimal | None = None
    amount: Decimal | None = None

    def __post_init__(self) -> None:
        """Validate TradeSignal invariants after initialization."""
        if (self.quantity is None) == (self.amount is None):
            raise ValueError("Exactly one of quantity or amount must be set")
        if self.quantity is not None and self.quantity <= 0:
            raise ValueError("quantity must be positive")
        if self.amount is not None and self.amount <= 0:
            raise ValueError("amount must be positive")
