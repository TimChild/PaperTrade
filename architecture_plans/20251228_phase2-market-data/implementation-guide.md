# Phase 2 Market Data Integration - Implementation Guide

**Created**: 2025-12-28  
**Status**: Approved  
**Audience**: Backend-SWE and Frontend-SWE agents

## Overview

This guide provides step-by-step instructions for implementing Phase 2 Market Data Integration. Follow these steps sequentially to ensure correct implementation.

## Pre-Implementation Checklist

Before starting any task:
- [ ] Read [overview.md](./overview.md) - Understand goals and context
- [ ] Read [interfaces.md](./interfaces.md) - Understand data structures
- [ ] Read relevant ADRs (adr-001 through adr-004) - Understand decisions
- [ ] Read [database-schema.md](./database-schema.md) - Understand storage
- [ ] Review Phase 1 code patterns (domain, application, adapters layers)

## Phase 2a: Current Price Only (Week 1)

### Task 015: Domain Models and Interfaces (2-3 hours)

**Agent**: Backend-SWE  
**Dependencies**: None  
**Branch**: `feature/phase2-domain-models`

#### Objectives
1. Create PricePoint value object (or DTO - decide based on domain semantics)
2. Define MarketDataError exception hierarchy
3. Update application layer exceptions

#### Files to Create/Modify

**Create**:
- `backend/src/papertrade/domain/value_objects/price_point.py` (if value object)
- OR `backend/src/papertrade/application/dtos/price_point_dto.py` (if DTO)
- `backend/src/papertrade/application/exceptions.py` (extend with market data errors)

**Tests**:
- `backend/tests/unit/domain/value_objects/test_price_point.py` (if value object)
- `backend/tests/unit/application/test_exceptions.py` (market data errors)

#### Implementation Steps

**Step 1**: Decide PricePoint classification
- **Question**: Is PricePoint a domain concept or just data transfer?
- **If domain**: Stock prices are external facts (not behavior) → Lean toward DTO
- **If DTO**: Lives in application layer, lighter weight

