# Phase 2 Market Data Integration - Architecture Overview

**Created**: 2025-12-28
**Status**: Approved
**Phase**: Phase 2 "Reality Injection"

## Executive Summary

This architecture plan extends PaperTrade's Phase 1 MVP (portfolio management with mock prices) to integrate real market data from Alpha Vantage API. The design prioritizes:

1. **Extensibility**: Interface designed for Phase 3 "Time Machine" (historical backtesting)
2. **Resilience**: Tiered caching strategy to respect API rate limits
3. **Testability**: VCR-based testing without real API calls
4. **Configurability**: TOML-based configuration management

## Current State (Phase 1 Complete)

### What We Have ✅
- **Domain Layer**: Portfolio, Transaction, Holding entities with Money/Ticker value objects
- **Application Layer**: CQRS commands/queries for portfolio operations
- **Adapters Layer**: FastAPI REST API, SQLModel repositories (PostgreSQL)
- **Frontend**: React + TypeScript with TanStack Query
- **Testing**: 218 tests passing (195 backend, 23 frontend)
- **Architecture Score**: 10/10 Clean Architecture compliance

### What's Missing ❌
- Real market data integration
- Price history storage
- Caching infrastructure (Redis)
- Background refresh scheduler
- Price charts and live updates

## Phase 2 Goals

### Phase 2a: Current Price Only (Week 1)
**Deliverable**: Portfolio displays real market values

- MarketDataPort interface (designed for future extensions)
- Alpha Vantage adapter with rate limiting
- Redis caching layer (hot data)
- PostgreSQL price storage (warm/historical data)
- Update portfolio use cases to fetch real prices
- Frontend displays real portfolio values

### Phase 2b: Historical Data (Week 2)
**Deliverable**: Price charts and historical queries

- Implement `get_price_at()` and `get_price_history()`
- Batch import for common stocks
- Background refresh scheduler (APScheduler)
- Frontend price history charts
- Testing and quality validation

## Key Design Decisions

### 1. MarketDataPort Interface
**Decision**: Time-aware interface from day one

```
get_current_price(ticker) → PricePoint
get_price_at(ticker, timestamp) → PricePoint       # Phase 3 ready!
get_price_history(ticker, start, end) → List[PricePoint]
```

**Rationale**: Phase 3 requires historical price queries. Designing the interface now prevents future refactoring.

### 2. Tiered Caching Strategy
**Decision**: Redis (hot) + PostgreSQL (warm) + Alpha Vantage (cold)

**Cache Flow**:
1. Check Redis (TTL: 1 hour) → HIT: Return cached
2. Check PostgreSQL → HIT: Warm Redis, return stored
3. Call Alpha Vantage (rate-limited) → Store in PostgreSQL + Redis

**Rationale**:
- Free tier: 5 calls/min, 500/day
- Pre-populate common stocks to avoid quota burn
- Graceful degradation when rate-limited

### 3. Configuration Management
**Decision**: TOML files with Pydantic validation (backend) + TypeScript validation (frontend)

**Files**:
- `backend/config.toml` - Rate limits, cache settings, scheduler config
- `frontend/config.toml` - API endpoints, feature flags, update intervals
- `.env` - Secrets (API keys) only

**Rationale**:
- TOML is more readable than JSON/YAML for config
- Pydantic Settings provides type-safe validation
- Environment overrides for deployment flexibility

### 4. Background Refresh
**Decision**: APScheduler (Python) for daily batch refresh

**Strategy**:
- Daily refresh at midnight (configurable cron)
- Pre-populate common stocks (AAPL, MSFT, GOOGL, etc.)
- Respect rate limits (batch with delays)
- Graceful error handling (continue on failure)

**Rationale**: Simple, no external dependencies (vs. Celery), sufficient for Phase 2 scale

## Architecture Layers

### Domain Layer (Minimal Changes)
**New Components**:
- No new entities (prices are external data, not domain)
- Potentially: `PricePoint` value object (or keep as DTO)

### Application Layer (New Port)
**New Components**:
- `MarketDataPort` - Protocol interface for fetching prices
- `MarketDataError` hierarchy (TickerNotFound, MarketDataUnavailable)

### Adapters Layer (Major Work)
**Inbound** (no changes to API):
- Portfolio endpoints continue to work
- May add new price query endpoints later

**Outbound** (new adapters):
- `AlphaVantageAdapter` - Implements MarketDataPort
- `PriceCache` - Redis wrapper for hot data
- `PriceRepository` - PostgreSQL storage for historical prices
- `RateLimiter` - Token bucket algorithm for API quota

**Infrastructure** (new):
- Redis configuration and connection management
- APScheduler setup and job definitions
- Background task orchestration

### Frontend (Enhancements)
**New Features**:
- Real-time price updates (via polling/refresh)
- Price charts (Phase 2b)
- Stock search/autocomplete

## Data Flow Diagrams

### Current Price Fetch Flow
```
User views portfolio
  → GetPortfolioBalance query
    → MarketDataPort.get_current_price(ticker)
      → AlphaVantageAdapter checks Redis
        → MISS: Check PostgreSQL
          → MISS: Call Alpha Vantage API
            → Store in PostgreSQL
            → Cache in Redis
        → HIT: Return cached
      → Return PricePoint
    → Calculate portfolio value
  → Display to user
```

### Background Refresh Flow
```
Scheduler triggers daily refresh
  → For each ticker in watchlist:
    → Check if stale (>24 hours)
      → YES: Fetch from Alpha Vantage (rate-limited)
        → Store in PostgreSQL
        → Update Redis cache
      → NO: Skip
  → Log refresh summary
```

