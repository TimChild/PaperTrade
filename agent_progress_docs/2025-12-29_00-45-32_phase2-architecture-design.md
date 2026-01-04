# Phase 2 Market Data Integration - Architecture Design

**Task**: 014 - Phase 2 Architecture Design - Market Data Integration
**Agent**: Architect
**Date**: 2025-12-29
**Duration**: ~5 hours

## Objective

Design the complete architecture for Phase 2 "Reality Injection" - integrating real market data from Alpha Vantage API while preparing for Phase 3 "Time Machine" historical backtesting.

## Deliverables Summary

### Architecture Documentation (architecture_plans/20251228_phase2-market-data/)

| Document | Lines | Purpose |
|----------|-------|---------|
| **README.md** | 350 | Quick start guide for implementation agents |
| **overview.md** | 400 | Goals, design decisions, risk analysis |
| **interfaces.md** | 650 | Structured specifications (NO code examples) |
| **database-schema.md** | 650 | PriceHistory + TickerWatchlist tables, indexes, migrations |
| **implementation-guide.md** | 900 | Step-by-step instructions for Tasks 015-025 |
| **testing-strategy.md** | 600 | Unit, integration, E2E testing with VCR cassettes |

### Architecture Decision Records (ADRs)

| ADR | Title | Lines | Key Decision |
|-----|-------|-------|--------------|
| **001** | Caching Strategy | 400 | Redis (hot) + PostgreSQL (warm) + Alpha Vantage (cold) |
| **002** | Rate Limiting | 500 | Token bucket algorithm with Redis persistence |
| **003** | Background Refresh | 550 | APScheduler with daily cron job |
| **004** | Configuration | 600 | TOML files with Pydantic/Zod validation |

### Configuration Templates

| File | Lines | Purpose |
|------|-------|---------|
| **backend/config.example.toml** | 140 | Backend configuration template |
| **frontend/config.example.toml** | 80 | Frontend configuration template |
| **.env.example** | Updated | Added Alpha Vantage API key placeholder |

## Architecture Highlights

### Key Design Decisions

#### 1. Tiered Caching Strategy

**Decision**: Three-tier fallback system

```
Tier 1 (Hot): Redis → <100ms
Tier 2 (Warm): PostgreSQL → <500ms
Tier 3 (Cold): Alpha Vantage API → <2s
```

**Rationale**:
- **API Quota Conservation**: Free tier = 5 calls/min, 500/day
- **Performance**: 90% cache hit rate in Redis (fast)
- **Resilience**: Multiple fallback layers
- **Phase 3 Ready**: Historical data already stored in PostgreSQL

**Alternatives Rejected**:
- Redis only (data lost on restart, no Phase 3 support)
- PostgreSQL only (too slow for real-time, 100-200ms)
- No caching (would exhaust quota in hours)

#### 2. Rate Limiting Implementation

**Decision**: Token bucket algorithm with dual time windows (minute + day)

**Implementation**:
- Redis-backed token storage
- Lua script for atomic check-and-consume
- Configurable limits (free tier → premium tier upgrade path)

**Rationale**:
- **Quota Protection**: Cannot exceed Alpha Vantage limits
- **Graceful Degradation**: Serve cached data when rate-limited
- **Persistent**: Token counts survive app restarts
- **Scalable**: Works with multiple instances

#### 3. Background Refresh Strategy

**Decision**: APScheduler with daily cron job (midnight UTC)

**Jobs**:
- Refresh all tracked tickers (portfolios + common stocks)
- Batch processing with rate limit respect
- Error handling (continue on individual failures)

**Rationale**:
- **Right-Sized**: No external dependencies (vs. Celery)
- **Fits Quota**: 500 tickers × 1 refresh/day = 500 calls/day
- **User Experience**: Prices pre-cached when users wake up
- **Extensible**: Easy to add more jobs later

**Alternatives Rejected**:
- Celery (overkill for Phase 2 scale)
- GitHub Actions cron (external dependency, hard to debug)
- Manual refresh only (poor UX, wastes quota)

#### 4. Configuration Management

**Decision**: TOML configuration files with Pydantic (backend) / Zod (frontend) validation

**Structure**:
```
config.toml (defaults, committed)
.env (secrets only, gitignored)
config.{env}.toml (environment overrides, gitignored)
```

**Rationale**:
- **Type Safety**: Validated at startup (fail fast)
- **Discoverability**: config.example.toml shows all options
- **Security**: Secrets separated from configuration
- **Flexibility**: Easy to override per environment

### Interface Design (Time-Aware for Phase 3)

#### MarketDataPort Protocol

```
Methods:
- get_current_price(ticker) → PricePoint
- get_price_at(ticker, timestamp) → PricePoint       # Phase 3 critical!
- get_price_history(ticker, start, end) → List[PricePoint]
- get_supported_tickers() → List[Ticker]
```

**Critical Design**: `get_price_at()` method included from day one to support Phase 3 backtesting without interface changes.

#### PricePoint Specification

