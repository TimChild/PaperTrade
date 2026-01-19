# Task 163: Fix Weekend Cache Validation Tests

**Agent**: backend-swe
**Priority**: HIGH (blocking CI)
**Estimated Effort**: 30-60 minutes

## Objective

Fix 2 failing tests in `test_alpha_vantage_weekend_cache.py` that are blocking CI.

## Problem

Tests `test_historical_request_ending_saturday` and `test_historical_request_ending_sunday` are failing with:
```
assert False is True
Cache incomplete: missing today's data (market closed) last_cached=2026-01-30 requested_end=2026-01-31
```

## Root Cause Analysis

The tests request historical price data through future weekend dates (Jan 31 Saturday, Feb 1 Sunday) from Jan 20-31/Feb 1. The cached data goes through Friday Jan 30 (the last trading day before the weekend).

**Expected behavior**: Cache should be considered complete since Friday is the last trading day before the weekend.

**Actual behavior**: `_is_cache_complete()` returns False, claiming "missing today's data (market closed)".

**Issue**: The condition `if end.date() >= now.date()` catches requests ending on future dates and applies "requesting through today" logic instead of "historical data" logic. This causes the method to check for today's data (Jan 19) instead of recognizing that Jan 30 (Friday) is the last available trading day before the requested weekend end dates.

## Files to Modify

- `backend/src/zebu/adapters/outbound/market_data/alpha_vantage_adapter.py`
  - Method: `_is_cache_complete()` (line ~872)
  - Fix the logic in the "requesting data through today or future dates" branch

## Solution Approach

The `_is_cache_complete()` method needs to properly handle requests that extend into the future but where the last *available* data point is still acceptable (i.e., last trading day).

**Option 1**: Adjust the boundary check logic to recognize when `last_cached` contains the most recent *available* trading day, even if `end` is in the future.

**Option 2**: Change the test dates to not extend into the future (simpler but less comprehensive).

**Recommended**: Option 1 - Fix the implementation to handle this real-world scenario (users requesting "data through this weekend").

## Quality Standards

- ✅ All tests in `test_alpha_vantage_weekend_cache.py` pass
- ✅ No regressions in other tests (`task test:backend` passes)
- ✅ Logic is clear and well-commented
- ✅ Handles edge cases (weekends, holidays, future dates)

## Success Criteria

1. Both failing tests pass
2. All 682 backend tests pass
3. CI is green
4. Code is cleaner/clearer after the fix

## Context

- These tests were added in PR #158 for weekend price handling
- Production code works correctly (serves cached prices on weekends)
- This is purely a test validation issue

## Testing

```bash
# Run the specific failing tests
cd backend && uv run pytest tests/unit/adapters/outbound/market_data/test_alpha_vantage_weekend_cache.py::TestHistoricalRequestsWithWeekendEndDates -v

# Run all weekend cache tests
cd backend && uv run pytest tests/unit/adapters/outbound/market_data/test_alpha_vantage_weekend_cache.py -v

# Run full backend tests
task test:backend
```

## References

- PR #158: Weekend/Holiday Price Handling
- File: `backend/src/zebu/adapters/outbound/market_data/alpha_vantage_adapter.py`
- Tests: `backend/tests/unit/adapters/outbound/market_data/test_alpha_vantage_weekend_cache.py`
