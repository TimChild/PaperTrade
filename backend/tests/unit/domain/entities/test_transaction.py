"""Tests for Transaction entity."""

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from papertrade.domain.entities import Transaction, TransactionType
from papertrade.domain.value_objects import Money, Quantity, Ticker


class TestTransactionCreation:
    """Test Transaction entity creation and validation."""

    def test_create_deposit_transaction(self) -> None:
        """Test creating a deposit transaction."""
        txn = Transaction(
            id=uuid4(),
            portfolio_id=uuid4(),
            type=TransactionType.DEPOSIT,
            amount=Money(Decimal("1000.00"), "USD"),
            timestamp=datetime.now(UTC),
        )
        assert txn.type == TransactionType.DEPOSIT
        assert txn.amount == Money(Decimal("1000.00"), "USD")
        assert txn.ticker is None
        assert txn.quantity is None
        assert txn.price_per_share is None

    def test_create_withdrawal_transaction(self) -> None:
        """Test creating a withdrawal transaction."""
        txn = Transaction(
            id=uuid4(),
            portfolio_id=uuid4(),
            type=TransactionType.WITHDRAWAL,
            amount=Money(Decimal("500.00"), "USD"),
            timestamp=datetime.now(UTC),
        )
        assert txn.type == TransactionType.WITHDRAWAL
        assert txn.amount == Money(Decimal("500.00"), "USD")

    def test_create_buy_transaction(self) -> None:
        """Test creating a buy transaction."""
        txn = Transaction(
            id=uuid4(),
            portfolio_id=uuid4(),
            type=TransactionType.BUY,
            amount=Money(Decimal("1500.00"), "USD"),
            ticker=Ticker("AAPL"),
            quantity=Quantity(Decimal("10")),
            price_per_share=Money(Decimal("150.00"), "USD"),
            timestamp=datetime.now(UTC),
        )
        assert txn.type == TransactionType.BUY
        assert txn.ticker == Ticker("AAPL")
        assert txn.quantity == Quantity(Decimal("10"))
        assert txn.price_per_share == Money(Decimal("150.00"), "USD")

    def test_create_sell_transaction(self) -> None:
        """Test creating a sell transaction."""
        txn = Transaction(
            id=uuid4(),
            portfolio_id=uuid4(),
            type=TransactionType.SELL,
            amount=Money(Decimal("1600.00"), "USD"),
            ticker=Ticker("AAPL"),
            quantity=Quantity(Decimal("10")),
            price_per_share=Money(Decimal("160.00"), "USD"),
            timestamp=datetime.now(UTC),
        )
        assert txn.type == TransactionType.SELL

    def test_create_buy_without_ticker_raises_error(self) -> None:
        """Test that buy transaction without ticker raises error."""
        with pytest.raises(ValueError, match="requires a ticker"):
            Transaction(
                id=uuid4(),
                portfolio_id=uuid4(),
                type=TransactionType.BUY,
                amount=Money(Decimal("1500.00"), "USD"),
                quantity=Quantity(Decimal("10")),
                price_per_share=Money(Decimal("150.00"), "USD"),
                timestamp=datetime.now(UTC),
            )

    def test_create_buy_without_quantity_raises_error(self) -> None:
        """Test that buy transaction without quantity raises error."""
        with pytest.raises(ValueError, match="requires a quantity"):
            Transaction(
                id=uuid4(),
                portfolio_id=uuid4(),
                type=TransactionType.BUY,
                amount=Money(Decimal("1500.00"), "USD"),
                ticker=Ticker("AAPL"),
                price_per_share=Money(Decimal("150.00"), "USD"),
                timestamp=datetime.now(UTC),
            )

    def test_create_buy_without_price_raises_error(self) -> None:
        """Test that buy transaction without price_per_share raises error."""
        with pytest.raises(ValueError, match="requires a price_per_share"):
            Transaction(
                id=uuid4(),
                portfolio_id=uuid4(),
                type=TransactionType.BUY,
                amount=Money(Decimal("1500.00"), "USD"),
                ticker=Ticker("AAPL"),
                quantity=Quantity(Decimal("10")),
                timestamp=datetime.now(UTC),
            )

    def test_create_deposit_with_ticker_raises_error(self) -> None:
        """Test that deposit transaction with ticker raises error."""
        with pytest.raises(ValueError, match="should not have a ticker"):
            Transaction(
                id=uuid4(),
                portfolio_id=uuid4(),
                type=TransactionType.DEPOSIT,
                amount=Money(Decimal("1000.00"), "USD"),
                ticker=Ticker("AAPL"),
                timestamp=datetime.now(UTC),
            )

    def test_create_deposit_with_quantity_raises_error(self) -> None:
        """Test that deposit transaction with quantity raises error."""
        with pytest.raises(ValueError, match="should not have a quantity"):
            Transaction(
                id=uuid4(),
                portfolio_id=uuid4(),
                type=TransactionType.DEPOSIT,
                amount=Money(Decimal("1000.00"), "USD"),
                quantity=Quantity(Decimal("10")),
                timestamp=datetime.now(UTC),
            )

    def test_create_transaction_negative_amount_raises_error(self) -> None:
        """Test that transaction with negative amount raises error."""
        with pytest.raises(ValueError, match="must be positive"):
            Transaction(
                id=uuid4(),
                portfolio_id=uuid4(),
                type=TransactionType.DEPOSIT,
                amount=Money(Decimal("-100.00"), "USD"),
                timestamp=datetime.now(UTC),
            )

    def test_create_transaction_zero_amount_raises_error(self) -> None:
        """Test that transaction with zero amount raises error."""
        with pytest.raises(ValueError, match="must be positive"):
            Transaction(
                id=uuid4(),
                portfolio_id=uuid4(),
                type=TransactionType.DEPOSIT,
                amount=Money(Decimal("0.00"), "USD"),
                timestamp=datetime.now(UTC),
            )

    def test_transaction_with_notes(self) -> None:
        """Test creating transaction with notes."""
        txn = Transaction(
            id=uuid4(),
            portfolio_id=uuid4(),
            type=TransactionType.DEPOSIT,
            amount=Money(Decimal("1000.00"), "USD"),
            timestamp=datetime.now(UTC),
            notes="Initial deposit",
        )
        assert txn.notes == "Initial deposit"

    def test_transaction_is_immutable(self) -> None:
        """Test that Transaction is immutable."""
        txn = Transaction(
            id=uuid4(),
            portfolio_id=uuid4(),
            type=TransactionType.DEPOSIT,
            amount=Money(Decimal("1000.00"), "USD"),
            timestamp=datetime.now(UTC),
        )
        with pytest.raises(FrozenInstanceError):
            txn.amount = Money(Decimal("2000.00"), "USD")  # type: ignore

    def test_dividend_with_ticker_raises_error(self) -> None:
        """Test that dividend transaction with ticker raises error."""
        with pytest.raises(ValueError, match="should not have a ticker"):
            Transaction(
                id=uuid4(),
                portfolio_id=uuid4(),
                type=TransactionType.DIVIDEND,
                amount=Money(Decimal("50.00"), "USD"),
                ticker=Ticker("AAPL"),
                timestamp=datetime.now(UTC),
            )

    def test_fee_with_quantity_raises_error(self) -> None:
        """Test that fee transaction with quantity raises error."""
        with pytest.raises(ValueError, match="should not have a quantity"):
            Transaction(
                id=uuid4(),
                portfolio_id=uuid4(),
                type=TransactionType.FEE,
                amount=Money(Decimal("10.00"), "USD"),
                quantity=Quantity(Decimal("5")),
                timestamp=datetime.now(UTC),
            )


