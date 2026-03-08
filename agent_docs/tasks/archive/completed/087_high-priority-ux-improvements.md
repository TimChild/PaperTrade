# Task 087: High-Priority UX Improvements

**Priority**: HIGH
**Estimated Effort**: 3-4 hours
**Agent**: frontend-swe
**Related**: Pre-deployment polish, user experience

## Objective

Implement high-value UX improvements that will significantly enhance the user experience for the first deployment on Proxmox.

## Scope

Focus on **quick wins** that prevent user frustration and improve polish:

1. ✅ **Portfolio Deletion** - Allow users to delete portfolios from dashboard
2. ✅ **Better Loading States** - Skeleton screens instead of blank pages
3. ✅ **Confirmation Dialogs** - Prevent accidental destructive actions
4. ✅ **Transaction History Search** - Find specific trades quickly
5. ⚠️ **Error State Improvements** - Helpful error messages when things fail

Out of scope (defer to Phase 4):
- ❌ Advanced filtering/sorting
- ❌ Bulk operations
- ❌ Export functionality
- ❌ Mobile-specific optimizations

---

## 1. Portfolio Deletion

### Problem
Users cannot delete portfolios. Once created, they're stuck forever.

### Solution
Add delete button to portfolio card on dashboard.

**File**: `frontend/src/components/features/portfolio/PortfolioCard.tsx`

```typescript
import { Trash2 } from 'lucide-react'
import { useState } from 'react'

export function PortfolioCard({ portfolio, onDelete }: PortfolioCardProps) {
  const [showConfirm, setShowConfirm] = useState(false)
  const deleteMutation = useDeletePortfolioMutation()

  const handleDelete = async () => {
    try {
      await deleteMutation.mutateAsync(portfolio.id)
      toast.success('Portfolio deleted')
      onDelete?.(portfolio.id)
    } catch (error) {
      toast.error('Failed to delete portfolio')
    }
  }

  return (
    <div className="relative rounded-lg border p-4 hover:shadow-md">
      {/* Existing portfolio content */}

      {/* Delete button - top-right corner */}
      <button
        onClick={() => setShowConfirm(true)}
        className="absolute right-2 top-2 rounded p-1 text-gray-400 hover:bg-red-50 hover:text-red-600"
        aria-label="Delete portfolio"
      >
        <Trash2 className="h-4 w-4" />
      </button>

      {/* Confirmation Dialog */}
      {showConfirm && (
        <ConfirmDialog
          title="Delete Portfolio?"
          message={`Are you sure you want to delete "${portfolio.name}"? This action cannot be undone.`}
          confirmLabel="Delete"
          onConfirm={handleDelete}
          onCancel={() => setShowConfirm(false)}
          variant="danger"
        />
      )}
    </div>
  )
}
```

**New Component**: `frontend/src/components/ui/ConfirmDialog.tsx`

```typescript
interface ConfirmDialogProps {
  title: string
  message: string
  confirmLabel: string
  onConfirm: () => void
  onCancel: () => void
  variant?: 'danger' | 'warning' | 'info'
}

export function ConfirmDialog({
  title,
  message,
  confirmLabel,
  onConfirm,
  onCancel,
  variant = 'info',
}: ConfirmDialogProps) {
  const variantStyles = {
    danger: 'bg-red-600 hover:bg-red-700',
    warning: 'bg-yellow-600 hover:bg-yellow-700',
    info: 'bg-blue-600 hover:bg-blue-700',
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="mx-4 max-w-md rounded-lg bg-white p-6 shadow-xl">
        <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
        <p className="mt-2 text-sm text-gray-600">{message}</p>

        <div className="mt-6 flex justify-end gap-3">
          <button
            onClick={onCancel}
            className="rounded-md px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            className={`rounded-md px-4 py-2 text-sm font-medium text-white ${variantStyles[variant]}`}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}
```

**API Hook**: `frontend/src/hooks/useDeletePortfolioMutation.ts` (new)

```typescript
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { deletePortfolio } from '@/services/api/portfolios'

export function useDeletePortfolioMutation() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: deletePortfolio,
    onSuccess: () => {
      // Invalidate portfolios list
      queryClient.invalidateQueries({ queryKey: ['portfolios'] })
    },
  })
}
```

