# Phase 2 Market Data Integration - Architecture Plan Summary

**Created**: 2025-12-28  
**Status**: Approved for Implementation  
**Phase**: Phase 2 "Reality Injection"

## Quick Start for Implementation Agents

**If you're implementing a Phase 2 task, read documents in this order**:

1. **START HERE**: [overview.md](./overview.md) - Goals, decisions, and context
2. **INTERFACES**: [interfaces.md](./interfaces.md) - MarketDataPort, PricePoint specifications
3. **YOUR TASK ADR**: Read relevant ADR for your task:
   - Caching work → [adr-001-caching-strategy.md](./adr-001-caching-strategy.md)
   - Rate limiting → [adr-002-rate-limiting.md](./adr-002-rate-limiting.md)
   - Scheduler → [adr-003-background-refresh.md](./adr-003-background-refresh.md)
   - Configuration → [adr-004-configuration.md](./adr-004-configuration.md)
4. **DATABASE**: [database-schema.md](./database-schema.md) - If touching persistence
5. **IMPLEMENTATION**: [implementation-guide.md](./implementation-guide.md) - Step-by-step for your task
6. **TESTING**: [testing-strategy.md](./testing-strategy.md) - How to test your changes

## What We're Building

### The Problem
Phase 1 works with **mock prices** ($100 for everything). Phase 2 connects to **Alpha Vantage API** for real market data.

### The Solution

**Phase 2a** (Week 1): Current prices only
- Real stock prices in portfolios
- Cached pricing (Redis + PostgreSQL)
- Rate limiting (5 calls/min free tier)

**Phase 2b** (Week 2): Historical data
- Price charts
- Historical queries (for Phase 3 backtesting)
- Background refresh (daily)

## Architecture at a Glance

### Data Flow

```
User views portfolio
  ↓
GetPortfolioBalance query
  ↓
MarketDataPort.get_current_price(AAPL)
  ↓
AlphaVantageAdapter checks caches:
  1. Redis (hot) → HIT: Return in <100ms
  2. PostgreSQL (warm) → HIT: Return in <500ms
  3. Alpha Vantage API (cold) → Return in <2s
  ↓
Price returned to user
```

### Key Design Decisions

| Decision | Choice | Why |
|----------|--------|-----|
| **Caching** | Redis + PostgreSQL | Fast + persistent |
| **Rate Limiting** | Token bucket (Redis) | Prevent quota exhaustion |
| **Scheduler** | APScheduler | Simple, no new infrastructure |
| **Config** | TOML files | Readable, validated |
| **Testing** | VCR cassettes | No API keys in CI |

### Components

| Component | Layer | Purpose | File Location |
|-----------|-------|---------|---------------|
| **PricePoint** | Domain/Application | Price data structure | `domain/value_objects/` or `application/dtos/` |
| **MarketDataPort** | Application | Interface for market data | `application/ports/market_data_port.py` |
| **AlphaVantageAdapter** | Adapters | Alpha Vantage API client | `adapters/outbound/alpha_vantage_adapter.py` |
| **PriceRepository** | Adapters | PostgreSQL storage | `adapters/outbound/repositories/price_repository.py` |
| **PriceCache** | Infrastructure | Redis wrapper | `infrastructure/cache/price_cache.py` |
| **RateLimiter** | Infrastructure | API quota management | `infrastructure/rate_limiter.py` |
| **PriceRefreshJob** | Infrastructure | Background refresh | `infrastructure/scheduler/jobs/refresh_prices.py` |

### Database Tables

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| **price_history** | All historical prices | ticker, timestamp, price, interval, OHLCV data |
| **ticker_watchlist** | Tickers to refresh | ticker, priority, last_refreshed_at |

## Implementation Tasks

### Phase 2a: Current Price Only

| Task | Agent | Effort | Dependencies |
|------|-------|--------|--------------|
| **015** | Backend-SWE | 2-3h | None |
| Domain models (PricePoint, exceptions) | | | |
| **016** | Backend-SWE | 1-2h | 015 |
| MarketDataPort interface | | | |
| **017** | Backend-SWE | 6-8h | 016 |
| AlphaVantageAdapter + RateLimiter + PriceCache | | | |
| **018** | Backend-SWE | 4-5h | 015 |
| PostgreSQL price repository + migrations | | | |
| **019** | Backend-SWE | 3-4h | 016, 017, 018 |
| Update portfolio use cases for real prices | | | |
| **020** | Frontend-SWE | 4-5h | 019 |
| Frontend display real values + config loading | | | |