class TestTransactionStringRepresentation:
    """Test Transaction string representations."""

    def test_str_deposit(self) -> None:
        """Test string representation of deposit."""
        txn = Transaction(
            id=uuid4(),
            portfolio_id=uuid4(),
            type=TransactionType.DEPOSIT,
            amount=Money(Decimal("1000.00"), "USD"),
            timestamp=datetime.now(UTC),
        )
        assert "DEPOSIT" in str(txn)
        assert "1000.00" in str(txn)

    def test_str_buy(self) -> None:
        """Test string representation of buy."""
        txn = Transaction(
            id=uuid4(),
            portfolio_id=uuid4(),
            type=TransactionType.BUY,
            amount=Money(Decimal("1500.00"), "USD"),
            ticker=Ticker("AAPL"),
            quantity=Quantity(Decimal("10")),
            price_per_share=Money(Decimal("150.00"), "USD"),
            timestamp=datetime.now(UTC),
        )
        assert "BUY" in str(txn)
        assert "AAPL" in str(txn)
        assert "10" in str(txn)

    def test_repr(self) -> None:
        """Test developer-friendly representation."""
        txn = Transaction(
            id=uuid4(),
            portfolio_id=uuid4(),
            type=TransactionType.DEPOSIT,
            amount=Money(Decimal("1000.00"), "USD"),
            timestamp=datetime.now(UTC),
        )
        assert "Transaction" in repr(txn)
        assert "DEPOSIT" in repr(txn)
