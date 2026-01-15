"""SQLModel database models for persistence.

These models represent the database schema and provide conversion functions
to/from domain entities.
"""

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from sqlmodel import Field, Index, SQLModel

from zebu.domain.entities.portfolio import Portfolio
from zebu.domain.entities.portfolio_snapshot import PortfolioSnapshot
from zebu.domain.entities.transaction import Transaction, TransactionType
from zebu.domain.value_objects.money import Money
from zebu.domain.value_objects.quantity import Quantity
from zebu.domain.value_objects.ticker import Ticker


class PortfolioModel(SQLModel, table=True):
    """Database model for Portfolio entity.

    Attributes:
        id: Primary key (UUID)
        user_id: Foreign key to user (UUID) - indexed for get_by_user queries
        name: Portfolio display name
        created_at: Timestamp of portfolio creation
        updated_at: Timestamp of last modification
        version: Version number for optimistic locking
    """

    __tablename__ = "portfolios"  # type: ignore[assignment]  # SQLModel requires string literal for __tablename__
    __table_args__ = (Index("idx_portfolio_user_id", "user_id"),)

    id: UUID = Field(primary_key=True)
    user_id: UUID = Field(index=True)
    name: str = Field(max_length=100)
    created_at: datetime
    updated_at: datetime
    version: int = Field(default=1)

    def to_domain(self) -> Portfolio:
        """Convert database model to domain entity.

        Returns:
            Portfolio domain entity
        """
        # Database stores naive UTC datetimes - add UTC timezone back
        created_at_utc = self.created_at.replace(tzinfo=UTC)

        return Portfolio(
            id=self.id,
            user_id=self.user_id,
            name=self.name,
            created_at=created_at_utc,
        )

    @classmethod
    def from_domain(cls, portfolio: Portfolio) -> "PortfolioModel":
        """Convert domain entity to database model.

        Args:
            portfolio: Domain Portfolio entity

        Returns:
            PortfolioModel for database persistence
        """
        now = datetime.now(UTC)
        # Strip timezone for PostgreSQL TIMESTAMP WITHOUT TIME ZONE columns
        # Convert to UTC first if needed, then strip timezone
        if portfolio.created_at.tzinfo:
            created_at_naive = portfolio.created_at.astimezone(UTC).replace(tzinfo=None)
        else:
            # Assume naive datetimes are already UTC (per domain contract)
            created_at_naive = portfolio.created_at
        updated_at_naive = now.replace(tzinfo=None)

        return cls(
            id=portfolio.id,
            user_id=portfolio.user_id,
            name=portfolio.name,
            created_at=created_at_naive,
            updated_at=updated_at_naive,
            version=1,
        )


class TransactionModel(SQLModel, table=True):
    """Database model for Transaction entity.

    Transactions are immutable and append-only. The model flattens value objects
    (Money, Ticker, Quantity) into primitive columns for database storage.

    Attributes:
        id: Primary key (UUID)
        portfolio_id: Foreign key to portfolio (UUID) - indexed
        transaction_type: Type of transaction (DEPOSIT, WITHDRAWAL, BUY, SELL)
        timestamp: When the transaction occurred
        cash_change_amount: Amount of cash change (Decimal)
        cash_change_currency: Currency code (e.g., "USD")
        ticker: Stock symbol (optional, only for BUY/SELL)
        quantity: Number of shares (optional, only for BUY/SELL)
        price_per_share_amount: Price per share (optional, only for BUY/SELL)
        price_per_share_currency: Currency for price (optional, only for BUY/SELL)
        notes: Optional transaction notes
        created_at: When record was inserted (for audit)
    """

    __tablename__ = "transactions"  # type: ignore[assignment]  # SQLModel requires string literal for __tablename__
    __table_args__ = (
        Index("idx_transaction_portfolio_id", "portfolio_id"),
        Index("idx_transaction_timestamp", "timestamp"),
        Index("idx_transaction_portfolio_timestamp", "portfolio_id", "timestamp"),
    )

    id: UUID = Field(primary_key=True)
    portfolio_id: UUID = Field(index=True)
    transaction_type: str = Field(max_length=20)
    timestamp: datetime
    cash_change_amount: Decimal = Field(max_digits=15, decimal_places=2)
    cash_change_currency: str = Field(max_length=3)
    ticker: str | None = Field(default=None, max_length=5)
    quantity: Decimal | None = Field(default=None, max_digits=15, decimal_places=4)
    price_per_share_amount: Decimal | None = Field(
        default=None, max_digits=15, decimal_places=2
    )
    price_per_share_currency: str | None = Field(default=None, max_length=3)
    notes: str | None = Field(default=None, max_length=500)
    created_at: datetime = Field(default_factory=datetime.now)

    def to_domain(self) -> Transaction:
        """Convert database model to domain entity.

        Returns:
            Transaction domain entity with reconstructed value objects
        """
        # Reconstruct value objects from primitive fields
        cash_change = Money(self.cash_change_amount, self.cash_change_currency)

        ticker_obj: Ticker | None = None
        quantity_obj: Quantity | None = None
        price_obj: Money | None = None

        if self.ticker:
            ticker_obj = Ticker(self.ticker)
        if self.quantity is not None:
            quantity_obj = Quantity(self.quantity)
        if self.price_per_share_amount is not None and self.price_per_share_currency:
            price_obj = Money(
                self.price_per_share_amount, self.price_per_share_currency
            )

        # Database stores naive UTC datetimes - add UTC timezone back
        timestamp_utc = self.timestamp.replace(tzinfo=UTC)

        return Transaction(
            id=self.id,
            portfolio_id=self.portfolio_id,
            transaction_type=TransactionType[self.transaction_type],
            timestamp=timestamp_utc,
            cash_change=cash_change,
            ticker=ticker_obj,
            quantity=quantity_obj,
            price_per_share=price_obj,
            notes=self.notes,
        )

    @classmethod
    def from_domain(cls, transaction: Transaction) -> "TransactionModel":
        """Convert domain entity to database model.

        Args:
            transaction: Domain Transaction entity

        Returns:
            TransactionModel for database persistence
        """
        # Flatten value objects to primitive fields
        ticker_str: str | None = None
        quantity_dec: Decimal | None = None
        price_amount: Decimal | None = None
        price_currency: str | None = None

        if transaction.ticker:
            ticker_str = transaction.ticker.symbol
        if transaction.quantity:
            quantity_dec = transaction.quantity.shares
        if transaction.price_per_share:
            price_amount = transaction.price_per_share.amount
            price_currency = transaction.price_per_share.currency

        # Strip timezone for PostgreSQL TIMESTAMP WITHOUT TIME ZONE columns
        # Convert to UTC first if needed, then strip timezone
        now = datetime.now(UTC)
        created_at_naive = now.replace(tzinfo=None)

        if transaction.timestamp.tzinfo:
            timestamp_naive = transaction.timestamp.astimezone(UTC).replace(tzinfo=None)
        else:
            # Assume naive datetimes are already UTC (per domain contract)
            timestamp_naive = transaction.timestamp

        return cls(
            id=transaction.id,
            portfolio_id=transaction.portfolio_id,
            transaction_type=transaction.transaction_type.value,
            timestamp=timestamp_naive,
            cash_change_amount=transaction.cash_change.amount,
            cash_change_currency=transaction.cash_change.currency,
            ticker=ticker_str,
            quantity=quantity_dec,
            price_per_share_amount=price_amount,
            price_per_share_currency=price_currency,
            notes=transaction.notes,
            created_at=created_at_naive,
        )


