"""Portfolio entity - Represents a user's trading portfolio."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class Portfolio:
    """Entity representing a user's trading portfolio.

    The portfolio's state (cash balance, holdings, total value) is derived
    from its transaction history. The portfolio itself only stores
    identifying information and metadata.
    """

    id: UUID
    user_id: UUID
    name: str
    created_at: datetime

    def __str__(self) -> str:
        """String representation."""
        return f"Portfolio({self.name}, user={self.user_id})"

    def __repr__(self) -> str:
        """Developer-friendly representation."""
        return (
            f"Portfolio(id={self.id}, user_id={self.user_id}, "
            f"name='{self.name}', created_at={self.created_at})"
        )
