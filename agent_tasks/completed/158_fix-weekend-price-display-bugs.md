# Task 158: Fix Weekend/Holiday Price Display & Calculation Bugs

**Agent**: frontend-swe
**Priority**: High
**Estimated Effort**: 4-6 hours
**Created**: 2026-01-18

## Problem Statement

Multiple bugs related to price fetching and display on weekends/holidays:

1. **Estimated Execution Price (Weekends)**: When typing a ticker on weekends, shows "Unable to fetch market data" instead of using last trading day's price
2. **Backtest Mode - No Price**: Backtest mode doesn't show estimated execution price at all
3. **Total Value Incorrect**: Dashboard shows only cash balance on weekends, not including stock holdings value
4. **Analytics Issues**: Analytics page likely has same problem as total value

## Root Causes

### Bug #1 & #2: TradeForm Price Fetching
**File**: `frontend/src/components/features/portfolio/TradeForm.tsx`

**Current Code** (Line 40):
```typescript
const {
  data: priceData,
  isLoading: isPriceLoading,
  error: priceError,
} = usePriceQuery(backtestMode ? '' : debouncedTicker)
```

**Problems**:
- When `backtestMode=true`, passes empty string → no price fetched
- `usePriceQuery` uses `/api/v1/prices/{ticker}` which should work on weekends (backend has `_get_last_trading_day()` logic)
- Need to verify backend actually returns Friday's price on weekends

**Backend Endpoint**: `/api/v1/prices/{ticker}/check?date={date}` exists for checking historical data availability

### Bug #3: Total Value Duplicate Calculation
**File**: `frontend/src/components/features/portfolio/PortfolioSummaryCard.tsx`

**Current Code** (Lines 28-45):
```typescript
const { totalValue, holdingsValue } = useMemo(() => {
  if (!priceMap || !holdingsDTO || holdingsDTO.length === 0) {
    return { totalValue: portfolio.cashBalance, holdingsValue: 0 }
  }

  const holdingsVal = holdingsDTO.reduce((sum, holding) => {
    const price = priceMap.get(holding.ticker)
    if (!price) return sum
    return sum + price.price.amount * parseFloat(holding.quantity)
  }, 0)

  return {
    totalValue: portfolio.cashBalance + holdingsVal,
    holdingsValue: holdingsVal,
  }
}, [portfolio.cashBalance, holdingsDTO, priceMap])
```

**Problem**:
- Frontend recalculates `totalValue` by fetching real-time prices via `useBatchPricesQuery`
- Backend already calculated correct `totalValue` (using cached Friday prices on weekends)
- Frontend calculation fails on weekends when batch price fetch returns no data
- Result: Shows only cash balance instead of correct total value

**Fix**: Use `portfolio.totalValue` from backend instead of recalculating

## Required Changes

### 1. Fix Backtest Mode Price Display (HIGH PRIORITY)

Create a new hook for fetching historical prices when backtest date is set:

**Option A**: Add `date` parameter to existing `usePriceQuery`:
```typescript
// frontend/src/hooks/usePriceQuery.ts
export function usePriceQuery(ticker: string, date?: string) {
  const endpoint = date
    ? `/prices/${ticker}/check?date=${date}`
    : `/prices/${ticker}`

  return useQuery({
    queryKey: date ? ['price-historical', ticker, date] : ['price', ticker],
    queryFn: () => date ? getHistoricalPrice(ticker, date) : getCurrentPrice(ticker),
    // ...rest of config
  })
}
```

**Option B**: Create separate `useHistoricalPriceQuery` hook:
```typescript
// frontend/src/hooks/useHistoricalPriceQuery.ts
export function useHistoricalPriceQuery(ticker: string, date: string) {
  return useQuery({
    queryKey: ['price-historical', ticker, date],
    queryFn: () => getHistoricalPrice(ticker, date),
    enabled: Boolean(ticker) && Boolean(date),
    // ...config
  })
}
```

Then update TradeForm.tsx:
```typescript
// Use different query based on backtest mode
const {
  data: priceData,
  isLoading: isPriceLoading,
  error: priceError,
} = backtestMode && backtestDate
    ? useHistoricalPriceQuery(debouncedTicker, backtestDate)
    : usePriceQuery(debouncedTicker)
```

**Recommendation**: Option B is cleaner (separation of concerns)

### 2. Fix Total Value Calculation (CRITICAL)

**File**: `frontend/src/components/features/portfolio/PortfolioSummaryCard.tsx`

**Change**: Use backend-calculated `totalValue` instead of recalculating:

```typescript
// REMOVE: Local calculation logic (lines 20-45)
// DELETE: useBatchPricesQuery hook usage
// DELETE: totalValue calculation useMemo

// REPLACE WITH: Simple destructuring
const totalValue = portfolio.totalValue
const holdingsValue = portfolio.totalValue - portfolio.cashBalance

// KEEP: staleness tracking if needed for UI indicator
```

