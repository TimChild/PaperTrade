# Task 011: Fix Frontend Tests with MSW (Mock Service Worker)

## Priority
**P1 - CRITICAL**: Must be completed before Phase 2 development

## Context
After Task 009 (Frontend-Backend Integration), 3 frontend tests in `App.test.tsx` are failing because they make real API calls to the backend. In the test environment, there's no backend running, causing tests to show loading spinner indefinitely and log network errors.

**Current Status**: 20/23 tests passing (87%)  
**Target**: 23/23 tests passing (100%)

## Problem Statement

The failing tests are:
1. `App.test.tsx > App > renders without crashing`
2. `App.test.tsx > App > displays dashboard page by default`
3. `App.test.tsx > App > renders portfolio summary section`

**Root Cause**:
```typescript
// Tests use real API client which makes HTTP requests
export function usePortfolio(portfolioId: string) {
  return useQuery({
    queryKey: ['portfolio', portfolioId],
    queryFn: () => portfoliosApi.getById(portfolioId),  // ← Real HTTP call
  })
}
```

Without a running backend, requests fail and components show loading state forever.

## Solution: Mock Service Worker (MSW)

MSW intercepts HTTP requests at the network level and returns mock responses, making tests reliable and fast without requiring a real backend.

### Why MSW vs. Other Solutions?

| Approach | Pros | Cons |
|----------|------|------|
| **MSW** ✅ | • Network-level mocking<br>• Same code in tests and dev<br>• Realistic request/response<br>• Industry standard | • Requires setup |
| Mock TanStack Query | • Simple | • Doesn't test API layer<br>• Unrealistic |
| Mock Axios directly | • Lower level control | • Brittle<br>• Mocks implementation not behavior |
| Test with real backend | • Most realistic | • Slow<br>• Flaky<br>• Complex CI setup |

**Recommendation**: Use MSW (industry best practice)

## Implementation Steps

### 1. Install MSW (~5 minutes)

```bash
cd frontend
npm install -D msw@latest
```

**Expected Version**: msw@2.x

### 2. Create MSW Handlers (~30 minutes)

**File**: `frontend/src/mocks/handlers.ts`

```typescript
import { http, HttpResponse } from 'msw'

const API_BASE_URL = 'http://localhost:8000/api/v1'

// Mock data
const mockPortfolio = {
  id: '00000000-0000-0000-0000-000000000001',
  user_id: '00000000-0000-0000-0000-000000000001',
  name: 'Test Portfolio',
  created_at: '2024-01-01T00:00:00Z',
}

const mockBalance = {
  amount: '10000.00',
  currency: 'USD',
}

const mockHoldings = {
  holdings: [
    {
      ticker: 'AAPL',
      quantity: '10.00',
      cost_basis: '1500.00',
    },
  ],
}

const mockTransactions = {
  transactions: [
    {
      id: '00000000-0000-0000-0000-000000000002',
      portfolio_id: '00000000-0000-0000-0000-000000000001',
      transaction_type: 'DEPOSIT',
      timestamp: '2024-01-01T00:00:00Z',
      cash_change_amount: '10000.00',
      cash_change_currency: 'USD',
      notes: 'Initial deposit',
    },
  ],
  page: 1,
  per_page: 50,
  total: 1,
}

// API handlers
export const handlers = [
  // List portfolios
  http.get(`${API_BASE_URL}/portfolios`, () => {
    return HttpResponse.json({
      portfolios: [mockPortfolio],
    })
  }),

  // Get portfolio by ID
  http.get(`${API_BASE_URL}/portfolios/:id`, ({ params }) => {
    return HttpResponse.json(mockPortfolio)
  }),

  // Get portfolio balance
  http.get(`${API_BASE_URL}/portfolios/:id/balance`, () => {
    return HttpResponse.json(mockBalance)
  }),

  // Get portfolio holdings
  http.get(`${API_BASE_URL}/portfolios/:id/holdings`, () => {
    return HttpResponse.json(mockHoldings)
  }),

  // Get portfolio transactions
  http.get(`${API_BASE_URL}/portfolios/:id/transactions`, () => {
    return HttpResponse.json(mockTransactions)
  }),

  // Create portfolio
  http.post(`${API_BASE_URL}/portfolios`, async ({ request }) => {
    const body = await request.json()
    return HttpResponse.json({
      portfolio_id: '00000000-0000-0000-0000-000000000001',
      transaction_id: '00000000-0000-0000-0000-000000000002',
    })
  }),

  // Deposit cash
  http.post(`${API_BASE_URL}/portfolios/:id/deposit`, () => {
    return HttpResponse.json({
      transaction_id: '00000000-0000-0000-0000-000000000003',
    })
  }),

  // Withdraw cash
  http.post(`${API_BASE_URL}/portfolios/:id/withdraw`, () => {
    return HttpResponse.json({
      transaction_id: '00000000-0000-0000-0000-000000000004',
    })
  }),

  // Execute trade
  http.post(`${API_BASE_URL}/portfolios/:id/trades`, () => {
    return HttpResponse.json({
      transaction_id: '00000000-0000-0000-0000-000000000005',
    })
  }),
]
```

