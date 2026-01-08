"""In-memory implementation of TransactionRepository for testing.

Provides fast, thread-safe in-memory storage suitable for unit testing.
No persistence between test runs.
"""

from threading import Lock
from uuid import UUID

from papertrade.domain.entities.transaction import Transaction, TransactionType


class DuplicateTransactionError(Exception):
    """Raised when attempting to save a transaction that already exists."""

    pass


class InMemoryTransactionRepository:
    """In-memory implementation of TransactionRepository protocol.

    Uses Python dictionaries for O(1) access. Thread-safe with locks.
    Enforces append-only constraint (no updates to existing transactions).
    """

    def __init__(self) -> None:
        """Initialize empty transaction storage."""
        self._transactions: dict[UUID, Transaction] = {}
        self._lock = Lock()

    async def get(self, transaction_id: UUID) -> Transaction | None:
        """Retrieve a transaction by ID."""
        with self._lock:
            return self._transactions.get(transaction_id)

    async def get_by_portfolio(
        self,
        portfolio_id: UUID,
        limit: int | None = None,
        offset: int = 0,
        transaction_type: TransactionType | None = None,
    ) -> list[Transaction]:
        """Retrieve transactions with optional filtering and pagination."""
        with self._lock:
            # Filter by portfolio
            portfolio_transactions = [
                t for t in self._transactions.values() if t.portfolio_id == portfolio_id
            ]

            # Filter by type if specified
            if transaction_type is not None:
                portfolio_transactions = [
                    t
                    for t in portfolio_transactions
                    if t.transaction_type == transaction_type
                ]

            # Sort chronologically
            sorted_transactions = sorted(
                portfolio_transactions, key=lambda t: t.timestamp
            )

            # Apply pagination
            start = offset
            end = None if limit is None else offset + limit
            return sorted_transactions[start:end]

    async def count_by_portfolio(
        self,
        portfolio_id: UUID,
        transaction_type: TransactionType | None = None,
    ) -> int:
        """Count transactions for a portfolio with optional type filter."""
        with self._lock:
            portfolio_transactions = [
                t for t in self._transactions.values() if t.portfolio_id == portfolio_id
            ]

            if transaction_type is not None:
                portfolio_transactions = [
                    t
                    for t in portfolio_transactions
                    if t.transaction_type == transaction_type
                ]

            return len(portfolio_transactions)

    async def save(self, transaction: Transaction) -> None:
        """Save a transaction (append-only, raises error if already exists)."""
        with self._lock:
            if transaction.id in self._transactions:
                raise DuplicateTransactionError(
                    f"Transaction already exists: {transaction.id}"
                )
            self._transactions[transaction.id] = transaction

    async def delete_by_portfolio(self, portfolio_id: UUID) -> int:
        """Delete all transactions for a portfolio.

        Args:
            portfolio_id: Portfolio identifier

        Returns:
            Count of transactions deleted
        """
        with self._lock:
            to_delete = [
                tid
                for tid, t in self._transactions.items()
                if t.portfolio_id == portfolio_id
            ]
            for tid in to_delete:
                del self._transactions[tid]
            return len(to_delete)

    def clear(self) -> None:
        """Clear all transactions (for testing)."""
        with self._lock:
            self._transactions.clear()