class PortfolioSnapshotModel(SQLModel, table=True):
    """Database model for portfolio snapshots.

    Snapshots represent the daily state of a portfolio for analytics.
    One snapshot per portfolio per day (unique constraint enforced).

    Attributes:
        id: Primary key (UUID)
        portfolio_id: Foreign key to portfolio (UUID) - indexed
        snapshot_date: Date of snapshot (end-of-day)
        total_value: Total portfolio value (cash + holdings)
        cash_balance: Available cash
        holdings_value: Total value of all holdings
        holdings_count: Number of unique stocks held
        created_at: When snapshot was calculated
    """

    __tablename__ = "portfolio_snapshots"  # type: ignore[assignment]  # SQLModel requires string literal for __tablename__
    __table_args__ = (
        Index("idx_snapshot_portfolio_date", "portfolio_id", "snapshot_date"),
        Index("idx_snapshot_date", "snapshot_date"),
    )

    id: UUID = Field(primary_key=True)
    portfolio_id: UUID = Field(index=False)  # Index covered by composite index
    snapshot_date: date
    total_value: Decimal = Field(max_digits=15, decimal_places=2)
    cash_balance: Decimal = Field(max_digits=15, decimal_places=2)
    holdings_value: Decimal = Field(max_digits=15, decimal_places=2)
    holdings_count: int
    created_at: datetime

    def to_domain(self) -> PortfolioSnapshot:
        """Convert database model to domain entity.

        Returns:
            PortfolioSnapshot domain entity
        """
        # Database stores naive UTC datetimes - add UTC timezone back
        created_at_utc = self.created_at.replace(tzinfo=UTC)

        return PortfolioSnapshot(
            id=self.id,
            portfolio_id=self.portfolio_id,
            snapshot_date=self.snapshot_date,
            total_value=self.total_value,
            cash_balance=self.cash_balance,
            holdings_value=self.holdings_value,
            holdings_count=self.holdings_count,
            created_at=created_at_utc,
        )

    @classmethod
    def from_domain(cls, snapshot: PortfolioSnapshot) -> "PortfolioSnapshotModel":
        """Convert domain entity to database model.

        Args:
            snapshot: Domain PortfolioSnapshot entity

        Returns:
            PortfolioSnapshotModel for database persistence
        """
        # Strip timezone for PostgreSQL TIMESTAMP WITHOUT TIME ZONE columns
        if snapshot.created_at.tzinfo:
            created_at_naive = snapshot.created_at.astimezone(UTC).replace(tzinfo=None)
        else:
            # Assume naive datetimes are already UTC (per domain contract)
            created_at_naive = snapshot.created_at

        return cls(
            id=snapshot.id,
            portfolio_id=snapshot.portfolio_id,
            snapshot_date=snapshot.snapshot_date,
            total_value=snapshot.total_value,
            cash_balance=snapshot.cash_balance,
            holdings_value=snapshot.holdings_value,
            holdings_count=snapshot.holdings_count,
            created_at=created_at_naive,
        )
