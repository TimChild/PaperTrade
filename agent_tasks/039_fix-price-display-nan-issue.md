# Task 039: Fix Current Price Display ($NaN Issue)

**Agent**: frontend-swe
**Priority**: High
**Estimated Effort**: 1-2 hours

## Objective

Fix the issue where current prices, market values, and price changes display as `$NaN` in the portfolio holdings table and price charts. Implement graceful handling when price data is unavailable due to rate limiting or missing data.

## Context

**Current Behavior**:
When viewing a portfolio with holdings, the UI displays:
- Current Price: `$NaN`
- Market Value: `$NaN`
- Gain/Loss: `$NaN (+NaN%)`
- Price charts show `$NaN` for price statistics

**Root Cause**:
The frontend attempts to fetch current prices for display, but:
1. Alpha Vantage rate limiting (5 calls/min) prevents fetching prices for UI display
2. No graceful fallback when price data is unavailable
3. Missing data results in `NaN` calculations propagating through the UI

**Discovered During**: Playwright E2E testing session (see `orchestrator_procedures/playwright_e2e_testing.md`)

## Requirements

### 1. Price Fetching Strategy

When displaying holdings or price charts, implement this fallback hierarchy:

```typescript
// Priority order for displaying prices:
1. Use cached price from recent trade execution (if available)
2. Attempt to fetch current price (respect rate limits)
3. Display last known price with timestamp indicator
4. Show "Price unavailable" with helpful message
```

### 2. UI Improvements

**Holdings Table**:
- If current price unavailable, show: `$296.21 *` (asterisk indicates last trade price)
- Add tooltip: "Last trade price (current price unavailable)"
- Calculate market value using last known price
- Show age of price data: "as of 2 minutes ago"

**Price Charts**:
- If no historical data, show placeholder: "No price history available yet"
- If price data exists but is stale, display with warning indicator
- Don't attempt to fetch price data on every chart render (respect rate limits)

**Price Stats Component** (`PriceStats.tsx`):
- Handle missing `currentPrice` gracefully
- Show "---" or "N/A" instead of `$NaN`
- Display helpful message when data unavailable

### 3. Rate Limit Awareness

The frontend should:
- Not make redundant price fetching calls if rate limit exceeded
- Cache price fetch failures to avoid repeated failed requests
- Show user-friendly message when rate limited: "Price updates limited to 5 per minute"

### 4. Use Trade Execution Price

When a trade is executed:
- The backend returns the price used for the trade
- Store this price locally for immediate display
- Use it as the "current price" for that ticker until fresher data available

## Technical Specifications

### Files to Modify

1. **`frontend/src/hooks/usePriceQuery.ts`** or **`frontend/src/services/api/prices.ts`**:
   - Add error handling for 503 (rate limit) and 404 (not found) responses
   - Implement caching of last known prices
   - Add timestamp tracking for price data age

2. **`frontend/src/components/features/portfolio/PortfolioHoldingsTable.tsx`** (or similar):
   - Display last known price when current price unavailable
   - Add visual indicators (asterisk, tooltip) for stale prices
   - Calculate market value using best available price

3. **`frontend/src/components/features/PriceChart/PriceStats.tsx`**:
   - Replace `$NaN` with appropriate fallback display
   - Show "---" or "N/A" when no data
   - Add helpful message explaining why data is unavailable

4. **`frontend/src/pages/PortfolioDetail.tsx`** (or wherever prices are fetched):
   - Don't fetch prices on every render
   - Use react-query's `staleTime` and `cacheTime` to prevent redundant calls
   - Implement manual refetch with user-facing "Refresh Prices" button

### Example Implementation

```typescript
// In usePriceQuery.ts or similar
export function useCurrentPrice(ticker: string) {
  return useQuery({
    queryKey: ['price', 'current', ticker],
    queryFn: () => apiClient.getCurrentPrice(ticker),
    staleTime: 60000, // Consider fresh for 1 minute
    retry: (failureCount, error) => {
      // Don't retry if rate limited or not found
      if (error.status === 503 || error.status === 404) {
        return false
      }
      return failureCount < 3
    },
    // Use last successful data even if query fails
    placeholderData: (previousData) => previousData,
  })
}

// In PortfolioHoldingsTable.tsx
function HoldingRow({ holding }) {
  const { data: currentPrice, error } = useCurrentPrice(holding.ticker)

  const displayPrice = currentPrice?.price ?? holding.avgCost
  const priceSource = currentPrice ? 'current' : 'lastTrade'
  const isPriceStale = !currentPrice

  return (
    <tr>
      <td>{holding.ticker}</td>
      <td>{holding.quantity}</td>
      <td>${holding.avgCost}</td>
      <td>
        ${displayPrice}
        {isPriceStale && (
          <Tooltip content="Last trade price (current price unavailable)">
            <span className="text-gray-400 ml-1">*</span>
          </Tooltip>
        )}
      </td>
      {/* ... rest of row */}
    </tr>
  )
}
```

## Success Criteria

- [ ] Holdings table never displays `$NaN` - shows last known price with indicator
- [ ] Price charts handle missing data gracefully with placeholder message
- [ ] Price statistics component shows "---" or "N/A" when no current price
- [ ] No redundant API calls - prices fetched at most once per minute per ticker
- [ ] User-friendly messages when rate limited or data unavailable
- [ ] Visual indicators (asterisk, timestamp) show when using stale/fallback data
- [ ] All existing tests pass
- [ ] New tests added for price unavailability scenarios

## Testing Steps

1. **Test with Rate Limiting**:
   - Execute a trade (uses 1 API call)
   - Navigate to portfolio - should show last trade price, not make new API call
   - Holdings should display correctly without `$NaN`

2. **Test Missing Historical Data**:
   - Create new portfolio, execute first trade
   - Price chart should show placeholder, not `$NaN`
   - Navigate back and forth - no redundant price fetches

3. **Test Error Handling**:
   - Mock 503 (rate limit) response
   - Verify graceful fallback to last known price
   - Check for helpful error message to user

4. **Test Multiple Holdings**:
   - Portfolio with 2+ different tickers
   - Should only fetch prices once each (not per component render)
   - All prices display correctly or show appropriate fallback

## References

- Current implementation: `frontend/src/hooks/__tests__/usePriceQuery.test.tsx`
- API client: `frontend/src/services/api/client.ts`
- Price cache: `backend/src/zebu/infrastructure/cache/price_cache.py` (backend reference)
- Testing session: `orchestrator_procedures/playwright_e2e_testing.md`

## Notes

- This is a UX issue, not a data integrity issue - trades still execute correctly
- The backend correctly fetches and caches prices for trade execution
- The issue is purely in the frontend's display layer
- Consider adding a "Refresh Prices" button for manual price updates
- Future enhancement: WebSocket for real-time price updates (Phase 3+)
