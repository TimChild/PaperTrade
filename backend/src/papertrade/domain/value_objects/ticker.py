"""Ticker value object - Represents a stock symbol."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Ticker:
    """Immutable value object representing a stock ticker symbol.

    Ticker symbols are automatically normalized to uppercase and must be 1-5 letters.
    """

    symbol: str

    def __post_init__(self) -> None:
        """Validate and normalize the ticker symbol."""
        # Normalize to uppercase (using object.__setattr__ since frozen=True)
        normalized = self.symbol.upper()
        object.__setattr__(self, "symbol", normalized)

        # Validate length (1-5 uppercase letters)
        if not (1 <= len(self.symbol) <= 5):
            raise ValueError("Ticker symbol must be 1-5 characters")

        # Validate only letters
        if not self.symbol.isalpha():
            raise ValueError("Ticker symbol must contain only letters")

    def __str__(self) -> str:
        """String representation."""
        return self.symbol

    def __repr__(self) -> str:
        """Developer-friendly representation."""
        return f"Ticker(symbol='{self.symbol}')"
