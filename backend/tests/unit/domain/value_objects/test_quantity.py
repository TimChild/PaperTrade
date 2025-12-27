"""Tests for Quantity value object."""

from dataclasses import FrozenInstanceError
from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from papertrade.domain.value_objects import Quantity


class TestQuantityCreation:
    """Test Quantity value object creation and validation."""

    def test_create_whole_quantity(self) -> None:
        """Test creating quantity with whole number."""
        qty = Quantity(Decimal("100"))
        assert qty.value == Decimal("100")

    def test_create_fractional_quantity(self) -> None:
        """Test creating quantity with fractional shares."""
        qty = Quantity(Decimal("10.5"))
        assert qty.value == Decimal("10.5")

    def test_create_quantity_zero_raises_error(self) -> None:
        """Test that zero quantity raises error."""
        with pytest.raises(ValueError, match="positive"):
            Quantity(Decimal("0"))

    def test_create_negative_quantity_raises_error(self) -> None:
        """Test that negative quantity raises error."""
        with pytest.raises(ValueError, match="positive"):
            Quantity(Decimal("-10"))

    def test_quantity_is_immutable(self) -> None:
        """Test that Quantity is immutable."""
        qty = Quantity(Decimal("100"))
        with pytest.raises(FrozenInstanceError):
            qty.value = Decimal("200")  # type: ignore


class TestQuantityArithmetic:
    """Test Quantity arithmetic operations."""

    def test_add_quantities(self) -> None:
        """Test adding two quantities."""
        q1 = Quantity(Decimal("100"))
        q2 = Quantity(Decimal("50"))
        result = q1 + q2
        assert result.value == Decimal("150")

    def test_subtract_quantities(self) -> None:
        """Test subtracting two quantities."""
        q1 = Quantity(Decimal("100"))
        q2 = Quantity(Decimal("30"))
        result = q1 - q2
        assert result.value == Decimal("70")

    def test_subtract_to_zero_raises_error(self) -> None:
        """Test that subtracting to zero raises error."""
        q1 = Quantity(Decimal("100"))
        q2 = Quantity(Decimal("100"))
        with pytest.raises(ValueError, match="positive"):
            _ = q1 - q2

    def test_subtract_to_negative_raises_error(self) -> None:
        """Test that subtracting to negative raises error."""
        q1 = Quantity(Decimal("50"))
        q2 = Quantity(Decimal("100"))
        with pytest.raises(ValueError, match="positive"):
            _ = q1 - q2

    def test_multiply_by_decimal(self) -> None:
        """Test multiplying quantity by decimal."""
        qty = Quantity(Decimal("100"))
        result = qty * Decimal("1.5")
        assert result.value == Decimal("150")

    def test_multiply_by_int(self) -> None:
        """Test multiplying quantity by int."""
        qty = Quantity(Decimal("100"))
        result = qty * 2
        assert result.value == Decimal("200")

    def test_multiply_by_float(self) -> None:
        """Test multiplying quantity by float."""
        qty = Quantity(Decimal("100"))
        result = qty * 0.5
        assert result.value == Decimal("50")

    def test_rmul_by_decimal(self) -> None:
        """Test reverse multiplication by decimal."""
        qty = Quantity(Decimal("100"))
        result = Decimal("1.5") * qty
        assert result.value == Decimal("150")

    def test_multiply_to_zero_raises_error(self) -> None:
        """Test that multiplying to zero raises error."""
        qty = Quantity(Decimal("100"))
        with pytest.raises(ValueError, match="positive"):
            _ = qty * Decimal("0")

    def test_multiply_to_negative_raises_error(self) -> None:
        """Test that multiplying to negative raises error."""
        qty = Quantity(Decimal("100"))
        with pytest.raises(ValueError, match="positive"):
            _ = qty * Decimal("-1")


class TestQuantityComparison:
    """Test Quantity comparison operations."""

    def test_less_than(self) -> None:
        """Test less than comparison."""
        q1 = Quantity(Decimal("50"))
        q2 = Quantity(Decimal("100"))
        assert q1 < q2
        assert not (q2 < q1)

    def test_less_than_or_equal(self) -> None:
        """Test less than or equal comparison."""
        q1 = Quantity(Decimal("50"))
        q2 = Quantity(Decimal("100"))
        q3 = Quantity(Decimal("50"))
        assert q1 <= q2
        assert q1 <= q3

    def test_greater_than(self) -> None:
        """Test greater than comparison."""
        q1 = Quantity(Decimal("100"))
        q2 = Quantity(Decimal("50"))
        assert q1 > q2
        assert not (q2 > q1)

    def test_greater_than_or_equal(self) -> None:
        """Test greater than or equal comparison."""
        q1 = Quantity(Decimal("100"))
        q2 = Quantity(Decimal("50"))
        q3 = Quantity(Decimal("100"))
        assert q1 >= q2
        assert q1 >= q3

    def test_equality(self) -> None:
        """Test equality comparison."""
        q1 = Quantity(Decimal("100"))
        q2 = Quantity(Decimal("100"))
        q3 = Quantity(Decimal("50"))
        assert q1 == q2
        assert q1 != q3


class TestQuantityStringRepresentation:
    """Test Quantity string representations."""

    def test_str(self) -> None:
        """Test string representation."""
        qty = Quantity(Decimal("100.5"))
        assert str(qty) == "100.5"

    def test_repr(self) -> None:
        """Test developer-friendly representation."""
        qty = Quantity(Decimal("100"))
        assert "Quantity" in repr(qty)
        assert "100" in repr(qty)


class TestQuantityPropertyBased:
    """Property-based tests for Quantity using Hypothesis."""

    @given(
        value=st.decimals(min_value=Decimal("0.01"), max_value=Decimal("1000000.00"))
    )
    def test_addition_is_commutative(self, value: Decimal) -> None:
        """Test that addition is commutative."""
        q1 = Quantity(value)
        q2 = Quantity(Decimal("50"))
        assert q1 + q2 == q2 + q1

    @given(
        a=st.decimals(
            min_value=Decimal("0.01"),
            max_value=Decimal("100000.00"),
            places=2,
        ),
        b=st.decimals(
            min_value=Decimal("0.01"),
            max_value=Decimal("100000.00"),
            places=2,
        ),
        c=st.decimals(
            min_value=Decimal("0.01"),
            max_value=Decimal("100000.00"),
            places=2,
        ),
    )
    def test_addition_is_associative(self, a: Decimal, b: Decimal, c: Decimal) -> None:
        """Test that addition is associative."""
        q1 = Quantity(a)
        q2 = Quantity(b)
        q3 = Quantity(c)
        assert (q1 + q2) + q3 == q1 + (q2 + q3)

    @given(
        value=st.decimals(
            min_value=Decimal("100.00"),
            max_value=Decimal("1000000.00"),
            places=2,
        )
    )
    def test_add_then_subtract_identity(self, value: Decimal) -> None:
        """Test that adding then subtracting gives identity."""
        q1 = Quantity(value)
        q2 = Quantity(Decimal("50.00"))
        # Only test if result would be positive
        if value > Decimal("50.00"):
            assert (q1 + q2) - q2 == q1

    @given(
        value=st.decimals(min_value=Decimal("0.01"), max_value=Decimal("1000000.00")),
        scalar=st.decimals(min_value=Decimal("0.01"), max_value=Decimal("100.00")),
    )
    def test_multiplication_preserves_positivity(
        self, value: Decimal, scalar: Decimal
    ) -> None:
        """Test that multiplication always results in positive quantity."""
        qty = Quantity(value)
        result = qty * scalar
        assert result.value > 0
