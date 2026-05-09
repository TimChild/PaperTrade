"""SnapshotJobService - Background job for calculating portfolio snapshots.

This service orchestrates the calculation and persistence of daily portfolio
snapshots for analytics and performance tracking.
"""

import logging
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from zebu.application.exceptions import (
    MarketDataUnavailableError,
    TickerNotFoundError,
)
from zebu.application.ports.market_data_port import MarketDataPort
from zebu.application.ports.portfolio_repository import PortfolioRepository
from zebu.application.ports.snapshot_repository import SnapshotRepository
from zebu.application.ports.transaction_repository import TransactionRepository
from zebu.domain.entities.portfolio_snapshot import PortfolioSnapshot
from zebu.domain.entities.transaction import Transaction
from zebu.domain.services.portfolio_calculator import PortfolioCalculator
from zebu.domain.services.snapshot_calculator import SnapshotCalculator
from zebu.domain.value_objects.price_point import PricePoint
from zebu.domain.value_objects.ticker import Ticker

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

        Performance: Bulk-fetches transactions for ALL portfolios in a single
        query, then bulk-fetches prices for the union of all distinct tickers.
        Per-portfolio iteration is then pure in-memory math. See
        agent_docs/audits/2026-05-09/database.md (P1-db-2): the previous
        implementation issued ~(1 + 1 + N_holdings) DB calls per portfolio.

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
        if not portfolios:
            logger.info(
                f"Daily snapshot complete: "
                f"{results['succeeded']}/{results['processed']} succeeded"
            )
            return results

        # Bulk-fetch: 1 query for transactions across ALL portfolios — replaces
        # N per-portfolio get_by_portfolio calls.
        portfolio_ids = [p.id for p in portfolios]
        transactions_by_portfolio = await self._transaction_repo.get_by_portfolios(
            portfolio_ids
        )

        # Determine the union of tickers held across all portfolios so we can
        # fetch prices in one batch (current date) or one call per unique ticker
        # (historical), instead of per-portfolio per-holding.
        unique_tickers: set[Ticker] = set()
        portfolio_holdings: dict[UUID, list[tuple[Ticker, int]]] = {}
        for portfolio in portfolios:
            transactions = transactions_by_portfolio.get(portfolio.id, [])
            holdings = PortfolioCalculator.calculate_holdings(transactions)
            held: list[tuple[Ticker, int]] = []
            for holding in holdings:
                if holding.quantity.shares > 0:
                    held.append((holding.ticker, int(holding.quantity.shares)))
                    unique_tickers.add(holding.ticker)
            portfolio_holdings[portfolio.id] = held

        # Bulk-fetch prices once. For "current" target_date we use the batch
        # endpoint (1 round-trip when the cache is hot). For historical dates,
        # we fall back to one get_price_at per *unique* ticker — still O(T)
        # where T is distinct tickers across the entire fleet, not O(P × H).
        price_map = await self._fetch_prices_for_date(
            tickers=unique_tickers,
            target_date=target_date,
        )

        for portfolio in portfolios:
            results["processed"] += 1
            try:
                snapshot = self._build_snapshot_from_data(
                    portfolio_id=portfolio.id,
                    snapshot_date=target_date,
                    transactions=transactions_by_portfolio.get(portfolio.id, []),
                    holdings=portfolio_holdings[portfolio.id],
                    price_map=price_map,
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
            f"Backfilling snapshots for {portfolio_id} from {start_date} to {end_date}"
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

        # Get prices for all holdings (historical or current)
        holdings_data: list[tuple[str, int, Decimal]] = []
        failed_tickers: list[str] = []
        is_historical = snapshot_date < date.today()
        for holding in holdings:
            if holding.quantity.shares > 0:
                try:
                    if is_historical:
                        # Use historical price for backfill dates
                        snapshot_dt = datetime(
                            snapshot_date.year,
                            snapshot_date.month,
                            snapshot_date.day,
                            12,
                            0,
                            0,
                            tzinfo=UTC,
                        )
                        price_point = await self._market_data.get_price_at(
                            holding.ticker, snapshot_dt
                        )
                    else:
                        price_point = await self._market_data.get_current_price(
                            holding.ticker
                        )
                    holdings_data.append(
                        (
                            holding.ticker.symbol,
                            int(holding.quantity.shares),
                            price_point.price.amount,
                        )
                    )
                except (TickerNotFoundError, MarketDataUnavailableError) as e:
                    logger.warning(
                        f"Price unavailable for {holding.ticker.symbol}: {e}"
                    )
                    failed_tickers.append(holding.ticker.symbol)

        # If any holdings had price lookup failures, skip this snapshot entirely.
        # Saving a snapshot with missing holdings would record an artificially low
        # total_value (just cash), causing erratic chart oscillation.
        if failed_tickers:
            raise MarketDataUnavailableError(
                f"Cannot calculate accurate snapshot: "
                f"price unavailable for {', '.join(failed_tickers)}"
            )

        # Calculate snapshot using domain service
        return self._calculator.calculate_snapshot(
            portfolio_id=portfolio_id,
            snapshot_date=snapshot_date,
            cash_balance=cash_balance_money.amount,
            holdings=holdings_data,
        )

    async def _fetch_prices_for_date(
        self,
        tickers: set[Ticker],
        target_date: date,
    ) -> dict[Ticker, PricePoint]:
        """Fetch prices for the union of tickers in a single batch.

        For ``target_date == today`` the batch endpoint is one round-trip
        (cache-hot) or one API call (cache-miss). For historical dates we
        fall back to one ``get_price_at`` per *unique* ticker — still
        deduplicated across portfolios. Tickers that fail to resolve are
        simply absent from the returned map; callers detect that and treat
        the per-portfolio snapshot as failed.

        Args:
            tickers: Distinct tickers to look up.
            target_date: Snapshot date (today → current price; past → historical).

        Returns:
            Dict mapping each successfully-resolved Ticker to its PricePoint.
        """
        if not tickers:
            return {}

        is_historical = target_date < date.today()
        if not is_historical:
            return await self._market_data.get_batch_prices(list(tickers))

        snapshot_dt = datetime(
            target_date.year,
            target_date.month,
            target_date.day,
            12,
            0,
            0,
            tzinfo=UTC,
        )
        result: dict[Ticker, PricePoint] = {}
        for ticker in tickers:
            try:
                result[ticker] = await self._market_data.get_price_at(
                    ticker, snapshot_dt
                )
            except (TickerNotFoundError, MarketDataUnavailableError) as e:
                logger.warning(
                    f"Historical price unavailable for {ticker.symbol} "
                    f"on {target_date}: {e}"
                )
        return result

    def _build_snapshot_from_data(
        self,
        portfolio_id: UUID,
        snapshot_date: date,
        transactions: list[Transaction],
        holdings: list[tuple[Ticker, int]],
        price_map: dict[Ticker, PricePoint],
    ) -> PortfolioSnapshot:
        """Build a snapshot from already-resolved transactions and prices.

        Pure in-memory: no I/O. Used by ``run_daily_snapshot`` after the
        bulk fetches have been done. Equivalent semantics to
        ``_calculate_snapshot_for_portfolio`` — same failure mode (raises
        ``MarketDataUnavailableError`` when any held ticker has no price)
        and same SnapshotCalculator output.
        """
        cash_balance_money = PortfolioCalculator.calculate_cash_balance(transactions)

        holdings_data: list[tuple[str, int, Decimal]] = []
        failed_tickers: list[str] = []
        for ticker, shares in holdings:
            price_point = price_map.get(ticker)
            if price_point is None:
                failed_tickers.append(ticker.symbol)
                continue
            holdings_data.append((ticker.symbol, shares, price_point.price.amount))

        if failed_tickers:
            raise MarketDataUnavailableError(
                f"Cannot calculate accurate snapshot: "
                f"price unavailable for {', '.join(failed_tickers)}"
            )

        return self._calculator.calculate_snapshot(
            portfolio_id=portfolio_id,
            snapshot_date=snapshot_date,
            cash_balance=cash_balance_money.amount,
            holdings=holdings_data,
        )