## Non-Functional Requirements

### Performance
- Price lookup: <100ms (Redis cache hit)
- Price lookup: <500ms (PostgreSQL cache hit)
- Price lookup: <2s (API call with retry)
- Historical query (1 year): <1s (PostgreSQL indexed query)

### Reliability
- API downtime: Serve stale data with warning
- Rate limit exceeded: Serve cached data, retry after window
- Invalid ticker: Return error immediately (don't burn quota)

### Scalability
- Support 1000 unique tickers (Phase 2 scope)
- Handle 100 concurrent users (Phase 2 scope)
- Horizontal scaling ready (Redis + PostgreSQL support it)

### Security
- API keys in `.env` (never committed)
- API keys in GitHub Secrets for CI/CD
- No API keys in logs or error messages
- Rate limiting prevents accidental quota exhaustion

## Testing Strategy

### Unit Tests
- MarketDataPort implementations (mock HTTP calls)
- RateLimiter logic (token bucket algorithm)
- Cache eviction logic
- Error handling and fallbacks

### Integration Tests
- Alpha Vantage adapter with VCR cassettes (record once, replay)
- Redis cache operations (use fakeredis or test container)
- PostgreSQL price repository (use test database)
- End-to-end flow: fetch price → cache → retrieve

### Contract Tests
- Alpha Vantage API response format (detect breaking changes)
- MarketDataPort interface compliance (all adapters)

### Performance Tests
- Cache hit ratio under load
- API rate limiting effectiveness
- Historical query performance (large date ranges)

## Risk Analysis

### Risk 1: API Rate Limits Exhausted
**Likelihood**: Medium
**Impact**: High (no new prices)
**Mitigation**:
- Pre-populate common stocks
- Aggressive caching (Redis + PostgreSQL)
- Graceful degradation (serve stale data)
- Upgrade to premium tier when needed (configurable)

### Risk 2: Alpha Vantage API Changes
**Likelihood**: Low
**Impact**: High (adapter breaks)
**Mitigation**:
- VCR cassettes detect format changes
- Abstract MarketDataPort allows provider swap
- Monitor API health and error rates

### Risk 3: Redis/PostgreSQL Operational Complexity
**Likelihood**: Low
**Impact**: Medium (deployment complexity)
**Mitigation**:
- Docker Compose for local development
- AWS managed services for production (RDS, ElastiCache)
- Fallback to API-only mode if cache unavailable

### Risk 4: Stale Price Data
**Likelihood**: Medium
**Impact**: Low (user sees old prices)
**Mitigation**:
- Display timestamp with prices ("as of 2:30 PM")
- Background refresh every 24 hours
- Frontend polling for updates (configurable interval)

### Risk 5: Time Zone Handling
**Likelihood**: Medium
**Impact**: Medium (incorrect price matching)
**Mitigation**:
- Store all timestamps in UTC
- Convert to market timezone for display
- Document timezone handling in ADRs

## Success Criteria

### Phase 2a Complete When:
- [ ] Portfolio displays real stock prices from Alpha Vantage
- [ ] Prices cached in Redis (verified by logs)
- [ ] Prices stored in PostgreSQL (verified by queries)
- [ ] Rate limiting prevents quota exhaustion
- [ ] All tests passing (including VCR tests)
- [ ] Configuration loaded from TOML files
- [ ] Frontend updates when prices change

### Phase 2b Complete When:
- [ ] Historical price queries working (`get_price_at`)
- [ ] Price history charts displayed in frontend
- [ ] Background refresh scheduler running
- [ ] Common stocks pre-populated (AAPL, MSFT, GOOGL, AMZN, TSLA, etc.)
- [ ] Performance meets targets (<1s for 1-year history)
- [ ] Documentation complete (API usage, configuration guide)

## Rollout Plan

### Phase 2a: Minimal Viable (Week 1)
**Day 1-2**: Backend foundation
- Task 015: Domain models and interfaces
- Task 016: MarketDataPort and exception hierarchy
- Task 017: Alpha Vantage adapter with rate limiting

**Day 3-4**: Storage and caching
- Task 018: PostgreSQL price repository and Redis cache
- Task 019: Update portfolio use cases

**Day 5**: Frontend integration
- Task 020: Display real portfolio values

### Phase 2b: Historical Data (Week 2)
**Day 6-7**: Historical queries
- Task 021: Implement `get_price_at` and `get_price_history`
- Task 022: Batch import for common stocks

**Day 8-9**: Automation and UI
- Task 023: Background refresh scheduler
- Task 024: Frontend price charts

**Day 10**: Polish and quality
- Task 025: Testing, documentation, quality validation

### Infrastructure Setup (Parallel)
**Can run alongside Phase 2a**:
- TOML config files
- Pydantic Settings integration
- Frontend config validation
- VCR test infrastructure
- `.env.example` update

## Next Steps

1. **Read ADRs** - Architecture Decision Records for detailed rationale
2. **Read Interface Specifications** - Structured specs for MarketDataPort and PricePoint
3. **Read Database Schema** - PriceHistory table design
4. **Read Implementation Guide** - Step-by-step instructions for SWE agents
5. **Review Task Specifications** - Tasks 015-025 detailed specs

## References

- [Alpha Vantage API Documentation](https://www.alphavantage.co/documentation/)
- [Phase 1 Architecture Plans](../20251227_phase1-backend-mvp/)
- [Project Plan - Phase 2](../../project_plan.md#phase-2-reality-injection)
- [Clean Architecture Principles](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