**Total Phase 2a**: ~25 hours over 5 days

### Phase 2b: Historical Data

| Task | Agent | Effort | Dependencies |
|------|-------|--------|--------------|
| **021** | Backend-SWE | 4-5h | 018 |
| Historical price queries (get_price_at, get_price_history) | | | |
| **022** | Backend-SWE | 3-4h | 021 |
| Batch import CLI for common stocks | | | |
| **023** | Backend-SWE | 5-6h | 018 |
| Background refresh scheduler (APScheduler) | | | |
| **024** | Frontend-SWE | 6-8h | 021 |
| Price history charts | | | |
| **025** | Backend/QA | 4-5h | All |
| Testing and quality validation | | | |

**Total Phase 2b**: ~25 hours over 5 days

## Configuration

### Backend (backend/config.toml)

```toml
[market_data.alpha_vantage]
api_key = "${ALPHA_VANTAGE_API_KEY}"  # From .env

[market_data.rate_limit]
tier = "free"  # 5 calls/min, 500/day
calls_per_minute = 5
calls_per_day = 500

[cache]
redis_url = "redis://localhost:6379"
price_ttl_seconds = 3600  # 1 hour

[scheduler]
refresh_cron = "0 0 * * *"  # Midnight UTC
```

### Frontend (frontend/config.toml)

```toml
[features]
enable_real_prices = true      # Phase 2a
enable_price_charts = false    # Phase 2b

[cache]
price_update_interval_ms = 60000  # 1 minute
```

### Secrets (.env)

```bash
ALPHA_VANTAGE_API_KEY=your_key_here
DATABASE_URL=postgresql+asyncpg://...
```

## Testing Approach

### Test Distribution
- **70% Unit Tests**: Domain, application, infrastructure logic
- **25% Integration Tests**: Database, Redis, Alpha Vantage (VCR)
- **5% E2E Tests**: Manual testing scenarios

### VCR Cassettes
Record Alpha Vantage responses once, replay in tests (no API key needed):

```python
@pytest.mark.vcr()
async def test_get_current_price_aapl():
    # Uses cassette: cassettes/test_get_current_price_aapl.yaml
    adapter = AlphaVantageAdapter(...)
    price = await adapter.get_current_price(Ticker("AAPL"))
    assert price.ticker.symbol == "AAPL"
```

### Performance Targets
- Cache hit: <100ms
- Database query: <500ms
- API call: <2s
- Historical query (1 year): <1s

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
- [ ] Historical price queries working
- [ ] Price history charts displayed
- [ ] Background refresh scheduler running
- [ ] Common stocks pre-populated
- [ ] Performance targets met
- [ ] Documentation complete

## Common Pitfalls

### ❌ Don't Do This

1. **Don't hardcode API keys** - Use environment variables
2. **Don't skip rate limiting** - Will exhaust quota
3. **Don't use naive datetimes** - Always UTC (`datetime.now(timezone.utc)`)
4. **Don't make API calls in tests** - Use VCR cassettes
5. **Don't ignore cache misses** - Implement full fallback chain

### ✅ Do This

1. **Do validate configuration at startup** - Fail fast with helpful errors
2. **Do log cache hit/miss** - Observability is critical
3. **Do handle API errors gracefully** - Serve stale data when possible
4. **Do test error paths** - Network failures, rate limits, etc.
5. **Do follow Phase 1 patterns** - Value objects, Protocols, type hints

## Questions?

### Before Asking
1. Check [implementation-guide.md](./implementation-guide.md) for your specific task
2. Review relevant ADR for design rationale
3. Look at Phase 1 code for similar patterns

### Where to Ask
- PR comments (for task-specific questions)
- Architecture plan issue (for design questions)
- Slack/Discord (for urgent blockers)

## Rollout Plan

### Week 1: Phase 2a (Current Prices)
- **Day 1-2**: Domain models, interfaces, adapters
- **Day 3-4**: Database, caching, rate limiting
- **Day 5**: Frontend integration

### Week 2: Phase 2b (Historical Data)
- **Day 6-7**: Historical queries, batch import
- **Day 8-9**: Scheduler, price charts
- **Day 10**: Testing, documentation, demo

## References

- [Alpha Vantage API Docs](https://www.alphavantage.co/documentation/)
- [Phase 1 Architecture](../20251227_phase1-backend-mvp/)
- [Project Plan](../../project_plan.md#phase-2-reality-injection)
- [Clean Architecture Principles](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)

---

**Ready to implement?** Start with [implementation-guide.md](./implementation-guide.md) for step-by-step instructions for your task.
