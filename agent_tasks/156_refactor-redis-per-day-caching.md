# Task 156: Refactor Redis Cache to Per-Day Storage for Simpler Subset Matching

**Agent**: backend-swe
**Priority**: High
**Estimated Effort**: Medium (2-3 hours)
**Alternative to**: Task 155 (subset matching approach)

## Objective

Refactor the Redis price caching system to store price points **individually per day** instead of in date-range chunks, eliminating the need for complex subset matching logic and aligning cache granularity with the database storage model.

## Context

### Current Problem

When users rapidly switch between time ranges on ticker price graphs, each range triggers unnecessary API requests despite having overlapping data:

**Example scenario**:
1. User views 1 Month (Jan 1-31) → API call → Cached as `AAPL:history:2026-01-01:2026-01-31:1day`
2. User switches to 1 Week (Jan 25-31) → **New API call** (different cache key: `AAPL:history:2026-01-25:2026-01-31:1day`)
3. User switches to 1 Day (Jan 31) → **New API call** (different cache key: `AAPL:history:2026-01-31:2026-01-31:1day`)

Result: 3 API calls for 100% overlapping data → rate limiting → user-facing errors

### Root Cause

**Current Redis cache design** stores price ranges as single chunked JSON blobs:
```python
# Current keys (range-based)
key = f"{ticker}:history:{start_date}:{end_date}:{interval}"
# Example: "AAPL:history:2026-01-01:2026-01-31:1day"
# Value: [{"ticker": "AAPL", "timestamp": "2026-01-01", ...}, ..., {"timestamp": "2026-01-31", ...}]
```

This creates different cache keys for overlapping ranges, causing cache misses.

### Database Reality

The PostgreSQL `price_history` table **already stores prices per-day**:
- Unique constraint: `(ticker, timestamp, source, interval)`
- One row per day per ticker
- Natural granularity: daily price observations

**Cache should match database granularity, not arbitrary date ranges.**

## Requirements

### 1. Change Redis Storage Model to Per-Day Keys

**File**: `backend/src/zebu/infrastructure/cache/price_cache.py`

**Current approach** (range-based):
```python
# Key for entire range
"AAPL:history:2026-01-01:2026-01-31:1day" → [{price1}, {price2}, ..., {price31}]
```

**New approach** (per-day):
```python
# Individual keys per day
"AAPL:1day:2026-01-01" → {ticker: "AAPL", price: 150.25, timestamp: "2026-01-01", ...}
"AAPL:1day:2026-01-02" → {ticker: "AAPL", price: 151.10, timestamp: "2026-01-02", ...}
"AAPL:1day:2026-01-03" → {ticker: "AAPL", price: 149.80, timestamp: "2026-01-03", ...}
```

**Key format**:
```python
def _get_day_key(ticker: Ticker, day: date, interval: str) -> str:
    """Generate Redis key for single day's price.

    Args:
        ticker: Stock ticker
        day: Date of price observation
        interval: Price interval type

    Returns:
        Redis key like "zebu:price:AAPL:1day:2026-01-01"
    """
    return f"{self.key_prefix}:{ticker.symbol}:{interval}:{day.isoformat()}"
```

### 2. Update `set_history()` to Store Individual Days

```python
async def set_history(
    self,
    ticker: Ticker,
    start: datetime,
    end: datetime,
    prices: list[PricePoint],
    interval: str = "1day",
    ttl: int | None = None,
) -> None:
    """Cache price history with per-day keys.

    Stores each price point individually by day, allowing flexible
    range queries without exact key matching.

    Args:
        ticker: Stock ticker
        start: Start of time range (for reference, not used in keys)
        end: End of time range (for reference, not used in keys)
        prices: List of PricePoints to cache
        interval: Price interval type (default: "1day")
        ttl: Time-to-live in seconds (overrides default_ttl if provided)

    Example:
        >>> await cache.set_history(
        ...     Ticker("AAPL"),
        ...     datetime(2026, 1, 1, tzinfo=UTC),
        ...     datetime(2026, 1, 31, tzinfo=UTC),
        ...     price_points,  # 31 days of data
        ...     ttl=7 * 24 * 3600
        ... )
        # Creates 31 individual Redis keys:
        # AAPL:1day:2026-01-01
        # AAPL:1day:2026-01-02
        # ...
        # AAPL:1day:2026-01-31
    """
    # Use Redis pipeline for efficiency (batch operation)
    pipeline = self.redis.pipeline()

    expiration = ttl if ttl is not None else self.default_ttl

    for price in prices:
        day = price.timestamp.date()
        key = self._get_day_key(ticker, day, interval)
        value = self._serialize_price(price)
        pipeline.set(key, value, ex=expiration)

    # Execute all SET operations in one network round-trip
    await pipeline.execute()
```

