# Task 059: Phase 3c Analytics - Background Snapshot Job

**Status**: Not Started
**Depends On**: Tasks 056, 057 (Domain & Repository) complete
**Blocks**: Task 060 (Frontend needs data to display)
**Estimated Effort**: 2 days

## Objective

Implement a background job that calculates and stores daily portfolio snapshots for all active portfolios. This enables fast chart rendering without on-demand calculation.

## Reference Architecture

Full specification: `docs/architecture/phase3-refined/phase3c-analytics.md` (see "Background Jobs" section)

## Success Criteria

- [ ] Daily snapshot job calculates snapshots for all portfolios
- [ ] Job runs on schedule (midnight UTC)
- [ ] Job can be triggered manually via API (admin only)
- [ ] Backfill script can generate historical snapshots
- [ ] Error handling with retry logic
- [ ] Job tests pass
- [ ] All existing tests still pass

## Implementation Details

### 1. Snapshot Job Service

**Location**: `backend/app/application/services/snapshot_job.py`

```python
from datetime import date, timedelta
from decimal import Decimal
from typing import Sequence
from uuid import UUID
import logging

from app.application.ports.portfolio_repository import PortfolioRepositoryPort
from app.application.ports.snapshot_repository import SnapshotRepositoryPort
from app.application.ports.market_data import MarketDataPort
from app.domain.entities.portfolio_snapshot import PortfolioSnapshot
from app.domain.services.snapshot_calculator import SnapshotCalculator

logger = logging.getLogger(__name__)

class SnapshotJobService:
    """Service for calculating portfolio snapshots."""

    def __init__(
        self,
        portfolio_repo: PortfolioRepositoryPort,
        snapshot_repo: SnapshotRepositoryPort,
        market_data: MarketDataPort,
    ):
        self._portfolio_repo = portfolio_repo
        self._snapshot_repo = snapshot_repo
        self._market_data = market_data
        self._calculator = SnapshotCalculator()

    async def run_daily_snapshot(self, snapshot_date: date | None = None) -> dict:
        """
        Calculate snapshots for all portfolios for the given date.

        Returns:
            dict with counts: {"processed": N, "succeeded": N, "failed": N}
        """
        target_date = snapshot_date or date.today()
        logger.info(f"Starting daily snapshot for {target_date}")

        portfolios = await self._portfolio_repo.list_all()

        results = {"processed": 0, "succeeded": 0, "failed": 0}

        for portfolio in portfolios:
            results["processed"] += 1
            try:
                snapshot = await self._calculate_snapshot_for_portfolio(
                    portfolio.id, target_date
                )
                await self._snapshot_repo.save(snapshot)
                results["succeeded"] += 1
                logger.debug(f"Snapshot saved for portfolio {portfolio.id}")
            except Exception as e:
                results["failed"] += 1
                logger.error(f"Failed to snapshot portfolio {portfolio.id}: {e}")

        logger.info(
            f"Daily snapshot complete: {results['succeeded']}/{results['processed']} succeeded"
        )
        return results

    async def backfill_snapshots(
        self,
        portfolio_id: UUID,
        start_date: date,
        end_date: date,
    ) -> dict:
        """
        Generate historical snapshots for a portfolio.

        Use for new portfolios or fixing gaps.
        """
        logger.info(f"Backfilling snapshots for {portfolio_id} from {start_date} to {end_date}")

        results = {"processed": 0, "succeeded": 0, "failed": 0}
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
        """Calculate a single snapshot for a portfolio."""
        # Get portfolio state
        portfolio = await self._portfolio_repo.get(portfolio_id)
        if not portfolio:
            raise ValueError(f"Portfolio {portfolio_id} not found")

        # Get current prices for all holdings
        holdings_data: list[tuple[str, int, Decimal]] = []
        for ticker, quantity in portfolio.holdings.items():
            if quantity > 0:
                # For historical snapshots, we'd need get_price_at(ticker, date)
                # For daily snapshots, current price is fine
                price = await self._market_data.get_current_price(ticker)
                holdings_data.append((ticker, quantity, price.price))

        return self._calculator.calculate_snapshot(
            portfolio_id=portfolio_id,
            snapshot_date=snapshot_date,
            cash_balance=portfolio.cash_balance,
            holdings=holdings_data,
        )
```

