"""Transaction repository port (interface).

Defines the contract for transaction persistence operations. Transactions are
immutable and append-only - no updates or deletes are supported.
"""

from typing import Protocol
from uuid import UUID

from zebu.domain.entities.transaction import Transaction, TransactionType


class TransactionRepository(Protocol):
    """Interface for transaction persistence operations.

    Transactions are immutable and append-only. Once created, they cannot be
    modified or deleted. This maintains the integrity of the audit ledger.
    """

    async def get(self, transaction_id: UUID) -> Transaction | None:
        """Retrieve a single transaction by ID.

        Args:
            transaction_id: Unique identifier of the transaction

        Returns:
            Transaction entity if found, None if not found

        Raises:
            RepositoryError: If database connection or query fails
        """
        ...

    async def get_by_portfolio(
        self,
        portfolio_id: UUID,
        limit: int | None = None,
        offset: int = 0,
        transaction_type: TransactionType | None = None,
    ) -> list[Transaction]:
        """Retrieve transactions for a portfolio, optionally filtered and paginated.

        Transactions are returned in chronological order (timestamp ascending).

        Args:
            portfolio_id: Portfolio to retrieve transactions for
            limit: Maximum number of transactions to return (None = all)
            offset: Number of transactions to skip (for pagination)
            transaction_type: Filter by transaction type (None = all types)

        Returns:
            List of Transaction entities (may be empty)
            Sorted by timestamp ascending (oldest first)

        Raises:
            RepositoryError: If database connection or query fails
        """
        ...

    async def count_by_portfolio(
        self,
        portfolio_id: UUID,
        transaction_type: TransactionType | None = None,
    ) -> int:
        """Count total transactions for a portfolio, optionally filtered by type.

        Used for pagination to calculate total pages.

        Args:
            portfolio_id: Portfolio to count transactions for
            transaction_type: Filter by transaction type (None = all types)

        Returns:
            Total count of matching transactions (0 if none)

        Raises:
            RepositoryError: If database connection or query fails
        """
        ...

    async def save(self, transaction: Transaction) -> None:
        """Persist a new transaction (append-only, no updates).

        This method ONLY creates new records. Attempting to save a transaction
        with an existing ID will raise an error to maintain ledger integrity.

        Args:
            transaction: Transaction entity to persist

        Raises:
            RepositoryError: If transaction already exists or save fails
        """
        ...

    async def delete_by_portfolio(self, portfolio_id: UUID) -> int:
        """Delete all transactions for a portfolio.

        Used for cleanup when a portfolio is deleted. This is the only scenario
        where transactions are deleted, as they are otherwise immutable.

        Args:
            portfolio_id: Portfolio identifier

        Returns:
            Count of transactions deleted (0 if none existed)

        Raises:
            RepositoryError: If database connection or delete fails
        """
        ...
