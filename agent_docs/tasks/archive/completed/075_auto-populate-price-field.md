# Task 075: Auto-Populate Price Per Share Field

**Agent**: frontend-swe
**Priority**: Medium
**Estimated Effort**: 2-3 hours

## Problem

When users enter a ticker symbol in the trade form, the "Price Per Share" field remains empty. Users have to manually look up and enter the price, which is tedious and error-prone.

The price field is meant to show estimated trade cost, but it's not useful if users have to find the price themselves.

## Requirements

Auto-fetch and populate the current stock price when user enters a ticker symbol:

1. **Debounced Price Fetch**
   - When user types ticker (e.g., "AAPL"), wait 500ms after typing stops
   - Fetch current price from backend API
   - Populate "Price Per Share" field automatically
   - Show loading state while fetching

2. **Error Handling**
   - If ticker invalid or price unavailable, show inline error
   - Don't block trade submission (backend will use real-time price)
   - Clear error when user changes ticker

3. **Visual Feedback**
   - Show loading spinner in price field while fetching
   - Show checkmark or success state when price loaded
   - Update estimated total cost immediately

4. **Backend API Endpoint**
   - Create `/api/v1/market/price/{ticker}` endpoint
   - Returns current price for given ticker
   - Uses existing market data infrastructure
   - Rate-limited to prevent abuse

## Implementation Notes

### Frontend

- Use `useDebouncedValue` hook (or create one) for ticker input
- Create `useStockPrice(ticker)` query hook with TanStack Query
- Update TradeForm component to:
  ```typescript
  const debouncedTicker = useDebouncedValue(ticker, 500);
  const { data: price, isLoading, error } = useStockPrice(debouncedTicker);

  useEffect(() => {
    if (price) {
      setPricePerShare(price.toString());
    }
  }, [price]);
  ```

### Backend

- Add `GET /api/v1/market/price/{ticker}` route
- Reuse existing `MarketDataPort` and `AlphaVantageAdapter`
- Return simple response: `{"ticker": "AAPL", "price": 260.33, "timestamp": "2026-01-07T..."}`
- Add caching (Redis) to minimize API calls

## Testing

### Backend
- Unit test for price endpoint
- Test caching behavior
- Test invalid ticker handling

### Frontend
- Test debounce behavior
- Test loading state
- Test error state
- Test price population
- Test estimated total calculation

## Acceptance Criteria

- [ ] Backend `/api/v1/market/price/{ticker}` endpoint implemented
- [ ] Price data cached in Redis (5-minute TTL)
- [ ] Frontend debounces ticker input (500ms)
- [ ] Price field auto-populates when ticker entered
- [ ] Loading spinner shown while fetching
- [ ] Error message shown for invalid ticker
- [ ] Estimated total cost updates automatically
- [ ] All scenarios have test coverage
- [ ] Works in both regular and backtest mode

## Related

- Found during manual testing in session 2026-01-07
- Complements error message improvements (task 074)
- Improves trade execution UX
