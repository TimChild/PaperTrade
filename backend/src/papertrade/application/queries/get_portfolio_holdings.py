"""GetPortfolioHoldings query - Calculate current stock positions."""

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from papertrade.application.dtos.holding_dto import HoldingDTO
from papertrade.application.ports.portfolio_repository import PortfolioRepository
from papertrade.application.ports.transaction_repository import TransactionRepository
from papertrade.domain.exceptions import InvalidPortfolioError
from papertrade.domain.services.portfolio_calculator import PortfolioCalculator


@dataclass(frozen=True)
class GetPortfolioHoldingsQuery:
    """Input data for retrieving portfolio holdings.

    Attributes:
        portfolio_id: Portfolio to calculate holdings for
    """

    portfolio_id: UUID


@dataclass(frozen=True)
class GetPortfolioHoldingsResult:
    """Result of retrieving portfolio holdings.

    Attributes:
        portfolio_id: Same as query input
        holdings: Current stock positions
        as_of: Timestamp when holdings were calculated
    """

    portfolio_id: UUID
    holdings: list[HoldingDTO]
    as_of: datetime


class GetPortfolioHoldingsHandler:
    """Handler for GetPortfolioHoldings query.

    Calculates current stock positions by aggregating buy/sell transactions.
    """

    def __init__(
        self,
        portfolio_repository: PortfolioRepository,
        transaction_repository: TransactionRepository,
    ) -> None:
        """Initialize handler with repository dependencies.

        Args:
            portfolio_repository: Repository for portfolio persistence
            transaction_repository: Repository for transaction persistence
        """
        self._portfolio_repository = portfolio_repository
        self._transaction_repository = transaction_repository

    def execute(self, query: GetPortfolioHoldingsQuery) -> GetPortfolioHoldingsResult:
        """Execute the GetPortfolioHoldings query.

        Args:
            query: Query with portfolio_id

        Returns:
            Result containing list of holdings

        Raises:
            InvalidPortfolioError: If portfolio doesn't exist
        """
        # Verify portfolio exists
        portfolio = self._portfolio_repository.get(query.portfolio_id)
        if portfolio is None:
            raise InvalidPortfolioError(f"Portfolio not found: {query.portfolio_id}")

        # Get all transactions
        transactions = self._transaction_repository.get_by_portfolio(query.portfolio_id)

        # Calculate holdings
        holdings = PortfolioCalculator.calculate_holdings(transactions)

        # Convert to DTOs
        holding_dtos = [HoldingDTO.from_entity(holding) for holding in holdings]

        return GetPortfolioHoldingsResult(
            portfolio_id=query.portfolio_id,
            holdings=holding_dtos,
            as_of=datetime.now(UTC),
        )
