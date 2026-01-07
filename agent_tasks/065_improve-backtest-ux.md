# Task 065: Improve Backtest Mode UX - Handle Missing Historical Data

**Status**: Not Started
**Priority**: HIGH (User-Facing Feature)
**Depends On**: None
**Estimated Effort**: 4-6 hours

## Objective

Fix the user experience issue where Backtest Mode fails with "Market data unavailable" error when historical price data doesn't exist in the database. Users should either get helpful guidance or the system should automatically fetch the required data.

## Problem Statement

### Current Behavior (Broken UX)
1. User enables "Backtest Mode" on trade form
2. User selects a historical date (e.g., 2025-12-01)
3. User enters ticker (e.g., IBM) and quantity
4. User clicks "Execute Backtest Buy Order"
5. **Error**: "Failed to execute trade: Request failed with status code 503"
6. Console error: "Market data unavailable: No price data available for IBM at 2025-12-01 00:00:00+00:00"

### Root Cause
The `get_price_at()` method in `AlphaVantageAdapter` queries the price repository for historical data. If no data exists for that ticker/date combination, it raises `MarketDataUnavailableError` with HTTP 503.

The backtest feature **requires** historical price data to exist in the database, but:
- Background scheduler only fetches **current** prices, not historical
- No automatic mechanism to fetch historical data when needed
- Users have no way to know if historical data exists
- Users have no way to trigger historical data fetching

### Expected Behavior (Good UX)
Users should have one of these experiences:

**Option A: Auto-Fetch Historical Data** (Recommended)
1. User selects backtest date
2. System checks if historical data exists for that date range
3. If missing, automatically fetch from Alpha Vantage in background
4. Show loading indicator: "Fetching historical prices..."
5. Enable trade execution once data is ready

**Option B: Show Clear Warning** (Fallback)
1. User selects ticker and backtest date
2. System checks if historical data exists
3. If missing, show warning: "⚠️ No historical data available for IBM on 12/1/2025. Try a more recent date."
4. Disable trade execution until valid date selected

**Option C: Pre-Populate Common Stocks** (Enhancement)
1. Background job fetches historical data for common stocks (S&P 500)
2. Backtest feature "just works" for popular tickers
3. Show warning for uncommon tickers

## Investigation

### Testing Steps (Already Completed)
Used Playwright MCP to test backtest mode:
1. ✅ Navigate to portfolio detail page
2. ✅ Enable backtest mode checkbox
3. ✅ Enter ticker: IBM
4. ✅ Enter quantity: 5
5. ✅ Select date: 2025-12-01
6. ✅ Click "Execute Backtest Buy Order"
7. ❌ Result: 503 error with "No price data available"

### Backend Code Analysis
From `backend/src/papertrade/adapters/outbound/market_data/alpha_vantage_adapter.py`:

```python
async def get_price_at(self, ticker: Ticker, timestamp: datetime) -> PricePoint:
    """Get the price for a ticker at a specific point in time.

    Queries price repository for historical data.
    """
    # Validate timestamp is not in the future
    if timestamp > datetime.now(UTC):
        raise MarketDataUnavailableError(
            f"Cannot get price for future timestamp: {timestamp}"
        )

    # Query repository for price at timestamp
    if not self.price_repository:
        raise MarketDataUnavailableError(
            "Price repository not configured"
        )

    price = await self.price_repository.get_price_at(ticker, timestamp)

    if not price:  # ← This is where it fails
        raise MarketDataUnavailableError(
            f"No price data available for {ticker.symbol} at {timestamp}"
        )

    return price
```

The method **only queries existing data** - it doesn't fetch from Alpha Vantage if data is missing.

### Related Code
From `backend/src/papertrade/adapters/inbound/api/portfolios.py`:

```python
# Fetch market price (current or historical based on as_of)
try:
    if request.as_of:
        # For backtesting - get historical price
        price_point = await market_data.get_price_at(ticker, request.as_of)
    else:
        # Current price - with caching
        price_point = await market_data.get_current_price(ticker)
except (TickerNotFoundError, MarketDataUnavailableError) as e:
    raise HTTPException(status_code=503, detail=str(e)) from e
```

## Recommended Solution: Option A (Auto-Fetch)

### Frontend Changes

**1. Add Data Availability Check**

Before enabling trade execution in backtest mode, check if historical data exists:

```typescript
// frontend/src/components/features/portfolio/TradeForm.tsx

const [isLoadingHistoricalData, setIsLoadingHistoricalData] = useState(false)

// When backtest date changes, check data availability
useEffect(() => {
  if (backtestMode && backtestDate && ticker) {
    checkHistoricalDataAvailability()
  }
}, [backtestMode, backtestDate, ticker])

async function checkHistoricalDataAvailability() {
  setIsLoadingHistoricalData(true)

  try {
    // Check if data exists (new endpoint)
    const response = await api.checkHistoricalData({
      ticker,
      date: backtestDate
    })

    if (!response.available) {
      // Trigger fetch in background
      await api.fetchHistoricalData({
        ticker,
        start: backtestDate,
        end: backtestDate
      })
    }
  } finally {
    setIsLoadingHistoricalData(false)
  }
}
```

**2. Update UI with Loading State**

```tsx
{backtestMode && (
  <div className="mt-4">
    {isLoadingHistoricalData && (
      <div className="flex items-center gap-2 text-blue-600">
        <Spinner />
        <span>Fetching historical prices for {ticker}...</span>
      </div>
    )}
  </div>
)}

<Button
  disabled={!isFormValid || isLoadingHistoricalData}
  loading={isSubmitting || isLoadingHistoricalData}
>
  {isLoadingHistoricalData
    ? 'Loading Historical Data...'
    : 'Execute Backtest Buy Order'
  }
</Button>
```

### Backend Changes

**1. Add Historical Data Check Endpoint**

```python
# backend/src/papertrade/adapters/inbound/api/prices.py

@router.get("/check/{ticker}")
async def check_historical_data(
    ticker: str,
    date: datetime,
    price_repo: PriceRepository = Depends(get_price_repository),
) -> dict:
    """Check if historical data exists for a ticker on a specific date.

    Returns:
        {"available": bool, "closest_date": datetime | None}
    """
    ticker_obj = Ticker(ticker)
    price = await price_repo.get_price_at(ticker_obj, date)

    return {
        "available": price is not None,
        "closest_date": price.timestamp if price else None
    }
```

**2. Add On-Demand Historical Data Fetch**

```python
# backend/src/papertrade/adapters/inbound/api/prices.py

@router.post("/fetch-historical")
async def fetch_historical_data(
    request: FetchHistoricalRequest,
    market_data: MarketDataPort = Depends(get_market_data),
) -> dict:
    """Fetch historical data for a ticker and date range.

    This endpoint is called by the frontend when backtest mode
    detects missing historical data.
    """
    ticker = Ticker(request.ticker)

    # Fetch from Alpha Vantage
    history = await market_data.get_price_history(
        ticker,
        start=request.start,
        end=request.end
    )

    return {
        "fetched": len(history),
        "date_range": {
            "start": request.start,
            "end": request.end
        }
    }
```

**3. Update `get_price_history` to Store Data**

Ensure `get_price_history` stores fetched data in the database:

```python
async def get_price_history(
    self, ticker: Ticker, start: datetime, end: datetime
) -> list[PricePoint]:
    """Fetch and store historical data."""

    # Check cache/database first
    cached_data = await self.price_repository.get_price_range(ticker, start, end)

    if len(cached_data) == expected_days:
        return cached_data

    # Fetch from API
    api_data = await self._fetch_from_alpha_vantage(ticker, start, end)

    # Store in database
    await self.price_repository.bulk_save(ticker, api_data)

    return api_data
```

## Alternative Solution: Option B (Warning Message)

