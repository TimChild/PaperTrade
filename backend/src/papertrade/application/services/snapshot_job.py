"""SnapshotJobService - Background job for calculating portfolio snapshots.

This service orchestrates the calculation and persistence of daily portfolio
snapshots for analytics and performance tracking.
"""

import logging
from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from papertrade.application.exceptions import (
    MarketDataUnavailableError,
    TickerNotFoundError,
)
from papertrade.application.ports.market_data_port import MarketDataPort
from papertrade.application.ports.portfolio_repository import PortfolioRepository
from papertrade.application.ports.snapshot_repository import SnapshotRepository
from papertrade.application.ports.transaction_repository import TransactionRepository
from papertrade.domain.entities.portfolio_snapshot import PortfolioSnapshot
from papertrade.domain.services.portfolio_calculator import PortfolioCalculator
from papertrade.domain.services.snapshot_calculator import SnapshotCalculator

logger = logging.getLogger(__name__)


class SnapshotJobService:
    """Service for calculating and persisting portfolio snapshots.

    This service is designed to be used by scheduled jobs to calculate
    daily snapshots for all portfolios. It handles errors gracefully and
    provides detailed logging for monitoring.
    """

    def __init__(
        self,
        portfolio_repo: PortfolioRepository,
        transaction_repo: TransactionRepository,
        snapshot_repo: SnapshotRepository,
        market_data: MarketDataPort,
    ) -> None:
        """Initialize snapshot job service.

        Args:
            portfolio_repo: Repository for portfolio persistence
            transaction_repo: Repository for transaction persistence
            snapshot_repo: Repository for snapshot persistence
            market_data: Market data port for fetching current prices
        """
        self._portfolio_repo = portfolio_repo
        self._transaction_repo = transaction_repo
        self._snapshot_repo = snapshot_repo
        self._market_data = market_data
        self._calculator = SnapshotCalculator()

    async def run_daily_snapshot(
        self, snapshot_date: date | None = None
    ) -> dict[str, int]:
        """Calculate snapshots for all portfolios for the given date.

        This method is designed to be called by a scheduled job
        (e.g., daily at midnight).
        It processes all portfolios and handles errors gracefully, continuing
        to process remaining portfolios even if some fail.

        Args:
            snapshot_date: Date for the snapshot (defaults to today)

        Returns:
            dict with counts: {"processed": N, "succeeded": N, "failed": N}

        Example:
            >>> service = SnapshotJobService(...)
            >>> result = await service.run_daily_snapshot()
            >>> print(f"{result['succeeded']}/{result['processed']} snapshots saved")
        """
        target_date = snapshot_date or date.today()
        logger.info(f"Starting daily snapshot for {target_date}")

        portfolios = await self._portfolio_repo.list_all()

        results: dict[str, int] = {"processed": 0, "succeeded": 0, "failed": 0}

        for portfolio in portfolios:
            results["processed"] += 1
            try:
                snapshot = await self._calculate_snapshot_for_portfolio(
                    portfolio.id, target_date
                )
                await self._snapshot_repo.save(snapshot)
                results["succeeded"] += 1
                logger.debug(
                    f"Snapshot saved for portfolio {portfolio.id} "
                    f"(total_value={snapshot.total_value})"
                )
            except Exception as e:
                results["failed"] += 1
                logger.error(f"Failed to snapshot portfolio {portfolio.id}: {e}")

        logger.info(
            f"Daily snapshot complete: "
            f"{results['succeeded']}/{results['processed']} succeeded"
        )
        return results

    async def backfill_snapshots(
        self,
        portfolio_id: UUID,
        start_date: date,
        end_date: date,
    ) -> dict[str, int]:
        """Generate historical snapshots for a portfolio.

        Use this for new portfolios or fixing gaps in snapshot history.
        Processes each day in the range sequentially.

        Args:
            portfolio_id: Portfolio to backfill
            start_date: Start of date range (inclusive)
            end_date: End of date range (inclusive)

        Returns:
            dict with counts: {"processed": N, "succeeded": N, "failed": N}

        Example:
            >>> from datetime import date, timedelta
            >>> service = SnapshotJobService(...)
            >>> start = date.today() - timedelta(days=30)
            >>> end = date.today()
            >>> result = await service.backfill_snapshots(portfolio_id, start, end)
            >>> print(f"Backfilled {result['succeeded']} snapshots")
        """
        logger.info(
            f"Backfilling snapshots for {portfolio_id} "
            f"from {start_date} to {end_date}"
        )

        results: dict[str, int] = {"processed": 0, "succeeded": 0, "failed": 0}
        current_date = start_date

        while current_date <= end_date:
            results["processed"] += 1
            try:
                snapshot = await self._calculate_snapshot_for_portfolio(
                    portfolio_id, current_date
                )
                await self._snapshot_repo.save(snapshot)
                results["succeeded"] += 1
            except Exception as e:
                results["failed"] += 1
                logger.warning(f"Failed to backfill {current_date}: {e}")

            current_date += timedelta(days=1)

        logger.info(f"Backfill complete: {results}")
        return results

    async def _calculate_snapshot_for_portfolio(
        self,
        portfolio_id: UUID,
        snapshot_date: date,
    ) -> PortfolioSnapshot:
        """Calculate a single snapshot for a portfolio.

        This method encapsulates the logic for calculating a snapshot:
        1. Get portfolio (verify it exists)
        2. Get all transactions for the portfolio
        3. Calculate cash balance from transactions
        4. Calculate holdings from transactions
        5. Get current prices for each holding
        6. Calculate snapshot using SnapshotCalculator

        Args:
            portfolio_id: Portfolio identifier
            snapshot_date: Date of the snapshot

        Returns:
            PortfolioSnapshot with calculated values

        Raises:
            ValueError: If portfolio not found
            Exception: If calculation fails (market data unavailable, etc.)
        """
        # Get portfolio state
        portfolio = await self._portfolio_repo.get(portfolio_id)
        if not portfolio:
            raise ValueError(f"Portfolio {portfolio_id} not found")

        # Get all transactions for this portfolio
        transactions = await self._transaction_repo.get_by_portfolio(portfolio_id)

        # Calculate cash balance from transactions
        cash_balance_money = PortfolioCalculator.calculate_cash_balance(transactions)

        # Calculate holdings from transactions
        holdings = PortfolioCalculator.calculate_holdings(transactions)

        # Get current prices for all holdings
        holdings_data: list[tuple[str, int, Decimal]] = []
        for holding in holdings:
            if holding.quantity.shares > 0:
                try:
                    # For historical snapshots, we'd need get_price_at(ticker, date)
                    # For daily snapshots, current price is fine
                    price_point = await self._market_data.get_current_price(
                        holding.ticker
                    )
                    holdings_data.append(
                        (
                            holding.ticker.symbol,
                            holding.quantity.shares,
                            price_point.price.amount,
                        )
                    )
                except (TickerNotFoundError, MarketDataUnavailableError) as e:
                    # Log warning but continue - use zero value for unavailable prices
                    logger.warning(
                        f"Price unavailable for {holding.ticker.symbol}: {e}"
                    )
                    # Skip this holding (don't include in snapshot)
                    continue

        # Calculate snapshot using domain service
        return self._calculator.calculate_snapshot(
            portfolio_id=portfolio_id,
            snapshot_date=snapshot_date,
            cash_balance=cash_balance_money.amount,
            holdings=holdings_data,
        )
