"""Background job scheduler for automated price refresh and maintenance tasks.

This module provides a background scheduler using APScheduler to run periodic jobs
like price refresh, snapshot calculation, and other maintenance tasks without blocking
the main API server.

The scheduler is integrated into the FastAPI application lifecycle and starts/stops
automatically with the application.
"""

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from zebu.adapters.inbound.api.dependencies import get_market_data
from zebu.adapters.outbound.database.portfolio_repository import (
    SQLModelPortfolioRepository,
)
from zebu.adapters.outbound.database.snapshot_repository import (
    SQLModelSnapshotRepository,
)
from zebu.adapters.outbound.database.transaction_repository import (
    SQLModelTransactionRepository,
)
from zebu.adapters.outbound.repositories.watchlist_manager import (
    WatchlistManager,
)
from zebu.application.queries.get_active_tickers import (
    GetActiveTickersHandler,
    GetActiveTickersQuery,
)
from zebu.application.services.snapshot_job import SnapshotJobService
from zebu.infrastructure.database import async_session_maker

logger = logging.getLogger("uvicorn.error")  # Use uvicorn's configured logger

# Global scheduler instance
_scheduler: AsyncIOScheduler | None = None


class SchedulerConfig:
    """Configuration for the background scheduler.

    This class holds configuration values for the scheduler, including
    job schedules, batch processing settings, and error thresholds.
    """

    def __init__(
        self,
        enabled: bool = True,
        refresh_cron: str = "0 0 * * *",  # Midnight UTC
        timezone: str = "UTC",
        max_instances: int = 1,
        batch_size: int = 5,
        batch_delay_seconds: int = 60,
        max_age_hours: int = 24,
        active_stock_days: int = 30,
    ) -> None:
        """Initialize scheduler configuration.

        Args:
            enabled: Whether scheduler is enabled
            refresh_cron: Cron expression for refresh schedule
            timezone: Timezone for scheduler
            max_instances: Max concurrent job instances
            batch_size: Tickers to refresh per batch
            batch_delay_seconds: Delay between batches
            max_age_hours: Refresh if price older than this
            active_stock_days: Consider stocks traded in last N days
        """
        self.enabled = enabled
        self.refresh_cron = refresh_cron
        self.timezone = timezone
        self.max_instances = max_instances
        self.batch_size = batch_size
        self.batch_delay_seconds = batch_delay_seconds
        self.max_age_hours = max_age_hours
        self.active_stock_days = active_stock_days


async def refresh_active_stocks(config: SchedulerConfig) -> None:
    """Background job to refresh prices for active stocks.

    This job:
    1. Gets list of active tickers (from watchlist and recent trades)
    2. Fetches current price for each ticker
    3. Updates cache via the normal MarketDataPort flow
    4. Respects rate limits with delays between batches

    The job is designed to be idempotent and can be safely re-run.

    Args:
        config: Scheduler configuration with batch settings
    """
    logger.info("Starting price refresh job")
    start_time = datetime.now(UTC)
    success_count = 0
    error_count = 0

    try:
        # Create database session
        async with async_session_maker() as session:
            # Get active tickers from watchlist
            watchlist_manager = WatchlistManager(session)
            watchlist_tickers = await watchlist_manager.get_all_active_tickers()

            # Get tickers from recent transactions
            query_handler = GetActiveTickersHandler(session)
            query = GetActiveTickersQuery(days=config.active_stock_days)
            query_result = await query_handler.execute(query)
            transaction_tickers = query_result.tickers

            # Combine and deduplicate
            all_tickers = list(set(watchlist_tickers + transaction_tickers))

            logger.info(
                f"Found {len(all_tickers)} active tickers to refresh "
                f"(watchlist: {len(watchlist_tickers)}, "
                f"transactions: {len(transaction_tickers)})"
            )

            if not all_tickers:
                logger.info("No active tickers to refresh")
                return

            # Get market data adapter (pass session)
            market_data = await get_market_data(session)

            # Process tickers in batches
            for batch_num, i in enumerate(
                range(0, len(all_tickers), config.batch_size), start=1
            ):
                batch = all_tickers[i : i + config.batch_size]

                logger.info(
                    f"Processing batch {batch_num} "
                    f"({len(batch)} tickers): {[t.symbol for t in batch]}"
                )

                # Refresh each ticker in the batch
                for ticker in batch:
                    try:
                        # Fetch current price (this updates cache automatically)
                        price_point = await market_data.get_current_price(ticker)

                        logger.debug(
                            f"Refreshed {ticker.symbol}: {price_point.price} "
                            f"(source: {price_point.source})"
                        )

                        # Update watchlist metadata if ticker is tracked
                        if ticker in watchlist_tickers:
                            now = datetime.now(UTC)
                            next_refresh = now + timedelta(hours=config.max_age_hours)
                            await watchlist_manager.update_refresh_metadata(
                                ticker=ticker,
                                last_refresh=now,
                                next_refresh=next_refresh,
                            )

                        success_count += 1

                    except Exception as e:
                        logger.error(
                            f"Failed to refresh {ticker.symbol}: {e}",
                            exc_info=True,
                        )
                        error_count += 1
                        # Continue to next ticker (don't stop entire batch)

                # Commit after each batch
                await session.commit()

                # Rate limiting: Sleep between batches (except last one)
                if i + config.batch_size < len(all_tickers):
                    import asyncio

                    logger.debug(
                        f"Batch {batch_num} complete. "
                        f"Sleeping {config.batch_delay_seconds}s before next batch"
                    )
                    await asyncio.sleep(config.batch_delay_seconds)

    except Exception as e:
        logger.error(f"Price refresh job failed: {e}", exc_info=True)
        raise

    finally:
        # Log summary
        duration = datetime.now(UTC) - start_time
        logger.info(
            f"Price refresh job completed in {duration.total_seconds():.1f}s: "
            f"{success_count} succeeded, {error_count} failed"
        )


