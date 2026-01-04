# ADR 003: Background Refresh Strategy

**Status**: Approved
**Date**: 2025-12-28
**Deciders**: Architecture Team
**Context**: Phase 2 Market Data Integration

## Context

To minimize API calls and provide consistent price data, we need a background refresh strategy that:
1. **Pre-populates** common stocks (AAPL, MSFT, GOOGL, etc.)
2. **Refreshes** prices on a schedule (daily, configurable)
3. **Respects** API rate limits
4. **Handles** errors gracefully (partial success)
5. **Observes** progress and failures

### User Experience Goals

- User opens portfolio → Prices already cached (no wait)
- Historical backtesting → Data already available (no gaps)
- After-hours trading → Prices updated overnight
- New stocks → Lazy-load on first request

## Decision

Implement **APScheduler** (Python background scheduler) with a **daily batch refresh job** that:
- Runs at midnight UTC (configurable cron)
- Refreshes all tracked tickers
- Respects rate limits (batched with delays)
- Logs progress and errors
- Continues on individual failures

### Why APScheduler?

**APScheduler** is a Python library for scheduling tasks (cron-like, interval-based).

| Feature | APScheduler | Celery | GitHub Actions | Manual (while loop) |
|---------|-------------|--------|----------------|---------------------|
| **Complexity** | Low | High | Medium | Low |
| **External Deps** | None | RabbitMQ/Redis | GitHub | None |
| **Persistence** | SQLite/PostgreSQL | Yes | N/A | No |
| **Distributed** | No | Yes | N/A | No |
| **Monitoring** | Logs | Flower | GitHub UI | Custom |
| **Phase 2 Suitable** | ✅ Yes | ❌ Overkill | ❌ External | ⚠️ Fragile |

**Decision**: APScheduler (simple, no new infrastructure, scales to Phase 3)

## Architecture

### Components

#### 1. BackgroundScheduler

**Purpose**: Manages job scheduling and execution

**Configuration**:
```toml
[scheduler]
# Cron expression for daily refresh
refresh_cron = "0 0 * * *"  # Midnight UTC every day

# Job persistence (SQLite for dev, PostgreSQL for prod)
jobstore_url = "${DATABASE_URL}"

# Timezone for cron expressions
timezone = "UTC"

# Maximum job instances running concurrently
max_instances = 1  # Only one refresh job at a time
```

**Jobs**:
- `refresh_all_prices` - Daily price refresh
- (Future: `backfill_history`, `cleanup_stale_data`)

#### 2. PriceRefreshJob

**Purpose**: Fetch and store prices for all tracked tickers

**Algorithm**:
```
1. Get list of all tracked tickers from database
2. Filter to tickers needing refresh (stale data)
3. For each ticker (batched):
   a. Check rate limiter
      - NO TOKENS: Sleep until refill, retry
   b. Fetch price from Alpha Vantage
      - SUCCESS: Store in PostgreSQL, update Redis
      - ERROR: Log error, continue to next ticker
4. Log summary (total/success/errors)
```

**Rate Limiting**:
- Batch size: Based on available tokens
- Inter-batch delay: 60 seconds (respect per-minute limit)
- Total time: ~2 hours for 500 tickers (respects daily limit)

**Error Handling**:
- Individual ticker failure: Log error, continue
- Rate limit exhausted: Sleep until refill
- Redis/PostgreSQL down: Retry after delay, abort if persistent

#### 3. WatchlistManager

**Purpose**: Maintains list of tickers to refresh

**Sources**:
1. **User Portfolios**: All tickers held in any portfolio
2. **Common Stocks**: Pre-defined list (AAPL, MSFT, GOOGL, AMZN, TSLA, etc.)
3. **Recently Queried**: Tickers queried in last 7 days

**Storage**: PostgreSQL table `ticker_watchlist`

| Column | Type | Description |
|--------|------|-------------|
| ticker | VARCHAR(5) | Ticker symbol (unique) |
| source | VARCHAR(20) | How added: "portfolio", "common", "recent" |
| added_at | TIMESTAMP | When added to watchlist |
| last_refreshed_at | TIMESTAMP | Last successful refresh |
| priority | INTEGER | Higher = refresh first (1=critical, 5=normal) |

