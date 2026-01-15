# Task 032: Phase 2b - Background Price Refresh Scheduler

## Priority

**MEDIUM** - Keeps price data fresh without manual intervention

## Dependencies

- ⚠️  **BLOCKED** until PR #40 (Task 030 - Trade API fix) is merged
- Should be done after Task 031 (Historical Price Data) or in parallel

## Objective

Implement a background scheduler that automatically refreshes price data for actively traded stocks, ensuring the cache stays warm and reducing API calls during peak usage.

## Context

Currently, price data is fetched on-demand. This causes:
- Slow response times for first user each hour (cache miss)
- Potential rate limit exhaustion during market hours
- Stale data for infrequently traded stocks

**Solution**: Background scheduler pre-populates cache for common stocks.

**Architecture Reference**: [ADR 003: Background Refresh](cci:7://file:///Users/timchild/github/Zebu/architecture_plans/20251228_phase2-market-data/adr-003-background-refresh.md:0:0-0:0)

## Requirements

### 1. Scheduler Infrastructure

Use APScheduler (already in dependencies) to:
- Run daily at configurable time (default: midnight EST)
- Refresh prices for "active" stocks (stocks with recent trades)
- Respect rate limits (5 calls/min, 500/day max)

### 2. Active Stock Identification

Query database to find tickers that:
- Have been traded in last 30 days, OR
- Are in any active portfolio holdings

This ensures we only refresh stocks users care about.

### 3. Batch Refresh Logic

```python
async def refresh_active_stocks():
    """Refresh prices for all active stocks"""
    active_tickers = await get_active_tickers()

    for ticker in active_tickers:
        try:
            # Fetch current price
            price = await market_data.get_current_price(ticker)
            # Cache automatically updated via normal flow

            # Rate limiting: 5/min = ~12 sec between calls
            await asyncio.sleep(12)
        except Exception as e:
            logger.error(f"Failed to refresh {ticker}: {e}")
            continue  # Don't stop entire batch
```

### 4. Configuration

Add to `backend/config.toml`:
```toml
[scheduler]
enabled = true
refresh_cron = "0 0 * * *"  # Daily at midnight
max_stocks_per_run = 500  # Don't exceed daily quota
delay_between_calls = 12  # Seconds (5 calls/min = 12s)

[market_data]
active_stock_days = 30  # Consider stocks traded in last N days
```

### 5. Observability

- Log start/end of each refresh run
- Log per-stock success/failure
- Metrics: stocks_refreshed, errors, duration
- Optional: Slack/email notification on completion

## Implementation Plan

### Step 1: Scheduler Setup

1. Create `backend/src/zebu/scheduler.py`:
```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

scheduler = AsyncIOScheduler()

async def start_scheduler():
    if settings.scheduler.enabled:
        scheduler.add_job(
            refresh_active_stocks,
            CronTrigger.from_crontab(settings.scheduler.refresh_cron),
            id="refresh_prices"
        )
        scheduler.start()
```

2. Initialize in `main.py`:
```python
@app.on_event("startup")
async def startup():
    await start_scheduler()

@app.on_event("shutdown")
async def shutdown():
    scheduler.shutdown()
```

### Step 2: Active Stock Query

Add query to fetch active tickers:
```python
async def get_active_tickers(days: int = 30) -> List[str]:
    """Get tickers with recent activity"""
    cutoff = datetime.now() - timedelta(days=days)

    # From transactions
    traded_tickers = await db.query(
        "SELECT DISTINCT ticker FROM transactions
         WHERE timestamp > ? AND ticker IS NOT NULL",
        cutoff
    )

    # From current holdings
    held_tickers = await db.query(
        "SELECT DISTINCT ticker FROM holdings
         WHERE quantity > 0"
    )

    return list(set(traded_tickers + held_tickers))
```

### Step 3: Refresh Task

Create the actual refresh logic with:
- Rate limiting
- Error handling
- Logging
- Progress tracking

### Step 4: Testing

- Unit test: scheduler configuration
- Integration test: refresh logic with mock market data
- Test: active ticker query returns correct stocks
- Test: rate limiting between calls
- Test: error in one stock doesn't stop batch

## Success Criteria

- [ ] Scheduler starts automatically on app startup
- [ ] Refresh runs at configured time
- [ ] Only active stocks are refreshed
- [ ] Rate limits respected (12s between calls)
- [ ] Errors logged but don't stop batch
- [ ] Cache warmed after refresh
- [ ] Configuration can disable scheduler for development
- [ ] Tests verify scheduler behavior

## Configuration Options

```toml
[scheduler]
enabled = true  # Set to false in dev/test
refresh_cron = "0 0 * * *"  # Cron expression
max_stocks_per_run = 500
delay_between_calls = 12

[market_data]
active_stock_days = 30
pre_populate = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]  # Always refresh these
```

## Testing Strategy

1. **Unit Tests**: Test scheduler configuration parsing
2. **Integration Tests**: Test refresh logic with VCR
3. **Manual Test**:
   ```bash
   # Disable scheduler in config
   # Run refresh manually
   uv run python -c "from zebu.scheduler import refresh_active_stocks; import asyncio; asyncio.run(refresh_active_stocks())"
   ```

## Files to Change

- [ ] `backend/src/zebu/scheduler.py` - New file
- [ ] `backend/src/zebu/main.py` - Register scheduler
- [ ] `backend/config.toml` - Add scheduler section
- [ ] `backend/src/zebu/config.py` - Add scheduler settings
- [ ] `backend/src/zebu/application/queries/` - Add get_active_tickers query
- [ ] Tests for scheduler and refresh logic

## Alternative: Celery

If APScheduler proves insufficient (distributed tasks, retries, etc.), consider migrating to Celery. But APScheduler is simpler for a single-instance deployment.

## Notes

- Start with simple daily refresh
- Phase 3 might add intraday updates (every hour during market hours)
- Consider adding manual refresh endpoint: `POST /api/v1/admin/refresh-prices`
- Scheduler should be disabled in tests (use config override)

## References

- [ADR 003: Background Refresh](cci:7://file:///Users/timchild/github/Zebu/architecture_plans/20251228_phase2-market-data/adr-003-background-refresh.md:0:0-0:0)
- [APScheduler Docs](https://apscheduler.readthedocs.io/)

---

**Created**: January 1, 2026
**Estimated Time**: 4-5 hours
**Agent**: backend-swe
