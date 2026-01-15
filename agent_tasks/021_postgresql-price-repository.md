# Task 021: PostgreSQL Price Repository

**Created**: 2025-12-29
**Agent**: backend-swe
**Estimated Effort**: 4-5 hours
**Dependencies**: Task 020 (Alpha Vantage Adapter merged)
**Phase**: Phase 2a - Market Data Integration

## Objective

Implement the PostgreSQL price repository to complete Tier 2 caching in the tiered market data architecture. This enables persistent storage of historical price data and improves the fallback strategy when Redis cache misses occur.

## Context

Task 020 implemented the Alpha Vantage adapter with Redis (Tier 1) and API (Tier 3) integration. This task completes the architecture by implementing Tier 2 (PostgreSQL) for persistent historical price storage.

### Architecture References
- [implementation-guide.md](../architecture_plans/20251228_phase2-market-data/implementation-guide.md#task-018-postgresql-price-repository-4-5-hours)
- [database-schema.md](../architecture_plans/20251228_phase2-market-data/database-schema.md)
- [interfaces.md](../architecture_plans/20251228_phase2-market-data/interfaces.md#pricerepository-interface)

## Success Criteria

- [ ] Alembic migrations created for price_history and ticker_watchlist tables
- [ ] SQLModel models implement database schema
- [ ] PriceRepository implements all interface methods
- [ ] WatchlistManager for ticker refresh tracking
- [ ] AlphaVantageAdapter integrated with PriceRepository
- [ ] Integration tests with database
- [ ] Performance <100ms for typical queries

## Implementation Details

### 1. Database Migrations

**Files to Create**:
- `backend/migrations/versions/002_phase2_price_history.py`
- `backend/migrations/versions/003_phase2_ticker_watchlist.py`

**price_history Table**:
```sql
CREATE TABLE price_history (
    id BIGSERIAL PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    price_amount DECIMAL(18, 2) NOT NULL,
    price_currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    timestamp TIMESTAMPTZ NOT NULL,
    source VARCHAR(50) NOT NULL,
    interval VARCHAR(10) NOT NULL,
    -- Optional OHLCV data
    open_amount DECIMAL(18, 2),
    open_currency VARCHAR(3),
    high_amount DECIMAL(18, 2),
    high_currency VARCHAR(3),
    low_amount DECIMAL(18, 2),
    low_currency VARCHAR(3),
    close_amount DECIMAL(18, 2),
    close_currency VARCHAR(3),
    volume BIGINT,
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT price_positive CHECK (price_amount > 0),
    CONSTRAINT unique_price UNIQUE (ticker, timestamp, source, interval)
);

-- Indexes for performance
CREATE INDEX idx_price_history_ticker_timestamp
    ON price_history(ticker, timestamp DESC);
CREATE INDEX idx_price_history_ticker_interval
    ON price_history(ticker, interval, timestamp DESC);
```

**ticker_watchlist Table**:
```sql
CREATE TABLE ticker_watchlist (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL UNIQUE,
    priority INTEGER NOT NULL DEFAULT 100,
    last_refresh_at TIMESTAMPTZ,
    next_refresh_at TIMESTAMPTZ,
    refresh_interval_seconds INTEGER NOT NULL DEFAULT 300,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index for refresh queries
CREATE INDEX idx_watchlist_next_refresh
    ON ticker_watchlist(next_refresh_at)
    WHERE is_active = TRUE;
```

**Pre-populate Common Stocks**:
```sql
INSERT INTO ticker_watchlist (ticker, priority) VALUES
    ('AAPL', 100),
    ('GOOGL', 100),
    ('MSFT', 100),
    ('AMZN', 100),
    ('TSLA', 90),
    ('NVDA', 90),
    ('META', 90),
    ('BRK.B', 80),
    ('V', 80),
    ('JPM', 80);
```

### 2. SQLModel Models

**File**: `backend/src/zebu/adapters/outbound/models/price_history.py`

```python
from datetime import datetime
from decimal import Decimal
from sqlmodel import Field, SQLModel
from typing import Optional

class PriceHistoryModel(SQLModel, table=True):
    """SQLModel for price_history table."""

    __tablename__ = "price_history"

    id: Optional[int] = Field(default=None, primary_key=True)
    ticker: str = Field(max_length=10, index=True)
    price_amount: Decimal = Field(decimal_places=2)
    price_currency: str = Field(default="USD", max_length=3)
    timestamp: datetime = Field(index=True)
    source: str = Field(max_length=50)
    interval: str = Field(max_length=10)

    # Optional OHLCV
    open_amount: Optional[Decimal] = Field(default=None, decimal_places=2)
    open_currency: Optional[str] = Field(default=None, max_length=3)
    high_amount: Optional[Decimal] = Field(default=None, decimal_places=2)
    high_currency: Optional[str] = Field(default=None, max_length=3)
    low_amount: Optional[Decimal] = Field(default=None, decimal_places=2)
    low_currency: Optional[str] = Field(default=None, max_length=3)
    close_amount: Optional[Decimal] = Field(default=None, decimal_places=2)
    close_currency: Optional[str] = Field(default=None, max_length=3)
    volume: Optional[int] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)

    def to_price_point(self) -> PricePoint:
        """Convert to PricePoint DTO."""
        # Implementation to convert model to PricePoint

    @classmethod
    def from_price_point(cls, price: PricePoint) -> "PriceHistoryModel":
        """Create from PricePoint DTO."""
        # Implementation to convert PricePoint to model
```

**File**: `backend/src/zebu/adapters/outbound/models/ticker_watchlist.py`

```python
from datetime import datetime
from sqlmodel import Field, SQLModel
from typing import Optional

class TickerWatchlistModel(SQLModel, table=True):
    """SQLModel for ticker_watchlist table."""

    __tablename__ = "ticker_watchlist"

    id: Optional[int] = Field(default=None, primary_key=True)
    ticker: str = Field(unique=True, max_length=10)
    priority: int = Field(default=100)
    last_refresh_at: Optional[datetime] = None
    next_refresh_at: Optional[datetime] = None
    refresh_interval_seconds: int = Field(default=300)  # 5 minutes
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

### 3. PriceRepository Implementation

**File**: `backend/src/zebu/adapters/outbound/repositories/price_repository.py`

**Key Methods** (from architecture):

```python
class PriceRepository:
    """PostgreSQL implementation of price storage."""

    async def upsert_price(self, price: PricePoint) -> None:
        """Insert or update price (ON CONFLICT DO UPDATE)."""

    async def get_latest_price(
        self,
        ticker: Ticker,
        max_age: timedelta | None = None
    ) -> PricePoint | None:
        """Get most recent price for ticker."""

    async def get_price_at(
        self,
        ticker: Ticker,
        timestamp: datetime
    ) -> PricePoint | None:
        """Get price closest to timestamp."""

    async def get_price_history(
        self,
        ticker: Ticker,
        start: datetime,
        end: datetime,
        interval: str = "1day"
    ) -> list[PricePoint]:
        """Get price history over time range."""

    async def get_all_tickers(self) -> list[Ticker]:
        """Get list of tickers we have data for."""
```

**Performance Considerations**:
- Use indexes for ticker + timestamp queries
- Limit results to prevent large scans
- Use EXPLAIN ANALYZE in tests to verify index usage
- Consider partitioning for very large datasets (future)

### 4. WatchlistManager Implementation

**File**: `backend/src/zebu/adapters/outbound/repositories/watchlist_manager.py`

**Key Methods**:

```python
class WatchlistManager:
    """Manages ticker watchlist for automated price refresh."""

    async def add_ticker(
        self,
        ticker: Ticker,
        priority: int = 100,
        refresh_interval: timedelta = timedelta(minutes=5)
    ) -> None:
        """Add ticker to watchlist."""

    async def remove_ticker(self, ticker: Ticker) -> None:
        """Remove ticker from watchlist."""

    async def get_stale_tickers(
        self,
        limit: int = 10
    ) -> list[Ticker]:
        """Get tickers that need refresh (past next_refresh_at)."""

    async def update_refresh_metadata(
        self,
        ticker: Ticker,
        last_refresh: datetime,
        next_refresh: datetime
    ) -> None:
        """Update refresh timestamps after fetching price."""

    async def get_all_active_tickers(self) -> list[Ticker]:
        """Get all active watched tickers."""
```

### 5. Integrate with AlphaVantageAdapter

**Modify**: `backend/src/zebu/adapters/outbound/market_data/alpha_vantage_adapter.py`

**Uncomment/Implement Tier 2 Logic**:

```python
async def get_current_price(self, ticker: Ticker) -> PricePoint:
    # Tier 1: Redis cache (already implemented)
    cached = await self.price_cache.get(ticker)
    if cached and not cached.is_stale(max_age=timedelta(hours=1)):
        return cached.with_source("cache")

    # Tier 2: PostgreSQL (IMPLEMENT THIS)
    if self.price_repository:
        db_price = await self.price_repository.get_latest_price(
            ticker,
            max_age=timedelta(hours=4)
        )
        if db_price and not db_price.is_stale(max_age=timedelta(hours=4)):
            await self.price_cache.set(db_price)  # Warm cache
            return db_price.with_source("database")

    # Tier 3: API (already implemented)
    # ... existing API logic ...

    # Store in database after API fetch
    if self.price_repository:
        await self.price_repository.upsert_price(price)
```

### 6. Testing Strategy

**Integration Tests** (`backend/tests/integration/repositories/`):

**test_price_repository.py**:
```python
@pytest.mark.asyncio
async def test_upsert_price():
    """Test inserting and updating prices."""

@pytest.mark.asyncio
async def test_get_latest_price():
    """Test retrieving most recent price."""

@pytest.mark.asyncio
async def test_get_price_at():
    """Test time-travel price queries."""

@pytest.mark.asyncio
async def test_get_price_history():
    """Test range queries."""

@pytest.mark.asyncio
async def test_performance_indexes():
    """Verify indexes are used (EXPLAIN ANALYZE)."""
```

**test_watchlist_manager.py**:
```python
@pytest.mark.asyncio
async def test_add_remove_ticker():
    """Test adding and removing from watchlist."""

@pytest.mark.asyncio
async def test_get_stale_tickers():
    """Test finding tickers needing refresh."""

@pytest.mark.asyncio
async def test_priority_ordering():
    """Test that higher priority tickers refreshed first."""
```

**Update Integration Test for AlphaVantageAdapter**:
```python
@pytest.mark.asyncio
async def test_tier2_fallback():
    """Test Redis miss → PostgreSQL hit → return."""

@pytest.mark.asyncio
async def test_tier3_stores_in_db():
    """Test API fetch stores in PostgreSQL."""
```

## Configuration Updates

### `backend/settings.toml`

```toml
[database]
url = "postgresql+asyncpg://user:pass@localhost:5432/zebu"

[market_data.cache]
tier1_ttl = 3600  # Redis: 1 hour
tier2_max_age = 14400  # PostgreSQL: 4 hours
```

## Migration Workflow

```bash
# Generate migrations
cd backend
alembic revision --autogenerate -m "Add price_history table"
alembic revision --autogenerate -m "Add ticker_watchlist table"

# Review migrations (ensure correct schema)

# Apply migrations
alembic upgrade head

# Verify schema
psql -d zebu -c "\d price_history"
psql -d zebu -c "\d ticker_watchlist"
```

## Files to Create/Modify

### New Files

**Migrations**:
- `backend/migrations/versions/002_*.py` (price_history)
- `backend/migrations/versions/003_*.py` (ticker_watchlist)

**Models**:
- `backend/src/zebu/adapters/outbound/models/price_history.py` (~120 lines)
- `backend/src/zebu/adapters/outbound/models/ticker_watchlist.py` (~50 lines)

**Repositories**:
- `backend/src/zebu/adapters/outbound/repositories/price_repository.py` (~280 lines)
- `backend/src/zebu/adapters/outbound/repositories/watchlist_manager.py` (~180 lines)

**Tests**:
- `backend/tests/integration/repositories/test_price_repository.py` (~350 lines)
- `backend/tests/integration/repositories/test_watchlist_manager.py` (~200 lines)

### Modified Files

**Adapter**:
- `backend/src/zebu/adapters/outbound/market_data/alpha_vantage_adapter.py`
  - Uncomment PostgreSQL integration
  - Add database storage after API calls
  - Update Tier 2 fallback logic

**Tests**:
- `backend/tests/integration/adapters/test_alpha_vantage_adapter.py`
  - Add Tier 2 caching tests
  - Test database storage

**Configuration**:
- `backend/settings.toml` - Add tier2_max_age

## Testing Checklist

- [ ] Migrations run successfully (up and down)
- [ ] Models serialize/deserialize PricePoint correctly
- [ ] Upsert handles duplicates correctly
- [ ] Latest price queries use index (verify with EXPLAIN)
- [ ] Time-travel queries work correctly
- [ ] Range queries handle edge cases (no data, partial data)
- [ ] Watchlist pre-populated with common stocks
- [ ] Stale ticker detection works
- [ ] AlphaVantageAdapter falls back to database
- [ ] AlphaVantageAdapter stores API results in database
- [ ] Type checking passes (pyright --strict)
- [ ] Linting passes (ruff check, ruff format)
- [ ] All tests pass (~334 existing + ~40 new = ~374 total)

## Definition of Done

- [ ] All success criteria met
- [ ] All tests passing
- [ ] Type checking passes
- [ ] Linting passes
- [ ] Migrations verified in development database
- [ ] PR created with clear description
- [ ] Progress document created
- [ ] Ready for architect review

## Next Steps

After this task:
- **Task 024**: Portfolio Use Cases with Real Prices (integrate market data into portfolio queries)
- **Phase 2b**: Historical data support (get_price_at, get_price_history)
- **Phase 3**: Backtesting with historical data

This task is **critical infrastructure** - it completes the tiered caching architecture and enables persistent price storage for all future features.
