# Task 084: Fix Price Chart "Invalid Price Data" Error

**Priority**: HIGH  
**Complexity**: Medium  
**Estimated Effort**: 1-2 hours  
**Agent**: frontend-swe

## Problem

The price chart on the portfolio detail page displays **"Invalid price data"** instead of showing the actual price history chart. This occurs because:

1. Backend `/api/v1/prices/{ticker}/history` endpoint returns prices as **strings** (e.g., `"271.0100"`)
2. Frontend `PriceChart` component expects `price.amount` to be a **number**
3. When the component tries to validate prices with `Number.isFinite(firstPrice)`, it fails because the price is a string

### Current Behavior
- User navigates to portfolio detail page
- Price chart section shows: **"Invalid price data"**
- Console error: None (silent failure in validation)
- Network request succeeds (200 OK)

### Expected Behavior
- Price chart displays line chart with historical prices
- Shows price statistics (current price, change, change %)
- Time range selector works (1D, 1W, 1M, 3M, 1Y, ALL)

## Root Cause Analysis

**Backend Response** (`/api/v1/prices/AAPL/history?start=2025-12-09&end=2026-01-09`):
```json
{
  "ticker": "AAPL",
  "prices": [
    {
      "ticker": "AAPL",
      "price": "271.0100",        // ❌ String, not number
      "currency": "USD",
      "timestamp": "2026-01-05T14:10:30.343797Z",
      "source": "alpha_vantage",
      "interval": "1day"
    }
  ]
}
```

**Frontend Type** (`frontend/src/types/price.ts`):
```typescript
export interface Money {
  amount: number  // ✅ Expects number
  currency: string
}

export interface PricePoint {
  ticker: Ticker
  price: Money  // ✅ Expects Money with number amount
  timestamp: string
  source: 'alpha_vantage' | 'cache' | 'database'
  interval: 'real-time' | '1day' | '1hour' | '5min' | '1min'
}
```

**Validation in PriceChart** (`frontend/src/components/features/PriceChart/PriceChart.tsx:102`):
```typescript
const firstPrice = data.prices[0]!.price.amount  // Gets string "271.0100"
const lastPrice = data.prices[data.prices.length - 1]!.price.amount  // Gets string

// Validate prices are numbers
if (!Number.isFinite(firstPrice) || !Number.isFinite(lastPrice)) {  // ❌ Fails because strings
  return (
    <div className="price-chart">
      <p className="text-gray-600 dark:text-gray-400">Invalid price data</p>
    </div>
  )
}
```

## Solution

Update `getPriceHistory()` in `frontend/src/services/api/prices.ts` to parse string prices to numbers, similar to how `getBatchPrices()` was fixed in PR #100.

### Implementation

**Before:**
```typescript
export async function getPriceHistory(
  ticker: string,
  startDate: string,
  endDate: string
): Promise<PriceHistory> {
  try {
    const response = await apiClient.get<PriceHistory>(
      `/prices/${ticker}/history`,
      { params: { start: startDate, end: endDate } }
    )
    return response.data  // ❌ Returns strings as-is
  } catch {
    // ... fallback to mock data
  }
}
```

**After:**
```typescript
export async function getPriceHistory(
  ticker: string,
  startDate: string,
  endDate: string
): Promise<PriceHistory> {
  try {
    // Backend returns prices as strings, need to parse to numbers
    const response = await apiClient.get<{
      ticker: string
      prices: Array<{
        ticker: string
        price: string  // Backend sends string
        currency: string
        timestamp: string
        source: string
        interval: string
      }>
    }>('/prices/${ticker}/history', {
      params: { start: startDate, end: endDate },
    })

    // Convert backend response to PriceHistory with number prices
    const priceHistory: PriceHistory = {
      ticker: response.data.ticker,
      prices: response.data.prices.map((point) => ({
        ticker: { symbol: point.ticker },
        price: {
          amount: parseFloat(point.price),  // ✅ Parse string to number
          currency: point.currency,
        },
        timestamp: point.timestamp,
        source: point.source as 'alpha_vantage' | 'cache' | 'database',
        interval: point.interval as '1day' | 'real-time' | '1hour' | '5min' | '1min',
      })),
      source: response.data.prices[0]?.source || 'unknown',
      cached: response.data.prices[0]?.source === 'cache',
    }

    return priceHistory
  } catch {
    // ... fallback to mock data
  }
}
```

