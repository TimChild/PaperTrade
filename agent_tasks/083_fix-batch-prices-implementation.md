# Task 083: Fix Batch Prices Implementation in Frontend

**Priority**: HIGH
**Complexity**: Medium
**Estimated Effort**: 1-2 hours
**Agent**: frontend-swe

## Problem

PR #98 added a batch price endpoint `/api/v1/prices/batch` on the backend with Redis caching, but the frontend `getBatchPrices()` function in `prices.ts` is NOT using it. Instead, it makes individual API calls for each ticker using `Promise.allSettled`, which:

1. Doesn't leverage the batch endpoint or Redis caching
2. Makes multiple HTTP requests instead of one
3. Hits the Alpha Vantage API rate limits more quickly
4. Causes real-time prices to NOT display in the HoldingsTable
5. Causes total value calculation to fail (shows "---")

## Current Implementation

`frontend/src/services/api/prices.ts`:
```typescript
export async function getBatchPrices(
  tickers: string[]
): Promise<Map<string, PricePoint>> {
  const results = await Promise.allSettled(
    tickers.map((ticker) => getCurrentPrice(ticker)) // ❌ Individual calls
  )

  const priceMap = new Map<string, PricePoint>()
  results.forEach((result, index) => {
    if (result.status === 'fulfilled') {
      priceMap.set(tickers[index], result.value)
    }
  })

  return priceMap
}
```

## Expected Implementation

The function should call the batch endpoint created in PR #98:

```typescript
export async function getBatchPrices(
  tickers: string[]
): Promise<Map<string, PricePoint>> {
  if (tickers.length === 0) {
    return new Map()
  }

  // Use batch endpoint: GET /prices/batch?tickers=AAPL,MSFT,GOOGL
  const response = await apiClient.get<PricePoint[]>('/prices/batch', {
    params: { tickers: tickers.join(',') },
  })

  // Convert array response to Map for easy lookup
  const priceMap = new Map<string, PricePoint>()
  response.data.forEach((price) => {
    priceMap.set(price.ticker.symbol, price)
  })

  return priceMap
}
```

## Backend API Reference

From `backend/src/papertrade/adapters/inbound/api/prices.py`:

```python
@router.get("/batch", response_model=list[PricePointResponse])
async def get_batch_prices(
    tickers: str = Query(..., description="Comma-separated list of ticker symbols"),
    market_data_service: MarketDataService = Depends(get_market_data_service),
) -> list[PricePointResponse]:
    """Get current prices for multiple tickers in a single request."""
    ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()]

    if not ticker_list:
        raise HTTPException(status_code=400, detail="No valid tickers provided")

    try:
        # Uses batch_get_current_prices which leverages Redis caching
        prices = await market_data_service.batch_get_current_prices(ticker_list)
        return [_price_point_to_response(p) for p in prices]
    except Exception as e:
        logger.error(f"Failed to fetch batch prices: {e}")
        raise HTTPException(
            status_code=503,
            detail="Market data service temporarily unavailable"
        )
```

Returns: `PricePoint[]` (array of PricePoint objects)

## Acceptance Criteria

1. `getBatchPrices()` function calls `/api/v1/prices/batch` endpoint instead of making individual calls
2. Function correctly converts comma-separated ticker string for query params
3. Function converts array response to Map for backward compatibility
4. Error handling matches backend (503 rate limit, 400 invalid tickers)
5. All existing tests pass
6. Real-time prices display in HoldingsTable (no more "*" fallback)
7. Total value displays correctly in PortfolioSummaryCard (no more "---")
8. Network tab shows single `/api/v1/prices/batch` call instead of multiple `/prices/{ticker}` calls

## Testing Strategy

### Unit Tests
Update existing `getBatchPrices` tests to verify:
- Correct endpoint called with query params
- Response array converted to Map
- Empty ticker list returns empty Map
- Error handling for 503, 400 responses

### Manual Testing
1. Navigate to portfolio detail page
2. Open browser DevTools Network tab
3. Verify single call to `/api/v1/prices/batch?tickers=AAPL` (or whatever tickers)
4. Verify holdings table shows real-time prices (no "*" asterisk)
5. Verify total value shows correct amount (not "---")
6. Verify price updates every 30 seconds (from useHoldings refetchInterval)

## Files to Modify

- `frontend/src/services/api/prices.ts` - Update `getBatchPrices()` implementation
- `frontend/src/services/api/prices.test.ts` - Update tests for new implementation (if exists)

## Related Work

- PR #98: Implemented batch price endpoint on backend
- PR #97: Fixed total_value calculation to include holdings
- Uses `useBatchPricesQuery` hook from `frontend/src/hooks/usePriceQuery.ts` (no changes needed)
- Used by `HoldingsTable.tsx` and `PortfolioSummaryCard.tsx` (no changes needed)

## Notes

- This is a critical bug preventing Phase 3 real-time pricing features from working
- The backend implementation is correct; this is purely a frontend integration issue
- Once fixed, users will see live stock prices instead of fallback average costs
- This will significantly improve UX for trading and portfolio valuation
