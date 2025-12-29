# ADR 001: Tiered Caching Strategy (Redis + PostgreSQL)

**Status**: Approved  
**Date**: 2025-12-28  
**Deciders**: Architecture Team  
**Context**: Phase 2 Market Data Integration

## Context

Alpha Vantage API has strict rate limits on the free tier:
- **5 API calls per minute**
- **500 API calls per day**

With multiple users viewing portfolios and potential for repeated queries, we need a caching strategy that:
1. Minimizes API calls to stay within quotas
2. Provides fast response times for users
3. Supports historical data storage for Phase 3 backtesting
4. Degrades gracefully when API is unavailable or rate-limited

### User Scenarios

**Scenario A**: User views portfolio with 5 stocks
- Without cache: 5 API calls (uses entire per-minute quota)
- With cache: 0-5 API calls depending on staleness

**Scenario B**: 20 users view portfolios during market hours
- Without cache: 100+ API calls (exceeds daily quota in hours)
- With cache: 10-20 API calls (only for cache misses)

**Scenario C**: User backtests strategy over 1 year
- Without cache: Thousands of API calls (impossible with free tier)
- With cache: 0 API calls (serve from historical database)

## Decision

Implement a **three-tier caching strategy**:

1. **Tier 1 (Hot): Redis** - In-memory cache for frequently accessed current prices
2. **Tier 2 (Warm): PostgreSQL** - Persistent storage for all price history
3. **Tier 3 (Cold): Alpha Vantage API** - External data source (rate-limited)

### Cache Flow

```
Request for price
  ↓
Check Redis (Tier 1)
  ├─ HIT: Return immediately (<100ms)
  └─ MISS: ↓
Check PostgreSQL (Tier 2)
  ├─ HIT (fresh data): Warm Redis, return (<500ms)
  ├─ HIT (stale data): ↓
  └─ MISS: ↓
Check Rate Limiter
  ├─ Tokens available: ↓
  │   Call Alpha Vantage (Tier 3)
  │     ├─ SUCCESS: Store in PostgreSQL, cache in Redis, return (<2s)
  │     └─ ERROR: Return stale data OR raise error
  └─ No tokens: Return stale data with warning OR raise error
```

### Tier 1: Redis Cache

**Purpose**: Fast access to recently queried prices

| Property | Value | Rationale |
|----------|-------|-----------|
| **TTL** | 1 hour during market hours, 4 hours after close | Balance freshness vs. API usage |
| **Storage** | Current price only (latest quote) | Keep hot cache small and fast |
| **Eviction** | TTL-based + LRU if memory limit reached | Automatic cleanup |
| **Key Format** | `papertrade:price:{ticker}` | Namespaced, easy to invalidate |
| **Serialization** | JSON | Human-readable, debuggable |

**When to use Redis**:
- Portfolio value calculations (frequent reads)
- Real-time price display in UI
- Quick validation (is price available?)

### Tier 2: PostgreSQL Storage

**Purpose**: Persistent storage for all price history (current + historical)

| Property | Value | Rationale |
|----------|-------|-----------|
| **Retention** | All historical data (unlimited) | Required for Phase 3 backtesting |
| **Indexing** | (ticker, timestamp), (ticker, interval) | Fast time-range queries |
| **Storage** | Full OHLCV data + metadata | Complete price information |
| **Updates** | Upsert (insert or update by ticker+timestamp+interval) | Handle duplicate data gracefully |

**When to use PostgreSQL**:
- Historical price queries (backtesting)
- Cache miss fallback (serve stale data)
- Price charts (date range queries)
- Ticker discovery (what tickers do we have?)

### Tier 3: Alpha Vantage API

**Purpose**: Source of truth for new/fresh data

| Property | Value | Rationale |
|----------|-------|-----------|
| **Rate Limiting** | Token bucket algorithm | Prevent quota exhaustion |
| **Retry Strategy** | Exponential backoff (3 attempts) | Handle transient errors |
| **Timeout** | 5 seconds | Fail fast on network issues |
| **Fallback** | Return stale data if available | Graceful degradation |

**When to call API**:
- Cache miss in both Redis and PostgreSQL
- Explicit refresh request (user action)
- Background refresh job (scheduled)

## Alternatives Considered

### Alternative 1: Redis Only

**Pros**:
- Simplest implementation
- Very fast (<10ms response time)
- No database queries

**Cons**:
- ❌ Data lost on Redis restart
- ❌ No historical data storage (Phase 3 blocker)
- ❌ Higher memory usage for large datasets
- ❌ No backup if Redis unavailable

**Decision**: **Rejected** - Insufficient for Phase 3 requirements

### Alternative 2: PostgreSQL Only

**Pros**:
- Simpler (one storage system)
- Persistent across restarts
- Supports historical queries

**Cons**:
- ❌ Slower for current price lookups (100-200ms)
- ❌ Higher database load (every portfolio view = 5+ queries)
- ❌ Scales poorly with high read traffic

**Decision**: **Rejected** - Performance unacceptable for real-time use

### Alternative 3: Application Memory Cache (LRU Dict)

**Pros**:
- Zero external dependencies
- Very fast (in-process)

**Cons**:
- ❌ Not shared across processes/servers
- ❌ Lost on application restart
- ❌ Memory pressure on app server
- ❌ No TTL management (manual eviction)

**Decision**: **Rejected** - Doesn't scale, manual cache management

### Alternative 4: CDN Caching (Cloudflare/CloudFront)

**Pros**:
- Extremely fast (edge caching)
- Handles high traffic well

