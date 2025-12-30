"""PostgreSQL implementation of price repository for persistent price storage.

This module implements the repository pattern for storing and retrieving historical
price data from PostgreSQL (or SQLite in development). It provides the Tier 2 caching
layer in the tiered market data architecture.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import desc, select
from sqlmodel.ext.asyncio.session import AsyncSession

from papertrade.adapters.outbound.models.price_history import PriceHistoryModel
from papertrade.application.dtos.price_point import PricePoint
from papertrade.domain.value_objects.ticker import Ticker


class PriceRepository:
    """PostgreSQL implementation of price storage repository.

    This repository provides persistent storage for historical price data using
    PostgreSQL (SQLite in development). It implements efficient querying with
    database indexes and supports upsert operations for data updates.

    Performance targets:
        - get_latest_price: <100ms
        - get_price_at: <100ms
        - get_price_history: <100ms for 1 year of daily data
        - upsert_price: <50ms

    Attributes:
        session: Async database session for executing queries

    Example:
        >>> repo = PriceRepository(session)
        >>> await repo.upsert_price(price_point)
        >>> latest = await repo.get_latest_price(Ticker("AAPL"))
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize price repository.

        Args:
            session: Async database session for query execution
        """
        self.session = session

    async def upsert_price(self, price: PricePoint) -> None:
        """Insert or update price (ON CONFLICT DO UPDATE).

        Uses database upsert semantics to handle duplicate price entries.
        If a price already exists for the same ticker/timestamp/source/interval,
        it will be updated with the new values.

        Args:
            price: PricePoint to store in database

        Example:
            >>> await repo.upsert_price(PricePoint(
            ...     ticker=Ticker("AAPL"),
            ...     price=Money(150.25, "USD"),
            ...     timestamp=datetime.now(UTC),
            ...     source="alpha_vantage",
            ...     interval="real-time"
            ... ))
        """
        # Check if a price already exists
        query = select(PriceHistoryModel).where(
            PriceHistoryModel.ticker == price.ticker.symbol,
            PriceHistoryModel.timestamp == price.timestamp,
            PriceHistoryModel.source == price.source,
            PriceHistoryModel.interval == price.interval,
        )
        result = await self.session.execute(query)
        existing = result.scalar_one_or_none()

        if existing:
            # Update existing record
            existing.price_amount = price.price.amount
            existing.price_currency = price.price.currency
            existing.open_amount = price.open.amount if price.open else None
            existing.open_currency = price.open.currency if price.open else None
            existing.high_amount = price.high.amount if price.high else None
            existing.high_currency = price.high.currency if price.high else None
            existing.low_amount = price.low.amount if price.low else None
            existing.low_currency = price.low.currency if price.low else None
            existing.close_amount = price.close.amount if price.close else None
            existing.close_currency = price.close.currency if price.close else None
            existing.volume = price.volume
        else:
            # Insert new record
            model = PriceHistoryModel.from_price_point(price)
            self.session.add(model)

        await self.session.flush()

    async def get_latest_price(
        self, ticker: Ticker, max_age: timedelta | None = None
    ) -> PricePoint | None:
        """Get most recent price for ticker.

        Queries the database for the most recent price observation for the given
        ticker. Optionally filters by maximum age to exclude stale data.

        Args:
            ticker: Stock ticker symbol to get price for
            max_age: Maximum age of price (optional). If provided, only returns
                    prices newer than (now - max_age)

        Returns:
            Most recent PricePoint if found, None otherwise

        Example:
            >>> # Get latest price regardless of age
            >>> price = await repo.get_latest_price(Ticker("AAPL"))
            >>>
            >>> # Get latest price only if within 4 hours
            >>> price = await repo.get_latest_price(
            ...     Ticker("AAPL"),
            ...     max_age=timedelta(hours=4)
            ... )
        """
        # Build query
        query = select(PriceHistoryModel).where(
            PriceHistoryModel.ticker == ticker.symbol
        )

        # Apply age filter if specified
        if max_age is not None:
            cutoff_time = datetime.now(UTC) - max_age
            query = query.where(PriceHistoryModel.timestamp >= cutoff_time)

        # Order by timestamp descending and take first result
        query = query.order_by(desc(PriceHistoryModel.timestamp)).limit(1)

        # Execute query
        result = await self.session.execute(query)
        model = result.scalar_one_or_none()

        # Convert to PricePoint if found
        if model:
            return model.to_price_point()
        return None

    async def get_price_at(
        self, ticker: Ticker, timestamp: datetime
    ) -> PricePoint | None:
        """Get price closest to specified timestamp.

        Finds the price observation closest to (but not after) the given timestamp.
        Useful for historical portfolio valuations and backtesting.

        Args:
            ticker: Stock ticker symbol
            timestamp: Target timestamp (finds price at or before this time)

        Returns:
            PricePoint closest to timestamp if found, None otherwise

        Example:
            >>> # Get AAPL price as of June 15, 2024 at 4:00 PM UTC
            >>> price = await repo.get_price_at(
            ...     Ticker("AAPL"),
            ...     datetime(2024, 6, 15, 16, 0, 0, tzinfo=UTC)
            ... )
        """
        # Query for prices at or before target timestamp
        query = (
            select(PriceHistoryModel)
            .where(PriceHistoryModel.ticker == ticker.symbol)
            .where(PriceHistoryModel.timestamp <= timestamp)
            .order_by(desc(PriceHistoryModel.timestamp))
            .limit(1)
        )

        # Execute query
        result = await self.session.execute(query)
        model = result.scalar_one_or_none()

        # Convert to PricePoint if found
        if model:
            return model.to_price_point()
        return None

    async def get_price_history(
        self,
        ticker: Ticker,
        start: datetime,
        end: datetime,
        interval: str = "1day",
    ) -> list[PricePoint]:
        """Get price history over time range.

        Retrieves all price observations for a ticker within the specified time range,
        filtered by interval type. Results are ordered chronologically.

        Args:
            ticker: Stock ticker symbol
            start: Start of time range (inclusive)
            end: End of time range (inclusive)
            interval: Interval type to filter (default: "1day")
                     Options: "real-time", "1day", "1hour", "5min", "1min"

        Returns:
            List of PricePoints in chronological order. Empty list if none found.

        Example:
            >>> # Get daily prices for AAPL in 2024
            >>> history = await repo.get_price_history(
            ...     Ticker("AAPL"),
            ...     start=datetime(2024, 1, 1, tzinfo=UTC),
            ...     end=datetime(2024, 12, 31, tzinfo=UTC),
            ...     interval="1day"
            ... )
        """
        # Build query
        query = (
            select(PriceHistoryModel)
            .where(PriceHistoryModel.ticker == ticker.symbol)
            .where(PriceHistoryModel.interval == interval)
            .where(PriceHistoryModel.timestamp >= start)
            .where(PriceHistoryModel.timestamp <= end)
            .order_by(PriceHistoryModel.timestamp)  # Chronological order
        )

        # Execute query
        result = await self.session.execute(query)
        models = result.scalars().all()

        # Convert to PricePoints
        return [model.to_price_point() for model in models]

    async def get_all_tickers(self) -> list[Ticker]:
        """Get list of tickers we have data for.

        Queries the database for all unique ticker symbols that have at least one
        price record. Used for frontend autocomplete and ticker discovery.

        Returns:
            List of Ticker objects, sorted alphabetically

        Example:
            >>> tickers = await repo.get_all_tickers()
            >>> print([t.symbol for t in tickers])
            ['AAPL', 'AMZN', 'GOOGL', 'MSFT', 'TSLA']
        """
        # Query for distinct tickers
        query = (
            select(PriceHistoryModel.ticker)
            .distinct()
            .order_by(PriceHistoryModel.ticker)
        )

        # Execute query
        result = await self.session.execute(query)
        ticker_symbols = result.scalars().all()

        # Convert to Ticker objects
        return [Ticker(symbol) for symbol in ticker_symbols]
