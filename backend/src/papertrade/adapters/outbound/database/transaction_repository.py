"""SQLModel implementation of TransactionRepository.

Provides transaction persistence using SQLModel ORM with append-only semantics.
"""

from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from papertrade.adapters.outbound.database.models import TransactionModel
from papertrade.domain.entities.transaction import Transaction, TransactionType


class DuplicateTransactionError(Exception):
    """Raised when attempting to save a transaction that already exists."""

    pass


class SQLModelTransactionRepository:
    """SQLModel implementation of TransactionRepository protocol.

    Enforces append-only semantics - transactions cannot be updated or deleted.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session.

        Args:
            session: Async database session for this unit of work
        """
        self._session = session

    async def get(self, transaction_id: UUID) -> Transaction | None:
        """Retrieve a single transaction by ID.

        Args:
            transaction_id: Unique identifier of the transaction

        Returns:
            Transaction entity if found, None if not found
        """
        result = await self._session.get(TransactionModel, transaction_id)
        if result is None:
            return None
        return result.to_domain()

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
            List of Transaction entities (may be empty), sorted by timestamp
        """
        statement = select(TransactionModel).where(
            TransactionModel.portfolio_id == portfolio_id
        )

        # Apply type filter if provided
        if transaction_type is not None:
            statement = statement.where(
                TransactionModel.transaction_type == transaction_type.value
            )

        # Order by timestamp (chronological)
        statement = statement.order_by(TransactionModel.timestamp.asc())  # type: ignore[attr-defined]  # SQLModel field has SQLAlchemy column methods

        # Apply pagination
        if offset > 0:
            statement = statement.offset(offset)
        if limit is not None:
            statement = statement.limit(limit)

        result = await self._session.exec(statement)
        models = result.all()
        return [model.to_domain() for model in models]

    async def count_by_portfolio(
        self,
        portfolio_id: UUID,
        transaction_type: TransactionType | None = None,
    ) -> int:
        """Count total transactions for a portfolio, optionally filtered by type.

        Args:
            portfolio_id: Portfolio to count transactions for
            transaction_type: Filter by transaction type (None = all types)

        Returns:
            Total count of matching transactions (0 if none)
        """
        from sqlalchemy import func

        statement = (
            select(func.count())
            .select_from(TransactionModel)
            .where(TransactionModel.portfolio_id == portfolio_id)
        )

        # Apply type filter if provided
        if transaction_type is not None:
            statement = statement.where(
                TransactionModel.transaction_type == transaction_type.value
            )

        result = await self._session.exec(statement)
        count = result.first()
        return count if count is not None else 0

    async def save(self, transaction: Transaction) -> None:
        """Persist a new transaction (append-only, no updates).

        Raises:
            DuplicateTransactionError: If transaction ID already exists
        """
        # Check if transaction already exists
        existing = await self.get(transaction.id)
        if existing is not None:
            raise DuplicateTransactionError(
                f"Transaction already exists: {transaction.id}"
            )

        # Create new transaction model
        model = TransactionModel.from_domain(transaction)
        self._session.add(model)

        # Try to flush to catch any integrity errors
        try:
            await self._session.flush()
        except IntegrityError as e:
            raise DuplicateTransactionError(
                f"Transaction already exists: {transaction.id}"
            ) from e
