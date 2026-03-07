# Task 041: Fix Cache Source Attribution Test

**Agent**: backend-swe
**Priority**: P3 (Low - Test Quality)
**Estimated Effort**: 30 minutes

## Objective

Fix the failing integration test `test_get_current_price_cache_hit` which expects cached prices to have source="cache" instead of retaining the original source.

## Context

After successfully fixing 129 SQLAlchemy deprecation warnings in Task #037/PR #49, one test remains failing:

```
FAILED tests/integration/adapters/test_alpha_vantage_adapter.py::TestAlphaVantageAdapterCacheHit::test_get_current_price_cache_hit
AssertionError: assert 'alpha_vantage' == 'cache'
```

**Current Behavior**: When a price is retrieved from cache, it retains the original source (e.g., "alpha_vantage")
**Expected Behavior**: Test expects source to change to "cache"

## Requirements

### 1. Determine Correct Behavior

Review the semantic meaning of the `source` field in `PricePoint`:
- Should it indicate the **original source** of the data (alpha_vantage, yahoo_finance, etc.)?
- Or should it indicate the **retrieval mechanism** (cache, api, database)?

**Recommendation**: The source should likely indicate the **current retrieval mechanism** for observability and debugging purposes. This allows developers to understand if data came from cache vs API.

### 2. Fix Implementation or Test

**Option A: Fix Adapter** (likely correct):
Update `AlphaVantageAdapter.get_current_price()` to change source to "cache" when returning cached data:

```python
async def get_current_price(self, ticker: Ticker) -> PricePoint:
    # Try Redis cache first
    cached_price = await self._redis_cache.get(ticker)
    if cached_price:
        # Change source to indicate cache retrieval
        return cached_price.with_source("cache")

    # Try PostgreSQL cache...
    db_price = await self._price_cache.get_latest_price(ticker)
    if db_price:
        return db_price.with_source("cache")

    # Fetch from API...
    return api_price
```

**Option B: Fix Test** (less likely):
If source should remain as original source, update test expectations to accept "alpha_vantage" instead of "cache".

### 3. Verify All Tests Pass

After fix:
```bash
cd backend
uv run pytest -v
# Expected: 403 passed, 4 skipped, 0 failed
```

## Files to Modify

**If fixing adapter**:
- `backend/src/zebu/adapters/outbound/market_data/alpha_vantage_adapter.py`
- Possibly add `with_source()` method to `PricePoint` if it doesn't exist

**If fixing test**:
- `backend/tests/integration/adapters/test_alpha_vantage_adapter.py`

## Success Criteria

- [ ] Test `test_get_current_price_cache_hit` passes
- [ ] All 403+ tests passing, 0 failed
- [ ] Decision documented: Why source should/shouldn't change to "cache"
- [ ] No behavioral regressions in price fetching

## References

- Task #037 / PR #49: SQLAlchemy deprecation fixes
- `PricePoint` domain entity definition
- AlphaVantage adapter caching strategy

## Notes

- This is a minor test issue that doesn't affect production functionality
- The deprecation warnings fix (main goal of Task #037) was successfully completed
- This test likely wasn't caught earlier because it tests a specific edge case
