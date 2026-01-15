"""Verify historical price data in the database.

This script checks if historical price data was successfully seeded
in the database and displays a sample of the data.

Usage:
    uv run python scripts/verify_historical_data.py
"""

import asyncio

from sqlmodel import select

from zebu.adapters.outbound.models.price_history import PriceHistoryModel
from zebu.infrastructure.database import async_session_maker, init_db


async def main() -> None:
    """Verify historical price data in database."""
    print("🔍 Verifying historical price data in database...\n")

    # Initialize database
    await init_db()

    async with async_session_maker() as session:
        # Get all price records
        result = await session.exec(select(PriceHistoryModel))
        all_prices = result.all()
        total_count = len(all_prices)

        if total_count == 0:
            print("❌ No historical price data found in database.")
            print("   Run the seed script first:")
            print(
                "   uv run python scripts/seed_historical_data.py "
                "--tickers IBM --days 3"
            )
            return

        print(f"✓ Found {total_count} price records in database\n")

        # Sort by timestamp descending and get first 10
        prices = sorted(all_prices, key=lambda p: p.timestamp, reverse=True)[:10]

        print("📊 Sample of most recent price records:\n")
        print(f"{'Ticker':<10} {'Price':<15} {'Timestamp':<30} {'Source':<15}")
        print("-" * 70)
        for price in prices:
            timestamp_str = price.timestamp.strftime("%Y-%m-%d %H:%M:%S %Z")
            price_str = f"${price.price_amount:.2f}"
            print(
                f"{price.ticker:<10} {price_str:<15} "
                f"{timestamp_str:<30} {price.source:<15}"
            )

        # Get unique tickers
        tickers = sorted(set(p.ticker for p in all_prices))

        print(f"\n✓ Price data available for tickers: {', '.join(tickers)}")
        print("\n✅ Verification complete!")


if __name__ == "__main__":
    asyncio.run(main())
