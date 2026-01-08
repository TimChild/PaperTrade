"""Verify historical price data in the database.

This script checks if historical price data was successfully seeded
in the database and displays a sample of the data.

Usage:
    uv run python scripts/verify_historical_data.py
"""

import asyncio
from datetime import datetime

from sqlalchemy import select

from papertrade.adapters.outbound.models.price_history import PriceHistoryModel
from papertrade.infrastructure.database import async_session_maker, init_db


async def main() -> None:
    """Verify historical price data in database."""
    print("🔍 Verifying historical price data in database...\n")

    # Initialize database
    await init_db()

    async with async_session_maker() as session:
        # Get total count of price records
        count_result = await session.execute(
            select(PriceHistoryModel.id)
        )
        total_count = len(count_result.all())

        if total_count == 0:
            print("❌ No historical price data found in database.")
            print("   Run the seed script first:")
            print("   uv run python scripts/seed_historical_data.py --tickers IBM --days 3")
            return

        print(f"✓ Found {total_count} price records in database\n")

        # Get sample of price records
        result = await session.execute(
            select(PriceHistoryModel).order_by(PriceHistoryModel.timestamp.desc()).limit(10)  # type: ignore[attr-defined]
        )
        prices = result.scalars().all()

        print("📊 Sample of most recent price records:\n")
        print(f"{'Ticker':<10} {'Price':<15} {'Timestamp':<30} {'Source':<15}")
        print("-" * 70)
        for price in prices:
            timestamp_str = price.timestamp.strftime("%Y-%m-%d %H:%M:%S %Z")
            price_str = f"${price.price_amount:.2f}"
            print(f"{price.ticker:<10} {price_str:<15} {timestamp_str:<30} {price.source:<15}")

        # Get tickers with data
        ticker_result = await session.execute(
            select(PriceHistoryModel.ticker).distinct()
        )
        tickers = sorted([row[0] for row in ticker_result.all()])

        print(f"\n✓ Price data available for tickers: {', '.join(tickers)}")
        print("\n✅ Verification complete!")


if __name__ == "__main__":
    asyncio.run(main())
