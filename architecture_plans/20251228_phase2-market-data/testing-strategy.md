# Phase 2 Market Data Integration - Testing Strategy

**Created**: 2025-12-28  
**Status**: Approved

## Overview

This document outlines the comprehensive testing strategy for Phase 2 Market Data Integration. Testing follows the same principles as Phase 1: test behavior, not implementation; sociable tests over solitary; isolation at architectural boundaries.

## Testing Pyramid

```
           E2E Tests (5%)
         /              \
    Integration Tests (25%)
   /                      \
  Unit Tests (70%)
```

**Distribution**:
- **70% Unit Tests**: Fast, isolated, test business logic
- **25% Integration Tests**: Test component interactions (DB, Redis, API)
- **5% E2E Tests**: Test full user journeys (manual + automated)

## Test Categories

### 1. Unit Tests (Fast, Isolated)

#### Domain Layer Tests

**PricePoint Value Object** (if domain):
```
✅ Valid price point creation
✅ Invalid price (negative) raises error
✅ Invalid timestamp (naive datetime) raises error
✅ Invalid source (unknown) raises error
✅ is_stale() returns True/False correctly
✅ with_source() creates new instance
✅ Equality semantics (ticker + price + timestamp + source)
✅ String representation includes all key info
✅ OHLCV data validation (low ≤ high, etc.)
```

**Test Count**: ~15 tests  
**Execution Time**: <10ms

#### Application Layer Tests

**MarketDataPort Protocol Compliance**:
```
✅ InMemoryMarketDataPort implements all methods
✅ get_current_price() returns latest price
✅ get_current_price() raises TickerNotFoundError for unknown ticker
✅ get_price_at() returns closest price to timestamp
✅ get_price_at() raises error for future timestamp
✅ get_price_history() returns ordered list
✅ get_price_history() handles empty range
✅ get_supported_tickers() returns all tickers
```

**Test Count**: ~12 tests  
**Execution Time**: <50ms

**Updated Use Cases**:
```
✅ GetPortfolioBalance with real prices
✅ GetPortfolioBalance handles market data error gracefully
✅ GetPortfolioBalance calculates total correctly
✅ GetHoldings includes current price
✅ GetHoldings calculates unrealized gain/loss
✅ GetHoldings handles missing ticker (price = $0)
```

**Test Count**: ~10 tests  
**Execution Time**: <100ms

#### Infrastructure Layer Tests

**RateLimiter** (Unit Tests with fakeredis):
```
✅ can_make_request() returns True with available tokens
✅ can_make_request() returns False when tokens exhausted
✅ consume_token() decrements both minute and day counters
✅ Token refill at minute boundary
✅ Token refill at day boundary
✅ wait_time() returns correct duration
✅ Dual-window enforcement (both buckets must have tokens)
✅ Thread safety (concurrent requests don't over-consume)
```

**Test Count**: ~15 tests  
**Execution Time**: <100ms  
**Tools**: fakeredis (in-memory Redis mock)

**PriceCache** (Unit Tests with fakeredis):
```
✅ get() returns cached price if exists
✅ get() returns None if not exists
✅ set() stores price with TTL
✅ get_ttl() returns remaining time
✅ exists() checks presence
✅ delete() removes from cache
✅ JSON serialization/deserialization
✅ TTL expiration (price removed after timeout)
```

**Test Count**: ~10 tests  
**Execution Time**: <100ms  
**Tools**: fakeredis

### 2. Integration Tests (Moderate Speed, Real Dependencies)

#### AlphaVantageAdapter (With VCR Cassettes)

**VCR Strategy**: Record API responses once, replay in tests (no API key needed).

**Test Setup**:
```python
import pytest
from pytest_recording import record

@pytest.mark.vcr()
async def test_get_current_price_success():
    # Uses cassette: cassettes/test_get_current_price_success.yaml
    adapter = AlphaVantageAdapter(...)
    price = await adapter.get_current_price(Ticker("AAPL"))
    assert price.ticker.symbol == "AAPL"
    assert price.price.amount > 0
```

