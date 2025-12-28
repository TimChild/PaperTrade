"""GetPortfolio query - Retrieve portfolio details."""

from dataclasses import dataclass
from uuid import UUID

from papertrade.application.dtos.portfolio_dto import PortfolioDTO
from papertrade.application.ports.portfolio_repository import PortfolioRepository
from papertrade.domain.exceptions import InvalidPortfolioError


@dataclass(frozen=True)
class GetPortfolioQuery:
    """Input data for retrieving a portfolio.

    Attributes:
        portfolio_id: Portfolio to retrieve
    """

    portfolio_id: UUID


@dataclass(frozen=True)
class GetPortfolioResult:
    """Result of retrieving a portfolio.

    Attributes:
        portfolio: Portfolio data
    """

    portfolio: PortfolioDTO


class GetPortfolioHandler:
    """Handler for GetPortfolio query.

    Retrieves portfolio details and converts to DTO for API response.
    """

    def __init__(self, portfolio_repository: PortfolioRepository) -> None:
        """Initialize handler with repository dependency.

        Args:
            portfolio_repository: Repository for portfolio persistence
        """
        self._portfolio_repository = portfolio_repository

    async def execute(self, query: GetPortfolioQuery) -> GetPortfolioResult:
        """Execute the GetPortfolio query.

        Args:
            query: Query with portfolio_id

        Returns:
            Result containing portfolio DTO

        Raises:
            InvalidPortfolioError: If portfolio doesn't exist
        """
        portfolio = await self._portfolio_repository.get(query.portfolio_id)
        if portfolio is None:
            raise InvalidPortfolioError(f"Portfolio not found: {query.portfolio_id}")

        return GetPortfolioResult(portfolio=PortfolioDTO.from_entity(portfolio))
