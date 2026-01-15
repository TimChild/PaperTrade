"""Tests for Money value object."""

from decimal import Decimal

import pytest

from zebu.domain.exceptions import InvalidMoneyError
from zebu.domain.value_objects.money import Money


class TestMoneyConstruction:
    """Tests for Money construction and validation."""

    def test_valid_construction_with_defaults(self) -> None:
        """Should create Money with valid amount and default USD currency."""
        money = Money(Decimal("100.50"))
        assert money.amount == Decimal("100.50")
        assert money.currency == "USD"

    def test_valid_construction_with_custom_currency(self) -> None:
        """Should create Money with valid amount and custom currency."""
        money = Money(Decimal("50.00"), "EUR")
        assert money.amount == Decimal("50.00")
        assert money.currency == "EUR"

    def test_valid_construction_with_zero(self) -> None:
        """Should allow zero amount."""
        money = Money(Decimal("0.00"))
        assert money.amount == Decimal("0.00")

    def test_valid_construction_with_negative(self) -> None:
        """Should allow negative amounts (for debts/losses)."""
        money = Money(Decimal("-50.25"))
        assert money.amount == Decimal("-50.25")

    def test_invalid_construction_with_too_many_decimals(self) -> None:
        """Should raise error for more than 2 decimal places."""
        with pytest.raises(InvalidMoneyError, match="maximum 2 decimal places"):
            Money(Decimal("100.123"))

    def test_invalid_construction_with_nan(self) -> None:
        """Should raise error for NaN amount."""
        with pytest.raises(InvalidMoneyError, match="finite"):
            Money(Decimal("NaN"))

    def test_invalid_construction_with_infinity(self) -> None:
        """Should raise error for infinite amount."""
        with pytest.raises(InvalidMoneyError, match="finite"):
            Money(Decimal("Infinity"))

    def test_invalid_construction_with_invalid_currency(self) -> None:
        """Should raise error for invalid currency code."""
        with pytest.raises(InvalidMoneyError, match="valid ISO 4217"):
            Money(Decimal("100.00"), "INVALID")

    def test_invalid_construction_with_empty_currency(self) -> None:
        """Should raise error for empty currency code."""
        with pytest.raises(InvalidMoneyError, match="valid ISO 4217"):
            Money(Decimal("100.00"), "")


class TestMoneyArithmetic:
    """Tests for Money arithmetic operations."""

    def test_add_same_currency(self) -> None:
        """Should add two Money objects with same currency."""
        m1 = Money(Decimal("100.50"), "USD")
        m2 = Money(Decimal("50.25"), "USD")
        result = m1.add(m2)
        assert result.amount == Decimal("150.75")
        assert result.currency == "USD"

    def test_add_different_currency_raises_error(self) -> None:
        """Should raise error when adding different currencies."""
        m1 = Money(Decimal("100.00"), "USD")
        m2 = Money(Decimal("50.00"), "EUR")
        with pytest.raises(InvalidMoneyError, match="same currency"):
            m1.add(m2)

    def test_subtract_same_currency(self) -> None:
        """Should subtract two Money objects with same currency."""
        m1 = Money(Decimal("100.50"), "USD")
        m2 = Money(Decimal("30.25"), "USD")
        result = m1.subtract(m2)
        assert result.amount == Decimal("70.25")
        assert result.currency == "USD"

    def test_subtract_different_currency_raises_error(self) -> None:
        """Should raise error when subtracting different currencies."""
        m1 = Money(Decimal("100.00"), "USD")
        m2 = Money(Decimal("50.00"), "EUR")
        with pytest.raises(InvalidMoneyError, match="same currency"):
            m1.subtract(m2)

    def test_multiply_by_factor(self) -> None:
        """Should multiply amount by factor."""
        money = Money(Decimal("100.00"), "USD")
        result = money.multiply(Decimal("1.5"))
        assert result.amount == Decimal("150.00")
        assert result.currency == "USD"

    def test_multiply_maintains_precision(self) -> None:
        """Should maintain 2 decimal precision after multiplication."""
        money = Money(Decimal("10.00"), "USD")
        result = money.multiply(Decimal("0.333"))
        # Should round to 2 decimals
        assert result.amount == Decimal("3.33")

    def test_divide_by_divisor(self) -> None:
        """Should divide amount by divisor."""
        money = Money(Decimal("100.00"), "USD")
        result = money.divide(Decimal("4"))
        assert result.amount == Decimal("25.00")
        assert result.currency == "USD"

    def test_divide_by_zero_raises_error(self) -> None:
        """Should raise error when dividing by zero."""
        money = Money(Decimal("100.00"), "USD")
        with pytest.raises(InvalidMoneyError, match="zero"):
            money.divide(Decimal("0"))

    def test_negate(self) -> None:
        """Should return negative of amount."""
        money = Money(Decimal("100.50"), "USD")
        result = money.negate()
        assert result.amount == Decimal("-100.50")
        assert result.currency == "USD"

    def test_absolute_positive(self) -> None:
        """Should return absolute value of positive amount."""
        money = Money(Decimal("100.50"), "USD")
        result = money.absolute()
        assert result.amount == Decimal("100.50")

    def test_absolute_negative(self) -> None:
        """Should return absolute value of negative amount."""
        money = Money(Decimal("-100.50"), "USD")
        result = money.absolute()
        assert result.amount == Decimal("100.50")


