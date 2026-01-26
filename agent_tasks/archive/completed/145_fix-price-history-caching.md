# Task 145: Fix Price History Caching to Prevent Rate Limiting

**Agent**: backend-swe
**Priority**: HIGH
**Date**: 2026-01-17

## Problem Statement

The `get_price_history()` method in AlphaVantageAdapter is hitting Alpha Vantage API on every request, causing rapid rate limit exhaustion (5 calls/minute). When rate limited, users see:

```json
{"detail":"Market data unavailable: Rate limit exceeded. Cannot fetch historical data at this time."}
```

### Root Cause Analysis

Investigation shows the caching logic is flawed in multiple ways:

1. **Historical data is NOT cached in Redis**: Only `get_current_price()` uses `PriceCache`. The `get_price_history()` method fetches from PostgreSQL and Alpha Vantage API, but never checks/stores in Redis cache.

2. **Database cache is considered "incomplete"**: The `_is_cache_complete()` method is too strict - it requires data up to "today" (end date tolerance of 1 day). When user requests data through today, cached data from yesterday is marked incomplete, triggering API fetch.

3. **Every API fetch stores to database but not Redis**: After fetching from API, data is stored in `price_repository` (PostgreSQL) but not in `PriceCache` (Redis). This means the hot cache layer is bypassed entirely for historical queries.

4. **No TTL awareness for historical data**: Historical price data (e.g., prices from last month) is immutable - it should be cached indefinitely or with very long TTL. Current implementation treats all data equally.

### Evidence from Logs

```
{"event": "Cache query result", "cached_points": 24, "cached_range": "2025-12-18 to 2026-01-17"}
{"event": "Cached data incomplete", "reason": "missing_dates", "requested_range": "2025-12-18 to 2026-01-18"}
{"event": "Fetching from Alpha Vantage API", "reason": "cache_incomplete"}
```

Even with 24 cached points covering 99% of the range, system fetches from API because today's data is "missing".

### Impact

- Users see rate limit errors after 2-3 page refreshes
- Frontend falls back to random mock data (separate issue - Task 146)
- Wasted API quota on redundant fetches
- Poor user experience with inconsistent data

## Objective

Fix the caching implementation for `get_price_history()` to:

1. **Use tiered caching properly**: Redis (Tier 1) → PostgreSQL (Tier 2) → Alpha Vantage API (Tier 3)
2. **Cache historical data in Redis**: Store fetched price history with appropriate TTL
3. **Fix "incomplete" cache detection**: Don't require today's data if it doesn't exist yet (market hours)
4. **Smart cache invalidation**: Historical data is immutable, only invalidate recent data

## Requirements

### 1. Implement Redis Caching for Historical Data

Add a new method to `PriceCache` for caching price history:

```python
async def get_history(
    self,
    ticker: Ticker,
    start: datetime,
    end: datetime,
    interval: str = "1day"
) -> list[PricePoint] | None:
    """Get cached price history for date range."""
    ...

async def set_history(
    self,
    ticker: Ticker,
    prices: list[PricePoint],
    ttl: int | None = None
) -> None:
    """Cache price history with appropriate TTL."""
    ...
```

**Key Design Decisions**:
- Use separate Redis keys for historical ranges (e.g., `papertrade:price:AAPL:history:2025-12-01:2026-01-17`)
- For historical data (older than 1 day), use long TTL (7 days or more)
- For recent data (includes today), use short TTL (1 hour) to allow updates

### 2. Update AlphaVantageAdapter.get_price_history()

Implement proper tiered caching:

```python
async def get_price_history(...) -> list[PricePoint]:
    # Tier 1: Check Redis cache
    cached_history = await self.price_cache.get_history(ticker, start, end, interval)
    if cached_history and self._is_cache_complete(cached_history, start, end):
        return cached_history

    # Tier 2: Check PostgreSQL
    db_history = await self.price_repository.get_price_history(...)
    if db_history and self._is_cache_complete(db_history, start, end):
        # Warm Redis cache
        await self.price_cache.set_history(ticker, db_history, ttl=...)
        return db_history

    # Tier 3: Fetch from API
    if await self.rate_limiter.can_make_request():
        api_history = await self._fetch_daily_history_from_api(ticker)

        # Store in both caches
        await self.price_repository.upsert_prices(api_history)  # PostgreSQL
        await self.price_cache.set_history(ticker, api_history, ttl=...)  # Redis

        return filter_to_range(api_history, start, end)

    # Rate limited - serve partial data if available
    ...
```

### 3. Fix _is_cache_complete() Logic

The current implementation is too strict. Improve it:

