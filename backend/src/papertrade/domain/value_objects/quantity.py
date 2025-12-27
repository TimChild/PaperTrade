"""Quantity value object - Represents share quantities."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Quantity:
    """Immutable value object representing a quantity of shares.

    Supports fractional shares and must be positive.
    """

    value: Decimal

    def __post_init__(self) -> None:
        """Validate the quantity value."""
        if self.value <= 0:
            raise ValueError("Quantity must be positive")

    def __add__(self, other: object) -> Quantity:
        """Add two Quantity values.

        Raises:
            TypeError: If other is not a Quantity.
        """
        if not isinstance(other, Quantity):
            return NotImplemented
        return Quantity(self.value + other.value)

    def __sub__(self, other: object) -> Quantity:
        """Subtract two Quantity values.

        Raises:
            ArithmeticError: If result would not be positive.
            TypeError: If other is not a Quantity.
        """
        if not isinstance(other, Quantity):
            return NotImplemented
        result = self.value - other.value
        if result <= 0:
            raise ArithmeticError("Resulting quantity must be positive")
        return Quantity(result)

    def __mul__(self, scalar: Decimal | int | float) -> Quantity:
        """Multiply Quantity by a scalar value.

        Raises:
            ArithmeticError: If result would not be positive.
        """
        if isinstance(scalar, (int, float)):
            scalar = Decimal(str(scalar))

        result = self.value * scalar
        if result <= 0:
            raise ArithmeticError("Resulting quantity must be positive")
        return Quantity(result)

    def __rmul__(self, scalar: Decimal | int | float) -> Quantity:
        """Multiply Quantity by a scalar value (reverse operation)."""
        return self.__mul__(scalar)

    def __lt__(self, other: object) -> bool:
        """Less than comparison."""
        if not isinstance(other, Quantity):
            return NotImplemented
        return self.value < other.value

    def __le__(self, other: object) -> bool:
        """Less than or equal comparison."""
        if not isinstance(other, Quantity):
            return NotImplemented
        return self.value <= other.value

    def __gt__(self, other: object) -> bool:
        """Greater than comparison."""
        if not isinstance(other, Quantity):
            return NotImplemented
        return self.value > other.value

    def __ge__(self, other: object) -> bool:
        """Greater than or equal comparison."""
        if not isinstance(other, Quantity):
            return NotImplemented
        return self.value >= other.value

    def __str__(self) -> str:
        """String representation."""
        return str(self.value)

    def __repr__(self) -> str:
        """Developer-friendly representation."""
        return f"Quantity(value=Decimal('{self.value}'))"
