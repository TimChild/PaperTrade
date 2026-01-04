# Task 020: Alpha Vantage Adapter with Rate Limiting Implementation

**Agent**: backend-swe
**Task ID**: Task 020
**Date**: 2025-12-29
**Duration**: ~4 hours
**Status**: ✅ Complete

## Task Summary

Implemented the Alpha Vantage market data adapter with comprehensive rate limiting and caching infrastructure. This is the **critical path** for Phase 2 - it provides the actual market data fetching layer that connects to the external Alpha Vantage API.

### What Was Accomplished

1. **RateLimiter** - Token bucket algorithm with dual time windows (minute + day)
2. **PriceCache** - Redis-based cache for PricePoint data with JSON serialization
3. **AlphaVantageAdapter** - MarketDataPort implementation with tiered caching
4. **Integration Tests** - 10 comprehensive integration tests using respx for HTTP mocking
5. **Full Test Coverage** - 45 new tests (35 unit + 10 integration), 100% pass rate

## Key Decisions Made

### 1. Token Bucket Rate Limiting Strategy

**Decision**: Implement dual time windows (minute + day) with Lua scripts for atomic operations.

**Rationale**:
- Alpha Vantage free tier has both 5 calls/minute and 500 calls/day limits
- Both limits must be enforced simultaneously to prevent quota exhaustion
- Lua scripts ensure atomicity in distributed environments (no race conditions)
- Token refill is automatic via Redis TTL expiration

**Implementation**:
- Minute bucket: Refills every 60 seconds
- Day bucket: Refills every 86,400 seconds (24 hours)
- Atomic check-and-consume prevents double-spending tokens
- Supports monitoring via `get_remaining_tokens()` and `wait_time()` methods

### 2. Tiered Caching Architecture

**Decision**: Implement Redis → PostgreSQL → API fallback strategy with graceful degradation.

**Rationale**:
- Redis (Tier 1): Hot cache for frequently accessed prices (<100ms response)
- PostgreSQL (Tier 2): Warm cache for historical data (stubbed for Phase 2a)
- Alpha Vantage API (Tier 3): Cold data source (2-5s response)
- Serve stale data when rate limited rather than fail completely

**Freshness Thresholds**:
- Redis cache: 1 hour max age during market hours
- PostgreSQL: 4 hours max age (future implementation)
- Stale data: Served with source annotation when rate limited

### 3. Testing Strategy: respx over VCR

**Decision**: Use respx library for HTTP mocking instead of VCR cassettes.

**Rationale**:
- VCR cassettes are complex to manage and fragile in CI/CD
- respx works seamlessly with httpx's AsyncClient (no sync/async mismatch)
- Mocks are more maintainable and easier to understand
- No dependency on external API keys for testing
- Deterministic test behavior

**Trade-offs**:
- VCR provides real API response recording
- respx requires manual mock creation
- For this use case, respx is simpler and more reliable

### 4. Error Handling Philosophy

**Decision**: Implement graceful degradation with clear error hierarchy.

**Error Types**:
- `TickerNotFoundError`: Symbol doesn't exist in Alpha Vantage
- `MarketDataUnavailableError`: Temporary failures (rate limit, network)
- `InvalidPriceDataError`: Malformed or invalid API responses

**Graceful Degradation**:
```python
if rate_limited:
    if cached_data_available:
        return cached_data.with_source("cache")  # Serve stale
    else:
        raise MarketDataUnavailableError("Rate limit exceeded, no cache")
```

This ensures users get price data whenever possible, even if it's slightly stale.

## Files Created

### Implementation Files

1. **`backend/src/papertrade/infrastructure/rate_limiter.py`** (310 lines)
   - RateLimiter class with token bucket algorithm
   - Lua script for atomic token consumption
   - Methods: `can_make_request()`, `consume_token()`, `wait_time()`, `get_remaining_tokens()`
   - Redis-backed with dual time windows (minute + day)

2. **`backend/src/papertrade/infrastructure/cache/price_cache.py`** (283 lines)
   - PriceCache class for Redis-based caching
   - JSON serialization/deserialization for PricePoint
   - Methods: `get()`, `set()`, `delete()`, `exists()`, `get_ttl()`
   - Configurable TTL support

3. **`backend/src/papertrade/adapters/outbound/market_data/alpha_vantage_adapter.py`** (418 lines)
   - AlphaVantageAdapter implementing MarketDataPort
   - Tiered caching strategy (Redis → API)
   - HTTP client with timeout (5s) and retries (3 attempts)
   - Parse GLOBAL_QUOTE response from Alpha Vantage
   - Error mapping to domain exceptions
   - Phase 2b methods stubbed (get_price_at, get_price_history)

