"""Money value object for representing monetary amounts with currency."""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from zebu.domain.exceptions import InvalidMoneyError

# Valid ISO 4217 currency codes (subset for MVP)
VALID_CURRENCIES = {"USD", "EUR", "GBP", "CAD", "JPY", "AUD"}

# Currency symbols for display
CURRENCY_SYMBOLS = {
    "USD": "$",
    "EUR": "€",
    "GBP": "£",
    "CAD": "CA$",
    "JPY": "¥",
    "AUD": "A$",
}


@dataclass(frozen=True)
class Money:
    """Represents a monetary amount with currency.

    Money is an immutable value object that ensures type safety and prevents
    mixing of different currencies. All arithmetic operations create new instances.

    Attributes:
        amount: The monetary value with maximum 2 decimal places
        currency: ISO 4217 currency code (defaults to USD)

    Raises:
        InvalidMoneyError: If amount has >2 decimals, is NaN/Infinity,
                          or currency code is invalid
    """

    amount: Decimal
    currency: str = "USD"

    def __post_init__(self) -> None:
        """Validate Money constraints after initialization."""
        # Validate currency
        if self.currency not in VALID_CURRENCIES:
            raise InvalidMoneyError(
                f"Currency must be a valid ISO 4217 code. "
                f"Supported currencies: {', '.join(sorted(VALID_CURRENCIES))}"
            )

        # Validate amount is finite
        if not self.amount.is_finite():
            raise InvalidMoneyError("Amount must be finite (not NaN or Infinity)")

        # Validate decimal precision (max 2 decimal places)
        # Check by quantizing - if it changes the value, there are too many decimals
        quantized = self.amount.quantize(Decimal("0.01"))
        if quantized != self.amount:
            raise InvalidMoneyError("Amount must have maximum 2 decimal places")

    def add(self, other: "Money") -> "Money":
        """Add two monetary amounts.

        Args:
            other: Money to add

        Returns:
            New Money with sum of amounts

        Raises:
            InvalidMoneyError: If currencies don't match
        """
        if self.currency != other.currency:
            raise InvalidMoneyError(
                f"Cannot add different currencies: {self.currency} and "
                f"{other.currency}. Both amounts must have the same currency."
            )
        return Money(self.amount + other.amount, self.currency)

    def subtract(self, other: "Money") -> "Money":
        """Subtract other from self.

        Args:
            other: Money to subtract

        Returns:
            New Money with difference

        Raises:
            InvalidMoneyError: If currencies don't match
        """
        if self.currency != other.currency:
            raise InvalidMoneyError(
                f"Cannot subtract different currencies: {self.currency} and "
                f"{other.currency}. Both amounts must have the same currency."
            )
        return Money(self.amount - other.amount, self.currency)

    def multiply(self, factor: Decimal) -> "Money":
        """Multiply amount by factor.

        Args:
            factor: Decimal to multiply by

        Returns:
            New Money with product, rounded to 2 decimals
        """
        result = self.amount * factor
        # Round to 2 decimal places
        rounded = result.quantize(Decimal("0.01"))
        return Money(rounded, self.currency)

    def divide(self, divisor: Decimal) -> "Money":
        """Divide amount by divisor.

        Args:
            divisor: Decimal to divide by

        Returns:
            New Money with quotient, rounded to 2 decimals

        Raises:
            InvalidMoneyError: If divisor is zero
        """
        if divisor == 0:
            raise InvalidMoneyError("Cannot divide by zero")
        try:
            result = self.amount / divisor
            # Round to 2 decimal places
            rounded = result.quantize(Decimal("0.01"))
            return Money(rounded, self.currency)
        except InvalidOperation as e:
            raise InvalidMoneyError(f"Division failed: {e}") from e

    def negate(self) -> "Money":
        """Return negative of amount.

        Returns:
            New Money with negated amount
        """
        return Money(-self.amount, self.currency)

    def absolute(self) -> "Money":
        """Return absolute value of amount.

        Returns:
            New Money with absolute amount
        """
        return Money(abs(self.amount), self.currency)

    def is_positive(self) -> bool:
        """Check if amount is greater than zero.

        Returns:
            True if amount > 0
        """
        return self.amount > 0

    def is_negative(self) -> bool:
        """Check if amount is less than zero.

        Returns:
            True if amount < 0
        """
        return self.amount < 0

    def is_zero(self) -> bool:
        """Check if amount is exactly zero.

        Returns:
            True if amount == 0
        """
        return self.amount == 0

    def __lt__(self, other: "Money") -> bool:
        """Compare if self is less than other.

        Args:
            other: Money to compare

        Returns:
            True if self.amount < other.amount

        Raises:
            InvalidMoneyError: If currencies don't match
        """
        if self.currency != other.currency:
            raise InvalidMoneyError(
                f"Cannot compare different currencies: {self.currency} and "
                f"{other.currency}. Both amounts must have the same currency."
            )
        return self.amount < other.amount

    def __le__(self, other: "Money") -> bool:
        """Compare if self is less than or equal to other."""
        if self.currency != other.currency:
            raise InvalidMoneyError(
                f"Cannot compare different currencies: {self.currency} and "
                f"{other.currency}"
            )
        return self.amount <= other.amount

    def __gt__(self, other: "Money") -> bool:
        """Compare if self is greater than other."""
        if self.currency != other.currency:
            raise InvalidMoneyError(
                f"Cannot compare different currencies: {self.currency} and "
                f"{other.currency}"
            )
        return self.amount > other.amount

    def __ge__(self, other: "Money") -> bool:
        """Compare if self is greater than or equal to other."""
        if self.currency != other.currency:
            raise InvalidMoneyError(
                f"Cannot compare different currencies: {self.currency} and "
                f"{other.currency}"
            )
        return self.amount >= other.amount

    def __str__(self) -> str:
        """Format as currency string.

        Returns:
            Formatted string like "$1,234.56"
        """
        symbol = CURRENCY_SYMBOLS.get(self.currency, self.currency)
        # Format with thousands separator
        formatted_amount = f"{self.amount:,.2f}"
        return f"{symbol}{formatted_amount}"

    def __repr__(self) -> str:
        """Return repr for debugging.

        Returns:
            String like "Money(Decimal('100.50'), 'USD')"
        """
        return f"Money(Decimal('{self.amount}'), '{self.currency}')"
