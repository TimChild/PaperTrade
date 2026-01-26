# Architecture Decision Records

This document contains all ADRs related to the Price Data Granularity System design.

---

## ADR-174-001: Backend-Determined Interval Selection

**Status**: Proposed
**Date**: 2026-01-25
**Context**: How to decide which interval to use for each time range

### Context

The frontend allows users to select time ranges (1D, 1W, 1M, 3M, 1Y, ALL). We need to determine the appropriate data interval (1min, 5min, 15min, 30min, 1hour, 1day) for each time range.

Three main approaches:
1. **Frontend-specified**: Frontend explicitly passes interval parameter
2. **Backend-determined**: Backend selects optimal interval based on time range
3. **Hybrid**: Frontend can suggest, backend can override

### Decision

**Backend determines optimal interval** based on time range when frontend doesn't specify.

The API contract becomes:
```
GET /api/v1/prices/{ticker}/history?start=X&end=Y&interval={optional}
```

If `interval` is omitted, backend selects based on this mapping:

| Time Range | Days Span | Selected Interval | Data Points (approx) | Rationale |
|------------|-----------|-------------------|----------------------|-----------|
| 1D | 1 | 15min | ~26 | Intraday movement without overwhelming chart |
| 1W | 7 | 1hour | ~35 | Hourly trends, manageable data volume |
| 1M | 30 | 1day | ~22 | Daily closes sufficient for monthly view |
| 3M | 90 | 1day | ~65 | Daily closes sufficient for quarterly view |
| 1Y | 365 | 1day | ~252 | Daily closes for yearly trends |
| ALL | 1825+ | 1day | ~1260 | Daily closes for long-term trends |

If `interval` IS specified, backend uses it (for advanced users, future features).

### Rationale

**Why backend-determined wins:**

1. **Graceful Degradation**: Backend knows API tier capabilities
   - Free tier: Falls back to 1day for all ranges
   - Premium tier: Uses optimal intraday intervals
   - Frontend unchanged regardless of tier

2. **Future-Proofing**: Easy to adjust mappings without frontend changes
   - Add weekly/monthly aggregation later
   - Adjust based on performance metrics
   - A/B test different granularities

3. **Reduced Frontend Complexity**: Frontend expresses user intent (time range), not implementation details
   - No need to duplicate interval selection logic
   - No need to know about API tiers
   - Simpler testing

4. **Optimal Data Volume**: Backend can balance chart quality vs. data size
   - Too many points = slow rendering
   - Too few points = poor visualization
   - Backend can tune per interval

### Consequences

**Positive**:
- ✅ Frontend remains simple (just pass time range)
- ✅ Backend adapts to available data sources
- ✅ Easy to A/B test different interval strategies
- ✅ Advanced users can override via `interval` parameter

**Negative**:
- ⚠️ Frontend doesn't know interval until response arrives
- ⚠️ May need API capability discovery endpoint later
- ⚠️ Interval logic lives in backend (must be documented)

**Mitigations**:
- Frontend receives interval in response, can adapt UI accordingly
- Document interval selection logic in API docs
- Consider `/capabilities` endpoint if needed for advanced features

### Alternatives Considered

**Alternative 1: Frontend-Specified Interval**

| Pros | Cons |
|------|------|
| Frontend has full control | Must duplicate interval logic |
| No surprises for frontend | Must know API tier capabilities |
| Easier to debug | Breaks when tier changes |

**Rejected because**: Too much coupling between frontend and data provider capabilities.

**Alternative 2: Hybrid (Frontend suggests, backend overrides)**

| Pros | Cons |
|------|------|
| Best of both worlds? | Adds complexity |
| Graceful fallback | Confusing for debugging |

**Rejected because**: Adds unnecessary complexity without clear benefit.

---

## ADR-174-002: Differential Caching for Intervals

**Status**: Proposed
**Date**: 2026-01-25
**Context**: How to cache different data intervals

### Context

We need to cache data at multiple intervals (intraday and daily). The existing 3-tier cache (Redis → PostgreSQL → API) needs to handle:
- Intraday data (ephemeral, changes frequently)
- Daily data (permanent, never changes after market close)

Key constraints:
- Intraday data for popular stocks = large volume (96 points/day for 15min interval)
- PostgreSQL storage costs money
- Redis is expensive for long-term storage
- Daily data essential for backtesting (Phase 3)

