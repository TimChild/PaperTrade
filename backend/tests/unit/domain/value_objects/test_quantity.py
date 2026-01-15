"""Tests for Quantity value object."""

from decimal import Decimal

import pytest

from zebu.domain.exceptions import InvalidQuantityError
from zebu.domain.value_objects.quantity import Quantity


class TestQuantityConstruction:
    """Tests for Quantity construction and validation."""

    def test_valid_construction_with_whole_number(self) -> None:
        """Should create Quantity with whole number."""
        quantity = Quantity(Decimal("100"))
        assert quantity.shares == Decimal("100")

    def test_valid_construction_with_decimal(self) -> None:
        """Should create Quantity with decimal shares (fractional shares)."""
        quantity = Quantity(Decimal("10.5"))
        assert quantity.shares == Decimal("10.5")

    def test_valid_construction_with_four_decimals(self) -> None:
        """Should allow up to 4 decimal places."""
        quantity = Quantity(Decimal("10.1234"))
        assert quantity.shares == Decimal("10.1234")

    def test_valid_construction_with_zero(self) -> None:
        """Should allow zero shares (closed position)."""
        quantity = Quantity(Decimal("0"))
        assert quantity.shares == Decimal("0")

    def test_invalid_construction_with_negative(self) -> None:
        """Should raise error for negative shares."""
        with pytest.raises(InvalidQuantityError, match="non-negative"):
            Quantity(Decimal("-10"))

    def test_invalid_construction_with_too_many_decimals(self) -> None:
        """Should raise error for more than 4 decimal places."""
        with pytest.raises(InvalidQuantityError, match="maximum 4 decimal places"):
            Quantity(Decimal("10.12345"))

    def test_invalid_construction_with_nan(self) -> None:
        """Should raise error for NaN."""
        with pytest.raises(InvalidQuantityError, match="finite"):
            Quantity(Decimal("NaN"))

    def test_invalid_construction_with_infinity(self) -> None:
        """Should raise error for infinite shares."""
        with pytest.raises(InvalidQuantityError, match="finite"):
            Quantity(Decimal("Infinity"))


class TestQuantityArithmetic:
    """Tests for Quantity arithmetic operations."""

    def test_add_quantities(self) -> None:
        """Should add two quantities."""
        q1 = Quantity(Decimal("10.5"))
        q2 = Quantity(Decimal("5.25"))
        result = q1.add(q2)
        assert result.shares == Decimal("15.75")

    def test_subtract_quantities(self) -> None:
        """Should subtract two quantities."""
        q1 = Quantity(Decimal("10.5"))
        q2 = Quantity(Decimal("5.25"))
        result = q1.subtract(q2)
        assert result.shares == Decimal("5.25")

    def test_subtract_to_zero(self) -> None:
        """Should allow subtraction to exactly zero."""
        q1 = Quantity(Decimal("10.0"))
        q2 = Quantity(Decimal("10.0"))
        result = q1.subtract(q2)
        assert result.shares == Decimal("0.0")

    def test_subtract_negative_result_raises_error(self) -> None:
        """Should raise error if subtraction would result in negative."""
        q1 = Quantity(Decimal("5.0"))
        q2 = Quantity(Decimal("10.0"))
        with pytest.raises(InvalidQuantityError, match="non-negative"):
            q1.subtract(q2)

    def test_multiply_by_factor(self) -> None:
        """Should multiply shares by factor."""
        quantity = Quantity(Decimal("10.0"))
        result = quantity.multiply(Decimal("1.5"))
        assert result.shares == Decimal("15.0000")

    def test_multiply_by_zero(self) -> None:
        """Should allow multiplication by zero."""
        quantity = Quantity(Decimal("10.0"))
        result = quantity.multiply(Decimal("0"))
        assert result.shares == Decimal("0.0000")

    def test_multiply_by_negative_raises_error(self) -> None:
        """Should raise error when multiplying by negative factor."""
        quantity = Quantity(Decimal("10.0"))
        with pytest.raises(InvalidQuantityError, match="non-negative"):
            quantity.multiply(Decimal("-1"))


class TestQuantityComparison:
    """Tests for Quantity comparison operations."""

    def test_equality(self) -> None:
        """Should be equal if shares match."""
        q1 = Quantity(Decimal("10.5"))
        q2 = Quantity(Decimal("10.5"))
        assert q1 == q2

    def test_inequality(self) -> None:
        """Should not be equal if shares differ."""
        q1 = Quantity(Decimal("10.5"))
        q2 = Quantity(Decimal("5.0"))
        assert q1 != q2

    def test_less_than(self) -> None:
        """Should compare quantities."""
        q1 = Quantity(Decimal("5.0"))
        q2 = Quantity(Decimal("10.0"))
        assert q1 < q2

    def test_greater_than(self) -> None:
        """Should compare quantities."""
        q1 = Quantity(Decimal("10.0"))
        q2 = Quantity(Decimal("5.0"))
        assert q1 > q2

    def test_less_than_or_equal(self) -> None:
        """Should compare or equal."""
        q1 = Quantity(Decimal("5.0"))
        q2 = Quantity(Decimal("10.0"))
        q3 = Quantity(Decimal("5.0"))
        assert q1 <= q2
        assert q1 <= q3

    def test_greater_than_or_equal(self) -> None:
        """Should compare or equal."""
        q1 = Quantity(Decimal("10.0"))
        q2 = Quantity(Decimal("5.0"))
        q3 = Quantity(Decimal("10.0"))
        assert q1 >= q2
        assert q1 >= q3


class TestQuantityPredicates:
    """Tests for Quantity predicate methods."""

    def test_is_zero(self) -> None:
        """Should return True for zero shares."""
        assert Quantity(Decimal("0")).is_zero()
        assert not Quantity(Decimal("0.0001")).is_zero()

    def test_is_positive(self) -> None:
        """Should return True for positive shares."""
        assert Quantity(Decimal("10.0")).is_positive()
        assert not Quantity(Decimal("0")).is_positive()


class TestQuantityImmutability:
    """Tests that Quantity is immutable."""

    def test_cannot_modify_shares(self) -> None:
        """Should not be able to modify shares after construction."""
        quantity = Quantity(Decimal("10.0"))
        with pytest.raises(AttributeError):
            quantity.shares = Decimal("20.0")  # type: ignore

    def test_operations_create_new_instances(self) -> None:
        """Operations should create new Quantity instances."""
        q1 = Quantity(Decimal("10.0"))
        q2 = q1.add(Quantity(Decimal("5.0")))
        assert q1.shares == Decimal("10.0")  # Original unchanged
        assert q2.shares == Decimal("15.0")  # New instance


class TestQuantityStringRepresentation:
    """Tests for Quantity string representation."""

    def test_str_representation(self) -> None:
        """Should format with 4 decimal places and 'shares'."""
        quantity = Quantity(Decimal("123.5"))
        assert str(quantity) == "123.5000 shares"

    def test_str_representation_zero(self) -> None:
        """Should format zero correctly."""
        quantity = Quantity(Decimal("0"))
        assert str(quantity) == "0.0000 shares"

    def test_repr_representation(self) -> None:
        """Should have useful repr."""
        quantity = Quantity(Decimal("10.5"))
        assert "Quantity" in repr(quantity)
        assert "10.5" in repr(quantity)
