# Task 155: Fix Price History Cache to Support Subset Range Matching

**Agent**: backend-swe
**Priority**: High
**Estimated Effort**: Medium (2-3 hours)

## Objective

Fix the price history caching system to recognize when a requested date range is a subset of already-cached data, preventing unnecessary Alpha Vantage API calls when users switch between time ranges (e.g., 1M → 1W → 1D).

## Context

### Current Problem

When users rapidly switch between time ranges on ticker price graphs, each range triggers a new API request despite having overlapping data cached:

**Example scenario**:
1. User views 1 Month (Jan 1-31) → API call → Cached as `AAPL:history:2026-01-01:2026-01-31:1day`
2. User switches to 1 Week (Jan 25-31) → **New API call** (different cache key)
3. User switches to 1 Day (Jan 31) → **New API call** (different cache key)

Result: 3 API calls for data that's 100% overlapping, leading to:
- Alpha Vantage rate limiting (5 calls/min)
- User-facing "too many requests" errors
- Wasted API quota (500 calls/day on free tier)

### Root Cause Analysis

**Redis Cache Implementation**:
```python
# Current cache key format (exact range match only)
key = f"{ticker}:history:{start_date}:{end_date}:{interval}"
```

This creates different cache keys for overlapping ranges:
- `AAPL:history:2026-01-01:2026-01-31:1day` (1 month)
- `AAPL:history:2026-01-25:2026-01-31:1day` (1 week - subset of above!)
- `AAPL:history:2026-01-31:2026-01-31:1day` (1 day - subset of both!)

**The cache lookup (`get_history()`) cannot find broader cached ranges that contain the requested range.**

### Related Work

- PR #148 (QA agent): Band-aid fix that serves stale data when rate-limited
  - This PR should be **closed** once this task is complete
  - Some test coverage from #148 can be reused (E2E tests for time range switching)

## Requirements

### 1. Implement Subset Cache Matching

**File**: `backend/src/zebu/adapters/outbound/market_data/redis_price_cache.py`

Modify `get_history()` method to:

1. **First**: Try exact cache key match (current behavior - fast path)
2. **If miss**: Search for cached ranges that contain the requested range
3. **If found**: Filter the broader cached data to the requested subset
4. **Return**: Filtered subset data

**Algorithm**:
```python
async def get_history(
    self, ticker: Ticker, start: datetime, end: datetime, interval: str
) -> list[PricePoint] | None:
    # 1. Try exact match (fast path - no change)
    exact_key = self._get_cache_key(ticker, start, end, interval)
    exact_data = await self._get_from_redis(exact_key)
    if exact_data:
        return exact_data

    # 2. NEW: Search for broader cached ranges that contain requested range
    # Pattern: {ticker}:history:*:*:{interval}
    pattern = f"{ticker.value}:history:*:*:{interval}"
    matching_keys = await self.redis.keys(pattern)

    for key in matching_keys:
        # Parse start/end from key
        cached_start, cached_end = self._parse_dates_from_key(key)

        # Check if cached range contains requested range
        if cached_start <= start and cached_end >= end:
            # Found a broader range! Get the data and filter it
            cached_data = await self._get_from_redis(key)
            if cached_data:
                # Filter to requested range
                filtered = [
                    p for p in cached_data
                    if start <= p.timestamp <= end
                ]
                if filtered:
                    return filtered

    # 3. No cache hit (exact or subset)
    return None
```

### 2. Add Helper Methods

```python
def _parse_dates_from_key(self, key: str) -> tuple[datetime, datetime]:
    """Parse start and end dates from cache key.

    Example key: 'AAPL:history:2026-01-01T00:00:00+00:00:2026-01-31T23:59:59+00:00:1day'
    """
    # Extract dates from key format
    # Return (start_datetime, end_datetime)

def _is_range_subset(
    self,
    requested_start: datetime,
    requested_end: datetime,
    cached_start: datetime,
    cached_end: datetime
) -> bool:
    """Check if requested range is subset of cached range."""
    return cached_start <= requested_start and cached_end >= requested_end
```

### 3. Performance Considerations

**Concern**: `redis.keys(pattern)` can be slow on large keyspaces

**Mitigation**:
- Use `SCAN` instead of `KEYS` for production (non-blocking)
- Limit to ticker-specific pattern (not `*:history:*`)
- Cache TTL is short (1-7 hours), so keyspace is bounded
- Consider adding a "master key index" for future optimization

