"""Money value object - Represents monetary amounts with currency."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal


@dataclass(frozen=True)
class Money:
    """Immutable value object representing a monetary amount.

    All amounts are stored with a precision of 2 decimal places.
    Currency defaults to USD.
    """

    amount: Decimal
    currency: str = "USD"

    def __post_init__(self) -> None:
        """Validate and normalize the money value."""
        # Validate currency is 3 uppercase letters
        if len(self.currency) != 3:
            raise ValueError("Currency must be a 3-letter code")
        if not self.currency.isupper():
            raise ValueError("Currency must be uppercase")

        # Ensure amount has at most 2 decimal places
        quantized = self.amount.quantize(Decimal("0.01"))
        if quantized != self.amount:
            raise ValueError("Amount must have at most 2 decimal places")

    def __add__(self, other: object) -> Money:
        """Add two Money values.

        Raises:
            TypeError: If currencies don't match or other is not Money.
        """
        if not isinstance(other, Money):
            return NotImplemented
        if self.currency != other.currency:
            raise TypeError(
                f"Cannot add different currencies: {self.currency} and {other.currency}"
            )
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: object) -> Money:
        """Subtract two Money values.

        Raises:
            TypeError: If currencies don't match or other is not Money.
        """
        if not isinstance(other, Money):
            return NotImplemented
        if self.currency != other.currency:
            raise TypeError(
                f"Cannot subtract different currencies: "
                f"{self.currency} and {other.currency}"
            )
        return Money(self.amount - other.amount, self.currency)

    def __mul__(self, scalar: Decimal | int | float) -> Money:
        """Multiply Money by a scalar value.

        Args:
            scalar: The multiplier (Decimal, int, or float).

        Returns:
            New Money instance with the multiplied amount.
        """
        if isinstance(scalar, (int, float)):
            scalar = Decimal(str(scalar))

        # Multiply and quantize to 2 decimal places with explicit rounding mode
        result = (self.amount * scalar).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        return Money(result, self.currency)

    def __rmul__(self, scalar: Decimal | int | float) -> Money:
        """Multiply Money by a scalar value (reverse operation)."""
        return self.__mul__(scalar)

    def __lt__(self, other: object) -> bool:
        """Less than comparison.

        Raises:
            TypeError: If currencies don't match or other is not Money.
        """
        if not isinstance(other, Money):
            return NotImplemented
        if self.currency != other.currency:
            raise TypeError(
                f"Cannot compare different currencies: "
                f"{self.currency} and {other.currency}"
            )
        return self.amount < other.amount

    def __le__(self, other: object) -> bool:
        """Less than or equal comparison.

        Raises:
            TypeError: If currencies don't match or other is not Money.
        """
        if not isinstance(other, Money):
            return NotImplemented
        if self.currency != other.currency:
            raise TypeError(
                f"Cannot compare different currencies: "
                f"{self.currency} and {other.currency}"
            )
        return self.amount <= other.amount

    def __gt__(self, other: object) -> bool:
        """Greater than comparison.

        Raises:
            TypeError: If currencies don't match or other is not Money.
        """
        if not isinstance(other, Money):
            return NotImplemented
        if self.currency != other.currency:
            raise TypeError(
                f"Cannot compare different currencies: "
                f"{self.currency} and {other.currency}"
            )
        return self.amount > other.amount

    def __ge__(self, other: object) -> bool:
        """Greater than or equal comparison.

        Raises:
            TypeError: If currencies don't match or other is not Money.
        """
        if not isinstance(other, Money):
            return NotImplemented
        if self.currency != other.currency:
            raise TypeError(
                f"Cannot compare different currencies: "
                f"{self.currency} and {other.currency}"
            )
        return self.amount >= other.amount

    def __neg__(self) -> Money:
        """Negate the money amount."""
        return Money(-self.amount, self.currency)

    def __str__(self) -> str:
        """String representation."""
        return f"{self.currency} {self.amount:.2f}"

    def __repr__(self) -> str:
        """Developer-friendly representation."""
        return f"Money(amount=Decimal('{self.amount}'), currency='{self.currency}')"
