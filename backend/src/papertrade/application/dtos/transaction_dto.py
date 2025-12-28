"""Transaction DTO for transferring transaction data across layers."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from papertrade.domain.entities.transaction import Transaction


@dataclass(frozen=True)
class TransactionDTO:
    """Data transfer object for Transaction entity.

    Provides a flat, serialization-friendly representation of a Transaction,
    converting value objects to primitive types for API responses.

    Attributes:
        id: Unique transaction identifier
        portfolio_id: Portfolio this transaction belongs to
        transaction_type: Type (DEPOSIT, WITHDRAWAL, BUY, SELL)
        timestamp: When transaction occurred (ISO 8601 format)
        cash_change_amount: Change in cash balance (decimal)
        cash_change_currency: Currency code (e.g., "USD")
        ticker_symbol: Stock symbol for trades (None for cash transactions)
        quantity_shares: Number of shares for trades (None for cash transactions)
        price_per_share_amount: Price per share for trades (None for cash transactions)
        price_per_share_currency: Currency for price (None for cash transactions)
        notes: Optional transaction description
    """

    id: UUID
    portfolio_id: UUID
    transaction_type: str
    timestamp: datetime
    cash_change_amount: Decimal
    cash_change_currency: str
    ticker_symbol: str | None = None
    quantity_shares: Decimal | None = None
    price_per_share_amount: Decimal | None = None
    price_per_share_currency: str | None = None
    notes: str | None = None

    @staticmethod
    def from_entity(transaction: Transaction) -> "TransactionDTO":
        """Convert a Transaction entity to DTO.

        Args:
            transaction: Domain Transaction entity

        Returns:
            TransactionDTO with value objects converted to primitives
        """
        return TransactionDTO(
            id=transaction.id,
            portfolio_id=transaction.portfolio_id,
            transaction_type=transaction.transaction_type.value,
            timestamp=transaction.timestamp,
            cash_change_amount=transaction.cash_change.amount,
            cash_change_currency=transaction.cash_change.currency,
            ticker_symbol=(
                transaction.ticker.symbol if transaction.ticker is not None else None
            ),
            quantity_shares=(
                transaction.quantity.shares
                if transaction.quantity is not None
                else None
            ),
            price_per_share_amount=(
                transaction.price_per_share.amount
                if transaction.price_per_share is not None
                else None
            ),
            price_per_share_currency=(
                transaction.price_per_share.currency
                if transaction.price_per_share is not None
                else None
            ),
            notes=transaction.notes,
        )
