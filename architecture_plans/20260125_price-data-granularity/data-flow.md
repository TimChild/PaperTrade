# Data Flow Diagrams

This document illustrates how data flows through the system for different scenarios.

## Overview

The price data granularity system involves multiple components:
- **Frontend**: TimeRangeSelector, PriceChart
- **API Layer**: Price history endpoint
- **Application Layer**: IntervalSelector service
- **Adapter Layer**: AlphaVantageAdapter, PriceCache, PriceRepository
- **External**: Alpha Vantage API

## Scenario 1: User Views 1D Chart (Premium Tier, Cache Hit)

```mermaid
sequenceDiagram
    actor User
    participant Frontend
    participant API as Price API
    participant Selector as IntervalSelector
    participant Adapter as AlphaVantageAdapter
    participant Redis as Redis Cache
    
    User->>Frontend: Select "1D" time range
    Frontend->>Frontend: Calculate start/end dates
    Note over Frontend: start = today - 1 day<br/>end = today
    Frontend->>API: GET /prices/AAPL/history?start=2026-01-24&end=2026-01-25
    Note over API: No interval parameter specified
    
    API->>Selector: select_interval(days=1, tier="premium")
    Selector->>Selector: Calculate optimal interval
    Note over Selector: 1 day → "15min"
    Selector-->>API: "15min"
    
    API->>Adapter: get_price_history("AAPL", start, end, "15min")
    Adapter->>Redis: GET papertrade:price:AAPL:15min:2026-01-25
    Redis-->>Adapter: HIT - 26 price points
    Note over Adapter: Data found in cache<br/>TTL: 15 minutes
    
    Adapter-->>API: List[PricePoint] (26 points)
    API-->>Frontend: {prices: [...], interval: "15min", count: 26}
    Frontend->>Frontend: Render chart with 26 points
    Frontend->>User: Display intraday chart
    Note over User: Sees smooth intraday movement
```

**Performance**: <100ms total (Redis cache hit)

---

## Scenario 2: User Views 1D Chart (Premium Tier, Cache Miss)

```mermaid
sequenceDiagram
    actor User
    participant Frontend
    participant API as Price API
    participant Selector as IntervalSelector
    participant Adapter as AlphaVantageAdapter
    participant Redis as Redis Cache
    participant AV as Alpha Vantage API
    
    User->>Frontend: Select "1D" time range
    Frontend->>API: GET /prices/AAPL/history?start=2026-01-24&end=2026-01-25
    
    API->>Selector: select_interval(days=1, tier="premium")
    Selector-->>API: "15min"
    
    API->>Adapter: get_price_history("AAPL", start, end, "15min")
    Adapter->>Redis: GET papertrade:price:AAPL:15min:2026-01-25
    Redis-->>Adapter: MISS
    
    Note over Adapter: Intraday data not in PostgreSQL<br/>Must call API
    
    Adapter->>Adapter: Check rate limiter
    Note over Adapter: Tokens available: 74/75
    
    Adapter->>AV: TIME_SERIES_INTRADAY<br/>symbol=AAPL, interval=15min
    AV-->>Adapter: JSON with 26 price points
    Note over AV: ~3KB response
    
    Adapter->>Adapter: Parse and transform to PricePoints
    Adapter->>Redis: SET papertrade:price:AAPL:15min:2026-01-25<br/>TTL = 15 minutes
    Redis-->>Adapter: OK
    
    Note over Adapter: NOT stored in PostgreSQL<br/>(intraday is ephemeral)
    
    Adapter-->>API: List[PricePoint] (26 points)
    API-->>Frontend: {prices: [...], interval: "15min", count: 26}
    Frontend->>User: Display intraday chart
```

**Performance**: ~2-3 seconds (API call + caching)

---

## Scenario 3: User Views 1D Chart (Free Tier, Graceful Fallback)

```mermaid
sequenceDiagram
    actor User
    participant Frontend
    participant API as Price API
    participant Selector as IntervalSelector
    participant Adapter as AlphaVantageAdapter
    participant Redis as Redis Cache
    participant PG as PostgreSQL
    participant AV as Alpha Vantage API
    
    User->>Frontend: Select "1D" time range
    Frontend->>API: GET /prices/AAPL/history?start=2026-01-24&end=2026-01-25
    
    API->>Selector: select_interval(days=1, tier="free")
    Note over Selector: Optimal: "15min"<br/>Available: ["1day"]<br/>Selected: "1day" (fallback)
    Selector-->>API: "1day"
    
    API->>Adapter: get_price_history("AAPL", start, end, "1day")
    Adapter->>Redis: GET papertrade:price:AAPL:1day:2026-01-24
    Redis-->>Adapter: MISS
    
    Adapter->>PG: SELECT * FROM price_history<br/>WHERE ticker='AAPL' AND interval='1day'<br/>AND timestamp BETWEEN ...
    PG-->>Adapter: HIT - 1 price point (yesterday's close)
    
    Adapter->>Redis: SET papertrade:price:AAPL:1day:2026-01-24<br/>TTL = 24 hours (historical)
    
    Adapter-->>API: List[PricePoint] (1 point)
    API-->>Frontend: {prices: [...], interval: "1day", count: 1}
    Frontend->>User: Display chart with 1 point
    Note over User: Limited data but functional
```

