# Task 177: Fix Recharts Trade Markers Implementation

## Objective

Fix the PriceChart component so trade markers (buy/sell indicators) work correctly alongside the price line without breaking the chart rendering.

## Background

The current implementation uses Recharts' `Scatter` component with a categorical XAxis (string-based time values). This causes the chart to break when trade markers are present - the price line renders as a single point instead of a complete curve.

**Root Cause**: Recharts' categorical XAxis calculates X positions based on data array indices. When a separate `Scatter` component has data with `time` values (even matching ones), it disrupts the XAxis calculation for all other components.

**PR #176 attempted** to fix this by filtering trade markers to only those within the visible date range, but testing revealed this doesn't solve the core issue - charts still break when markers ARE within the range.

## Requirements

### Functional
1. Price line MUST render correctly as a complete curve (not a single point)
2. Trade markers MUST display at correct positions when trades fall within the visible date range
3. Buy markers should be green circles, Sell markers should be red circles
4. Hovering over markers should show trade details (quantity, price, date)
5. Chart MUST work correctly in all scenarios:
   - No trade markers in range
   - Trade markers outside visible range (should not appear)
   - Trade markers inside visible range (MUST appear at correct positions)

### Technical Approach

Choose ONE of these approaches (recommended order):

**Option 1: Use ReferenceDot instead of Scatter (Recommended)**
- ReferenceDot positions by actual axis values, not data indices
- One ReferenceDot per trade marker
- Keeps data separation clean

**Option 2: Merge marker data into chartData**
- Add optional `tradeMarker` properties to each data point
- Use custom dot rendering on the Line component
- Single data source, but more complex data structure

**Option 3: Use numeric XAxis**
- Convert timestamps to numbers (Unix epoch)
- Use custom tickFormatter for display
- More fundamental change but solves categorical issues entirely

## Current Implementation

File: `frontend/src/components/features/PriceChart/PriceChart.tsx`

Key sections to modify:
- Lines 197-207: `formattedTradeMarkers` creation
- Lines 337-361: Scatter component rendering

## Success Criteria

1. All existing PriceChart tests pass
2. New tests added that verify:
   - Chart renders correctly with trade markers in range
   - Chart renders correctly with trade markers outside range
   - Chart renders correctly with no trade markers
3. Manual verification: Create a backtest trade on a date visible in the 1M chart view, confirm marker appears AND price line renders completely
4. No TypeScript errors or ESLint warnings

## Testing Instructions

After implementation, verify manually:
1. Navigate to a portfolio with IBM holdings
2. Check 1M view - price line should render completely (21+ data points)
3. Enable Backtest Mode, buy 1 share of IBM on Jan 15, 2026
4. Verify: Green marker appears at Jan 15 position AND price line still renders completely
5. Switch to 1W view - trade marker should not appear (outside range), line renders correctly

## Files to Modify

- `frontend/src/components/features/PriceChart/PriceChart.tsx` - Main implementation
- `frontend/src/components/features/PriceChart/PriceChart.test.tsx` - Add tests

## References

- Recharts ReferenceDot: https://recharts.org/en-US/api/ReferenceDot
- Current PriceChart: `frontend/src/components/features/PriceChart/`
- PR #176 (closed): Shows the filtering approach that was insufficient
