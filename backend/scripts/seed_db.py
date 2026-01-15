"""Seed the database with sample data for local development.

Usage:
    uv run python scripts/seed_db.py
    # Or via task: task db:seed
"""

import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import delete
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from zebu.adapters.outbound.database.models import (
    PortfolioModel,
    TransactionModel,
)
from zebu.adapters.outbound.models.price_history import PriceHistoryModel
from zebu.application.dtos.price_point import PricePoint
from zebu.domain.entities.portfolio import Portfolio
from zebu.domain.entities.transaction import Transaction, TransactionType
from zebu.domain.value_objects.money import Money
from zebu.domain.value_objects.ticker import Ticker
from zebu.infrastructure.database import async_session_maker, init_db


async def clear_existing_data(session: AsyncSession) -> None:
    """Clear all existing data from the database using bulk delete operations."""
    print("  🗑️  Clearing existing data...")

    # Use bulk delete operations for efficiency
    # Delete in order to respect foreign key constraints

    # First delete transactions (they reference portfolios)
    await session.exec(delete(TransactionModel))

    # Then delete portfolios
    await session.exec(delete(PortfolioModel))

    # Delete price history
    await session.exec(delete(PriceHistoryModel))

    await session.commit()
    print("    ✓ Existing data cleared")


async def seed_portfolios(session: AsyncSession) -> None:
    """Create sample portfolios with initial deposits."""
    print("📁 Creating sample portfolios...")

    # Use a consistent user_id for all sample portfolios
    user_id = uuid4()
    # Use single timestamp for all portfolios
    now = datetime.now(UTC)

    # Define portfolio configurations
    portfolio_configs = [
        ("Beginner's Portfolio", Decimal("10000.00")),
        ("Tech Growth Portfolio", Decimal("50000.00")),
        ("Dividend Income Portfolio", Decimal("100000.00")),
    ]

    for name, initial_amount in portfolio_configs:
        portfolio_id = uuid4()
        transaction_id = uuid4()

        portfolio = Portfolio(
            id=portfolio_id,
            user_id=user_id,
            name=name,
            created_at=now,
        )

        transaction = Transaction(
            id=transaction_id,
            portfolio_id=portfolio_id,
            transaction_type=TransactionType.DEPOSIT,
            timestamp=now,
            cash_change=Money(initial_amount, "USD"),
            notes="Initial portfolio deposit",
        )

        session.add(PortfolioModel.from_domain(portfolio))
        session.add(TransactionModel.from_domain(transaction))
        print(f"  ✓ Created: {name} (${initial_amount})")

    await session.commit()


async def seed_price_history(session: AsyncSession) -> None:
    """Create sample price history for common tickers."""
    print("📈 Seeding price history...")

    tickers = [
        (Ticker("AAPL"), Decimal("175.50")),
        (Ticker("GOOGL"), Decimal("142.30")),
        (Ticker("MSFT"), Decimal("378.20")),
        (Ticker("TSLA"), Decimal("238.50")),
        (Ticker("NVDA"), Decimal("495.80")),
    ]

    now = datetime.now(UTC)

    for ticker, base_price in tickers:
        print(f"  Adding history for {ticker.symbol}...")

        # Last 30 days of daily prices
        for days_ago in range(30, -1, -1):
            timestamp = now - timedelta(days=days_ago)

            # Simulate price variation (±3%)
            variation = Decimal(1.0) + (Decimal(days_ago % 7 - 3) / Decimal(100))
            price = (base_price * variation).quantize(Decimal("0.01"))

            price_point = PricePoint(
                ticker=ticker,
                price=Money(price, "USD"),
                timestamp=timestamp,
                source="database",
                interval="1day",
            )

            # Directly insert price history model instead of using repository
            model = PriceHistoryModel.from_price_point(price_point)
            session.add(model)

        print(f"    ✓ Added 31 days of data for {ticker.symbol}")

    await session.commit()


async def main() -> None:
    """Run all seeding operations."""
    print("🌱 Starting database seeding...")
    print()

    # Initialize database (creates tables if needed)
    await init_db()

    async with async_session_maker() as session:
        # Check if database already contains data
        result = await session.exec(select(PortfolioModel))
        existing_portfolio = result.first()

        if existing_portfolio:
            print("⚠️  Database already contains data.")
            response = input("   Clear and re-seed? (yes/no): ")
            if response.lower() != "yes":
                print("   Cancelled.")
                return

            # Clear existing data
            await clear_existing_data(session)
            print()

        # Seed data
        await seed_portfolios(session)
        print()
        await seed_price_history(session)
        print()

    print("✅ Database seeding complete!")
    print()
    print("Sample portfolios created:")
    print("  • Beginner's Portfolio ($10,000)")
    print("  • Tech Growth Portfolio ($50,000)")
    print("  • Dividend Income Portfolio ($100,000)")
    print()
    print("Price history added for:")
    print("  • AAPL, GOOGL, MSFT, TSLA, NVDA (31 days)")
    print()
    print("All portfolios belong to the same user for testing purposes.")


if __name__ == "__main__":
    asyncio.run(main())