**Performance**: ~500ms (PostgreSQL query)

---

## Scenario 4: User Views 1Y Chart (Any Tier)

```mermaid
sequenceDiagram
    actor User
    participant Frontend
    participant API as Price API
    participant Selector as IntervalSelector
    participant Adapter as AlphaVantageAdapter
    participant Redis as Redis Cache
    participant PG as PostgreSQL
    
    User->>Frontend: Select "1Y" time range
    Frontend->>API: GET /prices/AAPL/history?start=2025-01-25&end=2026-01-25
    
    API->>Selector: select_interval(days=365, tier="premium")
    Note over Selector: 365 days → "1day"<br/>(same for free or premium)
    Selector-->>API: "1day"
    
    API->>Adapter: get_price_history("AAPL", start, end, "1day")
    
    Adapter->>Redis: MGET papertrade:price:AAPL:1day:{2025-01-25..2026-01-25}
    Note over Redis: Query 365 keys (1 per day)
    Redis-->>Adapter: Partial HIT (200 days cached)
    
    Adapter->>PG: SELECT * FROM price_history<br/>WHERE ticker='AAPL' AND interval='1day'<br/>AND timestamp BETWEEN 2025-01-25 AND 2026-01-25
    PG-->>Adapter: HIT - 252 trading days
    
    Adapter->>Adapter: Combine Redis + PostgreSQL data<br/>Remove duplicates
    
    Adapter->>Redis: SET missing keys in Redis<br/>TTL = 24 hours (historical)
    
    Adapter-->>API: List[PricePoint] (252 points)
    API-->>Frontend: {prices: [...], interval: "1day", count: 252}
    Frontend->>User: Display yearly chart
```

**Performance**: ~1 second (PostgreSQL query + cache warming)

---

## Scenario 5: User Switches from 1D to 1W (Premium Tier)

```mermaid
sequenceDiagram
    actor User
    participant Frontend
    participant API as Price API
    participant Selector as IntervalSelector
    participant Adapter as AlphaVantageAdapter
    participant Redis as Redis Cache
    
    Note over User,Redis: Initial state: 1D chart displayed (15min data)
    
    User->>Frontend: Click "1W" button
    Frontend->>Frontend: Show loading skeleton
    Frontend->>API: GET /prices/AAPL/history?start=2026-01-18&end=2026-01-25
    
    API->>Selector: select_interval(days=7, tier="premium")
    Note over Selector: 7 days → "1hour"
    Selector-->>API: "1hour"
    
    API->>Adapter: get_price_history("AAPL", start, end, "1hour")
    Adapter->>Redis: GET papertrade:price:AAPL:1hour:2026-01-{18..25}
    Redis-->>Adapter: MISS (not cached yet)
    
    Note over Adapter: Must call API for hourly data
    Adapter->>Adapter: Call Alpha Vantage TIME_SERIES_INTRADAY<br/>interval=60min, outputsize=full
    
    Adapter->>Redis: SET hourly data for 7 days<br/>TTL = 1 hour
    
    Adapter-->>API: List[PricePoint] (35 points)
    API-->>Frontend: {prices: [...], interval: "1hour", count: 35}
    Frontend->>Frontend: Re-render chart with hourly data
    Frontend->>User: Display weekly chart
    Note over User: Sees hourly trends
```

**Performance**: ~3 seconds first time (API call), <100ms on repeat

---

## Scenario 6: Background Cache Warming (Daily Job)

