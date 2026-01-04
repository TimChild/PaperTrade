"""SQLModel for price_history table.

This module contains the database model for storing historical price data for stocks.
It includes conversion methods to/from the PricePoint DTO.
"""

from datetime import UTC, datetime
from decimal import Decimal

from sqlmodel import Field, Index, SQLModel

from papertrade.application.dtos.price_point import PricePoint
from papertrade.domain.value_objects.money import Money
from papertrade.domain.value_objects.ticker import Ticker


class PriceHistoryModel(SQLModel, table=True):
    """Database model for price_history table.

    Stores all historical and current price data for stocks. This table is append-mostly
    (updates only for corrections via upsert, never deletes).

    The model flattens Money value objects into separate amount/currency columns
    for database storage. OHLCV data is optional and only populated for
    interval-based prices.

    Attributes:
        id: Auto-incrementing primary key
        ticker: Stock ticker symbol (uppercase, 1-10 chars)
        price_amount: Price at observation time (decimal)
        price_currency: ISO 4217 currency code (default: USD)
        timestamp: When price was observed (UTC timezone)
        source: Data source identifier (alpha_vantage, cache, database)
        interval: Price interval type (real-time, 1day, 1hour, 5min, 1min)
        open_amount: Opening price for interval (optional)
        open_currency: Currency for open price (optional)
        high_amount: Highest price in interval (optional)
        high_currency: Currency for high price (optional)
        low_amount: Lowest price in interval (optional)
        low_currency: Currency for low price (optional)
        close_amount: Closing price for interval (optional)
        close_currency: Currency for close price (optional)
        volume: Trading volume (optional, non-negative)
        created_at: When record was inserted (for audit)
    """

    __tablename__ = "price_history"  # type: ignore[assignment]  # SQLModel requires string literal for __tablename__
    __table_args__ = (
        # Unique constraint: one price per ticker per timestamp per interval
        Index(
            "uk_price_history",
            "ticker",
            "timestamp",
            "source",
            "interval",
            unique=True,
        ),
        # Query optimization indexes
        Index("idx_price_history_ticker_timestamp", "ticker", "timestamp"),
        Index(
            "idx_price_history_ticker_interval_timestamp",
            "ticker",
            "interval",
            "timestamp",
        ),
    )

    # Primary key
    id: int | None = Field(default=None, primary_key=True)

    # Core price data
    ticker: str = Field(max_length=10, index=True)
    price_amount: Decimal = Field(decimal_places=2)
    price_currency: str = Field(default="USD", max_length=3)
    timestamp: datetime = Field(index=True)
    source: str = Field(max_length=50)
    interval: str = Field(max_length=10)

    # Optional OHLCV data
    open_amount: Decimal | None = Field(default=None, decimal_places=2)
    open_currency: str | None = Field(default=None, max_length=3)
    high_amount: Decimal | None = Field(default=None, decimal_places=2)
    high_currency: str | None = Field(default=None, max_length=3)
    low_amount: Decimal | None = Field(default=None, decimal_places=2)
    low_currency: str | None = Field(default=None, max_length=3)
    close_amount: Decimal | None = Field(default=None, decimal_places=2)
    close_currency: str | None = Field(default=None, max_length=3)
    volume: int | None = None

    # Metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def to_price_point(self) -> PricePoint:
        """Convert database model to PricePoint DTO.

        Reconstructs Money value objects from separate amount/currency columns.

        Returns:
            PricePoint DTO with price data
        """
        # Construct core Money object for price
        price = Money(amount=self.price_amount, currency=self.price_currency)

        # Construct optional OHLCV Money objects
        open_money: Money | None = None
        if self.open_amount is not None and self.open_currency is not None:
            open_money = Money(amount=self.open_amount, currency=self.open_currency)

        high_money: Money | None = None
        if self.high_amount is not None and self.high_currency is not None:
            high_money = Money(amount=self.high_amount, currency=self.high_currency)

        low_money: Money | None = None
        if self.low_amount is not None and self.low_currency is not None:
            low_money = Money(amount=self.low_amount, currency=self.low_currency)

        close_money: Money | None = None
        if self.close_amount is not None and self.close_currency is not None:
            close_money = Money(amount=self.close_amount, currency=self.close_currency)

        # Ensure timestamp is UTC-aware (SQLite stores naive datetimes)
        timestamp = self.timestamp
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=UTC)

        return PricePoint(
            ticker=Ticker(self.ticker),
            price=price,
            timestamp=timestamp,
            source=self.source,
            interval=self.interval,
            open=open_money,
            high=high_money,
            low=low_money,
            close=close_money,
            volume=self.volume,
        )

    @classmethod
    def from_price_point(cls, price: PricePoint) -> "PriceHistoryModel":
        """Create database model from PricePoint DTO.

        Flattens Money value objects into separate amount/currency columns.

        Args:
            price: PricePoint DTO to convert

        Returns:
            PriceHistoryModel for database persistence
        """
        return cls(
            ticker=price.ticker.symbol,
            price_amount=price.price.amount,
            price_currency=price.price.currency,
            # Strip timezone for PostgreSQL TIMESTAMP WITHOUT TIME ZONE
            timestamp=price.timestamp.replace(tzinfo=None) if price.timestamp.tzinfo else price.timestamp,
            source=price.source,
            interval=price.interval,
            open_amount=price.open.amount if price.open else None,
            open_currency=price.open.currency if price.open else None,
            high_amount=price.high.amount if price.high else None,
            high_currency=price.high.currency if price.high else None,
            low_amount=price.low.amount if price.low else None,
            low_currency=price.low.currency if price.low else None,
            close_amount=price.close.amount if price.close else None,
            close_currency=price.close.currency if price.close else None,
            volume=price.volume,
        )
