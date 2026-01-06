"""GetPortfolioComposition query - Calculate portfolio asset allocation."""

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from papertrade.application.ports.market_data_port import MarketDataPort
from papertrade.application.ports.portfolio_repository import PortfolioRepository
from papertrade.application.ports.transaction_repository import TransactionRepository
from papertrade.domain.exceptions import InvalidPortfolioError
from papertrade.domain.services.portfolio_calculator import PortfolioCalculator


@dataclass(frozen=True)
class CompositionItem:
    """Portfolio composition item (holding or cash).

    Attributes:
        ticker: Ticker symbol or "CASH"
        value: Current value in base currency
        percentage: Percentage of total portfolio value
        quantity: Number of shares (None for cash)
    """

    ticker: str
    value: Decimal
    percentage: Decimal
    quantity: int | None


@dataclass(frozen=True)
class GetPortfolioCompositionQuery:
    """Input data for retrieving portfolio composition.

    Attributes:
        portfolio_id: Portfolio to get composition for
    """

    portfolio_id: UUID


@dataclass(frozen=True)
class GetPortfolioCompositionResult:
    """Result of retrieving portfolio composition.

    Attributes:
        portfolio_id: Same as query input
        total_value: Total portfolio value (cash + holdings)
        composition: List of composition items (holdings + cash)
    """

    portfolio_id: UUID
    total_value: Decimal
    composition: list[CompositionItem]


class GetPortfolioCompositionHandler:
    """Handler for GetPortfolioComposition query.

    Calculates current portfolio asset allocation with live market prices.
    """

    def __init__(
        self,
        portfolio_repository: PortfolioRepository,
        transaction_repository: TransactionRepository,
        market_data: MarketDataPort,
    ) -> None:
        """Initialize handler with repository dependencies.

        Args:
            portfolio_repository: Repository for portfolio persistence
            transaction_repository: Repository for transaction persistence
            market_data: Market data port for fetching current prices
        """
        self._portfolio_repository = portfolio_repository
        self._transaction_repository = transaction_repository
        self._market_data = market_data

    async def execute(
        self, query: GetPortfolioCompositionQuery
    ) -> GetPortfolioCompositionResult:
        """Execute the GetPortfolioComposition query.

        Args:
            query: Query with portfolio_id

        Returns:
            Result containing portfolio composition

        Raises:
            InvalidPortfolioError: If portfolio doesn't exist
        """
        # Verify portfolio exists
        portfolio = await self._portfolio_repository.get(query.portfolio_id)
        if portfolio is None:
            raise InvalidPortfolioError(f"Portfolio not found: {query.portfolio_id}")

        # Get all transactions to calculate current state
        transactions = await self._transaction_repository.get_by_portfolio(
            query.portfolio_id
        )

        # Calculate cash balance
        cash_balance_money = PortfolioCalculator.calculate_cash_balance(transactions)
        cash_balance = cash_balance_money.amount

        # Calculate holdings
        holdings = PortfolioCalculator.calculate_holdings(transactions)

        # Build composition items
        items: list[CompositionItem] = []
        total_value = cash_balance

        # Add holdings with current market values
        for holding in holdings:
            try:
                price_point = await self._market_data.get_current_price(holding.ticker)
                value = price_point.price.amount * Decimal(str(holding.quantity.shares))
                total_value += value

                items.append(
                    CompositionItem(
                        ticker=holding.ticker.symbol,
                        value=value,
                        percentage=Decimal("0"),  # Calculate after total known
                        quantity=int(holding.quantity.shares),
                    )
                )
            except Exception:
                # If price unavailable, skip this holding
                # In production, might want to log this or use last known price
                continue

        # Add cash
        items.append(
            CompositionItem(
                ticker="CASH",
                value=cash_balance,
                percentage=Decimal("0"),  # Calculate after total known
                quantity=None,
            )
        )

        # Calculate percentages
        if total_value > 0:
            # Recalculate with percentages
            items_with_percentages = [
                CompositionItem(
                    ticker=item.ticker,
                    value=item.value,
                    percentage=(item.value / total_value * 100).quantize(
                        Decimal("0.1")
                    ),
                    quantity=item.quantity,
                )
                for item in items
            ]
            items = items_with_percentages

        return GetPortfolioCompositionResult(
            portfolio_id=query.portfolio_id,
            total_value=total_value,
            composition=items,
        )
