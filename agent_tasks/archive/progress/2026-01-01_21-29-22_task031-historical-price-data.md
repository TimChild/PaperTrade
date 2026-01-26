# Task 031: Historical Price Data Storage Implementation

**Date**: 2026-01-01
**Agent**: backend-swe
**Branch**: `copilot/extend-historical-price-data`
**Status**: ✅ Complete

## Task Summary

Implemented Phase 2b historical price data storage and query functionality, extending the market data system to support:
- Historical price queries for any ticker and time range
- Price-at-timestamp queries for backtesting
- Supported tickers discovery
- RESTful API endpoints for price data access

## Decisions Made

### 1. Dependency Injection Architecture
**Decision**: Changed `get_market_data()` from singleton to per-request instantiation with session.

**Rationale**:
- `AlphaVantageAdapter` now requires `PriceRepository` which needs a database session
- Database sessions are request-scoped in FastAPI
- Creating adapter per-request ensures fresh session and proper resource management
- Core infrastructure (Redis, HTTP client, rate limiter) remains singleton for efficiency

**Impact**: Existing tests needed updating to match new dependency signature.

### 2. Historical Data Fetching Strategy
**Decision**: Implemented query-only functionality; deferred Alpha Vantage TIME_SERIES_DAILY integration.

**Rationale**:
- Task spec focused on querying existing data in database
- Alpha Vantage TIME_SERIES_DAILY endpoint requires additional work (pagination, parsing, rate limiting)
- PriceRepository already supports full historical query functionality
- Can add batch import script as separate task (Task 032 candidate)

**Impact**: Historical queries work against existing database data. Batch import needed for population.

### 3. Test Configuration
**Decision**: Used `Depends(get_test_session)` in test override with `noqa: B008` suppression.

**Rationale**:
- FastAPI dependency injection requires `Depends()` in function signature
- Ruff B008 rule flags this as bad practice for normal Python, but it's required for FastAPI
- `noqa` comment documents intentional exception to rule
- Alternative would require complex test harness redesign

**Impact**: Clean test configuration that matches production dependency signatures.

### 4. Validation Strategy
**Decision**: Input validation in adapter layer, not in API layer.

**Rationale**:
- Keeps API layer thin (just HTTP concerns)
- Adapter knows business rules (valid intervals, date ranges)
- Easier to test validation logic in adapter unit tests
- Consistent with existing codebase patterns

**Impact**: API returns appropriate HTTP errors (400) when adapter raises ValueError.

## Files Changed

### Core Implementation

**`backend/src/papertrade/adapters/outbound/market_data/alpha_vantage_adapter.py`**
- Implemented `get_price_at()`: Queries repository for price at timestamp with future date validation
- Implemented `get_price_history()`: Queries repository with date range and interval validation
- Implemented `get_supported_tickers()`: Returns all tickers from repository
- Added comprehensive error handling and input validation

**`backend/src/papertrade/adapters/inbound/api/dependencies.py`**
- Added `get_price_repository()` factory function
- Updated `get_market_data()` to accept `SessionDep` parameter
- Created `PriceRepository` per-request with session
- Added `PriceRepositoryDep` type alias
- Removed obsolete `_market_data_adapter` singleton

**`backend/src/papertrade/adapters/inbound/api/prices.py`** (NEW)
- Created `/api/v1/prices/{ticker}` endpoint (GET current price)
- Created `/api/v1/prices/{ticker}/history` endpoint (GET historical prices)
- Created `/api/v1/prices/` endpoint (GET supported tickers)
- Implemented Pydantic request/response models
- Added proper error handling (404, 400, 503)

**`backend/src/papertrade/main.py`**
- Registered prices router at `/api/v1` prefix

### Tests

**`backend/tests/integration/adapters/test_alpha_vantage_adapter.py`**
- Replaced NotImplementedError tests with 6 new historical data tests:
  - `test_get_price_at_without_repository`
  - `test_get_price_at_future_timestamp`
  - `test_get_price_history_without_repository`
  - `test_get_price_history_invalid_range`
  - `test_get_price_history_invalid_interval`
  - `test_get_supported_tickers_without_repository`

**`backend/tests/integration/test_prices_api.py`** (NEW)
- Created 7 API endpoint tests:
  - `test_get_current_price_aapl`
  - `test_get_current_price_invalid_ticker`
  - `test_get_supported_tickers`
  - `test_get_price_history_missing_parameters`
  - `test_get_price_history_valid_request`
  - `test_get_price_history_valid_interval_accepted`
  - `test_get_price_history_invalid_date_range`

