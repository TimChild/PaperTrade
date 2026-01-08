"""WithdrawCash command - Remove cash from a portfolio with validation."""

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from papertrade.application.ports.portfolio_repository import PortfolioRepository
from papertrade.application.ports.transaction_repository import TransactionRepository
from papertrade.domain.entities.transaction import Transaction, TransactionType
from papertrade.domain.exceptions import InsufficientFundsError, InvalidPortfolioError
from papertrade.domain.services.portfolio_calculator import PortfolioCalculator
from papertrade.domain.value_objects.money import Money


@dataclass(frozen=True)
class WithdrawCashCommand:
    """Input data for withdrawing cash from a portfolio.

    Attributes:
        portfolio_id: Target portfolio
        amount: Cash amount to withdraw (decimal)
        currency: Currency code (default "USD")
        notes: Optional description
    """

    portfolio_id: UUID
    amount: Decimal
    currency: str = "USD"
    notes: str | None = None


@dataclass(frozen=True)
class WithdrawCashResult:
    """Result of withdrawing cash.

    Attributes:
        transaction_id: ID of the created transaction
    """

    transaction_id: UUID


class WithdrawCashHandler:
    """Handler for WithdrawCash command.

    Removes cash from a portfolio by creating a WITHDRAWAL transaction.
    Validates that sufficient funds are available before creating the transaction.
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

    async def execute(self, command: WithdrawCashCommand) -> WithdrawCashResult:
        """Execute the WithdrawCash command.

        Args:
            command: Command with withdrawal parameters

        Returns:
            Result containing transaction_id

        Raises:
            InvalidPortfolioError: If portfolio doesn't exist
            InvalidTransactionError: If amount is invalid (zero, negative)
            InsufficientFundsError: If withdrawal exceeds available balance
        """
        # Verify portfolio exists
        portfolio = await self._portfolio_repository.get(command.portfolio_id)
        if portfolio is None:
            raise InvalidPortfolioError(f"Portfolio not found: {command.portfolio_id}")

        # Create Money value object for withdrawal
        withdrawal_amount = Money(command.amount, command.currency)

        # Get all transactions to calculate current balance
        transactions = await self._transaction_repository.get_by_portfolio(
            command.portfolio_id
        )

        # Calculate current balance
        current_balance = PortfolioCalculator.calculate_cash_balance(transactions)

        # Validate sufficient funds
        if current_balance < withdrawal_amount:
            raise InsufficientFundsError(
                available=current_balance,
                required=withdrawal_amount,
            )

        # Generate transaction ID
        transaction_id = uuid4()

        # Create WITHDRAWAL transaction (negative cash_change)
        transaction = Transaction(
            id=transaction_id,
            portfolio_id=command.portfolio_id,
            transaction_type=TransactionType.WITHDRAWAL,
            timestamp=datetime.now(UTC),
            cash_change=withdrawal_amount.negate(),  # Negative for withdrawal
            notes=command.notes,
        )

        # Persist transaction
        await self._transaction_repository.save(transaction)

        return WithdrawCashResult(transaction_id=transaction_id)