**API Function**: `frontend/src/services/api/portfolios.ts`

```typescript
export async function deletePortfolio(portfolioId: number): Promise<void> {
  await apiClient.delete(`/portfolios/${portfolioId}`)
}
```

**Backend Endpoint** (already exists):
- `DELETE /api/v1/portfolios/{portfolio_id}` - Verify implementation

### Testing

```typescript
// frontend/src/components/features/portfolio/PortfolioCard.test.tsx
it('should show confirmation dialog when delete button clicked', async () => {
  const { getByLabelText, getByText } = render(<PortfolioCard portfolio={mockPortfolio} />)

  fireEvent.click(getByLabelText('Delete portfolio'))

  expect(getByText(/Are you sure/)).toBeInTheDocument()
  expect(getByText(/cannot be undone/)).toBeInTheDocument()
})

it('should delete portfolio when confirmed', async () => {
  const onDelete = vi.fn()
  const { getByLabelText, getByText } = render(
    <PortfolioCard portfolio={mockPortfolio} onDelete={onDelete} />
  )

  fireEvent.click(getByLabelText('Delete portfolio'))
  fireEvent.click(getByText('Delete'))

  await waitFor(() => {
    expect(onDelete).toHaveBeenCalledWith(mockPortfolio.id)
  })
})
```

---

## 2. Better Loading States

### Problem
Components show blank white space while loading data. Looks broken.

### Solution
Skeleton screens that match the layout of loaded content.

**Components to Add Skeletons**:
1. Portfolio list on dashboard
2. Portfolio detail page
3. Holdings table
4. Transaction history
5. Price charts

**Example**: `frontend/src/components/features/portfolio/PortfolioListSkeleton.tsx`

```typescript
export function PortfolioListSkeleton() {
  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {[1, 2, 3].map((i) => (
        <div key={i} className="animate-pulse rounded-lg border p-4">
          <div className="mb-2 h-6 w-3/4 rounded bg-gray-200" />
          <div className="mb-4 h-4 w-1/2 rounded bg-gray-200" />

          <div className="space-y-2">
            <div className="h-4 w-full rounded bg-gray-200" />
            <div className="h-4 w-5/6 rounded bg-gray-200" />
          </div>
        </div>
      ))}
    </div>
  )
}
```

**Usage**:

```typescript
export function PortfolioList() {
  const { data: portfolios, isLoading } = usePortfoliosQuery()

  if (isLoading) {
    return <PortfolioListSkeleton />
  }

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {portfolios?.map((p) => <PortfolioCard key={p.id} portfolio={p} />)}
    </div>
  )
}
```

**Skeletons to Create**:
- `PortfolioListSkeleton.tsx`
- `PortfolioDetailSkeleton.tsx`
- `HoldingsTableSkeleton.tsx`
- `TransactionHistorySkeleton.tsx`
- `PriceChartSkeleton.tsx`

---

## 3. Confirmation Dialogs

### Problem
Destructive actions (delete, sell all) happen without confirmation.

### Solution
ConfirmDialog component (created above for portfolio deletion).

**Apply to**:
1. ✅ Portfolio deletion (Task 1 above)
2. Trade execution (optional - might be annoying)
3. Large sell orders (e.g., selling >50% of holdings)

**Example**: Large Sell Order Confirmation

```typescript
// In TradeForm.tsx
const handleSubmit = async (data: TradeFormData) => {
  const isBigSell = data.orderType === 'SELL' &&
    data.quantity > (currentHolding?.quantity ?? 0) * 0.5

  if (isBigSell && !confirmBigSell) {
    setShowBigSellConfirm(true)
    return
  }

  // Execute trade...
}
```

---

## 4. Transaction History Search

### Problem
Users with many transactions cannot find specific trades.

### Solution
Simple search box that filters by ticker or date.

**File**: `frontend/src/components/features/transaction/TransactionHistory.tsx`

