"""GetPortfolioBalance query - Calculate current cash balance."""

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from papertrade.application.ports.portfolio_repository import PortfolioRepository
from papertrade.application.ports.transaction_repository import TransactionRepository
from papertrade.domain.exceptions import InvalidPortfolioError
from papertrade.domain.services.portfolio_calculator import PortfolioCalculator
from papertrade.domain.value_objects.money import Money


@dataclass(frozen=True)
class GetPortfolioBalanceQuery:
    """Input data for retrieving portfolio balance.

    Attributes:
        portfolio_id: Portfolio to calculate balance for
    """

    portfolio_id: UUID


@dataclass(frozen=True)
class GetPortfolioBalanceResult:
    """Result of retrieving portfolio balance.

    Attributes:
        portfolio_id: Same as query input
        cash_balance: Current available cash
        currency: Currency of the balance
        as_of: Timestamp when balance was calculated
    """

    portfolio_id: UUID
    cash_balance: Money
    currency: str
    as_of: datetime


class GetPortfolioBalanceHandler:
    """Handler for GetPortfolioBalance query.

    Calculates current cash balance by aggregating all transactions.
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

    def execute(self, query: GetPortfolioBalanceQuery) -> GetPortfolioBalanceResult:
        """Execute the GetPortfolioBalance query.

        Args:
            query: Query with portfolio_id

        Returns:
            Result containing cash balance

        Raises:
            InvalidPortfolioError: If portfolio doesn't exist
        """
        # Verify portfolio exists
        portfolio = self._portfolio_repository.get(query.portfolio_id)
        if portfolio is None:
            raise InvalidPortfolioError(f"Portfolio not found: {query.portfolio_id}")

        # Get all transactions
        transactions = self._transaction_repository.get_by_portfolio(query.portfolio_id)

        # Calculate cash balance
        cash_balance = PortfolioCalculator.calculate_cash_balance(transactions)

        return GetPortfolioBalanceResult(
            portfolio_id=query.portfolio_id,
            cash_balance=cash_balance,
            currency=cash_balance.currency,
            as_of=datetime.now(UTC),
        )
