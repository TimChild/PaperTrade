"""Transaction entity - Immutable ledger entry."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from uuid import UUID

from papertrade.domain.value_objects import Money, Quantity, Ticker


class TransactionType(Enum):
    """Type of transaction."""

    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    BUY = "buy"
    SELL = "sell"
    DIVIDEND = "dividend"
    FEE = "fee"


@dataclass(frozen=True)
class Transaction:
    """Immutable ledger entry representing a financial transaction.

    Transactions are the single source of truth for all portfolio activity.
    They are never modified or deleted once created.
    """

    id: UUID
    portfolio_id: UUID
    type: TransactionType
    amount: Money
    timestamp: datetime
    ticker: Ticker | None = None
    quantity: Quantity | None = None
    price_per_share: Money | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        """Validate transaction consistency."""
        # BUY and SELL transactions require ticker, quantity, and price_per_share
        if self.type in (TransactionType.BUY, TransactionType.SELL):
            if self.ticker is None:
                raise ValueError(f"{self.type.value} transaction requires a ticker")
            if self.quantity is None:
                raise ValueError(f"{self.type.value} transaction requires a quantity")
            if self.price_per_share is None:
                raise ValueError(
                    f"{self.type.value} transaction requires a price_per_share"
                )

        # DEPOSIT, WITHDRAWAL, DIVIDEND, and FEE should not have ticker,
        # quantity, or price_per_share
        if self.type in (
            TransactionType.DEPOSIT,
            TransactionType.WITHDRAWAL,
            TransactionType.DIVIDEND,
            TransactionType.FEE,
        ):
            if self.ticker is not None:
                raise ValueError(
                    f"{self.type.value} transaction should not have a ticker"
                )
            if self.quantity is not None:
                raise ValueError(
                    f"{self.type.value} transaction should not have a quantity"
                )
            if self.price_per_share is not None:
                raise ValueError(
                    f"{self.type.value} transaction should not have a price_per_share"
                )

        # Amount should always be positive (type determines direction)
        if self.amount.amount <= 0:
            raise ValueError("Transaction amount must be positive")

    def __str__(self) -> str:
        """String representation."""
        if self.type in (TransactionType.BUY, TransactionType.SELL):
            return (
                f"{self.type.value.upper()}: {self.quantity} shares of {self.ticker} "
                f"@ {self.price_per_share} = {self.amount}"
            )
        return f"{self.type.value.upper()}: {self.amount}"

    def __repr__(self) -> str:
        """Developer-friendly representation."""
        return (
            f"Transaction(id={self.id}, portfolio_id={self.portfolio_id}, "
            f"type={self.type}, amount={self.amount}, ticker={self.ticker}, "
            f"quantity={self.quantity}, price_per_share={self.price_per_share}, "
            f"timestamp={self.timestamp})"
        )
