# Task 023: Real Price Display UI

**Created**: 2025-12-28
**Agent**: frontend-swe
**Estimated Effort**: 3-4 hours
**Dependencies**: Task 018 (PricePoint foundation), can proceed in parallel with Task 020
**Related PRs**: N/A (new work)

## Objective

Implement frontend UI to display real-time stock prices in the portfolio dashboard. This task makes the portfolio valuation visible to users and demonstrates the market data integration.

**Key Independence**: This task can proceed in **parallel** with backend Task 020 (Alpha Vantage Adapter) because we can mock the API endpoints using MSW (already set up in the frontend).

## Context

Currently, the portfolio dashboard shows static portfolio data (name, cash balance) but doesn't display real-time holdings valuations. This task adds:
- API integration for price fetching
- Real-time portfolio value calculation
- Price staleness indicators
- Loading and error states

### Architecture References
- [implementation-guide.md](../docs/architecture/20251228_phase2-market-data/implementation-guide.md#task-020-frontend-price-display-3-4-hours)
- [interfaces.md](../docs/architecture/20251228_phase2-market-data/interfaces.md#pricepoint-data-structure)

## Success Criteria

- [ ] `usePriceQuery` hook implemented with TanStack Query
- [ ] PortfolioCard shows real-time portfolio value (cash + holdings)
- [ ] Individual holding rows show current price and value
- [ ] Price staleness indicator (e.g., "Updated 5 minutes ago")
- [ ] Loading states during price fetch
- [ ] Error handling for API failures
- [ ] MSW handlers for price endpoint
- [ ] Unit tests for price display logic
- [ ] E2E test for full price display flow

## Implementation Details

### 1. Price API Client

**File**: `frontend/src/api/prices.ts`

```typescript
import { apiClient } from './client';
import { PricePointSchema, type PricePoint } from './schemas';

/**
 * Fetch current price for a ticker
 */
export async function getCurrentPrice(ticker: string): Promise<PricePoint> {
  const response = await apiClient.get(`/api/v1/prices/${ticker}`);
  return PricePointSchema.parse(response.data);
}

/**
 * Batch fetch prices for multiple tickers
 * Uses Promise.allSettled to handle individual failures gracefully
 */
export async function getBatchPrices(
  tickers: string[]
): Promise<Map<string, PricePoint>> {
  const results = await Promise.allSettled(
    tickers.map(ticker => getCurrentPrice(ticker))
  );

  const priceMap = new Map<string, PricePoint>();
  results.forEach((result, index) => {
    if (result.status === 'fulfilled') {
      priceMap.set(tickers[index], result.value);
    }
  });

  return priceMap;
}
```

### 2. PricePoint Schema (Zod)

**File**: `frontend/src/api/schemas.ts`

Add to existing schemas:

```typescript
import { z } from 'zod';

// Money schema (already exists from Task 018)
const MoneySchema = z.object({
  amount: z.number(),
  currency: z.string(),
});

// PricePoint schema matching backend DTO
export const PricePointSchema = z.object({
  ticker: z.object({
    symbol: z.string(),
  }),
  price: MoneySchema,
  timestamp: z.string().datetime(), // ISO 8601 string
  source: z.string(),
  interval: z.string().optional(),
  // Optional OHLCV fields
  open: MoneySchema.optional(),
  high: MoneySchema.optional(),
  low: MoneySchema.optional(),
  close: MoneySchema.optional(),
  volume: z.number().optional(),
});

export type PricePoint = z.infer<typeof PricePointSchema>;
```

### 3. Price Query Hook

**File**: `frontend/src/hooks/usePriceQuery.ts`

```typescript
import { useQuery } from '@tanstack/react-query';
import { getCurrentPrice, getBatchPrices } from '../api/prices';
import type { PricePoint } from '../api/schemas';

/**
 * Hook to fetch current price for a single ticker
 * Uses TanStack Query for caching and automatic refetching
 */
export function usePriceQuery(ticker: string) {
  return useQuery({
    queryKey: ['price', ticker],
    queryFn: () => getCurrentPrice(ticker),
    staleTime: 5 * 60 * 1000, // 5 minutes
    refetchInterval: 5 * 60 * 1000, // Auto-refetch every 5 minutes
    retry: 3,
  });
}

/**
 * Hook to fetch prices for multiple tickers
 * Returns a Map<ticker, PricePoint> for easy lookup
 */
export function useBatchPricesQuery(tickers: string[]) {
  return useQuery({
    queryKey: ['prices', ...tickers.sort()],
    queryFn: () => getBatchPrices(tickers),
    staleTime: 5 * 60 * 1000,
    enabled: tickers.length > 0, // Only run if we have tickers
    retry: 3,
  });
}

/**
 * Utility hook for price staleness calculation
 */
export function usePriceStaleness(pricePoint: PricePoint | undefined) {
  if (!pricePoint) return null;

  const now = new Date();
  const priceTime = new Date(pricePoint.timestamp);
  const diffMs = now.getTime() - priceTime.getTime();
  const diffMinutes = Math.floor(diffMs / 60000);

  if (diffMinutes < 1) return 'Just now';
  if (diffMinutes < 60) return `${diffMinutes} minute${diffMinutes > 1 ? 's' : ''} ago`;

  const diffHours = Math.floor(diffMinutes / 60);
  if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;

  const diffDays = Math.floor(diffHours / 24);
  return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
}
```

### 4. Update PortfolioCard Component

**File**: `frontend/src/components/PortfolioCard.tsx`

Modify to show real-time portfolio value:

```typescript
import { useBatchPricesQuery, usePriceStaleness } from '../hooks/usePriceQuery';

interface PortfolioCardProps {
  portfolio: Portfolio;
}

export function PortfolioCard({ portfolio }: PortfolioCardProps) {
  // Extract tickers from holdings
  const tickers = portfolio.holdings.map(h => h.ticker);

  // Fetch prices for all holdings
  const { data: priceMap, isLoading, error } = useBatchPricesQuery(tickers);

  // Calculate total portfolio value
  const portfolioValue = useMemo(() => {
    if (!priceMap) return portfolio.cash_balance;

    const holdingsValue = portfolio.holdings.reduce((sum, holding) => {
      const price = priceMap.get(holding.ticker);
      if (!price) return sum;
      return sum + (price.price.amount * holding.shares);
    }, 0);

    return portfolio.cash_balance + holdingsValue;
  }, [portfolio, priceMap]);

  // Determine most stale price (for indicator)
  const stalestPrice = useMemo(() => {
    if (!priceMap || priceMap.size === 0) return null;

    const prices = Array.from(priceMap.values());
    return prices.reduce((oldest, current) => {
      return new Date(current.timestamp) < new Date(oldest.timestamp)
        ? current
        : oldest;
    }, prices[0]);
  }, [priceMap]);

  const staleness = usePriceStaleness(stalestPrice);

  return (
    <div className="portfolio-card">
      <h2>{portfolio.name}</h2>

      {/* Portfolio Value */}
      <div className="portfolio-value">
        <span className="label">Total Value</span>
        {isLoading ? (
          <span className="loading">Loading prices...</span>
        ) : error ? (
          <span className="error">Error loading prices</span>
        ) : (
          <>
            <span className="amount">${portfolioValue.toFixed(2)}</span>
            {staleness && (
              <span className="staleness">Updated {staleness}</span>
            )}
          </>
        )}
      </div>

      {/* Cash Balance */}
      <div className="cash-balance">
        <span className="label">Cash</span>
        <span className="amount">${portfolio.cash_balance.toFixed(2)}</span>
      </div>

      {/* Holdings */}
      <div className="holdings">
        <h3>Holdings</h3>
        {portfolio.holdings.length === 0 ? (
          <p className="empty">No holdings yet</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Ticker</th>
                <th>Shares</th>
                <th>Price</th>
                <th>Value</th>
              </tr>
            </thead>
            <tbody>
              {portfolio.holdings.map(holding => {
                const price = priceMap?.get(holding.ticker);
                const value = price ? price.price.amount * holding.shares : null;

                return (
                  <tr key={holding.ticker}>
                    <td>{holding.ticker}</td>
                    <td>{holding.shares}</td>
                    <td>
                      {isLoading ? (
                        <span className="loading">...</span>
                      ) : price ? (
                        `$${price.price.amount.toFixed(2)}`
                      ) : (
                        <span className="error">N/A</span>
                      )}
                    </td>
                    <td>
                      {value !== null ? `$${value.toFixed(2)}` : 'N/A'}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
```

### 5. MSW Handlers for Price Endpoint

**File**: `frontend/src/mocks/handlers.ts`

Add new handlers for price endpoint:

```typescript
import { http, HttpResponse } from 'msw';

const handlers = [
  // ... existing handlers ...

  // Get current price for a ticker
  http.get('/api/v1/prices/:ticker', ({ params }) => {
    const { ticker } = params;

    // Mock prices for common stocks
    const mockPrices: Record<string, number> = {
      'AAPL': 192.53,
      'GOOGL': 140.93,
      'MSFT': 374.58,
      'TSLA': 248.48,
      'AMZN': 178.25,
    };

    const price = mockPrices[ticker as string];
    if (!price) {
      return HttpResponse.json(
        { error: 'Ticker not found', ticker },
        { status: 404 }
      );
    }

    return HttpResponse.json({
      ticker: { symbol: ticker },
      price: { amount: price, currency: 'USD' },
      timestamp: new Date().toISOString(),
      source: 'mock',
      interval: 'current',
    });
  }),
];

export { handlers };
```

### 6. Testing Strategy

**Unit Tests** (`frontend/src/hooks/__tests__/usePriceQuery.test.ts`):

```typescript
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { usePriceQuery, usePriceStaleness } from '../usePriceQuery';
import { server } from '../../mocks/server';
import { http, HttpResponse } from 'msw';

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
}

describe('usePriceQuery', () => {
  it('fetches price successfully', async () => {
    const { result } = renderHook(() => usePriceQuery('AAPL'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toMatchObject({
      ticker: { symbol: 'AAPL' },
      price: { amount: 192.53, currency: 'USD' },
      source: 'mock',
    });
  });

  it('handles ticker not found error', async () => {
    const { result } = renderHook(() => usePriceQuery('INVALID'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error).toBeTruthy();
  });
});

describe('usePriceStaleness', () => {
  it('returns "Just now" for recent prices', () => {
    const pricePoint = {
      ticker: { symbol: 'AAPL' },
      price: { amount: 192.53, currency: 'USD' },
      timestamp: new Date().toISOString(),
      source: 'mock',
    };

    const { result } = renderHook(() => usePriceStaleness(pricePoint));
    expect(result.current).toBe('Just now');
  });

  it('returns minutes for slightly old prices', () => {
    const fiveMinutesAgo = new Date(Date.now() - 5 * 60 * 1000);
    const pricePoint = {
      ticker: { symbol: 'AAPL' },
      price: { amount: 192.53, currency: 'USD' },
      timestamp: fiveMinutesAgo.toISOString(),
      source: 'mock',
    };

    const { result } = renderHook(() => usePriceStaleness(pricePoint));
    expect(result.current).toBe('5 minutes ago');
  });
});
```

**E2E Tests** (`frontend/tests/price-display.spec.ts`):

```typescript
import { test, expect } from '@playwright/test';

test.describe('Price Display', () => {
  test('shows portfolio value with real prices', async ({ page }) => {
    await page.goto('/');

    // Wait for portfolio to load
    await expect(page.locator('h2').first()).toContainText('Portfolio');

    // Check that prices are loading
    await expect(page.locator('.loading')).toBeVisible();

    // Wait for prices to load
    await expect(page.locator('.loading')).not.toBeVisible();

    // Check that portfolio value is displayed
    const portfolioValue = page.locator('.portfolio-value .amount');
    await expect(portfolioValue).toBeVisible();

    // Verify staleness indicator
    await expect(page.locator('.staleness')).toContainText('ago');
  });

  test('shows individual holding prices', async ({ page }) => {
    await page.goto('/');

    // Wait for holdings table
    await page.waitForSelector('.holdings table');

    // Check first holding row
    const firstRow = page.locator('.holdings tbody tr').first();

    // Should have ticker, shares, price, value
    await expect(firstRow.locator('td').nth(0)).not.toBeEmpty(); // Ticker
    await expect(firstRow.locator('td').nth(1)).not.toBeEmpty(); // Shares
    await expect(firstRow.locator('td').nth(2)).toContainText('$'); // Price
    await expect(firstRow.locator('td').nth(3)).toContainText('$'); // Value
  });

  test('handles price fetch errors gracefully', async ({ page }) => {
    // Mock API error
    await page.route('/api/v1/prices/*', route =>
      route.fulfill({ status: 500, body: 'Server error' })
    );

    await page.goto('/');

    // Should show error state
    await expect(page.locator('.error')).toContainText('Error loading prices');
  });
});
```

## Files to Create/Modify

### New Files

**API Layer**:
- `frontend/src/api/prices.ts` (~50 lines) - Price fetching functions

**Hooks**:
- `frontend/src/hooks/usePriceQuery.ts` (~80 lines) - TanStack Query hooks

**Tests**:
- `frontend/src/hooks/__tests__/usePriceQuery.test.ts` (~100 lines)
- `frontend/tests/price-display.spec.ts` (~80 lines) - E2E tests

### Modified Files

**Schemas**:
- `frontend/src/api/schemas.ts` - Add PricePointSchema

**Components**:
- `frontend/src/components/PortfolioCard.tsx` - Add price display logic

**MSW**:
- `frontend/src/mocks/handlers.ts` - Add price endpoint handlers

**Types** (if needed):
- `frontend/src/types/portfolio.ts` - Ensure Portfolio type includes holdings

## Styling Notes

Use Tailwind CSS for styling (already configured). Key classes:
- `.loading` - Skeleton loaders or spinners
- `.error` - Error text (text-red-600)
- `.staleness` - Subtle text (text-gray-500, text-sm)
- Monetary values: `font-mono` for better alignment

Consider adding:
- Color coding for positive/negative changes (future enhancement)
- Animated loading states (shimmer effect)
- Refresh button to manually trigger price updates

## Performance Considerations

1. **Batch Fetching**: Use `useBatchPricesQuery` to fetch all prices in parallel (not sequential)
2. **Caching**: TanStack Query handles caching automatically (5 min stale time)
3. **Auto-refetch**: Prices refresh every 5 minutes in background
4. **Error Recovery**: Retry failed requests up to 3 times
5. **Stale Data**: Show stale prices with indicator rather than nothing

## Testing Checklist

- [ ] Unit tests for `usePriceQuery` hook (success, error cases)
- [ ] Unit tests for `usePriceStaleness` hook (time calculations)
- [ ] Unit tests for price calculations in PortfolioCard
- [ ] E2E test for full price display flow
- [ ] E2E test for error handling
- [ ] MSW handlers working in development mode
- [ ] Type checking passes (tsc --noEmit)
- [ ] Linting passes (eslint)
- [ ] All tests pass (~42 existing + ~15 new = ~57 total)

## Implementation Notes

### Backend Mocking Strategy

Since Task 020 (Alpha Vantage Adapter) will be in progress, we mock the backend API:
1. MSW handlers provide realistic responses
2. Frontend development proceeds independently
3. Once Task 020 merges, disable MSW in production mode
4. Integration testing happens naturally when both PRs merge

### Future Enhancements (Phase 2b)

This task implements **basic price display**. Future enhancements:
- Price change indicators (+2.3%, -1.5%)
- Price charts (sparklines, detailed charts)
- Historical price queries (`get_price_at()`)
- Real-time updates via WebSocket (Phase 4+)
- Market status indicator (open/closed)

### Accessibility

Ensure:
- Prices have proper ARIA labels for screen readers
- Loading states announced ("Loading prices")
- Error states announced ("Error loading prices")
- Monetary values formatted consistently ($XXX.XX)

## Definition of Done

- [ ] All success criteria met
- [ ] All tests passing (~57 total)
- [ ] Type checking passes (tsc --noEmit)
- [ ] Linting passes (eslint)
- [ ] MSW handlers working correctly
- [ ] PR created with clear description
- [ ] Self-reviewed for architecture compliance
- [ ] Progress document created in `agent_tasks/progress/`
- [ ] Ready for review

## Next Steps

After this task completes:
- **Integration**: Test with real backend from Task 020
- **Phase 2b**: Add price charts and historical data display
- **Phase 3**: Backtesting UI integration
- **Phase 4+**: Real-time updates via WebSocket

This task demonstrates user-facing value early and can proceed in parallel with backend infrastructure work!