**Important**: Verify `portfolio.totalValue` is correctly populated from backend in `utils/adapters.ts:adaptPortfolio()`

### 3. Add API Function for Historical Prices

**File**: `frontend/src/services/api/prices.ts`

```typescript
/**
 * Check if historical price data exists for a ticker at a specific date
 * Used by backtest mode to verify data availability
 */
export async function checkHistoricalPrice(
  ticker: string,
  date: string
): Promise<{ available: boolean; closest_date?: string }> {
  const response = await apiClient.get<{
    available: boolean
    closest_date: string | null
  }>(`/prices/${ticker}/check`, {
    params: { date },
  })

  return {
    available: response.data.available,
    closest_date: response.data.closest_date || undefined,
  }
}

/**
 * Get historical price for a ticker at a specific date
 * Returns the closest available price if exact date not available
 */
export async function getHistoricalPrice(
  ticker: string,
  date: string
): Promise<PricePoint> {
  // First check if data is available
  const check = await checkHistoricalPrice(ticker, date)

  if (!check.available) {
    throw new Error(`No historical data available for ${ticker} at ${date}`)
  }

  // Use the /history endpoint with a 1-day range around the target date
  const response = await apiClient.get<{
    ticker: string
    prices: Array<{
      ticker: string
      price: string
      currency: string
      timestamp: string
      source: string
      interval: string
    }>
    start: string
    end: string
    interval: string
    count: number
  }>(`/prices/${ticker}/history`, {
    params: {
      start: date,
      end: date,
      interval: '1day',
    },
  })

  if (!response.data.prices || response.data.prices.length === 0) {
    throw new Error(`No price data returned for ${ticker} at ${date}`)
  }

  // Return first (and should be only) price point
  const priceData = response.data.prices[0]
  return {
    ticker: { symbol: priceData.ticker },
    price: {
      amount: parseFloat(priceData.price),
      currency: priceData.currency,
    },
    timestamp: priceData.timestamp,
    source: priceData.source as 'alpha_vantage' | 'cache' | 'database',
    interval: priceData.interval,
  }
}
```

### 4. Verify Weekend Behavior for Current Prices

**Test Case**: Verify that `/api/v1/prices/{ticker}` returns Friday's price on Sunday

**File**: Add test to `backend/tests/integration/test_prices_api.py` (if not exists):
```python
def test_get_current_price_on_weekend(client, db):
    """Verify current price endpoint returns last trading day on weekends."""
    # Mock today as Sunday
    with freeze_time("2026-01-19"):  # Sunday
        response = client.get("/api/v1/prices/AAPL")
        assert response.status_code == 200
        data = response.json()
        # Should return Friday's price
        assert datetime.fromisoformat(data["timestamp"]).date() == date(2026, 1, 16)
```

**Note**: This test might already pass if backend logic is correct. Verify by running existing tests.

## Testing Requirements

### Unit Tests

1. **useHistoricalPriceQuery Hook**:
```typescript
// frontend/src/hooks/__tests__/useHistoricalPriceQuery.test.ts
describe('useHistoricalPriceQuery', () => {
  it('fetches historical price for valid date', async () => {
    // Mock API response
    // Test query executes correctly
  })

  it('disables query when ticker or date is empty', () => {
    // Test enabled logic
  })

  it('handles API errors gracefully', async () => {
    // Test error handling
  })
})
```

2. **PortfolioSummaryCard** (update existing tests):
```typescript
// frontend/src/components/features/portfolio/PortfolioSummaryCard.test.tsx
it('displays backend-calculated total value', () => {
  const mockPortfolio = {
    cashBalance: 1000,
    totalValue: 1500, // Backend calculated (cash + holdings)
    // ...
  }

  render(<PortfolioSummaryCard portfolio={mockPortfolio} />)

  expect(screen.getByTestId('portfolio-total-value')).toHaveTextContent('$1,500.00')
})

it('calculates holdings value as difference', () => {
  const mockPortfolio = {
    cashBalance: 1000,
    totalValue: 1500,
  }

  render(<PortfolioSummaryCard portfolio={mockPortfolio} />)

  // Holdings value = 1500 - 1000 = 500
  expect(screen.getByText(/Holdings Value/)).toBeInTheDocument()
  expect(screen.getByText('$500.00')).toBeInTheDocument()
})
```

