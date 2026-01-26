# Phase 2 Market Data Integration - Interface Specifications

**Created**: 2025-12-28
**Status**: Approved

## Overview

This document specifies the interfaces and data structures for Phase 2 Market Data Integration using **structured specifications** (NOT code examples). Implementation agents will translate these specifications into actual code.

## PricePoint Value Object

### Purpose
Represents a single price observation for a ticker at a specific point in time.

### Classification
**Value Object** (immutable, equality based on all fields)

### Properties

| Property | Type | Description | Constraints |
|----------|------|-------------|-------------|
| ticker | Ticker | Stock ticker symbol | Must be valid Ticker value object |
| price | Money | Price at observation time | Must be positive Money value |
| timestamp | datetime | When price was observed | Must be in UTC timezone |
| source | String | Data source identifier | One of: "alpha_vantage", "cache", "database" |
| interval | String | Price interval type | One of: "real-time", "1day", "1hour", "5min", "1min" |

### Optional Properties (OHLCV Data)

| Property | Type | Description | Constraints |
|----------|------|-------------|-------------|
| open | Money or None | Opening price for interval | Must match price currency if present |
| high | Money or None | Highest price in interval | Must match price currency if present |
| low | Money or None | Lowest price in interval | Must match price currency if present |
| close | Money or None | Closing price for interval | Must match price currency if present |
| volume | Integer or None | Trading volume | Must be non-negative if present |

### Invariants
- All Money values (price, open, high, low, close) must have same currency
- If OHLCV data present: low ≤ open, close ≤ high
- timestamp must be in UTC (no naive datetimes)
- source must be one of the allowed values

### Equality Semantics
Two PricePoint objects are equal if:
- ticker.symbol matches
- price matches
- timestamp matches (to the second)
- source matches
- interval matches

### String Representation
Format: `"{ticker} @ {price} as of {timestamp} (source: {source})"`
Example: `"AAPL @ $150.25 as of 2025-12-28 14:30:00 UTC (source: alpha_vantage)"`

### Methods/Operations

| Operation | Parameters | Returns | Description |
|-----------|-----------|---------|-------------|
| is_stale | max_age: timedelta | Boolean | Returns True if timestamp is older than max_age from now |
| with_source | new_source: String | PricePoint | Returns new PricePoint with different source (for cache hits) |

---

## MarketDataPort Interface

### Purpose
Defines the contract for fetching market data. This is a **port** (Protocol interface) in the Application Layer.

### Layer
**Application Layer** - Port interface (adapters implement it)

### Design Philosophy
- **Read-only**: Market data is external; we don't change it
- **Async**: Network calls may be slow
- **Time-aware**: Support historical queries for Phase 3
- **Source-transparent**: Caller knows if data is cached/stale
- **Extensible**: Easy to add new methods in future phases

### Methods

#### Method: get_current_price

| Aspect | Specification |
|--------|---------------|
| **Purpose** | Get the most recent available price for a ticker |
| **Parameters** | ticker: Ticker |
| **Returns** | PricePoint with latest available price |
| **Async** | Yes (may involve network I/O) |
| **Errors** | TickerNotFoundError: Ticker doesn't exist in data source<br>MarketDataUnavailableError: Cannot fetch price (API down, rate limited, network error) |
| **Performance Target** | <100ms (cache hit), <2s (API call) |
| **Caching Behavior** | MAY return cached data if fresh enough (implementation decides) |
| **Staleness** | Result includes timestamp; caller can check freshness |

**Semantics**:
- Returns most recent price available (may be delayed vs. real-time)
- If market closed, returns last closing price
- Source field indicates if cached or fresh from API
- Must not fail due to rate limiting (should return cached data)

#### Method: get_price_at

| Aspect | Specification |
|--------|---------------|
| **Purpose** | Get the price for a ticker at a specific point in time (for backtesting) |
| **Parameters** | ticker: Ticker<br>timestamp: datetime (UTC) |
| **Returns** | PricePoint with price closest to requested timestamp |
| **Async** | Yes (may query database or API) |
| **Errors** | TickerNotFoundError: Ticker doesn't exist<br>MarketDataUnavailableError: No data available for that time period |
| **Performance Target** | <500ms (database query) |
| **Precision** | Returns closest available price within reasonable window |
| **Critical For** | Phase 3 "Time Machine" backtesting |

