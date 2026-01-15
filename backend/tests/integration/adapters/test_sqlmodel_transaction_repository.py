"""Integration tests for SQLModelTransactionRepository.

Tests the transaction repository with a real SQLite database to verify
append-only semantics and query operations.
"""

from datetime import datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from zebu.adapters.outbound.database.transaction_repository import (
    DuplicateTransactionError,
    SQLModelTransactionRepository,
)
from zebu.domain.entities.transaction import Transaction, TransactionType
from zebu.domain.value_objects.money import Money
from zebu.domain.value_objects.quantity import Quantity
from zebu.domain.value_objects.ticker import Ticker


class TestSQLModelTransactionRepository:
    """Integration tests for SQLModel transaction repository."""

    @pytest.mark.asyncio
    async def test_save_and_get_transaction(self, session):
        """Test saving and retrieving a transaction."""
        # Arrange
        repo = SQLModelTransactionRepository(session)
        transaction = Transaction(
            id=uuid4(),
            portfolio_id=uuid4(),
            transaction_type=TransactionType.DEPOSIT,
            timestamp=datetime.now(),
            cash_change=Money(Decimal("1000.00"), "USD"),
            ticker=None,
            quantity=None,
            price_per_share=None,
            notes="Initial deposit",
        )

        # Act
        await repo.save(transaction)
        await session.commit()

        result = await repo.get(transaction.id)

        # Assert
        assert result is not None
        assert result.id == transaction.id
        assert result.portfolio_id == transaction.portfolio_id
        assert result.transaction_type == TransactionType.DEPOSIT
        assert result.cash_change.amount == Decimal("1000.00")
        assert result.notes == "Initial deposit"

    @pytest.mark.asyncio
    async def test_save_duplicate_transaction_raises_error(self, session):
        """Test saving a transaction with existing ID raises error."""
        # Arrange
        repo = SQLModelTransactionRepository(session)
        transaction_id = uuid4()
        transaction1 = Transaction(
            id=transaction_id,
            portfolio_id=uuid4(),
            transaction_type=TransactionType.DEPOSIT,
            timestamp=datetime.now(),
            cash_change=Money(Decimal("1000.00"), "USD"),
            ticker=None,
            quantity=None,
            price_per_share=None,
        )

        # Act
        await repo.save(transaction1)
        await session.commit()

        # Try to save again with same ID
        transaction2 = Transaction(
            id=transaction_id,
            portfolio_id=uuid4(),
            transaction_type=TransactionType.DEPOSIT,
            timestamp=datetime.now(),
            cash_change=Money(Decimal("500.00"), "USD"),
            ticker=None,
            quantity=None,
            price_per_share=None,
        )

        # Assert
        with pytest.raises(DuplicateTransactionError):
            await repo.save(transaction2)

    @pytest.mark.asyncio
    async def test_get_by_portfolio_returns_chronological_order(self, session):
        """Test transactions are returned in chronological order."""
        # Arrange
        repo = SQLModelTransactionRepository(session)
        portfolio_id = uuid4()

        import time

        t1 = Transaction(
            id=uuid4(),
            portfolio_id=portfolio_id,
            transaction_type=TransactionType.DEPOSIT,
            timestamp=datetime.now(),
            cash_change=Money(Decimal("1000.00"), "USD"),
            ticker=None,
            quantity=None,
            price_per_share=None,
        )
        time.sleep(0.01)
        t2 = Transaction(
            id=uuid4(),
            portfolio_id=portfolio_id,
            transaction_type=TransactionType.BUY,
            timestamp=datetime.now(),
            cash_change=Money(Decimal("-150.00"), "USD"),
            ticker=Ticker("AAPL"),
            quantity=Quantity(Decimal("1.0000")),
            price_per_share=Money(Decimal("150.00"), "USD"),
        )

        # Act
        await repo.save(t1)
        await repo.save(t2)
        await session.commit()

        result = await repo.get_by_portfolio(portfolio_id)

        # Assert
        assert len(result) == 2
        assert result[0].id == t1.id
        assert result[1].id == t2.id

    @pytest.mark.asyncio
    async def test_get_by_portfolio_with_pagination(self, session):
        """Test pagination works correctly."""
        # Arrange
        repo = SQLModelTransactionRepository(session)
        portfolio_id = uuid4()

        # Create 5 transactions
        transactions = []
        for i in range(5):
            t = Transaction(
                id=uuid4(),
                portfolio_id=portfolio_id,
                transaction_type=TransactionType.DEPOSIT,
                timestamp=datetime.now(),
                cash_change=Money(
                    Decimal(f"{(i + 1) * 100}.00"), "USD"
                ),  # Start from 100, not 0
                ticker=None,
                quantity=None,
                price_per_share=None,
            )
            transactions.append(t)
            await repo.save(t)

        await session.commit()

        # Act - Get first 2
        page1 = await repo.get_by_portfolio(portfolio_id, limit=2, offset=0)
        # Get next 2
        page2 = await repo.get_by_portfolio(portfolio_id, limit=2, offset=2)

        # Assert
        assert len(page1) == 2
        assert len(page2) == 2
        assert page1[0].id == transactions[0].id
        assert page2[0].id == transactions[2].id

    @pytest.mark.asyncio
    async def test_get_by_portfolio_with_type_filter(self, session):
        """Test filtering by transaction type."""
        # Arrange
        repo = SQLModelTransactionRepository(session)
        portfolio_id = uuid4()

        deposit = Transaction(
            id=uuid4(),
            portfolio_id=portfolio_id,
            transaction_type=TransactionType.DEPOSIT,
            timestamp=datetime.now(),
            cash_change=Money(Decimal("1000.00"), "USD"),
            ticker=None,
            quantity=None,
            price_per_share=None,
        )
        buy = Transaction(
            id=uuid4(),
            portfolio_id=portfolio_id,
            transaction_type=TransactionType.BUY,
            timestamp=datetime.now(),
            cash_change=Money(Decimal("-150.00"), "USD"),
            ticker=Ticker("AAPL"),
            quantity=Quantity(Decimal("1.0000")),
            price_per_share=Money(Decimal("150.00"), "USD"),
        )

        # Act
        await repo.save(deposit)
        await repo.save(buy)
        await session.commit()

        deposits = await repo.get_by_portfolio(
            portfolio_id, transaction_type=TransactionType.DEPOSIT
        )
        buys = await repo.get_by_portfolio(
            portfolio_id, transaction_type=TransactionType.BUY
        )

        # Assert
        assert len(deposits) == 1
        assert deposits[0].transaction_type == TransactionType.DEPOSIT
        assert len(buys) == 1
        assert buys[0].transaction_type == TransactionType.BUY

    @pytest.mark.asyncio
    async def test_count_by_portfolio(self, session):
        """Test counting transactions for a portfolio."""
        # Arrange
        repo = SQLModelTransactionRepository(session)
        portfolio_id = uuid4()

        # Create 3 transactions
        for _i in range(3):
            t = Transaction(
                id=uuid4(),
                portfolio_id=portfolio_id,
                transaction_type=TransactionType.DEPOSIT,
                timestamp=datetime.now(),
                cash_change=Money(Decimal("100.00"), "USD"),
                ticker=None,
                quantity=None,
                price_per_share=None,
            )
            await repo.save(t)

        await session.commit()

        # Act
        count = await repo.count_by_portfolio(portfolio_id)

        # Assert
        assert count == 3

    @pytest.mark.asyncio
    async def test_count_by_portfolio_with_type_filter(self, session):
        """Test counting with transaction type filter."""
        # Arrange
        repo = SQLModelTransactionRepository(session)
        portfolio_id = uuid4()

        deposit1 = Transaction(
            id=uuid4(),
            portfolio_id=portfolio_id,
            transaction_type=TransactionType.DEPOSIT,
            timestamp=datetime.now(),
            cash_change=Money(Decimal("1000.00"), "USD"),
            ticker=None,
            quantity=None,
            price_per_share=None,
        )
        deposit2 = Transaction(
            id=uuid4(),
            portfolio_id=portfolio_id,
            transaction_type=TransactionType.DEPOSIT,
            timestamp=datetime.now(),
            cash_change=Money(Decimal("500.00"), "USD"),
            ticker=None,
            quantity=None,
            price_per_share=None,
        )
        buy = Transaction(
            id=uuid4(),
            portfolio_id=portfolio_id,
            transaction_type=TransactionType.BUY,
            timestamp=datetime.now(),
            cash_change=Money(Decimal("-150.00"), "USD"),
            ticker=Ticker("AAPL"),
            quantity=Quantity(Decimal("1.0000")),
            price_per_share=Money(Decimal("150.00"), "USD"),
        )

        # Act
        await repo.save(deposit1)
        await repo.save(deposit2)
        await repo.save(buy)
        await session.commit()

        deposit_count = await repo.count_by_portfolio(
            portfolio_id, transaction_type=TransactionType.DEPOSIT
        )
        buy_count = await repo.count_by_portfolio(
            portfolio_id, transaction_type=TransactionType.BUY
        )

        # Assert
        assert deposit_count == 2
        assert buy_count == 1

    @pytest.mark.asyncio
    async def test_save_buy_transaction_with_ticker(self, session):
        """Test saving a BUY transaction with ticker, quantity, and price."""
        # Arrange
        repo = SQLModelTransactionRepository(session)
        transaction = Transaction(
            id=uuid4(),
            portfolio_id=uuid4(),
            transaction_type=TransactionType.BUY,
            timestamp=datetime.now(),
            cash_change=Money(Decimal("-150.00"), "USD"),
            ticker=Ticker("AAPL"),
            quantity=Quantity(Decimal("1.0000")),
            price_per_share=Money(Decimal("150.00"), "USD"),
            notes="Buy Apple stock",
        )

        # Act
        await repo.save(transaction)
        await session.commit()

        result = await repo.get(transaction.id)

        # Assert
        assert result is not None
        assert result.ticker is not None
        assert result.ticker.symbol == "AAPL"
        assert result.quantity is not None
        assert result.quantity.shares == Decimal("1.0000")
        assert result.price_per_share is not None
        assert result.price_per_share.amount == Decimal("150.00")