### Decision

Implement **differential caching strategy** based on interval type:

#### Daily Data (interval = "1day")
- **Redis**: TTL = 1 hour (market hours) or 4 hours (after-hours)
- **PostgreSQL**: Store forever (immutable historical data)
- **Rationale**: Required for backtesting, never changes after market close

#### Intraday Data (interval < "1day")
- **Redis**: TTL = 15 minutes (market hours) or 1 hour (after-hours)
- **PostgreSQL**: **DO NOT STORE** (too much data, ephemeral value)
- **Rationale**: Only useful for real-time charts, not backtesting

#### Cache Keys
Use interval-aware keys to prevent collisions:
```
papertrade:price:{ticker}:{interval}:{date}
```

Examples:
- `papertrade:price:AAPL:1day:2026-01-25`
- `papertrade:price:AAPL:15min:2026-01-25`

### Rationale

**Why differential caching:**

1. **Storage Efficiency**
   - Daily data for 1000 tickers × 5 years = ~1.2M rows (manageable)
   - 15min data for 1000 tickers × 5 years = ~12M rows (expensive)
   - Intraday data only useful for current day (not backtesting)

2. **Cost Optimization**
   - PostgreSQL storage costs per GB
   - Intraday data has low long-term value
   - Redis is sufficient for real-time use

3. **Performance**
   - Intraday queries hit Redis (fast)
   - Historical queries hit PostgreSQL (daily only)
   - No need to query large intraday tables

4. **TTL Alignment**
   - Intraday data stale after 15min during market hours
   - Daily data stale after 1 hour (or next market open)
   - TTLs reflect actual data freshness

### Cache Flow for Intraday Request

```
Request: 1D time range (backend selects 15min interval)
  ↓
Check Redis: papertrade:price:AAPL:15min:2026-01-25
  ├─ HIT: Return immediately (<100ms)
  └─ MISS: ↓
Check PostgreSQL: SKIP (intraday not stored)
  ↓
Check Rate Limiter
  ├─ Tokens available: ↓
  │   Call Alpha Vantage TIME_SERIES_INTRADAY (15min)
  │     ├─ SUCCESS: Cache in Redis (TTL: 15min), return
  │     └─ ERROR: Return error (no fallback)
  └─ No tokens: Return error OR downgrade to 1day
```

### Cache Flow for Daily Request

```
Request: 1Y time range (backend selects 1day interval)
  ↓
Check Redis: papertrade:price:AAPL:1day:2026-01-25
  ├─ HIT: Return immediately (<100ms)
  └─ MISS: ↓
Check PostgreSQL: SELECT WHERE interval='1day'
  ├─ HIT (fresh): Warm Redis, return (<500ms)
  ├─ HIT (stale): ↓
  └─ MISS: ↓
Call Alpha Vantage TIME_SERIES_DAILY
  ├─ SUCCESS: Store in PostgreSQL, cache in Redis, return
  └─ ERROR: Return stale data OR error
```

### Consequences

**Positive**:
- ✅ Storage costs contained (no massive intraday tables)
- ✅ Fast intraday queries (Redis-only)
- ✅ Historical backtesting unaffected (daily data preserved)
- ✅ Clear separation of ephemeral vs. permanent data