### 3. Update `get_history()` to Fetch Individual Days

```python
async def get_history(
    self,
    ticker: Ticker,
    start: datetime,
    end: datetime,
    interval: str = "1day",
) -> list[PricePoint] | None:
    """Get cached price history by fetching individual days.

    Uses Redis pipeline (MGET) to efficiently fetch all days in range.
    Returns partial results if only some days are cached.

    Args:
        ticker: Stock ticker to get history for
        start: Start of time range (inclusive)
        end: End of time range (inclusive)
        interval: Price interval type (default: "1day")

    Returns:
        List of cached PricePoints (may be partial), None if no days cached

    Example:
        >>> # User requests Jan 1-31
        >>> history = await cache.get_history(
        ...     Ticker("AAPL"),
        ...     datetime(2026, 1, 1, tzinfo=UTC),
        ...     datetime(2026, 1, 31, tzinfo=UTC)
        ... )
        >>> len(history)  # May return 15 if only 15 days are cached
        15
    """
    # Generate list of all days in range
    days_to_fetch = []
    current = start.date()
    end_date = end.date()

    while current <= end_date:
        days_to_fetch.append(current)
        current += timedelta(days=1)

    # Build pipeline to fetch all days
    pipeline = self.redis.pipeline()
    for day in days_to_fetch:
        key = self._get_day_key(ticker, day, interval)
        pipeline.get(key)

    # Execute all GET operations in one network round-trip
    results = await pipeline.execute()

    # Deserialize found prices (skip None results)
    prices = []
    for result in results:
        if result is not None:
            json_str = result.decode("utf-8") if isinstance(result, bytes) else result
            prices.append(self._deserialize_price(json_str))

    # Return None if no days were cached, otherwise return what we found
    return prices if prices else None
```

### 4. Add Helper Method for Day Key Generation

```python
def _get_day_key(
    self,
    ticker: Ticker,
    day: date,
    interval: str = "1day",
) -> str:
    """Generate Redis key for single day's price.

    Args:
        ticker: Stock ticker
        day: Date of price observation
        interval: Price interval type

    Returns:
        Redis key like "zebu:price:AAPL:1day:2026-01-01"

    Example:
        >>> cache._get_day_key(Ticker("AAPL"), date(2026, 1, 15), "1day")
        'zebu:price:AAPL:1day:2026-01-15'
    """
    return f"{self.key_prefix}:{ticker.symbol}:{interval}:{day.isoformat()}"
```

### 5. Update Alpha Vantage Adapter for Partial Cache Hits

**File**: `backend/src/zebu/adapters/outbound/market_data/alpha_vantage_adapter.py`

The adapter should handle partial cache hits gracefully:

```python
async def get_price_history(...) -> list[PricePoint]:
    # Tier 1: Check Redis cache (per-day lookup)
    cached_prices = await self.price_cache.get_history(ticker, start, end, interval)

    # Calculate which days we have cached
    if cached_prices:
        cached_dates = {p.timestamp.date() for p in cached_prices}
        log.info(
            "Redis partial cache hit",
            cached_days=len(cached_dates),
            total_days=(end - start).days + 1,
        )
    else:
        cached_dates = set()

    # Tier 2: Check PostgreSQL for missing days
    db_history = await self.price_repository.get_price_history(...)
    db_dates = {p.timestamp.date() for p in db_history}

    # Combine cached + database
    all_prices = (cached_prices or []) + db_history
    all_dates = cached_dates | db_dates

    # Tier 3: Fetch from API if still missing days
    expected_days = {start.date() + timedelta(days=i) for i in range((end - start).days + 1)}
    missing_days = expected_days - all_dates

    if missing_days and interval == "1day":
        if await self.rate_limiter.can_make_request():
            await self.rate_limiter.consume_token()
            api_data = await self._fetch_daily_history_from_api(ticker)

            # Store ALL fetched days in Redis (individually)
            await self.price_cache.set_history(ticker, start, end, api_data, interval, ttl=...)

            # Store in PostgreSQL
            await self.price_repository.upsert_prices(api_data)

            # Combine and filter to requested range
            all_prices = all_prices + api_data

    # Filter to requested range and sort
    filtered = [p for p in all_prices if start <= p.timestamp <= end]
    return sorted(filtered, key=lambda p: p.timestamp)
```

### 6. Performance Optimization: Use Redis Pipeline

**Critical**: All multi-day operations MUST use Redis pipelines to avoid N network round-trips.

```python
# BAD - 30 network round-trips for 30 days
for day in days:
    price = await redis.get(key)  # ❌ Individual network call

# GOOD - 1 network round-trip for 30 days
pipeline = redis.pipeline()
for day in days:
    pipeline.get(key)  # ✅ Queued
results = await pipeline.execute()  # ✅ Single network round-trip
```

**Performance target**: <20ms for 30-day range fetch from Redis

## Testing Requirements

### Unit Tests

**File**: `backend/tests/unit/infrastructure/cache/test_price_cache.py`

1. **Test per-day storage**:
   ```python
   async def test_set_history_stores_individual_days():
       """Verify each price point gets its own Redis key."""
       cache = PriceCache(redis, "test:price")
       prices = [
           create_price_point(Ticker("AAPL"), datetime(2026, 1, 1, tzinfo=UTC)),
           create_price_point(Ticker("AAPL"), datetime(2026, 1, 2, tzinfo=UTC)),
       ]

       await cache.set_history(Ticker("AAPL"), start, end, prices)

       # Verify two separate keys exist
       key1 = "test:price:AAPL:1day:2026-01-01"
       key2 = "test:price:AAPL:1day:2026-01-02"
       assert await redis.exists(key1)
       assert await redis.exists(key2)
   ```

2. **Test partial cache hits**:
   ```python
   async def test_get_history_returns_partial_results():
       """Verify partial cache hits return available days."""
       cache = PriceCache(redis, "test:price")

       # Cache only days 1-15
       prices_half = [create_price_point(...) for d in range(1, 16)]
       await cache.set_history(Ticker("AAPL"), ..., prices_half)

       # Request days 1-31
       result = await cache.get_history(Ticker("AAPL"), start=Jan1, end=Jan31)

       # Should return only the 15 days we have
       assert result is not None
       assert len(result) == 15
   ```

3. **Test overlapping ranges reuse cache**:
   ```python
   async def test_overlapping_ranges_reuse_cached_days():
       """Verify time range switching uses cached days."""
       cache = PriceCache(redis, "test:price")

       # Cache 1 month (Jan 1-31)
       month_prices = [create_price_point(...) for d in range(1, 32)]
       await cache.set_history(Ticker("AAPL"), Jan1, Jan31, month_prices)

       # Request 1 week (Jan 25-31) - should find all 7 days in cache
       week_result = await cache.get_history(Ticker("AAPL"), Jan25, Jan31)
       assert len(week_result) == 7

       # Request 1 day (Jan 31) - should find in cache
       day_result = await cache.get_history(Ticker("AAPL"), Jan31, Jan31)
       assert len(day_result) == 1
   ```