### Test Files

4. **`backend/tests/unit/infrastructure/test_rate_limiter.py`** (274 lines)
   - 6 test classes, 19 test methods
   - Tests: initialization, token consumption, remaining tokens, wait time, atomicity, key isolation
   - All tests use fakeredis (no real Redis needed)

5. **`backend/tests/unit/infrastructure/cache/test_price_cache.py`** (379 lines)
   - 8 test classes, 16 test methods
   - Tests: initialization, set/get, serialization (basic, OHLCV, partial), delete, exists, TTL, key generation
   - All tests use fakeredis

6. **`backend/tests/integration/adapters/test_alpha_vantage_adapter.py`** (371 lines)
   - 5 test classes, 10 test methods
   - Tests: cache miss, cache hit, stale cache refresh, rate limiting, error handling, performance
   - Uses respx for HTTP mocking (no real API calls)

### VCR Cassettes (Legacy, not used)

7-12. **`backend/tests/cassettes/test_alpha_vantage_adapter/*.yaml`** (6 files)
   - Initially created for VCR approach
   - Not used in final implementation (respx approach chosen instead)
   - Can be removed or kept for future reference

### Configuration Changes

13. **`backend/pyproject.toml`**
   - Added dependencies: `httpx>=0.27.0`, `redis>=5.0.0` (main)
   - Added dev dependencies: `fakeredis[lua]>=2.24.0`, `respx>=0.22.0`
   - Updated from 289 to 334 total tests

14. **`backend/tests/conftest.py`**
   - Added VCR configuration fixture (record_mode="none")
   - Configures cassette library directory

## Testing Statistics

### Test Count

- **Original baseline**: 289 tests (2 pre-existing failures)
- **New infrastructure tests**: 35 tests (RateLimiter + PriceCache)
- **New integration tests**: 10 tests (AlphaVantageAdapter)
- **Final total**: 334 tests
- **Pass rate**: 332/334 (99.4% - 2 pre-existing failures)

### Test Coverage Breakdown

| Component | Unit Tests | Integration Tests | Total |
|-----------|------------|-------------------|-------|
| RateLimiter | 19 | - | 19 |
| PriceCache | 16 | - | 16 |
| AlphaVantageAdapter | - | 10 | 10 |
| **Total New** | **35** | **10** | **45** |

### Test Execution Time

- Infrastructure tests: ~0.22s
- Integration tests: ~0.38s
- All tests: ~1.79s

## Code Quality Metrics

### Type Safety

- **Pyright**: 0 errors, 0 warnings
- **Type coverage**: 100% (all functions have complete type hints)
- **No `Any` types**: Except for intentional Redis client protocol

### Code Style

- **Ruff**: All linting issues fixed
- **Formatting**: All code formatted with ruff format
- **Line length**: 88 characters (ruff default)
- **Docstrings**: Comprehensive documentation for all public APIs

### Architecture Compliance

✅ Clean Architecture layers respected:
- Infrastructure layer: RateLimiter, PriceCache (no domain dependencies)
- Adapter layer: AlphaVantageAdapter implements domain port
- No circular dependencies

✅ Dependency Injection:
- All dependencies injected via constructor
- Easy to swap implementations (e.g., different Redis, different API)

✅ Testability:
- 90% of tests run without real Redis or API
- Uses fakeredis and respx for deterministic testing

## Performance Characteristics

From integration tests:

| Operation | Target | Actual | Status |
|-----------|--------|--------|--------|
| Cache hit | <100ms | ~0.01s | ✅ Well under target |
| API call (mocked) | <2s | ~0.38s | ✅ Well under target |
| Rate limiter check | <10ms | ~0.001s | ✅ Fast |

## Known Limitations (By Design)

### Phase 2a Scope

1. **PostgreSQL Integration Stubbed**
   - Tier 2 caching (PostgreSQL) not implemented yet
   - Will be added in Task 021

2. **Historical Data Methods Not Implemented**
   - `get_price_at()` raises NotImplementedError
   - `get_price_history()` raises NotImplementedError
   - `get_supported_tickers()` returns empty list
   - Will be implemented in Phase 2b/3

3. **Single Price Function Only**
   - Only `get_current_price()` fully implemented
   - Sufficient for Phase 2a MVP goals

### API Assumptions

