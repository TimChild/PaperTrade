# Implementation Guide

This guide provides step-by-step instructions for implementing the Price Data Granularity System.

## Overview

The implementation is structured in **three phases** to minimize risk and enable incremental delivery:

- **Phase 1: Infrastructure Preparation** - Backend changes with no behavior impact
- **Phase 2: Premium Tier Deployment** - Enable intraday data with feature flag
- **Phase 3: Full Activation** - Remove feature flags, optimize, monitor

## Prerequisites

Before starting implementation:

- [x] Read all architecture documents in this plan
- [x] Understand existing caching infrastructure (ADR-001)
- [x] Understand current Alpha Vantage adapter implementation
- [x] Have access to staging environment for testing
- [ ] Premium Alpha Vantage API key available (Phase 2)

## Phase 1: Infrastructure Preparation

**Goal**: Prepare backend to support multiple intervals without changing behavior

**Timeline**: 3-5 days
**Risk**: LOW (no behavior changes)

### Task 1.1: Create IntervalSelector Service

**Location**: `backend/src/zebu/application/services/interval_selector.py`

**Specification**:

| Component | Type | Description |
|-----------|------|-------------|
| **Class** | IntervalSelector | Service for selecting optimal interval |
| **Methods** | - | - |
| select_interval | time_range: str, available_intervals: List[str] → str | Selects optimal interval with fallback |
| get_available_intervals | api_tier: str → List[str] | Returns supported intervals for API tier |

**Logic**:

```
Based on time range days span:
  0-1 days → "15min"
  2-7 days → "1hour"
  8+ days → "1day"

Fallback chain:
  "15min" → ["30min", "1hour", "1day"]
  "30min" → ["1hour", "1day"]
  "1hour" → ["1day"]
  "1day" → [] (always available)
```

**Testing**:
- Unit tests for all time range mappings
- Unit tests for fallback chains
- Unit tests for free vs. premium tier

**Acceptance Criteria**:
- [ ] All unit tests passing
- [ ] Service follows Clean Architecture (no infrastructure dependencies)
- [ ] Documented with docstrings
- [ ] Type hints on all methods

### Task 1.2: Update Price API Endpoint

**Location**: `backend/src/zebu/adapters/inbound/api/prices.py`

**Changes**:

| Change | Type | Description |
|--------|------|-------------|
| Make `interval` parameter optional | Modify | Default to None instead of "1day" |
| Add interval selection logic | Add | Call IntervalSelector when interval not provided |
| Update response to include selected interval | Modify | Already exists, just document behavior |

**Logic**:

```
IF interval parameter provided:
    Use that interval (existing behavior)
ELSE:
    Calculate time range from start/end dates
    available_intervals = IntervalSelector.get_available_intervals(current_tier)
    interval = IntervalSelector.select_interval(time_range, available_intervals)
```

**Testing**:
- API tests with explicit interval (backward compatibility)
- API tests without interval (new behavior)
- API tests for each time range

**Acceptance Criteria**:
- [ ] Backward compatible (existing clients unaffected)
- [ ] All API tests passing
- [ ] OpenAPI spec updated

### Task 1.3: Implement Capability Detection

**Location**: `backend/src/zebu/adapters/outbound/market_data/alpha_vantage_adapter.py`

**Changes**:

| Change | Type | Description |
|--------|------|-------------|
| Add `detect_capabilities()` method | Add | Queries API to determine tier |
| Cache capabilities in Redis | Add | TTL: 24 hours |
| Add configuration override | Add | Allow manual tier specification |

**Logic**:

```
On adapter initialization:
  IF config.alpha_vantage.tier is set:
      Use configured tier
  ELSE:
      Try to detect tier via test API call:
          Call TIME_SERIES_INTRADAY with 1min interval
          IF success:
              Tier = "premium"
          ELSE IF error contains "premium":
              Tier = "free"
          ELSE:
              Tier = "unknown" (default to free)
```

**Configuration**:

Add to `backend/config.toml`:
```toml
[market_data.alpha_vantage]
tier = "auto"  # Options: "auto", "free", "premium"
```

**Testing**:
- Unit tests for detection logic (mocked HTTP responses)
- Integration tests with VCR cassettes (both tiers)
- Test configuration overrides

**Acceptance Criteria**:
- [ ] Capability detection works for free tier
- [ ] Capability detection works for premium tier
- [ ] Configuration override works
- [ ] Cached in Redis with 24-hour TTL

### Task 1.4: Update Cache Key Structure

