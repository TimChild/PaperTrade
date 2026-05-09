"""TradeSignal value object - represents a buy/sell signal from a strategy."""

from dataclasses import dataclass
from datetime import date
from enum import Enum

from zebu.domain.exceptions import InvalidTradeSignalError
from zebu.domain.value_objects.money import Money
from zebu.domain.value_objects.quantity import Quantity
from zebu.domain.value_objects.ticker import Ticker


class TradeAction(Enum):
    """Direction of a trade signal."""

    BUY = "BUY"
    SELL = "SELL"


@dataclass(frozen=True)
class TradeSignal:
    """Represents a buy or sell signal produced by a trading strategy.

    Exactly one of ``quantity`` (shares) or ``amount`` (Money) must be set —
    the "exactly one" invariant is enforced in ``__post_init__``.

    Attributes:
        action: Whether to buy or sell
        ticker: Stock ticker (Ticker value object)
        signal_date: Date on which the signal is generated
        quantity: Number of shares to trade (mutually exclusive with amount)
        amount: Monetary value to trade (mutually exclusive with quantity)

    Raises:
        InvalidTradeSignalError: If both or neither of quantity/amount are set,
            or if either value is non-positive.
    """

    action: TradeAction
    ticker: Ticker
    signal_date: date
    quantity: Quantity | None = None
    amount: Money | None = None

    def __post_init__(self) -> None:
        """Validate TradeSignal invariants after initialization."""
        if (self.quantity is None) == (self.amount is None):
            raise InvalidTradeSignalError(
                "Exactly one of quantity or amount must be set"
            )
        if self.quantity is not None and not self.quantity.is_positive():
            raise InvalidTradeSignalError("quantity must be positive")
        if self.amount is not None and not self.amount.is_positive():
            raise InvalidTradeSignalError("amount must be positive")
