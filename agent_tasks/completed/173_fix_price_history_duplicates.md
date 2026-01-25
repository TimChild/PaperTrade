# Task 173: Fix Price History API Duplicate Entries

**Agent**: backend-swe
**Priority**: HIGH (Production Bug)
**Estimated Effort**: 2-3 hours

## Problem Statement

The `/api/v1/prices/{ticker}/history` endpoint returns duplicate price entries for the same trading day, causing frontend charts to display incorrectly (collapsed into a single point instead of showing a proper price line).

### Root Cause Analysis

The `price_history` table stores multiple entries per trading day with different timestamps:

```sql
SELECT timestamp, source, price_amount FROM price_history
WHERE ticker='IBM' ORDER BY timestamp DESC LIMIT 10;

         timestamp          |    source     | price_amount
----------------------------+---------------+-------------
 2026-01-20 21:00:00        | alpha_vantage |       291.35  -- Market close
 2026-01-20 13:35:59.393722 | alpha_vantage |     305.6700  -- Intraday cache
 2026-01-20 00:37:58.91354  | alpha_vantage |     305.6700  -- Another cache
```

The unique constraint is on `(ticker, timestamp, source, interval)`, so entries with different timestamps are all considered unique - which is technically correct but problematic for daily interval data.

When the API aggregates data from Redis cache + PostgreSQL + API, it combines all entries without deduplicating by trading day.

### Impact

1. **Chart rendering broken**: Frontend receives 51 entries where many share the same formatted date (e.g., "Jan 20"), causing Recharts to collapse them into a single X-axis position
2. **No visible price line**: The "line" becomes a single dot because all duplicate entries stack on one point
3. **Trade markers misaligned**: Buy/sell markers can't align with price data when X-axis positions are collapsed

## Solution Requirements

### Option A: Deduplicate at Query Time (Recommended)

Modify `get_price_history()` in `alpha_vantage_adapter.py` to deduplicate entries by trading day before returning:

```python
# After combining all sources (cached_history + db_history + api_history)
# Deduplicate by date for daily interval, keeping the market close entry (21:00 UTC)

if interval == "1day":
    # Group by date, preferring market close time (21:00:00 UTC)
    by_date: dict[date, PricePoint] = {}
    for p in all_prices:
        d = p.timestamp.date()
        existing = by_date.get(d)
        # Prefer market close (21:00:00) over intraday entries
        if existing is None or p.timestamp.time() == time(21, 0, 0):
            by_date[d] = p
    return sorted(by_date.values(), key=lambda p: p.timestamp)
```

### Option B: Fix at Database Query Level

Modify `get_price_history()` in the price repository to use `DISTINCT ON` or window functions to return only one entry per trading day.

### Option C: Prevent Duplicates at Write Time

Modify the upsert logic to use date truncation for daily interval data, preventing multiple entries per day. This is more invasive and may affect historical data analysis.

## Implementation Notes

1. **Preserve behavior for non-daily intervals**: Only deduplicate when `interval == "1day"`
2. **Prefer market close price**: When multiple entries exist for a day, prefer the one at 21:00:00 UTC (market close)
3. **Handle timezone correctly**: All timestamps are UTC
4. **Don't modify database schema**: The current schema supports fine-grained timestamps which may be valuable for future features

## Files to Modify

- `backend/src/zebu/adapters/outbound/market_data/alpha_vantage_adapter.py`
  - `get_price_history()` method (lines ~614-825)
  - Add deduplication logic before returning results

## Testing

### Unit Tests

Add tests in `backend/tests/adapters/outbound/market_data/test_alpha_vantage_adapter.py`:

```python
async def test_get_price_history_deduplicates_daily_entries():
    """Verify that multiple entries for the same date are deduplicated."""
    # Setup: Mock repository returning multiple entries for same date
    # Assert: Only one entry per date in result
    # Assert: Market close time (21:00) is preferred

async def test_get_price_history_preserves_intraday_entries():
    """Verify that intraday intervals are NOT deduplicated."""
    # Setup: Mock repository returning multiple entries for same day with 1hour interval
    # Assert: All entries preserved (no deduplication)
```

### Integration Test

Verify via API:
```bash
curl "http://localhost:8000/api/v1/prices/IBM/history?start=2025-12-25&end=2026-01-25" | jq '.count'
# Should return ~20-22 entries (one per trading day), not 51
```

### Manual Test

After fix, the frontend chart should display:
- A proper line chart showing price movement over time
- Multiple X-axis labels (one per trading day, not collapsed)
- Trade markers aligned with the price line

## Success Criteria

1. ✅ API returns exactly one price entry per trading day for `interval=1day`
2. ✅ Market close price (21:00 UTC) is preferred when multiple entries exist
3. ✅ Non-daily intervals (1hour, 5min, etc.) are NOT affected
4. ✅ All existing tests pass
5. ✅ New unit tests cover deduplication logic
6. ✅ Frontend chart displays correctly (manual verification)

## Quality Standards

- Complete type hints (no `Any`)
- Docstrings for new/modified functions
- Follow existing code patterns in the adapter
- Tests must be behavior-focused (not implementation-focused)

## References

- Price history endpoint: `backend/src/zebu/adapters/inbound/api/prices.py` (line 242)
- Alpha Vantage adapter: `backend/src/zebu/adapters/outbound/market_data/alpha_vantage_adapter.py`
- Price history model: `backend/src/zebu/adapters/outbound/models/price_history.py`
- Frontend chart component: `frontend/src/components/features/PriceChart/PriceChart.tsx`
