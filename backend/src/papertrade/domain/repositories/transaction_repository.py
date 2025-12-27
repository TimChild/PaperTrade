"""Transaction repository interface (Port)."""

from typing import Protocol
from uuid import UUID

from papertrade.domain.entities import Transaction


class TransactionRepository(Protocol):
    """Protocol defining the interface for transaction persistence.

    This is a Port in Clean Architecture - adapters will implement this interface.
    Note: Transactions are immutable ledger entries, so there is no delete operation.
    """

    async def get(self, transaction_id: UUID) -> Transaction | None:
        """Get a transaction by ID.

        Args:
            transaction_id: The unique identifier of the transaction.

        Returns:
            The transaction if found, None otherwise.
        """
        ...

    async def get_by_portfolio(self, portfolio_id: UUID) -> list[Transaction]:
        """Get all transactions for a portfolio.

        Args:
            portfolio_id: The unique identifier of the portfolio.

        Returns:
            List of transactions ordered by timestamp (oldest first).
        """
        ...

    async def save(self, transaction: Transaction) -> None:
        """Save a new transaction.

        Args:
            transaction: The transaction to save.

        Note:
            Transactions are immutable and cannot be modified after creation.
        """
        ...