```typescript
import { useState } from 'react'
import { Search } from 'lucide-react'

export function TransactionHistory({ portfolioId }: TransactionHistoryProps) {
  const { data: transactions } = useTransactionsQuery(portfolioId)
  const [searchTerm, setSearchTerm] = useState('')

  const filteredTransactions = transactions?.filter((tx) => {
    const term = searchTerm.toLowerCase()
    return (
      tx.ticker.toLowerCase().includes(term) ||
      tx.orderType.toLowerCase().includes(term) ||
      tx.executedAt.includes(term)
    )
  })

  return (
    <div>
      {/* Search Box */}
      <div className="mb-4 relative">
        <Search className="absolute left-3 top-2.5 h-5 w-5 text-gray-400" />
        <input
          type="text"
          placeholder="Search by ticker, type, or date..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="w-full rounded-md border border-gray-300 pl-10 pr-4 py-2 focus:border-blue-500 focus:outline-none"
        />
      </div>

      {/* Transaction Table */}
      <TransactionTable transactions={filteredTransactions ?? []} />

      {/* No Results */}
      {filteredTransactions?.length === 0 && (
        <div className="py-8 text-center text-gray-500">
          No transactions found for "{searchTerm}"
        </div>
      )}
    </div>
  )
}
```

**Enhancement** (optional): Date range filter

```typescript
<div className="mb-4 flex gap-2">
  <input
    type="date"
    value={startDate}
    onChange={(e) => setStartDate(e.target.value)}
    className="rounded-md border px-3 py-2"
  />
  <span className="self-center text-gray-500">to</span>
  <input
    type="date"
    value={endDate}
    onChange={(e) => setEndDate(e.target.value)}
    className="rounded-md border px-3 py-2"
  />
</div>
```

---

## 5. Error State Improvements

### Problem
Generic "Something went wrong" messages don't help users recover.

### Solution
Specific error messages with actionable recovery steps.

**Component**: `frontend/src/components/ui/ErrorState.tsx`

```typescript
import { AlertCircle, RefreshCw } from 'lucide-react'

interface ErrorStateProps {
  title?: string
  message: string
  onRetry?: () => void
  actionLabel?: string
  onAction?: () => void
}

export function ErrorState({
  title = 'Something went wrong',
  message,
  onRetry,
  actionLabel,
  onAction,
}: ErrorStateProps) {
  return (
    <div className="flex flex-col items-center justify-center rounded-lg border border-red-200 bg-red-50 p-8">
      <AlertCircle className="mb-4 h-12 w-12 text-red-600" />

      <h3 className="mb-2 text-lg font-semibold text-red-900">{title}</h3>
      <p className="mb-6 text-center text-sm text-red-700">{message}</p>

      <div className="flex gap-3">
        {onRetry && (
          <button
            onClick={onRetry}
            className="flex items-center gap-2 rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700"
          >
            <RefreshCw className="h-4 w-4" />
            Try Again
          </button>
        )}

        {onAction && actionLabel && (
          <button
            onClick={onAction}
            className="rounded-md border border-red-600 px-4 py-2 text-sm font-medium text-red-600 hover:bg-red-50"
          >
            {actionLabel}
          </button>
        )}
      </div>
    </div>
  )
}
```

**Usage Examples**:

```typescript
// Portfolio fetch failed
if (error) {
  return (
    <ErrorState
      title="Failed to Load Portfolios"
      message="We couldn't fetch your portfolios. This might be a temporary network issue."
      onRetry={() => refetch()}
    />
  )
}

// Market data unavailable
if (marketDataError) {
  return (
    <ErrorState
      title="Market Data Unavailable"
      message="We're having trouble fetching real-time prices. Rate limit may have been exceeded."
      actionLabel="Use Last Known Prices"
      onAction={() => useCachedPrices()}
      onRetry={() => retryPrices()}
    />
  )
}

// Trade execution failed
if (tradeError) {
  return (
    <ErrorState
      title="Trade Failed"
      message={`Could not execute ${orderType} order for ${ticker}. ${error.message}`}
      onRetry={() => retryTrade()}
      actionLabel="Cancel"
      onAction={() => closeTrade()}
    />
  )
}
```

---

## Implementation Order

**Phase 1** (1-2 hours):
1. Create ConfirmDialog component
2. Add portfolio deletion with confirmation
3. Create ErrorState component
4. Update existing error displays to use ErrorState

