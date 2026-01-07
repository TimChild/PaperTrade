"""Seed historical price data from Alpha Vantage for backtest testing.

This script fetches historical daily price data from Alpha Vantage API and stores
it in the database for use in backtest mode. Useful for development and testing.

Usage:
    # Fetch 1 year of history for specific tickers
    uv run python scripts/seed_historical_data.py \
        --tickers AAPL,MSFT,GOOGL,IBM --days 365

    # Fetch 30 days of history for common tickers
    uv run python scripts/seed_historical_data.py --days 30

    # Or via task
    task seed-historical-data

Note: Respects Alpha Vantage rate limits (5 calls/min, 500 calls/day).
"""

import argparse
import asyncio
import os
import sys
from datetime import UTC, datetime, timedelta

import httpx

from papertrade.adapters.outbound.market_data.alpha_vantage_adapter import (
    AlphaVantageAdapter,
)
from papertrade.adapters.outbound.repositories.price_repository import (
    PriceRepository,
)
from papertrade.domain.value_objects.ticker import Ticker
from papertrade.infrastructure.cache.price_cache import PriceCache
from papertrade.infrastructure.database import async_session_maker, init_db
from papertrade.infrastructure.rate_limiter import RateLimiter

# Default tickers to seed (common stocks for testing)
DEFAULT_TICKERS = ["AAPL", "MSFT", "GOOGL", "TSLA", "NVDA"]


async def seed_ticker_history(
    ticker_symbol: str,
    days: int,
    adapter: AlphaVantageAdapter,
) -> int:
    """Fetch and store historical data for a single ticker.

    Args:
        ticker_symbol: Stock ticker symbol (e.g., "AAPL")
        days: Number of days of history to fetch
        adapter: AlphaVantageAdapter instance to use for fetching

    Returns:
        Number of price points fetched and stored
    """
    ticker = Ticker(ticker_symbol)
    end_date = datetime.now(UTC)
    start_date = end_date - timedelta(days=days)

    print(f"  Fetching {ticker_symbol}... ({days} days)", end="", flush=True)

    try:
        # Fetch historical data - adapter will store in database
        history = await adapter.get_price_history(
            ticker,
            start=start_date,
            end=end_date,
            interval="1day",
        )

        print(f" ✓ ({len(history)} data points)")
        return len(history)

    except Exception as e:
        print(f" ✗ Error: {e}")
        return 0


async def main() -> None:
    """Run historical data seeding."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Seed historical price data from Alpha Vantage"
    )
    parser.add_argument(
        "--tickers",
        type=str,
        help=f"Comma-separated list of tickers (default: {','.join(DEFAULT_TICKERS)})",
        default=",".join(DEFAULT_TICKERS),
    )
    parser.add_argument(
        "--days",
        type=int,
        help="Number of days of history to fetch (default: 30)",
        default=30,
    )

    args = parser.parse_args()

    # Parse tickers
    tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
    if not tickers:
        print("❌ Error: No valid tickers provided")
        sys.exit(1)

    print("📊 Starting historical data seeding...")
    print(f"   Tickers: {', '.join(tickers)}")
    print(f"   Days: {args.days}")
    print()

    # Check for API key
    api_key = os.getenv("ALPHA_VANTAGE_API_KEY", "")
    if not api_key or api_key == "your_api_key_here":
        print("⚠️  Warning: ALPHA_VANTAGE_API_KEY not set, using 'demo' key")
        print("   Demo key has limited functionality - set your own key")
        api_key = "demo"

    # Initialize database
    await init_db()

    # Create Alpha Vantage adapter with minimal dependencies
    # Note: We don't need Redis for this one-off script
    async with async_session_maker() as session:
        # Create mock Redis client (not used for this script)
        class MockRedis:
            """Mock Redis client for script usage."""

            async def get(self, key: str) -> None:
                return None

            async def setex(self, key: str, ttl: int, value: str) -> None:
                pass

            async def delete(self, key: str) -> None:
                pass

        # Create adapter
        redis_client = MockRedis()
        http_client = httpx.AsyncClient(timeout=10.0)

        rate_limiter = RateLimiter(
            redis=redis_client,  # type: ignore[arg-type]
            key_prefix="papertrade:ratelimit:alphavantage:seed",
            calls_per_minute=5,  # Alpha Vantage free tier
            calls_per_day=500,
        )

        price_cache = PriceCache(
            redis=redis_client,  # type: ignore[arg-type]
            key_prefix="papertrade:price:seed",
            default_ttl=3600,
        )

        price_repository = PriceRepository(session)

        adapter = AlphaVantageAdapter(
            rate_limiter=rate_limiter,
            price_cache=price_cache,
            http_client=http_client,
            api_key=api_key,
            price_repository=price_repository,
        )

        # Fetch data for each ticker
        total_points = 0
        print("📈 Fetching historical data...")
        print()

        for ticker in tickers:
            points = await seed_ticker_history(ticker, args.days, adapter)
            total_points += points

            # Small delay between tickers to avoid rate limiting
            if ticker != tickers[-1]:  # Don't wait after last ticker
                await asyncio.sleep(12)  # 5 calls/min = 12 sec between calls

        # Clean up
        await http_client.aclose()

    print()
    print(f"✅ Seeding complete! Total data points: {total_points}")
    print()
    print("Data is now available for backtest mode testing.")


if __name__ == "__main__":
    asyncio.run(main())