## Acceptance Criteria

1. ✅ Price chart displays correctly on portfolio detail page
2. ✅ Chart shows line graph with historical prices
3. ✅ Price statistics display (current price, change, change %)
4. ✅ All time range buttons work (1D, 1W, 1M, 3M, 1Y, ALL)
5. ✅ No "Invalid price data" error
6. ✅ All existing tests pass
7. ✅ Type safety maintained (no `any` types)

## Testing Strategy

### Unit Tests
- Add/update tests for `getPriceHistory()` to verify:
  - String prices converted to numbers
  - Response structure matches `PriceHistory` type
  - Error handling still works

### Manual Testing with Playwright MCP

**CRITICAL**: You MUST verify the fix using Playwright browser automation via MCP tools before marking complete.

```typescript
// Test script to verify fix
async function verifyPriceChart(page) {
  // 1. Navigate to portfolio detail page
  await page.goto('http://localhost:5173/portfolio/<portfolio-id>');
  await page.waitForLoadState('networkidle');
  
  // 2. Check that price chart is visible (not error state)
  const bodyText = await page.locator('body').textContent();
  const hasInvalidError = bodyText?.includes('Invalid price data');
  
  if (hasInvalidError) {
    throw new Error('FAIL: Price chart still showing "Invalid price data" error');
  }
  
  // 3. Verify chart elements exist
  const hasChart = await page.locator('svg').count() > 0;  // Recharts renders SVG
  const hasTimeButtons = bodyText?.includes('1D') && bodyText?.includes('1M');
  
  if (!hasChart || !hasTimeButtons) {
    throw new Error('FAIL: Price chart elements not found');
  }
  
  // 4. Test time range selector
  await page.getByRole('button', { name: '1W' }).click();
  await page.waitForTimeout(1000);
  
  // 5. Verify no errors in console
  const errors = await page.evaluate(() => {
    const logs = [];
    const originalError = console.error;
    console.error = (...args) => {
      logs.push(args.join(' '));
      originalError.apply(console, args);
    };
    return logs;
  });
  
  if (errors.length > 0) {
    throw new Error(`FAIL: Console errors: ${errors.join(', ')}`);
  }
  
  console.log('✅ PASS: Price chart working correctly');
}
```

Use the MCP Playwright tools:
```typescript
// In your agent code
await mcp_microsoft_pla_browser_navigate({ url: 'http://localhost:5173/portfolio/...' });
await mcp_microsoft_pla_browser_snapshot();  // Take snapshot to verify
const networkReqs = await mcp_microsoft_pla_browser_network_requests({ includeStatic: false });
// Verify /prices/{ticker}/history was called and succeeded
```

**Before marking task complete**, you MUST:
1. Run the app locally (`task docker:up:all`)
2. Use Playwright MCP to navigate to a portfolio detail page
3. Verify the price chart displays correctly (no "Invalid price data")
4. Test clicking different time range buttons (1D, 1W, 1M, etc.)
5. Include screenshots or snapshots in your progress doc

## Files to Modify

- `frontend/src/services/api/prices.ts` - Update `getPriceHistory()` to parse string prices
- `frontend/src/services/api/prices.test.ts` - Update/add tests (if exists)

## Related Work

- **Backend**: `/api/v1/prices/{ticker}/history` endpoint returns prices as strings (from Alpha Vantage)
- **PR #100**: Fixed similar issue in `getBatchPrices()` - use that as reference
- **Uses**: `PriceChart` component in portfolio detail page

## Notes

- This is a **type mismatch** between backend (strings) and frontend (numbers)
- The fix is straightforward: parse strings to numbers using `parseFloat()`
- Similar to PR #100's fix for batch prices
- Backend returning strings is correct (matches Alpha Vantage API format)
- Frontend must handle the conversion

## Verification Checklist

Before submitting PR, confirm:
- [ ] Code changes implemented
- [ ] Unit tests passing
- [ ] Frontend quality checks pass (`task quality:frontend`)
- [ ] **Playwright MCP manual test completed successfully**
- [ ] Screenshots/evidence included in progress doc
- [ ] Price chart displays on portfolio detail page
- [ ] No "Invalid price data" error
- [ ] Time range selector buttons work
- [ ] Network tab shows successful `/prices/{ticker}/history` call
