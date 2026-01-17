"""Backfill historical price data for active tickers.

This script fetches historical daily prices from Alpha Vantage for all active
tickers (from watchlist and recent transactions) and stores them in the database.

Usage:
    python scripts/backfill_prices.py [--days=7]

Environment:
    Must be run from the backend directory with database configured.
"""

import asyncio
import sys
from datetime import UTC, datetime, timedelta

from zebu.adapters.inbound.api.dependencies import get_market_data
from zebu.adapters.outbound.repositories.watchlist_manager import WatchlistManager
from zebu.application.queries.get_active_tickers import (
    GetActiveTickersHandler,
    GetActiveTickersQuery,
)
from zebu.infrastructure.database import async_session_maker


async def backfill_prices(days: int = 7) -> None:
    """Backfill price history for active tickers.

    Args:
        days: Number of days of history to backfill (default: 7)
    """
    print(f"Starting price backfill for last {days} days...")

    # Calculate date range
    end = datetime.now(UTC)
    start = end - timedelta(days=days)

    print(f"Date range: {start.date()} to {end.date()}")

    async with async_session_maker() as session:
        # Get active tickers
        watchlist_manager = WatchlistManager(session)
        watchlist_tickers = await watchlist_manager.get_all_active_tickers()

        query_handler = GetActiveTickersHandler(session)
        query = GetActiveTickersQuery(days=30)
        query_result = await query_handler.execute(query)
        transaction_tickers = query_result.tickers

        # Combine and deduplicate
        all_tickers = list(set(watchlist_tickers + transaction_tickers))

        ticker_symbols = [t.symbol for t in all_tickers]
        print(f"Found {len(all_tickers)} active tickers: {ticker_symbols}")

        # Get market data adapter
        market_data = await get_market_data(session)

        # Fetch history for each ticker
        success_count = 0
        error_count = 0

        for ticker in all_tickers:
            try:
                print(f"\nFetching history for {ticker.symbol}...")

                # This will fetch from API if not in cache and store in database
                history = await market_data.get_price_history(
                    ticker=ticker,
                    start=start,
                    end=end,
                    interval="1day",
                )

                print(f"  ✓ Got {len(history)} price points")
                success_count += 1

                # Commit after each ticker to persist data
                await session.commit()

                # Small delay to respect rate limits (5 calls/min = 12s between calls)
                await asyncio.sleep(12)

            except Exception as e:
                print(f"  ✗ Error: {e}")
                error_count += 1
                # Continue with next ticker

        print("\n=== Backfill Complete ===")
        print(f"Success: {success_count}, Errors: {error_count}")


if __name__ == "__main__":
    # Parse command line arguments
    days = 7
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg.startswith("--days="):
            days = int(arg.split("=")[1])

    # Run backfill
    asyncio.run(backfill_prices(days))
