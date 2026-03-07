# Task 176: Fix PriceChart XAxis Rendering Issue

## Objective

Fix the price chart line not rendering properly due to X coordinates being null for all data points except the first.

## Problem Analysis

**Symptoms:**
- Price chart shows only a single point instead of a line across the time range
- Chart SVG path is `M379.5,75.587Z` (single point) instead of a proper line path
- Only "Jan 25" appears on X-axis despite having 22 data points from Dec 26 to Jan 23

**Root Cause Identified:**
When inspecting the Recharts Line component's internal `points` array:
- Point 0: `{ x: 379.5, y: 75.58, payload: "Dec 26" }` ✓
- Point 1: `{ x: null, y: 71.79, payload: "Dec 29" }` ✗
- Point 2: `{ x: null, y: 93.33, payload: "Dec 30" }` ✗
- ... all remaining points have `x: null`

**Key Observation:**
- The trade marker has `time: "Jan 25"`
- The price history data range is Dec 26 - Jan 23
- "Jan 25" is **outside** the chart data's time range
- This may be causing Recharts categorical axis calculation to fail

**Data Flow (verified working):**
1. Backend returns 22 unique price points (Dec 26 - Jan 23) ✓
2. Frontend transforms to `chartData` with unique `time` values ✓
3. Trade markers are added with their own `time` values
4. Recharts ComposedChart receives data with 22 points ✓
5. XAxis uses `dataKey="time"` with categorical (string) values
6. But X coordinates calculate as null for points after the first

## Technical Context

**File:** `frontend/src/components/features/PriceChart/PriceChart.tsx`

**Current Implementation:**
```tsx
<ComposedChart data={chartData}>
  <XAxis dataKey="time" ... />
  <Line dataKey="price" ... />
  <Scatter data={formattedTradeMarkers} ... />
</ComposedChart>
```

**Hypothesis:**
The `Scatter` component is adding data with `time: "Jan 25"` which doesn't exist in `chartData`. This may be breaking the categorical XAxis domain calculation, causing all X coordinates after the first to be null.

## Requirements

1. **Fix the primary issue**: Ensure all 22+ price data points render correctly as a continuous line

2. **Handle trade markers outside chart range**:
   - Option A: Filter out trade markers whose `time` doesn't exist in `chartData`
   - Option B: Add the trade marker dates to the chart's domain even if no price data exists
   - Option C: Use separate XAxis configurations for Line vs Scatter

3. **Maintain existing functionality**:
   - Time range selector (1D, 1W, 1M, 3M, 1Y, ALL)
   - Price stats display
   - Trade marker tooltips
   - Y-axis domain calculation including trade marker prices

4. **Add tests** to prevent regression

## Investigation Steps (for agent)

1. Create a minimal reproduction:
   - Test with `chartData` only (no Scatter) to confirm Line renders
   - Add Scatter with matching times to confirm it works
   - Add Scatter with non-matching time to reproduce the bug

2. Check Recharts documentation/issues for:
   - ComposedChart + Scatter with mismatched data domains
   - Categorical XAxis behavior with multiple data sources

3. Implement fix and test across all time ranges

## Success Criteria

- [ ] Price line renders correctly with all data points visible
- [ ] Trade markers still display at correct positions
- [ ] Chart works for all time ranges (1D, 1W, 1M, 3M, 1Y, ALL)
- [ ] Edge cases handled:
  - Trade marker outside chart date range
  - Multiple trades on same day
  - Portfolio with no trades (Scatter hidden)
- [ ] Unit tests cover the fix
- [ ] No regressions in existing tests

## Related Files

- `frontend/src/components/features/PriceChart/PriceChart.tsx` - Main component
- `frontend/src/components/features/PriceChart/PriceChart.test.tsx` - Tests
- `frontend/src/hooks/usePriceHistory.ts` - Data fetching hook

## References

- PR #161, #166 - Original trade marker implementation
- PR #173 - Backend deduplication fix (working correctly)
- Recharts documentation: https://recharts.org/en-US/api/ComposedChart
