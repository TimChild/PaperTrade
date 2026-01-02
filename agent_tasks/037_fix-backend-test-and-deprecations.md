# Task 037: Fix Backend Test Failure and SQLAlchemy Deprecation Warnings

**Agent**: backend-swe
**Priority**: P2 (Code Quality)
**Estimated Effort**: 1-2 hours

## Objective

Fix a failing integration test and resolve 129 SQLAlchemy deprecation warnings by migrating from `session.execute()` to SQLModel's `session.exec()`.

## Context

After Phase 2b completion, test suite shows:
- 1 failing test: `test_get_current_price_cache_hit` - cache source attribution incorrect
- 129 deprecation warnings about using SQLAlchemy's deprecated `session.execute()` instead of SQLModel's `session.exec()`

Test run output:
```
FAILED tests/integration/adapters/test_alpha_vantage_adapter.py::TestAlphaVantageAdapterCacheHit::test_get_current_price_cache_hit
AssertionError: assert 'alpha_vantage' == 'cache'
```

Deprecation warnings appear in:
- `portfolio_repository.py` (lines ~60, ~96)
- `transaction_repository.py` (lines ~89, ~119)
- `price_repository.py` (lines ~74, ~137, ~177, ~227, ~255)
- `watchlist_manager.py` (lines ~69, ~111, ~152, ~192, ~214)
- `get_active_tickers.py` (line ~85)

## Requirements

### 1. Fix Cache Source Attribution Test

**File**: `backend/tests/integration/adapters/test_alpha_vantage_adapter.py`

The test expects that when a price is returned from cache, its `source` attribute should be `"cache"` instead of retaining the original source (`"alpha_vantage"`).

**Investigation needed**:
- Check `AlphaVantageAdapter.get_current_price()` implementation
- Verify if cached prices should have their source changed to `"cache"` or if test expectation is wrong
- Review `PricePoint.with_source()` method usage

**Options**:
- A) Update adapter to change source to `"cache"` when returning from cache (likely correct)
- B) Update test to accept original source if that's the intended behavior

### 2. Migrate from session.execute() to session.exec()

**Affected files** (in `backend/src/papertrade/`):
- `adapters/outbound/database/portfolio_repository.py`
- `adapters/outbound/database/transaction_repository.py`
- `adapters/outbound/repositories/price_repository.py`
- `adapters/outbound/repositories/watchlist_manager.py`
- `application/queries/get_active_tickers.py`

**Pattern to replace**:
```python
# OLD (deprecated)
result = await self.session.execute(statement)
items = result.scalars().all()

# NEW (SQLModel recommended)
items = await self.session.exec(statement).all()

# OR for single items:
# OLD
result = await self.session.execute(statement)
item = result.scalar_one_or_none()

# NEW
item = await self.session.exec(statement).one_or_none()
```

**Important**:
- SQLModel's `exec()` returns a `Result` object where `.all()`, `.one()`, `.one_or_none()`, `.first()` work directly
- No need to call `.scalars()` with `exec()`
- Maintain existing behavior - these are drop-in replacements

### 3. Verify All Tests Pass

After changes:
```bash
cd backend
uv run pytest -v
```

Expected: 403 passed, 4 skipped, 0 failed, 0 warnings (related to SQLAlchemy)

## Success Criteria

- [ ] Cache test passes: `test_get_current_price_cache_hit` shows correct source
- [ ] No SQLAlchemy deprecation warnings in test output
- [ ] All 403+ tests passing
- [ ] No behavioral changes - only refactoring deprecated API usage
- [ ] Code follows existing patterns and type hints

## Testing

### Unit Tests
All existing tests should continue to pass.

### Manual Verification
```bash
cd backend
uv run pytest tests/integration/adapters/test_alpha_vantage_adapter.py::TestAlphaVantageAdapterCacheHit -v
uv run pytest -v 2>&1 | grep "DeprecationWarning" | wc -l  # Should be 0
```

## Files to Modify

- `backend/src/papertrade/adapters/outbound/alpha_vantage.py` (possibly)
- `backend/src/papertrade/adapters/outbound/database/portfolio_repository.py`
- `backend/src/papertrade/adapters/outbound/database/transaction_repository.py`
- `backend/src/papertrade/adapters/outbound/repositories/price_repository.py`
- `backend/src/papertrade/adapters/outbound/repositories/watchlist_manager.py`
- `backend/src/papertrade/application/queries/get_active_tickers.py`
- `backend/tests/integration/adapters/test_alpha_vantage_adapter.py` (possibly - if test is wrong)

## References

- SQLModel documentation: https://sqlmodel.tiangolo.com/tutorial/select/
- Backlog item: "Resolve pyright deprecation warnings"
- Test output showing 129 warnings from session test run

## Notes

- This is pure refactoring - no new features
- The deprecation is from SQLAlchemy/SQLModel upstream changes
- Fixing these warnings will clean up test output significantly
- Cache source attribution may be a semantic question - decide whether cached items should show their original source or "cache" as the source
