# Task 168: Fix PriceChart Tooltip Type Safety and Y-Axis Domain

**Agent**: frontend-swe
**Priority**: HIGH (Production Bug)
**Estimated Effort**: 1-2 hours

## Objective

Fix two related bugs in the PriceChart component that were introduced when trade markers (scatter plot) were added:

1. **Tooltip Type Error**: `value.toFixed is not a function` when hovering over chart
2. **Chart Display Issue**: Line chart appears cut off/outside visible area because Y-axis domain doesn't account for scatter plot data points

## Root Causes

### Issue 1: Tooltip Formatter Type Safety

**File**: `frontend/src/components/features/PriceChart/PriceChart.tsx` (lines 289-292)

**Problem**:
```tsx
formatter={(value: number | undefined) =>
  value !== undefined
    ? [`$${value.toFixed(2)}`, 'Price']
    : ['N/A', 'Price']
}
```

The Tooltip component receives data from BOTH:
- **Line component**: `chartData` with numeric `price` values
- **Scatter component**: `formattedTradeMarkers` where `price` might be a string (from `parseFloat()` conversion)

When hovering over a scatter marker, `value` is a string, causing `toFixed()` to fail.

### Issue 2: Y-Axis Domain Calculation

**File**: `frontend/src/components/features/PriceChart/PriceChart.tsx` (line 274)

**Problem**:
```tsx
<YAxis
  domain={['dataMin - 5', 'dataMax + 5']}
  ...
/>
```

The domain is calculated from `chartData` (Line component) only. When scatter plot markers have prices outside this range, they appear cut off or cause the line to render outside the visible chart area.

**Visual Evidence**: See screenshot `.playwright-mcp/portfolio-chart-issue.png` - the red line appears flat and cut off.

## Solutions

### Fix 1: Tooltip Formatter Type Safety

Add proper type guards to handle both number and string values:

```tsx
formatter={(value: unknown) => {
  // Handle both Line data (numbers) and Scatter data (might be strings)
  const numValue = typeof value === 'number' 
    ? value 
    : typeof value === 'string' 
      ? parseFloat(value) 
      : NaN;
  
  return !Number.isNaN(numValue)
    ? [`$${numValue.toFixed(2)}`, 'Price']
    : ['N/A', 'Price'];
}}
```

**Alternative**: Ensure `formattedTradeMarkers.price` is always a number (not string) at the data transformation stage (line 208).

### Fix 2: Y-Axis Domain Calculation

Calculate domain from combined dataset (both line and scatter data):

```tsx
// Calculate Y-axis domain from both chart data and trade markers
const allPrices = [
  ...chartData.map(d => d.price),
  ...formattedTradeMarkers.map(m => m.price)
];
const minPrice = Math.min(...allPrices);
const maxPrice = Math.max(...allPrices);
const padding = (maxPrice - minPrice) * 0.1 || 5; // 10% padding or $5 min

// Later in YAxis component
<YAxis
  domain={[minPrice - padding, maxPrice + padding]}
  ...
/>
```

## Quality Standards

- ✅ Complete TypeScript types (no `any`)
- ✅ Proper type guards for runtime safety
- ✅ Tests for both fixes
- ✅ Verify fix works for portfolios with and without trade markers
- ✅ Chart displays correctly with markers at min/max price points

## Testing

### Unit Tests

Add to `frontend/src/components/features/PriceChart/PriceChart.test.tsx`:

```tsx
describe('PriceChart with trade markers', () => {
  it('should handle scatter plot data in tooltip without errors', async () => {
    // Render chart with trade markers
    // Simulate hovering over scatter marker
    // Verify tooltip renders without crashing
  });

  it('should calculate Y-axis domain including trade markers', () => {
    // Render chart where trade markers have prices outside line data range
    // Verify all data points are visible
    // Verify domain includes min/max from both datasets
  });

  it('should handle string and number values in tooltip formatter', () => {
    // Test formatter function directly
    // Pass various value types (number, string, undefined, null)
    // Verify correct output format
  });
});
```

### Manual Testing

1. **Navigate to portfolio with trade history**: http://localhost:5173/portfolio/{id}
2. **Verify chart displays correctly**:
   - All price line segments visible
   - Trade markers (green BUY, red SELL) visible
   - No markers cut off at top/bottom of chart
3. **Hover over different parts of chart**:
   - Hover over line → tooltip shows price
   - Hover over green marker → tooltip shows BUY trade details
   - Hover over red marker → tooltip shows SELL trade details
   - **No console errors** (`value.toFixed is not a function`)
4. **Test edge cases**:
   - Portfolio with markers at min price
   - Portfolio with markers at max price
   - Portfolio with no markers (portfolioId not provided)

### Regression Testing

Run existing tests to ensure no breakage:
```bash
task test:frontend
```

## Files to Modify

- `frontend/src/components/features/PriceChart/PriceChart.tsx` - Fix tooltip formatter and Y-axis domain
- `frontend/src/components/features/PriceChart/PriceChart.test.tsx` - Add tests for both fixes

## Success Criteria

1. ✅ No `toFixed is not a function` errors when hovering over chart
2. ✅ Tooltip works correctly for both line data and scatter markers
3. ✅ Chart displays all data points within visible area
4. ✅ Y-axis domain includes both line and scatter data
5. ✅ All frontend tests passing
6. ✅ Manual testing confirms fixes work in production-like scenario

## References

- **Bug Report**: User reported `TypeError: value.toFixed is not a function` at line 290
- **Screenshot**: `.playwright-mcp/portfolio-chart-issue.png` shows chart display issue
- **Related PR**: #161 (Added trade execution markers - introduced these bugs)
- **Recharts Docs**: https://recharts.org/en-US/api/Tooltip
- **Recharts Domain**: https://recharts.org/en-US/api/YAxis#domain
