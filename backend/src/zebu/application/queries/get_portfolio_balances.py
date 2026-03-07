"""GetPortfolioBalances query - Calculate balances for multiple portfolios in batch."""

import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from zebu.application.exceptions import (
    MarketDataUnavailableError,
    TickerNotFoundError,
)
from zebu.application.ports.market_data_port import MarketDataPort
from zebu.application.ports.portfolio_repository import PortfolioRepository
from zebu.application.ports.transaction_repository import TransactionRepository
from zebu.application.queries.get_portfolio_balance import (
    GetPortfolioBalanceResult,
    get_previous_trading_day,
)
from zebu.domain.services.portfolio_calculator import PortfolioCalculator
from zebu.domain.value_objects.money import Money
from zebu.domain.value_objects.ticker import Ticker

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GetPortfolioBalancesQuery:
    """Input data for retrieving balances for multiple portfolios.

    Attributes:
        portfolio_ids: List of portfolio IDs to calculate balances for
        as_of: Optional reference time for calculation (defaults to now)
    """

    portfolio_ids: list[UUID]
    as_of: datetime | None = None


@dataclass(frozen=True)
class GetPortfolioBalancesResult:
    """Result of retrieving balances for multiple portfolios.

    Attributes:
        balances: List of individual portfolio balance results
    """

    balances: list[GetPortfolioBalanceResult]


class GetPortfolioBalancesHandler:
    """Handler for GetPortfolioBalances batch query.

    Calculates current cash balance and holdings value for multiple portfolios
    using a single database query and batched market data fetches. This
    eliminates the N+1 query problem when loading a dashboard of portfolios.
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
        self, query: GetPortfolioBalancesQuery
    ) -> GetPortfolioBalancesResult:
        """Execute the GetPortfolioBalances batch query.

        Fetches all transactions in one query, collects unique tickers, then
        fetches current and previous prices in parallel across all portfolios.

        Args:
            query: Query with list of portfolio_ids

        Returns:
            Result containing balance for each portfolio_id in the same order
            as the input. Portfolios with no transactions return zero balances.
        """
        if not query.portfolio_ids:
            return GetPortfolioBalancesResult(balances=[])

        current_time = query.as_of or datetime.now(UTC)

        # Fetch all transactions for all portfolios in ONE query
        transactions_by_portfolio = (
            await self._transaction_repository.get_by_portfolios(query.portfolio_ids)
        )

        # Calculate holdings for each portfolio
        holdings_by_portfolio = {}
        all_tickers: set[Ticker] = set()

        for portfolio_id in query.portfolio_ids:
            transactions = transactions_by_portfolio.get(portfolio_id, [])
            holdings = PortfolioCalculator.calculate_holdings(transactions)
            holdings_by_portfolio[portfolio_id] = holdings
            for holding in holdings:
                all_tickers.add(holding.ticker)

        # Fetch all unique current prices in parallel (one fetch per ticker)
        current_prices_dict: dict[Ticker, Money] = {}
        if all_tickers:

            async def fetch_current_price_safe(
                ticker: Ticker,
            ) -> tuple[Ticker, Money | None]:
                """Fetch current price, returning None on any error."""
                try:
                    price_point = await self._market_data.get_current_price(ticker)
                    return ticker, price_point.price
                except (TickerNotFoundError, MarketDataUnavailableError) as e:
                    logger.warning(
                        f"Failed to fetch current price for {ticker.symbol}: {e}"
                    )
                    return ticker, None

            current_results = await asyncio.gather(
                *[fetch_current_price_safe(t) for t in all_tickers]
            )
            for ticker, price in current_results:
                if price is not None:
                    current_prices_dict[ticker] = price

        # Fetch all unique previous prices in parallel
        previous_date = get_previous_trading_day(current_time)
        previous_prices_dict: dict[Ticker, Money] = {}
        if all_tickers:

            async def fetch_previous_price_safe(
                ticker: Ticker,
            ) -> tuple[Ticker, Money | None]:
                """Fetch previous close price, returning None on any error."""
                try:
                    price_point = await self._market_data.get_price_at(
                        ticker, previous_date
                    )
                    return ticker, price_point.price
                except (TickerNotFoundError, MarketDataUnavailableError) as e:
                    logger.warning(
                        f"Failed to fetch previous close price for {ticker.symbol}: {e}"
                    )
                    return ticker, None

            previous_results = await asyncio.gather(
                *[fetch_previous_price_safe(t) for t in all_tickers]
            )
            for ticker, price in previous_results:
                if price is not None:
                    previous_prices_dict[ticker] = price

        # Compute balance for each portfolio
        balances: list[GetPortfolioBalanceResult] = []
        for portfolio_id in query.portfolio_ids:
            transactions = transactions_by_portfolio.get(portfolio_id, [])
            cash_balance = PortfolioCalculator.calculate_cash_balance(transactions)
            holdings = holdings_by_portfolio[portfolio_id]

            if not holdings:
                balances.append(
                    GetPortfolioBalanceResult(
                        portfolio_id=portfolio_id,
                        cash_balance=cash_balance,
                        holdings_value=Money(Decimal("0.00"), cash_balance.currency),
                        total_value=cash_balance,
                        currency=cash_balance.currency,
                        as_of=current_time,
                        daily_change=Money(Decimal("0.00"), cash_balance.currency),
                        daily_change_percent=Decimal("0.00"),
                    )
                )
                continue

            holdings_value = PortfolioCalculator.calculate_portfolio_value(
                holdings, current_prices_dict
            )
            total_value = PortfolioCalculator.calculate_total_value(
                cash_balance, holdings_value
            )
            daily_change, daily_change_percent = (
                PortfolioCalculator.calculate_daily_change(
                    holdings, current_prices_dict, previous_prices_dict
                )
            )

            balances.append(
                GetPortfolioBalanceResult(
                    portfolio_id=portfolio_id,
                    cash_balance=cash_balance,
                    holdings_value=holdings_value,
                    total_value=total_value,
                    currency=cash_balance.currency,
                    as_of=current_time,
                    daily_change=daily_change,
                    daily_change_percent=daily_change_percent,
                )
            )

        return GetPortfolioBalancesResult(balances=balances)