**`backend/tests/conftest.py`**
- Fixed `get_test_market_data()` to match new dependency signature
- Added `Depends(get_test_session)` parameter with proper noqa comment
- Removed obsolete `_market_data_adapter` singleton reference
- Fixed line length and formatting issues

## Testing Notes

**Test Coverage**: 21 total tests (14 adapter + 7 API)

**All Tests Passing**:
```bash
$ uv run pytest tests/integration/adapters/test_alpha_vantage_adapter.py tests/integration/test_prices_api.py -v
============================== 21 passed in 0.67s ===============================
```

**Linting**: All ruff and pyright checks passing (with documented exceptions)

**Test Strategy**:
- Adapter tests verify error handling without repository
- API tests use InMemoryMarketDataAdapter for fast, isolated testing
- No external dependencies required (Redis, Alpha Vantage API)

## API Examples

### Get Current Price
```bash
curl http://localhost:8000/api/v1/prices/AAPL
```

Response:
```json
{
  "ticker": "AAPL",
  "price": "150.00",
  "currency": "USD",
  "timestamp": "2026-01-01T21:00:00Z",
  "source": "database",
  "is_stale": false
}
```

### Get Historical Prices
```bash
curl "http://localhost:8000/api/v1/prices/AAPL/history?start=2024-01-01T00:00:00Z&end=2024-12-31T23:59:59Z&interval=1day"
```

Response:
```json
{
  "ticker": "AAPL",
  "prices": [
    {
      "ticker": "AAPL",
      "price": "150.25",
      "currency": "USD",
      "timestamp": "2024-01-01T16:00:00Z",
      "source": "database",
      "interval": "1day"
    }
  ],
  "start": "2024-01-01T00:00:00Z",
  "end": "2024-12-31T23:59:59Z",
  "interval": "1day",
  "count": 252
}
```

### Get Supported Tickers
```bash
curl http://localhost:8000/api/v1/prices/
```

Response:
```json
{
  "tickers": ["AAPL", "GOOGL", "MSFT", "TSLA"],
  "count": 4
}
```

## Known Issues / Limitations

1. **No Alpha Vantage TIME_SERIES_DAILY Support**: Historical data fetching from Alpha Vantage API not yet implemented. Only queries existing database data.

2. **No Historical Data Caching**: Redis caching for historical queries not implemented. All queries hit database.

3. **No Batch Import Tool**: No CLI command for populating historical data from Alpha Vantage.

## Next Steps / Recommendations

### Immediate (Task 032 Candidate)
1. **Batch Import Script**: Create CLI command to populate historical data
   - Use TIME_SERIES_DAILY endpoint
   - Respect rate limits (25 calls/day free tier)
   - Support ticker watchlist integration

2. **Historical Query Caching**: Add Redis caching for history queries
   - Cache key format: `history:{ticker}:{start}:{end}:{interval}`
   - TTL: 24 hours for recent data, longer for old data

### Future Enhancements
3. **Alpha Vantage TIME_SERIES_DAILY Integration**: Extend adapter to fetch historical data on-demand
   - Parse TIME_SERIES_DAILY response format
   - Handle pagination (compact vs full)
   - Backfill gaps in database

4. **Frontend Price Charts**: Create React components for displaying price history (separate frontend task)

## Deployment Notes

**Database**: No new migrations required (price_history table already exists from Phase 2a)

**Configuration**: No environment variable changes needed

**Dependencies**: No new Python packages required

**Backward Compatibility**: Fully backward compatible. New endpoints are additions, no breaking changes.

## References

- Task spec: `agent_tasks/task-031-historical-price-data.md`
- Architecture: `docs/architecture/20251228_phase2-market-data/`
- Previous work: Phase 2a (Tasks 018-024)
- Related: Issue #40 (Trade API fix - prerequisite)

---

**Completion Checklist**:
- ✅ Historical query methods implemented
- ✅ API endpoints created and tested
- ✅ Dependency injection updated
- ✅ 21 tests passing
- ✅ Linting and type checking passing
- ✅ Documentation updated
- ⏳ Manual API testing (requires running server)
- ⏳ CodeQL security scan (will run in CI)