**Cons**:
- ❌ Not suitable for dynamic data (per-user portfolios)
- ❌ Cache invalidation complexity
- ❌ Adds external dependency
- ❌ Overkill for Phase 2 scale

**Decision**: **Rejected** - Over-engineering for current needs

## Rationale for Chosen Approach

### Why Redis + PostgreSQL?

1. **Performance Layering**
   - Redis: <100ms for 90% of requests (hot data)
   - PostgreSQL: <500ms for 9% of requests (warm data)
   - API: <2s for 1% of requests (cold data)

2. **API Quota Conservation**
   - Pre-populate common stocks in PostgreSQL (batch import)
   - Redis caches prevent repeated API calls
   - Result: ~50-100 API calls/day for 100 active users

3. **Resilience**
   - Redis down: Fall back to PostgreSQL (slower but works)
   - PostgreSQL down: Fall back to API (if tokens available)
   - API down: Serve stale data from PostgreSQL with warning

4. **Phase 3 Readiness**
   - PostgreSQL stores all historical prices
   - `get_price_at(timestamp)` queries PostgreSQL directly
   - No API calls needed for backtesting

5. **Operational Simplicity**
   - Docker Compose for local dev (both Redis + PostgreSQL)
   - AWS managed services for production (ElastiCache + RDS)
   - Standard tools with good observability

## Cache Coherency Strategy

### Freshness Rules

| Time Period | Freshness Requirement | Cache TTL |
|-------------|----------------------|-----------|
| Market open (9:30 AM - 4:00 PM ET) | <15 minutes | 15 minutes (Redis) |
| After-hours (4:00 PM - 9:30 AM ET) | <4 hours | 4 hours (Redis) |
| Historical (>1 day old) | Immutable | No expiration (PostgreSQL) |

### Cache Invalidation

**Automatic Invalidation**:
- Redis TTL expires → Next read triggers PostgreSQL query
- PostgreSQL has no TTL → Data is immutable (historical prices never change)

**Manual Invalidation**:
- User requests "Refresh Prices" → Clear Redis, force API call
- Admin updates stock split → Adjust historical prices in PostgreSQL

### Consistency Guarantees

- **Eventual Consistency**: Redis and PostgreSQL may briefly diverge
- **Acceptable**: Prices are inherently delayed (not real-time even from API)
- **Trade-off**: Stronger consistency would require distributed locks (not worth complexity)

## Implementation Phases

### Phase 2a (Week 1)
- Implement PriceCache (Redis wrapper)
- Implement PriceRepository (PostgreSQL adapter)
- AlphaVantageAdapter uses both for `get_current_price()`
- Tests verify cache hit/miss behavior

### Phase 2b (Week 2)
- Background job to pre-populate PostgreSQL (common stocks)
- Historical query optimization (indexes)
- Cache warming on application startup
- Monitoring for cache hit rates

## Monitoring & Observability

### Metrics to Track

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| Redis hit rate | >85% | <70% |
| PostgreSQL query time (p95) | <200ms | >500ms |
| API calls per hour | <20 | >40 |
| API quota remaining | >100/day | <50/day |
| Stale data served (%) | <5% | >15% |

### Logs to Capture

- Cache miss reason (Redis miss, PostgreSQL miss, stale data)
- API call with response time
- Rate limit near-miss (tokens < 2)
- Errors serving stale data

## Consequences

### Positive

- ✅ **Performance**: Fast response times (<100ms for cache hits)
- ✅ **Quota Conservation**: Stay within free tier limits
- ✅ **Resilience**: Multiple fallback layers
- ✅ **Phase 3 Ready**: Historical data already stored
- ✅ **Scalability**: Both Redis and PostgreSQL scale horizontally
- ✅ **Debuggability**: Can inspect cached data easily

### Negative

- ⚠️ **Operational Complexity**: Two systems to manage vs. one
- ⚠️ **Eventual Consistency**: Redis and PostgreSQL may briefly diverge
- ⚠️ **Memory Usage**: Redis requires dedicated memory allocation
- ⚠️ **Cost**: Managed Redis (ElastiCache) adds infrastructure cost

### Neutral

- 🔄 **Data Staleness**: Trade-off between freshness and API usage
- 🔄 **Testing Complexity**: Need to test cache behavior (hit/miss/eviction)

## Migration Path

### Upgrading to Premium API Tier

When we outgrow free tier (500/day):
1. Update rate limiter configuration (75/min, 100K/day)
2. Reduce Redis TTL (fresher data)
3. No code changes required (just config)

### Switching Data Providers

If we switch from Alpha Vantage to another provider (e.g., Finnhub, Polygon):
1. Implement new adapter (same MarketDataPort interface)
2. Keep cache and repository unchanged
3. Test with VCR cassettes for new provider
4. Deploy with feature flag (gradual rollout)

## Review Schedule

- **After Phase 2a**: Review cache hit rates and API usage
- **After Phase 2b**: Review historical query performance
- **After Phase 3**: Review backtest performance with cached data
- **Quarterly**: Review AWS costs (ElastiCache vs. query frequency)

## References

- [Redis Caching Patterns](https://redis.io/docs/manual/patterns/caching/)
- [PostgreSQL Indexing for Time-Series Data](https://www.timescale.com/blog/time-series-data-postgresql-10-vs-timescaledb-816-vs-influxdb-1-7/)
- [Alpha Vantage API Rate Limits](https://www.alphavantage.co/documentation/#support)
- [Token Bucket Algorithm](https://en.wikipedia.org/wiki/Token_bucket)