class TestMoneyComparison:
    """Tests for Money comparison operations."""

    def test_equality_same_amount_and_currency(self) -> None:
        """Should be equal if amount and currency match."""
        m1 = Money(Decimal("100.00"), "USD")
        m2 = Money(Decimal("100.00"), "USD")
        assert m1 == m2

    def test_inequality_different_amount(self) -> None:
        """Should not be equal if amounts differ."""
        m1 = Money(Decimal("100.00"), "USD")
        m2 = Money(Decimal("50.00"), "USD")
        assert m1 != m2

    def test_inequality_different_currency(self) -> None:
        """Should not be equal if currencies differ."""
        m1 = Money(Decimal("100.00"), "USD")
        m2 = Money(Decimal("100.00"), "EUR")
        assert m1 != m2

    def test_less_than_same_currency(self) -> None:
        """Should compare amounts when same currency."""
        m1 = Money(Decimal("50.00"), "USD")
        m2 = Money(Decimal("100.00"), "USD")
        assert m1 < m2

    def test_less_than_different_currency_raises_error(self) -> None:
        """Should raise error when comparing different currencies."""
        m1 = Money(Decimal("50.00"), "USD")
        m2 = Money(Decimal("100.00"), "EUR")
        with pytest.raises(InvalidMoneyError, match="same currency"):
            _ = m1 < m2

    def test_greater_than_same_currency(self) -> None:
        """Should compare amounts when same currency."""
        m1 = Money(Decimal("100.00"), "USD")
        m2 = Money(Decimal("50.00"), "USD")
        assert m1 > m2

    def test_less_than_or_equal_same_currency(self) -> None:
        """Should compare or equal when same currency."""
        m1 = Money(Decimal("50.00"), "USD")
        m2 = Money(Decimal("100.00"), "USD")
        m3 = Money(Decimal("50.00"), "USD")
        assert m1 <= m2
        assert m1 <= m3

    def test_greater_than_or_equal_same_currency(self) -> None:
        """Should compare or equal when same currency."""
        m1 = Money(Decimal("100.00"), "USD")
        m2 = Money(Decimal("50.00"), "USD")
        m3 = Money(Decimal("100.00"), "USD")
        assert m1 >= m2
        assert m1 >= m3


class TestMoneyPredicates:
    """Tests for Money predicate methods."""

    def test_is_positive(self) -> None:
        """Should return True for positive amounts."""
        assert Money(Decimal("100.00")).is_positive()
        assert not Money(Decimal("0.00")).is_positive()
        assert not Money(Decimal("-100.00")).is_positive()

    def test_is_negative(self) -> None:
        """Should return True for negative amounts."""
        assert Money(Decimal("-100.00")).is_negative()
        assert not Money(Decimal("0.00")).is_negative()
        assert not Money(Decimal("100.00")).is_negative()

    def test_is_zero(self) -> None:
        """Should return True for zero amount."""
        assert Money(Decimal("0.00")).is_zero()
        assert not Money(Decimal("0.01")).is_zero()
        assert not Money(Decimal("-0.01")).is_zero()


class TestMoneyImmutability:
    """Tests that Money is immutable."""

    def test_cannot_modify_amount(self) -> None:
        """Should not be able to modify amount after construction."""
        money = Money(Decimal("100.00"))
        with pytest.raises(AttributeError):
            money.amount = Decimal("200.00")  # type: ignore

    def test_cannot_modify_currency(self) -> None:
        """Should not be able to modify currency after construction."""
        money = Money(Decimal("100.00"), "USD")
        with pytest.raises(AttributeError):
            money.currency = "EUR"  # type: ignore

    def test_operations_create_new_instances(self) -> None:
        """Operations should create new Money instances."""
        m1 = Money(Decimal("100.00"), "USD")
        m2 = m1.add(Money(Decimal("50.00"), "USD"))
        assert m1.amount == Decimal("100.00")  # Original unchanged
        assert m2.amount == Decimal("150.00")  # New instance


class TestMoneyStringRepresentation:
    """Tests for Money string representation."""

    def test_str_representation_usd(self) -> None:
        """Should format USD with $ symbol."""
        money = Money(Decimal("1234.56"), "USD")
        assert str(money) == "$1,234.56"

    def test_str_representation_eur(self) -> None:
        """Should format EUR with € symbol."""
        money = Money(Decimal("1234.56"), "EUR")
        assert str(money) == "€1,234.56"

    def test_str_representation_gbp(self) -> None:
        """Should format GBP with £ symbol."""
        money = Money(Decimal("1234.56"), "GBP")
        assert str(money) == "£1,234.56"

    def test_repr_representation(self) -> None:
        """Should have useful repr."""
        money = Money(Decimal("100.50"), "USD")
        assert "Money" in repr(money)
        assert "100.50" in repr(money)
        assert "USD" in repr(money)
