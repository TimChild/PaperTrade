"""Tests for TradeSignal value object."""

from datetime import date
from decimal import Decimal

import pytest

from zebu.domain.value_objects.trade_signal import TradeAction, TradeSignal


class TestTradeSignalConstruction:
    """Tests for TradeSignal construction and validation."""

    def test_valid_construction_with_quantity(self) -> None:
        """Should create a TradeSignal with quantity set."""
        signal = TradeSignal(
            action=TradeAction.BUY,
            ticker="AAPL",
            signal_date=date(2023, 1, 15),
            quantity=Decimal("10"),
        )
        assert signal.action == TradeAction.BUY
        assert signal.ticker == "AAPL"
        assert signal.signal_date == date(2023, 1, 15)
        assert signal.quantity == Decimal("10")
        assert signal.amount is None

    def test_valid_construction_with_amount(self) -> None:
        """Should create a TradeSignal with amount set."""
        signal = TradeSignal(
            action=TradeAction.SELL,
            ticker="TSLA",
            signal_date=date(2023, 6, 1),
            amount=Decimal("500.00"),
        )
        assert signal.action == TradeAction.SELL
        assert signal.ticker == "TSLA"
        assert signal.amount == Decimal("500.00")
        assert signal.quantity is None

    def test_error_when_both_quantity_and_amount_set(self) -> None:
        """Should raise ValueError if both quantity and amount are provided."""
        with pytest.raises(ValueError, match="Exactly one of quantity or amount"):
            TradeSignal(
                action=TradeAction.BUY,
                ticker="AAPL",
                signal_date=date(2023, 1, 15),
                quantity=Decimal("10"),
                amount=Decimal("500"),
            )

    def test_error_when_neither_quantity_nor_amount_set(self) -> None:
        """Should raise ValueError if neither quantity nor amount is provided."""
        with pytest.raises(ValueError, match="Exactly one of quantity or amount"):
            TradeSignal(
                action=TradeAction.BUY,
                ticker="AAPL",
                signal_date=date(2023, 1, 15),
            )

    def test_error_when_quantity_is_zero(self) -> None:
        """Should raise ValueError if quantity is zero."""
        with pytest.raises(ValueError, match="quantity must be positive"):
            TradeSignal(
                action=TradeAction.BUY,
                ticker="AAPL",
                signal_date=date(2023, 1, 15),
                quantity=Decimal("0"),
            )

    def test_error_when_quantity_is_negative(self) -> None:
        """Should raise ValueError if quantity is negative."""
        with pytest.raises(ValueError, match="quantity must be positive"):
            TradeSignal(
                action=TradeAction.BUY,
                ticker="AAPL",
                signal_date=date(2023, 1, 15),
                quantity=Decimal("-5"),
            )

    def test_error_when_amount_is_zero(self) -> None:
        """Should raise ValueError if amount is zero."""
        with pytest.raises(ValueError, match="amount must be positive"):
            TradeSignal(
                action=TradeAction.SELL,
                ticker="MSFT",
                signal_date=date(2023, 3, 1),
                amount=Decimal("0"),
            )

    def test_error_when_amount_is_negative(self) -> None:
        """Should raise ValueError if amount is negative."""
        with pytest.raises(ValueError, match="amount must be positive"):
            TradeSignal(
                action=TradeAction.SELL,
                ticker="MSFT",
                signal_date=date(2023, 3, 1),
                amount=Decimal("-100"),
            )


class TestTradeSignalImmutability:
    """Tests for TradeSignal immutability."""

    def test_is_frozen(self) -> None:
        """TradeSignal should be immutable (frozen dataclass)."""
        signal = TradeSignal(
            action=TradeAction.BUY,
            ticker="AAPL",
            signal_date=date(2023, 1, 15),
            quantity=Decimal("5"),
        )
        with pytest.raises(AttributeError):
            signal.ticker = "MSFT"  # type: ignore[misc]
