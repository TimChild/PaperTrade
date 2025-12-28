"""DepositCash command - Add cash to an existing portfolio."""

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from papertrade.application.ports.portfolio_repository import PortfolioRepository
from papertrade.application.ports.transaction_repository import TransactionRepository
from papertrade.domain.entities.transaction import Transaction, TransactionType
from papertrade.domain.exceptions import InvalidPortfolioError
from papertrade.domain.value_objects.money import Money


@dataclass(frozen=True)
class DepositCashCommand:
    """Input data for depositing cash to a portfolio.

    Attributes:
        portfolio_id: Target portfolio
        amount: Cash amount to deposit (decimal)
        currency: Currency code (default "USD")
        notes: Optional description
    """

    portfolio_id: UUID
    amount: Decimal
    currency: str = "USD"
    notes: str | None = None


@dataclass(frozen=True)
class DepositCashResult:
    """Result of depositing cash.

    Attributes:
        transaction_id: ID of the created transaction
    """

    transaction_id: UUID


class DepositCashHandler:
    """Handler for DepositCash command.

    Adds cash to an existing portfolio by creating a DEPOSIT transaction.
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

    def execute(self, command: DepositCashCommand) -> DepositCashResult:
        """Execute the DepositCash command.

        Args:
            command: Command with deposit parameters

        Returns:
            Result containing transaction_id

        Raises:
            InvalidPortfolioError: If portfolio doesn't exist
            InvalidTransactionError: If amount is invalid (zero, negative)
        """
        # Verify portfolio exists
        portfolio = self._portfolio_repository.get(command.portfolio_id)
        if portfolio is None:
            raise InvalidPortfolioError(f"Portfolio not found: {command.portfolio_id}")

        # Create Money value object
        deposit_amount = Money(command.amount, command.currency)

        # Generate transaction ID
        transaction_id = uuid4()

        # Create DEPOSIT transaction
        transaction = Transaction(
            id=transaction_id,
            portfolio_id=command.portfolio_id,
            transaction_type=TransactionType.DEPOSIT,
            timestamp=datetime.now(UTC),
            cash_change=deposit_amount,
            notes=command.notes,
        )

        # Persist transaction
        self._transaction_repository.save(transaction)

        return DepositCashResult(transaction_id=transaction_id)
