"""GetPortfolioHoldings query - Calculate current stock positions with market data."""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from zebu.application.dtos.holding_dto import HoldingDTO
from zebu.application.ports.market_data_port import MarketDataPort
from zebu.application.ports.portfolio_repository import PortfolioRepository
from zebu.application.ports.transaction_repository import TransactionRepository
from zebu.domain.exceptions import InvalidPortfolioError
from zebu.domain.services.portfolio_calculator import PortfolioCalculator

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GetPortfolioHoldingsQuery:
    """Input data for retrieving portfolio holdings.

    Attributes:
        portfolio_id: Portfolio to calculate holdings for
    """

    portfolio_id: UUID


@dataclass(frozen=True)
class GetPortfolioHoldingsResult:
    """Result of retrieving portfolio holdings.

    Attributes:
        portfolio_id: Same as query input
        holdings: Current stock positions
        as_of: Timestamp when holdings were calculated
    """

    portfolio_id: UUID
    holdings: list[HoldingDTO]
    as_of: datetime


class GetPortfolioHoldingsHandler:
    """Handler for GetPortfolioHoldings query.

    Calculates current stock positions and enriches them with real-time market data.
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
        self, query: GetPortfolioHoldingsQuery
    ) -> GetPortfolioHoldingsResult:
        """Execute the GetPortfolioHoldings query.

        Args:
            query: Query with portfolio_id

        Returns:
            Result containing list of holdings enriched with market data

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

        # Calculate holdings
        holdings = PortfolioCalculator.calculate_holdings(transactions)

        # Enrich with market data using batch fetch
        enriched_holdings: list[HoldingDTO] = []

        if holdings:
            # Extract unique tickers from holdings
            tickers = [holding.ticker for holding in holdings]

            # Batch fetch all prices
            prices = await self._market_data.get_batch_prices(tickers)

            # Enrich each holding with price data
            for holding in holdings:
                avg_cost = holding.average_cost_per_share
                price_point = prices.get(holding.ticker)

                if price_point is not None:
                    # Price available - calculate market data
                    try:
                        # Calculate metrics
                        quantity_decimal = Decimal(str(holding.quantity.shares))
                        market_value_amount = (
                            price_point.price.amount * quantity_decimal
                        )
                        cost_basis_amount = holding.cost_basis.amount
                        unrealized_gain_loss_amount = (
                            market_value_amount - cost_basis_amount
                        )
                        gain_loss_percent = (
                            (unrealized_gain_loss_amount / cost_basis_amount) * 100
                            if cost_basis_amount > 0
                            else Decimal("0")
                        )

                        # Create enriched DTO with market data
                        enriched_holdings.append(
                            HoldingDTO(
                                ticker_symbol=holding.ticker.symbol,
                                quantity_shares=holding.quantity.shares,
                                cost_basis_amount=holding.cost_basis.amount,
                                cost_basis_currency=holding.cost_basis.currency,
                                average_cost_per_share_amount=avg_cost.amount
                                if avg_cost is not None
                                else None,
                                average_cost_per_share_currency=avg_cost.currency
                                if avg_cost is not None
                                else None,
                                current_price_amount=price_point.price.amount,
                                current_price_currency=price_point.price.currency,
                                market_value_amount=market_value_amount,
                                market_value_currency=price_point.price.currency,
                                unrealized_gain_loss_amount=unrealized_gain_loss_amount,
                                unrealized_gain_loss_currency=price_point.price.currency,
                                unrealized_gain_loss_percent=gain_loss_percent,
                                price_timestamp=price_point.timestamp,
                                price_source=price_point.source,
                            )
                        )
                    except Exception as e:
                        # Calculation error - log and fall back to no market data
                        logger.warning(
                            f"Error calculating market data for "
                            f"{holding.ticker.symbol}: {e}"
                        )
                        enriched_holdings.append(
                            HoldingDTO(
                                ticker_symbol=holding.ticker.symbol,
                                quantity_shares=holding.quantity.shares,
                                cost_basis_amount=holding.cost_basis.amount,
                                cost_basis_currency=holding.cost_basis.currency,
                                average_cost_per_share_amount=avg_cost.amount
                                if avg_cost is not None
                                else None,
                                average_cost_per_share_currency=avg_cost.currency
                                if avg_cost is not None
                                else None,
                                # Market data fields = None (indicates unavailable)
                            )
                        )
                else:
                    # Price unavailable - return holding without market data
                    logger.warning(
                        f"Price unavailable for {holding.ticker.symbol} "
                        f"(not in batch result)"
                    )
                    enriched_holdings.append(
                        HoldingDTO(
                            ticker_symbol=holding.ticker.symbol,
                            quantity_shares=holding.quantity.shares,
                            cost_basis_amount=holding.cost_basis.amount,
                            cost_basis_currency=holding.cost_basis.currency,
                            average_cost_per_share_amount=avg_cost.amount
                            if avg_cost is not None
                            else None,
                            average_cost_per_share_currency=avg_cost.currency
                            if avg_cost is not None
                            else None,
                            # Market data fields = None (indicates unavailable)
                        )
                    )

        return GetPortfolioHoldingsResult(
            portfolio_id=query.portfolio_id,
            holdings=enriched_holdings,
            as_of=datetime.now(UTC),
        )