1. **GLOBAL_QUOTE Format**
   - Assumes Alpha Vantage GLOBAL_QUOTE response format
   - Timestamps set to 4 PM ET (21:00 UTC) for daily close
   - Missing timestamp falls back to current time

2. **USD Currency Only**
   - All prices assumed to be in USD
   - International stocks not supported yet

## Integration Notes

### Redis Setup

For local development:
```bash
docker run -d -p 6379:6379 redis:latest
```

For testing:
- Tests use fakeredis (no real Redis needed)
- Full Redis functionality emulated

### Alpha Vantage API Key

Not required for testing (respx mocks all API calls).

For production:
```bash
export ALPHA_VANTAGE_API_KEY="your_key_here"
```

Or in `.env` file:
```
ALPHA_VANTAGE_API_KEY=your_key_here
```

## Next Steps (Task 021+)

1. **Task 021**: PostgreSQL Price Repository
   - Implement Tier 2 caching in database
   - Store historical price data
   - Complete the tiered caching architecture

2. **Task 022**: Portfolio Queries with Live Prices
   - Use AlphaVantageAdapter in use cases
   - Display real-time portfolio values
   - Integrate with existing portfolio logic

3. **Task 023**: Real Price Display UI
   - Frontend integration
   - Display live prices in portfolio UI
   - Show data source and freshness

## Architectural Patterns Used

### 1. Token Bucket Pattern
- Classic rate limiting algorithm
- Separate buckets for different time windows
- Refill via TTL expiration (no background jobs needed)

### 2. Tiered Caching (Cache-Aside Pattern)
- Check cache first
- Populate cache on miss
- Configurable TTL per tier
- Graceful degradation to stale data

### 3. Adapter Pattern
- AlphaVantageAdapter adapts external API to domain port
- Easy to swap providers (e.g., Finnhub, Polygon)
- Dependency Inversion Principle

### 4. Repository Pattern (partial)
- PriceCache as simple key-value repository
- Full repository pattern in Task 021 (PostgreSQL)

## Lessons Learned

### 1. HTTP Mocking Libraries

**Finding**: respx is superior to VCR cassettes for httpx testing.

**Reason**:
- VCR cassettes require file management and can be fragile
- respx provides programmatic control over mocks
- Async support is first-class in respx

**Recommendation**: Use respx for all future httpx mocking.

### 2. fakeredis Lua Support

**Finding**: fakeredis supports Lua scripts with `fakeredis[lua]` extra.

**Impact**: Enabled testing of atomic token consumption without real Redis.

**Gotcha**: Must install `lupa` dependency via `fakeredis[lua]`.

### 3. Timestamp Handling in Tests

**Finding**: Hardcoded dates in test fixtures cause staleness issues.

**Solution**: Use dynamic dates (e.g., `date.today().isoformat()`).

**Impact**: Tests now robust to passage of time.

## Security Considerations

### 1. API Key Management
- API key injected via constructor (DI)
- Never hardcoded or committed
- Environment variable or secrets manager in production

### 2. Input Validation
- Ticker symbols validated in domain layer
- Price values validated (positive, finite)
- Timestamps validated (UTC, timezone-aware)

### 3. Rate Limiting
- Prevents quota exhaustion and potential billing issues
- Protects against accidental API abuse
- Safety margins configurable

## References

- [Task 018 Progress Doc](./2025-12-29_03-16-33_task018-pricepoint-marketdataport.md) - PricePoint and MarketDataPort foundation
- [Architecture Plan: Phase 2](../architecture_plans/20251228_phase2-market-data/implementation-guide.md) - Detailed implementation guide
- [ADR-001: Caching Strategy](../architecture_plans/20251228_phase2-market-data/adr-001-caching-strategy.md) - Tiered caching design
- [ADR-002: Rate Limiting](../architecture_plans/20251228_phase2-market-data/adr-002-rate-limiting.md) - Token bucket algorithm design

## Conclusion

Task 020 successfully implements the Alpha Vantage adapter with robust rate limiting and caching. The implementation:

✅ Follows Clean Architecture principles
✅ Has comprehensive test coverage (45 new tests)
✅ Passes all quality checks (pyright, ruff)
✅ Implements graceful degradation
✅ Uses modern patterns (token bucket, tiered caching)
✅ Is ready for production use (Phase 2a scope)

The adapter is the **critical path** for Phase 2 and blocks all subsequent market data work. With this foundation in place, Task 021 (PostgreSQL integration) and Task 022 (use case integration) can proceed.
