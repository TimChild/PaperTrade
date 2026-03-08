# Task 146: Improve Error State Handling for Price Data

**Agent**: frontend-swe
**Priority**: HIGH
**Date**: 2026-01-17

## Problem Statement

When the backend returns errors (503 Rate Limit Exceeded, 500 Server Error, etc.), the frontend silently falls back to **random mock data** without any indication to the user that something is wrong. This creates a confusing user experience where:

- Users see different price data on each page refresh (random mock data)
- No error message indicates the backend is having issues
- Users might make trading decisions based on fake data
- The error is only visible in browser DevTools console

### Current Behavior

From [frontend/src/services/api/prices.ts](../../frontend/src/services/api/prices.ts#L101-L149):

```typescript
export async function getPriceHistory(
  ticker: string,
  startDate: string,
  endDate: string
): Promise<PriceHistory> {
  try {
    const response = await apiClient.get<...>(`/prices/${ticker}/history`, {
      params: { start: startDate, end: endDate },
    })
    return priceHistory
  } catch {
    // Backend endpoint doesn't exist yet or failed
    // Return mock data for development
    console.warn(`Price history API not available, using mock data for ${ticker}`)
    return generateMockPriceHistory(ticker, startDate, endDate)
  }
}
```

**Problems**:
1. All errors (network, 503, 500, 404) are handled the same way
2. No user-facing error indication
3. Mock data generation makes debugging harder (data changes on each request)
4. `console.warn()` is inadequate - users don't check console

## Objective

Implement proper error handling with clear user feedback:

1. **Distinguish error types**: Network errors, rate limits, server errors, no data
2. **Show error UI**: Display clear error messages instead of mock data
3. **Provide actionable guidance**: Tell users what to do (retry, wait, contact support)
4. **Remove mock data fallback**: Only use mock data in development mode with explicit indicator

## Requirements

### 1. Define Error Types

Create a type-safe error classification system:

```typescript
// src/types/errors.ts
export type ApiErrorType =
  | 'rate_limit'      // 503 from rate limiting
  | 'server_error'    // 500 server error
  | 'not_found'       // 404 ticker not found
  | 'network_error'   // Network/timeout issues
  | 'unknown'         // Other errors

export interface ApiError {
  type: ApiErrorType
  message: string
  retryAfter?: number  // Seconds until retry (for rate limits)
  details?: string     // Technical details for debugging
}
```

### 2. Improve getPriceHistory() Error Handling

```typescript
export async function getPriceHistory(
  ticker: string,
  startDate: string,
  endDate: string
): Promise<PriceHistory> {
  try {
    const response = await apiClient.get<...>(`/prices/${ticker}/history`, {
      params: { start: startDate, end: endDate },
    })
    return transformToPriceHistory(response.data)
  } catch (error) {
    // Parse error into ApiError type
    const apiError = parseApiError(error)

    // In development mode, show mock data with warning banner
    if (import.meta.env.DEV) {
      console.warn('[DEV] API error, using mock data:', apiError.message)
      return {
        ...generateMockPriceHistory(ticker, startDate, endDate),
        error: apiError,  // Include error in response
      }
    }

    // In production, throw structured error for component to handle
    throw apiError
  }
}

function parseApiError(error: unknown): ApiError {
  if (axios.isAxiosError(error)) {
    const status = error.response?.status
    const detail = error.response?.data?.detail

    switch (status) {
      case 503:
        if (detail?.includes('Rate limit')) {
          return {
            type: 'rate_limit',
            message: 'Market data temporarily unavailable due to high demand',
            retryAfter: 60,  // Estimate based on rate limit
            details: detail
          }
        }
        return { type: 'server_error', message: 'Service temporarily unavailable', details: detail }

      case 404:
        return { type: 'not_found', message: `No data found for ${ticker}`, details: detail }

      case 500:
        return { type: 'server_error', message: 'Server error occurred', details: detail }

      default:
        return { type: 'unknown', message: error.message, details: detail }
    }
  }

  // Network/timeout errors
  return { type: 'network_error', message: 'Unable to connect to server' }
}
```

### 3. Update PriceHistory Type

```typescript
// src/types/price.ts
export interface PriceHistory {
  ticker: string
  prices: PricePoint[]
  source: string
  cached: boolean
  error?: ApiError  // Optional error info (for dev mode)
}
```

### 4. Create Error Display Component

```tsx
// src/components/features/PriceChart/PriceChartError.tsx
interface PriceChartErrorProps {
  error: ApiError
  ticker: string
  onRetry?: () => void
}

export function PriceChartError({ error, ticker, onRetry }: PriceChartErrorProps) {
  return (
    <div className="flex flex-col items-center justify-center h-64 p-6 bg-red-50 border border-red-200 rounded-lg">
      <div className="text-red-600 mb-4">
        {error.type === 'rate_limit' && <ClockIcon className="w-12 h-12" />}
        {error.type === 'server_error' && <ExclamationIcon className="w-12 h-12" />}
        {error.type === 'network_error' && <WifiOffIcon className="w-12 h-12" />}
        {error.type === 'not_found' && <SearchIcon className="w-12 h-12" />}
      </div>

      <h3 className="text-lg font-semibold text-gray-900 mb-2">
        {getErrorTitle(error.type)}
      </h3>

      <p className="text-sm text-gray-600 text-center mb-4">
        {error.message}
      </p>

      {error.type === 'rate_limit' && error.retryAfter && (
        <p className="text-xs text-gray-500 mb-4">
          Please try again in {error.retryAfter} seconds
        </p>
      )}

      {onRetry && error.type !== 'not_found' && (
        <button
          onClick={onRetry}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          Retry
        </button>
      )}

      {import.meta.env.DEV && error.details && (
        <details className="mt-4 text-xs text-gray-500">
          <summary>Technical Details</summary>
          <pre className="mt-2 p-2 bg-gray-100 rounded">{error.details}</pre>
        </details>
      )}
    </div>
  )
}

function getErrorTitle(type: ApiErrorType): string {
  switch (type) {
    case 'rate_limit': return 'Too Many Requests'
    case 'server_error': return 'Server Error'
    case 'network_error': return 'Connection Error'
    case 'not_found': return 'Data Not Found'
    default: return 'Something Went Wrong'
  }
}
```

### 5. Update PriceChart Component

```tsx
// src/components/features/PriceChart/PriceChart.tsx
export function PriceChart({ ticker, range }: PriceChartProps) {
  const { data, isLoading, error, refetch } = usePriceHistory(ticker, range)

  if (isLoading) {
    return <PriceChartSkeleton />
  }

  if (error) {
    return (
      <PriceChartError
        error={error as ApiError}
        ticker={ticker}
        onRetry={refetch}
      />
    )
  }

  // Show dev warning banner if using mock data
  if (import.meta.env.DEV && data?.error) {
    return (
      <div className="relative">
        <div className="absolute top-0 left-0 right-0 bg-yellow-100 border-b border-yellow-400 px-4 py-2 text-sm text-yellow-800 z-10">
          ⚠️ Development Mode: Using mock data due to API error
        </div>
        <div className="pt-12">
          <PriceChartView data={data} />
        </div>
      </div>
    )
  }

  return <PriceChartView data={data} />
}
```

### 6. Update usePriceHistory Hook

```typescript
// src/hooks/usePriceHistory.ts
export function usePriceHistory(ticker: string, range: TimeRange) {
  const { start, end } = getDateRange(range)

  return useQuery({
    queryKey: ['priceHistory', ticker, range],
    queryFn: async () => {
      try {
        return await getPriceHistory(ticker, start, end)
      } catch (error) {
        // Re-throw ApiError for component to handle
        if (isApiError(error)) {
          throw error
        }
        // Wrap unknown errors
        throw { type: 'unknown', message: String(error) } as ApiError
      }
    },
    staleTime: 5 * 60 * 1000,
    enabled: Boolean(ticker),
    retry: (failureCount, error) => {
      // Don't retry 404s (ticker not found)
      if (isApiError(error) && error.type === 'not_found') {
        return false
      }
      // Retry network errors and server errors once
      return failureCount < 1
    },
  })
}

function isApiError(error: unknown): error is ApiError {
  return (
    typeof error === 'object' &&
    error !== null &&
    'type' in error &&
    'message' in error
  )
}
```

## Testing Requirements

### Unit Tests

1. **Error parsing**:
   - `test_parseApiError_rate_limit_503()`
   - `test_parseApiError_not_found_404()`
   - `test_parseApiError_network_timeout()`

2. **Component rendering**:
   - `test_PriceChartError_shows_rate_limit_message()`
   - `test_PriceChartError_shows_retry_button()`
   - `test_PriceChartError_hides_retry_for_404()`

3. **Development mode**:
   - `test_dev_mode_shows_mock_data_with_warning()`
   - `test_production_mode_throws_error()`

### Integration Tests

1. **End-to-end error flow**:
   - Mock 503 API response
   - Verify error UI appears
   - Click retry button
   - Verify refetch is called

2. **Error state persistence**:
   - Switch between time ranges while in error state
   - Verify appropriate error handling for each request

## Success Criteria

- [ ] `ApiError` type defined with all error types
- [ ] `parseApiError()` correctly classifies errors
- [ ] `PriceChartError` component displays appropriate UI for each error type
- [ ] Development mode shows mock data with warning banner
- [ ] Production mode shows error UI instead of mock data
- [ ] Retry button works for retriable errors
- [ ] 404 errors don't show retry button
- [ ] Unit tests cover all error types (80%+ coverage)
- [ ] Manual test: Simulate rate limit → See proper error message
- [ ] Manual test: Disconnect network → See connection error

## Non-Requirements

- ❌ Don't add error tracking/logging service integration (future task)
- ❌ Don't implement automatic retry with exponential backoff (future enhancement)
- ❌ Don't change backend error response format

## UX Considerations

### Error Message Guidelines

**Rate Limit (503)**:
- Title: "Too Many Requests"
- Message: "Market data temporarily unavailable due to high demand. Please try again in 60 seconds."
- Action: Show countdown timer, auto-enable retry button

**Server Error (500)**:
- Title: "Server Error"
- Message: "We're experiencing technical difficulties. Please try again in a moment."
- Action: Retry button

**Network Error**:
- Title: "Connection Error"
- Message: "Unable to connect to server. Check your internet connection."
- Action: Retry button

**Not Found (404)**:
- Title: "Data Not Found"
- Message: "No price data available for [TICKER]. This may not be a valid ticker symbol."
- Action: No retry button (suggest search)

### Visual Design

- Use color-coded backgrounds: Red for errors, Yellow for warnings
- Include relevant icons for each error type
- Keep technical details collapsed by default (only show in dev mode)
- Make retry buttons prominent and easy to click

## References

- **Architecture**: [docs/architecture/technical-boundaries.md](../../docs/architecture/technical-boundaries.md)
- **Current Implementation**: [frontend/src/services/api/prices.ts](../../frontend/src/services/api/prices.ts)
- **Related Backend Issue**: Task 145 (caching fix)
- **Design System**: Use existing Tailwind classes for consistency

## Example User Experience After Fix

**Before** (Current):
1. User opens portfolio
2. Backend is rate limited (503)
3. Frontend shows random chart data (different each refresh)
4. User is confused: "Why does my portfolio value keep changing?"

**After** (With Fix):
1. User opens portfolio
2. Backend is rate limited (503)
3. Frontend shows clear error message: "Too Many Requests - Please try again in 60 seconds"
4. User understands the situation and waits/retries
5. (In dev mode: Shows mock data with yellow warning banner)

## Notes

- This task focuses on frontend error handling only
- Backend caching fix (Task 145) will reduce rate limit errors
- Together, these tasks provide a complete solution to the user-reported issue
- Consider adding Sentry or similar for production error tracking (future task)
