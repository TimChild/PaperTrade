# Task 174: Design Price Data Granularity System

**Agent**: architect
**Priority**: MEDIUM (Planning/Design)
**Type**: Architecture Design Document

## Context

Zebu is a paper trading platform where users view price charts across different time ranges (1D, 1W, 1M, 3M, 1Y, ALL). Currently, all time ranges display daily closing prices. We want to evolve the system to show appropriate data granularity based on the viewing context—for example, intraday data (15-minute intervals) for short time ranges and daily data for longer ranges.

### Current State

- **Frontend**: Users select time ranges via `TimeRangeSelector` (1D, 1W, 1M, 3M, 1Y, ALL)
- **API**: `/api/v1/prices/{ticker}/history` accepts `start`, `end`, and `interval` parameters
- **Backend**: The `interval` parameter flows through the stack but only `1day` is currently fetched from the data provider
- **Data Provider**: Alpha Vantage API (free tier: daily data only; premium tier: intraday at 1min/5min/15min/30min/60min)
- **Caching**: 3-tier caching exists (Redis → PostgreSQL → API) with interval-aware storage

### Upcoming Change

Within a few weeks, we will upgrade to a premium Alpha Vantage API key, unlocking intraday data access. The architecture should be ready to leverage this when available.

## Design Goals

Create a comprehensive architecture design that:

1. **Serves the right data granularity for the viewing context** — Users viewing a 1-day chart should see intraday movement, while users viewing a 1-year chart should see daily closes

2. **Maintains good user experience** — Fast load times, smooth transitions between time ranges, appropriate loading states

3. **Is cost-effective with API usage** — Respects rate limits, caches intelligently, avoids redundant fetches

4. **Supports graceful degradation** — Works well with free tier (daily only) and progressively enhances with premium tier

5. **Is maintainable and extensible** — Clean separation of concerns, easy to add new intervals or data providers in the future

6. **Handles edge cases well** — Market hours, weekends, holidays, gaps in data, timezone considerations

## Questions to Address

The design should thoroughly analyze and provide recommendations for:

### Data Strategy
- What interval should be used for each time range? Is this fixed or should it adapt (e.g., based on available data)?
- How should the frontend request data—should it specify exact intervals or let the backend decide?
- How do we handle the transition period where we have cached daily data but want intraday?

### Caching Architecture
- How should different intervals be cached (TTL, storage, invalidation)?
- Should intraday data be stored permanently or treated as ephemeral?
- How do we handle partial cache hits (e.g., have some days but not others)?

### API Design
- Should the API contract change, or can we work within the existing parameters?
- Should there be a "smart" mode where backend picks optimal interval?
- How do we communicate data limitations to the frontend (e.g., "intraday not available for this range")?

### Frontend Considerations
- How should the chart adapt to different data densities?
- What loading/transition UX makes sense when switching time ranges?
- How do we handle time ranges that span multiple data granularities?

### Rate Limiting & Cost
- How do we balance freshness vs. API call volume?
- Should we pre-fetch popular tickers or fetch on-demand only?
- How do we handle burst scenarios (user rapidly switching time ranges)?

## Deliverables

1. **Architecture Decision Record (ADR)** documenting:
   - Context and problem statement
   - Decision drivers
   - Considered options with pros/cons
   - Recommended approach with rationale

2. **Component Design** showing:
   - Data flow diagrams
   - API contract changes (if any)
   - Caching strategy
   - Frontend state management approach

3. **Implementation Roadmap** with:
   - Phased approach (what can be done now vs. after premium key)
   - Task breakdown with rough effort estimates
   - Dependencies and risks

## Constraints

- Must work with Alpha Vantage API (both free and premium tiers)
- Cannot break existing functionality during rollout
- Should leverage existing caching infrastructure where sensible
- Must handle the paper trading use case (users may look at historical periods for backtesting)

## References

- Current price history hook: `frontend/src/hooks/usePriceHistory.ts`
- Current adapter: `backend/src/zebu/adapters/outbound/market_data/alpha_vantage_adapter.py`
- TimeRange types: `frontend/src/types/price.ts`
- Alpha Vantage docs: https://www.alphavantage.co/documentation/

## Success Criteria

The design document should give us confidence that:
- We can implement incrementally without big-bang changes
- The architecture will scale as we add more features (e.g., candlestick charts, technical indicators)
- We won't paint ourselves into a corner that requires major refactoring later
