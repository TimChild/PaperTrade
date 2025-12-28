"""ListTransactions query - Retrieve transaction history with pagination."""

from dataclasses import dataclass
from uuid import UUID

from papertrade.application.dtos.transaction_dto import TransactionDTO
from papertrade.application.ports.portfolio_repository import PortfolioRepository
from papertrade.application.ports.transaction_repository import TransactionRepository
from papertrade.domain.entities.transaction import TransactionType
from papertrade.domain.exceptions import InvalidPortfolioError


@dataclass(frozen=True)
class ListTransactionsQuery:
    """Input data for retrieving transaction history.

    Attributes:
        portfolio_id: Portfolio to retrieve transactions for
        limit: Maximum transactions to return (default 100, max 1000)
        offset: Number of transactions to skip (default 0)
        transaction_type: Filter by type (None = all types)
    """

    portfolio_id: UUID
    limit: int = 100
    offset: int = 0
    transaction_type: TransactionType | None = None


@dataclass(frozen=True)
class ListTransactionsResult:
    """Result of retrieving transaction history.

    Attributes:
        portfolio_id: Same as query input
        transactions: List of transaction DTOs
        total_count: Total matching transactions (for pagination)
        limit: Applied limit
        offset: Applied offset
    """

    portfolio_id: UUID
    transactions: list[TransactionDTO]
    total_count: int
    limit: int
    offset: int


class ListTransactionsHandler:
    """Handler for ListTransactions query.

    Retrieves transaction history with pagination support.
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

    def execute(self, query: ListTransactionsQuery) -> ListTransactionsResult:
        """Execute the ListTransactions query.

        Args:
            query: Query with portfolio_id and pagination parameters

        Returns:
            Result containing paginated transaction list

        Raises:
            InvalidPortfolioError: If portfolio doesn't exist
            ValueError: If pagination parameters are invalid
        """
        # Verify portfolio exists
        portfolio = self._portfolio_repository.get(query.portfolio_id)
        if portfolio is None:
            raise InvalidPortfolioError(f"Portfolio not found: {query.portfolio_id}")

        # Validate pagination parameters
        if query.limit < 1 or query.limit > 1000:
            raise ValueError("Limit must be between 1 and 1000")
        if query.offset < 0:
            raise ValueError("Offset must be non-negative")

        # Get transactions with pagination
        transactions = self._transaction_repository.get_by_portfolio(
            portfolio_id=query.portfolio_id,
            limit=query.limit,
            offset=query.offset,
            transaction_type=query.transaction_type,
        )

        # Get total count
        total_count = self._transaction_repository.count_by_portfolio(
            portfolio_id=query.portfolio_id,
            transaction_type=query.transaction_type,
        )

        # Convert to DTOs
        transaction_dtos = [
            TransactionDTO.from_entity(transaction) for transaction in transactions
        ]

        return ListTransactionsResult(
            portfolio_id=query.portfolio_id,
            transactions=transaction_dtos,
            total_count=total_count,
            limit=query.limit,
            offset=query.offset,
        )