4. **Test Redis pipeline usage**:
   ```python
   async def test_set_history_uses_pipeline():
       """Verify set_history uses pipeline for efficiency."""
       mock_pipeline = AsyncMock()
       mock_redis = AsyncMock()
       mock_redis.pipeline.return_value = mock_pipeline

       cache = PriceCache(mock_redis, "test:price")
       prices = [create_price_point(...) for _ in range(30)]

       await cache.set_history(Ticker("AAPL"), ..., prices)

       # Verify pipeline was used
       mock_redis.pipeline.assert_called_once()
       assert mock_pipeline.set.call_count == 30
       mock_pipeline.execute.assert_called_once()
   ```

5. **Test TTL applied to all days**:
   ```python
   async def test_set_history_applies_ttl_to_all_days():
       """Verify custom TTL is applied to all cached days."""
       cache = PriceCache(redis, "test:price")
       prices = [create_price_point(...) for d in range(1, 4)]

       custom_ttl = 7 * 24 * 3600  # 7 days
       await cache.set_history(Ticker("AAPL"), ..., prices, ttl=custom_ttl)

       # Check TTL on all keys
       for day in [1, 2, 3]:
           key = f"test:price:AAPL:1day:2026-01-0{day}"
           ttl = await redis.ttl(key)
           assert custom_ttl - 5 <= ttl <= custom_ttl
   ```

**Test Coverage Goal**: 95%+ on modified methods

### Integration Tests

**File**: `backend/tests/integration/test_price_history_caching.py`

```python
async def test_time_range_switching_uses_per_day_cache():
    """Simulate user rapidly switching time ranges - should reuse cache."""
    adapter = AlphaVantageAdapter(...)
    ticker = Ticker("AAPL")

    # User views 1 month (API call #1)
    month_data = await adapter.get_price_history(
        ticker,
        datetime(2026, 1, 1, tzinfo=UTC),
        datetime(2026, 1, 31, tzinfo=UTC),
        "1day"
    )
    assert len(month_data) == 31
    assert mock_api.call_count == 1

    # User switches to 1 week (should use cached days, NO API call)
    week_data = await adapter.get_price_history(
        ticker,
        datetime(2026, 1, 25, tzinfo=UTC),
        datetime(2026, 1, 31, tzinfo=UTC),
        "1day"
    )
    assert len(week_data) == 7
    assert mock_api.call_count == 1  # No additional API call

    # User switches to 1 day (should use cached day, NO API call)
    day_data = await adapter.get_price_history(
        ticker,
        datetime(2026, 1, 31, tzinfo=UTC),
        datetime(2026, 1, 31, tzinfo=UTC),
        "1day"
    )
    assert len(day_data) == 1
    assert mock_api.call_count == 1  # Still only 1 API call total
```

### E2E Tests

**Reuse from PR #148**: `frontend/tests/e2e/price-chart-timerange.spec.ts`

The E2E test should pass with this implementation:
- Rapid time range switching (1D → 1W → 1M → 3M → 1Y → ALL)
- No rate limit errors
- No "too many requests" messages

## Success Criteria

### Functional Requirements
- ✅ Each price point stored as individual Redis key
- ✅ Range queries fetch multiple days via pipeline
- ✅ Partial cache hits return available days
- ✅ Overlapping ranges reuse cached days
- ✅ No API calls when data exists in cache
- ✅ API calls only for genuinely missing days

### Non-Functional Requirements
- ✅ Performance: <20ms for 30-day fetch from Redis (pipelined)
- ✅ All existing tests still pass (backward compatible behavior)
- ✅ 95%+ test coverage on new/modified code
- ✅ Clear logging for partial cache hits

### Quality Standards
- ✅ Clean Architecture compliance (no violations)
- ✅ Complete type hints (no `Any`)
- ✅ Behavior-focused tests (not implementation-focused)
- ✅ Redis pipelines used for all multi-day operations
- ✅ Performance tested (no N+1 network calls)

### User-Facing Success
- ✅ Users can rapidly switch time ranges without errors
- ✅ No "too many requests" messages
- ✅ Charts load instantly when data is cached
- ✅ E2E test from PR #148 passes

## File Structure