**Properties** (structured specification, NOT code):
- ticker: Ticker (stock symbol)
- price: Money (current/closing price)
- timestamp: datetime (UTC)
- source: String (alpha_vantage, cache, database)
- interval: String (real-time, 1day, 1hour, etc.)
- OHLCV: Optional (open, high, low, close, volume)

**Methods**:
- is_stale(max_age) → Boolean
- with_source(new_source) → PricePoint

### Database Schema

#### price_history Table

**Purpose**: Store all historical and current prices

| Column | Type | Purpose |
|--------|------|---------|
| ticker | VARCHAR(5) | Stock symbol |
| price | DECIMAL(15,2) | Price value |
| timestamp | TIMESTAMP WITH TIME ZONE | Observation time (UTC) |
| interval | VARCHAR(10) | Price interval |
| OHLCV | DECIMAL fields | Full market data |

**Indexes**:
- Unique: (ticker, timestamp, interval)
- Query: (ticker, interval, timestamp) - For time-range queries
- Partial: (timestamp WHERE interval='1day') - Most common pattern

**Performance**: <100ms for 1-year daily query (252 rows)

#### ticker_watchlist Table

**Purpose**: Track which tickers to refresh

**Priority Levels**:
1. Critical (1): In portfolios (refresh first)
2. High (2): Common stocks
3. Normal (3): Recently queried
4. Low (5): Stale (not queried in 30+ days)

## Implementation Task Breakdown

### Phase 2a: Current Price Only (Week 1)

| Task | Description | Effort | Agent |
|------|-------------|--------|-------|
| 015 | Domain models (PricePoint, exceptions) | 2-3h | Backend-SWE |
| 016 | MarketDataPort interface + in-memory mock | 1-2h | Backend-SWE |
| 017 | AlphaVantageAdapter + RateLimiter + PriceCache | 6-8h | Backend-SWE |
| 018 | PostgreSQL price repository + migrations | 4-5h | Backend-SWE |
| 019 | Update portfolio use cases for real prices | 3-4h | Backend-SWE |
| 020 | Frontend display real values + config loading | 4-5h | Frontend-SWE |

**Total**: ~25 hours (5 days)

### Phase 2b: Historical Data (Week 2)

| Task | Description | Effort | Agent |
|------|-------------|--------|-------|
| 021 | Historical price queries (get_price_at, get_price_history) | 4-5h | Backend-SWE |
| 022 | Batch import CLI for common stocks | 3-4h | Backend-SWE |
| 023 | Background refresh scheduler (APScheduler) | 5-6h | Backend-SWE |
| 024 | Frontend price history charts | 6-8h | Frontend-SWE |
| 025 | Testing and quality validation | 4-5h | Backend/QA |

**Total**: ~25 hours (5 days)

## Testing Strategy

### Test Distribution
- **70% Unit Tests**: Fast, isolated (domain, application, infrastructure)
- **25% Integration Tests**: With real dependencies (DB, Redis, VCR)
- **5% E2E Tests**: Full user journeys (manual)

### VCR Strategy (pytest-recording)

**Approach**: Record Alpha Vantage API responses once, replay in tests

**Benefits**:
- No API key needed for CI
- Fast tests (no network calls)
- Deterministic (same response every time)
- Detect API changes (cassette invalidation)

**Cassettes**:
```
cassettes/
├── test_get_current_price_aapl.yaml
├── test_get_current_price_ticker_not_found.yaml
├── test_get_current_price_rate_limited.yaml
├── test_get_price_history_daily.yaml
```

### Performance Targets

| Operation | Target | Test Method |
|-----------|--------|-------------|
| Redis cache hit | <100ms | pytest-benchmark |
| PostgreSQL query | <500ms | SQLite integration test |
| API call (cached) | <2s | VCR replay |
| Historical query (1 year) | <1s | 252 rows from test DB |

## Risk Analysis & Mitigation

### Risk 1: API Rate Limits Exhausted

**Likelihood**: Medium
**Impact**: High (no new prices)

**Mitigations**:
- ✅ Pre-populate common stocks (reduce on-demand calls)
- ✅ Aggressive caching (Redis + PostgreSQL)
- ✅ Graceful degradation (serve stale data)
- ✅ Configurable upgrade path to premium tier

### Risk 2: Alpha Vantage API Changes

**Likelihood**: Low
**Impact**: High (adapter breaks)

**Mitigations**:
- ✅ VCR cassettes detect format changes
- ✅ Abstract MarketDataPort allows provider swap
- ✅ Monitor API health and error rates
- ✅ Version pinning for API responses

### Risk 3: Redis/PostgreSQL Operational Complexity

**Likelihood**: Low
**Impact**: Medium (deployment complexity)

**Mitigations**:
- ✅ Docker Compose for local dev (simple setup)
- ✅ AWS managed services for prod (RDS, ElastiCache)
- ✅ Fallback to API-only if cache unavailable
- ✅ Monitoring and alerts for cache health

### Risk 4: Stale Price Data

**Likelihood**: Medium
**Impact**: Low (user sees old prices)

