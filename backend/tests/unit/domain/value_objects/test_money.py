"""Tests for Money value object."""

from dataclasses import FrozenInstanceError
from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from papertrade.domain.value_objects import Money


class TestMoneyCreation:
    """Test Money value object creation and validation."""

    def test_create_money_with_defaults(self) -> None:
        """Test creating money with default currency."""
        money = Money(Decimal("100.00"), "USD")
        assert money.amount == Decimal("100.00")
        assert money.currency == "USD"

    def test_create_money_with_different_currency(self) -> None:
        """Test creating money with different currency."""
        money = Money(Decimal("50.00"), "EUR")
        assert money.amount == Decimal("50.00")
        assert money.currency == "EUR"

    def test_create_money_invalid_currency_length(self) -> None:
        """Test that invalid currency length raises error."""
        with pytest.raises(ValueError, match="3-letter code"):
            Money(Decimal("100.00"), "US")

    def test_create_money_invalid_currency_case(self) -> None:
        """Test that lowercase currency raises error."""
        with pytest.raises(ValueError, match="uppercase"):
            Money(Decimal("100.00"), "usd")

    def test_create_money_too_many_decimal_places(self) -> None:
        """Test that more than 2 decimal places raises error."""
        with pytest.raises(ValueError, match="at most 2 decimal places"):
            Money(Decimal("100.123"), "USD")

    def test_money_is_immutable(self) -> None:
        """Test that Money is immutable."""
        money = Money(Decimal("100.00"), "USD")
        with pytest.raises(FrozenInstanceError):
            money.amount = Decimal("200.00")  # type: ignore


class TestMoneyArithmetic:
    """Test Money arithmetic operations."""

    def test_add_same_currency(self) -> None:
        """Test adding money with same currency."""
        m1 = Money(Decimal("100.00"), "USD")
        m2 = Money(Decimal("50.00"), "USD")
        result = m1 + m2
        assert result.amount == Decimal("150.00")
        assert result.currency == "USD"

    def test_add_different_currency_raises_error(self) -> None:
        """Test adding money with different currency raises error."""
        m1 = Money(Decimal("100.00"), "USD")
        m2 = Money(Decimal("50.00"), "EUR")
        with pytest.raises(ValueError, match="different currencies"):
            _ = m1 + m2

    def test_subtract_same_currency(self) -> None:
        """Test subtracting money with same currency."""
        m1 = Money(Decimal("100.00"), "USD")
        m2 = Money(Decimal("30.00"), "USD")
        result = m1 - m2
        assert result.amount == Decimal("70.00")
        assert result.currency == "USD"

    def test_subtract_different_currency_raises_error(self) -> None:
        """Test subtracting money with different currency raises error."""
        m1 = Money(Decimal("100.00"), "USD")
        m2 = Money(Decimal("30.00"), "EUR")
        with pytest.raises(ValueError, match="different currencies"):
            _ = m1 - m2

    def test_multiply_by_decimal(self) -> None:
        """Test multiplying money by decimal."""
        money = Money(Decimal("100.00"), "USD")
        result = money * Decimal("1.5")
        assert result.amount == Decimal("150.00")
        assert result.currency == "USD"

    def test_multiply_by_int(self) -> None:
        """Test multiplying money by int."""
        money = Money(Decimal("100.00"), "USD")
        result = money * 2
        assert result.amount == Decimal("200.00")
        assert result.currency == "USD"

    def test_multiply_by_float(self) -> None:
        """Test multiplying money by float."""
        money = Money(Decimal("100.00"), "USD")
        result = money * 0.5
        assert result.amount == Decimal("50.00")
        assert result.currency == "USD"

    def test_rmul_by_decimal(self) -> None:
        """Test reverse multiplication by decimal."""
        money = Money(Decimal("100.00"), "USD")
        result = Decimal("1.5") * money
        assert result.amount == Decimal("150.00")
        assert result.currency == "USD"

    def test_multiplication_quantizes_result(self) -> None:
        """Test that multiplication result is quantized to 2 decimal places."""
        money = Money(Decimal("10.00"), "USD")
        result = money * Decimal("0.333")
        # Should be 3.33, not 3.330
        assert result.amount == Decimal("3.33")

    def test_negate_money(self) -> None:
        """Test negating money."""
        money = Money(Decimal("100.00"), "USD")
        result = -money
        assert result.amount == Decimal("-100.00")
        assert result.currency == "USD"


