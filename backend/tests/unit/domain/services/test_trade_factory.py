"""Tests for trade_factory domain service."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from zebu.domain.entities.transaction import TransactionType
from zebu.domain.exceptions import InsufficientFundsError, InsufficientSharesError
from zebu.domain.services.trade_factory import (
    create_buy_transaction,
    create_sell_transaction,
)
from zebu.domain.value_objects.money import Money
from zebu.domain.value_objects.quantity import Quantity
from zebu.domain.value_objects.ticker import Ticker


class TestCreateBuyTransaction:
    """Tests for create_buy_transaction."""

    def test_create_buy_transaction_success(self) -> None:
        """Valid buy creates correct Transaction with negative cash_change."""
        portfolio_id = uuid4()
        ticker = Ticker("AAPL")
        quantity = Quantity(Decimal("10"))
        price = Money(Decimal("150.00"), "USD")
        cash = Money(Decimal("5000.00"), "USD")
        timestamp = datetime(2024, 6, 15, 14, 30, tzinfo=UTC)

        transaction = create_buy_transaction(
            portfolio_id=portfolio_id,
            ticker=ticker,
            quantity=quantity,
            price_per_share=price,
            cash_balance=cash,
            timestamp=timestamp,
            notes="Test buy",
        )

        assert transaction.portfolio_id == portfolio_id
        assert transaction.transaction_type == TransactionType.BUY
        assert transaction.ticker == ticker
        assert transaction.quantity == quantity
        assert transaction.price_per_share == price
        assert transaction.cash_change == Money(Decimal("-1500.00"), "USD")
        assert transaction.timestamp == timestamp
        assert transaction.notes == "Test buy"

    def test_create_buy_transaction_insufficient_funds(self) -> None:
        """Raises InsufficientFundsError when cash < total cost."""
        portfolio_id = uuid4()
        ticker = Ticker("AAPL")
        quantity = Quantity(Decimal("10"))
        price = Money(Decimal("150.00"), "USD")
        cash = Money(Decimal("1000.00"), "USD")  # Only 1000, need 1500
        timestamp = datetime(2024, 6, 15, 14, 30, tzinfo=UTC)

        with pytest.raises(InsufficientFundsError):
            create_buy_transaction(
                portfolio_id=portfolio_id,
                ticker=ticker,
                quantity=quantity,
                price_per_share=price,
                cash_balance=cash,
                timestamp=timestamp,
            )

    def test_create_buy_transaction_exact_balance(self) -> None:
        """Buying when cash == total cost succeeds."""
        portfolio_id = uuid4()
        ticker = Ticker("AAPL")
        quantity = Quantity(Decimal("10"))
        price = Money(Decimal("150.00"), "USD")
        cash = Money(Decimal("1500.00"), "USD")  # Exactly enough
        timestamp = datetime(2024, 6, 15, 14, 30, tzinfo=UTC)

        transaction = create_buy_transaction(
            portfolio_id=portfolio_id,
            ticker=ticker,
            quantity=quantity,
            price_per_share=price,
            cash_balance=cash,
            timestamp=timestamp,
        )

        assert transaction.transaction_type == TransactionType.BUY
        assert transaction.cash_change == Money(Decimal("-1500.00"), "USD")


class TestCreateSellTransaction:
    """Tests for create_sell_transaction."""

    def test_create_sell_transaction_success(self) -> None:
        """Valid sell creates correct Transaction with positive cash_change."""
        portfolio_id = uuid4()
        ticker = Ticker("AAPL")
        quantity = Quantity(Decimal("5"))
        price = Money(Decimal("160.00"), "USD")
        holding_qty = Quantity(Decimal("10"))
        timestamp = datetime(2024, 6, 15, 14, 30, tzinfo=UTC)

        transaction = create_sell_transaction(
            portfolio_id=portfolio_id,
            ticker=ticker,
            quantity=quantity,
            price_per_share=price,
            current_holding_quantity=holding_qty,
            timestamp=timestamp,
            notes="Test sell",
        )

        assert transaction.portfolio_id == portfolio_id
        assert transaction.transaction_type == TransactionType.SELL
        assert transaction.ticker == ticker
        assert transaction.quantity == quantity
        assert transaction.price_per_share == price
        assert transaction.cash_change == Money(Decimal("800.00"), "USD")
        assert transaction.timestamp == timestamp
        assert transaction.notes == "Test sell"

    def test_create_sell_transaction_insufficient_shares(self) -> None:
        """Raises InsufficientSharesError when holding < quantity."""
        portfolio_id = uuid4()
        ticker = Ticker("AAPL")
        quantity = Quantity(Decimal("20"))
        price = Money(Decimal("160.00"), "USD")
        holding_qty = Quantity(Decimal("10"))  # Only 10, need 20
        timestamp = datetime(2024, 6, 15, 14, 30, tzinfo=UTC)

        with pytest.raises(InsufficientSharesError):
            create_sell_transaction(
                portfolio_id=portfolio_id,
                ticker=ticker,
                quantity=quantity,
                price_per_share=price,
                current_holding_quantity=holding_qty,
                timestamp=timestamp,
            )

    def test_create_sell_transaction_exact_shares(self) -> None:
        """Selling all shares (holding == quantity) succeeds."""
        portfolio_id = uuid4()
        ticker = Ticker("AAPL")
        quantity = Quantity(Decimal("10"))
        price = Money(Decimal("160.00"), "USD")
        holding_qty = Quantity(Decimal("10"))  # Exactly enough
        timestamp = datetime(2024, 6, 15, 14, 30, tzinfo=UTC)

        transaction = create_sell_transaction(
            portfolio_id=portfolio_id,
            ticker=ticker,
            quantity=quantity,
            price_per_share=price,
            current_holding_quantity=holding_qty,
            timestamp=timestamp,
        )

        assert transaction.transaction_type == TransactionType.SELL
        assert transaction.cash_change == Money(Decimal("1600.00"), "USD")
