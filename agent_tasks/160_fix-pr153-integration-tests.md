# Task 160: Fix Integration Tests for Weekend Price Fetching (PR #153)

**Agent**: backend-swe
**Priority**: High
**Estimated Effort**: 1-2 hours
**Created**: 2026-01-18
**Base Branch**: copilot/fix-weekend-price-fetching (PR #153)

## Problem Statement

PR #153 successfully implements weekend price fetching logic, but 7 integration tests fail when run on actual weekends (Sunday, Jan 18, 2026) because they don't mock datetime. The code changes are correct - the test failures actually **prove** the weekend detection is working!

**Current Situation**:
- ✅ Code implementation is correct
- ✅ 10 new unit tests pass (they mock datetime properly)
- ❌ 7 existing integration tests fail on weekends (they use real datetime)
- ❌ CI blocking merge because tests run on Sunday

**Test Failures**: Integration tests in `backend/tests/integration/test_prices_api.py` that call price endpoints are getting weekend behavior instead of weekday behavior.

## Root Cause

Integration tests use real `datetime.now()` which returns Sunday. The new weekend detection code correctly identifies it's a non-trading day and returns cached prices instead of attempting API calls. Tests expect API calls to happen.

## Required Changes

### Approach: Refactor for Testability (PREFERRED)

Instead of mocking datetime globally, refactor the code to accept an optional datetime parameter for testing. This is cleaner and more explicit.

**Files to Modify**:

#### 1. `backend/src/zebu/adapters/outbound/market_data/alpha_vantage_adapter.py`

Add optional `current_time` parameter to methods:

```python
async def get_current_price(
    self,
    ticker: Ticker,
    current_time: datetime | None = None  # NEW: For testing
) -> PricePoint:
    """Get the most recent available price for a ticker.

    Args:
        ticker: Stock ticker symbol to get price for
        current_time: Current time (defaults to now, used for testing)

    Returns:
        PricePoint with latest available price
    """
    # Use provided time or default to now
    now = current_time or datetime.now(UTC)

    # Tier 1: Check Redis cache
    cached = await self.price_cache.get(ticker)
    if cached and not cached.is_stale(max_age=timedelta(hours=1)):
        return cached.with_source("cache")

    # Tier 2: Check PostgreSQL
    if self.price_repository:
        db_price = await self.price_repository.get_latest_price(
            ticker, max_age=timedelta(hours=4)
        )
        if db_price and not db_price.is_stale(max_age=timedelta(hours=4)):
            await self.price_cache.set(db_price, ttl=3600)
            return db_price.with_source("database")

    # Weekend/Holiday Check
    if not MarketCalendar.is_trading_day(now.date()):  # Use 'now' variable
        last_trading_day = self._get_last_trading_day(now)
        # ... rest of weekend logic
```

Similarly update `get_batch_prices()`:

```python
async def get_batch_prices(
    self,
    tickers: list[Ticker],
    current_time: datetime | None = None  # NEW: For testing
) -> dict[Ticker, PricePoint]:
    """Get current prices for multiple tickers.

    Args:
        tickers: List of stock ticker symbols
        current_time: Current time (defaults to now, used for testing)

    Returns:
        Dictionary mapping tickers to their price points
    """
    now = current_time or datetime.now(UTC)
    is_trading_day = MarketCalendar.is_trading_day(now.date())
    # ... rest of implementation
```

**Note**: The API endpoints don't need to accept this parameter - it's only for internal testing.

#### 2. Update Integration Tests

**File**: `backend/tests/integration/test_prices_api.py`

Add fixtures to simulate weekday behavior:

```python
import pytest
from datetime import datetime, UTC
from unittest.mock import patch

@pytest.fixture
def mock_weekday():
    """Mock current time as a weekday (Friday, Jan 16, 2026)."""
    friday = datetime(2026, 1, 16, 15, 0, 0, tzinfo=UTC)
    with patch('zebu.adapters.outbound.market_data.alpha_vantage_adapter.datetime') as mock_dt:
        mock_dt.now.return_value = friday
        mock_dt.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
        yield mock_dt


@pytest.fixture
def mock_weekend():
    """Mock current time as a weekend (Sunday, Jan 18, 2026)."""
    sunday = datetime(2026, 1, 18, 15, 0, 0, tzinfo=UTC)
    with patch('zebu.adapters.outbound.market_data.alpha_vantage_adapter.datetime') as mock_dt:
        mock_dt.now.return_value = sunday
        mock_dt.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
        yield mock_dt
```

Then update failing tests:

```python
def test_get_current_price(client, db, mock_weekday):  # Add mock_weekday fixture
    """Test getting current price for a ticker (weekday behavior)."""
    # Setup: Insert test data
    # ...existing setup...

    response = client.get("/api/v1/prices/AAPL")
    assert response.status_code == 200
    # ...existing assertions...


def test_get_current_price_weekend(client, db, mock_weekend):  # NEW TEST
    """Test getting current price on weekend returns cached price."""
    # Setup: Insert Friday's price into database
    # ...setup...

    response = client.get("/api/v1/prices/AAPL")
    assert response.status_code == 200
    data = response.json()
    assert data["source"] in ["cache", "database"]
    # Should return Friday's price
```

Apply `mock_weekday` fixture to all existing integration tests that interact with price endpoints:
- `test_get_current_price`
- `test_batch_prices`
- `test_get_price_history`
- Any other tests that fetch prices

### Alternative Approach: Global Datetime Mocking (If Needed)

If the preferred approach doesn't work for some reason:

```python
@pytest.fixture(autouse=True)
def mock_datetime_for_integration_tests(monkeypatch):
    """Auto-mock datetime to Friday for all integration tests."""
    friday = datetime(2026, 1, 16, 15, 0, 0, tzinfo=UTC)

    class MockDateTime:
        @staticmethod
        def now(tz=None):
            return friday if tz == UTC else friday.replace(tzinfo=None)

        def __call__(self, *args, **kwargs):
            return datetime(*args, **kwargs)

    monkeypatch.setattr('zebu.adapters.outbound.market_data.alpha_vantage_adapter.datetime', MockDateTime())
```

But the preferred approach is cleaner and more explicit.

## New Tests Required

Add comprehensive weekend/weekday tests:

```python
def test_price_fetching_weekday_vs_weekend(client, db):
    """Verify different behavior on weekdays vs weekends."""
    # Setup: Insert Friday's cached price
    # ...

    # Test 1: Weekday (Friday) - should attempt API fetch
    with patch('zebu.adapters.outbound.market_data.alpha_vantage_adapter.datetime') as mock_dt:
        mock_dt.now.return_value = datetime(2026, 1, 16, 15, 0, 0, tzinfo=UTC)  # Friday
        response = client.get("/api/v1/prices/AAPL")
        assert response.status_code == 200
        # Should fetch from API (or cached if fresh)

    # Test 2: Weekend (Sunday) - should use cached price, no API call
    with patch('zebu.adapters.outbound.market_data.alpha_vantage_adapter.datetime') as mock_dt:
        mock_dt.now.return_value = datetime(2026, 1, 18, 15, 0, 0, tzinfo=UTC)  # Sunday
        response = client.get("/api/v1/prices/AAPL")
        assert response.status_code == 200
        data = response.json()
        assert data["source"] in ["cache", "database"]
        # Verify it's Friday's price
        timestamp = datetime.fromisoformat(data["timestamp"])
        assert timestamp.date() == date(2026, 1, 16)


def test_batch_prices_weekend(client, db, mock_weekend):
    """Batch prices should work on weekends."""
    # Setup: Insert cached prices for multiple tickers
    # ...

    response = client.get("/api/v1/prices/batch?tickers=AAPL,MSFT")
    assert response.status_code == 200
    data = response.json()
    assert data["requested"] == 2
    assert data["returned"] == 2
    assert "AAPL" in data["prices"]
    assert "MSFT" in data["prices"]
```

## Testing Requirements

### Local Testing

Before marking complete:

```bash
# Run backend quality checks (includes tests)
task quality:backend

# Specifically run integration tests
cd backend && uv run pytest tests/integration/test_prices_api.py -v

# Verify both approaches work:
# 1. On a weekday (mocked as Friday)
# 2. On a weekend (mocked as Sunday)
```

### CI Validation

- All backend tests must pass
- No new ESLint/Pyright errors
- Integration tests should pass regardless of what day CI runs

## Success Criteria

- [ ] All 7 failing integration tests now pass
- [ ] New tests added for both weekday and weekend scenarios
- [ ] `task quality:backend` passes with no errors
- [ ] Tests explicitly verify weekend behavior (not just accidentally passing)
- [ ] Code is refactored for testability (optional datetime parameter preferred)
- [ ] No global datetime mocking that could hide bugs
- [ ] CI passes on PR #153
- [ ] No regression in existing test coverage

## Files to Modify

- `backend/src/zebu/adapters/outbound/market_data/alpha_vantage_adapter.py` - Add optional `current_time` parameter
- `backend/tests/integration/test_prices_api.py` - Add datetime mocking fixtures
- `backend/tests/integration/test_prices_api.py` - Update existing tests to use `mock_weekday`
- `backend/tests/integration/test_prices_api.py` - Add new weekend-specific tests

## Important Notes

- **Target Branch**: `copilot/fix-weekend-price-fetching` (PR #153 branch)
- **Do NOT** merge to main - this is a fix for an existing PR
- Run `task quality:backend` before finishing work
- The weekend detection logic is CORRECT - we're just fixing tests to handle it
- Prefer refactoring for testability over mocking when possible

## References

- PR #153: https://github.com/TimChild/PaperTrade/pull/153
- Weekend detection logic: `alpha_vantage_adapter.py` lines added in PR #153
- MarketCalendar: `backend/src/zebu/infrastructure/market_calendar.py`
- Integration test pattern: `backend/tests/integration/test_prices_api.py`

## Architecture Compliance

- ✅ No changes to public API contracts
- ✅ Optional parameters for testability (dependency injection pattern)
- ✅ Tests validate behavior, not implementation
- ✅ No mocking of domain logic
- ✅ Comprehensive edge case coverage