**Mitigations**:
- ✅ Display timestamp with prices ("as of 2:30 PM")
- ✅ Background refresh every 24 hours
- ✅ Frontend polling for updates (configurable interval)
- ✅ Manual refresh button for users

## Adherence to Requirements

### ✅ Clean Architecture Compliance
- **Dependency Rule**: Enforced (Domain → Application → Adapters → Infrastructure)
- **MarketDataPort**: Protocol interface in Application layer
- **Adapters**: Alpha Vantage adapter implements port
- **No coupling**: Domain layer has zero knowledge of Alpha Vantage

### ✅ Phase 3 Readiness
- **Time-aware interface**: `get_price_at(ticker, timestamp)` designed from day one
- **Historical storage**: PostgreSQL stores all prices indefinitely
- **No refactoring needed**: Interface supports backtesting without changes

### ✅ Testability
- **VCR cassettes**: No real API calls in CI
- **Mocks at boundaries**: MarketDataPort mockable in use cases
- **In-memory implementations**: InMemoryMarketDataPort for fast unit tests
- **Integration tests**: Use test database and fakeredis

### ✅ Extensibility
- **Multi-provider ready**: MarketDataPort supports any data source
- **Configurable**: Tier upgrades, providers, schedules all in TOML
- **Pluggable**: RateLimiter, cache, scheduler are replaceable

### ✅ Type Safety
- **Pyright strict**: All interfaces fully typed
- **Pydantic Settings**: Configuration validated at startup
- **Zod (frontend)**: TypeScript config validation
- **Protocol interfaces**: Type-safe port contracts

## Architect Notes

### Design Philosophy

**"Design for the system you know you'll need, not the system you might need someday"**

- **Phase 3 backtesting**: Known requirement → Design `get_price_at()` now
- **Multi-cloud deployment**: Unknown requirement → Don't over-engineer
- **Multiple data providers**: Possible future → Abstract interface, but only implement one

### Structured Specifications (Not Code)

**Critical**: This architecture uses **tables, prose, and diagrams** instead of code examples.

**Rationale**:
- Code examples can mislead SWE agents (architect lacks full implementation context)
- Structured specs are clearer about requirements vs. implementation
- SWE agents translate specs to code using project patterns

**Example**:
- ❌ Don't: "Here's example code for PricePoint class..."
- ✅ Do: "PricePoint properties table: ticker (Ticker), price (Money), ..."

### Lessons from Phase 1

**What Worked**:
- Comprehensive architecture plans reduced implementation questions
- Structured specifications (tables) clearer than pseudocode
- ADRs captured rationale (prevents revisiting decisions)
- Step-by-step implementation guides kept agents on track

**Applied to Phase 2**:
- Same documentation structure (overview → interfaces → ADRs → guide)
- Explicit task breakdown with dependencies
- Testing strategy upfront (not afterthought)
- Risk analysis with concrete mitigations

## Follow-Up Actions

### For Implementation Agents

**Before starting any task**:
1. Read [README.md](../architecture_plans/20251228_phase2-market-data/README.md) (overview)
2. Read [implementation-guide.md](../architecture_plans/20251228_phase2-market-data/implementation-guide.md) (your specific task)
3. Read relevant ADRs (design rationale)
4. Review Phase 1 code (patterns to follow)

### For Stakeholders

**Review Points**:
- After Phase 2a (Week 1): Demo real prices in portfolios
- After Phase 2b (Week 2): Demo price charts and background refresh
- Metrics to track: Cache hit rate, API usage, query performance

## Success Metrics (How We'll Know It Worked)

### Technical Metrics
- **API usage**: <50 calls/day with 100 active users (target: <20)
- **Cache hit rate**: >85% (Redis + PostgreSQL combined)
- **Response time**: <500ms for portfolio value calculation (p95)
- **Test coverage**: >85% overall

### User Experience Metrics
- **Portfolio load time**: <1s (including price fetch)
- **Price staleness**: <5% of users see prices >1 hour old
- **Error rate**: <1% of price fetches fail

### Business Metrics
- **User engagement**: Time spent on platform increases (real prices more interesting)
- **Feature usage**: >50% of users view price charts (Phase 2b)
- **API costs**: Stay on free tier until >500 active daily users

## Conclusion

This architecture design provides a comprehensive blueprint for Phase 2 Market Data Integration. Key strengths:

1. **Pragmatic**: Solves current needs (real prices) without over-engineering
2. **Future-Proof**: Designed for Phase 3 backtesting from day one
3. **Resilient**: Multiple fallback layers, graceful degradation
4. **Testable**: VCR cassettes, mocks at boundaries, clear test strategy
5. **Documented**: Implementation agents have clear step-by-step guides

**Estimated Total Effort**: 50 hours (2 weeks with 1 FTE)

**Critical Path**:
- Backend foundation (Tasks 015-018) must complete before frontend (Task 020)
- Phase 2b builds on Phase 2a (no parallelization)

**Ready for Implementation**: All specifications complete, agents can begin work.

---

**Architect Sign-Off**: This design is ready for implementation. All architectural decisions documented, risks identified and mitigated, task breakdown complete.
