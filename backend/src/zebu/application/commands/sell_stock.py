"""SellStock command - Sell shares with holdings validation."""

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from zebu.application.ports.portfolio_repository import PortfolioRepository
from zebu.application.ports.transaction_repository import TransactionRepository
from zebu.domain.exceptions import InvalidPortfolioError
from zebu.domain.services.portfolio_calculator import PortfolioCalculator
from zebu.domain.services.trade_factory import create_sell_transaction
from zebu.domain.value_objects.money import Money
from zebu.domain.value_objects.quantity import Quantity
from zebu.domain.value_objects.ticker import Ticker


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

        # Get all transactions to calculate current holdings
        transactions = await self._transaction_repository.get_by_portfolio(
            command.portfolio_id
        )

        # Use as_of timestamp if provided, otherwise use current time
        effective_timestamp = command.as_of if command.as_of else datetime.now(UTC)

        # Get holding quantity for validation
        holding = PortfolioCalculator.calculate_holding_for_ticker(transactions, ticker)
        holding_quantity = holding.quantity if holding else Quantity(Decimal("0"))

        # Create validated SELL transaction using shared domain function
        transaction = create_sell_transaction(
            portfolio_id=command.portfolio_id,
            ticker=ticker,
            quantity=quantity,
            price_per_share=price_per_share,
            current_holding_quantity=holding_quantity,
            timestamp=effective_timestamp,
            notes=command.notes,
        )

        # Persist transaction
        await self._transaction_repository.save(transaction)

        return SellStockResult(
            transaction_id=transaction.id,
            total_proceeds=price_per_share.multiply(quantity.shares),
        )
