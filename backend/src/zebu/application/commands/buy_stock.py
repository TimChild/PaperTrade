"""BuyStock command - Purchase shares with balance validation."""

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from zebu.application.ports.portfolio_repository import PortfolioRepository
from zebu.application.ports.transaction_repository import TransactionRepository
from zebu.domain.entities.transaction import Transaction, TransactionType
from zebu.domain.exceptions import InsufficientFundsError, InvalidPortfolioError
from zebu.domain.services.portfolio_calculator import PortfolioCalculator
from zebu.domain.value_objects.money import Money
from zebu.domain.value_objects.quantity import Quantity
from zebu.domain.value_objects.ticker import Ticker


@dataclass(frozen=True)
class BuyStockCommand:
    """Input data for buying stock.

    Attributes:
        portfolio_id: Target portfolio
        ticker_symbol: Stock symbol to buy
        quantity_shares: Number of shares to buy
        price_per_share_amount: Price per share (decimal)
        price_per_share_currency: Currency code (default "USD")
        notes: Optional description
        as_of: Optional timestamp for backtesting (defaults to now)
    """

    portfolio_id: UUID
    ticker_symbol: str
    quantity_shares: Decimal
    price_per_share_amount: Decimal
    price_per_share_currency: str = "USD"
    notes: str | None = None
    as_of: datetime | None = None


@dataclass(frozen=True)
class BuyStockResult:
    """Result of buying stock.

    Attributes:
        transaction_id: ID of the created transaction
        total_cost: Total amount spent (quantity × price)
    """

    transaction_id: UUID
    total_cost: Money


class BuyStockHandler:
    """Handler for BuyStock command.

    Executes a stock purchase by creating a BUY transaction.
    Validates that sufficient cash is available before executing the trade.
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

    async def execute(self, command: BuyStockCommand) -> BuyStockResult:
        """Execute the BuyStock command.

        Args:
            command: Command with buy parameters

        Returns:
            Result containing transaction_id and total_cost

        Raises:
            InvalidPortfolioError: If portfolio doesn't exist
            InvalidTickerError: If ticker format is invalid
            InvalidQuantityError: If quantity is invalid (zero, negative)
            InvalidMoneyError: If price is invalid (zero, negative)
            InsufficientFundsError: If purchase exceeds available cash
        """
        # Verify portfolio exists
        portfolio = await self._portfolio_repository.get(command.portfolio_id)
        if portfolio is None:
            raise InvalidPortfolioError(f"Portfolio not found: {command.portfolio_id}")

        # Create value objects
        ticker = Ticker(command.ticker_symbol)
        quantity = Quantity(command.quantity_shares)
        price_per_share = Money(
            command.price_per_share_amount, command.price_per_share_currency
        )

        # Calculate total cost
        total_cost = price_per_share.multiply(quantity.shares)

        # Get all transactions to calculate current balance
        transactions = await self._transaction_repository.get_by_portfolio(
            command.portfolio_id
        )

        # Calculate current balance
        current_balance = PortfolioCalculator.calculate_cash_balance(transactions)

        # Validate sufficient funds
        if current_balance < total_cost:
            raise InsufficientFundsError(
                available=current_balance,
                required=total_cost,
            )

        # Generate transaction ID
        transaction_id = uuid4()

        # Use as_of timestamp if provided, otherwise use current time
        effective_timestamp = command.as_of if command.as_of else datetime.now(UTC)

        # Create BUY transaction (negative cash_change)
        transaction = Transaction(
            id=transaction_id,
            portfolio_id=command.portfolio_id,
            transaction_type=TransactionType.BUY,
            timestamp=effective_timestamp,
            cash_change=total_cost.negate(),  # Negative for purchase
            ticker=ticker,
            quantity=quantity,
            price_per_share=price_per_share,
            notes=command.notes,
        )

        # Persist transaction
        await self._transaction_repository.save(transaction)

        return BuyStockResult(transaction_id=transaction_id, total_cost=total_cost)