**Test Cases**:
```
✅ get_current_price() - Success (AAPL)
✅ get_current_price() - Ticker not found (INVALID)
✅ get_current_price() - Rate limited (429 response)
✅ get_current_price() - Network timeout
✅ get_current_price() - Cache hit (no API call)
✅ get_current_price() - Cache miss, DB hit
✅ get_current_price() - Cache miss, DB miss, API success
✅ get_price_history() - 1 year daily data
✅ get_price_at() - Historical query
✅ API response parsing (GLOBAL_QUOTE format)
✅ API response parsing (TIME_SERIES_DAILY format)
✅ Error mapping (API errors → PaperTrade exceptions)
```

**Test Count**: ~15 tests  
**Execution Time**: <500ms (replaying cassettes)  
**Tools**: pytest-recording

**Recording Cassettes** (one-time setup):
```bash
# Set real API key
export ALPHA_VANTAGE_API_KEY=your_actual_key

# Record cassettes (makes real API calls)
pytest --record-mode=once tests/integration/adapters/test_alpha_vantage_adapter.py

# Commit cassettes to repo
git add tests/cassettes/*.yaml
```

**Cassette Files**:
- `cassettes/test_get_current_price_aapl.yaml`
- `cassettes/test_get_current_price_ticker_not_found.yaml`
- `cassettes/test_get_current_price_rate_limited.yaml`
- `cassettes/test_get_price_history_daily.yaml`

#### PriceRepository (With Test Database)

**Test Setup**:
```python
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

@pytest.fixture
async def test_db():
    # SQLite in-memory for speed
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    # Run migrations
    await run_migrations(engine)
    yield engine
    await engine.dispose()
```

**Test Cases**:
```
✅ save() inserts new price
✅ save() updates existing price (upsert)
✅ get_latest() returns most recent price
✅ get_at() returns closest price to timestamp
✅ get_history() returns ordered list
✅ get_history() filters by interval
✅ get_history() handles date range
✅ get_all_tickers() returns distinct list
✅ count() returns total prices for ticker
✅ Unique constraint enforced (ticker + timestamp + interval)
✅ Check constraints enforced (positive prices)
✅ Index usage (EXPLAIN query plan)
```

**Test Count**: ~15 tests  
**Execution Time**: <1s (SQLite fast)  
**Tools**: SQLite (in-memory), Alembic (migrations)

#### WatchlistManager (With Test Database)

**Test Cases**:
```
✅ add_ticker() adds to watchlist
✅ add_ticker() upgrades priority if exists
✅ get_stale_tickers() returns tickers needing refresh
✅ get_stale_tickers() respects priority order
✅ update_refresh_success() updates metadata
✅ update_refresh_error() increments error count
✅ Common stocks pre-populated after migration
```

**Test Count**: ~8 tests  
**Execution Time**: <500ms

### 3. End-to-End Tests (Slow, Full Stack)

#### Manual Testing Scenarios

**Scenario 1: View Portfolio with Real Prices**
```
1. Start backend + frontend
2. Navigate to portfolio
3. Verify: Holdings show current prices
4. Verify: Total value calculated correctly
5. Verify: Price timestamp displayed
6. Verify: Source indicator (cached vs live)
```

**Scenario 2: Refresh Prices**
```
1. View portfolio
2. Click "Refresh Prices" button
3. Verify: Loading indicator shown
4. Verify: Prices updated
5. Verify: Timestamp updated
6. Verify: Source shows "live"
```

**Scenario 3: View Price Chart**
```
1. Click on holding (AAPL)
2. Navigate to detail page
3. Verify: Price chart displayed
4. Verify: Can switch timeframes (1D, 1W, 1M, 1Y)
5. Verify: Chart shows correct data points
```

**Scenario 4: Background Job**
```
1. Trigger refresh job manually
2. Check logs for progress
3. Verify: Prices updated in database
4. Verify: Cache warmed
5. Verify: Error handling (if any failures)
```

#### Automated E2E Tests (Optional, Phase 3+)

**Tools**: Playwright or Cypress

**Test Cases** (Future):
```
✅ User creates portfolio → sees real prices
✅ User refreshes prices → values update
✅ User views price chart → chart renders
✅ Background job runs → prices refreshed
```

## Mock Strategies

### Where to Mock

