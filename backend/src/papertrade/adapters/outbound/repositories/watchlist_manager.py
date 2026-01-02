"""Watchlist manager for tracking tickers that need price refresh.

This module manages the ticker_watchlist table, which tracks which tickers should
be automatically refreshed in background jobs. It provides methods for adding/removing
tickers and finding stale tickers that need updates.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import update
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from papertrade.adapters.outbound.models.ticker_watchlist import TickerWatchlistModel
from papertrade.domain.value_objects.ticker import Ticker


class WatchlistManager:
    """Manages ticker watchlist for automated price refresh.

    This class provides an interface for managing which tickers should be tracked
    and refreshed in background jobs. It handles priority-based refresh scheduling
    and metadata tracking for refresh status.

    Attributes:
        session: Async database session for executing queries

    Example:
        >>> manager = WatchlistManager(session)
        >>> await manager.add_ticker(Ticker("AAPL"), priority=50)
        >>> stale = await manager.get_stale_tickers(limit=10)
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize watchlist manager.

        Args:
            session: Async database session for query execution
        """
        self.session = session

    async def add_ticker(
        self,
        ticker: Ticker,
        priority: int = 100,
        refresh_interval: timedelta = timedelta(minutes=5),
    ) -> None:
        """Add ticker to watchlist.

        Adds a ticker to the watchlist for automatic price refresh. If the ticker
        already exists, updates its priority (takes lower/higher priority value).

        Args:
            ticker: Ticker to add to watchlist
            priority: Refresh priority (lower number = higher priority, range: 1-100)
            refresh_interval: How often to refresh this ticker

        Example:
            >>> # Add AAPL with high priority (refreshed more frequently)
            >>> await manager.add_ticker(
            ...     Ticker("AAPL"),
            ...     priority=50,
            ...     refresh_interval=timedelta(minutes=5)
            ... )
        """
        # Check if ticker already exists
        query = select(TickerWatchlistModel).where(
            TickerWatchlistModel.ticker == ticker.symbol
        )
        result = await self.session.exec(query)
        existing = result.one_or_none()

        if existing:
            # Update priority if the new priority is higher (lower number)
            if priority < existing.priority:
                existing.priority = priority
                existing.refresh_interval_seconds = int(
                    refresh_interval.total_seconds()
                )
            # Re-activate if currently inactive
            existing.is_active = True
            existing.updated_at = datetime.now(UTC)
            await self.session.flush()
        else:
            # Create new watchlist entry
            model = TickerWatchlistModel.from_ticker(
                ticker,
                priority=priority,
                refresh_interval_seconds=int(refresh_interval.total_seconds()),
            )
            self.session.add(model)
            await self.session.flush()

    async def remove_ticker(self, ticker: Ticker) -> None:
        """Remove ticker from watchlist.

        Marks a ticker as inactive in the watchlist rather than deleting it,
        preserving historical refresh data.

        Args:
            ticker: Ticker to remove from watchlist

        Example:
            >>> await manager.remove_ticker(Ticker("AAPL"))
        """
        # Mark as inactive rather than delete (preserve history)
        stmt = (
            update(TickerWatchlistModel)
            .where(TickerWatchlistModel.ticker == ticker.symbol)
            .values(is_active=False, updated_at=datetime.now(UTC))
        )
        await self.session.exec(stmt)
        await self.session.flush()

    async def get_stale_tickers(self, limit: int = 10) -> list[Ticker]:
        """Get tickers that need refresh (past next_refresh_at).

        Finds active tickers whose next_refresh_at time has passed or is None,
        ordered by priority (lower number = higher priority). Used by background
        refresh jobs to determine which tickers to update.

        Args:
            limit: Maximum number of tickers to return (default: 10)

        Returns:
            List of Ticker objects that need refresh, ordered by priority

        Example:
            >>> # Get top 10 stale tickers for refresh
            >>> stale = await manager.get_stale_tickers(limit=10)
            >>> for ticker in stale:
            ...     price = await fetch_price(ticker)
            ...     await manager.update_refresh_metadata(ticker, ...)
        """
        now = datetime.now(UTC)

        # Query for active tickers that need refresh
        query = (
            select(TickerWatchlistModel)
            .where(TickerWatchlistModel.is_active == True)  # noqa: E712
            .where(
                (TickerWatchlistModel.next_refresh_at == None)  # noqa: E711
                | (TickerWatchlistModel.next_refresh_at <= now)
            )
            .order_by(
                TickerWatchlistModel.priority,  # Lower priority number first
                TickerWatchlistModel.last_refresh_at.asc().nullsfirst(),
            )
            .limit(limit)
        )

        # Execute query
        result = await self.session.exec(query)
        models = result.all()

        # Convert to Ticker objects
        return [model.to_ticker() for model in models]

    async def update_refresh_metadata(
        self,
        ticker: Ticker,
        last_refresh: datetime,
        next_refresh: datetime,
    ) -> None:
        """Update refresh timestamps after fetching price.

        Updates the watchlist metadata after successfully refreshing a ticker's price.
        Records when the refresh happened and when the next refresh should occur.

        Args:
            ticker: Ticker that was refreshed
            last_refresh: When the refresh completed
            next_refresh: When the next refresh should occur

        Example:
            >>> now = datetime.now(UTC)
            >>> next_time = now + timedelta(minutes=5)
            >>> await manager.update_refresh_metadata(
            ...     Ticker("AAPL"),
            ...     last_refresh=now,
            ...     next_refresh=next_time
            ... )
        """
        stmt = (
            update(TickerWatchlistModel)
            .where(TickerWatchlistModel.ticker == ticker.symbol)
            .values(
                last_refresh_at=last_refresh,
                next_refresh_at=next_refresh,
                updated_at=datetime.now(UTC),
            )
        )
        await self.session.exec(stmt)
        await self.session.flush()

    async def get_all_active_tickers(self) -> list[Ticker]:
        """Get all active watched tickers.

        Returns all tickers currently marked as active in the watchlist,
        ordered by priority.

        Returns:
            List of active Ticker objects, ordered by priority

        Example:
            >>> active = await manager.get_all_active_tickers()
            >>> print(f"Tracking {len(active)} tickers")
        """
        query = (
            select(TickerWatchlistModel)
            .where(TickerWatchlistModel.is_active == True)  # noqa: E712
            .order_by(TickerWatchlistModel.priority)
        )

        result = await self.session.exec(query)
        models = result.all()

        return [model.to_ticker() for model in models]
