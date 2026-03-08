# Task 013: Add Portfolio Creation UI

**Created**: 2025-12-28 18:13 PST
**Priority**: P1 - BLOCKING
**Estimated Effort**: 1-2 hours
**Agent**: Frontend-SWE

## Problem Statement

Users cannot create a portfolio in the UI. The app currently assumes a portfolio with ID `00000000-0000-0000-0000-000000000001` exists, but there's no way to create one through the interface.

**Current State**:
- Backend has `POST /api/v1/portfolios` endpoint working
- Frontend has `portfoliosApi.create()` function
- Frontend has `useCreatePortfolio()` mutation hook
- **Missing**: UI component to actually call this functionality

**Impact**: Users cannot use the app without manually creating a portfolio via API

## Requirements

### Functional Requirements

1. **Portfolio Creation Form**:
   - Input: Portfolio name (required, 1-100 characters)
   - Input: Initial deposit amount (optional, default $0.00)
   - Submit button
   - Cancel button (if modal)
   - Form validation with helpful error messages

2. **User Experience**:
   - Show form when no portfolios exist (empty state)
   - OR: Add "Create Portfolio" button in header/navigation
   - Display loading state during creation
   - Show success message and redirect to new portfolio
   - Handle errors gracefully (API failures, validation errors)

3. **Integration**:
   - Use existing `useCreatePortfolio()` mutation hook
   - Invalidate/refetch portfolio list after creation
   - Update route to show new portfolio immediately

### Non-Functional Requirements

- **Accessibility**: Form labels, keyboard navigation, ARIA attributes
- **Validation**: Client-side validation before API call
- **Error Handling**: Network errors, validation errors, server errors
- **Responsive**: Works on mobile and desktop

## Proposed Implementation

### Option A: Modal Dialog (Recommended)

**Pros**:
- Doesn't disrupt current page flow
- Common pattern for creation actions
- Can trigger from anywhere (header button)

**Cons**:
- Requires modal/dialog component

### Option B: Dedicated Page/Route

**Pros**:
- More space for form fields
- Clear user journey

**Cons**:
- Requires routing changes
- More navigation steps

**Recommendation**: Start with Option A (modal) for simplicity

## Technical Approach

### 1. Create Portfolio Creation Form Component

**File**: `frontend/src/components/features/portfolio/CreatePortfolioForm.tsx`

```typescript
interface CreatePortfolioFormProps {
  onSuccess?: (portfolioId: string) => void
  onCancel?: () => void
}

export function CreatePortfolioForm({ onSuccess, onCancel }: CreatePortfolioFormProps) {
  const [name, setName] = useState('')
  const [initialDeposit, setInitialDeposit] = useState('0.00')
  const createPortfolio = useCreatePortfolio()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    try {
      const result = await createPortfolio.mutateAsync({
        name,
        initial_deposit: parseFloat(initialDeposit) || 0,
        currency: 'USD'
      })

      onSuccess?.(result.portfolio_id)
    } catch (error) {
      // Error handling already in mutation hook
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label htmlFor="portfolio-name" className="block text-sm font-medium">
          Portfolio Name
        </label>
        <input
          id="portfolio-name"
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
          minLength={1}
          maxLength={100}
          className="mt-1 block w-full rounded-md border-gray-300"
        />
      </div>

      <div>
        <label htmlFor="initial-deposit" className="block text-sm font-medium">
          Initial Deposit (USD)
        </label>
        <input
          id="initial-deposit"
          type="number"
          step="0.01"
          min="0"
          value={initialDeposit}
          onChange={(e) => setInitialDeposit(e.target.value)}
          className="mt-1 block w-full rounded-md border-gray-300"
        />
      </div>

      <div className="flex gap-2 justify-end">
        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            className="px-4 py-2 border rounded-md"
          >
            Cancel
          </button>
        )}
        <button
          type="submit"
          disabled={createPortfolio.isPending || !name.trim()}
          className="px-4 py-2 bg-blue-600 text-white rounded-md disabled:opacity-50"
        >
          {createPortfolio.isPending ? 'Creating...' : 'Create Portfolio'}
        </button>
      </div>
    </form>
  )
}
```

### 2. Add Modal Dialog Component (if needed)

**File**: `frontend/src/components/ui/Dialog.tsx`