**Priority Levels**:
1. **Critical (1)**: Held in portfolios, refresh first
2. **High (2)**: Common stocks (large cap indices)
3. **Normal (3)**: Recently queried
4. **Low (5)**: Historical (not queried in >30 days)

### Data Flow

```
Daily Scheduler Trigger (midnight UTC)
  ↓
PriceRefreshJob.execute()
  ↓
WatchlistManager.get_stale_tickers(max_age=24h)
  ↓
For each ticker (ordered by priority):
  ↓
  RateLimiter.can_make_request()?
    YES → AlphaVantageAdapter.fetch_price(ticker)
            ↓
            PriceRepository.save(price)
            ↓
            PriceCache.set(ticker, price, ttl=4h)
    NO → Sleep 60s, retry
  ↓
Log summary: "Refreshed 487/500 tickers, 13 errors"
```

## Alternatives Considered

### Alternative 1: Celery (Distributed Task Queue)

**Pros**:
- Highly scalable (distributed workers)
- Robust retry mechanisms
- Web UI (Flower) for monitoring

**Cons**:
- ❌ Requires RabbitMQ or Redis (additional infrastructure)
- ❌ Complex setup (broker, workers, scheduler)
- ❌ Overkill for Phase 2 scale (single server)
- ❌ Higher operational overhead

**Decision**: **Rejected** - Over-engineering for current needs

**Future**: Consider Celery for Phase 5+ (automation, high scale)

### Alternative 2: GitHub Actions Cron Job

**Implementation**: Scheduled workflow calls API endpoint to trigger refresh

**Pros**:
- Zero infrastructure (uses GitHub)
- Simple configuration (YAML file)
- Familiar to developers

**Cons**:
- ❌ External dependency (GitHub availability)
- ❌ Harder to debug (logs in GitHub UI)
- ❌ Can't react to events (only cron schedule)
- ❌ Awkward for local development

**Decision**: **Rejected** - Too external, limits flexibility

### Alternative 3: FastAPI BackgroundTasks

**Implementation**: Use FastAPI's `BackgroundTasks` for async jobs

**Pros**:
- Built into FastAPI (no new dependency)
- Simple for one-off tasks