class TestMoneyComparison:
    """Test Money comparison operations."""

    def test_less_than_same_currency(self) -> None:
        """Test less than comparison with same currency."""
        m1 = Money(Decimal("50.00"), "USD")
        m2 = Money(Decimal("100.00"), "USD")
        assert m1 < m2
        assert not (m2 < m1)

    def test_less_than_different_currency_raises_error(self) -> None:
        """Test less than comparison with different currency raises error."""
        m1 = Money(Decimal("50.00"), "USD")
        m2 = Money(Decimal("100.00"), "EUR")
        with pytest.raises(ValueError, match="different currencies"):
            _ = m1 < m2

    def test_less_than_or_equal(self) -> None:
        """Test less than or equal comparison."""
        m1 = Money(Decimal("50.00"), "USD")
        m2 = Money(Decimal("100.00"), "USD")
        m3 = Money(Decimal("50.00"), "USD")
        assert m1 <= m2
        assert m1 <= m3

    def test_greater_than(self) -> None:
        """Test greater than comparison."""
        m1 = Money(Decimal("100.00"), "USD")
        m2 = Money(Decimal("50.00"), "USD")
        assert m1 > m2
        assert not (m2 > m1)

    def test_greater_than_or_equal(self) -> None:
        """Test greater than or equal comparison."""
        m1 = Money(Decimal("100.00"), "USD")
        m2 = Money(Decimal("50.00"), "USD")
        m3 = Money(Decimal("100.00"), "USD")
        assert m1 >= m2
        assert m1 >= m3

    def test_equality(self) -> None:
        """Test equality comparison."""
        m1 = Money(Decimal("100.00"), "USD")
        m2 = Money(Decimal("100.00"), "USD")
        m3 = Money(Decimal("100.00"), "EUR")
        assert m1 == m2
        assert m1 != m3


class TestMoneyStringRepresentation:
    """Test Money string representations."""

    def test_str(self) -> None:
        """Test string representation."""
        money = Money(Decimal("100.00"), "USD")
        assert str(money) == "USD 100.00"

    def test_repr(self) -> None:
        """Test developer-friendly representation."""
        money = Money(Decimal("100.00"), "USD")
        assert "Money" in repr(money)
        assert "100.00" in repr(money)
        assert "USD" in repr(money)


class TestMoneyPropertyBased:
    """Property-based tests for Money using Hypothesis."""

    @given(
        amount=st.decimals(
            min_value=Decimal("-1000000.00"),
            max_value=Decimal("1000000.00"),
            places=2,
        )
    )
    def test_addition_is_commutative(self, amount: Decimal) -> None:
        """Test that addition is commutative."""
        m1 = Money(amount, "USD")
        m2 = Money(Decimal("50.00"), "USD")
        assert m1 + m2 == m2 + m1

    @given(
        a=st.decimals(
            min_value=Decimal("-1000000.00"),
            max_value=Decimal("1000000.00"),
            places=2,
        ),
        b=st.decimals(
            min_value=Decimal("-1000000.00"),
            max_value=Decimal("1000000.00"),
            places=2,
        ),
        c=st.decimals(
            min_value=Decimal("-1000000.00"),
            max_value=Decimal("1000000.00"),
            places=2,
        ),
    )
    def test_addition_is_associative(self, a: Decimal, b: Decimal, c: Decimal) -> None:
        """Test that addition is associative."""
        m1 = Money(a, "USD")
        m2 = Money(b, "USD")
        m3 = Money(c, "USD")
        assert (m1 + m2) + m3 == m1 + (m2 + m3)

    @given(
        amount=st.decimals(
            min_value=Decimal("-1000000.00"),
            max_value=Decimal("1000000.00"),
            places=2,
        )
    )
    def test_add_then_subtract_identity(self, amount: Decimal) -> None:
        """Test that adding then subtracting gives identity."""
        m1 = Money(amount, "USD")
        m2 = Money(Decimal("50.00"), "USD")
        assert (m1 + m2) - m2 == m1

    @given(
        amount=st.decimals(
            min_value=Decimal("-1000000.00"),
            max_value=Decimal("1000000.00"),
            places=2,
        ),
        scalar=st.decimals(min_value=Decimal("0.01"), max_value=Decimal("100.00")),
    )
    def test_multiplication_result_has_two_decimals(
        self, amount: Decimal, scalar: Decimal
    ) -> None:
        """Test that multiplication result always has exactly 2 decimal places."""
        money = Money(amount, "USD")
        result = money * scalar
        # Check that the decimal part has at most 2 places
        str_result = str(result.amount)
        if "." in str_result:
            decimal_part = str_result.split(".")[1]
            assert len(decimal_part) <= 2
