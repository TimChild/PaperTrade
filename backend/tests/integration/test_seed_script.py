"""Integration tests for database seeding script."""

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from scripts.seed_db import clear_existing_data, seed_portfolios, seed_price_history
from zebu.adapters.outbound.database.models import (
    PortfolioModel,
    TransactionModel,
)
from zebu.adapters.outbound.models.price_history import PriceHistoryModel


@pytest_asyncio.fixture
async def session(test_engine: AsyncEngine) -> AsyncSession:
    """Create a test database session."""
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        yield session


class TestSeedPortfolios:
    """Tests for portfolio seeding functionality."""

    async def test_creates_three_portfolios(self, session: AsyncSession) -> None:
        """Test that seed_portfolios creates exactly 3 portfolios."""
        await seed_portfolios(session)

        result = await session.exec(select(PortfolioModel))
        portfolios = result.all()

        assert len(portfolios) == 3

    async def test_creates_portfolios_with_correct_names(
        self, session: AsyncSession
    ) -> None:
        """Test that portfolios have expected names."""
        await seed_portfolios(session)

        result = await session.exec(select(PortfolioModel))
        portfolios = result.all()

        names = {p.name for p in portfolios}
        expected_names = {
            "Beginner's Portfolio",
            "Tech Growth Portfolio",
            "Dividend Income Portfolio",
        }

        assert names == expected_names

    async def test_creates_portfolios_with_correct_cash_amounts(
        self, session: AsyncSession
    ) -> None:
        """Test that portfolios have correct initial deposits."""
        await seed_portfolios(session)

        # Get transactions
        result = await session.exec(select(TransactionModel))
        transactions = result.all()

        # Should have 3 deposit transactions
        assert len(transactions) == 3

        # Check amounts
        amounts = {float(t.cash_change_amount) for t in transactions}
        expected_amounts = {10000.00, 50000.00, 100000.00}

        assert amounts == expected_amounts

    async def test_creates_matching_transactions(self, session: AsyncSession) -> None:
        """Test that each portfolio has a matching DEPOSIT transaction."""
        await seed_portfolios(session)

        result = await session.exec(select(PortfolioModel))
        portfolios = result.all()

        result = await session.exec(select(TransactionModel))
        transactions = result.all()

        # Each portfolio should have exactly one transaction
        portfolio_ids = {p.id for p in portfolios}
        transaction_portfolio_ids = {t.portfolio_id for t in transactions}

        assert portfolio_ids == transaction_portfolio_ids

        # All transactions should be DEPOSIT type
        assert all(t.transaction_type == "DEPOSIT" for t in transactions)

    async def test_uses_same_user_id(self, session: AsyncSession) -> None:
        """Test that all portfolios belong to the same user."""
        await seed_portfolios(session)

        result = await session.exec(select(PortfolioModel))
        portfolios = result.all()

        user_ids = {p.user_id for p in portfolios}

        # All portfolios should have the same user_id
        assert len(user_ids) == 1

    async def test_uses_same_timestamp(self, session: AsyncSession) -> None:
        """Test that all portfolios use the same creation timestamp."""
        await seed_portfolios(session)

        result = await session.exec(select(PortfolioModel))
        portfolios = result.all()

        timestamps = {p.created_at for p in portfolios}

        # All portfolios should have the same timestamp
        assert len(timestamps) == 1


class TestSeedPriceHistory:
    """Tests for price history seeding functionality."""

    async def test_creates_price_history(self, session: AsyncSession) -> None:
        """Test that seed_price_history creates price records."""
        await seed_price_history(session)

        result = await session.exec(select(PriceHistoryModel))
        prices = result.all()

        # Should have 5 tickers * 31 days = 155 records
        assert len(prices) == 155

    async def test_creates_prices_for_expected_tickers(
        self, session: AsyncSession
    ) -> None:
        """Test that prices are created for all expected tickers."""
        await seed_price_history(session)

        result = await session.exec(select(PriceHistoryModel))
        prices = result.all()

        tickers = {p.ticker for p in prices}
        expected_tickers = {"AAPL", "GOOGL", "MSFT", "TSLA", "NVDA"}

        assert tickers == expected_tickers

    async def test_creates_31_days_per_ticker(self, session: AsyncSession) -> None:
        """Test that exactly 31 price points are created per ticker."""
        await seed_price_history(session)

        result = await session.exec(select(PriceHistoryModel))
        prices = result.all()

        # Count prices per ticker
        ticker_counts = {}
        for price in prices:
            ticker_counts[price.ticker] = ticker_counts.get(price.ticker, 0) + 1

        # Each ticker should have exactly 31 price points
        assert all(count == 31 for count in ticker_counts.values())

    async def test_price_amounts_have_two_decimals(self, session: AsyncSession) -> None:
        """Test that all prices have exactly 2 decimal places."""
        await seed_price_history(session)

        result = await session.exec(select(PriceHistoryModel))
        prices = result.all()

        for price in prices:
            # Convert to string and check decimal places
            price_str = str(price.price_amount)
            if "." in price_str:
                decimal_part = price_str.split(".")[1]
                assert len(decimal_part) <= 2

    async def test_uses_database_source_and_1day_interval(
        self, session: AsyncSession
    ) -> None:
        """Test that prices use 'database' source and '1day' interval."""
        await seed_price_history(session)

        result = await session.exec(select(PriceHistoryModel))
        prices = result.all()

        assert all(p.source == "database" for p in prices)
        assert all(p.interval == "1day" for p in prices)


class TestClearExistingData:
    """Tests for data clearing functionality."""

    async def test_clears_portfolios(self, session: AsyncSession) -> None:
        """Test that clear_existing_data removes all portfolios."""
        # First seed some data
        await seed_portfolios(session)

        # Verify data exists
        result = await session.exec(select(PortfolioModel))
        assert len(result.all()) > 0

        # Clear data
        await clear_existing_data(session)

        # Verify data is gone
        result = await session.exec(select(PortfolioModel))
        assert len(result.all()) == 0

    async def test_clears_transactions(self, session: AsyncSession) -> None:
        """Test that clear_existing_data removes all transactions."""
        # First seed some data
        await seed_portfolios(session)

        # Verify data exists
        result = await session.exec(select(TransactionModel))
        assert len(result.all()) > 0

        # Clear data
        await clear_existing_data(session)

        # Verify data is gone
        result = await session.exec(select(TransactionModel))
        assert len(result.all()) == 0

    async def test_clears_price_history(self, session: AsyncSession) -> None:
        """Test that clear_existing_data removes all price history."""
        # First seed some data
        await seed_price_history(session)

        # Verify data exists
        result = await session.exec(select(PriceHistoryModel))
        assert len(result.all()) > 0

        # Clear data
        await clear_existing_data(session)

        # Verify data is gone
        result = await session.exec(select(PriceHistoryModel))
        assert len(result.all()) == 0

    async def test_respects_foreign_key_constraints(
        self, session: AsyncSession
    ) -> None:
        """Test that clearing respects foreign key constraints.
        (transactions before portfolios).
        """
        # Seed portfolios (which creates transactions)
        await seed_portfolios(session)

        # This should not raise foreign key constraint errors
        await clear_existing_data(session)

        # Verify everything is cleared
        result = await session.exec(select(PortfolioModel))
        assert len(result.all()) == 0

        result = await session.exec(select(TransactionModel))
        assert len(result.all()) == 0