3. **TradeForm Backtest**:
```typescript
// frontend/src/components/features/portfolio/TradeForm.test.tsx
it('fetches historical price when backtest mode enabled', async () => {
  render(<TradeForm {...defaultProps} />)

  // Enable backtest mode
  const backtestCheckbox = screen.getByTestId('backtest-mode-toggle')
  fireEvent.click(backtestCheckbox)

  // Set date
  const dateInput = screen.getByTestId('backtest-date-picker')
  fireEvent.change(dateInput, { target: { value: '2026-01-10' } })

  // Enter ticker
  const tickerInput = screen.getByTestId('trade-form-ticker-input')
  fireEvent.change(tickerInput, { target: { value: 'AAPL' } })

  // Should show loading, then price
  await waitFor(() => {
    expect(screen.getByTestId('trade-form-price-input')).toHaveValue('150.25')
  })
})
```

### Manual Testing (Weekend Specific)

**Test on Sunday, January 19, 2026**:

1. **TradeForm - Current Price**:
   - Navigate to portfolio
   - Click "Execute Trade"
   - Type ticker "AAPL"
   - ✅ EXPECT: Shows Friday's (Jan 16) price, not error
   - ✅ EXPECT: Timestamp shows "Live market price (as of Friday...)"

2. **TradeForm - Backtest Mode**:
   - Enable backtest mode
   - Set date to "2026-01-10" (Friday)
   - Type ticker "AAPL"
   - ✅ EXPECT: Shows estimated execution price for Jan 10
   - ✅ EXPECT: Info text: "Trade will execute with historical price from selected date"

3. **Total Value Display**:
   - View portfolio dashboard
   - ✅ EXPECT: Total Value = Cash + (Shares × Friday's Price)
   - ✅ EXPECT: Holdings Value shows non-zero if stocks owned
   - ✅ EXPECT: No "$NaN" or "undefined"

4. **Daily Change**:
   - ✅ EXPECT: Shows change from previous trading day (Friday → Friday, so likely $0.00)
   - ⚠️ NOTE: On Monday, should show change from Friday's close

## Edge Cases

1. **Market Holidays**: MLK Day (Jan 20, 2026)
   - Should use last trading day (Jan 16, Friday)
   - Backend has `MarketCalendar.is_trading_day()` logic

2. **No Holdings**: Portfolio with only cash
   - Total Value = Cash Balance
   - Holdings Value = $0.00 (don't show section)

3. **Partial Price Failures**: Some tickers succeed, some fail
   - Show partial results
   - Log warnings for failed tickers

## Success Criteria

- [ ] Backtest mode shows estimated execution price when date is set
- [ ] Weekend ticker search shows last trading day's price (no error)
- [ ] Total value correctly shows cash + holdings value on weekends
- [ ] No duplicate price fetching (use backend calculations)
- [ ] All existing tests pass
- [ ] New tests added for backtest price fetching
- [ ] Manual testing on Sunday/Monday confirms correct behavior
- [ ] No ESLint errors, no TypeScript `any` types
- [ ] Code follows existing patterns (TanStack Query, hooks)

## Files to Modify

### Frontend
- `frontend/src/components/features/portfolio/TradeForm.tsx` - Use historical price query when backtest mode enabled
- `frontend/src/components/features/portfolio/PortfolioSummaryCard.tsx` - Remove duplicate calculation, use backend totalValue
- `frontend/src/hooks/useHistoricalPriceQuery.ts` - **NEW FILE** - Historical price fetching hook
- `frontend/src/services/api/prices.ts` - Add `checkHistoricalPrice` and `getHistoricalPrice` functions
- `frontend/src/hooks/__tests__/useHistoricalPriceQuery.test.ts` - **NEW FILE** - Tests for new hook
- `frontend/src/components/features/portfolio/PortfolioSummaryCard.test.tsx` - Update tests for backend value usage
- `frontend/src/components/features/portfolio/TradeForm.test.tsx` - Add backtest price test

## References

- Backend `/prices/{ticker}/check?date={date}` endpoint: `backend/src/zebu/adapters/inbound/api/prices.py:410`
- Backend `/prices/{ticker}/history` endpoint: `backend/src/zebu/adapters/inbound/api/prices.py:242`
- Backend `_get_last_trading_day()`: `backend/src/zebu/adapters/outbound/market_data/alpha_vantage_adapter.py:762`
- Backend `MarketCalendar`: `backend/src/zebu/infrastructure/market_calendar.py`
- Frontend price API: `frontend/src/services/api/prices.ts`

## Architecture Compliance

- ✅ Clean Architecture: Frontend uses backend calculations (separation of concerns)
- ✅ No business logic in UI components
- ✅ TanStack Query for data fetching
- ✅ Type safety maintained
- ✅ Error handling with graceful fallbacks

## Notes

- The root issue is the frontend trying to be "too smart" by recalculating values that the backend already computed correctly
- Backend already handles weekends/holidays via `_get_last_trading_day()` and `MarketCalendar`
- By trusting backend calculations, we get simpler frontend code and consistent behavior