**Cons**:
- ❌ Not persistent (lost on server restart)
- ❌ No scheduling (only triggered by requests)
- ❌ No job management (can't list, cancel jobs)
- ❌ Not suitable for cron-like jobs

**Decision**: **Rejected** - Not designed for scheduled jobs

### Alternative 4: Manual Cron + Script

**Implementation**: System cron job calls Python script

**Pros**:
- Simple, no Python library needed
- Uses OS-level scheduler

**Cons**:
- ❌ Requires shell access (not Dockerized)
- ❌ Hard to test (system dependency)
- ❌ No job persistence (can't track history)
- ❌ Awkward for multi-instance deployments

**Decision**: **Rejected** - Not cloud-friendly

### Alternative 5: User-Triggered Refresh Only

**Implementation**: No background job, refresh on user request

**Pros**:
- Simplest (no scheduler)
- Zero background resources

**Cons**:
- ❌ Poor UX (user waits for API calls)
- ❌ Wastes API quota (repeated requests)
- ❌ Doesn't work for historical backtesting

**Decision**: **Rejected** - Defeats purpose of caching

## Rationale for Chosen Approach

### Why APScheduler?

1. **Right-Sized Complexity**: Complex enough for scheduling, simple enough to operate
2. **Python Native**: No language/platform switching
3. **Persistence**: Jobs stored in database (survive restarts)
4. **Testable**: Can run jobs on-demand in tests
5. **Phase 3 Ready**: Can add more jobs (backfill, cleanup)

### Why Daily Refresh (Not Hourly)?

| Frequency | API Calls/Day | Pros | Cons |
|-----------|---------------|------|------|
| Every 5 minutes | 28,800 (500 tickers × 288) | Fresh data | ❌ Exceeds quota |
| Hourly | 12,000 | Frequent updates | ❌ Exceeds quota |
| Every 4 hours | 3,000 | Good balance | ❌ Still exceeds quota |
| **Daily** | **500** | ✅ Fits quota | Stale intraday |
| Weekly | 71 | Under quota | ❌ Too stale |

**Decision**: Daily refresh (midnight UTC)
- **Rationale**: Fits within 500/day quota, acceptable staleness (after-hours updates)
- **Mitigation**: User can manually refresh critical tickers

### Why Midnight UTC?

- **Market Closed**: US markets closed (4 PM ET = 9 PM UTC)
- **Load Balancing**: Low user traffic at midnight
- **Consistent**: Same time every day (no timezone confusion)
- **Log Friendly**: Easy to find in logs (daily "2025-12-28 00:00" entry)

## Implementation Details

### Job Execution Flow

**Phase 1: Preparation** (10 seconds)
1. Load configuration (cron schedule, rate limits)
2. Get watchlist from database (all tracked tickers)
3. Filter to stale tickers (last refresh >24h ago)
4. Sort by priority (portfolio holdings first)

**Phase 2: Batch Processing** (1-2 hours)
1. Split tickers into batches (batch size = rate limit per minute)
2. For each batch:
   - Check rate limiter (wait if needed)
   - Fetch prices in parallel (async)
   - Store in PostgreSQL + Redis
   - Sleep 60 seconds (next batch)

**Phase 3: Cleanup** (10 seconds)
1. Log summary statistics
2. Update job metadata (last run time, success rate)
3. Send alerts if errors exceed threshold

### Error Handling

| Error Type | Behavior | Recovery |
|------------|----------|----------|
| **Single ticker API error** | Log warning, continue | Next refresh attempts again |
| **Rate limit exceeded** | Sleep 60s, retry | Eventually processes all |
| **Redis unavailable** | Skip caching, continue | Prices still stored in PostgreSQL |
| **PostgreSQL down** | Abort job, log error | Retry entire job next cycle |
| **Network timeout** | Retry 3 times, skip ticker | Next refresh attempts again |

### Idempotency

Job is **idempotent**: Running multiple times has same effect as running once.
- Price updates are upserts (insert or update by ticker+timestamp)
- No side effects beyond database writes
- Safe to re-run manually if job fails

### Monitoring

**Job Metadata** (stored in database):

| Field | Description |
|-------|-------------|
| job_id | Unique job execution ID |
| started_at | Job start time |
| completed_at | Job end time |
| tickers_attempted | Total tickers processed |
| tickers_success | Successful refreshes |
| tickers_failed | Failed refreshes |
| errors | JSON array of error messages |

**Alerts**:
- Success rate <90% (too many failures)
- Job duration >4 hours (API too slow or rate-limited)
- Job didn't run (scheduler malfunction)

## Configuration

### Config File (backend/config.toml)

```toml
[scheduler]
# Enable/disable background jobs
enabled = true

# Daily refresh schedule (cron expression)
# Format: "minute hour day month day_of_week"
refresh_cron = "0 0 * * *"  # Midnight UTC

# Job persistence
jobstore = "postgresql"  # or "sqlite" for development
jobstore_url = "${DATABASE_URL}"

# Execution settings
timezone = "UTC"
max_instances = 1  # Only one refresh job at a time
misfire_grace_time = 3600  # 1 hour (if job missed, run within this window)

[scheduler.refresh]
# Which tickers to refresh
sources = ["portfolio", "common", "recent"]

# Staleness threshold (refresh if older than this)
max_age_hours = 24

# Batch processing
batch_size = 5  # Match rate limit per minute
batch_delay_seconds = 60

# Error thresholds
max_error_rate = 0.15  # Alert if >15% errors
retry_failed_after_hours = 6
```

### Common Stocks List

Pre-populate with major indices:
- **Dow 30**: Top 30 blue-chip stocks
- **S&P 100**: Largest 100 companies
- **FAANG**: AAPL, AMZN, GOOGL, META, NFLX
- **Crypto-Related**: COIN, MSTR, RIOT

Total: ~150 tickers (fits well within 500/day quota)

## Testing Strategy

### Unit Tests

Test `PriceRefreshJob` class:
- Watchlist filtering (stale vs fresh)
- Batch sizing logic
- Error handling (continue on failure)
- Rate limit respect (delays between batches)

Use **freezegun** to control time (test midnight trigger).

### Integration Tests

Test with real scheduler:
- Job triggers on cron schedule
- Job persists to database
- Job can be cancelled/re-run

Use **test database** (isolated from production).

### Load Tests

Simulate large watchlist:
- 500 tickers (max for free tier)
- All stale (all need refresh)
- Measure total time (should be <2 hours)

### Manual Testing

Trigger job manually:
```bash
# Via API endpoint (admin only)
curl -X POST http://localhost:8000/api/v1/admin/jobs/refresh-prices

# Via CLI
python -m papertrade.infrastructure.scheduler run-job refresh_all_prices
```

## Consequences

### Positive

- ✅ **Better UX**: Prices pre-cached (fast portfolio loads)
- ✅ **Quota Efficiency**: Batch processing minimizes waste
- ✅ **Phase 3 Ready**: Historical data continuously accumulated
- ✅ **Observable**: Job logs and metrics
- ✅ **Extensible**: Easy to add more jobs later

### Negative

- ⚠️ **Background Complexity**: Need to monitor job health
- ⚠️ **Intraday Staleness**: Prices updated once per day
- ⚠️ **Resource Usage**: Job runs for 1-2 hours daily

### Neutral

- 🔄 **Scheduler Management**: Need to handle job failures
- 🔄 **Configuration**: Cron expressions can be confusing

## Migration & Rollback

### Migration Plan

**Phase 2a** (Week 1):
- Install APScheduler (no jobs yet)
- Test job persistence
- Manual job trigger only

**Phase 2b** (Week 2):
- Enable daily refresh job
- Monitor for 1 week (errors, duration)
- Adjust batch size/delays if needed

### Rollback Plan

If background refresh causes issues:
1. Disable job in config (`enabled = false`)
2. Restart application (job stops)
3. Fall back to on-demand refresh only
4. Fix issue and re-enable

## Future Enhancements

### Phase 3+

- **Backfill Job**: Fill historical gaps (one-time or weekly)
- **Cleanup Job**: Delete old price data (retention policy)
- **Smart Refresh**: Only refresh during market hours
- **Adaptive Scheduling**: Hourly during market, daily after-hours

### Phase 5+

- **Multi-Provider**: Parallel jobs for Alpha Vantage + Finnhub
- **Event-Driven**: Refresh on user portfolio changes
- **Distributed Jobs**: Celery for horizontal scaling

## Operations Guide

### Starting the Scheduler

**Development**:
```bash
# Scheduler starts automatically with FastAPI app
task dev
```

**Production**:
```bash
# Supervisor or systemd ensures scheduler runs
systemctl start papertrade-app
```

### Checking Job Status

**Logs**:
```bash
# Grep for job execution
grep "refresh_all_prices" /var/log/papertrade/app.log

# Sample output:
# 2025-12-28 00:00:00 INFO Job refresh_all_prices started
# 2025-12-28 01:23:45 INFO Refreshed 487/500 tickers, 13 errors
# 2025-12-28 01:23:45 INFO Job refresh_all_prices completed (duration: 1h 23m)
```

**Database**:
```sql
-- Check recent job runs
SELECT * FROM apscheduler_job_runs
ORDER BY started_at DESC
LIMIT 10;
```

### Manually Triggering Job

```bash
# API endpoint (requires admin auth)
curl -X POST http://localhost:8000/api/v1/admin/jobs/refresh-prices

# CLI script
python -m papertrade.infrastructure.scheduler run-now refresh_all_prices
```

## References

- [APScheduler Documentation](https://apscheduler.readthedocs.io/)
- [Cron Expression Syntax](https://crontab.guru/)
- [FastAPI Background Tasks](https://fastapi.tiangolo.com/tutorial/background-tasks/)
- [Celery vs APScheduler](https://www.reddit.com/r/Python/comments/13k9za5/apscheduler_vs_celery/)
