# Phase 2 Market Data Integration - Database Schema

**Created**: 2025-12-28
**Status**: Approved

## Overview

This document specifies the database schema for storing historical price data. The schema is designed to:
- Support fast time-range queries (for charts and backtesting)
- Store full OHLCV data (Open, High, Low, Close, Volume)
- Handle multiple price intervals (daily, hourly, minute)
- Scale to millions of price records
- Support Phase 3 backtesting requirements

## PriceHistory Table

### Purpose
Store all historical and current price data for stocks. This table is append-mostly (updates only for corrections, never deletes).

### Table Specification

| Column | Type | Nullable | Description | Constraints |
|--------|------|----------|-------------|-------------|
| **id** | UUID | NO | Primary key | Unique, auto-generated |
| **ticker** | VARCHAR(5) | NO | Stock ticker symbol | Uppercase, 1-5 chars |
| **price** | DECIMAL(15,2) | NO | Price at timestamp | Positive |
| **currency** | VARCHAR(3) | NO | ISO 4217 currency code | Default: 'USD' |
| **timestamp** | TIMESTAMP WITH TIME ZONE | NO | When price was observed | UTC timezone |
| **source** | VARCHAR(20) | NO | Data source | One of: 'alpha_vantage', 'finnhub', 'manual' |
| **interval** | VARCHAR(10) | NO | Price interval type | One of: 'real-time', '1min', '5min', '15min', '30min', '1hour', '1day' |
| **open** | DECIMAL(15,2) | YES | Opening price for interval | Positive if present |
| **high** | DECIMAL(15,2) | YES | Highest price in interval | Positive if present |
| **low** | DECIMAL(15,2) | YES | Lowest price in interval | Positive if present |
| **close** | DECIMAL(15,2) | YES | Closing price for interval | Positive if present |
| **volume** | BIGINT | YES | Trading volume | Non-negative if present |
| **created_at** | TIMESTAMP WITH TIME ZONE | NO | When record was created | Auto-set on insert |
| **updated_at** | TIMESTAMP WITH TIME ZONE | NO | When record was last updated | Auto-set on update |

### Constraints

#### Primary Key
- `id` (UUID)

#### Unique Constraint
- `(ticker, timestamp, interval)` - One price per ticker per timestamp per interval

**Rationale**: Prevents duplicate entries. If Alpha Vantage returns same data twice, upsert updates existing record.

#### Check Constraints

| Constraint Name | Expression | Purpose |
|----------------|------------|---------|
| `price_positive` | `price > 0` | Prices must be positive |
| `ohlc_positive` | `open IS NULL OR open > 0` (and similar for h/l/c) | OHLC values positive if present |
| `volume_nonnegative` | `volume IS NULL OR volume >= 0` | Volume can't be negative |
| `ohlc_valid_range` | `low IS NULL OR high IS NULL OR low <= high` | Low can't exceed high |
| `valid_interval` | `interval IN ('real-time', '1min', '5min', '15min', '30min', '1hour', '1day')` | Only allowed intervals |
| `valid_source` | `source IN ('alpha_vantage', 'finnhub', 'manual')` | Only allowed sources |
| `valid_currency` | `currency IN ('USD', 'EUR', 'GBP', 'CAD', 'JPY', 'AUD')` | Only supported currencies |

#### Foreign Keys
None (prices are independent data, not related to portfolios)

### Indexes

#### Primary Indexes

| Index Name | Columns | Type | Purpose | Estimated Rows |
|------------|---------|------|---------|----------------|
| `pk_price_history` | `id` | PRIMARY KEY | Fast lookup by ID | All (millions) |
| `uk_price_history` | `ticker, timestamp, interval` | UNIQUE | Enforce uniqueness | All (millions) |

#### Query Optimization Indexes

| Index Name | Columns | Type | Purpose | Use Case |
|------------|---------|------|---------|----------|
| `idx_ticker_timestamp` | `ticker, timestamp` | BTREE | Time-range queries | `get_price_history(AAPL, 2024-01-01, 2024-12-31)` |
| `idx_ticker_interval_timestamp` | `ticker, interval, timestamp` | BTREE | Interval-specific queries | `get_price_history(AAPL, interval='1day')` |
| `idx_source_created` | `source, created_at` | BTREE | Track data source health | Admin queries |
| `idx_timestamp_partial` | `timestamp WHERE interval = '1day'` | PARTIAL BTREE | Daily price queries | Most common query pattern |

**Index Strategy**:
- Composite indexes for multi-column filters
- Partial index for daily prices (most common interval)
- Covering indexes (include columns to avoid table lookup)

### Example Queries with Index Usage

