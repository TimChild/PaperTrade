"""Ticker value object for representing stock ticker symbols."""

import re
from dataclasses import dataclass

from zebu.domain.exceptions import InvalidTickerError

# Pattern for valid ticker symbols: 1-5 uppercase letters
TICKER_PATTERN = re.compile(r"^[A-Z]{1,5}$")


@dataclass(frozen=True)
class Ticker:
    """Represents a stock ticker symbol.

    Ticker is an immutable value object that validates stock symbols.
    Symbols are automatically converted to uppercase.

    Attributes:
        symbol: Stock ticker symbol (1-5 uppercase letters)

    Raises:
        InvalidTickerError: If symbol format is invalid
    """

    symbol: str

    def __post_init__(self) -> None:
        """Validate Ticker constraints after initialization."""
        # Strip whitespace and convert to uppercase
        normalized = self.symbol.strip().upper()

        # Update the symbol field (even though frozen, __post_init__ allows this)
        object.__setattr__(self, "symbol", normalized)

        # Validate format first (more specific error)
        if not TICKER_PATTERN.match(normalized):
            # Check if it's a length issue or character issue
            if len(normalized) == 0 or len(normalized) > 5:
                raise InvalidTickerError(
                    f"Ticker symbol must be 1 to 5 characters long, "
                    f"got: '{self.symbol}'"
                )
            else:
                raise InvalidTickerError(
                    f"Ticker symbol must contain only uppercase letters A-Z, "
                    f"got: '{self.symbol}'"
                )

    def __str__(self) -> str:
        """Return the ticker symbol as string.

        Returns:
            The ticker symbol (e.g., "AAPL")
        """
        return self.symbol

    def __repr__(self) -> str:
        """Return repr for debugging.

        Returns:
            String like "Ticker('AAPL')"
        """
        return f"Ticker('{self.symbol}')"

    def __hash__(self) -> int:
        """Return hash for use in dicts/sets.

        Returns:
            Hash based on symbol
        """
        return hash(self.symbol)
