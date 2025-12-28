"""Tests for Transaction entity."""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from papertrade.domain.entities.transaction import Transaction, TransactionType
from papertrade.domain.exceptions import InvalidTransactionError
from papertrade.domain.value_objects.money import Money
from papertrade.domain.value_objects.quantity import Quantity
from papertrade.domain.value_objects.ticker import Ticker


class TestTransactionTypeEnum:
    """Tests for TransactionType enumeration."""

    def test_transaction_types_exist(self) -> None:
        """Should have all four transaction types."""
        assert TransactionType.DEPOSIT
        assert TransactionType.WITHDRAWAL
        assert TransactionType.BUY
        assert TransactionType.SELL

    def test_transaction_type_values(self) -> None:
        """Transaction types should have string values."""
        assert isinstance(TransactionType.DEPOSIT.value, str)
        assert isinstance(TransactionType.WITHDRAWAL.value, str)
        assert isinstance(TransactionType.BUY.value, str)
        assert isinstance(TransactionType.SELL.value, str)


class TestTransactionConstruction:
    """Tests for Transaction construction with type-specific validation."""

    def test_valid_deposit_transaction(self) -> None:
        """Should create valid DEPOSIT transaction."""
        transaction = Transaction(
            id=uuid4(),
            portfolio_id=uuid4(),
            transaction_type=TransactionType.DEPOSIT,
            timestamp=datetime.now(timezone.utc),
            cash_change=Money(Decimal("1000.00")),
            ticker=None,
            quantity=None,
            price_per_share=None,
            notes="Initial deposit",
        )

        assert transaction.transaction_type == TransactionType.DEPOSIT
        assert transaction.cash_change.amount == Decimal("1000.00")
        assert transaction.ticker is None
        assert transaction.quantity is None
        assert transaction.price_per_share is None

    def test_valid_withdrawal_transaction(self) -> None:
        """Should create valid WITHDRAWAL transaction."""
        transaction = Transaction(
            id=uuid4(),
            portfolio_id=uuid4(),
            transaction_type=TransactionType.WITHDRAWAL,
            timestamp=datetime.now(timezone.utc),
            cash_change=Money(Decimal("-500.00")),
            ticker=None,
            quantity=None,
            price_per_share=None,
            notes="Withdraw funds",
        )

        assert transaction.transaction_type == TransactionType.WITHDRAWAL
        assert transaction.cash_change.amount == Decimal("-500.00")

    def test_valid_buy_transaction(self) -> None:
        """Should create valid BUY transaction."""
        quantity = Quantity(Decimal("10"))
        price = Money(Decimal("150.00"))
        # cash_change should be negative (money leaving)
        cash_change = Money(Decimal("-1500.00"))

        transaction = Transaction(
            id=uuid4(),
            portfolio_id=uuid4(),
            transaction_type=TransactionType.BUY,
            timestamp=datetime.now(timezone.utc),
            cash_change=cash_change,
            ticker=Ticker("AAPL"),
            quantity=quantity,
            price_per_share=price,
            notes=None,
        )

        assert transaction.transaction_type == TransactionType.BUY
        assert transaction.ticker == Ticker("AAPL")
        assert transaction.quantity == quantity
        assert transaction.price_per_share == price
        assert transaction.cash_change == cash_change

    def test_valid_sell_transaction(self) -> None:
        """Should create valid SELL transaction."""
        quantity = Quantity(Decimal("5"))
        price = Money(Decimal("160.00"))
        # cash_change should be positive (money coming in)
        cash_change = Money(Decimal("800.00"))

        transaction = Transaction(
            id=uuid4(),
            portfolio_id=uuid4(),
            transaction_type=TransactionType.SELL,
            timestamp=datetime.now(timezone.utc),
            cash_change=cash_change,
            ticker=Ticker("AAPL"),
            quantity=quantity,
            price_per_share=price,
            notes=None,
        )

        assert transaction.transaction_type == TransactionType.SELL
        assert transaction.cash_change.is_positive()

    def test_invalid_deposit_with_negative_cash_change(self) -> None:
        """DEPOSIT must have positive cash_change."""
        with pytest.raises(InvalidTransactionError, match="positive cash"):
            Transaction(
                id=uuid4(),
                portfolio_id=uuid4(),
                transaction_type=TransactionType.DEPOSIT,
                timestamp=datetime.now(timezone.utc),
                cash_change=Money(Decimal("-100.00")),
                ticker=None,
                quantity=None,
                price_per_share=None,
            )

    def test_invalid_withdrawal_with_positive_cash_change(self) -> None:
        """WITHDRAWAL must have negative cash_change."""
        with pytest.raises(InvalidTransactionError, match="negative cash"):
            Transaction(
                id=uuid4(),
                portfolio_id=uuid4(),
                transaction_type=TransactionType.WITHDRAWAL,
                timestamp=datetime.now(timezone.utc),
                cash_change=Money(Decimal("100.00")),
                ticker=None,
                quantity=None,
                price_per_share=None,
            )

    def test_invalid_buy_without_ticker(self) -> None:
        """BUY must have ticker."""
        with pytest.raises(InvalidTransactionError, match="ticker"):
            Transaction(
                id=uuid4(),
                portfolio_id=uuid4(),
                transaction_type=TransactionType.BUY,
                timestamp=datetime.now(timezone.utc),
                cash_change=Money(Decimal("-100.00")),
                ticker=None,
                quantity=Quantity(Decimal("1")),
                price_per_share=Money(Decimal("100.00")),
            )

    def test_invalid_buy_without_quantity(self) -> None:
        """BUY must have quantity."""
        with pytest.raises(InvalidTransactionError, match="quantity"):
            Transaction(
                id=uuid4(),
                portfolio_id=uuid4(),
                transaction_type=TransactionType.BUY,
                timestamp=datetime.now(timezone.utc),
                cash_change=Money(Decimal("-100.00")),
                ticker=Ticker("AAPL"),
                quantity=None,
                price_per_share=Money(Decimal("100.00")),
            )

    def test_invalid_buy_without_price(self) -> None:
        """BUY must have price_per_share."""
        with pytest.raises(InvalidTransactionError, match="price"):
            Transaction(
                id=uuid4(),
                portfolio_id=uuid4(),
                transaction_type=TransactionType.BUY,
                timestamp=datetime.now(timezone.utc),
                cash_change=Money(Decimal("-100.00")),
                ticker=Ticker("AAPL"),
                quantity=Quantity(Decimal("1")),
                price_per_share=None,
            )

    def test_invalid_buy_with_positive_cash_change(self) -> None:
        """BUY must have negative cash_change (money leaving)."""
        with pytest.raises(InvalidTransactionError, match="negative cash"):
            Transaction(
                id=uuid4(),
                portfolio_id=uuid4(),
                transaction_type=TransactionType.BUY,
                timestamp=datetime.now(timezone.utc),
                cash_change=Money(Decimal("100.00")),
                ticker=Ticker("AAPL"),
                quantity=Quantity(Decimal("1")),
                price_per_share=Money(Decimal("100.00")),
            )

    def test_invalid_buy_cash_change_not_matching_calculation(self) -> None:
        """BUY cash_change must equal -(quantity × price)."""
        with pytest.raises(InvalidTransactionError, match="must equal"):
            Transaction(
                id=uuid4(),
                portfolio_id=uuid4(),
                transaction_type=TransactionType.BUY,
                timestamp=datetime.now(timezone.utc),
                cash_change=Money(Decimal("-99.00")),  # Should be -100.00
                ticker=Ticker("AAPL"),
                quantity=Quantity(Decimal("1")),
                price_per_share=Money(Decimal("100.00")),
            )

    def test_invalid_sell_with_negative_cash_change(self) -> None:
        """SELL must have positive cash_change (money coming in)."""
        with pytest.raises(InvalidTransactionError, match="positive cash"):
            Transaction(
                id=uuid4(),
                portfolio_id=uuid4(),
                transaction_type=TransactionType.SELL,
                timestamp=datetime.now(timezone.utc),
                cash_change=Money(Decimal("-100.00")),
                ticker=Ticker("AAPL"),
                quantity=Quantity(Decimal("1")),
                price_per_share=Money(Decimal("100.00")),
            )

    def test_invalid_sell_cash_change_not_matching_calculation(self) -> None:
        """SELL cash_change must equal (quantity × price)."""
        with pytest.raises(InvalidTransactionError, match="must equal"):
            Transaction(
                id=uuid4(),
                portfolio_id=uuid4(),
                transaction_type=TransactionType.SELL,
                timestamp=datetime.now(timezone.utc),
                cash_change=Money(Decimal("99.00")),  # Should be 100.00
                ticker=Ticker("AAPL"),
                quantity=Quantity(Decimal("1")),
                price_per_share=Money(Decimal("100.00")),
            )

    def test_invalid_deposit_with_ticker(self) -> None:
        """DEPOSIT should not have ticker."""
        with pytest.raises(InvalidTransactionError, match="must not have"):
            Transaction(
                id=uuid4(),
                portfolio_id=uuid4(),
                transaction_type=TransactionType.DEPOSIT,
                timestamp=datetime.now(timezone.utc),
                cash_change=Money(Decimal("100.00")),
                ticker=Ticker("AAPL"),
                quantity=None,
                price_per_share=None,
            )

    def test_notes_can_be_none(self) -> None:
        """Notes should be optional."""
        transaction = Transaction(
            id=uuid4(),
            portfolio_id=uuid4(),
            transaction_type=TransactionType.DEPOSIT,
            timestamp=datetime.now(timezone.utc),
            cash_change=Money(Decimal("100.00")),
            ticker=None,
            quantity=None,
            price_per_share=None,
            notes=None,
        )
        assert transaction.notes is None

    def test_notes_with_max_length(self) -> None:
        """Notes should allow up to 500 characters."""
        long_note = "A" * 500
        transaction = Transaction(
            id=uuid4(),
            portfolio_id=uuid4(),
            transaction_type=TransactionType.DEPOSIT,
            timestamp=datetime.now(timezone.utc),
            cash_change=Money(Decimal("100.00")),
            ticker=None,
            quantity=None,
            price_per_share=None,
            notes=long_note,
        )
        assert transaction.notes == long_note

    def test_invalid_notes_too_long(self) -> None:
        """Notes should not exceed 500 characters."""
        with pytest.raises(InvalidTransactionError, match="maximum 500"):
            Transaction(
                id=uuid4(),
                portfolio_id=uuid4(),
                transaction_type=TransactionType.DEPOSIT,
                timestamp=datetime.now(timezone.utc),
                cash_change=Money(Decimal("100.00")),
                ticker=None,
                quantity=None,
                price_per_share=None,
                notes="A" * 501,
            )


