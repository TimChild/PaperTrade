"""Background job scheduler for automated price refresh and maintenance tasks.

This module provides a background scheduler using APScheduler to run periodic jobs
like price refresh, snapshot calculation, and other maintenance tasks without blocking
the main API server.

The scheduler is integrated into the FastAPI application lifecycle and starts/stops
automatically with the application.
"""

import asyncio
import logging
import os
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlmodel.ext.asyncio.session import AsyncSession

from zebu.adapters.inbound.api.dependencies import get_market_data
from zebu.adapters.outbound.anthropic.agent_invocation_adapter import (
    AnthropicAgentInvocationAdapter,
)
from zebu.adapters.outbound.database.api_key_repository import (
    SQLModelApiKeyRepository,
)
from zebu.adapters.outbound.database.exploration_task_repository import (
    SQLModelExplorationTaskRepository,
)
from zebu.adapters.outbound.database.portfolio_cap_adapter import (
    PortfolioCapRepositoryAdapter,
)
from zebu.adapters.outbound.database.portfolio_repository import (
    SQLModelPortfolioRepository,
)
from zebu.adapters.outbound.database.snapshot_repository import (
    SQLModelSnapshotRepository,
)
from zebu.adapters.outbound.database.strategy_activation_repository import (
    SQLModelStrategyActivationRepository,
)
from zebu.adapters.outbound.database.strategy_condition_trigger_repository import (
    SQLModelTriggerRepository,
)
from zebu.adapters.outbound.database.strategy_repository import (
    SQLModelStrategyRepository,
)
from zebu.adapters.outbound.database.transaction_repository import (
    SQLModelTransactionRepository,
)
from zebu.adapters.outbound.database.trigger_fire_repository import (
    SQLModelTriggerFireRepository,
)
from zebu.adapters.outbound.earnings.stub_calendar_adapter import (
    StubEarningsCalendarAdapter,
)
from zebu.adapters.outbound.repositories.watchlist_manager import (
    WatchlistManager,
)
from zebu.application.ports.market_data_port import MarketDataPort
from zebu.application.queries.get_active_tickers import (
    GetActiveTickersHandler,
    GetActiveTickersQuery,
)
from zebu.application.services.snapshot_job import SnapshotJobService
from zebu.application.services.strategy_execution_service import (
    StrategyExecutionService,
)
from zebu.application.services.trigger_evaluation_service import (
    TriggerEvaluationService,
)
from zebu.application.services.trigger_invocation_orchestrator import (
    TriggerInvocationOrchestrator,
)
from zebu.domain.exceptions import AgentInvocationError
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
        strategy_execution_cron: str = "30 0 * * 1-5",
        strategy_execution_enabled: bool = True,
        trigger_evaluation_market_hours_cron: str = "*/15 14-20 * * 1-5",
        trigger_evaluation_off_hours_cron: str = "0 */6 * * *",
        trigger_evaluation_enabled: bool = True,
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
            strategy_execution_cron: Cron expression for the live strategy
                execution job (Phase C1.2). Defaults to 00:30 UTC Mon-Fri,
                which sits ~30 minutes after the price-refresh job at 00:00
                UTC so today's prices are warm before strategies fire. The
                weekday-only restriction matches ``DAILY_MARKET_CLOSE`` —
                US markets are closed on weekends so a weekend run would
                reuse stale Friday prices.
            strategy_execution_enabled: When False, the strategy execution
                job is not registered. Useful for tests / staging where the
                price-refresh job should still run but live trading must
                stay off.
            trigger_evaluation_market_hours_cron: Cron for the Phase F-2
                trigger evaluator during US market hours. Default
                ``*/15 14-20 * * 1-5`` runs every 15 minutes Mon-Fri
                between 14:00 and 20:59 UTC (covers 09:30–17:00 ET ±1
                hour for DST). Drawdown / volatility need timely fires
                during market hours.
            trigger_evaluation_off_hours_cron: Cron for the off-hours
                trigger evaluator. Default ``0 */6 * * *`` (every 6
                hours) catches earnings-proximity fires that may need
                pre-market evaluation. APScheduler can't compose two
                windows in one expression cleanly, so the two crons are
                registered as separate jobs that share the same
                handler.
            trigger_evaluation_enabled: When False, the trigger
                evaluator jobs are not registered. Tests / staging may
                disable them while keeping the rest of the scheduler.
        """
        self.enabled = enabled
        self.refresh_cron = refresh_cron
        self.timezone = timezone
        self.max_instances = max_instances
        self.batch_size = batch_size
        self.batch_delay_seconds = batch_delay_seconds
        self.max_age_hours = max_age_hours
        self.active_stock_days = active_stock_days
        self.strategy_execution_cron = strategy_execution_cron
        self.strategy_execution_enabled = strategy_execution_enabled
        self.trigger_evaluation_market_hours_cron = trigger_evaluation_market_hours_cron
        self.trigger_evaluation_off_hours_cron = trigger_evaluation_off_hours_cron
        self.trigger_evaluation_enabled = trigger_evaluation_enabled


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


async def execute_active_strategies() -> None:
    """Background job to run every active live strategy once.

    Phase C1.2 — wired into the scheduler so each ACTIVE
    :class:`StrategyActivation` is executed once per cycle. The work itself
    (signal generation, transaction creation, error capture) lives in
    :class:`StrategyExecutionService`; this function is just the
    request-scoped wiring + DB transaction boundary.

    Design notes:

    * One DB session for the whole batch. Each per-activation update inside
      ``execute_active_strategies`` is staged on the same unit-of-work and
      committed once at the end. A bug in one activation does not roll
      back the others' status updates because they're persisted as part
      of the same atomic write — the *trades themselves* and the
      ``last_executed_at`` / ``last_error`` mutations are tied together.
    * Errors at the batch level (DB connection drop, market data outage)
      propagate so APScheduler logs them and the operator can see the
      failure. The service's per-activation try/except handles the
      narrower "this strategy misbehaved" case.
    """
    logger.info("Starting strategy execution job")
    start_time = datetime.now(UTC)

    try:
        async with async_session_maker() as session:
            activation_repo = SQLModelStrategyActivationRepository(session)
            strategy_repo = SQLModelStrategyRepository(session)
            portfolio_repo = SQLModelPortfolioRepository(session)
            transaction_repo = SQLModelTransactionRepository(session)
            market_data = await get_market_data(session)

            service = StrategyExecutionService(
                activation_repo=activation_repo,
                strategy_repo=strategy_repo,
                portfolio_repo=portfolio_repo,
                transaction_repo=transaction_repo,
                market_data=market_data,
            )

            summary = await service.execute_active_strategies()
            await session.commit()

            logger.info(
                "Strategy execution job completed: "
                f"{summary['succeeded']}/{summary['processed']} succeeded, "
                f"{summary['failed']} failed, "
                f"{summary['trades']} trades persisted"
            )

    except Exception as exc:
        logger.error(
            f"Strategy execution job failed at batch level: {exc}", exc_info=True
        )
        raise

    finally:
        duration = datetime.now(UTC) - start_time
        logger.info(f"Strategy execution job duration: {duration.total_seconds():.1f}s")


async def evaluate_triggers() -> None:
    """Background job to run one trigger-evaluation cycle.

    Loads every ACTIVE :class:`StrategyConditionTrigger` whose cooldown
    has expired, evaluates each one's condition (DRAWDOWN_THRESHOLD,
    VOLATILITY_SPIKE, or EARNINGS_PROXIMITY), and on fire hands off to
    the :class:`TriggerInvocationOrchestrator` which calls the
    Anthropic Messages API and persists a :class:`TriggerFireRecord`
    audit row.

    The fire handoff is gated behind two safety mechanisms:

    * ``ZEBU_TRIGGER_FIRES_ENABLED`` env var (default ``false``) — the
      service ignores the orchestrator unless this is ``true``. When
      ``false``, the evaluator detects fires but takes no action.
    * Missing ``ANTHROPIC_API_KEY`` — the Anthropic adapter refuses to
      construct, so the service is built with ``orchestrator=None``
      and falls back to "would fire" behavior.

    The actual work lives in :class:`TriggerEvaluationService`; this
    function is the request-scoped wiring + DB transaction boundary.
    Mirrors :func:`execute_active_strategies`.

    Design notes:

    * One DB session for the whole batch — the per-trigger errors are
      caught inside the service so a misbehaving trigger never aborts
      the cycle.
    * Errors at the batch level (DB connection drop, market data
      outage) propagate so APScheduler logs them and the scheduler
      surfaces the failure.
    * The orchestrator owns its own catch-all (it converts every
      failure into an INVOCATION_FAILED audit row), so an Anthropic
      outage does not crash the cycle.

    References:

    * ``docs/architecture/phase-f-agent-in-the-loop.md`` §3 (agent
      decision flow), §5 (scheduler runtime model).
    * ``docs/deployment/production-checklist.md`` — the F-7 procedure
      for enabling fires in production.
    """
    logger.info("Starting trigger evaluation job")
    start_time = datetime.now(UTC)

    try:
        async with async_session_maker() as session:
            trigger_repo = SQLModelTriggerRepository(session)
            activation_repo = SQLModelStrategyActivationRepository(session)
            strategy_repo = SQLModelStrategyRepository(session)
            portfolio_repo = SQLModelPortfolioRepository(session)
            transaction_repo = SQLModelTransactionRepository(session)
            market_data = await get_market_data(session)

            # F-4 default: stub earnings calendar — returns []. Real
            # source attaches via a third-party MCP at runtime per
            # Phase F design Q5. The label is echoed into the audit
            # row's ``source`` field.
            earnings_calendar = StubEarningsCalendarAdapter()

            # F-7 wiring: construct the orchestrator if (a) Anthropic
            # is configured and (b) the feature flag is on. When either
            # check fails, ``orchestrator=None`` and the service stops
            # at "would fire" results (no audit rows, no API calls).
            orchestrator = _try_build_orchestrator(
                session=session,
                trigger_repo=trigger_repo,
                activation_repo=activation_repo,
                strategy_repo=strategy_repo,
                portfolio_repo=portfolio_repo,
                transaction_repo=transaction_repo,
                market_data=market_data,
            )

            service = TriggerEvaluationService(
                trigger_repo=trigger_repo,
                activation_repo=activation_repo,
                strategy_repo=strategy_repo,
                portfolio_repo=portfolio_repo,
                transaction_repo=transaction_repo,
                market_data=market_data,
                earnings_calendar=earnings_calendar,
                earnings_calendar_label="stub",
                orchestrator=orchestrator,
            )

            summary = await service.evaluate_all()
            await session.commit()

            logger.info(
                "trigger_evaluation_completed",
                extra={
                    "processed": summary["processed"],
                    "fired": summary["fired"],
                    "failed": summary["failed"],
                    "skipped": summary["skipped"],
                    "orchestrator_wired": orchestrator is not None,
                },
            )

    except Exception as exc:
        logger.error(
            f"Trigger evaluation job failed at batch level: {exc}", exc_info=True
        )
        raise

    finally:
        duration = datetime.now(UTC) - start_time
        logger.info(f"Trigger evaluation job duration: {duration.total_seconds():.1f}s")


def _try_build_orchestrator(
    *,
    session: AsyncSession,
    trigger_repo: SQLModelTriggerRepository,
    activation_repo: SQLModelStrategyActivationRepository,
    strategy_repo: SQLModelStrategyRepository,
    portfolio_repo: SQLModelPortfolioRepository,
    transaction_repo: SQLModelTransactionRepository,
    market_data: MarketDataPort,
) -> TriggerInvocationOrchestrator | None:
    """Construct the orchestrator if Anthropic is configured.

    The orchestrator depends on a live Anthropic client. Constructing
    the adapter raises :class:`AgentInvocationError` if
    ``ANTHROPIC_API_KEY`` is missing — when that happens we log a
    one-line warning and return ``None`` so the service falls back to
    "would fire" behavior. The evaluator job still runs; it just won't
    invoke an agent.

    The feature flag check is delegated to the service (which already
    reads ``ZEBU_TRIGGER_FIRES_ENABLED``) — we always build the
    orchestrator if Anthropic is configured, and let the service decide
    whether to hand off to it. This way "the flag is on but Anthropic
    isn't configured" produces a clear log line rather than a silent
    no-op deep inside the per-trigger loop.

    Caps for the F-6 per-portfolio per-UTC-day guardrail come from env:

    * ``AGENT_TRADE_DAILY_CAP_COUNT`` (default 10)
    * ``AGENT_TRADE_DAILY_CAP_USD`` (default 5000)

    Args:
        session: Async DB session — shared with the rest of the
            request-scoped repos so the unit of work is consistent.
        trigger_repo: Already-constructed SQL trigger repo.
        activation_repo: Activation repo for the same session.
        strategy_repo: Strategy repo for the same session.
        portfolio_repo: Portfolio repo for the same session.
        transaction_repo: Transaction repo for the same session.
        market_data: Market data port (current-price reads only).

    Returns:
        The orchestrator, or ``None`` if Anthropic isn't configured.
    """
    try:
        agent_adapter = AnthropicAgentInvocationAdapter()
    except AgentInvocationError as exc:
        logger.warning(
            "Trigger orchestrator not wired — Anthropic adapter "
            "construction failed: %s. Triggers will detect fires but "
            "take no action.",
            exc,
        )
        return None

    # F-6 cap: read defaults from env with same names as the docs.
    cap_count = int(os.environ.get("AGENT_TRADE_DAILY_CAP_COUNT", "10"))
    cap_value_usd = Decimal(os.environ.get("AGENT_TRADE_DAILY_CAP_USD", "5000"))

    # The remaining SQL repos (api keys, fire records, exploration tasks,
    # portfolio cap) share the session with the others — single unit of
    # work per cycle.
    fire_repo = SQLModelTriggerFireRepository(session)
    api_key_repo = SQLModelApiKeyRepository(session)
    task_repo = SQLModelExplorationTaskRepository(session)
    portfolio_cap = PortfolioCapRepositoryAdapter(
        session,
        cap_count=cap_count,
        cap_value_usd=cap_value_usd,
    )

    return TriggerInvocationOrchestrator(
        agent_invocation=agent_adapter,
        trigger_repo=trigger_repo,
        trigger_fire_repo=fire_repo,
        activation_repo=activation_repo,
        strategy_repo=strategy_repo,
        portfolio_repo=portfolio_repo,
        transaction_repo=transaction_repo,
        market_data=market_data,
        api_key_repo=api_key_repo,
        exploration_task_repo=task_repo,
        portfolio_cap=portfolio_cap,
    )


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

    # Add live strategy execution job (Phase C1.2). Runs after
    # ``refresh_active_stocks`` so prices for the strategy's tickers are
    # current. ``replace_existing=True`` makes the registration idempotent
    # — calling ``start_scheduler`` twice does not duplicate the job.
    if config.strategy_execution_enabled:
        _scheduler.add_job(
            execute_active_strategies,
            trigger=CronTrigger.from_crontab(
                config.strategy_execution_cron,
                timezone=config.timezone,
            ),
            id="execute_active_strategies",
            name="Execute Active Live Strategies",
            max_instances=config.max_instances,
            replace_existing=True,
        )
        logger.info(
            f"Scheduled live strategy execution job with cron: "
            f"{config.strategy_execution_cron} (timezone: {config.timezone})"
        )
    else:
        logger.info(
            "Live strategy execution job disabled by config "
            "(strategy_execution_enabled=False)"
        )

    # Phase F-2 — trigger evaluation jobs. Two cron windows (market
    # hours every 15 minutes; off-hours every 6 hours) since
    # APScheduler's cron parser can't compose disjoint windows in one
    # expression. Both call the same ``evaluate_triggers`` handler.
    # ``max_instances=1`` so a slow tick can't queue duplicates — the
    # handler itself doesn't take a request-scoped lock so the
    # APScheduler-level limit is the only deduplication mechanism.
    if config.trigger_evaluation_enabled:
        _scheduler.add_job(
            evaluate_triggers,
            trigger=CronTrigger.from_crontab(
                config.trigger_evaluation_market_hours_cron,
                timezone=config.timezone,
            ),
            id="evaluate_triggers_market_hours",
            name="Evaluate Triggers (Market Hours)",
            max_instances=1,
            replace_existing=True,
        )
        _scheduler.add_job(
            evaluate_triggers,
            trigger=CronTrigger.from_crontab(
                config.trigger_evaluation_off_hours_cron,
                timezone=config.timezone,
            ),
            id="evaluate_triggers_off_hours",
            name="Evaluate Triggers (Off Hours)",
            max_instances=1,
            replace_existing=True,
        )
        logger.info(
            "Scheduled trigger evaluation jobs: "
            f"market-hours='{config.trigger_evaluation_market_hours_cron}' "
            f"off-hours='{config.trigger_evaluation_off_hours_cron}' "
            f"(timezone: {config.timezone})"
        )
    else:
        logger.info(
            "Trigger evaluation jobs disabled by config "
            "(trigger_evaluation_enabled=False)"
        )

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
