"""Quantity value object for representing share quantities."""

from dataclasses import dataclass
from decimal import Decimal

from papertrade.domain.exceptions import InvalidQuantityError


@dataclass(frozen=True)
class Quantity:
    """Represents a number of shares in a holding or trade.

    Quantity is an immutable value object that ensures shares are always
    non-negative and properly validated. Supports fractional shares with
    up to 4 decimal places.

    Attributes:
        shares: Number of shares (must be non-negative, max 4 decimal places)

    Raises:
        InvalidQuantityError: If shares are negative, have >4 decimals,
                             or are NaN/Infinity
    """

    shares: Decimal

    def __post_init__(self) -> None:
        """Validate Quantity constraints after initialization."""
        # Validate shares are finite
        if not self.shares.is_finite():
            raise InvalidQuantityError("Shares must be finite (not NaN or Infinity)")

        # Validate non-negative
        if self.shares < 0:
            raise InvalidQuantityError(
                f"Shares must be non-negative, got: {self.shares}"
            )

        # Validate decimal precision (max 4 decimal places)
        quantized = self.shares.quantize(Decimal("0.0001"))
        if quantized != self.shares:
            raise InvalidQuantityError("Shares must have maximum 4 decimal places")

    def add(self, other: "Quantity") -> "Quantity":
        """Add two quantities.

        Args:
            other: Quantity to add

        Returns:
            New Quantity with sum of shares
        """
        return Quantity(self.shares + other.shares)

    def subtract(self, other: "Quantity") -> "Quantity":
        """Subtract other from self.

        Args:
            other: Quantity to subtract

        Returns:
            New Quantity with difference

        Raises:
            InvalidQuantityError: If result would be negative
        """
        result = self.shares - other.shares
        # This will raise InvalidQuantityError if negative
        return Quantity(result)

    def multiply(self, factor: Decimal) -> "Quantity":
        """Multiply shares by factor.

        Args:
            factor: Decimal to multiply by (must be non-negative)

        Returns:
            New Quantity with product, maintaining 4 decimal precision

        Raises:
            InvalidQuantityError: If factor is negative
        """
        if factor < 0:
            raise InvalidQuantityError(
                f"Factor must be non-negative, got: {factor}"
            )
        result = self.shares * factor
        # Quantize to 4 decimal places
        quantized = result.quantize(Decimal("0.0001"))
        return Quantity(quantized)

    def is_zero(self) -> bool:
        """Check if shares are exactly zero.

        Returns:
            True if shares == 0
        """
        return self.shares == 0

    def is_positive(self) -> bool:
        """Check if shares are greater than zero.

        Returns:
            True if shares > 0
        """
        return self.shares > 0

    def __lt__(self, other: "Quantity") -> bool:
        """Compare if self is less than other."""
        return self.shares < other.shares

    def __le__(self, other: "Quantity") -> bool:
        """Compare if self is less than or equal to other."""
        return self.shares <= other.shares

    def __gt__(self, other: "Quantity") -> bool:
        """Compare if self is greater than other."""
        return self.shares > other.shares

    def __ge__(self, other: "Quantity") -> bool:
        """Compare if self is greater than or equal to other."""
        return self.shares >= other.shares

    def __str__(self) -> str:
        """Format as share count string.

        Returns:
            Formatted string like "123.5000 shares"
        """
        # Format with 4 decimal places
        formatted = f"{self.shares:.4f}"
        return f"{formatted} shares"

    def __repr__(self) -> str:
        """Return repr for debugging.

        Returns:
            String like "Quantity(Decimal('10.5000'))"
        """
        return f"Quantity(Decimal('{self.shares}'))"
