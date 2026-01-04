# Task 020: Alpha Vantage Adapter with Rate Limiting

**Created**: 2025-12-28
**Agent**: backend-swe
**Estimated Effort**: 6-8 hours
**Dependencies**: Task 018 (PricePoint + MarketDataPort foundation)
**Related PRs**: N/A (new work)

## Objective

Implement the Alpha Vantage adapter with comprehensive rate limiting and caching infrastructure. This is the **critical path** for Phase 2 - it implements the actual market data fetching layer that connects to the external API.

## Context

This task implements the infrastructure described in the Phase 2 architecture:
- **Rate Limiting**: Token bucket algorithm to respect Alpha Vantage quotas (5 calls/min, 500/day)
- **Caching**: Redis-based hot cache for frequently accessed prices
- **Adapter**: MarketDataPort implementation that orchestrates Redis → PostgreSQL → API fallback
- **Testing**: VCR cassettes to test without real API calls

### Architecture References
- [implementation-guide.md](../architecture_plans/20251228_phase2-market-data/implementation-guide.md#task-017-alpha-vantage-adapter-with-rate-limiting-6-8-hours)
- [adr-001-caching-strategy.md](../architecture_plans/20251228_phase2-market-data/adr-001-caching-strategy.md)
- [adr-002-rate-limiting.md](../architecture_plans/20251228_phase2-market-data/adr-002-rate-limiting.md)

## Success Criteria

- [ ] RateLimiter prevents quota exhaustion (tested with fakeredis)
- [ ] PriceCache works with Redis (CRUD operations, TTL handling)
- [ ] AlphaVantageAdapter implements MarketDataPort protocol
- [ ] VCR cassettes recorded for all scenarios (no real API calls in CI)
- [ ] All tests pass without real API key
- [ ] Integration tests demonstrate tiered caching strategy
- [ ] Error handling for API failures, rate limits, network issues

## Implementation Details

### 1. RateLimiter (Token Bucket Algorithm)

**File**: `backend/src/papertrade/infrastructure/rate_limiter.py`

**Key Features**:
- Dual time windows (minute + day) to enforce both Alpha Vantage limits
- Redis-backed token storage for distributed systems
- Lua script for atomic check-and-consume operation
- Methods:
  - `async def can_make_request() -> bool` - Check if tokens available
  - `async def consume_token() -> bool` - Atomically check and consume
  - `async def wait_time() -> float` - Seconds until next token available
  - `async def get_remaining_tokens() -> dict[str, int]` - For monitoring

**Configuration**:
```python
# From settings.toml
[market_data.rate_limits]
calls_per_minute = 5
calls_per_day = 500
```

**Testing Notes**:
- Use `fakeredis` for unit tests (no real Redis needed)
- Test token refill at window boundaries
- Test concurrent requests (ensure atomic operations)
- Test daily quota exhaustion

### 2. PriceCache (Redis Wrapper)

**File**: `backend/src/papertrade/infrastructure/cache/price_cache.py`

**Key Features**:
- Simple wrapper around Redis for PricePoint storage
- JSON serialization (use PricePoint.model_dump() / model_validate())
- Configurable TTL (1 hour during market hours, 4 hours after close)
- Methods:
  - `async def get(ticker: Ticker) -> PricePoint | None`
  - `async def set(price: PricePoint, ttl: int | None = None) -> None`
  - `async def delete(ticker: Ticker) -> None`
  - `async def exists(ticker: Ticker) -> bool`
  - `async def get_ttl(ticker: Ticker) -> int` - Remaining seconds

**Key Format**: `papertrade:price:{ticker.symbol}`

**Testing Notes**:
- Use `fakeredis` for unit tests
- Test TTL expiration behavior
- Test serialization round-trip
- Test error handling (Redis connection lost)

### 3. AlphaVantageAdapter

**File**: `backend/src/papertrade/adapters/outbound/market_data/alpha_vantage_adapter.py`

**Key Features**:
- Implements `MarketDataPort` protocol from Task 018
- Tiered fallback strategy: Redis → PostgreSQL → Alpha Vantage API
- HTTP client with timeout (5s) and retries (3 attempts with exponential backoff)
- Parse Alpha Vantage GLOBAL_QUOTE response format
- Error mapping:
  - Invalid ticker → `TickerNotFoundError`
  - Rate limited → `MarketDataUnavailableError("Rate limit exceeded")`
  - Network errors → `MarketDataUnavailableError("API unreachable")`
  - Malformed data → `InvalidPriceDataError`

**Dependencies** (inject via constructor):
- `rate_limiter: RateLimiter`
- `price_cache: PriceCache`
- `price_repository: PriceRepository` (will create in next task, use None for now)
- `http_client: httpx.AsyncClient`
- `api_key: str`

**Tiered Caching Logic**:
```python
async def get_current_price(self, ticker: Ticker) -> PricePoint:
    # Tier 1: Check Redis cache
    cached = await self.price_cache.get(ticker)
    if cached and not cached.is_stale(max_age=timedelta(hours=1)):
        return cached

    # Tier 2: Check PostgreSQL (skip for now, implement in Task 021)
    # if self.price_repository:
    #     db_price = await self.price_repository.get_latest_price(ticker)
    #     if db_price and not db_price.is_stale(max_age=timedelta(hours=4)):
    #         await self.price_cache.set(db_price)  # Warm cache
    #         return db_price

    # Tier 3: Fetch from Alpha Vantage API
    if not await self.rate_limiter.can_make_request():
        # Serve stale data if available, else raise error
        if cached:
            return cached.with_source("alpha_vantage_stale")
        raise MarketDataUnavailableError("Rate limit exceeded, no cached data")

    # Make API request
    await self.rate_limiter.consume_token()
    price = await self._fetch_from_api(ticker)

    # Store in cache and database
    await self.price_cache.set(price)
    # if self.price_repository:
    #     await self.price_repository.upsert_price(price)

    return price
```

**Alpha Vantage API Details**:
- Endpoint: `https://www.alphavantage.co/query`
- Function: `GLOBAL_QUOTE`
- Example: `?function=GLOBAL_QUOTE&symbol=AAPL&apikey={key}`
- Response format:
  ```json
  {
    "Global Quote": {
      "01. symbol": "AAPL",
      "05. price": "192.53",
      "07. latest trading day": "2025-12-27",
      ...
    }
  }
  ```

**Testing Notes**:
- **DO NOT use real API key in tests** - use VCR cassettes
- Test all cache tiers (hit, miss, stale)
- Test rate limiter integration
- Test error scenarios (API down, invalid ticker, rate limited)

### 4. VCR Cassettes (pytest-recording)

**Setup**:
1. Add `pytest-recording` to dependencies
2. Configure in `conftest.py`:
   ```python
   @pytest.fixture(scope="module")
   def vcr_config():
       return {
           "filter_headers": ["authorization", "x-api-key"],
           "record_mode": "once",  # Record once, replay after
           "match_on": ["uri", "method"],
       }
   ```
3. Use `@pytest.mark.vcr()` decorator on integration tests

**Cassettes to Record** (in `backend/tests/cassettes/`):
- `alpha_vantage_current_price_aapl.yaml` - Successful price fetch
- `alpha_vantage_current_price_tsla.yaml` - Another ticker
- `alpha_vantage_ticker_not_found.yaml` - Invalid ticker response
- `alpha_vantage_api_error.yaml` - API error response

**Recording Process**:
1. Run tests ONCE with real API key in environment: `ALPHA_VANTAGE_API_KEY=xxx pytest`
2. Cassettes recorded in `backend/tests/cassettes/`
3. Commit cassettes to git
4. CI runs tests without API key (uses cassettes)

### 5. Testing Strategy

**Unit Tests** (`backend/tests/unit/infrastructure/`):

`test_rate_limiter.py`:
- Token consumption in minute window
- Token consumption in day window
- Token refill behavior
- Concurrent request handling (atomic operations)
- Wait time calculation
- Remaining tokens query

`test_price_cache.py`:
- Get/set/delete operations
- TTL behavior
- Serialization round-trip (PricePoint → JSON → PricePoint)
- Cache miss returns None
- Exists check
- Error handling (Redis connection lost)

**Integration Tests** (`backend/tests/integration/adapters/`):

`test_alpha_vantage_adapter.py`:
```python
@pytest.mark.vcr()
async def test_get_current_price_cache_miss():
    """Test full flow: cache miss → API call → cache population"""
    adapter = AlphaVantageAdapter(...)
    price = await adapter.get_current_price(Ticker.create("AAPL"))

    assert price.ticker.symbol == "AAPL"
    assert price.price.amount > 0
    assert price.source == "alpha_vantage"

    # Verify cache was populated
    cached = await adapter.price_cache.get(Ticker.create("AAPL"))
    assert cached == price

@pytest.mark.vcr()
async def test_get_current_price_cache_hit():
    """Test cache hit (no API call)"""
    adapter = AlphaVantageAdapter(...)

    # First call populates cache (uses VCR)
    price1 = await adapter.get_current_price(Ticker.create("AAPL"))

    # Second call hits cache (no VCR interaction)
    price2 = await adapter.get_current_price(Ticker.create("AAPL"))

    assert price2 == price1

@pytest.mark.vcr()
async def test_rate_limit_exceeded():
    """Test behavior when rate limited"""
    adapter = AlphaVantageAdapter(...)

    # Exhaust rate limit (make 5+ requests in rapid succession)
    for _ in range(6):
        try:
            await adapter.get_current_price(Ticker.create("AAPL"))
        except MarketDataUnavailableError as e:
            assert "Rate limit exceeded" in str(e)
            break

@pytest.mark.vcr()
async def test_ticker_not_found():
    """Test invalid ticker handling"""
    adapter = AlphaVantageAdapter(...)

    with pytest.raises(TickerNotFoundError):
        await adapter.get_current_price(Ticker.create("INVALID"))
```

## Files to Create/Modify

### New Files

**Infrastructure**:
- `backend/src/papertrade/infrastructure/__init__.py`
- `backend/src/papertrade/infrastructure/rate_limiter.py` (~150 lines)
- `backend/src/papertrade/infrastructure/cache/__init__.py`
- `backend/src/papertrade/infrastructure/cache/price_cache.py` (~100 lines)

**Adapters**:
- `backend/src/papertrade/adapters/outbound/market_data/alpha_vantage_adapter.py` (~250 lines)

**Tests**:
- `backend/tests/unit/infrastructure/test_rate_limiter.py` (~200 lines)
- `backend/tests/unit/infrastructure/cache/test_price_cache.py` (~150 lines)
- `backend/tests/integration/adapters/test_alpha_vantage_adapter.py` (~300 lines)

**VCR Cassettes**:
- `backend/tests/cassettes/alpha_vantage_current_price_aapl.yaml`
- `backend/tests/cassettes/alpha_vantage_current_price_tsla.yaml`
- `backend/tests/cassettes/alpha_vantage_ticker_not_found.yaml`
- `backend/tests/cassettes/alpha_vantage_api_error.yaml`

### Modified Files

**Configuration**:
- `backend/settings.toml` - Add market_data.rate_limits section
- `backend/pyproject.toml` - Add pytest-recording, httpx, redis dependencies
- `backend/tests/conftest.py` - Add VCR configuration fixture

**Documentation**:
- `backend/README.md` - Document Alpha Vantage setup (API key, VCR usage)

## Configuration Updates

### `backend/settings.toml`

Add section:
```toml
[market_data]
provider = "alpha_vantage"

[market_data.alpha_vantage]
base_url = "https://www.alphavantage.co/query"
timeout = 5.0
max_retries = 3

[market_data.rate_limits]
calls_per_minute = 5
calls_per_day = 500

[market_data.cache]
ttl_market_hours = 3600  # 1 hour
ttl_after_close = 14400  # 4 hours
```

### `backend/pyproject.toml`

Add dependencies:
```toml
dependencies = [
    # ... existing ...
    "httpx>=0.27.0",
    "redis>=5.0.0",
    "pytest-recording>=0.13.0",
]
```

## Testing Checklist

- [ ] RateLimiter: All unit tests pass with fakeredis
- [ ] PriceCache: All unit tests pass with fakeredis
- [ ] AlphaVantageAdapter: Integration tests pass with VCR cassettes
- [ ] VCR cassettes recorded for all scenarios
- [ ] Tests pass WITHOUT real API key in environment
- [ ] Error handling tested for all failure modes
- [ ] Type checking passes (pyright --strict)
- [ ] Linting passes (ruff check)
- [ ] Test coverage ≥80% for new code

## Implementation Notes

### Phase 2a vs 2b Split

This task is **Phase 2a** (MVP):
- Implements `get_current_price()` only (not `get_price_at()` or `get_price_history()`)
- PostgreSQL integration stubbed (will implement in Task 021)
- Focus on proving the caching and rate limiting infrastructure works

**Phase 2b** (future tasks) will add:
- Historical data fetching (`get_price_at()`, `get_price_history()`)
- PostgreSQL price repository integration
- Batch fetching optimizations
- Time-aware caching (different TTLs for different times of day)

### Error Handling Philosophy

Follow the architecture's error handling strategy:
- **Graceful degradation**: Serve stale data when rate limited (if available)
- **Clear exceptions**: Use domain exceptions from `application/exceptions.py`
- **Logging**: Log all API calls, rate limit hits, cache misses for observability
- **User-friendly**: Map technical errors to business errors (e.g., "Symbol not found" vs "HTTP 404")

### Performance Targets

From the architecture plan:
- Redis cache hit: <100ms
- PostgreSQL fallback: <500ms (future task)
- API call: <2s (Alpha Vantage typical response time)

Test these targets in integration tests.

## Definition of Done

- [ ] All success criteria met
- [ ] All tests passing (289 existing + ~40 new = ~330 total)
- [ ] Type checking passes (pyright --strict)
- [ ] Linting passes (ruff check, ruff format)
- [ ] PR created with clear description
- [ ] Self-reviewed for architecture compliance
- [ ] Progress document created in `agent_progress_docs/`
- [ ] Ready for architect review

## Next Steps

After this task completes:
- **Task 021**: PostgreSQL Price Repository (integrate Tier 2 caching)
- **Task 022**: Portfolio Queries with Live Prices (use case layer)
- **Task 023**: Real Price Display UI (frontend integration)

This task is the **critical path** - it's the longest task and blocks all subsequent Phase 2 work. Prioritize getting this right!
