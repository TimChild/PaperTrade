"""Tests for enhanced domain exceptions with structured data."""

from decimal import Decimal

import pytest

from papertrade.domain.exceptions import InsufficientFundsError, InsufficientSharesError
from papertrade.domain.value_objects.money import Money
from papertrade.domain.value_objects.quantity import Quantity


class TestInsufficientFundsError:
    """Tests for InsufficientFundsError with structured data."""

    def test_creates_with_money_objects(self) -> None:
        """Exception should be created with Money objects."""
        available = Money(Decimal("1000.00"), "USD")
        required = Money(Decimal("1500.00"), "USD")

        exc = InsufficientFundsError(available=available, required=required)

        assert exc.available == available
        assert exc.required == required
        # Message uses Money's __str__ which includes $ and commas
        assert "$1,000.00" in exc.message
        assert "$1,500.00" in exc.message

    def test_auto_generates_message(self) -> None:
        """Exception should auto-generate descriptive message."""
        available = Money(Decimal("1000.00"), "USD")
        required = Money(Decimal("1500.00"), "USD")

        exc = InsufficientFundsError(available=available, required=required)

        assert "Insufficient funds" in exc.message
        assert "$1,000.00" in exc.message
        assert "$1,500.00" in exc.message
        assert "$500.00" in exc.message  # shortfall

    def test_accepts_custom_message(self) -> None:
        """Exception should accept custom message."""
        available = Money(Decimal("1000.00"), "USD")
        required = Money(Decimal("1500.00"), "USD")
        custom_msg = "Custom error message"

        exc = InsufficientFundsError(
            available=available, required=required, message=custom_msg
        )

        assert exc.message == custom_msg

    def test_calculates_shortfall(self) -> None:
        """Exception should provide shortfall information in message."""
        available = Money(Decimal("100.00"), "USD")
        required = Money(Decimal("350.75"), "USD")

        exc = InsufficientFundsError(available=available, required=required)

        # Shortfall should be 250.75
        assert "250.75" in exc.message

    def test_rejects_mismatched_currencies(self) -> None:
        """Exception should reject Money objects with different currencies."""
        available = Money(Decimal("1000.00"), "USD")
        required = Money(Decimal("1500.00"), "EUR")

        with pytest.raises(ValueError, match="same currency"):
            InsufficientFundsError(available=available, required=required)

    def test_rejects_non_money_available(self) -> None:
        """Exception should reject non-Money available argument."""
        required = Money(Decimal("1500.00"), "USD")

        with pytest.raises(TypeError, match="available must be Money"):
            InsufficientFundsError(available="not money", required=required)  # type: ignore

    def test_rejects_non_money_required(self) -> None:
        """Exception should reject non-Money required argument."""
        available = Money(Decimal("1000.00"), "USD")

        with pytest.raises(TypeError, match="required must be Money"):
            InsufficientFundsError(available=available, required="not money")  # type: ignore


class TestInsufficientSharesError:
    """Tests for InsufficientSharesError with structured data."""

    def test_creates_with_quantity_objects(self) -> None:
        """Exception should be created with Quantity objects."""
        available = Quantity(Decimal("10"))
        required = Quantity(Decimal("20"))
        ticker = "AAPL"

        exc = InsufficientSharesError(
            ticker=ticker, available=available, required=required
        )

        assert exc.ticker == ticker
        assert exc.available == available
        assert exc.required == required
        assert "AAPL" in exc.message
        assert "10" in exc.message
        assert "20" in exc.message

    def test_auto_generates_message(self) -> None:
        """Exception should auto-generate descriptive message."""
        available = Quantity(Decimal("5"))
        required = Quantity(Decimal("15"))
        ticker = "TSLA"

        exc = InsufficientSharesError(
            ticker=ticker, available=available, required=required
        )

        assert "Insufficient shares" in exc.message
        assert "TSLA" in exc.message
        assert "5" in exc.message
        assert "15" in exc.message
        assert "10" in exc.message  # shortfall

    def test_accepts_custom_message(self) -> None:
        """Exception should accept custom message."""
        available = Quantity(Decimal("5"))
        required = Quantity(Decimal("15"))
        ticker = "GOOGL"
        custom_msg = "Custom share error"

        exc = InsufficientSharesError(
            ticker=ticker, available=available, required=required, message=custom_msg
        )

        assert exc.message == custom_msg

    def test_calculates_shortfall(self) -> None:
        """Exception should provide shortfall information in message."""
        available = Quantity(Decimal("7.5"))
        required = Quantity(Decimal("20.25"))
        ticker = "MSFT"

        exc = InsufficientSharesError(
            ticker=ticker, available=available, required=required
        )

        # Shortfall should be 12.75
        assert "12.75" in exc.message

    def test_rejects_non_quantity_available(self) -> None:
        """Exception should reject non-Quantity available argument."""
        required = Quantity(Decimal("15"))

        with pytest.raises(TypeError, match="available must be Quantity"):
            InsufficientSharesError(
                ticker="AAPL", available="not quantity", required=required  # type: ignore
            )

    def test_rejects_non_quantity_required(self) -> None:
        """Exception should reject non-Quantity required argument."""
        available = Quantity(Decimal("5"))

        with pytest.raises(TypeError, match="required must be Quantity"):
            InsufficientSharesError(
                ticker="AAPL", available=available, required="not quantity"  # type: ignore
            )