class TestTransactionEquality:
    """Tests for Transaction equality semantics."""

    def test_equality_based_on_id(self) -> None:
        """Two transactions with same ID should be equal."""
        transaction_id = uuid4()
        portfolio_id = uuid4()
        timestamp = datetime.now(timezone.utc)

        t1 = Transaction(
            id=transaction_id,
            portfolio_id=portfolio_id,
            transaction_type=TransactionType.DEPOSIT,
            timestamp=timestamp,
            cash_change=Money(Decimal("100.00")),
        )
        t2 = Transaction(
            id=transaction_id,
            portfolio_id=portfolio_id,
            transaction_type=TransactionType.DEPOSIT,
            timestamp=timestamp,
            cash_change=Money(Decimal("200.00")),  # Different amount
        )

        assert t1 == t2

    def test_inequality_different_ids(self) -> None:
        """Transactions with different IDs should not be equal."""
        portfolio_id = uuid4()
        timestamp = datetime.now(timezone.utc)

        t1 = Transaction(
            id=uuid4(),
            portfolio_id=portfolio_id,
            transaction_type=TransactionType.DEPOSIT,
            timestamp=timestamp,
            cash_change=Money(Decimal("100.00")),
        )
        t2 = Transaction(
            id=uuid4(),
            portfolio_id=portfolio_id,
            transaction_type=TransactionType.DEPOSIT,
            timestamp=timestamp,
            cash_change=Money(Decimal("100.00")),
        )

        assert t1 != t2


