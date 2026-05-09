"""Tests for TradeSignal value object."""

from datetime import date
from decimal import Decimal

import pytest

from zebu.domain.exceptions import InvalidTradeSignalError
from zebu.domain.value_objects.money import Money
from zebu.domain.value_objects.quantity import Quantity
from zebu.domain.value_objects.ticker import Ticker
from zebu.domain.value_objects.trade_signal import TradeAction, TradeSignal


class TestTradeSignalConstruction:
    """Tests for TradeSignal construction and validation."""

    def test_valid_construction_with_quantity(self) -> None:
        """Should create a TradeSignal with quantity set."""
        signal = TradeSignal(
            action=TradeAction.BUY,
            ticker=Ticker("AAPL"),
            signal_date=date(2023, 1, 15),
            quantity=Quantity(Decimal("10")),
        )
        assert signal.action == TradeAction.BUY
        assert signal.ticker == Ticker("AAPL")
        assert signal.signal_date == date(2023, 1, 15)
        assert signal.quantity is not None
        assert signal.quantity.shares == Decimal("10")
        assert signal.amount is None

    def test_valid_construction_with_amount(self) -> None:
        """Should create a TradeSignal with amount set."""
        signal = TradeSignal(
            action=TradeAction.SELL,
            ticker=Ticker("TSLA"),
            signal_date=date(2023, 6, 1),
            amount=Money(Decimal("500.00"), "USD"),
        )
        assert signal.action == TradeAction.SELL
        assert signal.ticker == Ticker("TSLA")
        assert signal.amount is not None
        assert signal.amount.amount == Decimal("500.00")
        assert signal.quantity is None

    def test_error_when_both_quantity_and_amount_set(self) -> None:
        """Should raise InvalidTradeSignalError if both quantity and amount set."""
        with pytest.raises(
            InvalidTradeSignalError, match="Exactly one of quantity or amount"
        ):
            TradeSignal(
                action=TradeAction.BUY,
                ticker=Ticker("AAPL"),
                signal_date=date(2023, 1, 15),
                quantity=Quantity(Decimal("10")),
                amount=Money(Decimal("500"), "USD"),
            )

    def test_error_when_neither_quantity_nor_amount_set(self) -> None:
        """Should raise InvalidTradeSignalError if neither quantity nor amount set."""
        with pytest.raises(
            InvalidTradeSignalError, match="Exactly one of quantity or amount"
        ):
            TradeSignal(
                action=TradeAction.BUY,
                ticker=Ticker("AAPL"),
                signal_date=date(2023, 1, 15),
            )

    def test_error_when_quantity_is_zero(self) -> None:
        """Should raise InvalidTradeSignalError if quantity is zero."""
        with pytest.raises(InvalidTradeSignalError, match="quantity must be positive"):
            TradeSignal(
                action=TradeAction.BUY,
                ticker=Ticker("AAPL"),
                signal_date=date(2023, 1, 15),
                quantity=Quantity(Decimal("0")),
            )

    def test_error_when_amount_is_zero(self) -> None:
        """Should raise InvalidTradeSignalError if amount is zero."""
        with pytest.raises(InvalidTradeSignalError, match="amount must be positive"):
            TradeSignal(
                action=TradeAction.SELL,
                ticker=Ticker("MSFT"),
                signal_date=date(2023, 3, 1),
                amount=Money(Decimal("0"), "USD"),
            )


class TestTradeSignalImmutability:
    """Tests for TradeSignal immutability."""

    def test_is_frozen(self) -> None:
        """TradeSignal should be immutable (frozen dataclass)."""
        signal = TradeSignal(
            action=TradeAction.BUY,
            ticker=Ticker("AAPL"),
            signal_date=date(2023, 1, 15),
            quantity=Quantity(Decimal("5")),
        )
        with pytest.raises(AttributeError):
            signal.ticker = Ticker("MSFT")  # type: ignore[misc]