#### Query 1: Get Latest Price
```sql
SELECT * FROM price_history
WHERE ticker = 'AAPL'
  AND interval = 'real-time'
ORDER BY timestamp DESC
LIMIT 1;

-- Uses: idx_ticker_interval_timestamp (seeks to end, returns 1 row)
-- Performance: <10ms
```

#### Query 2: Get Price at Specific Time
```sql
SELECT * FROM price_history
WHERE ticker = 'AAPL'
  AND interval = '1day'
  AND timestamp <= '2024-06-15 16:00:00+00'
ORDER BY timestamp DESC
LIMIT 1;

-- Uses: idx_ticker_interval_timestamp (binary search)
-- Performance: <50ms
```

#### Query 3: Get Price History (1 Year Daily)
```sql
SELECT * FROM price_history
WHERE ticker = 'AAPL'
  AND interval = '1day'
  AND timestamp BETWEEN '2024-01-01' AND '2024-12-31'
ORDER BY timestamp ASC;

-- Uses: idx_ticker_interval_timestamp (range scan)
-- Returns: ~252 trading days
-- Performance: <100ms
```

#### Query 4: Get All Tickers with Data
```sql
SELECT DISTINCT ticker FROM price_history
ORDER BY ticker;

-- Uses: uk_price_history (index scan on ticker column)
-- Performance: <500ms (even with millions of rows)
```

### Partitioning Strategy (Future)

For very large datasets (>100M rows), consider **time-based partitioning**:

```sql
-- Partition by month (example for Phase 4+)
CREATE TABLE price_history (
    -- ... columns ...
) PARTITION BY RANGE (timestamp);

CREATE TABLE price_history_2024_01 PARTITION OF price_history
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

CREATE TABLE price_history_2024_02 PARTITION OF price_history
    FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');
-- ... etc
```

**When to Partition**:
- Phase 2/3: NOT needed (tables <10M rows)
- Phase 4+: Consider if >100M rows
- Benefit: Faster queries (only scan relevant partitions)
- Cost: More complex schema management

### Storage Estimates

**Assumptions**:
- 500 tickers tracked
- 1 year of daily data: 252 trading days per ticker
- Total rows: 500 × 252 = 126,000 rows/year

**Row Size**:
- Fixed columns: ~100 bytes
- OHLCV data: ~40 bytes
- Indexes: ~80 bytes
- **Total: ~220 bytes per row**

**Storage**:
- 1 year: 126K rows × 220 bytes = ~27 MB
- 5 years: ~135 MB
- 10 years: ~270 MB

**With Intraday Data** (hourly):
- 500 tickers × 252 days × 6.5 hours = 819,000 rows/year
- 1 year: ~180 MB
- 5 years: ~900 MB

**Conclusion**: Storage not a concern for Phase 2-4 (GB-scale, not TB-scale)

## TickerWatchlist Table

### Purpose
Track which tickers to refresh in background job. Separate from price_history to manage refresh priority independently.

### Table Specification

| Column | Type | Nullable | Description | Constraints |
|--------|------|----------|-------------|-------------|
| **ticker** | VARCHAR(5) | NO | Stock ticker symbol | PRIMARY KEY, uppercase |
| **source** | VARCHAR(20) | NO | How ticker was added | One of: 'portfolio', 'common', 'recent', 'manual' |
| **priority** | INTEGER | NO | Refresh priority (1=highest) | Range: 1-10 |
| **added_at** | TIMESTAMP WITH TIME ZONE | NO | When added to watchlist | Auto-set on insert |
| **last_refreshed_at** | TIMESTAMP WITH TIME ZONE | YES | Last successful refresh | NULL if never refreshed |
| **refresh_count** | INTEGER | NO | Total refresh attempts | Default: 0 |
| **error_count** | INTEGER | NO | Failed refresh attempts | Default: 0 |
| **last_error** | TEXT | YES | Last error message | NULL if no errors |

### Constraints

#### Primary Key
- `ticker`

#### Check Constraints

| Constraint | Expression | Purpose |
|------------|------------|---------|
| `valid_source` | `source IN ('portfolio', 'common', 'recent', 'manual')` | Only allowed sources |
| `valid_priority` | `priority BETWEEN 1 AND 10` | Priority range |
| `counts_nonnegative` | `refresh_count >= 0 AND error_count >= 0` | Counts can't be negative |

#### Indexes

| Index | Columns | Purpose |
|-------|---------|---------|
| `pk_ticker_watchlist` | `ticker` | PRIMARY KEY |
| `idx_watchlist_priority_refresh` | `priority, last_refreshed_at` | Select tickers for refresh |

### Example Queries