| Layer | Mock? | Why |
|-------|-------|-----|
| **Domain Logic** | ❌ Never | Pure functions, no I/O |
| **Application Use Cases** | ❌ Rarely | Sociable tests with real domain |
| **MarketDataPort** | ✅ Yes | Mock in use case tests (boundary) |
| **HTTP Client** | ✅ Yes | Use VCR cassettes |
| **Redis** | ✅ Yes | Use fakeredis |
| **PostgreSQL** | ⚠️ Sometimes | Use SQLite for speed, PostgreSQL for correctness |

### Mock Implementation

**InMemoryMarketDataPort** (for testing use cases):
```python
class InMemoryMarketDataPort:
    def __init__(self):
        self.prices: Dict[Ticker, List[PricePoint]] = {}

    def seed(self, ticker: Ticker, prices: List[PricePoint]):
        """Seed test data."""
        self.prices[ticker] = prices

    async def get_current_price(self, ticker: Ticker) -> PricePoint:
        if ticker not in self.prices:
            raise TickerNotFoundError(ticker)
        return self.prices[ticker][-1]  # Latest price
```

**NoOpCache** (fallback when Redis unavailable):
```python
class NoOpCache:
    """Cache that does nothing (testing/fallback)."""

    async def get(self, ticker: Ticker) -> None:
        return None  # Always cache miss

    async def set(self, ticker: Ticker, price: PricePoint, ttl: timedelta) -> None:
        pass  # Do nothing
```

## Test Data Management

### Fixtures

**Backend Fixtures** (`backend/tests/fixtures/`):
- `price_points.json` - Sample price data (5 tickers, 1 year)
- `alpha_vantage_responses/` - Sample API responses
- `market_data_scenarios.py` - Test scenario builders

**Example Fixture**:
```json
{
  "ticker": "AAPL",
  "price": {"amount": "150.25", "currency": "USD"},
  "timestamp": "2024-12-28T14:30:00Z",
  "source": "alpha_vantage",
  "interval": "real-time",
  "open": {"amount": "148.50", "currency": "USD"},
  "high": {"amount": "151.00", "currency": "USD"},
  "low": {"amount": "147.75", "currency": "USD"},
  "close": {"amount": "150.25", "currency": "USD"},
  "volume": 52847392
}
```

### VCR Cassettes

**Directory**: `backend/tests/cassettes/`

**Cassette Format** (YAML):
```yaml
version: 1
interactions:
  - request:
      uri: https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=AAPL&apikey=***
      method: GET
      body: null
      headers: {}
    response:
      status:
        code: 200
        message: OK
      headers:
        Content-Type: application/json
      body:
        string: '{"Global Quote": {"01. symbol": "AAPL", "05. price": "150.25"}}'
```

**Benefits**:
- No API key needed for tests
- Fast (no network calls)
- Deterministic (same response every time)
- Detect API changes (cassette invalidates)

## Performance Testing

### Targets

| Operation | Target | Test Method |
|-----------|--------|-------------|
| Cache hit (Redis) | <100ms | Time with pytest-benchmark |
| Database query (latest price) | <50ms | Time with pytest-benchmark |
| API call (with retry) | <2s | Record with VCR, replay |
| Historical query (1 year) | <500ms | SQLite test with 252 records |

### Benchmark Tests

**Example**:
```python
import pytest

def test_price_cache_performance(benchmark, price_cache):
    """Cache get should be <100ms."""
    ticker = Ticker("AAPL")
    price = create_price_point(ticker)
    
    # Warmup
    await price_cache.set(ticker, price, ttl=timedelta(hours=1))
    
    # Benchmark
    result = benchmark(lambda: price_cache.get(ticker))
    
    assert result == price
    # Assertion: benchmark reports <100ms
```

### Load Testing (Manual, Phase 3+)

**Tools**: Locust or k6

**Scenario**:
- 100 concurrent users
- Each views portfolio (5 stocks)
- Expected: <500ms response time
- Expected: >85% cache hit rate

## Security Testing

### Code Security Scanning

**Tool**: CodeQL (GitHub built-in)

**Checks**:
- ✅ No hardcoded secrets (API keys, passwords)
- ✅ No SQL injection (parametrized queries only)
- ✅ No command injection
- ✅ No path traversal
- ✅ Proper error handling (no sensitive data in errors)