Simple modal wrapper using Headless UI or native dialog element.

### 3. Update Dashboard to Show Creation Option

**File**: `frontend/src/pages/Dashboard.tsx`

```typescript
export function Dashboard() {
  const [showCreateModal, setShowCreateModal] = useState(false)
  const { data: portfolios, isLoading } = usePortfolios()

  // Show creation form if no portfolios exist
  const hasNoPortfolios = portfolios && portfolios.length === 0

  return (
    <div>
      {/* Header with create button */}
      <div className="flex justify-between items-center mb-4">
        <h1>Portfolio Dashboard</h1>
        <button onClick={() => setShowCreateModal(true)}>
          Create Portfolio
        </button>
      </div>

      {/* Empty state if no portfolios */}
      {hasNoPortfolios && (
        <EmptyState
          title="No Portfolios Yet"
          description="Create your first portfolio to start tracking investments"
          action={
            <button onClick={() => setShowCreateModal(true)}>
              Create Portfolio
            </button>
          }
        />
      )}

      {/* Existing portfolio display */}
      {/* ... */}

      {/* Creation modal */}
      {showCreateModal && (
        <Dialog onClose={() => setShowCreateModal(false)}>
          <CreatePortfolioForm
            onSuccess={(id) => {
              setShowCreateModal(false)
              // Navigate to new portfolio or refresh
            }}
            onCancel={() => setShowCreateModal(false)}
          />
        </Dialog>
      )}
    </div>
  )
}
```

### 4. Add Empty State Component

**File**: `frontend/src/components/ui/EmptyState.tsx`

Reusable empty state component for when no data exists.

## Files to Create/Modify

### New Files
- `frontend/src/components/features/portfolio/CreatePortfolioForm.tsx`
- `frontend/src/components/features/portfolio/CreatePortfolioForm.test.tsx`
- `frontend/src/components/ui/Dialog.tsx` (if not exists)
- `frontend/src/components/ui/Dialog.test.tsx`
- `frontend/src/components/ui/EmptyState.tsx` (if not exists)
- `frontend/src/components/ui/EmptyState.test.tsx`

### Modified Files
- `frontend/src/pages/Dashboard.tsx` - Add create button and modal
- `frontend/src/App.tsx` - May need to adjust default portfolio ID logic

## Testing Requirements

### Unit Tests
1. **CreatePortfolioForm.test.tsx**:
   - Renders form with empty fields
   - Validates required name field
   - Handles form submission
   - Shows loading state during creation
   - Calls onSuccess callback with portfolio ID
   - Handles errors gracefully

2. **Dialog.test.tsx**:
   - Opens and closes modal
   - Handles escape key
   - Handles backdrop click

### Integration Tests
3. **Dashboard integration**:
   - Shows empty state when no portfolios
   - Opens creation modal on button click
   - Creates portfolio and updates list
   - Handles API errors

### Manual Testing
- [ ] Create portfolio with name only
- [ ] Create portfolio with name + initial deposit
- [ ] Validate required fields
- [ ] Cancel creation (modal closes)
- [ ] Create multiple portfolios
- [ ] Error handling (network failure)
- [ ] Keyboard navigation
- [ ] Mobile responsive

## Success Criteria

- [ ] User can create a portfolio from the UI
- [ ] Form has proper validation
- [ ] Loading states shown during creation
- [ ] Errors displayed clearly to user
- [ ] New portfolio appears in list immediately
- [ ] All tests passing (maintain 23/23)
- [ ] Accessible (keyboard nav, ARIA labels)
- [ ] Responsive on mobile and desktop

## Notes

- **Existing hooks**: Already have `useCreatePortfolio()` mutation
- **API contract**: Matches backend `CreatePortfolioRequest` DTO
- **Design**: Use existing Tailwind classes for consistency
- **MSW**: Add handler for create endpoint in tests (may already exist)

## Related Files

- API Hook: `frontend/src/hooks/usePortfolio.ts`
- API Client: `frontend/src/services/api/portfolios.ts`
- Types: `frontend/src/services/api/types.ts`
- Backend: `backend/src/zebu/adapters/inbound/api.py` (POST /portfolios)

## Future Enhancements (Backlog)

- Edit portfolio name
- Delete portfolio
- Portfolio settings (currency, etc.)
- Portfolio archiving/activation