#### Query 1: Get Stale Tickers for Refresh
```sql
SELECT ticker FROM ticker_watchlist
WHERE last_refreshed_at IS NULL
   OR last_refreshed_at < NOW() - INTERVAL '24 hours'
ORDER BY priority ASC, last_refreshed_at ASC NULLS FIRST
LIMIT 100;

-- Returns: Up to 100 tickers needing refresh, prioritized
```

#### Query 2: Add Ticker to Watchlist
```sql
INSERT INTO ticker_watchlist (ticker, source, priority, added_at)
VALUES ('AAPL', 'portfolio', 1, NOW())
ON CONFLICT (ticker) DO UPDATE
SET priority = LEAST(ticker_watchlist.priority, EXCLUDED.priority);

-- Upsert: Add if new, upgrade priority if exists
```

#### Query 3: Record Successful Refresh
```sql
UPDATE ticker_watchlist
SET last_refreshed_at = NOW(),
    refresh_count = refresh_count + 1,
    last_error = NULL
WHERE ticker = 'AAPL';
```

#### Query 4: Record Failed Refresh
```sql
UPDATE ticker_watchlist
SET error_count = error_count + 1,
    last_error = 'Rate limit exceeded'
WHERE ticker = 'AAPL';
```

## Database Migrations

### Migration Strategy

Use **Alembic** (SQLAlchemy migration tool) for schema changes.

**Migration Files**:
```
backend/migrations/
├── env.py                          # Alembic config
├── script.py.mako                  # Migration template
├── versions/
│   ├── 001_phase1_initial.py       # Existing (Portfolio, Transaction)
│   ├── 002_phase2_price_history.py # New (This migration)
│   └── 003_phase2_ticker_watchlist.py
```

### Migration 002: Add PriceHistory Table

**File**: `backend/migrations/versions/002_phase2_price_history.py`

**Upgrade Steps**:
1. Create `price_history` table with all columns
2. Create unique constraint `(ticker, timestamp, interval)`
3. Create indexes (primary, unique, query optimization)
4. Create check constraints (positive prices, valid intervals)
5. Add comments to table and columns (documentation)

**Downgrade Steps**:
1. Drop indexes
2. Drop table (CASCADE to remove all data)

**Data Migration**: None (new table, no existing data)

### Migration 003: Add TickerWatchlist Table

**File**: `backend/migrations/versions/003_phase2_ticker_watchlist.py`

**Upgrade Steps**:
1. Create `ticker_watchlist` table
2. Create indexes
3. Pre-populate with common stocks (AAPL, MSFT, etc.)

**Downgrade Steps**:
1. Drop table

**Data Migration**: Insert common stock tickers

**Common Stocks to Pre-populate**:
```sql
INSERT INTO ticker_watchlist (ticker, source, priority, added_at) VALUES
    ('AAPL', 'common', 2, NOW()),
    ('MSFT', 'common', 2, NOW()),
    ('GOOGL', 'common', 2, NOW()),
    ('AMZN', 'common', 2, NOW()),
    ('TSLA', 'common', 2, NOW()),
    ('META', 'common', 2, NOW()),
    ('NVDA', 'common', 2, NOW()),
    ('SPY', 'common', 2, NOW()),   -- S&P 500 ETF
    ('QQQ', 'common', 2, NOW());   -- NASDAQ ETF
```

## SQLModel Models

### PriceHistoryModel

**File**: `backend/src/papertrade/adapters/outbound/models/price_history.py`

**Purpose**: SQLModel ORM representation of price_history table

**Key Features**:
- Maps to `price_history` table
- Includes validators for constraints
- Provides helper methods (to_price_point, from_price_point)
- Supports async queries

**Relationship to Domain**:
- NOT a domain entity (prices are external data)
- Converts to/from `PricePoint` value object
- Lives in adapters layer (persistence concern)

### TickerWatchlistModel

**File**: `backend/src/papertrade/adapters/outbound/models/ticker_watchlist.py`

**Purpose**: SQLModel ORM representation of ticker_watchlist table

**Key Features**:
- Maps to `ticker_watchlist` table
- Includes priority management methods
- Tracks refresh metadata

## Performance Considerations

### Query Performance Targets

| Query Type | Target | Acceptable | Unacceptable |
|------------|--------|------------|--------------|
| Get latest price | <10ms | <50ms | >100ms |
| Get price at time | <50ms | <100ms | >200ms |
| Get 1 year daily history | <100ms | <500ms | >1s |
| Get all tickers | <200ms | <500ms | >1s |
| Insert single price | <10ms | <50ms | >100ms |
| Batch insert (100 prices) | <100ms | <500ms | >1s |

### Index Maintenance

**PostgreSQL Auto-Vacuum**:
- Runs automatically to reclaim space
- Updates index statistics for query planner
- No manual intervention needed

