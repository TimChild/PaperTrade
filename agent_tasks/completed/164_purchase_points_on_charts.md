# Task 164: Show Purchase Points on Stock Price Charts

**Agent**: frontend-swe
**Priority**: HIGH (UX Polish - Phase 4a)
**Estimated Effort**: 2-3 hours

## Objective

Add visual markers (dots) on historical price charts showing exactly when BUY and SELL trades were executed for that ticker.

## User Value

**Problem**: Users can't see when they bought/sold stocks relative to price movements.
**Solution**: Show BUY (green) and SELL (red) markers on price charts at the exact dates of trades.
**Benefit**: Instantly evaluate trade timing - "Did I buy at the bottom? Sell at the peak?"

## Implementation

### Backend (Already Available)
- ✅ Transaction history API exists: `GET /api/v1/portfolios/{id}/transactions`
- ✅ Includes ticker, action (BUY/SELL), timestamp, price, quantity

### Frontend Changes

**File**: `frontend/src/components/features/analytics/PriceChart.tsx` (or wherever stock price charts are)

**Changes Needed**:
1. Fetch transactions for the displayed ticker
2. Filter to BUY/SELL actions only (not DEPOSIT/WITHDRAW)
3. Add scatter plot layer to Recharts
4. Position markers at transaction dates
5. Color code: BUY = green, SELL = red
6. Tooltip on hover: "Bought 10 shares at $150.00 on Jan 15, 2026"

**Example Code Pattern**:
```tsx
// In PriceChart component
const { data: transactions } = useTransactions(portfolioId);

// Filter to trades for this ticker
const tickerTrades = transactions?.filter(
  (t) => t.ticker === ticker && (t.action === 'BUY' || t.action === 'SELL')
) || [];

// Add to Recharts
<ScatterChart>
  {/* Existing price line chart */}
  <Line ... />

  {/* Trade markers */}
  <Scatter
    name="Trades"
    data={tickerTrades.map(t => ({
      date: t.timestamp,
      price: t.price,
      action: t.action,
      quantity: t.quantity
    }))}
    fill={(entry) => entry.action === 'BUY' ? '#10b981' : '#ef4444'}
  />
</ScatterChart>
```

## Quality Standards

- ✅ Complete TypeScript types (no `any`)
- ✅ Mobile responsive (markers visible on all screen sizes)
- ✅ Accessible (color + shape differentiation for colorblind users)
- ✅ Performance: Don't fetch transactions on every render (use React Query cache)
- ✅ Error handling: Gracefully handle missing transaction data
- ✅ Tests: Unit tests for filtering logic, integration test for chart rendering

## Testing

**Unit Tests**:
- Filter transactions to correct ticker
- Separate BUY from SELL
- Handle empty transaction list
- Format tooltip text correctly

**Manual Testing**:
1. Create portfolio with multiple trades for AAPL
2. View AAPL price chart
3. Verify green/red markers appear at correct dates
4. Hover over marker - should show trade details
5. Test on mobile - markers should be visible and tappable

## UI/UX Requirements

- Marker size: 8-10px diameter (visible but not overwhelming)
- Colors:
  - BUY: `#10b981` (green-500)
  - SELL: `#ef4444` (red-500)
- Tooltip format: `"[BUY|SELL] {quantity} shares at ${price} on {date}"`
- Z-index: Markers should appear above the price line
- Shape: Use different shapes if possible (circle for BUY, triangle for SELL)

## Success Criteria

1. Markers appear on all stock price charts
2. Correct positioning (date + price)
3. Correct color coding (green = BUY, red = SELL)
4. Tooltip shows complete trade information
5. Mobile responsive and accessible
6. No performance degradation (charts render smoothly)
7. All tests passing

## Files to Create/Modify

- `frontend/src/components/features/analytics/PriceChart.tsx` - Add scatter plot layer
- `frontend/src/components/features/analytics/__tests__/PriceChart.test.tsx` - Add tests
- `frontend/src/hooks/useTransactions.ts` - Use existing or create if needed

## References

- Recharts Scatter Chart: https://recharts.org/en-US/api/ScatterChart
- Existing price charts in the app
- Transaction API endpoint documentation
- UX Polish Phase Plan: `docs/planning/ux-polish-phase-plan.md`
