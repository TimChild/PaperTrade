"""Portfolio DTO for transferring portfolio data across layers."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from zebu.domain.entities.portfolio import Portfolio
from zebu.domain.value_objects.portfolio_type import PortfolioType


@dataclass(frozen=True)
class PortfolioDTO:
    """Data transfer object for Portfolio entity.

    This DTO provides a serialization-friendly representation of a Portfolio,
    suitable for API responses and inter-layer communication.

    Attributes:
        id: Unique portfolio identifier
        user_id: Owner of the portfolio
        name: Display name for portfolio
        created_at: When portfolio was created (ISO 8601 format)
        portfolio_type: Whether this is a paper-trading or backtest portfolio
    """

    id: UUID
    user_id: UUID
    name: str
    created_at: datetime
    portfolio_type: PortfolioType

    @staticmethod
    def from_entity(portfolio: Portfolio) -> "PortfolioDTO":
        """Convert a Portfolio entity to DTO.

        Args:
            portfolio: Domain Portfolio entity

        Returns:
            PortfolioDTO with data copied from entity
        """
        return PortfolioDTO(
            id=portfolio.id,
            user_id=portfolio.user_id,
            name=portfolio.name,
            created_at=portfolio.created_at,
            portfolio_type=portfolio.portfolio_type,
        )
