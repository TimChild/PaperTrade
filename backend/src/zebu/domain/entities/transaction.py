"""Transaction entity - Immutable ledger entry for portfolio state changes."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from uuid import UUID

from zebu.domain.exceptions import InvalidTransactionError
from zebu.domain.value_objects.money import Money
from zebu.domain.value_objects.quantity import Quantity
from zebu.domain.value_objects.ticker import Ticker


class TransactionType(Enum):
    """Types of transactions in the portfolio ledger."""

    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"
    BUY = "BUY"
    SELL = "SELL"


@dataclass(frozen=True)
class Transaction:
    """Represents a single immutable entry in the portfolio ledger.

    Transaction records all state changes (deposits, withdrawals, trades).
    Once created, transactions are completely immutable to maintain audit integrity.

    Attributes:
        id: Unique transaction identifier
        portfolio_id: Portfolio this transaction belongs to
        transaction_type: Type of transaction (DEPOSIT, WITHDRAWAL, BUY, SELL)
        timestamp: When transaction occurred (UTC timezone)
        cash_change: Change in cash balance (can be positive or negative)
        ticker: Stock symbol (required for BUY/SELL, None otherwise)
        quantity: Number of shares (required for BUY/SELL, None otherwise)
        price_per_share: Share price at execution (required for BUY/SELL,
            None otherwise)
        notes: Optional description (max 500 characters)

    Raises:
        InvalidTransactionError: If type-specific invariants are violated
    """

    id: UUID
    portfolio_id: UUID
    transaction_type: TransactionType
    timestamp: datetime
    cash_change: Money
    ticker: Ticker | None = None
    quantity: Quantity | None = None
    price_per_share: Money | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        """Validate Transaction type-specific invariants."""
        # Validate notes length if provided
        if self.notes is not None and len(self.notes) > 500:
            raise InvalidTransactionError(
                f"Notes must be maximum 500 characters, got {len(self.notes)}"
            )

        # Type-specific validation
        if self.transaction_type == TransactionType.DEPOSIT:
            self._validate_deposit()
        elif self.transaction_type == TransactionType.WITHDRAWAL:
            self._validate_withdrawal()
        elif self.transaction_type == TransactionType.BUY:
            self._validate_buy()
        elif self.transaction_type == TransactionType.SELL:
            self._validate_sell()

    def _validate_deposit(self) -> None:
        """Validate DEPOSIT transaction constraints."""
        # Must have positive cash_change
        if not self.cash_change.is_positive():
            raise InvalidTransactionError(
                "DEPOSIT transaction must have positive cash_change"
            )

        # Must not have ticker, quantity, or price
        if (
            self.ticker is not None
            or self.quantity is not None
            or self.price_per_share is not None
        ):
            raise InvalidTransactionError(
                "DEPOSIT transaction must not have ticker, quantity, or price_per_share"
            )

    def _validate_withdrawal(self) -> None:
        """Validate WITHDRAWAL transaction constraints."""
        # Must have negative cash_change
        if not self.cash_change.is_negative():
            raise InvalidTransactionError(
                "WITHDRAWAL transaction must have negative cash_change"
            )

        # Must not have ticker, quantity, or price
        if (
            self.ticker is not None
            or self.quantity is not None
            or self.price_per_share is not None
        ):
            raise InvalidTransactionError(
                "WITHDRAWAL transaction must not have ticker, quantity, "
                "or price_per_share"
            )

    def _validate_buy(self) -> None:
        """Validate BUY transaction constraints."""
        # Must have ticker, quantity, and price
        if self.ticker is None:
            raise InvalidTransactionError("BUY transaction must have ticker")
        if self.quantity is None:
            raise InvalidTransactionError("BUY transaction must have quantity")
        if self.price_per_share is None:
            raise InvalidTransactionError("BUY transaction must have price_per_share")

        # Must have negative cash_change (money leaving)
        if not self.cash_change.is_negative():
            raise InvalidTransactionError(
                "BUY transaction must have negative cash_change (money leaving)"
            )

        # Verify cash_change = -(quantity × price)
        expected_cash_change = Money(
            -(self.quantity.shares * self.price_per_share.amount),
            self.cash_change.currency,
        )
        if self.cash_change != expected_cash_change:
            raise InvalidTransactionError(
                f"BUY transaction cash_change must equal "
                f"-(quantity × price_per_share). "
                f"Expected {expected_cash_change}, got {self.cash_change}"
            )

    def _validate_sell(self) -> None:
        """Validate SELL transaction constraints."""
        # Must have ticker, quantity, and price
        if self.ticker is None:
            raise InvalidTransactionError("SELL transaction must have ticker")
        if self.quantity is None:
            raise InvalidTransactionError("SELL transaction must have quantity")
        if self.price_per_share is None:
            raise InvalidTransactionError("SELL transaction must have price_per_share")

        # Must have positive cash_change (money coming in)
        if not self.cash_change.is_positive():
            raise InvalidTransactionError(
                "SELL transaction must have positive cash_change (money coming in)"
            )

        # Verify cash_change = (quantity × price)
        expected_cash_change = Money(
            self.quantity.shares * self.price_per_share.amount,
            self.cash_change.currency,
        )
        if self.cash_change != expected_cash_change:
            raise InvalidTransactionError(
                f"SELL transaction cash_change must equal "
                f"(quantity × price_per_share). "
                f"Expected {expected_cash_change}, got {self.cash_change}"
            )

    def __eq__(self, other: object) -> bool:
        """Equality based on ID only.

        Args:
            other: Object to compare

        Returns:
            True if other is Transaction with same ID
        """
        if not isinstance(other, Transaction):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        """Hash based on ID for use in dicts/sets.

        Returns:
            Hash of transaction ID
        """
        return hash(self.id)

    def __lt__(self, other: "Transaction") -> bool:
        """Compare transactions by timestamp for sorting.

        Args:
            other: Transaction to compare

        Returns:
            True if self.timestamp < other.timestamp
        """
        return self.timestamp < other.timestamp

    def __repr__(self) -> str:
        """Return repr for debugging.

        Returns:
            String with transaction details
        """
        base = f"Transaction(id={self.id}, type={self.transaction_type.value}"
        if self.ticker:
            base += (
                f", ticker={self.ticker.symbol}, quantity={self.quantity}, "
                f"price={self.price_per_share}"
            )
        base += f", cash_change={self.cash_change})"
        return base
