# Background Price Refresh Scheduler

## Overview

The background price refresh scheduler automatically updates stock prices for actively traded tickers on a configurable schedule. This keeps the cache warm and reduces API calls during peak usage.

## Architecture

The scheduler is built using [APScheduler](https://apscheduler.readthedocs.io/) and integrates into the FastAPI application lifecycle. It runs as part of the main application process and starts/stops automatically with the app.

### Key Components

1. **SchedulerConfig**: Configuration class for scheduler settings
2. **refresh_active_stocks()**: Main job function that refreshes prices
3. **GetActiveTickers**: Query that identifies stocks needing refresh
4. **WatchlistManager**: Manages ticker priorities and refresh metadata

## Configuration

The scheduler is configured in `main.py` with the following defaults:

```python
scheduler_config = SchedulerConfig(
    enabled=True,                    # Enable/disable scheduler
    refresh_cron="0 0 * * *",       # Cron expression (midnight UTC)
    batch_size=5,                    # Tickers per batch (rate limit)
    batch_delay_seconds=12,          # Delay between batches
    active_stock_days=30,            # Consider stocks traded in last N days
    max_age_hours=24,                # Refresh if price older than N hours
    timezone="UTC",                  # Scheduler timezone
    max_instances=1,                 # Max concurrent job instances
)
```

### Cron Expression

The default cron expression `"0 0 * * *"` runs the job daily at midnight UTC.

### Rate Limiting

The scheduler respects Alpha Vantage API rate limits:
- **Free tier**: 5 calls/min, 500 calls/day
- **Batch size**: 5 tickers per batch
- **Batch delay**: 12 seconds (~5 calls/min)

With these settings, refreshing 500 tickers takes ~100 minutes and stays within daily quota.

## How It Works

### 1. Active Ticker Discovery

The scheduler finds tickers that need refresh from two sources:

1. **Watchlist**: Tickers in `ticker_watchlist` table
2. **Recent Transactions**: Tickers traded in the last N days

### 2. Batch Processing

Tickers are processed in batches to respect rate limits.

### 3. Error Handling

The job is designed to be resilient:
- **Single ticker failure**: Logs error, continues to next ticker
- **Batch completion**: Commits after each batch
- **Idempotent**: Safe to re-run if interrupted

## Usage

### Enable/Disable Scheduler

To disable the scheduler:

```python
scheduler_config = SchedulerConfig(enabled=False)
```

### Manual Trigger

Trigger a refresh manually:

```python
from papertrade.infrastructure.scheduler import refresh_active_stocks, SchedulerConfig

config = SchedulerConfig(batch_size=5, batch_delay_seconds=1)
await refresh_active_stocks(config)
```

## Testing

### Unit Tests

```bash
pytest tests/unit/infrastructure/test_scheduler.py -v
pytest tests/unit/application/queries/test_get_active_tickers.py -v
```

## Related Documentation

- [ADR 003: Background Refresh Strategy](../../architecture_plans/20251228_phase2-market-data/adr-003-background-refresh.md)
- [Market Data Architecture](../../architecture_plans/20251228_phase2-market-data/overview.md)
