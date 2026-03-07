# Task 162: Implement Weekend/Holiday Price Handling with Date-Aware E2E Tests

**Agent**: backend-swe
**Priority**: High
**Estimated Effort**: 3-4 hours
**Created**: 2026-01-18

## Context

Users currently get "Ticker not found" errors when trying to view portfolio values or execute trades on weekends/holidays. This is poor UX - users should see their portfolio values using cached prices from the last trading day.

**Manual Testing (Sunday, Jan 18, 2026):**
```bash
curl "http://localhost:8000/api/v1/prices/AAPL"
# Returns: {"detail":"Ticker not found: AAPL"}  ❌

# Database has cached data from Friday
psql> SELECT ticker, price_amount, timestamp FROM price_history
      WHERE ticker = 'AAPL' ORDER BY timestamp DESC LIMIT 1;
# AAPL | 259.96 | 2026-01-15 01:36:08  ✅
```

## Problem Statement

The backend has correct infrastructure (MarketCalendar, 3-tier caching, _get_last_trading_day helper) but doesn't use it in the price fetching flow. On non-trading days, the adapter tries to fetch from Alpha Vantage API instead of serving cached prices from the last trading day.

## Requirements

### Backend Implementation

Modify `AlphaVantageAdapter.get_current_price()` to detect weekends/holidays and serve cached prices:

```python
async def get_current_price(self, ticker: Ticker) -> PricePoint:
    """Get current price with weekend/holiday awareness.

    Strategy:
    1. Check Redis cache (return if fresh)
    2. Check PostgreSQL (return if reasonably fresh)
    3. **NEW**: If weekend/holiday, get last trading day's cached price
    4. Fetch from Alpha Vantage API (if trading day and rate limit allows)
    5. Serve stale cache if rate limited
    """
    # Tier 1: Redis cache
    cached = await self.price_cache.get(ticker)
    if cached and not cached.is_stale(max_age=timedelta(hours=1)):
        return cached.with_source("cache")

    # Tier 2: PostgreSQL
    if self.price_repository:
        db_price = await self.price_repository.get_latest_price(
            ticker, max_age=timedelta(hours=4)
        )
        if db_price and not db_price.is_stale(max_age=timedelta(hours=4)):
            await self.price_cache.set(db_price, ttl=3600)
            return db_price.with_source("database")

    # NEW: Weekend/Holiday check - serve last trading day's cached price
    now = datetime.now(UTC)
    if not MarketCalendar.is_trading_day(now.date()):
        last_trading_day = self._get_last_trading_day(now)

        if self.price_repository:
            historical_price = await self.price_repository.get_price_at(
                ticker, last_trading_day
            )
            if historical_price:
                # Cache with longer TTL on weekends (2 hours)
                await self.price_cache.set(historical_price, ttl=7200)
                logger.info(
                    f"Markets closed, using last trading day price",
                    ticker=ticker.value,
                    current_date=now.date(),
                    last_trading_day=last_trading_day,
                )
                return historical_price.with_source("database")

        # No cached data available - raise error with helpful message
        raise MarketDataUnavailableError(
            f"Markets are closed and no cached price available for {ticker.value}"
        )

    # Tier 3: Fetch from API (trading days only)
    # ... existing API fetch logic ...
```

Similar logic for `get_batch_prices()` - check once if it's a trading day, route all tickers appropriately.

### E2E Test Updates

**CRITICAL**: E2E tests should test **real user experience** - no test-specific code paths, no mock auth.

Update tests to be **date-aware** and validate appropriate behavior:

```typescript
// frontend/tests/e2e/utils/date-helpers.ts
import { MarketCalendar } from './market-calendar'

export function isTradingDay(): boolean {
  return MarketCalendar.is_trading_day(new Date())
}

export function getExpectedBehavior() {
  return {
    isTradingDay: isTradingDay(),
    expectFreshPrices: isTradingDay(),
    expectCachedMessage: !isTradingDay(),
  }
}
```