### 2. Scheduler Integration

**Location**: `backend/app/adapters/scheduler/jobs.py` (update existing)

Add the snapshot job to the existing APScheduler configuration:

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.application.services.snapshot_job import SnapshotJobService

def setup_scheduler(snapshot_job: SnapshotJobService) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()

    # Existing price refresh job...

    # New: Daily snapshot job at midnight UTC
    scheduler.add_job(
        snapshot_job.run_daily_snapshot,
        trigger=CronTrigger(hour=0, minute=0, timezone="UTC"),
        id="daily_portfolio_snapshot",
        name="Calculate daily portfolio snapshots",
        replace_existing=True,
    )

    return scheduler
```

### 3. Admin API Endpoint (Manual Trigger)

**Location**: Update `backend/app/adapters/api/routes/analytics.py`

```python
@router.post("/{portfolio_id}/snapshots", status_code=201)
async def trigger_snapshot(
    portfolio_id: UUID,
    date: date | None = None,
    snapshot_job=Depends(get_snapshot_job),
    current_user=Depends(require_admin),  # Admin only
):
    """Manually trigger a snapshot calculation for a portfolio."""
    results = await snapshot_job.backfill_snapshots(
        portfolio_id=portfolio_id,
        start_date=date or date.today(),
        end_date=date or date.today(),
    )
    return {"status": "completed", "results": results}

@router.post("/snapshots/daily", status_code=201)
async def trigger_daily_snapshots(
    snapshot_job=Depends(get_snapshot_job),
    current_user=Depends(require_admin),  # Admin only
):
    """Manually trigger daily snapshot job for all portfolios."""
    results = await snapshot_job.run_daily_snapshot()
    return {"status": "completed", "results": results}
```

### 4. Dependency Injection

**Location**: Update `backend/app/adapters/api/dependencies.py`

```python
from app.application.services.snapshot_job import SnapshotJobService

def get_snapshot_job(
    portfolio_repo=Depends(get_portfolio_repository),
    snapshot_repo=Depends(get_snapshot_repository),
    market_data=Depends(get_market_data),
) -> SnapshotJobService:
    return SnapshotJobService(portfolio_repo, snapshot_repo, market_data)
```

### 5. Tests

**Location**: `backend/tests/application/test_snapshot_job.py`

Required tests:
- `test_run_daily_snapshot_all_portfolios`
- `test_run_daily_snapshot_handles_failures`
- `test_run_daily_snapshot_empty_portfolios`
- `test_backfill_snapshots_date_range`
- `test_backfill_snapshots_single_day`
- `test_calculate_snapshot_cash_only`
- `test_calculate_snapshot_with_holdings`

**Location**: `backend/tests/api/test_analytics_api.py` (add to existing)

- `test_trigger_snapshot_admin_only`
- `test_trigger_snapshot_success`
- `test_trigger_daily_snapshots_admin_only`

## Implementation Order

1. Create `SnapshotJobService` class
2. Add job to scheduler configuration
3. Add admin API endpoints
4. Update dependency injection
5. Write unit tests for job service
6. Write API tests for admin endpoints
7. Manual testing with scheduler
8. Run full test suite

## Commands

```bash
# Run job tests
cd backend && uv run pytest tests/application/test_snapshot_job.py -v

# Test scheduler manually
cd backend && uv run python -c "from app.adapters.scheduler.jobs import setup_scheduler; print('OK')"

# Full backend test suite
task test:backend
```

## Notes

- Job runs at midnight UTC (00:00) daily
- For backfill, need to handle historical prices (may need `get_price_at(ticker, date)`)
- Admin-only endpoints for manual triggers
- Job should be idempotent (can run multiple times safely)
- Log success/failure counts for monitoring
- Consider rate limiting for backfill operations
- Follow existing scheduler patterns in `backend/app/adapters/scheduler/`