**Semantics**:
- If exact timestamp not available, return closest price within ±1 hour (configurable)
- If timestamp in future, raise MarketDataUnavailableError
- If timestamp before available data, raise MarketDataUnavailableError
- Returned PricePoint.timestamp indicates actual observation time
- Source typically "database" for historical queries

#### Method: get_price_history

| Aspect | Specification |
|--------|---------------|
| **Purpose** | Get price history over a time range (for charts and analysis) |
| **Parameters** | ticker: Ticker<br>start: datetime (UTC)<br>end: datetime (UTC)<br>interval: String (default: "1day") |
| **Returns** | List of PricePoint objects covering time range |
| **Async** | Yes (may query database or API) |
| **Errors** | TickerNotFoundError: Ticker doesn't exist<br>MarketDataUnavailableError: Insufficient data for range<br>ValueError: Invalid interval or end before start |
| **Performance Target** | <1s for 1 year of daily data |
| **Ordering** | Results ordered chronologically (oldest first) |

**Semantics**:
- interval options: "1min", "5min", "15min", "30min", "1hour", "1day"
- Returns empty list if no data in range (not an error)
- May return partial data if some periods missing
- Each PricePoint includes OHLCV data when available
- end timestamp is inclusive (includes data up to and including end)

**Interval Semantics**:
- "1day": One price per day (typically closing price)
- "1hour": One price per hour during market hours
- "1min": One price per minute (high frequency, use with caution)

#### Method: get_supported_tickers

| Aspect | Specification |
|--------|---------------|
| **Purpose** | Get list of tickers we have data for (for search/autocomplete) |
| **Parameters** | None |
| **Returns** | List of Ticker objects |
| **Async** | Yes (may query database) |
| **Errors** | MarketDataUnavailableError: Cannot access ticker list |
| **Performance Target** | <200ms |
| **Caching** | SHOULD be cached aggressively (list changes infrequently) |

**Semantics**:
- Returns all tickers for which we have ANY price data
- Used for frontend search/autocomplete
- May include tickers not currently tracked
- List may grow over time as users query new tickers

---

## Exception Hierarchy

### Base: MarketDataError

| Aspect | Specification |
|--------|---------------|
| **Base Class** | Exception (Python standard) |
| **Purpose** | Base class for all market data related errors |
| **Attributes** | message: String - Human-readable error description |
| **When Raised** | Never directly; use specific subclasses |

### Subclass: TickerNotFoundError

| Aspect | Specification |
|--------|---------------|
| **Base Class** | MarketDataError |
| **Purpose** | Ticker symbol doesn't exist in data source |
| **Additional Attributes** | ticker: Ticker - The invalid ticker |
| **When Raised** | API returns "invalid symbol" or ticker not in database |
| **HTTP Status** | 404 Not Found (when converted to API error) |

**Example Message**: `"Ticker not found: XYZ. Please verify the symbol is correct."`

### Subclass: MarketDataUnavailableError

| Aspect | Specification |
|--------|---------------|
| **Base Class** | MarketDataError |
| **Purpose** | Cannot fetch market data for temporary reasons |
| **Additional Attributes** | reason: String - Specific cause (optional)<br>retry_after: datetime - When to retry (optional) |
| **When Raised** | API down, rate limited, network error, cache miss with no fallback |
| **HTTP Status** | 503 Service Unavailable (when converted to API error) |

**Example Messages**:
- `"Market data unavailable: API rate limit exceeded. Retry after 2025-12-28 15:00:00 UTC"`
- `"Market data unavailable: Alpha Vantage API is not responding"`
- `"Market data unavailable: No cached data for TSLA and API unavailable"`

### Subclass: InvalidPriceDataError

| Aspect | Specification |
|--------|---------------|
| **Base Class** | MarketDataError |
| **Purpose** | Price data received but invalid/corrupted |
| **Additional Attributes** | ticker: Ticker - Which ticker had invalid data<br>details: String - What was invalid |
| **When Raised** | API returns malformed data, negative prices, impossible OHLCV values |
| **HTTP Status** | 502 Bad Gateway (data source error) |

**Example Message**: `"Invalid price data for AAPL: price must be positive, got -150.00"`

