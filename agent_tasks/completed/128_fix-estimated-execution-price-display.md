# Task 128: Fix Estimated Execution Price Display Bug

**Agent**: frontend-swe (or backend-swe if API issue)
**Priority**: High
**Estimated Complexity**: Low
**Dependencies**: None

## Objective

Fix the "Estimated Execution Price" field in the TradeForm component which currently displays "--" instead of the actual price, even though the loading spinner and live market price timestamp work correctly.

## Problem Description

User report: "The 'Estimated Execution Price' doesn't populate, just shows '--', but does show a tick and the live market price time"

This indicates:
- The price query IS executing (loading state works)
- The API IS responding (timestamp updates)
- But the price value itself is not displaying

## Current Code Context

**Component**: `frontend/src/components/features/portfolio/TradeForm.tsx`

```typescript
const {
  data: priceData,
  isLoading: isPriceLoading,
  error: priceError,
} = usePriceQuery(backtestMode ? '' : debouncedTicker)

// Derive display price directly from priceData
const displayPrice = priceData?.price?.amount?.toFixed(2) ?? '--'
```

**Hook**: `frontend/src/hooks/usePriceQuery.ts`
- Returns `useQuery<PricePoint>` from TanStack Query
- Calls `getCurrentPrice(ticker)` from prices API service

**Type**: `frontend/src/types/price.ts`
```typescript
export interface PricePoint {
  ticker: Ticker
  price: Money
  timestamp: string
  source: 'alpha_vantage' | 'cache' | 'database'
  interval: 'real-time' | '1day' | '1hour' | '5min' | '1min'
  // ... OHLCV fields
}
```

## Investigation Steps

1. **Check API Response**: Use browser DevTools Network tab to inspect the actual API response from `/api/v1/prices/current/{ticker}`. Does it match the PricePoint interface?

2. **Check Data Transformation**: Review `frontend/src/services/api/prices.ts` - does `getCurrentPrice()` properly transform the API response?

3. **Check Backend DTO**: Review backend price endpoint - does it return data in the expected format?

4. **Add Logging**: Temporarily add `console.log('priceData:', priceData)` in TradeForm to see what's actually being received

## Likely Root Causes

Based on symptoms (loading works, timestamp updates, but price shows '--'):

1. **Most likely**: API response doesn't match expected structure (e.g., nested differently, uses different field names)
2. **Possible**: Frontend type definitions don't match backend DTOs
3. **Possible**: Data transformation layer has a bug
4. **Less likely**: Price value is null/undefined in database (but then timestamp wouldn't work either)

## Acceptance Criteria

- [ ] Estimated Execution Price displays actual price value (e.g., "$150.23")
- [ ] Price updates when ticker changes
- [ ] Loading state still works correctly
- [ ] Price only fetches when not in backtest mode
- [ ] No console errors related to price fetching

## Implementation Notes

- Test with real ticker (e.g., "AAPL") that has known data
- Verify the fix works with both successful and error states
- Ensure type safety is maintained (no `any` types)
- If changing API contract, ensure backend tests are updated too

## Testing

Manual testing:
1. Open TradeForm component
2. Enter ticker "AAPL"
3. Wait for debounce (500ms)
4. Verify price displays as dollar amount, not "--"
5. Change ticker to "MSFT"
6. Verify price updates
7. Enter invalid ticker "INVALID"
8. Verify appropriate error handling

## Related Files

- `frontend/src/components/features/portfolio/TradeForm.tsx` - UI component
- `frontend/src/hooks/usePriceQuery.ts` - React Query hook
- `frontend/src/services/api/prices.ts` - API service layer
- `frontend/src/types/price.ts` - Type definitions
- `backend/src/adapters/inbound/http/routers/prices.py` - Backend endpoint (if needed)