**Location**: `backend/src/zebu/infrastructure/cache/price_cache.py`

**Changes**:

| Change | Type | Description |
|--------|------|-------------|
| Update cache key format | Modify | Include interval in key |
| Update TTL logic | Modify | Different TTLs for different intervals |
| Add market hours detection | Add | Helper to determine if market is open |

**New Key Format**:
```
Old: papertrade:price:{ticker}:{date}
New: papertrade:price:{ticker}:{interval}:{date}
```

**TTL Logic**:

| Interval | Market Hours | After Hours | Historical |
|----------|--------------|-------------|------------|
| 15min, 30min, 1hour | 15 min | 1 hour | Not cached |
| 1day (today) | 1 hour | 4 hours | - |
| 1day (historical) | 24 hours | 24 hours | 24 hours |

**Testing**:
- Unit tests for key generation
- Unit tests for TTL calculation
- Integration tests for cache operations

**Acceptance Criteria**:
- [ ] New key format works
- [ ] TTL logic correct for all scenarios
- [ ] Backward compatible (old keys still work during migration)

### Task 1.5: Update Alpha Vantage Adapter for Intraday

**Location**: `backend/src/zebu/adapters/outbound/market_data/alpha_vantage_adapter.py`

**Changes**:

| Change | Type | Description |
|--------|------|-------------|
| Add `_fetch_intraday_data()` method | Add | Call TIME_SERIES_INTRADAY endpoint |
| Update `get_price_history()` | Modify | Route to intraday or daily based on interval |
| Update caching logic | Modify | Don't store intraday in PostgreSQL |

**Routing Logic**:

```
IF interval == "1day":
    Use existing _fetch_daily_data() method
    Store in PostgreSQL + Redis
ELSE:  # Intraday intervals
    Use new _fetch_intraday_data() method
    Store in Redis only (NOT PostgreSQL)
```

**API Endpoints**:

| Interval | Alpha Vantage Endpoint | Parameters |
|----------|------------------------|------------|
| 1min | TIME_SERIES_INTRADAY | interval=1min, outputsize=full |
| 5min | TIME_SERIES_INTRADAY | interval=5min, outputsize=full |
| 15min | TIME_SERIES_INTRADAY | interval=15min, outputsize=full |
| 30min | TIME_SERIES_INTRADAY | interval=30min, outputsize=full |
| 60min | TIME_SERIES_INTRADAY | interval=60min, outputsize=full |
| 1day | TIME_SERIES_DAILY | outputsize=full |

**Testing**:
- Unit tests with mocked API responses
- VCR cassettes for each interval
- Test error handling (premium tier required)

**Acceptance Criteria**:
- [ ] Intraday data fetching works
- [ ] Intraday data NOT stored in PostgreSQL
- [ ] Daily data still stored in PostgreSQL
- [ ] Rate limiting respected
- [ ] All tests passing

### Phase 1 Completion Checklist

- [ ] All tasks 1.1-1.5 complete
- [ ] All unit tests passing
- [ ] All integration tests passing
- [ ] No behavior changes (still returns daily data for all requests)
- [ ] Code reviewed and approved
- [ ] Deployed to staging environment
- [ ] Smoke tested on staging

**Phase 1 Deliverable**: Backend infrastructure ready, no user-visible changes

---

## Phase 2: Premium Tier Deployment

**Goal**: Enable intraday data with premium API key

**Timeline**: 2-3 days
**Risk**: MEDIUM (new behavior, API usage)

### Task 2.1: Deploy Premium API Key

**Actions**:

1. Update environment variable:
   ```
   ALPHA_VANTAGE_API_KEY=<premium-key>
   ```

2. Update configuration:
   ```toml
   [market_data.alpha_vantage]
   tier = "premium"  # Or leave as "auto" for detection
   ```

3. Restart backend services

**Testing**:
- Verify capability detection returns "premium"
- Verify supported_intervals includes intraday options
- Test API rate limits (75 calls/min)

**Acceptance Criteria**:
- [ ] Premium key deployed to staging
- [ ] Capability detection confirms premium tier
- [ ] Rate limits updated

### Task 2.2: Enable Feature Flag

**Location**: `backend/config.toml`

**Add Feature Flag**:
```toml
[features]
intraday_data = false  # Start disabled
```

**Modify IntervalSelector**:
```
IF config.features.intraday_data is False:
    # Force all intervals to 1day (Phase 1 behavior)
    available_intervals = ["1day"]
ELSE:
    # Use actual capabilities
    available_intervals = detect_capabilities()
```