**Step 2**: Implement PricePoint (based on [interfaces.md](./interfaces.md#pricepoint-value-object))
- All properties from specification
- Validation (positive prices, UTC timestamps, valid source)
- `is_stale()` method
- `with_source()` method
- Equality semantics
- String representation

**Step 3**: Implement MarketDataError hierarchy
- Base: `MarketDataError(Exception)`
- Subclass: `TickerNotFoundError(MarketDataError)`
- Subclass: `MarketDataUnavailableError(MarketDataError)`
- Subclass: `InvalidPriceDataError(MarketDataError)`
- Each with attributes from specification

**Step 4**: Write comprehensive tests
- PricePoint validation (all constraints)
- PricePoint methods (is_stale, with_source)
- Exception messages and attributes
- Edge cases (timezone handling, None values)

#### Success Criteria
- [ ] All tests passing (target: 30+ tests)
- [ ] Pyright strict mode passing
- [ ] Ruff linting passing
- [ ] PricePoint follows Money/Ticker patterns from Phase 1
- [ ] Exception hierarchy matches specification

---

### Task 016: MarketDataPort Interface (1-2 hours)

**Agent**: Backend-SWE  
**Dependencies**: Task 015  
**Branch**: `feature/phase2-market-data-port`

#### Objectives
1. Define MarketDataPort Protocol interface
2. Create in-memory mock implementation for testing
3. Update application layer to use port

#### Files to Create

**Create**:
- `backend/src/papertrade/application/ports/market_data_port.py`
- `backend/src/papertrade/application/ports/in_memory_market_data.py` (for testing)

**Tests**:
- `backend/tests/unit/application/ports/test_market_data_port.py`

#### Implementation Steps

**Step 1**: Implement MarketDataPort Protocol
- Use `typing.Protocol` (like PortfolioRepository)
- All methods from [interfaces.md](./interfaces.md#marketdataport-interface)
- Full type hints (ticker: Ticker, timestamp: datetime, etc.)
- Comprehensive docstrings (parameters, returns, raises)

**Step 2**: Implement InMemoryMarketDataPort (for testing)
- Store prices in `Dict[Ticker, List[PricePoint]]`
- Implement all interface methods
- Support seeding with test data
- Thread-safe (use locks if needed)

**Step 3**: Write protocol compliance tests
- Test that InMemoryMarketDataPort implements protocol
- Test all methods (get_current_price, get_price_at, get_price_history)
- Test error cases (ticker not found, no data)

#### Success Criteria
- [ ] Protocol matches specification exactly
- [ ] InMemoryMarketDataPort works for testing
- [ ] Tests demonstrate all interface methods
- [ ] Can seed test data easily

---

### Task 017: Alpha Vantage Adapter with Rate Limiting (6-8 hours)

**Agent**: Backend-SWE  
**Dependencies**: Task 016  
**Branch**: `feature/phase2-alpha-vantage-adapter`

#### Objectives
1. Implement RateLimiter (token bucket algorithm)
2. Implement PriceCache (Redis wrapper)
3. Implement AlphaVantageAdapter (implements MarketDataPort)
4. Set up VCR cassettes for testing

#### Files to Create

**Infrastructure**:
- `backend/src/papertrade/infrastructure/rate_limiter.py`
- `backend/src/papertrade/infrastructure/cache/price_cache.py`

**Adapters**:
- `backend/src/papertrade/adapters/outbound/alpha_vantage_adapter.py`

**Tests**:
- `backend/tests/unit/infrastructure/test_rate_limiter.py`
- `backend/tests/unit/infrastructure/test_price_cache.py`
- `backend/tests/integration/adapters/test_alpha_vantage_adapter.py`

**VCR Cassettes**:
- `backend/tests/cassettes/alpha_vantage_current_price_aapl.yaml`
- `backend/tests/cassettes/alpha_vantage_ticker_not_found.yaml`
- `backend/tests/cassettes/alpha_vantage_rate_limited.yaml`

#### Implementation Steps

**Step 1**: Implement RateLimiter
- Token bucket algorithm (see [adr-002-rate-limiting.md](./adr-002-rate-limiting.md))
- Dual time windows (minute + day)
- Redis-backed token storage
- Lua script for atomic check-and-consume
- Methods: `can_make_request()`, `consume_token()`, `wait_time()`

**Step 2**: Implement PriceCache
- Redis client wrapper
- Methods: `get()`, `set()`, `delete()`, `exists()`, `get_ttl()`
- JSON serialization for PricePoint
- Key format: `papertrade:price:{ticker}`

**Step 3**: Implement AlphaVantageAdapter
- Tiered fallback strategy (Redis → PostgreSQL → API)
- HTTP client with timeout and retries
- Parse Alpha Vantage GLOBAL_QUOTE response
- Error mapping (API errors → PaperTrade exceptions)
- Integration with RateLimiter and PriceCache

**Step 4**: Set up VCR (pytest-recording)
- Install pytest-recording
- Record real API responses (run once with real API key)
- Replay in tests (no API key needed)
- Test success, failure, rate limit scenarios

**Step 5**: Write comprehensive tests
- RateLimiter: Token consumption, refill, dual windows
- PriceCache: CRUD operations, TTL expiration
- AlphaVantageAdapter: All code paths (cache hit, miss, API success, API error)

#### Success Criteria
- [ ] RateLimiter prevents quota exhaustion (tested)
- [ ] PriceCache works with Redis (use fakeredis for tests)
- [ ] AlphaVantageAdapter implements MarketDataPort
- [ ] VCR cassettes recorded for all scenarios
- [ ] Tests pass without real API calls
- [ ] Integration test with real API (manual, optional)

---

### Task 018: PostgreSQL Price Repository (4-5 hours)

**Agent**: Backend-SWE  
**Dependencies**: Task 015  
**Branch**: `feature/phase2-price-repository`

#### Objectives
1. Create database migration for price_history table
2. Create SQLModel model for price_history
3. Implement PriceRepository adapter
4. Implement WatchlistManager

#### Files to Create

**Models**:
- `backend/src/papertrade/adapters/outbound/models/price_history.py`
- `backend/src/papertrade/adapters/outbound/models/ticker_watchlist.py`

**Repositories**:
- `backend/src/papertrade/adapters/outbound/repositories/price_repository.py`
- `backend/src/papertrade/adapters/outbound/repositories/watchlist_manager.py`

**Migrations**:
- `backend/migrations/versions/002_phase2_price_history.py`
- `backend/migrations/versions/003_phase2_ticker_watchlist.py`

**Tests**:
- `backend/tests/integration/repositories/test_price_repository.py`
- `backend/tests/integration/repositories/test_watchlist_manager.py`

#### Implementation Steps

**Step 1**: Create Alembic migrations
- Follow [database-schema.md](./database-schema.md)
- price_history table with all columns, indexes, constraints
- ticker_watchlist table
- Pre-populate common stocks in watchlist

**Step 2**: Create SQLModel models
- PriceHistoryModel maps to price_history table
- TickerWatchlistModel maps to ticker_watchlist table
- Validators for constraints
- Helper methods (to_price_point, from_price_point)

**Step 3**: Implement PriceRepository
- Methods from [interfaces.md](./interfaces.md#pricerepository-interface)
- Async operations (use SQLModel async session)
- Efficient queries (use indexes)
- Upsert behavior (ON CONFLICT DO UPDATE)

**Step 4**: Implement WatchlistManager
- Add/remove tickers
- Get stale tickers for refresh
- Update refresh metadata
- Priority management

**Step 5**: Write integration tests
- Test with real PostgreSQL (or SQLite for speed)
- Test all repository methods
- Test index usage (EXPLAIN queries)
- Test constraint enforcement

#### Success Criteria
- [ ] Migrations run successfully
- [ ] Models match schema specification
- [ ] Repository implements all methods efficiently
- [ ] Common stocks pre-populated in watchlist
- [ ] Integration tests pass with database
- [ ] Performance targets met (<100ms for queries)

---

### Task 019: Update Portfolio Use Cases (3-4 hours)

**Agent**: Backend-SWE  
**Dependencies**: Tasks 016, 017, 018  
**Branch**: `feature/phase2-portfolio-real-prices`

#### Objectives
1. Update GetPortfolioBalance query to use real prices
2. Update GetHoldings query to include real prices
3. Inject MarketDataPort into use cases

#### Files to Modify

**Application Layer**:
- `backend/src/papertrade/application/queries/get_portfolio_balance.py`
- `backend/src/papertrade/application/queries/get_portfolio_holdings.py`

**Adapters Layer**:
- `backend/src/papertrade/adapters/inbound/api/dependencies.py` (add market data DI)
- `backend/src/papertrade/adapters/inbound/api/routes/portfolios.py` (inject port)

**Tests**:
- `backend/tests/unit/application/queries/test_get_portfolio_balance.py` (update)
- `backend/tests/unit/application/queries/test_get_portfolio_holdings.py` (update)

#### Implementation Steps

**Step 1**: Update GetPortfolioBalance
- Add `market_data: MarketDataPort` parameter
- For each holding, call `market_data.get_current_price(ticker)`
- Calculate portfolio value with real prices
- Handle errors (ticker not found → use $0, log warning)

**Step 2**: Update GetHoldings  
- Add current price to HoldingDTO
- Include unrealized gain/loss calculation
- Include price timestamp and source

**Step 3**: Update dependency injection
- Create `get_market_data()` dependency (FastAPI Depends)
- Wire AlphaVantageAdapter with config (API key, rate limiter, cache, repository)
- Inject into portfolio routes

**Step 4**: Update tests
- Mock MarketDataPort in unit tests
- Test with different price scenarios (normal, error, stale)
- Integration test with InMemoryMarketDataPort

#### Success Criteria
- [ ] Portfolio value calculated with real prices
- [ ] Holdings show current price and gain/loss
- [ ] Errors handled gracefully (missing prices)
- [ ] Tests pass with mocked market data
- [ ] Integration test with real adapter (manual)

---

### Task 020: Frontend - Display Real Portfolio Values (4-5 hours)

**Agent**: Frontend-SWE  
**Dependencies**: Task 019  
**Branch**: `feature/phase2-frontend-real-prices`

#### Objectives
1. Update API client to handle new holding fields (current price)
2. Update PortfolioDashboard to display real values
3. Add price update indicator (timestamp, source)
4. Add manual refresh button

#### Files to Modify

**API Client**:
- `frontend/src/api/types.ts` (add current_price to Holding type)
- `frontend/src/api/adapters.ts` (adapt new fields)

**Components**:
- `frontend/src/components/PortfolioDashboard.tsx` (show real values)
- `frontend/src/components/HoldingsTable.tsx` (add price columns)
- `frontend/src/components/PriceIndicator.tsx` (new: show price metadata)

**Hooks**:
- `frontend/src/hooks/usePortfolio.ts` (update types)

**Config**:
- `frontend/src/config/index.ts` (load config.toml, implement Zod validation)

#### Implementation Steps

**Step 1**: Implement config loading (TypeScript)
- Install smol-toml and zod
- Create Zod schema matching config.example.toml
- Load config at app initialization
- Validate with helpful error messages

**Step 2**: Update API types
- Add `current_price: Money` to Holding interface
- Add `unrealized_gain_loss: Money` to Holding interface
- Add `price_timestamp: string` and `price_source: string`

**Step 3**: Update PortfolioDashboard
- Display total portfolio value (with real prices)
- Show last update timestamp
- Add "Refresh Prices" button (triggers API refetch)
- Handle loading and error states

**Step 4**: Update HoldingsTable
- Add "Current Price" column
- Add "Value" column (quantity × current price)
- Add "Gain/Loss" column (unrealized gain/loss)
- Color-code gain (green) vs loss (red)

**Step 5**: Create PriceIndicator component
- Shows price timestamp ("as of 2:30 PM")
- Shows price source ("cached" vs "live")
- Warning icon if stale (>1 hour old)

#### Success Criteria
- [ ] Portfolio displays real market values
- [ ] Holdings table shows prices and gain/loss
- [ ] Price metadata visible (timestamp, source)
- [ ] Refresh button works (triggers refetch)
- [ ] Loading and error states handled
- [ ] Config loads from TOML file
- [ ] All tests passing (update existing tests)

---

## Phase 2b: Historical Data (Week 2)

### Task 021: Implement Historical Price Queries (4-5 hours)

**Agent**: Backend-SWE  
**Dependencies**: Task 018  
**Branch**: `feature/phase2-historical-queries`

#### Objectives
1. Implement `get_price_at()` in AlphaVantageAdapter
2. Implement `get_price_history()` in AlphaVantageAdapter
3. Add Alpha Vantage TIME_SERIES_DAILY endpoint support

#### Files to Modify

**Adapters**:
- `backend/src/papertrade/adapters/outbound/alpha_vantage_adapter.py`
- `backend/src/papertrade/adapters/outbound/repositories/price_repository.py`

**Tests**:
- `backend/tests/integration/adapters/test_alpha_vantage_adapter.py`
- `backend/tests/cassettes/alpha_vantage_daily_history_aapl.yaml`

#### Implementation Steps

**Step 1**: Implement `get_price_at()`
- Query PriceRepository for closest price
- If not found, optionally fetch from Alpha Vantage (Phase 2b optional)
- Return PricePoint with actual timestamp

**Step 2**: Implement `get_price_history()`
- Query PriceRepository for date range
- Return list of PricePoints, ordered chronologically
- Handle partial data (gaps in history)

**Step 3**: Add TIME_SERIES_DAILY support
- Parse Alpha Vantage daily data format
- Batch insert to PriceRepository
- Respect rate limits (one API call = 100+ days of data)

**Step 4**: Record VCR cassettes
- Daily history for AAPL (1 year)
- Edge cases (empty range, future dates)

#### Success Criteria
- [ ] Historical queries work efficiently
- [ ] Phase 3 backtesting is unblocked
- [ ] Tests verify correctness
- [ ] Performance targets met

---

### Task 022: Batch Import for Common Stocks (3-4 hours)

**Agent**: Backend-SWE  
**Dependencies**: Task 021  
**Branch**: `feature/phase2-batch-import`

#### Objectives
1. Create CLI command for batch import
2. Import 1 year of daily data for common stocks
3. Add progress logging

#### Files to Create

**CLI**:
- `backend/src/papertrade/cli/import_prices.py`

**Tests**:
- `backend/tests/integration/cli/test_import_prices.py`

#### Implementation Steps

**Step 1**: Create import command
- Click CLI framework
- Import tickers from watchlist
- Fetch daily history (Alpha Vantage TIME_SERIES_DAILY)
- Store in PriceRepository
- Progress bar (tqdm)

**Step 2**: Run import manually
```bash
python -m papertrade.cli.import_prices --lookback-days=365
```

**Step 3**: Document process
- Add to README (how to populate initial data)
- Add to ops guide (re-running import)

#### Success Criteria
- [ ] Can import 1 year of data for 10 stocks in <5 minutes
- [ ] Progress logged clearly
- [ ] Respects rate limits
- [ ] Handles errors gracefully

---

### Task 023: Background Refresh Scheduler (5-6 hours)

**Agent**: Backend-SWE  
**Dependencies**: Task 018  
**Branch**: `feature/phase2-scheduler`

#### Objectives
1. Set up APScheduler
2. Implement daily refresh job
3. Add job monitoring and logging

#### Files to Create

**Infrastructure**:
- `backend/src/papertrade/infrastructure/scheduler/scheduler.py`
- `backend/src/papertrade/infrastructure/scheduler/jobs/refresh_prices.py`

**Tests**:
- `backend/tests/unit/infrastructure/scheduler/test_refresh_job.py`

#### Implementation Steps

**Step 1**: Install APScheduler
```bash
pip install apscheduler
```

**Step 2**: Configure scheduler
- Load cron expression from config
- Job persistence to PostgreSQL
- Error handling and logging

**Step 3**: Implement refresh job
- Get stale tickers from WatchlistManager
- Batch fetch with rate limiting
- Update PriceRepository and cache
- Log summary (success/error counts)

**Step 4**: Integrate with FastAPI
- Start scheduler on app startup
- Stop scheduler on shutdown
- Add admin endpoint to trigger manually

**Step 5**: Test thoroughly
- Unit test job logic (mock dependencies)
- Integration test with test database
- Manual test (trigger job via endpoint)

#### Success Criteria
- [ ] Job runs on schedule (midnight UTC)
- [ ] Prices refreshed successfully
- [ ] Errors logged and handled
- [ ] Job can be triggered manually
- [ ] Scheduler starts/stops cleanly

---

### Task 024: Frontend - Price History Charts (6-8 hours)

**Agent**: Frontend-SWE  
**Dependencies**: Task 021  
**Branch**: `feature/phase2-price-charts`

#### Objectives
1. Add price chart component (Recharts or Chart.js)
2. Add API endpoint for price history
3. Display charts in holdings detail view

#### Files to Create

**Components**:
- `frontend/src/components/PriceChart.tsx`
- `frontend/src/pages/HoldingDetail.tsx`

**API**:
- `backend/src/papertrade/adapters/inbound/api/routes/market_data.py` (new)

**Hooks**:
- `frontend/src/hooks/usePriceHistory.ts`

#### Implementation Steps

**Step 1**: Create API endpoint
- `GET /api/v1/market-data/price-history/{ticker}`
- Query params: start, end, interval
- Returns list of PricePoints

**Step 2**: Create price chart component
- Install chart library (Recharts recommended)
- Line chart with OHLC support
- Timeframe selector (1D, 1W, 1M, 1Y)
- Responsive design

**Step 3**: Create holding detail page
- Shows holding info + price chart
- Links from holdings table
- Price history below chart

**Step 4**: Implement hook
- Fetch price history from API
- TanStack Query for caching
- Handle loading/error states

#### Success Criteria
- [ ] Charts display correctly
- [ ] Timeframe selector works
- [ ] Data cached appropriately
- [ ] Responsive on mobile
- [ ] Tests passing

---

### Task 025: Testing and Quality Validation (4-5 hours)

**Agent**: Backend-SWE or Quality-Assurance agent  
**Dependencies**: All previous tasks  
**Branch**: `feature/phase2-final-testing`

#### Objectives
1. Run full test suite (backend + frontend)
2. Integration test end-to-end flow
3. Performance testing (cache hit rates, query times)
4. Security scan (CodeQL)
5. Update documentation

#### Implementation Steps

**Step 1**: Run all tests
```bash
# Backend
task test:backend

# Frontend  
task test:frontend
```

**Step 2**: Integration testing
- Manual test: View portfolio → See real prices
- Manual test: Refresh prices → See updated values
- Manual test: View price chart → See historical data
- Manual test: Background job → Verify prices refreshed

**Step 3**: Performance testing
- Check cache hit rates (should be >85%)
- Check query times (should meet targets)
- Check API call counts (should be <20/hour)

**Step 4**: Security scan
- Run CodeQL
- Check for secrets in code
- Verify API keys not logged

**Step 5**: Update documentation
- README: How to get API key
- README: How to run batch import
- PROGRESS.md: Update with Phase 2 completion

#### Success Criteria
- [ ] All tests passing (200+ backend, 25+ frontend)
- [ ] Integration tests pass
- [ ] Performance targets met
- [ ] Security scan clean
- [ ] Documentation updated

---

## Infrastructure Setup (Parallel with Phase 2a)

Can be done anytime during Phase 2a:

### Redis Setup

**Local Development**:
```bash
# Add to docker-compose.yml
redis:
  image: redis:7-alpine
  ports:
    - "6379:6379"
  volumes:
    - redis_data:/data

# Start Redis
docker-compose up -d redis
```

**Tests**:
```bash
pip install fakeredis
```

### Configuration Files

**Backend**:
1. Copy `backend/config.example.toml` to `backend/config.toml`
2. Update `.env` with Alpha Vantage API key
3. Verify config loads at startup

**Frontend**:
1. Copy `frontend/config.example.toml` to `frontend/config.toml`
2. Verify config loads in browser console

---

## Common Patterns from Phase 1

### Value Objects
- Immutable (`@dataclass(frozen=True)`)
- Validation in `__post_init__`
- Full type hints
- Rich methods (add, subtract, multiply for Money)

### Repository Ports
- Use `Protocol` class
- Async methods (`async def`)
- Clear error semantics (None vs Exception)
- Full docstrings

### Testing
- pytest for backend
- Vitest for frontend
- Mock at architecture boundaries (ports)
- Integration tests with real DB (test container)

### Dependency Injection
- FastAPI `Depends()`
- Factories for adapters (`get_market_data()`)
- Config injected from settings

---

## Troubleshooting

### Redis Connection Errors
```python
# Graceful fallback if Redis unavailable
try:
    cache = PriceCache(redis_url)
except ConnectionError:
    logger.warning("Redis unavailable, using no-op cache")
    cache = NoOpCache()  # All methods return None/do nothing
```

### API Key Issues
```bash
# Verify API key works
curl "https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=AAPL&apikey=YOUR_API_KEY"

# Should return JSON with price data
```

### Rate Limiting Issues
```python
# Check rate limiter status
status = rate_limiter.get_status()
print(f"Minute tokens: {status['minute_tokens']}")
print(f"Day tokens: {status['day_tokens']}")
```

### Database Migration Issues
```bash
# Check migration status
alembic current

# Run migrations
alembic upgrade head

# Rollback if needed
alembic downgrade -1
```

---

## Quality Checklist

Before merging any PR:
- [ ] All tests passing (run `task test`)
- [ ] Linting passing (run `task lint`)
- [ ] Type checking passing (run `task typecheck`)
- [ ] Code review requested
- [ ] Documentation updated
- [ ] No secrets in code
- [ ] Performance acceptable
- [ ] Error handling comprehensive

---

## Next Steps After Phase 2

Once Phase 2 is complete:
1. Update PROGRESS.md with completion
2. Demo to stakeholders
3. Retrospective (what worked, what didn't)
4. Plan Phase 3 (Time Machine backtesting)
5. Consider premium API tier upgrade (if needed)

---

## Questions?

If specifications are unclear:
1. Check existing code for patterns
2. Review Phase 1 architecture plans
3. Ask for clarification in PR comments
4. Document assumptions in code comments

## References

- [Phase 1 Implementation Sequence](../20251227_phase1-backend-mvp/implementation-sequence.md)
- [Alpha Vantage API Documentation](https://www.alphavantage.co/documentation/)
- [pytest-recording (VCR)](https://github.com/kiwicom/pytest-recording)
- [APScheduler Documentation](https://apscheduler.readthedocs.io/)
- [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
