# Price Caching Architecture Analysis

## Current Implementation

### Database (PostgreSQL)
**Storage**: Individual price points per day
- Table: `price_history`
- Unique constraint: `(ticker, timestamp, source, interval)`
- Each row = one price point for one day
- Indexed by: `(ticker, interval, timestamp)`

### Redis Cache
**Storage**: Date range chunks (current approach)
- Key format: `{ticker}:history:{start_date}:{end_date}:{interval}`
- Example: `AAPL:history:2026-01-01:2026-01-31:1day`
- Stores: JSON array of ALL price points in that range

### API Layer (Alpha Vantage)
**Fetches**: Batch data (all available history at once)
- Returns: ~100 days of daily data in one API call
- Rate limit: 5 calls/min, 500/day

## The Problem You Identified

**Caching by date ranges creates cache misses for subset requests:**

1. User requests 1 Month (Jan 1-31) → Cache miss → API call → Stores: `AAPL:history:2026-01-01:2026-01-31:1day`
2. User requests 1 Week (Jan 25-31) → **Cache miss** (different key!) → API call → Rate limit

**Root cause**: Redis cache keys are exact range matches, not flexible.

**Proposed solution in Task 155**: Add subset matching logic to search existing caches

## Your Alternative Approach: Per-Day Caching

### Proposal
Store Redis cache data **per individual day** (matching database granularity):

**Redis Keys**:
```
AAPL:1day:2026-01-01  →  { ticker, price, timestamp, ... }
AAPL:1day:2026-01-02  →  { ticker, price, timestamp, ... }
AAPL:1day:2026-01-03  →  { ticker, price, timestamp, ... }
```

**Cache lookup for range (Jan 1-31)**:
- Check each day: `AAPL:1day:2026-01-01`, `AAPL:1day:2026-01-02`, ...
- Return all cached days found
- Only fetch missing days from database or API

### Advantages ✅

1. **Simpler logic**: No subset matching needed
2. **Better cache utilization**: Any overlapping days are reused
3. **Matches database granularity**: Price points already stored per-day
4. **Partial cache hits**: Can serve some days from cache, fetch rest from DB/API
5. **Easier debugging**: Individual days easier to inspect than large JSON blobs

### Disadvantages ❌

1. **More Redis operations**: `n` GET calls for `n` days vs 1 GET for range
2. **Network overhead**: Redis pipeline needed for efficiency
3. **Memory overhead**: More keys = more Redis metadata per key

### Performance Analysis

**Current approach (range caching)**:
- Best case (exact match): 1 Redis GET → instant
- Worst case (subset): SCAN all keys + filter → Task 155 complexity

**Per-day approach**:
- Best case (all days cached): 30 Redis GETs (pipelined) → ~10-20ms
- Worst case (no cache): 30 Redis GETs → 30 DB queries → ~100ms

## Recommendation

**Yes, per-day caching is simpler and better aligned with your data model.**

### Why It Makes Sense

1. **Database already stores per-day**: The unique constraint is `(ticker, timestamp, interval)` - one row per day
2. **Natural granularity**: Stock prices are daily observations (or intraday intervals)
3. **Simpler code**: No complex subset matching, no SCAN operations
4. **Predictable performance**: Redis pipeline = O(n) where n = days requested

### Implementation Strategy

**Phase 1: Change Redis cache to per-day keys**
- Modify `PriceCache.set_history()` to store each price point individually
- Modify `PriceCache.get_history()` to fetch multiple days via pipeline
- Update TTL logic (same per-day, just applied to individual keys)

**Phase 2: Update Alpha Vantage adapter**
- When API returns 100 days of data, store each day individually in Redis
- Cache lookup checks all requested days, returns partial hits
- Only fetch truly missing days from API

**Phase 3: Optimize**
- Use Redis pipelines (MGET) for batch day fetches
- Consider Redis sorted sets for range queries if needed later

## Code Changes Required

### 1. Update `PriceCache` class

```python
# OLD (range-based)
async def set_history(ticker, start, end, prices, ttl):
    key = f"{ticker}:history:{start}:{end}:{interval}"
    await redis.set(key, json.dumps(prices), ex=ttl)

# NEW (per-day)
async def set_history(ticker, start, end, prices, ttl):
    """Store each price point individually by day."""
    pipeline = self.redis.pipeline()
    for price in prices:
        day = price.timestamp.date().isoformat()
        key = f"{ticker}:{interval}:{day}"
        pipeline.set(key, self._serialize_price(price), ex=ttl)
    await pipeline.execute()

async def get_history(ticker, start, end, interval):
    """Fetch all days in range via pipeline."""
    days = []
    current = start.date()
    while current <= end.date():
        days.append(current)
        current += timedelta(days=1)

    # Batch fetch all days
    pipeline = self.redis.pipeline()
    for day in days:
        key = f"{ticker}:{interval}:{day.isoformat()}"
        pipeline.get(key)

    results = await pipeline.execute()

    # Deserialize found prices
    prices = []
    for result in results:
        if result:
            prices.append(self._deserialize_price(result))

    return prices if prices else None
```

### 2. Simplify `AlphaVantageAdapter`

```python
async def get_price_history(ticker, start, end, interval):
    # Try Redis cache first (per-day lookup)
    cached = await self.price_cache.get_history(ticker, start, end, interval)

    # If we got ALL days from cache, return them
    expected_days = (end - start).days + 1
    if cached and len(cached) == expected_days:
        return cached

    # Partial cache hit - check database for missing days
    cached_dates = {p.timestamp.date() for p in cached} if cached else set()
    db_history = await self.price_repository.get_price_history(...)

    # Combine cached + database
    combined = (cached or []) + db_history
    combined_dates = {p.timestamp.date() for p in combined}

    # If still missing days and not rate limited, fetch from API
    if len(combined_dates) < expected_days:
        if await self.rate_limiter.can_make_request():
            api_data = await self._fetch_daily_history_from_api(ticker)
            # Store ALL days from API in Redis (individually)
            await self.price_cache.set_history(ticker, ..., api_data, ttl)
            await self.price_repository.upsert_prices(api_data)
            return filter_to_range(api_data, start, end)

    # Return best effort (cached + database)
    return sorted(combined, key=lambda p: p.timestamp)
```

## Comparison to Task 155

**Task 155 (subset matching)**:
- Keeps range-based caching
- Adds SCAN logic to find broader cached ranges
- Filters cached data to requested subset
- More complex, harder to debug

**Per-day caching**:
- Changes storage model
- Simpler lookup (pipeline MGET)
- Matches database granularity
- Easier to understand and maintain

## Decision

**Recommendation**: Go with per-day caching.

**Rationale**:
1. Aligns with database storage model (one row per day)
2. Simpler mental model and code
3. Better cache utilization (any overlapping days reused)
4. Scales to intraday intervals naturally (`AAPL:1hour:2026-01-01T14:00`)
5. Avoids Task 155 complexity (SCAN, key parsing, subset filtering)

**Tradeoff**:
- Slightly more Redis operations (pipelined, ~10-20ms for 30 days)
- Worth it for simplicity and maintainability

## Next Steps

1. **Close PR #148** ✅ (already done - band-aid approach)
2. **Cancel Task 155** - Subset matching is unnecessary with per-day caching
3. **Create new Task 156**: Refactor Redis cache to per-day storage
   - Update `PriceCache.set_history()` and `get_history()`
   - Use Redis pipelines for batch operations
   - Update Alpha Vantage adapter to work with per-day cache
   - Comprehensive tests for partial cache hits
   - Migration strategy (old range keys will expire naturally via TTL)
