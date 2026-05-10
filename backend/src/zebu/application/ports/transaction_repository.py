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

    async def save(
        self,
        transaction: Transaction,
        *,
        api_key_id: UUID | None = None,
        trigger_id: UUID | None = None,
    ) -> None:
        """Persist a new transaction (append-only, no updates).

        This method ONLY creates new records. Attempting to save a transaction
        with an existing ID will raise an error to maintain ledger integrity.

        Args:
            transaction: Transaction entity to persist.
            api_key_id: Phase H2 — ID of the API key that authenticated the
                writing request, or None for Clerk Bearer (human via UI).
                Adapters that don't track this (e.g. older in-memory tests)
                may ignore the kwarg; production adapters MUST stamp it onto
                the row so the activity-feed aggregator can join back to
                ``api_keys.label`` for the actor identity column.
            trigger_id: Phase F-5 — ID of the StrategyConditionTrigger that
                produced this transaction (when the trade was the result of
                a woken-agent BUY/SELL decision). None for trades that did
                NOT come from a trigger fire — direct human-initiated trades,
                daily-strategy execution-loop trades, etc. The activity feed
                joins on this column to connect a trade back to the fire
                that produced it.

        Raises:
            RepositoryError: If transaction already exists or save fails
        """
        ...

    async def save_all(
        self,
        transactions: list[Transaction],
        *,
        api_key_id: UUID | None = None,
        trigger_id: UUID | None = None,
    ) -> None:
        """Persist multiple new transactions in a single bulk insert.

        Bulk-insert path for hot loops (e.g. backtest persistence) where
        per-row ``save()`` is N+1 against the DB. Adapters MUST issue a
        single round-trip (one ``INSERT ... VALUES (...), (...), ...`` /
        ``add_all`` + flush) rather than looping ``save()``.

        Args:
            transactions: List of Transaction entities to persist.
                An empty list is a no-op.
            api_key_id: Phase H2 — stamped uniformly onto every row in the
                batch (the request itself only has one auth context). None
                for Clerk Bearer / human-via-UI.
            trigger_id: Phase F-5 — stamped uniformly onto every row in the
                batch when the trades all originate from the same trigger
                fire (the typical case — one fire produces one BUY or one
                SELL, not a mix). None for non-trigger-driven trades.

        Raises:
            RepositoryError: If any transaction ID already exists or
                the bulk insert fails. On failure, no transactions are
                persisted (atomic at the session level).
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

    async def get_by_portfolios(
        self, portfolio_ids: list[UUID]
    ) -> dict[UUID, list[Transaction]]:
        """Retrieve transactions for multiple portfolios in a single query.

        Args:
            portfolio_ids: List of portfolio IDs to retrieve transactions for

        Returns:
            Dict mapping each portfolio_id to its list of transactions,
            sorted by timestamp ascending. Missing portfolio_ids are excluded.

        Raises:
            RepositoryError: If database connection or query fails
        """
        ...
