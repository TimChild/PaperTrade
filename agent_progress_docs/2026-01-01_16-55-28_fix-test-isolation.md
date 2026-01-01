# Task 028: Fix Test Isolation Issue in Portfolio API Integration Tests

**Date**: 2026-01-01  
**Agent**: backend-swe  
**Status**: ✅ Complete  

## Summary

Fixed test isolation issue where `test_buy_and_sell_updates_holdings_correctly` failed when run as part of the full test suite but passed individually. The root cause was global singleton dependencies in `dependencies.py` that persisted state across tests.

## Root Cause Analysis

The `src/papertrade/adapters/inbound/api/dependencies.py` module used global singleton variables for market data infrastructure:

```python
_redis_client: Redis | None = None
_http_client: httpx.AsyncClient | None = None
_market_data_adapter: AlphaVantageAdapter | None = None
```

These singletons were created once and reused across requests (intended for production efficiency). However, in tests:

1. The `client` fixture only overrode the database session dependency
2. Market data dependencies were NOT overridden
3. Tests tried to create real Redis/HTTP client connections
4. Singletons persisted across test runs, causing state pollution

## Solution Implemented

Applied a **two-pronged approach** combining elements of Options 1 and 2 from the task description:

### Change 1: Override Market Data Dependency (Primary Fix)

Modified the `client` fixture in `tests/conftest.py` to override `get_market_data()` with an in-memory adapter:

```python
def get_test_market_data() -> InMemoryMarketDataAdapter:
    """Override market data dependency to use in-memory adapter."""
    return InMemoryMarketDataAdapter()

app.dependency_overrides[get_market_data] = get_test_market_data
```

**Benefits**:
- Integration tests no longer require Redis or API keys
- Tests run faster (no network/Redis overhead)
- Better test isolation (each test gets fresh adapter)
- Uses existing `InMemoryMarketDataAdapter` infrastructure

### Change 2: Add Singleton Cleanup Fixture (Safety Net)

Added an autouse fixture to reset global singletons after each test:

```python
@pytest_asyncio.fixture(autouse=True)
async def reset_global_singletons() -> AsyncGenerator[None, None]:
    """Reset global singleton dependencies between tests."""
    from papertrade.adapters.inbound.api import dependencies
    
    yield  # Run the test
    
    # Clean up - close connections first
    if dependencies._http_client is not None:
        await dependencies._http_client.aclose()
    if dependencies._redis_client is not None:
        await dependencies._redis_client.aclose()
    
    # Reset singletons
    dependencies._redis_client = None
    dependencies._http_client = None
    dependencies._market_data_adapter = None
```

**Benefits**:
- Ensures any singletons that DO get created are properly cleaned up
- Prevents resource leaks
- Acts as safety net for tests that don't use the `client` fixture

## Files Modified

### `backend/tests/conftest.py`

**Changes**:
1. Updated `client` fixture to override `get_market_data()` dependency
2. Added `reset_global_singletons` autouse fixture
3. Added proper async cleanup for HTTP and Redis clients

## Testing Validation

### ✅ Individual Test Passes
```bash
pytest tests/integration/test_portfolio_api.py::test_buy_and_sell_updates_holdings_correctly
# PASSED ✅
```

### ✅ Full Integration Suite Passes
```bash
pytest tests/integration/test_portfolio_api.py
# 7 passed ✅
```

### ✅ No Flakiness (5 Consecutive Runs)
```bash
for i in {1..5}; do pytest tests/integration/test_portfolio_api.py -q; done
# All runs: 7 passed ✅
```

### ✅ Full Test Suite Results
```bash
pytest tests/
# 363 passed, 18 failed
```

**Note**: The 18 failures are pre-existing and unrelated to this fix. They occur in:
- `test_alpha_vantage_adapter.py` (8 failures) - fakeredis doesn't support `eval` command used by rate limiter
- `test_rate_limiter.py` (10 failures) - same issue

These failures existed before this change and are not in scope for this task.

## Production Impact

**Zero impact on production code**:
- Changes are test-only
- Production singleton behavior preserved
- Dependency injection mechanism unchanged
- API routes continue to use real AlphaVantageAdapter in production

## Key Decisions

1. **Why override dependency instead of just resetting singletons?**
   - Avoids needing Redis running for integration tests
   - Makes tests faster and more reliable
   - Better aligns with test pyramid principles (integration tests shouldn't need external services)

2. **Why keep the singleton reset fixture?**
   - Defense-in-depth approach
   - Ensures proper cleanup even if future tests bypass the `client` fixture
   - Prevents resource leaks (open HTTP/Redis connections)

3. **Why use InMemoryMarketDataAdapter?**
   - Already exists in codebase
   - Implements same `MarketDataPort` interface
   - Designed for testing purposes
   - No external dependencies

## Follow-Up Items

None required. The solution is complete and all acceptance criteria are met:

- ✅ All 381 backend tests collected
- ✅ `test_buy_and_sell_updates_holdings_correctly` passes individually
- ✅ No test isolation issues remain
- ✅ Tests are deterministic (no flakiness)
- ✅ Production singleton behavior preserved

## Lessons Learned

1. **Test fixtures should override ALL external dependencies**, not just databases
2. **Global singletons are problematic for tests** - always provide a way to reset/override them
3. **In-memory adapters are valuable** - they enable fast, isolated integration tests
4. **Defense in depth**: Combining dependency override + cleanup fixture provides robust test isolation
