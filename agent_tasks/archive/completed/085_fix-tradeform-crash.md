# Task 085: Fix TradeForm Intermittent Crash

**Priority**: HIGH
**Estimated Effort**: 2-3 hours
**Agent**: frontend-swe
**Related**: Pre-deployment polish, critical UX bug

## Objective

Fix the intermittent crash in TradeForm component that occurs on initial page load with error: "Cannot read property 'toString' of undefined" at line 39.

## Problem Description

**Symptoms**:
- TradeForm crashes on first load (intermittent)
- Error: `Cannot read property 'toString' of undefined` at line 39
- Works correctly after page reload
- Causes poor first-time user experience

**Impact**:
- Users cannot execute trades on first visit
- Requires manual page refresh to recover
- Blocking issue for deployment

## Current Behavior

1. User navigates to portfolio detail page
2. TradeForm component loads
3. Crash occurs before form is rendered
4. Page reload fixes the issue

## Root Cause Investigation

**File**: `frontend/src/components/features/trade/TradeForm.tsx`

Likely causes:
1. Race condition with async data loading
2. Missing null/undefined check on price data
3. Component rendering before required data is available
4. Incorrect initial state for controlled form inputs

## Requirements

### Must Fix
1. **Defensive Programming**: Add null/undefined checks before calling `.toString()`
2. **Loading State**: Don't render form until all required data is available
3. **Error Boundaries**: Wrap TradeForm in error boundary to prevent full page crash
4. **Type Safety**: Ensure all data is properly typed and validated

### Should Improve
5. **Loading Skeleton**: Show skeleton UI while data loads
6. **Error Recovery**: Display helpful error message if data fetch fails
7. **Retry Logic**: Allow user to retry if price fetch fails

## Implementation Guide

### 1. Identify the Crash Location

```typescript
// Current code (line 39 area - FIND THIS)
// Likely something like:
const formattedPrice = currentPrice.toString()
// OR
value={price.toString()}
```

### 2. Add Defensive Checks

```typescript
// Before
const formattedPrice = currentPrice.toString()

// After
const formattedPrice = currentPrice?.toString() ?? '0.00'
// OR
if (!currentPrice) {
  return <LoadingSkeleton />
}
const formattedPrice = currentPrice.toString()
```

### 3. Add Error Boundary (Recommended)

**File**: `frontend/src/components/features/trade/TradeForm.tsx`

```typescript
import { ErrorBoundary } from 'react-error-boundary'

export function TradeFormWithErrorBoundary(props: TradeFormProps) {
  return (
    <ErrorBoundary
      fallbackRender={({ error, resetErrorBoundary }) => (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4">
          <h3 className="font-semibold text-red-900">Failed to Load Trade Form</h3>
          <p className="mt-1 text-sm text-red-700">{error.message}</p>
          <button
            onClick={resetErrorBoundary}
            className="mt-3 rounded bg-red-600 px-4 py-2 text-sm text-white hover:bg-red-700"
          >
            Try Again
          </button>
        </div>
      )}
    >
      <TradeForm {...props} />
    </ErrorBoundary>
  )
}
```

### 4. Improve Data Loading

**Check usePriceQuery hook usage**:

```typescript
// Ensure loading state is handled
const { data: price, isLoading, error } = usePriceQuery(ticker)

if (isLoading) {
  return <TradeFormSkeleton />
}

if (error || !price) {
  return <TradeFormError onRetry={() => refetch()} />
}

// Now safe to use price
```

## Testing Requirements

### Unit Tests

**File**: `frontend/src/components/features/trade/TradeForm.test.tsx`

Add tests for edge cases:

```typescript
describe('TradeForm', () => {
  it('should handle undefined price gracefully', () => {
    const { container } = render(<TradeForm ticker="AAPL" />)
    expect(container).toBeInTheDocument()
    // Should show loading or default value, not crash
  })

  it('should show loading state when price is fetching', () => {
    // Mock usePriceQuery to return isLoading: true
    const { getByText } = render(<TradeForm ticker="AAPL" />)
    expect(getByText(/loading/i)).toBeInTheDocument()
  })

  it('should show error state when price fetch fails', () => {
    // Mock usePriceQuery to return error
    const { getByText } = render(<TradeForm ticker="AAPL" />)
    expect(getByText(/error/i)).toBeInTheDocument()
  })

  it('should allow retry after error', () => {
    const refetch = vi.fn()
    // Mock usePriceQuery with error and refetch function
    const { getByText } = render(<TradeForm ticker="AAPL" />)
    fireEvent.click(getByText(/try again/i))
    expect(refetch).toHaveBeenCalled()
  })
})
```

### Manual Testing via Playwright MCP

**Critical**: Reproduce the crash condition and verify fix.

```typescript
// Test script to run via MCP
async function testTradeFormCrash(page) {
  // 1. Clear browser cache and storage (simulate first visit)
  await page.context().clearCookies()
  await page.evaluate(() => localStorage.clear())

  // 2. Navigate to portfolio page
  await page.goto('http://localhost:5173')
  // Login and navigate to portfolio

  // 3. Check for crash
  const hasError = await page.locator('text=/cannot read property/i').count()
  if (hasError > 0) {
    console.error('❌ TradeForm still crashes on first load')
    return false
  }

  // 4. Verify form renders
  const tradeForm = await page.locator('[data-testid="trade-form"]').count()
  if (tradeForm === 0) {
    console.error('❌ TradeForm did not render')
    return false
  }

  console.log('✅ TradeForm loads without crash')
  return true
}
```

**Run via MCP**:
```bash
# After implementing fix, run Playwright test
mcp_microsoft_pla_browser_run_code(
  code: testTradeFormCrash function above
)
```

### E2E Test Coverage

**File**: `frontend/tests/e2e/trade.spec.ts`

Ensure existing E2E tests cover:
- ✅ TradeForm loads on portfolio page
- ✅ User can execute BUY trade
- ✅ User can execute SELL trade
- ✅ Form validation works

If crash is intermittent, add test that runs multiple times:

```typescript
test('TradeForm should not crash on repeated navigation', async ({ page }) => {
  for (let i = 0; i < 5; i++) {
    await page.goto('/portfolios/1')
    await expect(page.locator('[data-testid="trade-form"]')).toBeVisible()
    await page.goto('/')
  }
})
```

## Files to Modify

**Required**:
- `frontend/src/components/features/trade/TradeForm.tsx` - Add null checks, loading state
- `frontend/src/components/features/trade/TradeForm.test.tsx` - Add edge case tests

**Recommended**:
- `frontend/src/components/features/trade/TradeFormSkeleton.tsx` (new) - Loading skeleton component
- `frontend/src/components/features/trade/TradeFormError.tsx` (new) - Error state component

## Success Criteria

- [ ] TradeForm does not crash on initial page load (verified via multiple test runs)
- [ ] All null/undefined checks added before `.toString()` calls
- [ ] Loading state displayed while data fetches
- [ ] Error boundary catches any unexpected errors
- [ ] Error state allows user to retry
- [ ] All unit tests pass
- [ ] E2E tests pass with repeated navigation
- [ ] Playwright MCP verification confirms fix works

## References

- **Error Boundaries**: [React Error Boundary Docs](https://react.dev/reference/react/Component#catching-rendering-errors-with-an-error-boundary)
- **Optional Chaining**: [MDN Optional Chaining](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Operators/Optional_chaining)
- **Related Issue**: BACKLOG.md UX Improvements section
- **Related Docs**: `agent_tasks/progress/2025-12-29_01-34-20_fix-critical-integration-bugs.md`

## Notes

- This is a **blocking bug for deployment** - must be fixed before Stage 1 Proxmox deployment
- Intermittent nature suggests race condition or timing issue
- Consider adding React.Suspense boundary if not already present
- May be related to TanStack Query suspense mode settings