If auto-fetch is too complex for Phase 1, implement a clear warning:

### Frontend Changes

```typescript
const [historicalDataAvailable, setHistoricalDataAvailable] = useState(true)

useEffect(() => {
  if (backtestMode && backtestDate && ticker) {
    api.checkHistoricalData({ ticker, date: backtestDate })
      .then(response => {
        setHistoricalDataAvailable(response.available)
      })
  }
}, [backtestMode, backtestDate, ticker])

// In render:
{backtestMode && !historicalDataAvailable && (
  <Alert severity="warning">
    ⚠️ No historical data available for {ticker} on {backtestDate}.
    Try a more recent date or a different ticker.
  </Alert>
)}

<Button disabled={!isFormValid || !historicalDataAvailable}>
  Execute Backtest Buy Order
</Button>
```

## Testing

### Manual Testing
1. Enable backtest mode
2. Enter ticker: IBM
3. Select historical date: 2025-12-01
4. **Expected**: Loading indicator appears
5. **Expected**: Historical data fetches automatically
6. **Expected**: Trade executes successfully with historical price
7. Try again with same date: should use cached data (instant)

### E2E Test

```typescript
// frontend/tests/e2e/backtest.spec.ts

test('should auto-fetch historical data for backtest trades', async ({ page }) => {
  await page.goto('/portfolio/xxx')

  // Enable backtest mode
  await page.getByTestId('backtest-mode-toggle').check()

  // Enter trade details
  await page.getByTestId('trade-form-ticker-input').fill('AAPL')
  await page.getByTestId('trade-form-quantity-input').fill('10')
  await page.getByTestId('backtest-date-picker').fill('2025-11-01')

  // Wait for historical data fetch
  await expect(page.getByText(/fetching historical prices/i)).toBeVisible()
  await expect(page.getByText(/fetching historical prices/i)).toBeHidden({ timeout: 10000 })

  // Execute trade
  await page.getByTestId('trade-form-buy-button').click()

  // Verify success
  await expect(page.getByText(/buy order executed successfully/i)).toBeVisible()
})
```

## Success Criteria

- [ ] Backtest mode detects missing historical data
- [ ] System automatically fetches missing data OR shows clear warning
- [ ] User can successfully execute backtest trades
- [ ] Loading indicators show during data fetch
- [ ] Error messages are clear and actionable
- [ ] E2E tests verify backtest functionality
- [ ] No 503 errors when using backtest mode

## Files to Create/Modify

### Frontend
- `frontend/src/components/features/portfolio/TradeForm.tsx` (add data check)
- `frontend/src/services/api/prices.ts` (add check/fetch endpoints)

### Backend
- `backend/src/papertrade/adapters/inbound/api/prices.py` (add endpoints)
- `backend/src/papertrade/adapters/outbound/market_data/alpha_vantage_adapter.py` (ensure history stores data)

### Tests
- `frontend/tests/e2e/backtest.spec.ts` (create)
- `backend/tests/integration/api/test_prices.py` (add tests)

## Implementation Notes

### Rate Limiting Considerations
- Alpha Vantage free tier: 5 calls/min, 500/day
- Fetching daily data uses TIME_SERIES_DAILY (1 API call)
- One call can fetch up to 100 days of data
- Show warning if date range is too large

### Date Handling
- Market is closed weekends/holidays
- Get closest **trading day** before requested date
- Show actual price date to user: "Using price from 11/29/2025 (closest trading day)"

## Commands

```bash
# Test locally
task dev
# Navigate to http://localhost:5173/portfolio/xxx
# Enable backtest mode and try different tickers/dates

# Run E2E tests
task test:e2e

# Check backend logs
docker logs papertrade-backend-1 -f
```

## References

- Alpha Vantage API: https://www.alphavantage.co/documentation/#daily
- PR #78: Original backtest implementation
- `architecture_plans/phase3c-analytics/backtesting.md`: Design docs