```mermaid
sequenceDiagram
    participant Scheduler as APScheduler
    participant Job as Cache Warming Job
    participant Adapter as AlphaVantageAdapter
    participant Redis as Redis Cache
    participant PG as PostgreSQL
    participant AV as Alpha Vantage API
    
    Note over Scheduler: Midnight ET (market closed)
    
    Scheduler->>Job: Trigger daily cache warming
    Job->>Job: Load list of top 100 tickers
    
    loop For each ticker (rate-limited)
        Job->>Adapter: get_price_history(ticker, last_30_days, "1day")
        
        Adapter->>PG: Check for missing dates
        PG-->>Adapter: Missing: last 1 day
        
        Adapter->>Adapter: Wait for rate limiter token
        Note over Adapter: Batch calls with 12s delays<br/>(5 calls/min free tier)
        
        Adapter->>AV: TIME_SERIES_DAILY (ticker)
        AV-->>Adapter: Last 30 days of daily data
        
        Adapter->>PG: INSERT new daily prices
        Adapter->>Redis: SET daily prices (TTL: 24h)
        
        Job->>Job: Log: "Ticker {ticker} refreshed"
    end
    
    Job->>Job: Summary: "100 tickers refreshed in 20 minutes"
    Job-->>Scheduler: Complete
```

**Duration**: ~20 minutes (100 tickers × 12 seconds with rate limiting)
**Benefit**: All popular tickers cached before market open

---

## Scenario 7: Rate Limit Exceeded (Graceful Degradation)

```mermaid
sequenceDiagram
    actor User
    participant Frontend
    participant API as Price API
    participant Adapter as AlphaVantageAdapter
    participant Limiter as Rate Limiter
    participant Redis as Redis Cache
    participant PG as PostgreSQL
    
    User->>Frontend: Select "1D" time range
    Frontend->>API: GET /prices/AAPL/history?start=2026-01-24&end=2026-01-25
    API->>Adapter: get_price_history("AAPL", start, end, "15min")
    
    Adapter->>Redis: GET papertrade:price:AAPL:15min:2026-01-25
    Redis-->>Adapter: MISS
    
    Adapter->>Limiter: Request token
    Limiter-->>Adapter: ❌ No tokens available<br/>Rate limit: 5/min (all used)
    
    Note over Adapter: Intraday data unavailable<br/>Try fallback to daily
    
    Adapter->>Adapter: Retry with interval="1day"
    Adapter->>Redis: GET papertrade:price:AAPL:1day:2026-01-24
    Redis-->>Adapter: HIT
    
    Note over Adapter: Serve daily data instead<br/>Log warning: "Rate limited, served fallback"
    
    Adapter-->>API: List[PricePoint] (1 point, interval="1day")
    API-->>Frontend: {prices: [...], interval: "1day", count: 1}
    Note over API: Response includes actual interval used
    
    Frontend->>Frontend: Display message:<br/>"Showing daily data (intraday unavailable)"
    Frontend->>User: Chart with 1 point + explanation
```

**Graceful Degradation**: System continues working with reduced granularity

---

## Scenario 8: Capability Detection on Startup

```mermaid
sequenceDiagram
    participant App as Backend Application
    participant Adapter as AlphaVantageAdapter
    participant Redis as Redis Cache
    participant AV as Alpha Vantage API
    
    App->>Adapter: Initialize on startup
    
    Adapter->>Redis: GET papertrade:capabilities:alpha_vantage
    Redis-->>Adapter: MISS (or expired)
    
    Note over Adapter: Need to detect API tier
    
    Adapter->>Adapter: Check configuration
    Note over Adapter: config.tier = "auto"<br/>(not manually set)
    
    Adapter->>AV: Test call: TIME_SERIES_INTRADAY<br/>symbol=AAPL, interval=1min
    
    alt Premium Tier
        AV-->>Adapter: ✅ Success (data returned)
        Adapter->>Adapter: Set tier = "premium"
        Adapter->>Adapter: Set supported_intervals = <br/>["1min","5min","15min","30min","60min","1day"]
    else Free Tier
        AV-->>Adapter: ❌ Error: "Premium only"
        Adapter->>Adapter: Set tier = "free"
        Adapter->>Adapter: Set supported_intervals = ["1day"]
    end
    
    Adapter->>Redis: SET papertrade:capabilities:alpha_vantage<br/>TTL = 24 hours
    Redis-->>Adapter: OK
    
    Adapter->>Adapter: Log: "Detected {tier} tier with intervals: {intervals}"
    Adapter-->>App: Initialization complete
```

**Frequency**: Once per day (or on cache miss)
**Cost**: 1 API call per day

---

## Component Interaction Summary

### Component Responsibilities

| Component | Responsibility | Key Decisions |
|-----------|----------------|---------------|
| **Frontend** | User interaction, time range selection | Display appropriate chart for interval |
| **API Layer** | Request validation, interval selection | Choose optimal interval when not specified |
| **IntervalSelector** | Interval selection logic | Map time ranges to intervals with fallback |
| **AlphaVantageAdapter** | Data fetching, caching | Route to correct endpoint, store appropriately |
| **Redis Cache** | Fast data access | TTL management, key generation |
| **PostgreSQL** | Historical data storage | Store daily data permanently |
| **Rate Limiter** | API quota management | Allow/deny API calls based on token bucket |