**Negative**:
- ⚠️ No historical intraday data (can't backtest with 15min bars)
- ⚠️ Intraday cache misses require API call (no DB fallback)
- ⚠️ Different code paths for different intervals

**Mitigations**:
- Document clearly: "Intraday data for current day only"
- If historical intraday needed (future): Add separate intraday table with retention policy
- Fallback to 1day interval if intraday unavailable

### Alternatives Considered

**Alternative 1: Store Everything**

| Pros | Cons |
|------|------|
| Complete historical data | Massive storage costs |
| Can backtest with any interval | Slow queries on huge tables |
| Simple (same logic for all) | Intraday data rarely used historically |

**Rejected because**: Storage costs exceed value (intraday backtesting unlikely in Phase 3)

**Alternative 2: Time-Based Retention (e.g., keep last 30 days of intraday)**

| Pros | Cons |
|------|------|
| Some historical intraday | Complex retention logic |
| Supports short-term backtesting | Still expensive |

**Rejected because**: Adds complexity without clear use case (Phase 3 uses daily data)

---

## ADR-174-003: Progressive Enhancement for API Tiers

**Status**: Proposed
**Date**: 2026-01-25
**Context**: How to handle free tier (daily only) vs. premium tier (intraday)

### Context

Alpha Vantage free tier only provides daily data. Premium tier unlocks intraday intervals. We need an architecture that:
- Works perfectly with free tier
- Progressively enhances when premium tier is available
- Doesn't break when downgrading tiers
- Requires minimal configuration changes

### Decision

Implement **capability-based progressive enhancement**:

1. **Capability Detection**
   - Backend queries Alpha Vantage to detect supported intervals
   - Cached in Redis for 24 hours
   - Fallback to configuration if detection fails

2. **Interval Selection with Fallback**
   - Attempt to use optimal interval (e.g., 15min for 1D)
   - If interval not available: fall back to next-best available
   - Always fall back to 1day (guaranteed available)

3. **Transparent to Frontend**
   - Frontend requests time range, backend handles tier limitations
   - Response includes actual interval used
   - No error states for "unavailable interval"

### Capability Detection

```
Configuration file (config.toml):
[market_data.alpha_vantage]
tier = "free"  # or "premium"
supported_intervals = ["1day"]  # or ["1min", "5min", "15min", "30min", "60min", "1day"]
```

Capability query (runs on startup and cached):
```
Try calling TIME_SERIES_INTRADAY endpoint
  ├─ SUCCESS: Premium tier detected
  │   supported_intervals = ["1min", "5min", "15min", "30min", "60min", "1day"]
  └─ FAILURE (error message contains "premium only"):
      Free tier detected
      supported_intervals = ["1day"]
```

### Interval Selection Algorithm

```
def select_interval(time_range: TimeRange, available_intervals: List[str]) -> str:
    # Optimal interval mapping
    optimal = {
        "1D": "15min",
        "1W": "1hour", 
        "1M": "1day",
        "3M": "1day",
        "1Y": "1day",
        "ALL": "1day",
    }
    
    # Fallback chain
    fallbacks = {
        "15min": ["30min", "1hour", "1day"],
        "30min": ["1hour", "1day"],
        "1hour": ["1day"],
        "1day": [],  # Always available
    }
    
    desired = optimal[time_range]
    
    # Try desired interval
    if desired in available_intervals:
        return desired
    
    # Try fallbacks in order
    for fallback in fallbacks[desired]:
        if fallback in available_intervals:
            return fallback
    
    # Ultimate fallback
    return "1day"
```

### Behavior Examples

**Example 1: Free Tier, 1D Time Range**
```
User selects: 1D
Optimal interval: 15min
Available intervals: ["1day"]
Fallback chain: 15min → 30min → 1hour → 1day
Selected: 1day
Result: 1 data point (previous day's close)
UX: Still functional, just less granular
```

**Example 2: Premium Tier, 1D Time Range**
```
User selects: 1D
Optimal interval: 15min
Available intervals: ["1min", "5min", "15min", "30min", "60min", "1day"]
Selected: 15min
Result: ~26 data points (intraday movement)
UX: Rich intraday chart
```

**Example 3: Premium Tier Degraded to Free**
```
User selects: 1D
Optimal interval: 15min
API call fails with "premium only" error
Backend detects tier downgrade
Updates cached capabilities: ["1day"]
Retries with fallback: 1day
Selected: 1day
Result: Graceful degradation, no error
```

### Consequences

**Positive**:
- ✅ Zero code changes when upgrading tier (just config)
- ✅ No errors when downgrading tier (graceful fallback)
- ✅ Frontend unaware of backend capabilities
- ✅ Easy to test both tiers without API key changes

**Negative**:
- ⚠️ Free tier provides poor UX for 1D time range (1 data point)
- ⚠️ Capability detection adds startup complexity
- ⚠️ Cached capabilities may become stale

**Mitigations**:
- Document free tier limitations clearly
- Display message in UI: "Upgrade for intraday data"
- Refresh capability cache on API errors
- Manual override via configuration

### Alternatives Considered

**Alternative 1: Hardcode Tier in Configuration**

| Pros | Cons |
|------|------|
| Simple, no detection logic | Manual configuration required |
| No runtime errors | Can become stale |
| Easy to test | Error-prone (forget to update) |

**Rejected because**: Requires manual intervention on tier changes (error-prone)

**Alternative 2: Try-Catch on Every Request**

| Pros | Cons |
|------|------|
| Always accurate | Extra API call overhead |
| No capability cache | Wastes rate limit quota |

**Rejected because**: Inefficient, burns API quota unnecessarily

---

## ADR-174-004: API Contract Backward Compatibility

**Status**: Proposed
**Date**: 2026-01-25
**Context**: How to change API without breaking existing clients

### Context

Current API contract:
```
GET /api/v1/prices/{ticker}/history?start=X&end=Y&interval={optional}
```

Frontend currently:
- Always passes `interval=1day` implicitly (not in URL)
- Expects response with daily data

We need to:
- Enable backend interval selection (omit interval)
- Maintain backward compatibility for explicit `interval` parameter
- Not break existing frontend

### Decision

**Make `interval` parameter truly optional with backward-compatible defaults**:

1. **Request**: `interval` parameter becomes optional
   - If provided: Use that interval (existing behavior)
   - If omitted: Backend selects optimal interval (NEW)

2. **Response**: Always include actual `interval` in response
   - Existing field: `interval: string`
   - Frontend can check what interval was used

3. **Frontend Migration**: Two-phase approach
   - Phase 1: Frontend continues passing `interval=1day` (no change)
   - Phase 2: Frontend stops passing interval, lets backend choose

### API Contract

**Before (Current)**:
```typescript
GET /api/v1/prices/AAPL/history?start=2026-01-20&end=2026-01-25

// Backend assumes interval=1day if omitted
// Response always has interval="1day"
```

**After (Proposed)**:
```typescript
GET /api/v1/prices/AAPL/history?start=2026-01-20&end=2026-01-25

// Backend selects optimal interval based on date range
// Response includes actual interval used

Response:
{
  "ticker": "AAPL",
  "prices": [...],
  "start": "2026-01-20T00:00:00Z",
  "end": "2026-01-25T23:59:59Z",
  "interval": "15min",  // ← Backend selected this
  "count": 130
}
```

**Backward Compatible**:
```typescript
GET /api/v1/prices/AAPL/history?start=2026-01-20&end=2026-01-25&interval=1day

// Backend honors explicit interval parameter
// Response has interval="1day" as requested
```

### Migration Strategy

**Phase 1: Backend Preparation** (Week 1)
- Add interval selection logic to backend
- Default to "1day" when omitted (no behavior change)
- Deploy to production (no impact)

**Phase 2: Backend Activation** (Week 2)
- Enable smart interval selection
- Frontend still passes `interval=1day` explicitly
- Test with internal users

**Phase 3: Frontend Simplification** (Week 3)
- Remove `interval` parameter from frontend requests
- Backend selects optimal interval
- Frontend adapts chart to received interval

### Consequences

**Positive**:
- ✅ Zero breaking changes
- ✅ Incremental rollout (low risk)
- ✅ Frontend can migrate at own pace
- ✅ Advanced users can still specify interval

**Negative**:
- ⚠️ Transition period with both modes active
- ⚠️ Must maintain both code paths temporarily

**Mitigations**:
- Document migration clearly
- Feature flag for interval selection
- Monitor both request patterns

### Alternatives Considered

**Alternative 1: New API Version (/v2/prices)**

| Pros | Cons |
|------|------|
| Clean separation | API version sprawl |
| No backward compat complexity | Must maintain two APIs |

**Rejected because**: Overkill for backward-compatible change

**Alternative 2: New Parameter (`auto_interval=true`)**

| Pros | Cons |
|------|------|
| Explicit opt-in | Extra parameter |
| Clear intent | Awkward API design |

**Rejected because**: Optional parameter achieves same goal more elegantly

---

## Summary of Decisions

| ADR | Decision | Impact |
|-----|----------|--------|
| 174-001 | Backend determines interval | Frontend simplified, backend flexible |
| 174-002 | Differential caching (daily=persist, intraday=ephemeral) | Storage efficient, clear data lifecycle |
| 174-003 | Progressive enhancement with capability detection | Works on free tier, enhances on premium |
| 174-004 | Backward-compatible optional interval parameter | Zero breaking changes, incremental migration |

These decisions work together to create a system that:
- **Works today** (free tier, daily data only)
- **Enhances tomorrow** (premium tier, intraday data)
- **Scales long-term** (new intervals, new providers)
- **Maintains simplicity** (frontend unchanged, backend adapts)
