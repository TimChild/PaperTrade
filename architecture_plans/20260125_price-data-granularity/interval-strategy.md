# Interval Selection Strategy

This document defines the detailed rules for selecting data intervals based on time ranges.

## Overview

The backend automatically selects optimal data intervals when the frontend doesn't specify one. This selection balances:
- **Chart quality**: Enough data points for smooth visualization
- **Performance**: Not so many points that charts render slowly
- **API efficiency**: Minimize redundant fetches
- **User experience**: Appropriate granularity for the viewing context

## Interval Selection Mapping

### Primary Mapping Table

| Time Range | Days Span | Optimal Interval | Data Points (Market Hours) | Chart Density | API Calls (cache miss) |
|------------|-----------|------------------|----------------------------|---------------|------------------------|
| **1D** | 1 | **15min** | 26 (6.5 hours × 4 per hour) | ████████ Good | 1 call |
| **1W** | 7 | **1hour** | 35 (7 days × ~5 market hours) | ████████ Good | 1 call |
| **1M** | 30 | **1day** | 22 (30 days × ~0.73 trading days) | ████████ Good | 1 call |
| **3M** | 90 | **1day** | 65 (90 days × ~0.73 trading days) | ████████ Good | 1 call |
| **1Y** | 365 | **1day** | 252 (365 days × ~0.69 trading days) | ████████ Good | 1 call |
| **ALL** | 1825 | **1day** | 1260 (5 years × 252 trading days) | ██████ Acceptable | 1 call |

**Notes**:
- Market hours: 6.5 hours/day (9:30 AM - 4:00 PM ET)
- Trading days: ~252 per year (~21 per month)
- Data points assume full market coverage (actual may vary with weekends/holidays)

### Fallback Chain

When optimal interval is unavailable, fall back in this order:

| Optimal | 1st Fallback | 2nd Fallback | 3rd Fallback | Ultimate Fallback |
|---------|--------------|--------------|--------------|-------------------|
| 15min | 30min | 1hour | 1day | 1day |
| 30min | 1hour | 1day | - | 1day |
| 1hour | 1day | - | - | 1day |
| 1day | - | - | - | 1day |

**Guarantee**: `1day` is always available (even on free tier), so fallback chain always succeeds.

## Detailed Interval Characteristics

### 1min Interval (Not Used Currently)

| Property | Value |
|----------|-------|
| **Use Case** | High-frequency trading, tick-level analysis |
| **Data Points (1D)** | ~390 (6.5 hours × 60 minutes) |
| **API Cost** | Very high (large responses) |
| **Cache TTL** | 1 minute (very ephemeral) |
| **Storage** | NOT stored in PostgreSQL |
| **Alpha Vantage** | Premium tier only |
| **When to Use** | Future feature (day trading simulator) |

**Why not used now**: Too much data for typical chart rendering, high API cost, limited value for paper trading

### 5min Interval (Not Used Currently)

| Property | Value |
|----------|-------|
| **Use Case** | Intraday trading, short-term patterns |
| **Data Points (1D)** | ~78 (6.5 hours × 12 per hour) |
| **API Cost** | High (large responses) |
| **Cache TTL** | 5 minutes |
| **Storage** | NOT stored in PostgreSQL |
| **Alpha Vantage** | Premium tier only |
| **When to Use** | Alternative to 15min if user wants more detail |

**Why not used now**: 15min provides sufficient granularity for 1D view without overwhelming chart

### 15min Interval ⭐ (Primary Intraday)

| Property | Value |
|----------|-------|
| **Use Case** | 1-day time range, intraday price movements |
| **Data Points (1D)** | ~26 (6.5 hours × 4 per hour) |
| **API Cost** | Medium (reasonable response size) |
| **Cache TTL** | 15 minutes (market hours), 1 hour (after-hours) |
| **Storage** | NOT stored in PostgreSQL |
| **Alpha Vantage** | Premium tier only |
| **When to Use** | Default for 1D time range |

**Why this is optimal**:
- ✅ Enough points to show intraday movement (26 points)
- ✅ Not so many that chart is cluttered
- ✅ Single API call per cache miss
- ✅ Good balance of detail vs. performance

### 30min Interval

| Property | Value |
|----------|-------|
| **Use Case** | Fallback for 15min, slightly less detail |
| **Data Points (1D)** | ~13 (6.5 hours × 2 per hour) |
| **API Cost** | Medium |
| **Cache TTL** | 30 minutes (market hours), 1 hour (after-hours) |
| **Storage** | NOT stored in PostgreSQL |
| **Alpha Vantage** | Premium tier only |
| **When to Use** | Fallback if 15min unavailable |

