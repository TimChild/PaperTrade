"""CreatePortfolio command - Create a new portfolio with initial deposit."""

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from papertrade.application.ports.portfolio_repository import PortfolioRepository
from papertrade.application.ports.transaction_repository import TransactionRepository
from papertrade.domain.entities.portfolio import Portfolio
from papertrade.domain.entities.transaction import Transaction, TransactionType
from papertrade.domain.value_objects.money import Money


@dataclass(frozen=True)
class CreatePortfolioCommand:
    """Input data for creating a portfolio.

    Attributes:
        user_id: Owner of the portfolio
        name: Display name for the portfolio
        initial_deposit_amount: Starting cash amount (decimal)
        initial_deposit_currency: Currency code (default "USD")
    """

    user_id: UUID
    name: str
    initial_deposit_amount: Decimal
    initial_deposit_currency: str = "USD"


@dataclass(frozen=True)
class CreatePortfolioResult:
    """Result of creating a portfolio.

    Attributes:
        portfolio_id: ID of the newly created portfolio
        transaction_id: ID of the initial deposit transaction
    """

    portfolio_id: UUID
    transaction_id: UUID


class CreatePortfolioHandler:
    """Handler for CreatePortfolio command.

    Creates a new portfolio with an initial cash deposit. This is the only way
    to create a portfolio - every portfolio must start with some cash.
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

    def execute(self, command: CreatePortfolioCommand) -> CreatePortfolioResult:
        """Execute the CreatePortfolio command.

        Args:
            command: Command with portfolio creation parameters

        Returns:
            Result containing portfolio_id and transaction_id

        Raises:
            InvalidMoneyError: If initial deposit is invalid (zero, negative)
            InvalidPortfolioError: If name is invalid (empty, too long)
        """
        # Create Money value object (validates positive amount)
        initial_deposit = Money(
            command.initial_deposit_amount, command.initial_deposit_currency
        )

        # Generate IDs
        portfolio_id = uuid4()
        transaction_id = uuid4()
        now = datetime.now(UTC)

        # Create Portfolio entity
        portfolio = Portfolio(
            id=portfolio_id,
            user_id=command.user_id,
            name=command.name,
            created_at=now,
        )

        # Create initial DEPOSIT transaction
        transaction = Transaction(
            id=transaction_id,
            portfolio_id=portfolio_id,
            transaction_type=TransactionType.DEPOSIT,
            timestamp=now,
            cash_change=initial_deposit,
            notes="Initial portfolio deposit",
        )

        # Persist both entities
        self._portfolio_repository.save(portfolio)
        self._transaction_repository.save(transaction)

        return CreatePortfolioResult(
            portfolio_id=portfolio_id,
            transaction_id=transaction_id,
        )