**Implementation**:
```python
# Use SCAN for non-blocking iteration
async def _find_broader_cached_ranges(
    self, ticker: Ticker, start: datetime, end: datetime, interval: str
) -> list[PricePoint] | None:
    """Search for cached ranges that contain the requested range."""
    pattern = f"{ticker.value}:history:*:*:{interval}"

    cursor = 0
    while True:
        cursor, keys = await self.redis.scan(
            cursor,
            match=pattern,
            count=100  # Batch size
        )

        for key in keys:
            cached_start, cached_end = self._parse_dates_from_key(key)
            if self._is_range_subset(start, end, cached_start, cached_end):
                cached_data = await self._get_from_redis(key)
                if cached_data:
                    return self._filter_to_range(cached_data, start, end)

        if cursor == 0:
            break

    return None
```

### 4. Update Tests

**File**: `backend/tests/unit/adapters/outbound/market_data/test_redis_price_cache.py`

Add tests for:

1. **Exact match still works** (regression test)
   ```python
   async def test_get_history_exact_match_fast_path():
       # Cache 1 month
       # Request exact same range
       # Should return immediately (fast path)
   ```

2. **Subset matching works**
   ```python
   async def test_get_history_finds_broader_cached_range():
       # Cache Jan 1-31 (1 month)
       # Request Jan 25-31 (1 week subset)
       # Should find and filter the broader range
   ```

3. **Multiple overlapping ranges (pick best fit)**
   ```python
   async def test_get_history_multiple_overlapping_caches():
       # Cache Jan 1-31 (1 month)
       # Cache Jan 15-31 (2 weeks)
       # Request Jan 25-31 (1 week)
       # Should find both, prefer exact match or narrowest fit
   ```

4. **No overlap returns None**
   ```python
   async def test_get_history_no_overlapping_cache():
       # Cache Jan 1-31
       # Request Feb 1-28
       # Should return None (trigger API call)
   ```