class TestTransactionOrdering:
    """Tests for Transaction ordering by timestamp."""

    def test_ordering_by_timestamp(self) -> None:
        """Transactions should be ordered by timestamp."""
        from datetime import timedelta

        portfolio_id = uuid4()
        now = datetime.now(timezone.utc)

        t1 = Transaction(
            id=uuid4(),
            portfolio_id=portfolio_id,
            transaction_type=TransactionType.DEPOSIT,
            timestamp=now,
            cash_change=Money(Decimal("100.00")),
        )
        t2 = Transaction(
            id=uuid4(),
            portfolio_id=portfolio_id,
            transaction_type=TransactionType.DEPOSIT,
            timestamp=now + timedelta(seconds=1),
            cash_change=Money(Decimal("100.00")),
        )

        assert t1 < t2
        assert t2 > t1


class TestTransactionImmutability:
    """Tests that Transaction is completely immutable."""

    def test_cannot_modify_any_field(self) -> None:
        """Should not be able to modify any field after construction."""
        transaction = Transaction(
            id=uuid4(),
            portfolio_id=uuid4(),
            transaction_type=TransactionType.DEPOSIT,
            timestamp=datetime.now(timezone.utc),
            cash_change=Money(Decimal("100.00")),
        )

        with pytest.raises(AttributeError):
            transaction.cash_change = Money(Decimal("200.00"))  # type: ignore


class TestTransactionStringRepresentation:
    """Tests for Transaction string representation."""

    def test_repr_representation(self) -> None:
        """Should have useful repr."""
        transaction = Transaction(
            id=uuid4(),
            portfolio_id=uuid4(),
            transaction_type=TransactionType.BUY,
            timestamp=datetime.now(timezone.utc),
            cash_change=Money(Decimal("-1000.00")),
            ticker=Ticker("AAPL"),
            quantity=Quantity(Decimal("10")),
            price_per_share=Money(Decimal("100.00")),
        )
        repr_str = repr(transaction)
        assert "Transaction" in repr_str
        assert "BUY" in repr_str
        assert "AAPL" in repr_str
