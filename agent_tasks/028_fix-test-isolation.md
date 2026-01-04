# Task 028: Fix Test Isolation Issue in Portfolio API Integration Tests

**Created**: 2026-01-01
**Agent**: backend-swe
**Estimated Effort**: 1-2 hours
**Dependencies**: None
**Phase**: Quality Improvement

## Objective

Fix the test isolation issue where `test_buy_and_sell_updates_holdings_correctly` fails when run as part of the full test suite but passes when run individually.

## Context

After merging PRs #33-36 (PostgreSQL repository, portfolio use cases integration, test fixes), one integration test shows flaky behavior:

```bash
# Passes individually
pytest tests/integration/test_portfolio_api.py::test_buy_and_sell_updates_holdings_correctly
# ✅ PASSED

# Fails in full suite
pytest tests/
# ❌ FAILED tests/integration/test_portfolio_api.py::test_buy_and_sell_updates_holdings_correctly
# ✅ 380 other tests pass
```

### Root Cause Hypothesis

The new market data integration (PR #34) added singleton dependencies in `dependencies.py`:
- `_redis_client`
- `_http_client`
- `_market_data_adapter`

These global singletons may persist state across tests, causing the integration test to fail when other tests have already initialized these singletons.

## Current Test Setup

**File**: `tests/integration/test_portfolio_api.py`

The failing test likely:
1. Uses the real FastAPI dependency injection
2. Calls endpoints that use `get_market_data()` dependency
3. Expects certain market data state
4. Gets polluted state from earlier tests

**Dependency File**: `src/papertrade/adapters/inbound/api/dependencies.py`

```python
# Global singletons (problematic for tests)
_redis_client: Redis | None = None
_http_client: httpx.AsyncClient | None = None
_market_data_adapter: AlphaVantageAdapter | None = None

async def get_market_data() -> MarketDataPort:
    global _redis_client, _http_client, _market_data_adapter

    if _market_data_adapter is not None:
        return _market_data_adapter

    # Create singletons...
```

## Success Criteria

- [ ] All 381 backend tests pass when run together
- [ ] `test_buy_and_sell_updates_holdings_correctly` passes individually
- [ ] No test isolation issues remain
- [ ] Test fixtures properly clean up global state
- [ ] Solution doesn't break production singleton behavior

## Implementation Details

### Option 1: Add Test Fixture to Reset Singletons (RECOMMENDED)

**File**: `tests/conftest.py`

Add a fixture that resets the global singletons after each test:

```python
import pytest
from papertrade.adapters.inbound.api import dependencies

@pytest.fixture(autouse=True)
async def reset_global_singletons():
    """Reset global singleton dependencies between tests.

    This prevents test isolation issues where one test's market data
    adapter affects another test's behavior.
    """
    yield  # Run the test

    # Clean up after test
    dependencies._redis_client = None
    dependencies._http_client = None
    dependencies._market_data_adapter = None
```

**Pros**:
- Simple fix
- Doesn't change production code
- Preserves singleton behavior in production
- Automatic cleanup for all tests

**Cons**:
- Relies on internal module variables
- May slow tests slightly (recreating connections)

### Option 2: Override Dependency in Integration Tests

**File**: `tests/integration/test_portfolio_api.py`

Override the `get_market_data()` dependency for integration tests:

```python
from fastapi.testclient import TestClient
from papertrade.adapters.inbound.api.dependencies import get_market_data
from papertrade.adapters.outbound.market_data.in_memory_adapter import InMemoryMarketDataAdapter

@pytest.fixture
def client(app):
    """Create test client with overridden dependencies."""
    # Create fresh in-memory adapter for each test
    market_data = InMemoryMarketDataAdapter()

    # Override dependency
    app.dependency_overrides[get_market_data] = lambda: market_data

    with TestClient(app) as client:
        yield client

    # Clean up
    app.dependency_overrides.clear()
```

**Pros**:
- Clean test isolation
- Uses FastAPI's built-in dependency override mechanism
- No global state pollution

**Cons**:
- Requires updating test setup
- May need to seed market data for each test

### Option 3: Make Singletons Request-Scoped (More Complex)

Use FastAPI's dependency caching instead of global variables:

```python
from functools import lru_cache

@lru_cache
async def get_market_data() -> MarketDataPort:
    # FastAPI caches per-request automatically
    # No global state needed
```

**Pros**:
- More FastAPI-idiomatic
- Better for production (easier to test)

**Cons**:
- Requires more refactoring
- May not achieve true singleton behavior across requests

## Recommended Approach

**Use Option 1** (autouse fixture to reset singletons) because:
1. Minimal code changes
2. Preserves production behavior
3. Fixes all potential test isolation issues
4. Easy to understand and maintain

## Testing Strategy

### 1. Reproduce the Issue

```bash
# Run full suite to confirm failure
pytest tests/ -v --tb=short

# Run specific test to confirm it passes
pytest tests/integration/test_portfolio_api.py::test_buy_and_sell_updates_holdings_correctly -v
```

### 2. Apply the Fix

Implement the chosen solution (recommended: Option 1).

### 3. Verify the Fix

```bash
# Run full suite multiple times to ensure stability
pytest tests/ -v
pytest tests/ -v
pytest tests/ -v

# All 381 tests should pass every time
```

### 4. Run in Isolation

```bash
# Confirm individual test still passes
pytest tests/integration/test_portfolio_api.py::test_buy_and_sell_updates_holdings_correctly -v
```

## Additional Investigation

If the recommended fix doesn't work, investigate further:

### Check Test Execution Order

```bash
# Run tests in verbose mode to see order
pytest tests/ -v | grep -E "(PASSED|FAILED)"
```

### Check for Shared Database State

```bash
# Look for tests that might not clean up database
grep -r "papertrade.db" tests/
```

### Check Redis State

The singleton Redis client might have cached data:

```python
# In fixture, add Redis flush
await redis_client.flushdb()
```

## Expected Outcome

After this fix:

```bash
# Full test suite
pytest tests/
# ✅ 381 passed in ~1.5s

# Individual test
pytest tests/integration/test_portfolio_api.py::test_buy_and_sell_updates_holdings_correctly
# ✅ 1 passed in ~0.2s

# Multiple runs (no flakiness)
pytest tests/ && pytest tests/ && pytest tests/
# ✅ All runs pass
```

## Files to Modify

**Primary**:
- `tests/conftest.py` - Add autouse fixture to reset singletons

**Investigate** (if needed):
- `tests/integration/test_portfolio_api.py` - Check test setup/teardown
- `src/papertrade/adapters/inbound/api/dependencies.py` - Review singleton implementation

## References

- pytest autouse fixtures: https://docs.pytest.org/en/stable/reference/fixtures.html#autouse-fixtures
- FastAPI dependency overrides: https://fastapi.tiangolo.com/advanced/testing-dependencies/
- Test isolation patterns: https://docs.pytest.org/en/stable/explanation/goodpractices.html#test-isolation

## Definition of Done

- [ ] All 381 backend tests pass together
- [ ] No flaky test behavior
- [ ] Test runs are deterministic (same result every time)
- [ ] Production singleton behavior preserved
- [ ] Progress doc created with findings and solution