**Why not primary**: 13 points is borderline too few for smooth 1D chart

### 1hour Interval

| Property | Value |
|----------|-------|
| **Use Case** | 1-week time range, multi-day trends |
| **Data Points (1W)** | ~35 (7 days × 5 market hours) |
| **API Cost** | Medium |
| **Cache TTL** | 1 hour (market hours), 4 hours (after-hours) |
| **Storage** | NOT stored in PostgreSQL |
| **Alpha Vantage** | Premium tier only |
| **When to Use** | Default for 1W time range |

**Why this is optimal**:
- ✅ Shows hourly trends across a week
- ✅ 35 points = good chart density
- ✅ Captures market open/close patterns
- ✅ Reasonable API response size

### 1day Interval ⭐ (Primary Historical)

| Property | Value |
|----------|-------|
| **Use Case** | All time ranges ≥ 1M, historical analysis, backtesting |
| **Data Points (1M)** | ~22 trading days |
| **Data Points (1Y)** | ~252 trading days |
| **API Cost** | Low (daily endpoint optimized) |
| **Cache TTL** | 1 hour (market hours), 4 hours (after-hours) |
| **Storage** | ✅ ALWAYS stored in PostgreSQL |
| **Alpha Vantage** | Free and premium tiers |
| **When to Use** | Default for 1M, 3M, 1Y, ALL; fallback for all intervals |

**Why this is optimal**:
- ✅ Available on both free and premium tiers
- ✅ Provides sufficient granularity for long-term analysis
- ✅ Required for backtesting (Phase 3)
- ✅ Stored permanently for historical queries
- ✅ Immutable after market close (cache-friendly)

## Selection Algorithm

### Pseudocode

```
FUNCTION select_interval(time_range, start_date, end_date, available_intervals):
    # Calculate time span
    days_span = (end_date - start_date).days
    
    # Define optimal mappings based on days span
    IF days_span <= 1:
        optimal = "15min"
    ELSE IF days_span <= 7:
        optimal = "1hour"
    ELSE:
        optimal = "1day"
    
    # Try optimal interval
    IF optimal IN available_intervals:
        RETURN optimal
    
    # Fallback chain
    fallbacks = {
        "15min": ["30min", "1hour", "1day"],
        "30min": ["1hour", "1day"],
        "1hour": ["1day"],
        "1day": []
    }
    
    FOR fallback IN fallbacks[optimal]:
        IF fallback IN available_intervals:
            RETURN fallback
    
    # Ultimate fallback (always available)
    RETURN "1day"
END FUNCTION
```

### Structured Specification Table

| Input: Days Span | Optimal Interval | Fallback 1 | Fallback 2 | Fallback 3 | Guaranteed Result |
|------------------|------------------|------------|------------|------------|-------------------|
| 0-1 days | 15min | 30min | 1hour | 1day | Always succeeds |
| 2-7 days | 1hour | 1day | - | - | Always succeeds |
| 8+ days | 1day | - | - | - | Always succeeds |

### Implementation Location

**Backend Component**: `IntervalSelector` service

**Location**: `backend/src/zebu/application/services/interval_selector.py` (new file)

**Interface**:

| Method | Parameters | Returns | Description |
|--------|-----------|---------|-------------|
| select_interval | time_range: TimeRange<br>available_intervals: List[str] | str | Selects optimal interval with fallback |
| get_available_intervals | api_tier: ApiTier | List[str] | Returns supported intervals for tier |

**Usage**:
```
# In price history handler
interval_selector = IntervalSelector()
available = interval_selector.get_available_intervals(current_tier)
selected = interval_selector.select_interval(time_range, available)
```

## Edge Cases and Handling

### Edge Case 1: Partial Trading Days

**Scenario**: User selects 1D time range at 11:00 AM (only 1.5 hours of market data)

**Behavior**:
- Selected interval: 15min
- Expected points: ~6 (1.5 hours × 4 per hour)
- Chart may look sparse but that's accurate

**Handling**: Display timestamp range in chart subtitle ("10:00 AM - 11:00 AM ET")

### Edge Case 2: Weekend/Holiday Queries

**Scenario**: User selects 1D on a Saturday

**Behavior**:
- Selected interval: 15min
- API returns Friday's data (last trading day)
- Data points: ~26 from Friday

**Handling**: Display message "Showing last trading day: Friday, Jan 24"

### Edge Case 3: After-Hours Queries

**Scenario**: User selects 1D at 8:00 PM ET (after market close)

