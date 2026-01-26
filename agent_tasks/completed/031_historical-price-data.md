# Task 031: Phase 2b - Historical Price Data Storage

## Priority

**HIGH** - Core functionality for Phase 2b

## Dependencies

⚠️  **BLOCKED** until PR #40 (Task 030 - Trade API fix) is merged

## Objective

Extend the market data system to store and query historical price data, enabling:
- Price history queries for any ticker and time range
- Background batch import of historical data
- Foundation for Phase 3 backtesting

## Context

Phase 2a implemented current price fetching and caching. Phase 2b extends this to historical data.

**Architecture Reference**: [docs/architecture/20251228_phase2-market-data/](cci:7://file:///Users/timchild/github/Zebu/docs/architecture/20251228_phase2-market-data/:0:0-0:0)

## Requirements

### 1. MarketDataPort Extensions

Implement the remaining methods in `MarketDataPort`:

```python
@abstractmethod
async def get_price_at(
    self, ticker: Ticker, timestamp: datetime
) -> Optional[PricePoint]:
    """Get price at specific timestamp (for backtesting)"""
    pass

@abstractmethod
async def get_price_history(
    self, ticker: Ticker, start: datetime, end: datetime
) -> List[PricePoint]:
    """Get price history for a time range"""
    pass
```

### 2. Alpha Vantage Historical Data

Extend `AlphaVantageAdapter` to fetch historical data:
- Use `TIME_SERIES_DAILY` endpoint for historical prices
- Parse and convert to `PricePoint` objects
- Handle pagination if needed
- Respect rate limits (same limiter as current price)

### 3. Price Repository Storage

Extend `PriceRepository` to:
- Store historical price data in PostgreSQL
- Query price at specific timestamp (nearest)
- Query price range with optional sampling/filtering
- Efficient indexing on (ticker, timestamp)

### 4. Caching Strategy

For historical data:
- Redis: Cache recent history queries (last 30 days)
- PostgreSQL: Store all historical data
- No caching for very old data (rare queries)

### 5. Database Schema

Add to existing `price_cache` table or create new `price_history` table:
```sql
CREATE TABLE price_history (
    id UUID PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    price DECIMAL(12, 4) NOT NULL,
    source VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (ticker, timestamp)
);

CREATE INDEX idx_price_history_ticker_timestamp
    ON price_history (ticker, timestamp DESC);
```

## Implementation Plan

### Step 1: Domain & Application Layer
1. No changes needed in Domain (PricePoint already supports timestamps)
2. Optionally add query: `GetPriceHistoryQuery` in Application layer
3. Update `MarketDataPort` with new methods (if not already done)

### Step 2: Infrastructure Layer
1. Extend `AlphaVantageAdapter`:
   - Add `fetch_daily_prices(ticker, outputsize='full')` method
   - Parse TIME_SERIES_DAILY response
   - Convert to List[PricePoint]

2. Extend `PriceRepository`:
   - Add `save_price_history(ticker, prices)` - bulk insert
   - Add `get_price_at(ticker, timestamp)` - find nearest
   - Add `get_price_history(ticker, start, end)`

3. Extend `RedisCacheAdapter`:
   - Cache history queries with key pattern: `history:{ticker}:{start}:{end}`
   - TTL: 24 hours for recent data

### Step 3: API Layer
Add endpoint:
```
GET /api/v1/prices/{ticker}/history?start=2024-01-01&end=2024-12-31
```

Response:
```json
{
  "ticker": "AAPL",
  "prices": [
    {"timestamp": "2024-01-01T16:00:00Z", "price": "150.25"},
    ...
  ],
  "source": "alpha_vantage",
  "cached": true
}
```

### Step 4: Testing
- Unit tests for AlphaVantageAdapter historical fetch
- Integration tests for PriceRepository history methods
- Test cache hit/miss for history queries
- Test nearest timestamp matching for `get_price_at()`

## Success Criteria

- [ ] `get_price_at()` returns nearest price for any timestamp
- [ ] `get_price_history()` returns price series for date range
- [ ] Historical data persisted in PostgreSQL
- [ ] History queries cached in Redis
- [ ] API endpoint returns historical data
- [ ] All tests pass (unit + integration)
- [ ] Rate limiting works for historical fetches
- [ ] Graceful handling when historical data unavailable

## Testing Strategy

1. **VCR Tests**: Record Alpha Vantage responses
2. **Repository Tests**: Test timestamp queries, range queries
3. **Cache Tests**: Verify history caching behavior
4. **E2E Test**: Fetch and display 1 year of AAPL history

## Files to Change

- [ ] `backend/src/zebu/application/ports/market_data.py` - Port interface
- [ ] `backend/src/zebu/adapters/outbound/alpha_vantage.py` - Historical fetch
- [ ] `backend/src/zebu/adapters/outbound/price_repository.py` - Storage
- [ ] `backend/src/zebu/adapters/outbound/redis_cache.py` - History caching
- [ ] `backend/src/zebu/adapters/inbound/api/prices.py` - New endpoint (or create it)
- [ ] Database migration for price_history table
- [ ] Tests for all above

## Notes

- This task focuses on **backend only** - no frontend work
- Frontend price charts will be a separate task (032)
- Consider adding a batch import script for common stocks
- Rate limiting is critical - historical data uses same quota

## References

- [ADR 001: Caching Strategy](cci:7://file:///Users/timchild/github/Zebu/docs/architecture/20251228_phase2-market-data/adr-001-caching-strategy.md:0:0-0:0)
- [Database Schema](cci:7://file:///Users/timchild/github/Zebu/docs/architecture/20251228_phase2-market-data/database-schema.md:0:0-0:0)
- [Implementation Guide](cci:7://file:///Users/timchild/github/Zebu/docs/architecture/20251228_phase2-market-data/implementation-guide.md:0:0-0:0)

---

**Created**: January 1, 2026
**Estimated Time**: 6-8 hours
**Agent**: backend-swe