```
backend/src/zebu/infrastructure/cache/
├── price_cache.py  (MODIFY - change to per-day keys)

backend/src/zebu/adapters/outbound/market_data/
├── alpha_vantage_adapter.py  (MODIFY - handle partial cache hits)

backend/tests/unit/infrastructure/cache/
├── test_price_cache.py  (MODIFY - update tests, add 5+ new tests)

backend/tests/integration/
├── test_price_history_caching.py  (MODIFY - time range switching test)

frontend/tests/e2e/
└── price-chart-timerange.spec.ts  (REUSE from PR #148)
```

## Implementation Notes

### Migration Strategy

**No breaking changes required**:
- Old range-based keys will expire naturally via TTL (1-7 days)
- New per-day keys coexist with old keys during transition
- No manual migration script needed

**Cache warming**:
- After deployment, first API call stores data in new per-day format
- Subsequent requests immediately benefit from per-day caching

### Edge Cases to Handle

1. **Empty results**: If no days cached, return `None` (consistent with current behavior)
2. **Single day request**: Works naturally (1-item list)
3. **Future dates**: May have partial data (market still open)
4. **Weekends/holidays**: Cache whatever days are available, don't fail
5. **Different intervals**: Key includes interval (`1day`, `1hour`, etc.)

### Performance Considerations

**Redis pipeline overhead**:
- 30 days: ~1-2ms overhead vs single GET
- 365 days: ~10-15ms overhead vs single GET
- **Worth it**: Eliminates complex subset matching logic

**Memory usage**:
- Per-day keys have more Redis metadata overhead (~50 bytes/key)
- 30 days × 50 bytes = 1.5 KB extra per month per ticker
- Negligible for typical usage (hundreds of tickers)

**Network efficiency**:
- Redis pipelines batch operations in single TCP round-trip
- Latency = 1 RTT regardless of number of keys (up to pipeline limit)

### Future Extensions

This design naturally scales to intraday intervals:
```python
# Hourly data
"AAPL:1hour:2026-01-15T14:00" → {price at 2pm}
"AAPL:1hour:2026-01-15T15:00" → {price at 3pm}

# 5-minute data
"AAPL:5min:2026-01-15T14:30" → {price at 2:30pm}
```

## Comparison to Task 155

**Task 155** (subset matching):
- Keeps range-based caching
- Adds `SCAN` to find broader cached ranges
- Filters cached data to requested subset
- More complex, harder to debug
- Performance: Variable (depends on keyspace size)

**Task 156** (per-day caching):
- Changes storage model to per-day
- Simpler lookup (pipeline MGET)
- Matches database granularity
- Easier to understand and maintain
- Performance: Predictable (O(n) where n = days requested)

## Acceptance Criteria Checklist

- [ ] `_get_day_key()` helper method added
- [ ] `set_history()` stores each price point individually using pipeline
- [ ] `get_history()` fetches individual days using pipeline
- [ ] Partial cache hits return available days (not None)
- [ ] 5+ unit tests added (per-day storage, partial hits, overlapping ranges, pipeline usage, TTL)
- [ ] Integration test added (time range switching simulation)
- [ ] E2E test from PR #148 reused and passing
- [ ] All existing tests pass (no regressions)
- [ ] Performance tested (<20ms for 30-day fetch)
- [ ] Logging added (partial cache hits with day counts)
- [ ] Type hints complete (no `Any`)
- [ ] CI passing (Backend, Frontend, E2E, GitGuardian)
- [ ] Manual testing: Rapidly switch time ranges on live chart → No errors

## Estimated Impact

**Before**:
- 1M → 1W → 1D = 3 API calls → Rate limit exceeded

**After**:
- 1M → 1W → 1D = 1 API call (1M cached per-day, 1W and 1D served from cache)

**API Call Reduction**: ~67% for typical time range switching behavior
**User Experience**: Instant chart updates, no rate limit errors
**Code Simplicity**: -100 lines (no subset matching logic)
**Maintainability**: Easier debugging, clearer intent
