# Price Data Granularity System - Architecture Plan

**Created**: 2026-01-25
**Status**: Proposed
**Priority**: MEDIUM
**Type**: Architecture Design Document

## Quick Start

This architecture plan defines how Zebu will serve appropriate price data granularity based on viewing context (intraday for short ranges, daily for long ranges).

### For Implementers

Read documents in this order:

1. **[overview.md](./overview.md)** - Start here for context and goals
2. **[decisions.md](./decisions.md)** - Understand key architecture decisions (ADRs)
3. **[interval-strategy.md](./interval-strategy.md)** - Learn interval selection rules
4. **[caching-strategy.md](./caching-strategy.md)** - Understand caching for multiple intervals
5. **[data-flow.md](./data-flow.md)** - See sequence diagrams and flows
6. **[implementation-guide.md](./implementation-guide.md)** - Step-by-step implementation plan

### For Reviewers

Key decisions to review:

- **ADR-174-001**: Backend determines interval (not frontend) - [decisions.md](./decisions.md#adr-174-001)
- **ADR-174-002**: Differential caching (daily=persist, intraday=ephemeral) - [decisions.md](./decisions.md#adr-174-002)
- **ADR-174-003**: Progressive enhancement for API tiers - [decisions.md](./decisions.md#adr-174-003)
- **ADR-174-004**: Backward-compatible API changes - [decisions.md](./decisions.md#adr-174-004)

## Problem Summary

**Current State**: All time ranges (1D, 1W, 1M, 3M, 1Y, ALL) display daily closing prices only.

**Desired State**: Show appropriate granularity:
- **1D time range** → 15-minute intraday data (~26 points)
- **1W time range** → 1-hour intraday data (~35 points)  
- **1M+ time ranges** → Daily data (~22-252 points)

**Constraints**:
- Must work with free tier (daily only)
- Must enhance with premium tier (intraday)
- Must not break existing functionality
- Must respect API rate limits

## Solution Summary

### Core Components

| Component | Purpose | Location |
|-----------|---------|----------|
| **IntervalSelector** | Chooses optimal interval based on time range | `backend/src/zebu/application/services/` |
| **AlphaVantageAdapter** | Fetches intraday and daily data | `backend/src/zebu/adapters/outbound/market_data/` |
| **PriceCache** | Caches data with interval-aware keys | `backend/src/zebu/infrastructure/cache/` |
| **Price API** | Accepts optional interval parameter | `backend/src/zebu/adapters/inbound/api/prices.py` |

### Key Design Principles

1. **Backend Determines Interval**: Frontend requests time range, backend chooses best interval
2. **Differential Caching**: Daily data persisted forever, intraday data ephemeral (Redis only)
3. **Progressive Enhancement**: Works on free tier, enhances with premium tier
4. **Backward Compatible**: Optional interval parameter, no breaking changes

### Interval Selection Logic

```
Time Range → Optimal Interval → Fallback Chain

1D (1 day)     → 15min → 30min → 1hour → 1day
1W (7 days)    → 1hour → 1day
1M+ (30+ days) → 1day
```

**Free Tier**: Always falls back to 1day (only available interval)
**Premium Tier**: Uses optimal interval

### Caching Strategy

| Interval | Redis TTL | PostgreSQL | Rationale |
|----------|-----------|------------|-----------|
| 15min, 30min, 1hour | 15min - 1h | ❌ NO | Ephemeral, current day only |
| 1day | 1h - 24h | ✅ YES | Permanent, backtesting required |

**Key Format**: `papertrade:price:{ticker}:{interval}:{date}`

### Implementation Phases

| Phase | Goal | Timeline | Risk |
|-------|------|----------|------|
| **Phase 1** | Infrastructure preparation | 3-5 days | LOW |
| **Phase 2** | Premium tier deployment | 2-3 days | MEDIUM |
| **Phase 3** | Full activation & optimization | 1-2 weeks | LOW |

**Total**: 2-3 weeks from start to full production

## Success Criteria

The architecture design succeeds if:

- ✅ **Incremental Implementation**: Can deploy in phases without breaking changes
- ✅ **Tier-Agnostic Frontend**: Frontend works identically on free or premium tier
- ✅ **API Efficiency**: Reduces API calls through smart caching (target: <30 calls/hour)
- ✅ **Performance**: Charts load <1s for cache hits, <3s for cache misses
- ✅ **Scalability**: Supports new intervals (weekly/monthly) without refactoring
- ✅ **Extensibility**: Supports new features (candlestick charts, technical indicators)

## Document Overview

### [overview.md](./overview.md)

**Purpose**: High-level summary of the problem and solution
**Audience**: Product managers, stakeholders, reviewers
**Length**: ~10 min read

**Contains**:
- Problem statement and context
- Design goals and success criteria
- High-level component interactions
- Terminology and references

### [decisions.md](./decisions.md)

**Purpose**: Architecture Decision Records (ADRs) for key choices
**Audience**: Engineers, architects, reviewers
**Length**: ~20 min read

**Contains**:
- ADR-174-001: Backend-determined interval selection
- ADR-174-002: Differential caching for intervals
- ADR-174-003: Progressive enhancement for API tiers
- ADR-174-004: Backward-compatible API changes

Each ADR includes:
- Context and problem statement
- Decision and rationale
- Alternatives considered
- Consequences (positive, negative, mitigations)

### [interval-strategy.md](./interval-strategy.md)

**Purpose**: Detailed interval selection rules and algorithm
**Audience**: Backend engineers implementing IntervalSelector
**Length**: ~15 min read

**Contains**:
- Interval characteristics (1min, 5min, 15min, 1hour, 1day)
- Selection algorithm (pseudocode and structured tables)
- Edge case handling (weekends, holidays, partial days)
- Performance considerations

### [caching-strategy.md](./caching-strategy.md)

**Purpose**: How different intervals are cached in 3-tier system
**Audience**: Backend engineers, DevOps
**Length**: ~20 min read

**Contains**:
- Cache key structure and format
- TTL rules for each interval type
- Storage estimates (Redis and PostgreSQL)
- Cache warming and invalidation strategies
- Monitoring metrics and targets

### [data-flow.md](./data-flow.md)

**Purpose**: Visual representation of system behavior
**Audience**: All engineers, QA, reviewers
**Length**: ~25 min read

**Contains**:
- 8 detailed sequence diagrams (Mermaid format)
- Scenarios: cache hits, cache misses, free tier, premium tier, rate limits
- Component interaction summary
- Performance optimization strategies

### [implementation-guide.md](./implementation-guide.md)

**Purpose**: Step-by-step instructions for implementation
**Audience**: SWE agents (backend-swe, quality-infra)
**Length**: ~30 min read

**Contains**:
- 3-phase rollout plan with task breakdown
- Detailed task specifications (inputs, outputs, acceptance criteria)
- Testing strategy (unit, integration, performance, E2E)
- Rollback plans for each phase
- Success metrics and post-launch monitoring

## Key Metrics

### Performance Targets

| Metric | Target | Current (Daily Only) | Improvement |
|--------|--------|----------------------|-------------|
| 1D chart data points | 26 (15min) | 1 (daily) | **26x more detail** |
| Chart load time (cache hit) | <100ms | ~100ms | Maintained |
| Chart load time (cache miss) | <3s | ~2s | Acceptable |
| API calls per user per day | <3 | ~5 | **40% reduction** |
| Cache hit rate | >90% | ~85% | **+5%** |

### Business Impact

| Metric | Expected Change |
|--------|-----------------|
| User engagement (chart views) | +20% |
| Support tickets (chart issues) | -50% |
| Infrastructure cost | +$20/month (Redis + premium API) |
| Development cost | ~2-3 weeks engineering time |

**ROI**: Better user experience justifies modest infrastructure cost increase

## Dependencies

### External

- **Alpha Vantage Premium API Key**: Required for Phase 2 (intraday data)
- **Redis**: Already deployed, no changes needed
- **PostgreSQL**: Already deployed, no schema changes

### Internal

- **Existing Caching Infrastructure**: Phase 2 market data caching (ADR-001)
- **Rate Limiter**: Token bucket implementation already exists
- **MarketDataPort**: Interface already supports interval parameter

**Conclusion**: Architecture builds on existing infrastructure, minimal new dependencies

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **Premium API costs exceed budget** | Medium | Medium | Start with 100 tickers, monitor usage, can downgrade |
| **Intraday data quality issues** | Low | Medium | Validate data in tests, alert on anomalies |
| **Cache key collisions** | Low | High | Use interval in key, comprehensive testing |
| **Free tier users see degraded UX** | High | Low | Display message "Upgrade for intraday", still functional |
| **Performance issues with many intervals** | Low | Medium | Monitor cache hit rates, tune TTLs |

**Overall Risk**: LOW - Architecture is conservative, incremental rollout, easy rollback

## Future Enhancements

### Phase 4: Candlestick Charts

Add OHLCV (Open, High, Low, Close, Volume) data to PricePoint:

**Benefit**: Technical analysis, pattern recognition
**Effort**: 1 week (backend + frontend)
**Dependency**: This architecture (intervals support it)

### Phase 5: Real-Time Streaming

Replace polling with WebSocket for live updates:

**Benefit**: Instant price updates, lower API usage
**Effort**: 2 weeks (WebSocket infrastructure + frontend)
**Dependency**: Premium API tier (streaming support)

### Phase 6: Weekly/Monthly Aggregation

Add "1week" and "1month" intervals for very long time ranges:

**Benefit**: Smoother charts for ALL time range (reduce from 1260 to 60 points)
**Effort**: 3 days (backend aggregation logic)
**Dependency**: This architecture (easy extension)

## Questions and Answers

### Q: Why not let frontend specify interval?

**A**: Backend knows API tier capabilities, can gracefully degrade. Frontend would need duplicate logic and tier detection. See [ADR-174-001](./decisions.md#adr-174-001).

### Q: Why not store intraday data in PostgreSQL?

**A**: Storage cost (12M rows vs. 1.2M for daily) doesn't justify value (intraday only useful for current day). See [ADR-174-002](./decisions.md#adr-174-002).

### Q: What if free tier users complain about 1D chart?

**A**: Display message "Upgrade to premium for intraday data". Still shows daily close (functional). Can also show last week's hourly data as preview.

### Q: How do we handle timezone issues?

**A**: All timestamps in UTC. Market hours detection uses ET timezone. Display converts to user's timezone (frontend).

### Q: What if Alpha Vantage changes API?

**A**: MarketDataPort abstraction allows swapping providers. VCR cassettes detect API changes in tests.

## Approval and Sign-Off

### Reviewers

| Role | Reviewer | Status | Date |
|------|----------|--------|------|
| **Architect** | Design Author | ✅ Proposed | 2026-01-25 |
| **Backend Lead** | TBD | ⏳ Pending | - |
| **Frontend Lead** | TBD | ⏳ Pending | - |
| **DevOps** | TBD | ⏳ Pending | - |
| **Product** | TBD | ⏳ Pending | - |

### Review Checklist

- [ ] Architecture aligns with Clean Architecture principles
- [ ] No breaking changes to existing APIs
- [ ] Caching strategy is sound and scalable
- [ ] Performance targets are achievable
- [ ] Implementation plan is realistic
- [ ] Rollback plan is clear
- [ ] Risks are identified and mitigated
- [ ] Documentation is complete

### Next Steps After Approval

1. **Create Implementation Tasks** in project tracker
2. **Assign Backend SWE** to Phase 1 (infrastructure)
3. **Schedule Architecture Review** with team
4. **Obtain Premium API Key** (if not already available)
5. **Set Up Monitoring** (dashboards, alerts)
6. **Begin Phase 1 Implementation**

## Contact

**For Questions About This Plan**:
- Architecture decisions: Review [decisions.md](./decisions.md)
- Implementation details: Review [implementation-guide.md](./implementation-guide.md)
- Technical questions: Review specific document or raise issue

**For Issues During Implementation**:
- Blockers: Escalate to architecture lead
- Bugs: Create issue with "price-granularity" label
- Clarifications: Comment on relevant task

---

**Document Version**: 1.0
**Last Updated**: 2026-01-25
**Next Review**: After Phase 2 completion
