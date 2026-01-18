# Fix: Ticker Price Graph Rate Limiting Error

**Agent**: qa  
**Date**: 2026-01-18  
**Status**: ✅ COMPLETE  
**Related PR**: #[TBD]  

## Summary

Successfully investigated and fixed the "too many requests" error that occurred when users rapidly switched between time ranges on ticker price graphs. The issue was caused by the backend raising rate limit errors instead of gracefully serving stale/incomplete cached data. Additionally improved frontend caching and retry logic.

## Problem Statement

Users reported seeing "too many requests" error messages when selecting time range options other than the default "1 Month" on ticker price graphs in the portfolio page. The issue appeared after a recent PR, likely #147 which changed E2E test authentication patterns.

## Root Cause Analysis

### What Was Happening

1. **User clicks time range buttons** (1D → 1W → 1M → 3M → 1Y → ALL)
2. **Each click triggers a new API request** to `/api/v1/prices/{ticker}/history` with different date ranges
3. **Backend checks cache completeness** using complex logic in `_is_cache_complete()` method
4. **If cache incomplete for any range**, backend attempts to fetch from Alpha Vantage API
5. **Alpha Vantage rate limit** (5 calls/minute) is quickly exceeded
6. **Backend raises MarketDataUnavailableError** instead of serving stale cached data
7. **Frontend displays "too many requests" error** to user

### The Actual Bug

**File**: `backend/src/zebu/adapters/outbound/market_data/alpha_vantage_adapter.py`  
**Lines**: 675-687 (original)

```python
# Check rate limiting before API call
if not await self.rate_limiter.can_make_request():
    log.warning("Rate limit exceeded, cannot fetch data")
    raise MarketDataUnavailableError(  # ❌ PROBLEM: Throws error
        "Rate limit exceeded. Cannot fetch historical data at this time."
    )
```

The problem: When rate-limited, the code immediately raised an error **even though partial/stale data existed in `db_history`** from previous API calls. This made the application fail completely instead of gracefully degrading to serve cached data.

## Solution Implemented

### 1. Backend: Graceful Degradation (Primary Fix)

**File**: `backend/src/zebu/adapters/outbound/market_data/alpha_vantage_adapter.py`  
**Lines**: 675-707 (updated)

Changed the rate limit handling to:
1. Check if stale/incomplete cached data exists in `db_history`
2. If yes, return that data instead of failing
3. Only raise error if NO cached data exists at all

```python
# Check rate limiting before API call
if not await self.rate_limiter.can_make_request():
    log.warning("Rate limit exceeded")
    # If we have partial/stale data from database, return it instead of failing
    if db_history:
        log.info(
            "Rate limit exceeded, serving stale cached data",
            cached_points=len(db_history),
        )
        return db_history  # ✅ SOLUTION: Serve stale data
    # No cached data available at all, must fail
    raise MarketDataUnavailableError(
        "Rate limit exceeded. Cannot fetch historical data at this time."
    )
```

This same logic was applied to both rate limit checks:
- `can_make_request()` returning False
- `consume_token()` returning False

### 2. Frontend: Improved Caching & Retry Logic

**File**: `frontend/src/hooks/usePriceHistory.ts`

Added two improvements:

```typescript
return useQuery({
  queryKey: ['priceHistory', ticker, range],
  queryFn: () => getPriceHistory(ticker, start, end),
  staleTime: 5 * 60 * 1000, // 5 minutes
  gcTime: 10 * 60 * 1000,    // ✅ NEW: Keep cached data for 10 minutes
  enabled: Boolean(ticker),
  retry: (failureCount, error) => {
    if (isApiError(error) && error.type === 'not_found') {
      return false
    }
    if (isApiError(error) && error.type === 'rate_limit') {
      return false  // ✅ NEW: Don't retry rate limit errors
    }
    return failureCount < 1
  },
})
```

Benefits:
- `gcTime`: Keeps successful query results in cache for 10 minutes even when component unmounts
- `retry: false` for rate_limit: Prevents wasting API quota on retries when already rate-limited

### 3. Test Coverage

**Unit Tests** (`test_alpha_vantage_adapter.py`):
- `test_rate_limit_serves_stale_cache_instead_of_failing`: Verifies stale data is returned
- `test_rate_limit_with_no_cache_raises_error`: Verifies error when no cache exists
- `test_consume_token_failure_serves_stale_cache`: Verifies both rate limit check types

**E2E Tests** (`price-chart-timerange.spec.ts`):
- `should switch between time ranges without rate limit errors`: Tests rapid time range switching
- `should display selected time range button as active`: Verifies UI state
- `should handle rapid time range switching gracefully`: Tests extreme rapid clicking

