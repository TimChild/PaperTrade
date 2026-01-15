"""SQLModel for ticker_watchlist table.

This module contains the database model for tracking which tickers to refresh in
background jobs.
"""

from datetime import UTC, datetime

from sqlmodel import Field, Index, SQLModel

from zebu.domain.value_objects.ticker import Ticker


class TickerWatchlistModel(SQLModel, table=True):
    """Database model for ticker_watchlist table.

    Tracks which tickers should be automatically refreshed in background jobs.
    Separate from price_history to manage refresh priority independently.

    Attributes:
        id: Auto-incrementing primary key
        ticker: Stock ticker symbol (unique, uppercase)
        priority: Refresh priority (lower number = higher priority, 1-100)
        last_refresh_at: Last successful price refresh timestamp (UTC)
        next_refresh_at: When next refresh should occur (UTC)
        refresh_interval_seconds: Seconds between refreshes (default: 300 = 5 min)
        is_active: Whether ticker is actively tracked (default: True)
        created_at: When ticker was added to watchlist
        updated_at: When record was last modified
    """

    __tablename__ = "ticker_watchlist"  # type: ignore[assignment]  # SQLModel requires string literal for __tablename__
    __table_args__ = (
        # Index for finding tickers that need refresh
        Index(
            "idx_watchlist_next_refresh",
            "next_refresh_at",
            postgresql_where="is_active = TRUE",  # Partial index (PostgreSQL only)
        ),
    )

    # Primary key
    id: int | None = Field(default=None, primary_key=True)

    # Ticker identification
    ticker: str = Field(unique=True, max_length=10)

    # Refresh scheduling
    priority: int = Field(default=100)  # Lower = higher priority
    last_refresh_at: datetime | None = None
    next_refresh_at: datetime | None = None
    refresh_interval_seconds: int = Field(default=300)  # 5 minutes default

    # Status
    is_active: bool = Field(default=True)

    # Metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def to_ticker(self) -> Ticker:
        """Convert to Ticker value object.

        Returns:
            Ticker value object
        """
        return Ticker(self.ticker)

    @classmethod
    def from_ticker(
        cls, ticker: Ticker, priority: int = 100, refresh_interval_seconds: int = 300
    ) -> "TickerWatchlistModel":
        """Create watchlist model from Ticker.

        Args:
            ticker: Ticker to track
            priority: Refresh priority (lower = higher priority)
            refresh_interval_seconds: Seconds between refreshes

        Returns:
            TickerWatchlistModel for database persistence
        """
        return cls(
            ticker=ticker.symbol,
            priority=priority,
            refresh_interval_seconds=refresh_interval_seconds,
        )