async def calculate_daily_snapshots() -> None:
    """Background job to calculate daily portfolio snapshots.

    This job:
    1. Gets all portfolios
    2. For each portfolio, calculates current snapshot
    3. Saves snapshot to database for analytics

    The job is designed to be idempotent and can be safely re-run.
    Snapshots are upserted (updated if already exist for the date).
    """
    logger.info("Starting daily snapshot calculation job")
    start_time = datetime.now(UTC)

    try:
        # Create database session
        async with async_session_maker() as session:
            # Create repositories
            portfolio_repo = SQLModelPortfolioRepository(session)
            transaction_repo = SQLModelTransactionRepository(session)
            snapshot_repo = SQLModelSnapshotRepository(session)

            # Get market data adapter
            market_data = await get_market_data(session)

            # Create snapshot job service
            snapshot_service = SnapshotJobService(
                portfolio_repo=portfolio_repo,
                transaction_repo=transaction_repo,
                snapshot_repo=snapshot_repo,
                market_data=market_data,
            )

            # Run daily snapshot
            results = await snapshot_service.run_daily_snapshot()

            # Commit all snapshots
            await session.commit()

            logger.info(
                f"Daily snapshot job completed: "
                f"{results['succeeded']}/{results['processed']} succeeded, "
                f"{results['failed']} failed"
            )

    except Exception as e:
        logger.error(f"Daily snapshot job failed: {e}", exc_info=True)
        raise

    finally:
        # Log summary
        duration = datetime.now(UTC) - start_time
        logger.info(f"Daily snapshot job completed in {duration.total_seconds():.1f}s")


async def start_scheduler(config: SchedulerConfig | None = None) -> None:
    """Initialize and start the background scheduler.

    This function creates the APScheduler instance, configures jobs,
    and starts the scheduler. Should be called during application startup.

    Args:
        config: Scheduler configuration (uses defaults if None)
    """
    global _scheduler

    if config is None:
        config = SchedulerConfig()

    if not config.enabled:
        logger.info("Scheduler is disabled in configuration")
        return

    if _scheduler is not None:
        logger.warning("Scheduler already running")
        return

    logger.info("Starting background scheduler")

    # Create scheduler with explicit event loop
    # This ensures the scheduler uses the same event loop as FastAPI
    try:
        event_loop = asyncio.get_running_loop()
        logger.info(f"Using running event loop: {event_loop}")
    except RuntimeError:
        # No running loop, let AsyncIOScheduler create one
        event_loop = None
        logger.warning("No running event loop found, using default")

    _scheduler = AsyncIOScheduler(timezone=config.timezone, event_loop=event_loop)

    # Add refresh job
    _scheduler.add_job(
        refresh_active_stocks,
        trigger=CronTrigger.from_crontab(config.refresh_cron),
        id="refresh_prices",
        name="Refresh Active Stock Prices",
        max_instances=config.max_instances,
        replace_existing=True,
        kwargs={"config": config},
    )

    logger.info(
        f"Scheduled price refresh job with cron: {config.refresh_cron} "
        f"(timezone: {config.timezone})"
    )

    # Add daily snapshot job (midnight UTC)
    _scheduler.add_job(
        calculate_daily_snapshots,
        trigger=CronTrigger(hour=0, minute=0, timezone="UTC"),
        id="daily_portfolio_snapshot",
        name="Calculate Daily Portfolio Snapshots",
        max_instances=1,
        replace_existing=True,
    )

    logger.info("Scheduled daily snapshot job at midnight UTC")

    # Start the scheduler
    _scheduler.start()
    logger.info(
        f"Background scheduler started successfully. "
        f"State: running={_scheduler.running}, "
        f"jobs={len(_scheduler.get_jobs())}"
    )


async def stop_scheduler() -> None:
    """Stop the background scheduler.

    Gracefully shuts down the scheduler and waits for running jobs to complete.
    Should be called during application shutdown.
    """
    global _scheduler

    if _scheduler is None:
        logger.debug("Scheduler not running, nothing to stop")
        return

    logger.info("Stopping background scheduler")
    _scheduler.shutdown(wait=True)
    _scheduler = None
    logger.info("Background scheduler stopped")


def get_scheduler() -> AsyncIOScheduler | None:
    """Get the current scheduler instance.

    Returns:
        The scheduler instance if running, None otherwise
    """
    return _scheduler


def is_scheduler_running() -> bool:
    """Check if scheduler is currently running.

    Returns:
        True if scheduler is running, False otherwise
    """
    return _scheduler is not None and _scheduler.running
