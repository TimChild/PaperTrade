"""Tests for GetActiveTickers query."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlmodel.ext.asyncio.session import AsyncSession

from zebu.adapters.outbound.database.models import TransactionModel
from zebu.application.queries.get_active_tickers import (
    GetActiveTickersHandler,
    GetActiveTickersQuery,
)
from zebu.domain.value_objects.ticker import Ticker


class TestGetActiveTickers:
    """Tests for GetActiveTickers query handler."""

    async def test_returns_empty_list_when_no_transactions(
        self, test_engine: AsyncSession
    ) -> None:
        """Test that query returns empty list when there are no transactions."""
        # Arrange
        async with AsyncSession(test_engine, expire_on_commit=False) as session:
            handler = GetActiveTickersHandler(session)
            query = GetActiveTickersQuery(days=30)

            # Act
            result = await handler.execute(query)

            # Assert
            assert result.tickers == []
            assert result.days_window == 30

    async def test_returns_tickers_from_recent_transactions(
        self, test_engine: AsyncSession
    ) -> None:
        """Test that query returns tickers from recent transactions."""
        # Arrange
        async with AsyncSession(test_engine, expire_on_commit=False) as session:
            # Create test transactions with different tickers
            portfolio_id = uuid4()
            now = datetime.now(UTC)

            transactions = [
                TransactionModel(
                    id=uuid4(),
                    portfolio_id=portfolio_id,
                    transaction_type="BUY",
                    timestamp=now - timedelta(days=1),
                    cash_change_amount=-100.00,
                    cash_change_currency="USD",
                    ticker="AAPL",
                    quantity=10.0,
                    price_per_share_amount=10.00,
                    price_per_share_currency="USD",
                ),
                TransactionModel(
                    id=uuid4(),
                    portfolio_id=portfolio_id,
                    transaction_type="BUY",
                    timestamp=now - timedelta(days=5),
                    cash_change_amount=-200.00,
                    cash_change_currency="USD",
                    ticker="GOOGL",
                    quantity=5.0,
                    price_per_share_amount=40.00,
                    price_per_share_currency="USD",
                ),
                TransactionModel(
                    id=uuid4(),
                    portfolio_id=portfolio_id,
                    transaction_type="BUY",
                    timestamp=now - timedelta(days=10),
                    cash_change_amount=-300.00,
                    cash_change_currency="USD",
                    ticker="MSFT",
                    quantity=15.0,
                    price_per_share_amount=20.00,
                    price_per_share_currency="USD",
                ),
            ]

            for txn in transactions:
                session.add(txn)
            await session.commit()

            handler = GetActiveTickersHandler(session)
            query = GetActiveTickersQuery(days=30)

            # Act
            result = await handler.execute(query)

            # Assert
            assert len(result.tickers) == 3
            assert Ticker("AAPL") in result.tickers
            assert Ticker("GOOGL") in result.tickers
            assert Ticker("MSFT") in result.tickers

    async def test_filters_by_days_window(self, test_engine: AsyncSession) -> None:
        """Test that query only returns tickers within the specified days window."""
        # Arrange
        async with AsyncSession(test_engine, expire_on_commit=False) as session:
            portfolio_id = uuid4()
            now = datetime.now(UTC)

            # Create transactions: some recent, some old
            transactions = [
                # Recent transaction (within 7 days)
                TransactionModel(
                    id=uuid4(),
                    portfolio_id=portfolio_id,
                    transaction_type="BUY",
                    timestamp=now - timedelta(days=3),
                    cash_change_amount=-100.00,
                    cash_change_currency="USD",
                    ticker="AAPL",
                    quantity=10.0,
                    price_per_share_amount=10.00,
                    price_per_share_currency="USD",
                ),
                # Old transaction (beyond 7 days)
                TransactionModel(
                    id=uuid4(),
                    portfolio_id=portfolio_id,
                    transaction_type="BUY",
                    timestamp=now - timedelta(days=20),
                    cash_change_amount=-200.00,
                    cash_change_currency="USD",
                    ticker="GOOGL",
                    quantity=5.0,
                    price_per_share_amount=40.00,
                    price_per_share_currency="USD",
                ),
            ]

            for txn in transactions:
                session.add(txn)
            await session.commit()

            handler = GetActiveTickersHandler(session)
            query = GetActiveTickersQuery(days=7)

            # Act
            result = await handler.execute(query)

            # Assert
            assert len(result.tickers) == 1
            assert Ticker("AAPL") in result.tickers
            assert Ticker("GOOGL") not in result.tickers

    async def test_deduplicates_tickers(self, test_engine: AsyncSession) -> None:
        """Test that query returns unique tickers even with multiple transactions."""
        # Arrange
        async with AsyncSession(test_engine, expire_on_commit=False) as session:
            portfolio_id = uuid4()
            now = datetime.now(UTC)

            # Create multiple transactions for same ticker
            transactions = [
                TransactionModel(
                    id=uuid4(),
                    portfolio_id=portfolio_id,
                    transaction_type="BUY",
                    timestamp=now - timedelta(days=1),
                    cash_change_amount=-100.00,
                    cash_change_currency="USD",
                    ticker="AAPL",
                    quantity=10.0,
                    price_per_share_amount=10.00,
                    price_per_share_currency="USD",
                ),
                TransactionModel(
                    id=uuid4(),
                    portfolio_id=portfolio_id,
                    transaction_type="SELL",
                    timestamp=now - timedelta(days=2),
                    cash_change_amount=50.00,
                    cash_change_currency="USD",
                    ticker="AAPL",
                    quantity=5.0,
                    price_per_share_amount=10.00,
                    price_per_share_currency="USD",
                ),
                TransactionModel(
                    id=uuid4(),
                    portfolio_id=portfolio_id,
                    transaction_type="BUY",
                    timestamp=now - timedelta(days=3),
                    cash_change_amount=-200.00,
                    cash_change_currency="USD",
                    ticker="AAPL",
                    quantity=20.0,
                    price_per_share_amount=10.00,
                    price_per_share_currency="USD",
                ),
            ]

            for txn in transactions:
                session.add(txn)
            await session.commit()

            handler = GetActiveTickersHandler(session)
            query = GetActiveTickersQuery(days=30)

            # Act
            result = await handler.execute(query)

            # Assert
            assert len(result.tickers) == 1
            assert Ticker("AAPL") in result.tickers

    async def test_ignores_transactions_without_ticker(
        self, test_engine: AsyncSession
    ) -> None:
        """Test that query ignores DEPOSIT/WITHDRAWAL transactions (no ticker)."""
        # Arrange
        async with AsyncSession(test_engine, expire_on_commit=False) as session:
            portfolio_id = uuid4()
            now = datetime.now(UTC)

            transactions = [
                # DEPOSIT (no ticker)
                TransactionModel(
                    id=uuid4(),
                    portfolio_id=portfolio_id,
                    transaction_type="DEPOSIT",
                    timestamp=now - timedelta(days=1),
                    cash_change_amount=1000.00,
                    cash_change_currency="USD",
                    ticker=None,
                    quantity=None,
                    price_per_share_amount=None,
                    price_per_share_currency=None,
                ),
                # BUY (has ticker)
                TransactionModel(
                    id=uuid4(),
                    portfolio_id=portfolio_id,
                    transaction_type="BUY",
                    timestamp=now - timedelta(days=2),
                    cash_change_amount=-100.00,
                    cash_change_currency="USD",
                    ticker="AAPL",
                    quantity=10.0,
                    price_per_share_amount=10.00,
                    price_per_share_currency="USD",
                ),
            ]

            for txn in transactions:
                session.add(txn)
            await session.commit()

            handler = GetActiveTickersHandler(session)
            query = GetActiveTickersQuery(days=30)

            # Act
            result = await handler.execute(query)

            # Assert
            assert len(result.tickers) == 1
            assert Ticker("AAPL") in result.tickers

    async def test_raises_error_for_invalid_days(
        self, test_engine: AsyncSession
    ) -> None:
        """Test that query raises ValueError for invalid days parameter."""
        # Arrange
        async with AsyncSession(test_engine, expire_on_commit=False) as session:
            handler = GetActiveTickersHandler(session)
            query = GetActiveTickersQuery(days=0)

            # Act & Assert
            with pytest.raises(ValueError, match="Days must be at least 1"):
                await handler.execute(query)