### Data Flow Patterns

| Pattern | When Used | Performance |
|---------|-----------|-------------|
| **Direct Cache Hit** | Recent data, high traffic ticker | <100ms |
| **Database Fallback** | Historical daily data | <500ms |
| **API Call (Intraday)** | Cache miss, premium tier | 2-3s |
| **API Call (Daily)** | Cache miss, any tier | 2-3s |
| **Graceful Fallback** | Rate limited, tier downgrade | <500ms |

### Cache Invalidation Triggers

| Trigger | Action | Frequency |
|---------|--------|-----------|
| **TTL Expiration** | Redis evicts key automatically | Continuous |
| **Market Close** | Update today's TTL from 1h → 4h | Daily at 4PM ET |
| **Manual Refresh** | Clear Redis keys, refetch | On-demand |
| **Stock Split** | Clear all keys, update PostgreSQL | Rare |

---

## Performance Optimization Strategies

### 1. Parallel Cache Lookups

For date range queries (e.g., 1Y), lookup all dates in parallel:

```
Instead of:
  FOR each date:
      Redis.GET(key)

Do:
  Redis.MGET(all_keys)  # Single round-trip
```

**Benefit**: 10x faster for multi-day queries

### 2. Cache Warming Before Market Open

Pre-fetch popular tickers before 9:30 AM ET:

```
At 8:00 AM ET:
  FOR top_100_tickers:
      Fetch daily data for yesterday
      Cache in Redis
```

**Benefit**: Zero API calls during market open rush

### 3. Interval Downgrade on Rate Limit

Instead of error, try coarser interval:

```
Request 15min → Rate limited
Try 1hour → Rate limited
Try 1day → Success (served from cache)
```

**Benefit**: Better user experience than error page

### 4. Smart TTL Adjustment

Extend TTL during low volatility periods:

```
IF after_hours AND low_volume:
    TTL = 4 hours
ELSE IF market_hours:
    TTL = 15 minutes
```

**Benefit**: Fewer API calls without stale data

---

## Error Handling Flow

```mermaid
flowchart TD
    Start[API Request] --> CheckCache{Cache Hit?}
    CheckCache -->|Yes| Return[Return Cached Data]
    CheckCache -->|No| CheckDB{DB Hit?}
    CheckDB -->|Yes| WarmCache[Warm Cache] --> Return
    CheckDB -->|No| CheckRateLimit{Rate Limit OK?}
    CheckRateLimit -->|Yes| CallAPI[Call Alpha Vantage]
    CheckRateLimit -->|No| Fallback{Fallback Available?}
    
    CallAPI --> APISuccess{Success?}
    APISuccess -->|Yes| StoreData[Store in Cache/DB] --> Return
    APISuccess -->|No| APIError{Error Type?}
    
    APIError -->|Premium Required| Fallback
    APIError -->|Network Error| Retry{Retry Count < 3?}
    APIError -->|Invalid Ticker| Error404[Return 404]
    
    Retry -->|Yes| Wait[Wait + Backoff] --> CallAPI
    Retry -->|No| Fallback
    
    Fallback -->|Daily Data| ReturnStale[Return Stale/Daily Data]
    Fallback -->|No Fallback| Error503[Return 503 Error]
```

---

## Future Enhancements

### Real-Time Streaming (Phase 5)

Instead of polling, use WebSocket for real-time updates:

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant WebSocket
    participant Backend
    participant AV as Alpha Vantage Stream
    
    User->>Frontend: Open 1D chart
    Frontend->>WebSocket: Subscribe to AAPL real-time
    WebSocket->>Backend: Register subscription
    Backend->>AV: Connect to streaming API
    
    loop Every minute
        AV->>Backend: New price point
        Backend->>WebSocket: Push update
        WebSocket->>Frontend: New data
        Frontend->>Frontend: Update chart incrementally
        Frontend->>User: Live chart update
    end
```

**Benefit**: No polling, instant updates, lower API usage

---

## References

- [Mermaid Sequence Diagram Syntax](https://mermaid.js.org/syntax/sequenceDiagram.html)
- [Alpha Vantage API Documentation](https://www.alphavantage.co/documentation/)
- [ADR-174-001: Backend-Determined Interval Selection](./decisions.md#adr-174-001)
- [Caching Strategy](./caching-strategy.md)