---

## RateLimiter Interface

### Purpose
Manages API rate limiting using token bucket algorithm.

### Layer
**Infrastructure Layer** - Used by Alpha Vantage adapter

### Properties

| Property | Type | Description |
|----------|------|-------------|
| tokens_per_minute | Integer | How many API calls allowed per minute |
| tokens_per_day | Integer | How many API calls allowed per day |
| current_minute_tokens | Integer | Tokens remaining this minute |
| current_day_tokens | Integer | Tokens remaining today |
| minute_reset_at | datetime | When minute tokens refill |
| day_reset_at | datetime | When day tokens refill |

### Methods

| Method | Parameters | Returns | Description |
|--------|-----------|---------|-------------|
| can_make_request | None | Boolean | Returns True if a token is available |
| consume_token | None | None | Consumes one token (call after successful request) |
| wait_time | None | timedelta | How long to wait for next available token |
| reset | None | None | Reset all tokens (for testing) |

### Configuration

Default configuration (Alpha Vantage free tier):
- tokens_per_minute: 5
- tokens_per_day: 500

Must be configurable for premium tier upgrades:
- tokens_per_minute: 75 (premium example)
- tokens_per_day: 100,000 (premium example)

### Thread Safety
Must be thread-safe for concurrent requests.

### Persistence
Token counts SHOULD persist across restarts (use Redis or database) to prevent quota exhaustion.

---

## PriceCache Interface

### Purpose
Manages hot cache of recent prices using Redis.

### Layer
**Infrastructure Layer** - Used by Alpha Vantage adapter

### Methods

| Method | Parameters | Returns | Description |
|--------|-----------|---------|-------------|
| get | ticker: Ticker | PricePoint or None | Retrieve cached price if exists and fresh |
| set | ticker: Ticker, price: PricePoint, ttl: timedelta | None | Store price in cache with TTL |
| delete | ticker: Ticker | None | Remove price from cache |
| exists | ticker: Ticker | Boolean | Check if ticker has cached price |
| get_ttl | ticker: Ticker | timedelta or None | Get remaining TTL for cached price |

### Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| default_ttl | 3600 seconds (1 hour) | How long to cache prices |
| redis_url | "redis://localhost:6379" | Redis connection string |
| key_prefix | "papertrade:price:" | Prefix for all cache keys |

### Key Format
Keys: `papertrade:price:{ticker.symbol}`
Example: `papertrade:price:AAPL`

### Serialization
PricePoint objects must be serialized to JSON for Redis storage.

### Cache Eviction
- TTL-based eviction (automatic by Redis)
- Manual eviction via `delete()` method
- LRU eviction if Redis memory limit reached

---

## PriceRepository Interface

### Purpose
Manages persistence of historical price data in PostgreSQL.

### Layer
**Adapters Layer** - Implements outbound port

### Methods

| Method | Parameters | Returns | Description |
|--------|-----------|---------|-------------|
| save | price: PricePoint | None | Store price (upsert by ticker+timestamp+interval) |
| get_latest | ticker: Ticker | PricePoint or None | Get most recent price for ticker |
| get_at | ticker: Ticker, timestamp: datetime | PricePoint or None | Get price closest to timestamp |
| get_history | ticker: Ticker, start: datetime, end: datetime, interval: String | List[PricePoint] | Get price history in range |
| count | ticker: Ticker | Integer | Count total price records for ticker |
| get_all_tickers | None | List[Ticker] | Get all tickers with price data |

### Constraints
- Unique constraint: (ticker, timestamp, interval)
- If duplicate save, update existing record (upsert behavior)
- Efficient indexing for time-range queries

### Performance Requirements
- get_latest: <50ms
- get_at: <100ms
- get_history (1 year daily): <500ms
- save (single): <10ms
- save (batch of 100): <100ms

---

## AlphaVantageAdapter Specification

### Purpose
Implements MarketDataPort using Alpha Vantage API as data source.

### Layer
**Adapters Layer** - Outbound adapter

### Dependencies

| Dependency | Type | Purpose |
|------------|------|---------|
| api_key | String | Alpha Vantage API key (from config) |
| rate_limiter | RateLimiter | Prevent quota exhaustion |
| cache | PriceCache | Redis cache for hot data |
| repository | PriceRepository | PostgreSQL for historical data |
| http_client | HTTP library | For making API requests |