```typescript
// Update tests to validate appropriate behavior
test('portfolio displays total value', async ({ page }) => {
  const { isTradingDay, expectCachedMessage } = getExpectedBehavior()

  await page.goto('/dashboard')

  // Total value should ALWAYS be visible
  const totalValue = page.getByTestId('total-value')
  await expect(totalValue).toBeVisible()

  if (!isTradingDay) {
    // Weekend: Show indicator that prices are from last trading day
    await expect(
      page.getByText(/prices from last trading day/i)
    ).toBeVisible()
  }

  // Portfolio value should be calculated correctly regardless of day
  await expect(totalValue).not.toContainText('$0.00')
})

test('user can execute a trade', async ({ page }) => {
  const { isTradingDay } = getExpectedBehavior()

  await page.goto('/dashboard')
  await page.getByRole('button', { name: /buy/i }).first().click()

  // Fill trade form
  await page.getByLabel(/ticker/i).fill('AAPL')
  await page.getByLabel(/quantity/i).fill('10')

  if (isTradingDay) {
    // Trading day: Should fetch current price and allow trade
    await expect(page.getByTestId('current-price')).toBeVisible()
    await expect(page.getByRole('button', { name: /confirm/i })).toBeEnabled()
  } else {
    // Weekend: Should show cached price and allow trade with warning
    await expect(
      page.getByText(/price from last trading day/i)
    ).toBeVisible()
    await expect(page.getByRole('button', { name: /confirm/i })).toBeEnabled()
  }
})
```

### Frontend Updates (if needed)

Add UI indicators when showing cached prices:

```typescript
// Show badge or text when prices are from last trading day
{!isTradingDay() && (
  <p className="text-sm text-muted-foreground">
    Prices from last trading day (markets closed)
  </p>
)}
```

## Testing Requirements

### Unit Tests
- ✅ Test weekend detection logic
- ✅ Test last trading day calculation
- ✅ Test fetching from cache when markets closed
- ✅ Test error when no cached data available
- ✅ Test normal API fetch on trading days

### Integration Tests
- ✅ Test full flow on simulated weekend (mock datetime)
- ✅ Test batch prices on weekend
- ✅ Test cache TTL extension on weekends

### E2E Tests
- ✅ Tests run on actual date
- ✅ Validate behavior appropriate for trading day vs weekend
- ✅ Both code paths get exercised (CI runs on different days)
- ✅ Use real Clerk authentication (existing setup)

## Success Criteria

1. **Weekend price fetching works**: `curl http://localhost:8000/api/v1/prices/AAPL` returns cached price on Sunday
2. **Batch prices work**: `curl http://localhost:8000/api/v1/prices/batch?tickers=AAPL,MSFT` returns cached prices on weekend
3. **All unit tests pass**: Including new weekend scenarios
4. **All integration tests pass**: With datetime mocking for deterministic testing
5. **All E2E tests pass**: On both trading days AND non-trading days
6. **No test-specific code in production**: No flags, no bypasses, clean implementation

## Files to Modify

**Backend:**
- `backend/src/zebu/adapters/outbound/market_data/alpha_vantage_adapter.py` - Add weekend logic
- `backend/tests/unit/test_alpha_vantage_adapter.py` - Add weekend unit tests
- `backend/tests/integration/test_alpha_vantage_adapter.py` - Add weekend integration tests

**Frontend:**
- `frontend/tests/e2e/utils/date-helpers.ts` - NEW: Date-aware test helpers
- `frontend/tests/e2e/trading.spec.ts` - Update with date-aware assertions
- `frontend/tests/e2e/portfolio-creation.spec.ts` - Update with date-aware assertions
- `frontend/src/components/PortfolioDashboard.tsx` - Add weekend indicator (optional UX improvement)

## Important Constraints

**DO NOT:**
- ❌ Add test-specific flags or environment variables
- ❌ Create separate authentication for tests
- ❌ Bypass weekend logic in any code path
- ❌ Seed test data

**DO:**
- ✅ Use real Clerk authentication in E2E tests
- ✅ Make E2E tests adapt to actual date
- ✅ Test real user experience
- ✅ Keep production code clean

## Architecture Compliance

- ✅ Weekend detection stays in adapter layer (infrastructure)
- ✅ Use existing `MarketCalendar` utility
- ✅ Use existing `_get_last_trading_day()` helper
- ✅ No domain logic changes needed
- ✅ Follows existing caching patterns

## Validation Steps

1. Test manually on weekend: `curl http://localhost:8000/api/v1/prices/AAPL`
2. Run backend tests: `task test:backend`
3. Run E2E tests: `task test:e2e`
4. Verify appropriate behavior on both trading days and weekends
5. Check logs show "Markets closed, using last trading day price" on weekends

---

**This approach tests real production behavior, maintains clean architecture, and provides excellent user experience on all days.**