5. **Partial overlap returns None** (don't serve incomplete data)
   ```python
   async def test_get_history_partial_overlap_returns_none():
       # Cache Jan 1-31
       # Request Jan 25 - Feb 5 (extends beyond cache)
       # Should return None (not a complete subset)
   ```

**Test Coverage Goal**: 95%+ on new/modified methods

### 5. Integration Test

**File**: `backend/tests/integration/test_price_history_caching.py`

End-to-end test simulating user behavior:

```python
async def test_time_range_switching_uses_cache():
    """Simulate user rapidly switching time ranges on price chart."""
    adapter = AlphaVantageAdapter(...)
    ticker = Ticker("AAPL")

    # User views 1 month (API call)
    month_data = await adapter.get_price_history(
        ticker,
        datetime(2026, 1, 1),
        datetime(2026, 1, 31),
        "1day"
    )
    assert len(month_data) > 0
    # Verify API was called
    assert mock_alpha_vantage.call_count == 1

    # User switches to 1 week (should use cache)
    week_data = await adapter.get_price_history(
        ticker,
        datetime(2026, 1, 25),
        datetime(2026, 1, 31),
        "1day"
    )
    assert len(week_data) > 0
    # Verify NO additional API call
    assert mock_alpha_vantage.call_count == 1

    # User switches to 1 day (should use cache)
    day_data = await adapter.get_price_history(
        ticker,
        datetime(2026, 1, 31),
        datetime(2026, 1, 31),
        "1day"
    )
    assert len(day_data) > 0
    # Verify STILL no additional API calls
    assert mock_alpha_vantage.call_count == 1
```

### 6. Reuse E2E Tests from PR #148

The E2E test `price-chart-timerange.spec.ts` from PR #148 should pass with this fix:
- Rapid time range switching (1D → 1W → 1M → 3M → 1Y → ALL)
- No rate limit errors
- No "too many requests" messages

**Action**: Cherry-pick the E2E test file from PR #148:
```bash
git fetch origin pull/148/head:pr-148
git checkout pr-148 -- frontend/tests/e2e/price-chart-timerange.spec.ts
```

## Success Criteria

### Functional Requirements
- ✅ Exact cache key matches still work (fast path)
- ✅ Subset requests find broader cached data
- ✅ Filtered data is correct (only returns requested range)
- ✅ No API calls when data exists in cache
- ✅ API calls still happen when genuinely new data needed

### Non-Functional Requirements
- ✅ Performance: Subset matching adds <50ms latency
- ✅ Use `SCAN` instead of `KEYS` (non-blocking)
- ✅ All existing tests still pass
- ✅ 95%+ test coverage on new code

### Quality Standards
- ✅ Clean Architecture compliance (no violations)
- ✅ Complete type hints (no `Any`)
- ✅ Behavior-focused tests (not implementation-focused)
- ✅ Clear logging for cache hits/misses (aid debugging)
- ✅ Performance tested (no N+1 queries, no blocking operations)

### User-Facing Success
- ✅ Users can rapidly switch time ranges without errors
- ✅ No "too many requests" messages
- ✅ Charts load instantly when data is cached
- ✅ E2E test from PR #148 passes

## File Structure

```
backend/src/zebu/adapters/outbound/market_data/
├── redis_price_cache.py  (MODIFY - add subset matching)
└── alpha_vantage_adapter.py  (no changes needed)

backend/tests/unit/adapters/outbound/market_data/
├── test_redis_price_cache.py  (ADD - 5+ new tests)

backend/tests/integration/
├── test_price_history_caching.py  (ADD - end-to-end cache test)

frontend/tests/e2e/
└── price-chart-timerange.spec.ts  (REUSE from PR #148)
```

## Implementation Notes

### Edge Cases to Handle

1. **Empty cached data**: If broader range exists but has no data, continue searching
2. **Multiple matches**: Prefer narrowest fit (least filtering needed)
3. **Timezone handling**: Ensure datetime comparisons use UTC consistently
4. **Key parsing errors**: Handle malformed keys gracefully (log warning, skip)

### Performance Optimization Ideas (Future)

1. **Master index key**: Maintain a sorted set of all cached ranges per ticker
   ```python
   # Redis sorted set: {ticker}:history:index
   # Members: "2026-01-01:2026-01-31" with score = timestamp
   ```

2. **LRU eviction awareness**: Don't rely on keys that might be evicted
3. **Prefetch common ranges**: Background job warms cache for popular stocks
4. **Compression**: Store price data as compressed JSON for larger ranges

### Backward Compatibility

- Existing cache keys continue to work (exact match path)
- No database migrations needed
- No breaking changes to public APIs
- Redis TTL behavior unchanged

## Testing Strategy

### Unit Tests (Fast - ~10ms each)
- Helper methods (`_parse_dates_from_key`, `_is_range_subset`)
- Cache lookup logic (exact match, subset match, no match)
- Edge cases (empty data, malformed keys, timezone issues)

### Integration Tests (Medium - ~100ms each)
- Full adapter flow (API → Redis → PostgreSQL)
- Cache warming and retrieval
- Time range switching simulation

### E2E Tests (Slow - ~10s)
- Real user interaction with price charts
- Rapid time range switching
- No rate limit errors

**Run locally before PR**:
```bash
task test:backend          # All backend tests
task test:e2e              # E2E tests
```

## References

- **PR #148**: Band-aid fix (close after this is merged)
- **Architecture**: `docs/architecture/technical-boundaries.md`
- **Redis Cache**: `backend/src/zebu/adapters/outbound/market_data/redis_price_cache.py`
- **Alpha Vantage Adapter**: `backend/src/zebu/adapters/outbound/market_data/alpha_vantage_adapter.py`
- **Rate Limiting**: 5 calls/min, 500 calls/day (Alpha Vantage free tier)

## Acceptance Criteria Checklist

- [ ] Subset cache matching implemented with `SCAN` (non-blocking)
- [ ] Helper methods added (`_parse_dates_from_key`, `_is_range_subset`, etc.)
- [ ] 5+ unit tests added (exact match, subset match, edge cases)
- [ ] Integration test added (time range switching simulation)
- [ ] E2E test from PR #148 reused and passing
- [ ] All existing tests pass (no regressions)
- [ ] Performance tested (subset matching <50ms)
- [ ] Logging added (cache hit/miss with reason)
- [ ] Type hints complete (no `Any`)
- [ ] CI passing (Backend, Frontend, E2E, GitGuardian)
- [ ] PR #148 closed after this merges
- [ ] Manual testing: Rapidly switch time ranges on live chart → No errors

## Estimated Impact

**Before**:
- 1M → 1W → 1D = 3 API calls → Rate limit exceeded

**After**:
- 1M → 1W → 1D = 1 API call (1M cached, 1W and 1D served from cache)

**API Call Reduction**: ~67% for typical time range switching behavior
**User Experience**: Instant chart updates, no rate limit errors
**Quota Savings**: Extends 500 calls/day limit significantly