### Secret Scanning

**Tool**: git-secrets or GitHub secret scanning

**Checks**:
- ✅ .env not committed
- ✅ API keys not in code
- ✅ API keys not in logs
- ✅ Cassettes have API keys redacted (`apikey=***`)

### Dependency Scanning

**Tools**: pip-audit (backend), npm audit (frontend)

**Checks**:
- ✅ No known vulnerabilities in dependencies
- ✅ Dependencies up to date

## Continuous Integration

### GitHub Actions Workflow

**On Pull Request**:
1. Lint (ruff, ESLint)
2. Type check (Pyright, TypeScript)
3. Unit tests (pytest, Vitest)
4. Integration tests (with test DB, fakeredis)
5. Security scan (CodeQL)
6. Coverage report (>80% target)

**On Merge to Main**:
1. All PR checks
2. E2E tests (optional, manual)
3. Deploy to staging (optional)

### Test Execution Times

| Test Suite | Tests | Target Time | Actual (Phase 1) |
|------------|-------|-------------|------------------|
| Backend Unit | ~100 | <5s | 0.5s |
| Backend Integration | ~40 | <30s | TBD |
| Frontend Unit | ~30 | <10s | <1s |
| Frontend E2E | ~5 | <60s | Manual |
| **Total** | **~175** | **<2min** | TBD |

## Test Documentation

### Docstrings

**Required for all tests**:
```python
async def test_get_current_price_with_cache_hit():
    """
    Test that get_current_price returns cached data without API call.
    
    Scenario:
    1. Price is cached in Redis
    2. Call get_current_price()
    3. Expect: Cached price returned
    4. Expect: No API call made (verified by VCR)
    """
    # ... test implementation
```

### README Testing Section

**Add to README.md**:
```markdown
## Testing

### Run All Tests
```bash
task test
```

### Run Backend Tests Only
```bash
task test:backend
```

### Run Frontend Tests Only
```bash
task test:frontend
```

### Run with Coverage
```bash
task test:coverage
```

### Update VCR Cassettes
```bash
export ALPHA_VANTAGE_API_KEY=your_key
pytest --record-mode=rewrite tests/integration/adapters/
```
```

## Test Coverage Targets

| Component | Target | Rationale |
|-----------|--------|-----------|
| **Domain Layer** | 100% | Pure logic, easy to test |
| **Application Layer** | 95% | Core business rules |
| **Adapters Layer** | 80% | Some code hard to test (network errors) |
| **Infrastructure Layer** | 75% | External dependencies |
| **Overall** | 85% | Industry best practice |

**Measurement**: pytest-cov (backend), Vitest coverage (frontend)

## Debugging Failed Tests

### Common Issues

**Issue 1: VCR Cassette Not Found**
```bash
# Solution: Record cassette
pytest --record-mode=once tests/integration/adapters/test_alpha_vantage_adapter.py::test_name
```

**Issue 2: Redis Connection Error**
```bash
# Solution: Use fakeredis
pip install fakeredis
# Tests automatically use fakeredis if Redis unavailable
```

**Issue 3: Database Migration Failed**
```bash
# Solution: Drop and recreate test DB
alembic downgrade base
alembic upgrade head
```

**Issue 4: Timestamp Mismatch (Timezone)**
```python
# Solution: Always use UTC
from datetime import datetime, timezone
now = datetime.now(timezone.utc)  # Correct
now = datetime.now()  # Wrong (naive datetime)
```

## Review Checklist

Before merging PR:
- [ ] All tests passing in CI
- [ ] Coverage meets targets (85%+)
- [ ] No flaky tests (run 3x to verify)
- [ ] VCR cassettes committed (if new)
- [ ] Test docstrings explain what/why
- [ ] Performance targets met
- [ ] Security scan clean

## References

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-recording (VCR)](https://github.com/kiwicom/pytest-recording)
- [fakeredis Documentation](https://github.com/cunla/fakeredis-py)
- [pytest-benchmark](https://pytest-benchmark.readthedocs.io/)
- [Vitest Documentation](https://vitest.dev/)
- [Phase 1 Testing Strategy](../20251227_phase1-backend-mvp/domain-layer.md#testing-approach)