**Testing**:
- Test with flag disabled (Phase 1 behavior)
- Test with flag enabled (new behavior)
- Verify no impact when disabled

**Acceptance Criteria**:
- [ ] Feature flag works
- [ ] Disabled = Phase 1 behavior
- [ ] Enabled = intraday data flows

### Task 2.3: Selective Activation (Staging)

**Enable for Specific Tickers**:

```toml
[features]
intraday_data = true
intraday_tickers = ["AAPL", "MSFT"]  # Test with 2 tickers first
```

**Logic**:
```
IF ticker in config.features.intraday_tickers:
    Use intraday intervals (15min, 1hour, etc.)
ELSE:
    Force 1day interval (safe fallback)
```

**Testing**:
- Request AAPL with 1D range → should get 15min data
- Request GOOGL with 1D range → should get 1day data
- Verify API usage stays within limits

**Acceptance Criteria**:
- [ ] Selective activation works
- [ ] AAPL/MSFT show intraday data
- [ ] Other tickers still use daily
- [ ] No errors or crashes

### Task 2.4: Monitor API Usage

**Metrics to Track**:

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| API calls per hour | <50 | >60 |
| API quota remaining | >1000/day | <500/day |
| Cache hit rate (intraday) | >70% | <50% |
| Response time (p95) | <2s | >5s |
| Error rate | <1% | >5% |

**Actions**:
- Add Datadog/CloudWatch monitoring
- Create dashboard for API metrics
- Set up alerts for threshold violations

**Acceptance Criteria**:
- [ ] Monitoring dashboard created
- [ ] Alerts configured
- [ ] Daily report of API usage

### Task 2.5: Gradual Rollout (Staging)

**Week 1**: 2 tickers (AAPL, MSFT)
**Week 2**: 10 tickers (add GOOGL, AMZN, TSLA, etc.)
**Week 3**: 50 tickers
**Week 4**: All tickers (remove feature flag)

**Criteria for Expansion**:
- [ ] No increase in error rate
- [ ] API usage within limits
- [ ] Cache hit rate acceptable
- [ ] User feedback positive (if any)

### Phase 2 Completion Checklist

- [ ] All tasks 2.1-2.5 complete
- [ ] Premium API key deployed
- [ ] Feature flag tested
- [ ] Monitoring in place
- [ ] Gradual rollout successful
- [ ] No P0/P1 issues
- [ ] Deployed to production (limited rollout)

**Phase 2 Deliverable**: Intraday data available for select tickers

---

## Phase 3: Full Activation

**Goal**: Enable intraday for all tickers, optimize, monitor

**Timeline**: 1-2 weeks
**Risk**: LOW (proven in Phase 2)

### Task 3.1: Remove Feature Flags

**Changes**:

1. Remove feature flag from config
2. Remove ticker whitelist
3. Clean up conditional logic

**Acceptance Criteria**:
- [ ] Feature flag removed
- [ ] All tickers use optimal intervals
- [ ] Code simplified

### Task 3.2: Frontend Updates (Optional)

**Location**: `frontend/src/hooks/usePriceHistory.ts`

**Changes**:

| Change | Type | Description |
|--------|------|-------------|
| Remove explicit interval parameter | Modify | Let backend choose |
| Add interval indicator in UI | Add | Show "15-minute data" in chart subtitle |
| Add loading state for interval changes | Add | Skeleton loader during refetch |

**Testing**:
- Test all time ranges (1D, 1W, 1M, 3M, 1Y, ALL)
- Verify interval indicator displays correctly
- Test loading states

**Acceptance Criteria**:
- [ ] Frontend simplified
- [ ] Interval indicator works
- [ ] Loading states smooth

### Task 3.3: Optimize Cache Warming

**Strategy**:

Run daily job at midnight to pre-fetch:
- Top 100 tickers (daily data for last 30 days)
- Top 20 tickers (15min data for today)

**Benefits**:
- Reduced first-request latency
- Better cache hit rates
- Predictable API usage

**Acceptance Criteria**:
- [ ] Cache warming job scheduled
- [ ] Pre-fetches complete before market open
- [ ] Cache hit rates improved

### Task 3.4: Performance Optimization

**Targets**:

| Metric | Current | Target | Optimization |
|--------|---------|--------|--------------|
| Redis hit rate (15min) | 70% | >80% | Longer TTL during low volatility |
| API calls per hour | 50 | <30 | Better cache warming |
| Response time (p95) | 2s | <1s | Parallel cache lookups |

