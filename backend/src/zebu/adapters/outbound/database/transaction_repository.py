"""SQLModel implementation of TransactionRepository.

Provides transaction persistence using SQLModel ORM with append-only semantics.
"""

from uuid import UUID

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlmodel import delete, select
from sqlmodel.ext.asyncio.session import AsyncSession

from zebu.adapters.outbound.database.models import TransactionModel
from zebu.domain.entities.transaction import Transaction, TransactionType


class DuplicateTransactionError(Exception):
    """Raised when attempting to save a transaction that already exists."""

    pass


def _is_pk_conflict(error: IntegrityError) -> bool:
    """Return True iff ``error`` is a primary-key / UNIQUE conflict on
    ``transactions.id`` (i.e. a duplicate-transaction insert).

    Other ``IntegrityError`` variants — FK violations, NOT NULL violations,
    CHECK constraint failures — must surface unchanged so callers can
    distinguish a real referential-integrity bug from a duplicate
    insert. Historically this catch was a catch-all that translated every
    ``IntegrityError`` to ``DuplicateTransactionError``, which masked the
    FK ordering bug fixed in #287 and the FK regressions fixed in #291.

    Detection is by inspecting the message of the underlying DB-API
    exception (``error.orig``). Both SQLite and Postgres mention the
    table-qualified column name in the UNIQUE / PK violation message —
    that's enough to distinguish from FK / NOT NULL.
    """
    orig = error.orig
    if orig is None:
        # Defensive: SQLAlchemy normally populates ``orig`` from the
        # DB-API. Without it we can't tell what kind of integrity error
        # this is; refuse to translate to DuplicateTransactionError.
        return False
    message = str(orig).lower()
    # SQLite: ``UNIQUE constraint failed: transactions.id``
    # Postgres: ``duplicate key value violates unique constraint
    #            "transactions_pkey"`` and message includes ``Key (id)=...``
    return "transactions.id" in message or "transactions_pkey" in message


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

    async def save(
        self,
        transaction: Transaction,
        *,
        api_key_id: UUID | None = None,
        trigger_id: UUID | None = None,
    ) -> None:
        """Persist a new transaction (append-only, no updates).

        Args:
            transaction: Transaction entity to persist.
            api_key_id: Phase H2 — ID of the API key that authenticated the
                writing request, or None for Clerk Bearer (human via UI).
                Activity feed joins on this column to surface the API-key
                label as the actor identity.
            trigger_id: Phase F-5 — ID of the StrategyConditionTrigger that
                produced this transaction (when the trade came from a woken-
                agent BUY/SELL decision). None for non-trigger-driven trades.

        Raises:
            DuplicateTransactionError: If transaction ID already exists.
            IntegrityError: If a non-PK integrity constraint fails (FK,
                NOT NULL, CHECK). The caller is responsible for surfacing
                this as a real bug — silent swallowing previously masked
                FK ordering errors (#287, #291).
        """
        # Check if transaction already exists
        existing = await self.get(transaction.id)
        if existing is not None:
            raise DuplicateTransactionError(
                f"Transaction already exists: {transaction.id}"
            )

        # Create new transaction model
        model = TransactionModel.from_domain(transaction)
        model.api_key_id = api_key_id
        model.trigger_id = trigger_id
        self._session.add(model)

        # Try to flush to catch any integrity errors. Only PK / UNIQUE
        # conflicts on ``transactions.id`` are translated to the
        # domain-level ``DuplicateTransactionError`` — every other
        # ``IntegrityError`` (FK, NOT NULL, CHECK) propagates unchanged
        # so callers can distinguish duplicate inserts from real
        # referential-integrity bugs.
        try:
            await self._session.flush()
        except IntegrityError as e:
            if _is_pk_conflict(e):
                raise DuplicateTransactionError(
                    f"Transaction already exists: {transaction.id}"
                ) from e
            raise

    async def save_all(
        self,
        transactions: list[Transaction],
        *,
        api_key_id: UUID | None = None,
        trigger_id: UUID | None = None,
    ) -> None:
        """Bulk-persist multiple transactions in a single round-trip.

        Hot path for backtest persistence — single ``add_all`` + ``flush``
        replaces N per-row ``save()`` calls (each of which did SELECT-then-
        INSERT). For a 100-trade backtest this drops 200+ round-trips to 1.

        Note: This relies on PK uniqueness rather than a per-row SELECT.
        A PK conflict surfaces as DuplicateTransactionError with no
        information about which ID collided — acceptable for the
        backtest path (IDs are uuid4-generated in-process). Non-PK
        integrity errors (FK, NOT NULL, CHECK) propagate as IntegrityError.

        Args:
            transactions: Transactions to persist.
            api_key_id: Phase H2 — stamped onto every row in the batch
                (uniform credential, since the request itself only has one
                auth context). None for Clerk Bearer / human-via-UI.
            trigger_id: Phase F-5 — stamped uniformly onto every row in the
                batch when the trades all originate from one trigger fire.
                None for non-trigger-driven trades.

        Raises:
            DuplicateTransactionError: If any transaction ID already exists.
            IntegrityError: If a non-PK integrity constraint fails (FK,
                NOT NULL, CHECK) on any row in the batch.
        """
        if not transactions:
            return

        models: list[TransactionModel] = []
        for t in transactions:
            model = TransactionModel.from_domain(t)
            model.api_key_id = api_key_id
            model.trigger_id = trigger_id
            models.append(model)
        self._session.add_all(models)
        # Same narrowing as ``save``: only translate PK / UNIQUE conflicts
        # on ``transactions.id`` to DuplicateTransactionError. FK / NOT
        # NULL / CHECK violations propagate unchanged.
        try:
            await self._session.flush()
        except IntegrityError as e:
            if _is_pk_conflict(e):
                raise DuplicateTransactionError(
                    f"Bulk insert failed: one or more of {len(transactions)} "
                    f"transactions already exists"
                ) from e
            raise

    async def delete_by_portfolio(self, portfolio_id: UUID) -> int:
        """Delete all transactions for a portfolio.

        Used for cleanup when a portfolio is deleted. This is the only scenario
        where transactions are deleted, as they are otherwise immutable.

        Args:
            portfolio_id: Portfolio identifier

        Returns:
            Count of transactions deleted (0 if none existed)
        """
        # Count transactions before deleting
        count_statement = (
            select(func.count())
            .select_from(TransactionModel)
            .where(TransactionModel.portfolio_id == portfolio_id)
        )
        count_result = await self._session.exec(count_statement)
        count = count_result.one()

        # Now delete them
        statement = delete(TransactionModel).where(
            TransactionModel.portfolio_id == portfolio_id  # type: ignore[arg-type]  # SQLModel field comparison returns bool-like column expression
        )
        await self._session.exec(statement)

        return count

    async def get_by_portfolios(
        self, portfolio_ids: list[UUID]
    ) -> dict[UUID, list[Transaction]]:
        """Retrieve transactions for multiple portfolios in a single query.

        Args:
            portfolio_ids: List of portfolio IDs to retrieve transactions for

        Returns:
            Dict mapping each portfolio_id to its list of transactions,
            sorted by timestamp ascending. Missing portfolio_ids are excluded.
        """
        if not portfolio_ids:
            return {}

        statement = (
            select(TransactionModel)
            .where(TransactionModel.portfolio_id.in_(portfolio_ids))  # type: ignore[attr-defined]
            .order_by(TransactionModel.timestamp.asc())  # type: ignore[attr-defined]
        )

        result = await self._session.exec(statement)
        models = result.all()

        # Group by portfolio_id
        grouped: dict[UUID, list[Transaction]] = {}
        for model in models:
            transaction = model.to_domain()
            pid = transaction.portfolio_id
            if pid not in grouped:
                grouped[pid] = []
            grouped[pid].append(transaction)

        return grouped
