"""GetPortfolioBalance query - Calculate current cash balance with holdings value."""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from zebu.application.exceptions import (
    MarketDataUnavailableError,
    TickerNotFoundError,
)
from zebu.application.ports.market_data_port import MarketDataPort
from zebu.application.ports.portfolio_repository import PortfolioRepository
from zebu.application.ports.transaction_repository import TransactionRepository
from zebu.domain.exceptions import InvalidPortfolioError
from zebu.domain.services.portfolio_calculator import PortfolioCalculator
from zebu.domain.value_objects.money import Money
from zebu.domain.value_objects.ticker import Ticker

logger = logging.getLogger(__name__)


def _get_previous_trading_day(reference_date: datetime | None = None) -> datetime:
    """Get previous trading day for daily change calculation (skip weekends).

    This function determines what "yesterday's close" means for daily change calculations.
    The logic depends on what day we're on:
    
    - Monday: Compare current (Mon) to Friday's close (3 days back)
    - Tuesday-Friday: Compare current to previous day's close (1 day back)
    - Saturday: Compare current (Fri close) to Thursday close (2 days back)
    - Sunday: Compare current (Fri close) to Thursday close (3 days back)
    
    The key insight is that on weekends, both "current" and "most recent trading day"
    resolve to Friday. For daily change, we need to compare Friday to Thursday.

    Args:
        reference_date: Reference date to calculate from (defaults to now)

    Returns:
        Datetime representing previous trading day at market close (21:00 UTC)
    """
    if reference_date is None:
        reference_date = datetime.now(UTC)

    # Get just the date part
    current_date = reference_date.date()
    day_of_week = current_date.weekday()

    # Calculate days to go back based on day of week
    if day_of_week == 0:  # Monday
        # Current: Monday
        # Previous close: Friday (3 days back)
        days_back = 3
    elif day_of_week == 5:  # Saturday
        # Current: Friday close (using most recent)
        # Previous close: Thursday (2 days back)
        days_back = 2
    elif day_of_week == 6:  # Sunday
        # Current: Friday close (using most recent)
        # Previous close: Thursday (3 days back)
        days_back = 3
    else:  # Tuesday (1) through Friday (4)
        # Current: Today
        # Previous close: Yesterday
        days_back = 1

    previous_date = current_date - timedelta(days=days_back)

    # Return datetime at market close (4 PM ET = 21:00 UTC)
    return datetime(
        previous_date.year,
        previous_date.month,
        previous_date.day,
        hour=21,
        minute=0,
        second=0,
        tzinfo=UTC,
    )


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
        daily_change: Daily change amount (current - previous close)
        daily_change_percent: Daily change as percentage
    """

    portfolio_id: UUID
    cash_balance: Money
    holdings_value: Money
    total_value: Money
    currency: str
    as_of: datetime
    daily_change: Money
    daily_change_percent: Decimal


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
            Result containing cash balance, holdings value, total value,
            and daily change

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

        # If no holdings, return zero values immediately
        if not holdings:
            return GetPortfolioBalanceResult(
                portfolio_id=query.portfolio_id,
                cash_balance=cash_balance,
                holdings_value=Money(Decimal("0.00"), cash_balance.currency),
                total_value=cash_balance,
                currency=cash_balance.currency,
                as_of=datetime.now(UTC),
                daily_change=Money(Decimal("0.00"), cash_balance.currency),
                daily_change_percent=Decimal("0.00"),
            )

        # Collect all unique tickers
        tickers = [holding.ticker for holding in holdings]

        # Fetch current prices
        current_prices_dict: dict[Ticker, Money] = {}
        for ticker in tickers:
            try:
                price_point = await self._market_data.get_current_price(ticker)
                current_prices_dict[ticker] = price_point.price
            except (TickerNotFoundError, MarketDataUnavailableError) as e:
                logger.warning(
                    f"Failed to fetch current price for {ticker.symbol}: {e}"
                )
                # Skip ticker if price unavailable
                continue

        # Fetch previous close prices
        previous_date = _get_previous_trading_day()
        previous_prices_dict: dict[Ticker, Money] = {}
        for ticker in tickers:
            try:
                price_point = await self._market_data.get_price_at(
                    ticker, previous_date
                )
                previous_prices_dict[ticker] = price_point.price
            except (TickerNotFoundError, MarketDataUnavailableError) as e:
                logger.warning(
                    f"Failed to fetch previous close price for {ticker.symbol}: {e}"
                )
                # Skip ticker if price unavailable
                continue

        # Calculate holdings value using PortfolioCalculator
        holdings_value = PortfolioCalculator.calculate_portfolio_value(
            holdings, current_prices_dict
        )

        # Calculate total value
        total_value = PortfolioCalculator.calculate_total_value(
            cash_balance, holdings_value
        )

        # Calculate daily change
        daily_change, daily_change_percent = PortfolioCalculator.calculate_daily_change(
            holdings, current_prices_dict, previous_prices_dict
        )

        return GetPortfolioBalanceResult(
            portfolio_id=query.portfolio_id,
            cash_balance=cash_balance,
            holdings_value=holdings_value,
            total_value=total_value,
            currency=cash_balance.currency,
            as_of=datetime.now(UTC),
            daily_change=daily_change,
            daily_change_percent=daily_change_percent,
        )