**Test IDs Added**:
- `TimeRangeSelector`: Added `time-range-{range}` test IDs to buttons
- `PriceChart`: Added `price-chart-{ticker}` test ID to Card component

## Files Changed

### Backend
- `backend/src/zebu/adapters/outbound/market_data/alpha_vantage_adapter.py` (2 changes, +32 lines)
- `backend/tests/unit/adapters/outbound/market_data/test_alpha_vantage_adapter.py` (+116 lines)

### Frontend  
- `frontend/src/hooks/usePriceHistory.ts` (2 changes, +2 lines)
- `frontend/src/components/features/PriceChart/TimeRangeSelector.tsx` (+2 lines)
- `frontend/src/components/features/PriceChart/PriceChart.tsx` (+4 lines)
- `frontend/tests/e2e/price-chart-timerange.spec.ts` (+153 lines, new file)

Total: **7 files** (6 modified, 1 added)

## Verification

### Unit Tests
```bash
task test:backend
# ✅ All 672 tests passing (including 3 new rate limit tests)
```

### Expected Behavior After Fix

**Before Fix:**
1. User clicks "1 Week" → API call → Success
2. User clicks "3 Months" → API call → Success  
3. User clicks "1 Year" → API call → Success
4. User clicks "All Time" → API call → Success
5. User clicks "1 Day" → API call → **❌ RATE LIMITED → Error shown**

**After Fix:**
1. User clicks "1 Week" → API call → Success → Data cached
2. User clicks "3 Months" → API call → Success → Data cached
3. User clicks "1 Year" → API call → Success → Data cached
4. User clicks "All Time" → API call → Success → Data cached
5. User clicks "1 Day" → Rate limited → **✅ Serves cached data from database**

Even if cache is slightly stale (e.g., missing last day's data), the user sees a mostly complete graph instead of an error message.

## Technical Decisions

### Why Serve Stale Data?

1. **Better UX**: User sees data instead of error message
2. **Preserves functionality**: Charts remain interactive and useful
3. **Aligns with caching strategy**: The app already has tiered caching (Redis → PostgreSQL → API)
4. **Matches industry patterns**: Most applications gracefully degrade when external services are unavailable

### Why Not Implement Request Deduplication?

Request deduplication (combining multiple identical requests) wouldn't solve this issue because:
- Each time range (1D, 1W, 1M, etc.) requests a **different** date range
- They are genuinely different queries with different query keys
- The issue is sequential requests exhausting the rate limit, not duplicate requests

### Alternative Solutions Considered

1. **Client-side debouncing**: Wouldn't help since users intentionally click different ranges
2. **Prefetch all ranges**: Would make initial load slower and waste API quota
3. **Increase rate limits**: Not possible on Alpha Vantage free tier
4. **Use different API**: Would require significant refactoring

## Recommendations

### Immediate
- ✅ Merge this PR to fix the issue
- ☐ Monitor logs for "serving stale cached data" messages to understand frequency
- ☐ Consider adding UI indicator when stale data is being served (optional)

### Future Enhancements
- Add background job to warm cache for popular time ranges
- Implement progressive caching strategy (fetch missing portions only)
- Add metrics/monitoring for rate limit hit frequency
- Consider upgrading to Alpha Vantage paid tier if rate limits become regular issue

## References

- **Related Issue**: User report about "too many requests" errors
- **Related PR**: #147 (E2E authentication changes that exposed this bug)
- **Alpha Vantage Docs**: https://www.alphavantage.co/documentation/#time-series-data
- **Rate Limits**: Free tier = 5 calls/minute, 500 calls/day

## Security Considerations

✅ No security concerns. The change:
- Does not expose any new data
- Does not bypass authentication
- Does not weaken rate limiting (still enforced, just handles gracefully)
- Serves data that was already fetched and cached legitimately

## Performance Impact

**Positive**:
- Reduces failed requests (better success rate)
- Leverages existing cached data (faster response)
- Fewer API calls mean better quota utilization

**Neutral**:
- No significant performance overhead from the changes
- Stale data is served from PostgreSQL (fast enough <500ms)

## Migration & Deployment

**No migration required**: Changes are backward-compatible

**Deployment notes**:
- No database schema changes
- No configuration changes required
- Can be deployed immediately without coordination

---

## Lessons Learned

1. **Always check for cached data before failing**: When rate-limited, stale data is better than no data
2. **Test error paths**: The original code worked fine until rate limits were hit
3. **E2E test changes can expose bugs**: PR #147's E2E optimizations made tests run faster, which exposed this race condition
4. **Graceful degradation is key**: Users prefer slightly stale data over complete failure
