"""Portfolio entity - Aggregate root for trading activity."""

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from papertrade.domain.exceptions import InvalidPortfolioError


@dataclass(frozen=True)
class Portfolio:
    """Represents a user's investment portfolio.

    Portfolio serves as the aggregate root for all trading activity. It has identity
    and lifecycle, with equality based on ID rather than properties.

    Attributes:
        id: Unique portfolio identifier
        user_id: Owner of the portfolio (immutable)
        name: Display name for portfolio (1-100 characters)
        created_at: When portfolio was created (UTC timezone, immutable)

    Raises:
        InvalidPortfolioError: If invariants are violated
    """

    id: UUID
    user_id: UUID
    name: str
    created_at: datetime

    def __post_init__(self) -> None:
        """Validate Portfolio invariants after initialization."""
        # Validate name is not empty or whitespace
        if not self.name or not self.name.strip():
            raise InvalidPortfolioError("Portfolio name cannot be empty or whitespace")

        # Validate name length
        if len(self.name) > 100:
            raise InvalidPortfolioError(
                f"Portfolio name must be maximum 100 characters, got {len(self.name)}"
            )

        # Validate created_at is not in future
        # Get current time in UTC for comparison
        now = datetime.now(timezone.utc)
        # Handle both timezone-aware and naive datetimes
        created_at_utc = (
            self.created_at
            if self.created_at.tzinfo is not None
            else self.created_at.replace(tzinfo=timezone.utc)
        )

        if created_at_utc > now:
            raise InvalidPortfolioError("Portfolio created_at cannot be in the future")

    def __eq__(self, other: object) -> bool:
        """Equality based on ID only.

        Args:
            other: Object to compare

        Returns:
            True if other is Portfolio with same ID
        """
        if not isinstance(other, Portfolio):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        """Hash based on ID for use in dicts/sets.

        Returns:
            Hash of portfolio ID
        """
        return hash(self.id)

    def __repr__(self) -> str:
        """Return repr for debugging.

        Returns:
            String like "Portfolio(id=UUID('...'), name='My Portfolio')"
        """
        return f"Portfolio(id={self.id}, user_id={self.user_id}, name='{self.name}')"
