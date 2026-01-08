"""SellStock command - Sell shares with holdings validation."""

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from papertrade.application.ports.portfolio_repository import PortfolioRepository
from papertrade.application.ports.transaction_repository import TransactionRepository
from papertrade.domain.entities.transaction import Transaction, TransactionType
from papertrade.domain.exceptions import (
    InsufficientSharesError,
    InvalidPortfolioError,
)
from papertrade.domain.services.portfolio_calculator import PortfolioCalculator
from papertrade.domain.value_objects.money import Money
from papertrade.domain.value_objects.quantity import Quantity
from papertrade.domain.value_objects.ticker import Ticker


@dataclass(frozen=True)
class SellStockCommand:
    """Input data for selling stock.

    Attributes:
        portfolio_id: Target portfolio
        ticker_symbol: Stock symbol to sell
        quantity_shares: Number of shares to sell
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
class SellStockResult:
    """Result of selling stock.

    Attributes:
        transaction_id: ID of the created transaction
        total_proceeds: Total amount received (quantity × price)
    """

    transaction_id: UUID
    total_proceeds: Money


class SellStockHandler:
    """Handler for SellStock command.

    Executes a stock sale by creating a SELL transaction.
    Validates that sufficient shares are owned before executing the trade.
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

    async def execute(self, command: SellStockCommand) -> SellStockResult:
        """Execute the SellStock command.

        Args:
            command: Command with sell parameters

        Returns:
            Result containing transaction_id and total_proceeds

        Raises:
            InvalidPortfolioError: If portfolio doesn't exist
            InvalidTickerError: If ticker format is invalid
            InvalidQuantityError: If quantity is invalid (zero, negative)
            InvalidMoneyError: If price is invalid (zero, negative)
            InsufficientSharesError: If sale exceeds owned shares
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

        # Calculate total proceeds
        total_proceeds = price_per_share.multiply(quantity.shares)

        # Get all transactions to calculate current holdings
        transactions = await self._transaction_repository.get_by_portfolio(
            command.portfolio_id
        )

        # Calculate current holding for this ticker
        holding = PortfolioCalculator.calculate_holding_for_ticker(transactions, ticker)

        # Validate sufficient shares
        if holding is None or holding.quantity < quantity:
            owned_quantity = holding.quantity if holding else Quantity(Decimal("0"))
            raise InsufficientSharesError(
                ticker=ticker.symbol,
                available=owned_quantity,
                required=quantity,
            )

        # Generate transaction ID
        transaction_id = uuid4()

        # Use as_of timestamp if provided, otherwise use current time
        effective_timestamp = command.as_of if command.as_of else datetime.now(UTC)

        # Create SELL transaction (positive cash_change)
        transaction = Transaction(
            id=transaction_id,
            portfolio_id=command.portfolio_id,
            transaction_type=TransactionType.SELL,
            timestamp=effective_timestamp,
            cash_change=total_proceeds,  # Positive for sale
            ticker=ticker,
            quantity=quantity,
            price_per_share=price_per_share,
            notes=command.notes,
        )

        # Persist transaction
        await self._transaction_repository.save(transaction)

        return SellStockResult(
            transaction_id=transaction_id, total_proceeds=total_proceeds
        )