```python
def _is_cache_complete(
    self,
    cached_data: list[PricePoint],
    start: datetime,
    end: datetime,
) -> bool:
    """Check if cached data is complete for requested range.

    Improvements:
    - Don't require today's data if market hasn't closed yet
    - Allow 1-day gap for weekends/holidays at boundaries
    - For historical data (end date > 1 day ago), don't expect new data
    """
    # If end date is today and market is open, cache is never complete
    now = datetime.now(UTC)
    market_close_today = now.replace(hour=21, minute=0, second=0, microsecond=0)

    # If requesting data through today and market hasn't closed,
    # we can't have complete data yet
    if end.date() >= now.date() and now < market_close_today:
        # Check if we have data through yesterday
        yesterday = now.date() - timedelta(days=1)
        if cached_data[-1].timestamp.date() >= yesterday:
            # We have data through yesterday, good enough
            return True

    # Original boundary + density checks (keep these)
    ...
```

### 4. Implement Smart TTL Selection

```python
def _calculate_history_ttl(self, prices: list[PricePoint]) -> int:
    """Calculate appropriate TTL based on data recency.

    - Recent data (includes today): 1 hour (data may update)
    - Yesterday's data: 4 hours (market closed, but might get corrections)
    - Older data: 7 days (immutable, long cache)
    """
    now = datetime.now(UTC)
    most_recent = max(p.timestamp for p in prices)

    if most_recent.date() >= now.date():
        return 3600  # 1 hour
    elif most_recent.date() >= (now.date() - timedelta(days=1)):
        return 4 * 3600  # 4 hours
    else:
        return 7 * 24 * 3600  # 7 days
```

## Testing Requirements

### Unit Tests

1. **Test Redis caching for historical data**:
   - `test_get_price_history_uses_redis_cache()`
   - `test_get_price_history_warms_redis_from_db()`
   - `test_get_price_history_stores_api_results_in_redis()`

2. **Test improved cache completeness check**:
   - `test_cache_complete_with_data_through_yesterday()`
   - `test_cache_incomplete_when_missing_recent_data()`
   - `test_historical_cache_complete_without_today()`

3. **Test TTL calculation**:
   - `test_ttl_short_for_recent_data()`
   - `test_ttl_long_for_historical_data()`

4. **Test rate limit avoidance**:
   - `test_cached_data_prevents_api_calls()`
   - `test_multiple_requests_use_cache()`

### Integration Tests

1. **Full cache flow**:
   - First request: API → Store in Redis + PostgreSQL
   - Second request: Served from Redis (no DB query)
   - After Redis TTL expires: Served from PostgreSQL (rewarms Redis)

2. **Rate limit scenario**:
   - Make 6 requests in 1 minute
   - First 5 should succeed (cached after first)
   - 6th should serve from cache, not error

## Success Criteria

- [ ] `PriceCache` has `get_history()` and `set_history()` methods
- [ ] `get_price_history()` checks Redis cache before PostgreSQL
- [ ] Fetched API data is stored in both Redis and PostgreSQL
- [ ] `_is_cache_complete()` doesn't require today's data unnecessarily
- [ ] Historical data uses long TTL, recent data uses short TTL
- [ ] Unit tests verify caching logic (80%+ coverage)
- [ ] Integration test: 10 consecutive requests don't trigger API calls
- [ ] Manual test: Refresh portfolio page 5 times, no rate limit errors

## Non-Requirements

- ❌ Don't change the PostgreSQL repository implementation
- ❌ Don't modify rate limiter behavior
- ❌ Don't change API response format

## References

- **Architecture**: [docs/architecture/technical-boundaries.md](../../docs/architecture/technical-boundaries.md)
- **Current Implementation**: [backend/src/zebu/adapters/outbound/market_data/alpha_vantage_adapter.py](../../backend/src/zebu/adapters/outbound/market_data/alpha_vantage_adapter.py)
- **Cache Module**: [backend/src/zebu/infrastructure/cache/price_cache.py](../../backend/src/zebu/infrastructure/cache/price_cache.py)
- **Related Frontend Issue**: Task 146 (error state handling)

## Example Usage After Fix

```python
# First request (cache miss)
history1 = await adapter.get_price_history(
    Ticker("AAPL"),
    start=datetime(2025, 12, 1),
    end=datetime(2026, 1, 17)
)
# Logs: "Cache miss" → "Fetching from API" → "Stored in Redis + PostgreSQL"

# Second request (Redis cache hit)
history2 = await adapter.get_price_history(
    Ticker("AAPL"),
    start=datetime(2025, 12, 1),
    end=datetime(2026, 1, 17)
)
# Logs: "Redis cache hit" (no DB query, no API call)

# After 8 days (Redis TTL expired, PostgreSQL still has data)
history3 = await adapter.get_price_history(
    Ticker("AAPL"),
    start=datetime(2025, 12, 1),
    end=datetime(2026, 1, 17)
)
# Logs: "Redis miss" → "PostgreSQL hit" → "Warmed Redis cache"
```

## Notes

- This task focuses on backend caching only
- Frontend error handling (showing mock data on errors) is addressed in Task 146
- After this fix, rate limit errors should only occur during initial data population
- Consider adding metrics to track cache hit rates (future enhancement)