### 3. Create Test Setup (~15 minutes)

**File**: `frontend/src/test/setup.ts`

```typescript
import { beforeAll, afterEach, afterAll } from 'vitest'
import { setupServer } from 'msw/node'
import { handlers } from '../mocks/handlers'

// Create MSW server instance
export const server = setupServer(...handlers)

// Start server before all tests
beforeAll(() => {
  server.listen({ onUnhandledRequest: 'error' })
})

// Reset handlers after each test
afterEach(() => {
  server.resetHandlers()
})

// Clean up after all tests
afterAll(() => {
  server.close()
})
```

### 4. Update Vitest Config (~5 minutes)

**File**: `frontend/vite.config.ts`

Add setup file to Vitest configuration:

```typescript
export default defineConfig({
  // ... existing config
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],  // ← Add this line
  },
})
```

### 5. Update App.test.tsx (~30 minutes)

**File**: `frontend/src/App.test.tsx`

Update tests to wait for async data loading:

```typescript
import { describe, it, expect } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import App from '@/App'

function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  })
}

describe('App', () => {
  it('renders without crashing', async () => {
    const queryClient = createTestQueryClient()

    render(
      <QueryClientProvider client={queryClient}>
        <App />
      </QueryClientProvider>
    )

    // Wait for data to load (MSW will respond)
    await waitFor(() => {
      expect(screen.getByText('Portfolio Dashboard')).toBeInTheDocument()
    })
  })

  it('displays dashboard page by default', async () => {
    const queryClient = createTestQueryClient()

    render(
      <QueryClientProvider client={queryClient}>
        <App />
      </QueryClientProvider>
    )

    await waitFor(() => {
      expect(screen.getByText(/Track your investments and performance/i)).toBeInTheDocument()
    })
  })

  it('renders portfolio summary section', async () => {
    const queryClient = createTestQueryClient()

    render(
      <QueryClientProvider client={queryClient}>
        <App />
      </QueryClientProvider>
    )

    // Wait for portfolio data to load
    await waitFor(() => {
      expect(screen.getByText('Test Portfolio')).toBeInTheDocument()
    })
  })
})
```

**Key Changes**:
- Made tests `async`
- Use `waitFor()` to wait for API responses
- MSW returns mock data, components render successfully

### 6. Verify Tests Pass (~15 minutes)

```bash
cd frontend
npm test

# Expected output:
# ✓ src/App.test.tsx (3)
# ✓ src/utils/formatters.test.ts (11)
# ✓ src/components/features/portfolio/PortfolioSummaryCard.test.tsx (6)
# ✓ src/components/HealthCheck.test.tsx (3)
#
# Test Files  4 passed (4)
#      Tests  23 passed (23)  ← All passing!
```

## File Structure

After implementation:

```
frontend/
├── src/
│   ├── mocks/
│   │   ├── handlers.ts          # ← NEW: MSW request handlers
│   │   └── browser.ts           # (future) Browser integration for dev
│   ├── test/
│   │   └── setup.ts             # ← NEW: Test setup with MSW
│   ├── App.test.tsx             # ← UPDATED: Add async/await
│   └── ...
├── vite.config.ts               # ← UPDATED: Add setupFiles
└── package.json                 # ← UPDATED: Add msw dependency
```

## Testing Strategy

### What MSW Tests

✅ **Tests**:
- API client integration
- Request/response handling
- Data adapters (DTO → UI types)
- Component behavior with async data
- Loading states
- Error states (can mock error responses)

❌ **Doesn't Test**:
- Real backend implementation
- Network failures
- Backend validation logic

This is **good** - unit tests should focus on frontend behavior, not backend.

### Future Enhancements

After this task, can add:

1. **Error scenario tests**:
```typescript
it('displays error when API fails', async () => {
  server.use(
    http.get('/api/v1/portfolios/:id', () => {
      return HttpResponse.json({ detail: 'Not found' }, { status: 404 })
    })
  )
  
  render(<App />)
  await waitFor(() => {
    expect(screen.getByText('Portfolio not found')).toBeInTheDocument()
  })
})
```

2. **Loading state tests**:
```typescript
it('shows loading spinner initially', () => {
  render(<App />)
  expect(screen.getByRole('status', { name: 'Loading' })).toBeInTheDocument()
})
```

3. **Form submission tests**:
```typescript
it('handles trade form submission', async () => {
  render(<TradeForm />)
  
  await userEvent.type(screen.getByLabelText('Ticker'), 'AAPL')
  await userEvent.type(screen.getByLabelText('Quantity'), '10')
  await userEvent.click(screen.getByRole('button', { name: 'Buy' }))
  
  await waitFor(() => {
    expect(screen.getByText('Trade executed successfully')).toBeInTheDocument()
  })
})
```

## Success Criteria

- [ ] MSW installed (`npm list msw` shows version 2.x)
- [ ] Handlers created in `frontend/src/mocks/handlers.ts`
- [ ] Test setup created in `frontend/src/test/setup.ts`
- [ ] Vitest config updated with setupFiles
- [ ] App.test.tsx updated with async/waitFor
- [ ] All 23 frontend tests passing (100%)
- [ ] No console errors during test run
- [ ] CI/CD pipeline tests pass

## Estimated Time

**Total**: 2 hours

| Task | Time |
|------|------|
| Install MSW | 5 min |
| Create handlers | 30 min |
| Create test setup | 15 min |
| Update Vitest config | 5 min |
| Update App.test.tsx | 30 min |
| Verify and debug | 15 min |
| Documentation | 20 min |

## Dependencies

**NPM Packages**:
- `msw@latest` (2.x) - Mock Service Worker

**Existing**:
- Vitest (already installed)
- @testing-library/react (already installed)

## Resources

- [MSW Documentation](https://mswjs.io/docs/)
- [MSW with Vitest](https://mswjs.io/docs/integrations/vitest)
- [TanStack Query Testing](https://tanstack.com/query/latest/docs/react/guides/testing)

## Related Tasks

- Task 009: Frontend-Backend Integration (created the failing tests)
- Task 010: Code Quality Assessment (identified this issue)
- Future: Add error scenario tests (backlog)
- Future: Add form interaction tests (backlog)

## Notes

- MSW v2.x uses `http` instead of `rest` from v1.x
- MSW can also be used in development mode (browser) for testing without backend
- Handlers can be reused for Storybook integration
- Mock data should match backend DTO structure exactly

## Acceptance Criteria

When this task is complete:

1. ✅ All 23 frontend tests pass
2. ✅ Tests complete in <10 seconds
3. ✅ No network requests made during tests
4. ✅ CI/CD pipeline green
5. ✅ Mock data matches backend DTOs
6. ✅ Code coverage maintained or improved
7. ✅ Documentation updated (if needed)

---

**Created**: 2025-12-28  
**Priority**: P1 - Critical  
**Estimated Effort**: 2 hours  
**Assigned To**: Frontend Software Engineer (or available agent)