**Phase 2** (1-2 hours):
5. Create skeleton components for major views
6. Replace loading states with skeletons
7. Test loading UX flow

**Phase 3** (1 hour):
8. Add search to transaction history
9. Test filtering works correctly

---

## Testing Requirements

### Unit Tests

```typescript
// ConfirmDialog.test.tsx
it('should call onConfirm when confirm button clicked', () => {
  const onConfirm = vi.fn()
  const { getByText } = render(<ConfirmDialog {...props} onConfirm={onConfirm} />)

  fireEvent.click(getByText('Delete'))
  expect(onConfirm).toHaveBeenCalled()
})

// TransactionHistory.test.tsx
it('should filter transactions by ticker', () => {
  const { getByPlaceholderText, getByText, queryByText } = render(
    <TransactionHistory portfolioId={1} />
  )

  fireEvent.change(getByPlaceholderText(/search/i), { target: { value: 'AAPL' } })

  expect(getByText(/AAPL/)).toBeInTheDocument()
  expect(queryByText(/MSFT/)).not.toBeInTheDocument()
})
```

### E2E Tests

```typescript
// portfolio.spec.ts
test('should delete portfolio with confirmation', async ({ page }) => {
  await page.goto('/')

  // Click delete button
  await page.click('[aria-label="Delete portfolio"]')

  // Confirm deletion
  await expect(page.locator('text=Are you sure')).toBeVisible()
  await page.click('text=Delete')

  // Verify portfolio removed
  await expect(page.locator('text=My Portfolio')).not.toBeVisible()
})

// transaction.spec.ts
test('should search transactions by ticker', async ({ page }) => {
  await page.goto('/portfolios/1')

  // Type search term
  await page.fill('[placeholder*="Search"]', 'AAPL')

  // Verify filtering
  await expect(page.locator('text=AAPL')).toBeVisible()
  await expect(page.locator('text=MSFT')).not.toBeVisible()
})
```

---

## Files to Create

**New Components**:
- `frontend/src/components/ui/ConfirmDialog.tsx`
- `frontend/src/components/ui/ErrorState.tsx`
- `frontend/src/components/features/portfolio/PortfolioListSkeleton.tsx`
- `frontend/src/components/features/portfolio/PortfolioDetailSkeleton.tsx`
- `frontend/src/components/features/portfolio/HoldingsTableSkeleton.tsx`
- `frontend/src/components/features/transaction/TransactionHistorySkeleton.tsx`
- `frontend/src/components/features/PriceChart/PriceChartSkeleton.tsx`
- `frontend/src/hooks/useDeletePortfolioMutation.ts`

**Modified Components**:
- `frontend/src/components/features/portfolio/PortfolioCard.tsx` - Add delete button
- `frontend/src/components/features/portfolio/PortfolioList.tsx` - Use skeleton
- `frontend/src/components/features/portfolio/PortfolioDetailPage.tsx` - Use skeleton
- `frontend/src/components/features/transaction/TransactionHistory.tsx` - Add search
- `frontend/src/services/api/portfolios.ts` - Add deletePortfolio function

---

## Success Criteria

- [ ] Users can delete portfolios with confirmation dialog
- [ ] All major views show skeleton loading states
- [ ] Error messages are specific and actionable
- [ ] Transaction history search filters correctly
- [ ] All new components have unit tests
- [ ] E2E tests verify deletion and search flows
- [ ] No console errors or warnings
- [ ] Responsive design works on mobile (basic check)

---

## References

- **Tailwind UI Components**: [Dialogs](https://tailwindui.com/components/application-ui/overlays/dialogs)
- **Skeleton Screens**: [Best Practices](https://www.smashingmagazine.com/2020/04/skeleton-screens-react/)
- **Related Tasks**: Task 085 (TradeForm fix), Task 086 (Daily Change)
- **BACKLOG.md**: UX Improvements section

---

## Notes

- These are **high-impact, low-effort** improvements
- Focus on preventing user frustration for first deployment
- Defer advanced features (export, bulk operations) to Phase 4
- Keep implementations simple and testable
- Prioritize clarity over cleverness
