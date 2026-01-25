# Task 165: Real-Time Stock Prices in Holdings Table

**Agent**: frontend-swe
**Priority**: HIGH (UX Polish - Phase 4a)
**Estimated Effort**: 1-2 hours

## Objective

Replace "Using average cost (current price unavailable)" placeholder with real-time stock prices in the Holdings table, showing users their current P&L at a glance.

## User Value

**Problem**: Holdings table shows average cost instead of current price, users can't see if stocks went up/down.
**Solution**: Fetch current prices for all holdings and display with P&L indicators.
**Benefit**: Immediate portfolio health visibility - see gains/losses in real-time.

## Implementation

### Backend (Already Available)
- ✅ Batch price endpoint exists: `GET /api/v1/prices/batch?tickers=AAPL,MSFT,GOOGL`
- ✅ Returns current prices with source attribution (cache/db/api)
- ✅ Handles rate limiting gracefully
- ✅ Weekend-aware (serves last trading day's prices)

### Frontend Changes

**File**: `frontend/src/components/features/portfolio/HoldingsTable.tsx`

**Current State**:
```tsx
// Shows: "Using average cost (current price unavailable)*"
<td>{formatCurrency(holding.averageCost)}</td>
```

**New Implementation**:
```tsx
// 1. Fetch batch prices for all holdings
const tickers = holdings.map(h => h.ticker).join(',');
const { data: prices } = useBatchPrices(tickers);

// 2. Display current price with P&L indicator
<td className="text-right">
  {prices?.[holding.ticker] ? (
    <>
      <span>{formatCurrency(prices[holding.ticker].price)}</span>
      {/* P&L indicator */}
      <span className={getProfitColor(prices[holding.ticker].price, holding.averageCost)}>
        {formatPercentChange(prices[holding.ticker].price, holding.averageCost)}
      </span>
    </>
  ) : (
    <span className="text-muted">Loading...</span>
  )}
</td>
```

**New Hook** (`frontend/src/hooks/useBatchPrices.ts`):
```tsx
export function useBatchPrices(tickers: string) {
  return useQuery({
    queryKey: ['prices', 'batch', tickers],
    queryFn: () => apiClient.get(`/api/v1/prices/batch?tickers=${tickers}`),
    staleTime: 5 * 60 * 1000, // 5 minutes
    enabled: !!tickers
  });
}
```

## Quality Standards

- ✅ Complete TypeScript types (no `any`)
- ✅ Mobile responsive (table scrolls horizontally if needed)
- ✅ Accessible (color + text for P&L indicators)
- ✅ Error handling: Show fallback if batch price fetch fails
- ✅ Loading states: Show spinner while fetching
- ✅ Tests: Unit tests for P&L calculation, integration tests for API calls

## UI/UX Requirements

**Current Price Display**:
- Format: `$150.25`
- Font size: Match existing table cells
- Alignment: Right-aligned

**P&L Indicator**:
- Positive (gain): Green text, e.g., `+5.2% ▲`
- Negative (loss): Red text, e.g., `-2.1% ▼`
- Neutral (0%): Gray text, `0.0%`
- Position: Below or next to current price

**Colors**:
- Gain: `text-green-600` (light mode), `text-green-400` (dark mode)
- Loss: `text-red-600` (light mode), `text-red-400` (dark mode)
- Neutral: `text-gray-500`

**Loading/Error States**:
- Loading: `<Spinner size="sm" />`
- Error: `"Price unavailable"` (gray text)
- Stale price: Add small indicator if price is >1 hour old

## Testing

**Unit Tests**:
- Calculate P&L percentage correctly
- Handle missing prices gracefully
- Format currency and percentages
- Color coding based on gain/loss

**Integration Tests**:
- Fetch batch prices for multiple tickers
- Handle empty holdings list
- Handle API errors (rate limiting, network failure)

**Manual Testing**:
1. Create portfolio with holdings (AAPL, MSFT, GOOGL)
2. View holdings table
3. Verify current prices appear
4. Verify P&L indicators show correct colors
5. Test on mobile - table should scroll/wrap appropriately

## Success Criteria

1. Current prices displayed for all holdings
2. P&L indicators show percentage gain/loss
3. Color coding (green/red) is clear and accessible
4. Loading states are smooth (no jarring flashes)
5. Error handling graceful (fallback to average cost)
6. Mobile responsive
7. All tests passing (234+ frontend tests)

## Files to Create/Modify

- `frontend/src/components/features/portfolio/HoldingsTable.tsx` - Add batch price display
- `frontend/src/hooks/useBatchPrices.ts` - **CREATE** new hook
- `frontend/src/utils/formatters.ts` - Add `formatPercentChange()` if needed
- `frontend/src/components/features/portfolio/__tests__/HoldingsTable.test.tsx` - Add tests

## API Response Format

```json
{
  "prices": {
    "AAPL": {
      "ticker": "AAPL",
      "price": "150.25",
      "currency": "USD",
      "timestamp": "2026-01-19T21:00:00Z",
      "source": "cache",
      "is_stale": false
    },
    "MSFT": { ... }
  }
}
```

## References

- Batch price endpoint: `backend/src/zebu/adapters/inbound/api/prices.py`
- Existing holdings table component
- TanStack Query documentation: https://tanstack.com/query/latest
- UX Polish Phase Plan: `docs/planning/ux-polish-phase-plan.md`
