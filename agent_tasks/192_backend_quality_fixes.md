# Task 192: Backend Quality Fixes

**Agent**: backend-swe
**Priority**: High
**Estimated Effort**: 3-5 hours

## Objective

Fix known backend quality issues: 2 failing weekend cache tests and the performance problem when a user has ~50 portfolios.

## Part 1: Fix Weekend Cache Validation Tests (~30min)

### Problem

2 tests in `tests/unit/adapters/outbound/market_data/test_alpha_vantage_weekend_cache.py` are failing:
- `test_historical_request_ending_saturday` (line ~369)
- `test_historical_request_ending_sunday` (line ~410)

Both are in the `TestHistoricalRequestsWithWeekendEndDates` class.

### Root Cause

These tests call `_is_cache_complete()` **without mocking `datetime.now()`**, unlike the working tests in `TestWeekendCacheValidation` which do mock it. Since the test dates (Jan 2026) are now in the past, the method code path depends on the `now` vs `end` comparison to decide which branch to enter.

The `_is_cache_complete()` method is at `src/zebu/adapters/outbound/market_data/alpha_vantage_adapter.py` line ~999.

### Approach

Either:
1. Mock `datetime.now()` in both failing tests (consistent with other working tests), OR
2. Fix `_is_cache_complete()` to properly handle historical weekend end-dates regardless of when the test runs

Option 2 is preferred if it doesn't add undue complexity — the bug is that the logic depends on `now` vs `end` comparison in a way that breaks for historical dates. But option 1 is acceptable if option 2 is too invasive.

### Validation
- Both tests pass
- All existing tests still pass (`task test:backend`)
- No new test-specific code paths in production code

## Part 2: Investigate and Fix 50-Portfolio Performance (~2-4h)

### Problem

The app becomes very slow when a user has ~50 portfolios. E2E tests also time out due to accumulated test portfolios.

### Investigation Areas

**Backend N+1 Pattern:**
- `GET /api/v1/portfolios` (in `adapters/inbound/api/portfolios.py` `list_portfolios()`) returns all portfolios for a user with no pagination
- After listing, the frontend calls `GET /api/v1/portfolios/{id}/balance` individually for **each** portfolio — 50 separate API requests
- The portfolio repository (`adapters/outbound/database/portfolio_repository.py` `get_by_user()`) does a simple `SELECT * WHERE user_id = ? ORDER BY created_at`

**Recommended Investigation Steps:**
1. Profile the `list_portfolios` endpoint with many portfolios
2. Check if the balance endpoint does expensive DB queries per portfolio
3. Look at whether balance data could be included in the list response (avoid N+1)

### Suggested Solutions (validate with investigation first)

1. **Add a batch balance endpoint** or include balance in the list response — this is the highest-impact fix since it eliminates the N+1 API calls
2. **Add pagination** to `list_portfolios` (offset/limit with reasonable default, e.g., 20)
3. **Add database indexes** on `Transaction.portfolio_id` and `Transaction.timestamp` if missing

### Architecture Notes
- Follow Clean Architecture — changes flow through ports and adapters
- The existing pattern: API route → use case handler → repository port → database adapter
- If adding a batch balance endpoint, consider whether it's a new use case or extends the existing list query
- Include balance in the list response DTO if the query can be done efficiently (single join)

### Validation
- All backend tests pass
- New behavior has tests (pagination, batch balance)
- Performance improvement is measurable (e.g., 50 portfolios loads in <1s)

## References
- Backlog items: `BACKLOG.md` - High Priority section
- Architecture: `docs/architecture/` for layer boundaries
- Existing tests: `backend/tests/` for patterns