**Index Bloat Monitoring**:
```sql
-- Check index size
SELECT schemaname, tablename, indexname,
       pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY pg_relation_size(indexrelid) DESC;
```

**Reindex Strategy** (if needed):
```sql
-- Rebuild index to reclaim space (rarely needed)
REINDEX INDEX idx_ticker_timestamp;
```

### Connection Pooling

**SQLAlchemy Pool Settings** (in config):
```toml
[database]
pool_size = 10          # Concurrent connections
max_overflow = 20       # Extra connections under load
pool_timeout = 30       # Wait for connection (seconds)
pool_recycle = 3600     # Recycle connections hourly
```

## Data Retention Policy

### Phase 2-3
**Policy**: Retain all historical data indefinitely
- **Rationale**: Required for backtesting, storage is cheap
- **Cost**: ~1 GB per year (acceptable)

### Phase 4+ (Future)
**Policy**: Retain based on age and interval

| Interval | Retention | Rationale |
|----------|-----------|-----------|
| 1min | 30 days | High volume, low long-term value |
| 5min | 90 days | Medium volume |
| 1hour | 1 year | Useful for intraday backtesting |
| 1day | Indefinite | Low volume, high value |

**Cleanup Job** (Future):
```sql
-- Delete old minute-level data (after 30 days)
DELETE FROM price_history
WHERE interval = '1min'
  AND timestamp < NOW() - INTERVAL '30 days';
```

## Disaster Recovery

### Backup Strategy

**PostgreSQL Backups**:
- **Frequency**: Daily (automated)
- **Retention**: 30 days
- **Method**: AWS RDS automated snapshots (production)

**Point-in-Time Recovery**:
- WAL (Write-Ahead Logging) enabled
- Can restore to any point within last 7 days

### Data Loss Scenarios

| Scenario | Impact | Recovery |
|----------|--------|----------|
| **Single price corrupted** | Minimal (one data point) | Re-fetch from API or ignore |
| **Day of prices lost** | Low (can re-fetch) | Background job backfills |
| **All price history lost** | High (Phase 3 broken) | Restore from backup, backfill gaps |
| **Database totally lost** | Critical | Restore from backup, full re-fetch (2-3 days) |

### Re-fetch Strategy

If historical data is lost:
1. Restore latest backup (gets most data)
2. Identify gaps (query for missing days)
3. Backfill gaps from Alpha Vantage (respecting rate limits)
4. For very old data: Use TIME_SERIES_DAILY (bulk download)

## Testing Data

### Test Fixtures

**Fixture Files**: `backend/tests/fixtures/price_history_*.json`

**Sample Data**:
- 5 tickers (AAPL, MSFT, GOOGL, TSLA, SPY)
- 1 year of daily prices (252 days each)
- Realistic OHLCV data
- Various scenarios (price drops, splits, etc.)

**Loading Fixtures**:
```python
# pytest fixture
@pytest.fixture
async def price_history_db(db_session):
    # Load from JSON fixture
    fixtures = load_json("price_history_2024.json")
    for fixture in fixtures:
        price = PriceHistoryModel(**fixture)
        db_session.add(price)
    await db_session.commit()
    return db_session
```

### Test Database

**SQLite for Tests** (fast, in-memory):
```python
# test config
DATABASE_URL = "sqlite+aiosqlite:///:memory:"
```

**Benefits**:
- Fast (in-memory)
- Isolated (each test gets fresh DB)
- No cleanup needed
- Same schema as PostgreSQL (SQLModel compatible)

## Monitoring & Observability

### Metrics to Track

| Metric | Query | Alert Threshold |
|--------|-------|-----------------|
| Total price records | `SELECT COUNT(*) FROM price_history` | - |
| Prices per ticker | `SELECT ticker, COUNT(*) FROM price_history GROUP BY ticker` | <100 per ticker |
| Data gaps | `SELECT ticker, MAX(timestamp) FROM price_history GROUP BY ticker` | >7 days stale |
| Table size | `SELECT pg_size_pretty(pg_total_relation_size('price_history'))` | >10 GB |
| Index efficiency | `SELECT * FROM pg_stat_user_indexes WHERE idx_scan < 100` | Unused indexes |

### Logs to Capture

- Price insert/update (INFO level)
- Missing data detected (WARNING level)
- Constraint violation (ERROR level)
- Index slow queries (WARNING level if >1s)

## References

- [PostgreSQL Indexing Strategies](https://www.postgresql.org/docs/current/indexes.html)
- [SQLModel Documentation](https://sqlmodel.tiangolo.com/)
- [Alembic Migrations](https://alembic.sqlalchemy.org/)
- [Time-Series Data in PostgreSQL](https://www.timescale.com/blog/time-series-data-postgresql/)