**Actions**:
- Implement parallel cache key lookups
- Tune TTLs based on volatility
- Pre-fetch during low-traffic periods

**Acceptance Criteria**:
- [ ] All targets met
- [ ] No performance regressions

### Task 3.5: Documentation

**Documents to Create/Update**:

| Document | Location | Content |
|----------|----------|---------|
| API docs | `docs/api/prices.md` | Interval selection behavior |
| User guide | `docs/user-guide.md` | What intervals mean |
| Runbook | `docs/operations/runbook.md` | Troubleshooting guide |
| Architecture docs | `docs/architecture/` | This implementation |

**Acceptance Criteria**:
- [ ] All docs written
- [ ] Reviewed for accuracy
- [ ] Published

### Phase 3 Completion Checklist

- [ ] All tasks 3.1-3.5 complete
- [ ] Feature fully rolled out
- [ ] Performance targets met
- [ ] Documentation complete
- [ ] Monitoring stable
- [ ] User feedback collected

**Phase 3 Deliverable**: Production-ready price data granularity system

---

## Testing Strategy

### Unit Tests

**Coverage Targets**: >90%

| Component | Test Cases |
|-----------|------------|
| IntervalSelector | Time range mappings, fallback chains, tier detection |
| PriceCache | Key generation, TTL calculation, market hours detection |
| AlphaVantageAdapter | Intraday fetching, routing logic, error handling |
| API endpoint | Parameter validation, interval selection, response format |

### Integration Tests

**Scenarios**:

| Scenario | Time Range | Expected Interval | Expected Behavior |
|----------|------------|-------------------|-------------------|
| Free tier 1D | 1D | 1day | Single point (fallback) |
| Premium 1D | 1D | 15min | ~26 points |
| Premium 1W | 1W | 1hour | ~35 points |
| Premium 1M | 1M | 1day | ~22 points |

### Performance Tests

**Load Testing**:

| Test | Load | Expected Response Time |
|------|------|------------------------|
| Cache hit (1day) | 100 req/s | <100ms (p95) |
| Cache miss (1day) | 10 req/s | <2s (p95) |
| Cache hit (15min) | 100 req/s | <100ms (p95) |
| Cache miss (15min) | 5 req/s | <3s (p95) |

### E2E Tests

**User Journeys**:

1. View portfolio → See real-time values (1day data)
2. Click 1D chart → See intraday movement (15min data)
3. Click 1W chart → See hourly trends (1hour data)
4. Click 1Y chart → See daily closes (1day data)

---

## Rollback Plan

### Phase 1 Rollback

**Risk**: Infrastructure changes cause issues

**Action**:
1. Revert code changes via git
2. Redeploy previous version
3. Verify system stable

**Time**: <30 minutes

### Phase 2 Rollback

**Risk**: Premium tier causes API quota issues

**Action**:
1. Disable feature flag: `intraday_data = false`
2. Restart services (no code changes needed)
3. Verify system falls back to daily data

**Time**: <5 minutes

### Phase 3 Rollback

**Risk**: Full rollout causes performance issues

**Action**:
1. Re-enable feature flag with limited tickers
2. Investigate and fix root cause
3. Re-roll out gradually

**Time**: <10 minutes

---

## Success Metrics

### Quantitative

| Metric | Baseline (current) | Target (Phase 3) |
|--------|--------------------|------------------|
| 1D chart data points | 1 | 26 (15min) |
| API calls per user per day | 5 | <3 (better caching) |
| Cache hit rate | 85% (daily) | >90% (all intervals) |
| Response time (p95) | 1.5s | <1s |
| User engagement (chart views) | Baseline | +20% |

### Qualitative

- [ ] Users report better 1D chart experience
- [ ] No increase in support tickets
- [ ] Engineering team confident in system
- [ ] Documentation clear and complete

---

## Post-Launch

### Week 1

- Monitor metrics daily
- Fix any P0/P1 issues immediately
- Collect user feedback

### Week 2-4

- Analyze API usage patterns
- Optimize cache TTLs based on data
- A/B test interval selections if needed

### Month 2+

- Evaluate premium API cost vs. value
- Consider additional intervals (weekly/monthly aggregation)
- Plan for Phase 4 features (candlestick charts, technical indicators)

---

## Contact and Support

**For Implementation Questions**:
- Architecture: Review this plan and ADRs
- Backend: Check Alpha Vantage adapter code
- Frontend: Check usePriceHistory hook

**For Issues**:
- P0 (system down): Rollback immediately
- P1 (degraded): Investigate, rollback if needed
- P2 (minor): Fix in next sprint