**Behavior**:
- Selected interval: 15min
- API returns today's intraday data (9:30 AM - 4:00 PM)
- Data points: ~26 from today

**Handling**: Display "Market closed. Showing today's trading session."

### Edge Case 4: Time Range Spans Weekend

**Scenario**: User selects 1W time range that includes a weekend

**Behavior**:
- Selected interval: 1hour
- API returns data for trading days only (skip Saturday/Sunday)
- Data points: ~35 (5 trading days × 7 hours)

**Handling**: Chart x-axis shows dates with gaps (or compressed weekends)

### Edge Case 5: Historical Intraday Not Available

**Scenario**: User selects 1W time range but premium tier only keeps 30 days of intraday

**Behavior**:
- Selected interval: 1hour
- API returns partial data (last 30 days) or error
- Fallback: Use 1day interval instead

**Handling**: Automatically fall back to 1day with warning log

### Edge Case 6: Free Tier with 1D Time Range

**Scenario**: User on free tier selects 1D (wants intraday but it's unavailable)

**Behavior**:
- Optimal interval: 15min
- Available intervals: ["1day"]
- Selected interval: 1day (fallback)
- Data points: 1 (previous day's close)

**Handling**: 
- Chart displays single point (poor UX but functional)
- Future enhancement: Display message "Upgrade for intraday data"

## Performance Considerations

### Chart Rendering Performance

| Interval | Points (1D) | Points (1W) | Points (1M) | Points (1Y) | Render Time (est.) |
|----------|-------------|-------------|-------------|-------------|--------------------|
| 15min | 26 | 182 | 780 | - | <50ms |
| 1hour | 7 | 35 | 150 | - | <50ms |
| 1day | 1 | 5 | 22 | 252 | <50ms |

**Target**: All charts render in <100ms with current data volumes.

**Threshold**: If chart has >1000 points, consider aggregation or downsampling.

### API Response Sizes

| Interval | Data Points (1D) | Response Size (est.) | Transfer Time (est.) |
|----------|------------------|----------------------|----------------------|
| 1min | 390 | ~50 KB | ~200ms |
| 5min | 78 | ~10 KB | ~50ms |
| 15min | 26 | ~3 KB | ~20ms |
| 1hour | 7 | ~1 KB | <10ms |
| 1day | 1 | <1 KB | <10ms |

**Optimization**: 15min strikes best balance (small response, good detail)

## Future Enhancements

### Weekly/Monthly Aggregation

For very long time ranges (>5 years), consider:
- **1week** interval: Aggregated weekly closes
- **1month** interval: Aggregated monthly closes

**When**: Phase 4 (if users request it)

**Benefits**: Reduce data points for ALL time range (1260 → ~60 monthly points)

### User Preferences

Allow advanced users to override interval selection:
- Setting: "Preferred interval for 1D charts"
- Options: Auto (15min), Always 30min, Always 1hour, Always 1day
- Storage: User preferences table

**When**: Phase 4 (user feedback)

### Adaptive Selection Based on Load

During high traffic:
- Prefer cached intervals over API calls
- Downgrade to coarser intervals if cache miss
- Example: 1D → prefer 1day if 15min not cached

**When**: Phase 5 (scale optimization)

## Testing Strategy

### Unit Tests

Test interval selection logic:

| Test Case | Input (days) | Available | Expected Output |
|-----------|--------------|-----------|-----------------|
| 1D optimal | 1 | ["15min", "1day"] | "15min" |
| 1D fallback | 1 | ["1day"] | "1day" |
| 1W optimal | 7 | ["1hour", "1day"] | "1hour" |
| 1W fallback | 7 | ["1day"] | "1day" |
| 1Y optimal | 365 | ["1day"] | "1day" |

### Integration Tests

Test full flow with different tiers:

| Test Case | API Tier | Time Range | Expected Interval | Expected Points (approx) |
|-----------|----------|------------|-------------------|--------------------------|
| Free tier 1D | free | 1D | 1day | 1 |
| Premium 1D | premium | 1D | 15min | 26 |
| Premium 1W | premium | 1W | 1hour | 35 |
| Premium 1M | premium | 1M | 1day | 22 |

## References

- [Alpha Vantage Intraday API](https://www.alphavantage.co/documentation/#intraday)
- [Alpha Vantage Daily API](https://www.alphavantage.co/documentation/#daily)
- [Chart Rendering Performance](https://recharts.org/en-US/guide/performance)
- [ADR-174-001: Backend-Determined Interval Selection](./decisions.md#adr-174-001-backend-determined-interval-selection)
