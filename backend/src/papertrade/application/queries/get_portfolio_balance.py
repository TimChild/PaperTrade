"""GetPortfolioBalance query - Calculate current cash balance with holdings value."""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from papertrade.application.exceptions import (
    MarketDataUnavailableError,
    TickerNotFoundError,
)
from papertrade.application.ports.market_data_port import MarketDataPort
from papertrade.application.ports.portfolio_repository import PortfolioRepository
from papertrade.application.ports.transaction_repository import TransactionRepository
from papertrade.domain.exceptions import InvalidPortfolioError
from papertrade.domain.services.portfolio_calculator import PortfolioCalculator
from papertrade.domain.value_objects.money import Money

logger = logging.getLogger(__name__)


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
        holdings_value: Current market value of all holdings
        total_value: Sum of cash_balance and holdings_value
        currency: Currency of the balance
        as_of: Timestamp when balance was calculated
    """

    portfolio_id: UUID
    cash_balance: Money
    holdings_value: Money
    total_value: Money
    currency: str
    as_of: datetime


class GetPortfolioBalanceHandler:
    """Handler for GetPortfolioBalance query.

    Calculates current cash balance and holdings value using real market prices.
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
        self, query: GetPortfolioBalanceQuery
    ) -> GetPortfolioBalanceResult:
        """Execute the GetPortfolioBalance query.

        Args:
            query: Query with portfolio_id

        Returns:
            Result containing cash balance, holdings value, and total value

        Raises:
            InvalidPortfolioError: If portfolio doesn't exist
        """
        # Verify portfolio exists
        portfolio = await self._portfolio_repository.get(query.portfolio_id)
        if portfolio is None:
            raise InvalidPortfolioError(f"Portfolio not found: {query.portfolio_id}")

        # Get all transactions
        transactions = await self._transaction_repository.get_by_portfolio(
            query.portfolio_id
        )

        # Calculate cash balance
        cash_balance = PortfolioCalculator.calculate_cash_balance(transactions)

        # Calculate holdings
        holdings = PortfolioCalculator.calculate_holdings(transactions)

        # Calculate holdings value with real prices
        holdings_value = Money(Decimal("0"), cash_balance.currency)

        for holding in holdings:
            try:
                # Fetch current price from market data
                price_point = await self._market_data.get_current_price(holding.ticker)
                holding_value = Money(
                    price_point.price.amount * Decimal(str(holding.quantity.shares)),
                    price_point.price.currency,
                )
                holdings_value = Money(
                    holdings_value.amount + holding_value.amount,
                    holdings_value.currency,
                )

            except TickerNotFoundError:
                # Ticker not found - skip this holding (value = 0)
                logger.warning(
                    f"Ticker {holding.ticker.symbol} not found in market data"
                )
                continue

            except MarketDataUnavailableError as e:
                # API down or rate limited - skip but log
                logger.error(
                    f"Market data unavailable for {holding.ticker.symbol}: {e}"
                )
                continue

        # Calculate total value
        total_value = Money(
            cash_balance.amount + holdings_value.amount,
            cash_balance.currency,
        )

        return GetPortfolioBalanceResult(
            portfolio_id=query.portfolio_id,
            cash_balance=cash_balance,
            holdings_value=holdings_value,
            total_value=total_value,
            currency=cash_balance.currency,
            as_of=datetime.now(UTC),
        )
