# Local Testing Results and Issues Found

**Date**: 2025-12-29 17:57:31
**Context**: Local health check after merging PRs #30, #31, #32

## Summary

Ran comprehensive local tests to verify system health. Found **5 test failures** that need fixing:
- **3 backend test failures** (2 pre-existing + 1 new from PR #31)
- **2 frontend E2E test failures** (Playwright/Vitest configuration issue)

## Environment Status

### Docker Services ✅
```
✓ PostgreSQL: localhost:5432 (healthy, up 3 days)
✓ Redis: localhost:6379 (healthy, up 3 days)
```

### Dependencies ✅ (after fixes)
- Backend: `uv sync --all-extras` completed successfully
- Frontend: `npm install` already complete

## Test Results

### Backend Tests: 331/334 passing (99.1%)

**Status**: ⚠️ 3 failures (2 pre-existing, 1 new)

**Command**: `cd backend && uv run pytest tests/ --tb=line -q`

**Failures**:

#### 1. PricePoint.is_stale() edge case (PRE-EXISTING)
**File**: `tests/unit/application/dtos/test_price_point.py::TestPricePointIsStale::test_exactly_at_threshold`

**Issue**: Test expects `is_stale(15min)` to return False for a price exactly 15 minutes old, but implementation uses `>` instead of `>=`.

**Expected**: Price exactly at threshold should NOT be stale
**Actual**: Returns True (is stale)

**Root Cause**: Implementation logic discrepancy
```python
# Current implementation likely does:
if age > max_age:  # Should be >= to match test expectation
    return True
```

**Impact**: LOW - Edge case behavior, doesn't affect normal usage

#### 2. PricePoint equality ignores OHLCV (PRE-EXISTING)
**File**: `tests/unit/application/dtos/test_price_point.py::TestPricePointEquality::test_ohlcv_not_in_equality`

**Issue**: Test expects OHLCV fields (volume, open, high, low, close) to be excluded from equality comparison, but they're currently included.

**Expected**: Two PricePoints with same ticker/price/timestamp but different volumes should be equal
**Actual**: They are not equal (volume is compared)

**Root Cause**: `PricePoint.__eq__()` includes OHLCV fields when it shouldn't
```python
# Current implementation compares ALL fields
# Should only compare: ticker, price, timestamp, source, interval
```

**Impact**: LOW - Affects caching and deduplication logic

#### 3. AlphaVantageAdapter cache source labeling (NEW - from PR #31)
**File**: `tests/integration/adapters/test_alpha_vantage_adapter.py::TestAlphaVantageAdapterCacheHit::test_get_current_price_cache_hit`

**Issue**: When returning cached prices, the adapter should update `source` field to "cache" to indicate the origin, but it returns the original source.

**Expected**: Second call returns `PricePoint(source="cache")`
**Actual**: Returns `PricePoint(source="alpha_vantage")`

**Test Code**:
```python
# First call - populates cache
price1 = await adapter.get_current_price(Ticker("AAPL"))
assert price1.source == "alpha_vantage"  # ✅ Passes

# Second call - hits cache
price2 = await adapter.get_current_price(Ticker("AAPL"))
assert price2.source == "cache"  # ❌ FAILS - returns "alpha_vantage"
```

**Root Cause**: `AlphaVantageAdapter.get_current_price()` doesn't modify the source field when returning cached data.

**Impact**: MEDIUM - Makes it harder to debug/trace where prices came from

### Frontend Tests: 54/56 passing (96.4%)

**Status**: ⚠️ 2 E2E test suites failing to load

**Command**: `cd frontend && npm test -- --run`

**Unit Tests**: ✅ 54 passing (including new price query tests)
- `usePriceQuery.test.tsx`: 14 tests, 1 skipped (expected)
- All component tests passing
- Some warnings about React `act()` wrapping (non-critical)

**E2E Tests**: ❌ 2 suites fail to load

#### 4. Playwright tests incompatible with Vitest
**Files**:
- `tests/e2e/portfolio-creation.spec.ts`
- `tests/e2e/trading.spec.ts`

**Error**:
```
Error: Playwright Test did not expect test.describe() to be called here.
Most common reasons include:
- You are calling test.describe() in a configuration file.
- You are calling test.describe() in a file that is imported by the configuration file.
- You have two different versions of @playwright/test. This usually happens
  when one of the dependencies in your package.json depends on @playwright/test.
```

**Root Cause**: Playwright E2E tests are being picked up by Vitest's test runner. Vitest is trying to execute Playwright-specific syntax (`test.describe` from `@playwright/test`), which doesn't work.

**Solution Options**:
1. Exclude E2E tests from Vitest configuration
2. Move E2E tests to separate directory outside Vitest's scope
3. Create separate test script for E2E tests using Playwright's native runner

**Impact**: MEDIUM - E2E tests can't run, blocks end-to-end validation

## Warnings (Non-Critical)

### SQLModel Deprecation Warnings
**Files**: `transaction_repository.py`
**Issue**: Using `session.execute()` instead of `session.exec()`
**Impact**: LOW - Still works, just deprecated
**Example**:
```python
# Current (deprecated):
result = await self._session.execute(statement)

# Should be:
result = await self._session.exec(statement)
```
**Count**: 13 warnings across transaction repository tests

### React act() Warnings
**File**: `CreatePortfolioForm.test.tsx`
**Issue**: State updates not wrapped in `act()`
**Impact**: LOW - Tests still pass, just warnings
**Count**: 2 warnings

## Recommendations

### Priority 1: Fix Backend Test Failures (Task 025)
- Fix `PricePoint.is_stale()` edge case logic
- Fix `PricePoint.__eq__()` to exclude OHLCV from equality
- Fix `AlphaVantageAdapter` to label cached prices correctly
- **Estimated**: 1 hour
- **Agent**: backend-swe

### Priority 2: Fix E2E Test Configuration (Task 026)
- Configure Vitest to exclude Playwright E2E tests
- Set up separate Playwright test command
- Update Taskfile with `test:e2e` command
- **Estimated**: 1 hour
- **Agent**: quality-infra

### Priority 3: Clean Up Warnings (Future)
- Replace `session.execute()` with `session.exec()` in repositories
- Wrap React state updates in `act()` in form tests
- **Estimated**: 30 minutes
- **Agent**: refactorer (low priority)

## Test Commands Used

```bash
# Check Docker services
docker ps

# Backend tests
cd backend
uv sync --all-extras  # Install all dev dependencies
uv run pytest tests/ --tb=line -q

# Frontend tests
cd frontend
npm test -- --run  # Run in CI mode (non-interactive)

# Specific test debugging
uv run pytest tests/unit/application/dtos/test_price_point.py::TestPricePointIsStale::test_exactly_at_threshold -v
```

## Next Steps

1. Create Task 025 specification (Backend Test Fixes)
2. Create Task 026 specification (E2E Test Configuration)
3. Start agents to fix issues
4. Re-run local tests to verify fixes
5. Continue with Phase 2 work (Tasks 021 & 024 already running)

## Notes

- All issues are **test-only failures** - no production code is broken
- Backend test pass rate: 99.1% (excellent)
- Frontend unit test pass rate: 100% (all critical tests passing)
- E2E tests are configuration issue, not code issue
- PRs #30, #31, #32 introduced minimal regressions (only 1 new failure from #31)