### Implementation Strategy

**get_current_price() logic**:
1. Check cache (Redis) for ticker
   - HIT: Return cached price
2. Check repository (PostgreSQL) for latest price
   - HIT and fresh (<1 hour during market hours): Warm cache, return
   - HIT and stale: Continue to step 3
3. Check rate limiter
   - NO tokens: Return stale data from step 2 OR raise MarketDataUnavailableError
4. Call Alpha Vantage API (GLOBAL_QUOTE endpoint)
   - SUCCESS: Store in repository, cache in Redis, return
   - ERROR: Return stale data OR raise appropriate error

**get_price_at() logic**:
1. Query repository for price closest to timestamp
   - HIT: Return
   - MISS: May need to call API for historical data (Phase 2b)

**get_price_history() logic**:
1. Query repository for date range
   - If sufficient data: Return
   - If gaps: May need to backfill from API (Phase 2b)

### Alpha Vantage API Endpoints

| Endpoint | Purpose | Rate Limit Impact |
|----------|---------|-------------------|
| GLOBAL_QUOTE | Get current price | 1 call per request |
| TIME_SERIES_DAILY | Get daily historical prices | 1 call per request |
| TIME_SERIES_INTRADAY | Get intraday prices (hourly/minute) | 1 call per request |

### Error Mapping

| Alpha Vantage Response | PaperTrade Exception |
|------------------------|----------------------|
| "Invalid API call" | TickerNotFoundError |
| "Thank you for using..." (rate limit) | MarketDataUnavailableError |
| HTTP 5xx errors | MarketDataUnavailableError |
| Malformed JSON | InvalidPriceDataError |
| Network timeout | MarketDataUnavailableError |

### Retry Strategy
- Retry on transient errors (5xx, timeouts): Up to 3 attempts with exponential backoff
- Do NOT retry on 4xx errors (bad request, invalid ticker)
- Do NOT retry on rate limit (wait for token refill)

---

## Configuration Specifications

See [configuration.md](./configuration.md) for detailed TOML structure and validation requirements.

---

## Implementation Notes for SWE Agents

### Translation Guidance

These specifications use **structured formats** (tables, prose) instead of code. When implementing:

1. **Value Objects**: Use `@dataclass(frozen=True)` pattern from Phase 1
2. **Ports**: Use `Protocol` class (typing.Protocol) for interfaces
3. **Exceptions**: Inherit from appropriate base classes
4. **Async Methods**: All I/O operations should be `async def`
5. **Type Hints**: Full type annotations required (Pyright strict mode)

### Do NOT Copy/Paste
These specifications are NOT implementation code. Translate them into actual Python/TypeScript following the project's established patterns.

### Consistency with Phase 1
Review Phase 1 implementations for:
- Value object patterns (Money, Ticker)
- Port definition patterns (PortfolioRepository, TransactionRepository)
- Exception hierarchy (domain/exceptions.py)
- Testing patterns (pytest, mocking with Protocol)

### Where to Put Files

**Domain Layer** (if PricePoint is domain value object):
- `backend/src/papertrade/domain/value_objects/price_point.py`

**Application Layer**:
- `backend/src/papertrade/application/ports/market_data_port.py`
- `backend/src/papertrade/application/exceptions.py` (extend for MarketDataError hierarchy)

**Adapters Layer**:
- `backend/src/papertrade/adapters/outbound/alpha_vantage_adapter.py`
- `backend/src/papertrade/adapters/outbound/price_repository.py`

**Infrastructure Layer**:
- `backend/src/papertrade/infrastructure/cache/price_cache.py`
- `backend/src/papertrade/infrastructure/rate_limiter.py`

---

## Questions for Implementation

If specifications are unclear:
1. Check Phase 1 architecture plans for similar patterns
2. Review existing code for consistency
3. Document assumptions in implementation
4. Ask for clarification in PR review

## Next Steps

1. Read [database-schema.md](./database-schema.md) for PriceHistory table design
2. Read [configuration.md](./configuration.md) for TOML structure
3. Read [implementation-guide.md](./implementation-guide.md) for step-by-step instructions
4. Review [adr-*.md](./adr-001-caching-strategy.md) files for decision rationale
