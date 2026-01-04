# Agent Progress: Task 045 - Migrate E2E Tests to Test IDs

**Date**: 2026-01-04  
**Agent**: frontend-swe  
**Task**: Task 045 - Migrate E2E Tests to Test IDs  
**PR**: copilot/migrate-e2e-tests-to-test-ids  

## Task Summary

Successfully migrated all E2E tests from brittle text-based and role-based selectors to stable `data-testid` attributes. All 7 E2E tests now pass consistently using test IDs, making them more reliable and maintainable.

## Problem Statement

E2E tests were using fragile selectors (`.getByText()`, `.getByRole()` with name matching) that:
- Broke when UI copy changed
- Made it difficult to target specific elements reliably
- Had unclear intent (testing accessibility vs. just finding elements)
- Were hard to debug when failures occurred

**Solution**: Add `data-testid` attributes throughout frontend and migrate all E2E tests to use `.getByTestId()`.

## Changes Made

### Phase 1: Established Test ID Conventions

**File**: `docs/TESTING_CONVENTIONS.md` (new)

Created comprehensive documentation for test ID naming conventions:

**Naming Pattern**: `{component}-{element}-{variant?}`

**Key Guidelines**:
- Use kebab-case (lowercase with hyphens)
- Start with component or page name
- Be specific but not overly verbose
- Use semantic names (what it is, not what it does)
- For dynamic lists, include ID: `portfolio-card-${portfolio.id}`

**Examples**:
- `create-portfolio-name-input` - Portfolio name input
- `trade-form-ticker-input` - Stock symbol input
- `holding-symbol-IBM` - IBM symbol in holdings table
- `transaction-row-0` - First transaction row

### Phase 2: Added Test IDs to Components

Added `data-testid` attributes to all interactive elements used in E2E tests:

#### 1. **CreatePortfolioForm.tsx**
```tsx
// Name input
<input
  id="portfolio-name"
  data-testid="create-portfolio-name-input"
  // ...
/>

// Deposit input
<input
  id="initial-deposit"
  data-testid="create-portfolio-deposit-input"
  // ...
/>

// Cancel button
<button
  data-testid="create-portfolio-cancel-button"
  // ...
/>
```

#### 2. **TradeForm.tsx**
```tsx
// Action toggle buttons
<button data-testid="trade-form-action-buy">Buy</button>
<button data-testid="trade-form-action-sell">Sell</button>

// Form inputs
<input data-testid="trade-form-ticker-input" />
<input data-testid="trade-form-quantity-input" />
<input data-testid="trade-form-price-input" />

// Submit button (dynamic based on action)
<button data-testid={action === 'BUY' ? 'trade-form-buy-button' : 'trade-form-sell-button'}>
```

#### 3. **PortfolioDetail.tsx**
```tsx
// Back link
<Link data-testid="portfolio-detail-back-link">
  ← Back to Dashboard
</Link>

// Portfolio name heading
<h1 data-testid="portfolio-detail-name">
  {portfolio?.name}
</h1>
```

#### 4. **HoldingsTable.tsx**
```tsx
// Table container
<table data-testid="holdings-table">

// Dynamic rows and cells
<tr data-testid={`holding-row-${holding.ticker}`}>
  <td data-testid={`holding-symbol-${holding.ticker}`}>
  <td data-testid={`holding-quantity-${holding.ticker}`}>
  <td data-testid={`holding-value-${holding.ticker}`}>
</tr>
```

#### 5. **TransactionList.tsx**
```tsx
// List container
<div data-testid="transaction-history-table">

// Dynamic transaction rows
<div data-testid={`transaction-row-${idx}`}>
  <p data-testid={`transaction-type-${idx}`}>
  <span data-testid={`transaction-symbol-${idx}`}>
  <p data-testid={`transaction-amount-${idx}`}>
</div>
```

#### 6. **Dashboard.tsx**
```tsx
// Trade Stocks quick action link
<Link
  to={`/portfolio/${primaryPortfolio.id}`}
  data-testid="dashboard-trade-stocks-link"
>
  Trade Stocks
</Link>
```

### Phase 3: Updated E2E Tests

#### **portfolio-creation.spec.ts** (4 tests)

**Before** (fragile selectors):
```typescript
await page.getByLabel(/portfolio name/i).fill('My Test Portfolio')
await page.getByLabel(/initial deposit/i).fill('10000')
await expect(page.getByRole('heading', { name: 'My Test Portfolio' })).toBeVisible()
```

**After** (stable test IDs):
```typescript
await page.getByTestId('create-portfolio-name-input').fill('My Test Portfolio')
await page.getByTestId('create-portfolio-deposit-input').fill('10000')
await expect(page.getByRole('heading', { name: 'My Test Portfolio' })).toBeVisible()
```

**Key Change**: Tests now correctly expect portfolio to remain on dashboard after creation (not navigate to detail page).

#### **trading.spec.ts** (3 tests)

**Before** (role-based selectors):
```typescript
await page.getByRole('textbox', { name: /symbol/i }).fill('IBM')
await page.getByRole('spinbutton', { name: /quantity/i }).fill('2')
const buyButton = page.getByRole('button', { name: /execute buy order/i })
await expect(page.getByRole('cell', { name: 'IBM' })).toBeVisible()
```

**After** (test IDs):
```typescript
await page.getByTestId('trade-form-ticker-input').fill('IBM')
await page.getByTestId('trade-form-quantity-input').fill('2')
const buyButton = page.getByTestId('trade-form-buy-button')
await expect(page.getByTestId('holding-symbol-IBM')).toBeVisible()
```

**Key Changes**:
1. Added explicit navigation to portfolio detail page after creation
2. Used `dashboard-trade-stocks-link` test ID for navigation
3. Verified `portfolio-detail-name` test ID after navigation
4. Used specific test IDs for holdings verification

### Phase 4: Validation

✅ **Type Checking**: No TypeScript errors  
✅ **E2E Tests**: All 7 tests passing  
✅ **Stability**: Tests passed 3 consecutive runs without flakiness  
✅ **Performance**: Test suite completes in ~21 seconds  

**Test Run Results**:
```
Run 1: 7 passed (21.6s)
Run 2: 7 passed (21.3s)
Run 3: 7 passed (21.4s)
```

## Design Decisions

### 1. Test ID Naming Convention

**Decision**: Use `{component}-{element}-{variant?}` pattern with kebab-case

**Rationale**:
- Consistent with HTML/CSS conventions (kebab-case)
- Component prefix prevents naming collisions
- Clear hierarchy (component → element → variant)
- Easy to search and maintain

**Example**: `trade-form-ticker-input` clearly indicates:
- Component: `trade-form`
- Element: `ticker-input`

### 2. Dynamic Test IDs for Lists

**Decision**: Include unique identifier in test ID for list items

**Pattern**: `{component}-{element}-{id}`

**Examples**:
- `holding-row-IBM` (using ticker as ID)
- `transaction-row-0` (using index as ID)

**Rationale**:
- Allows targeting specific items in lists
- Makes test failures easier to debug
- Prevents ambiguity when multiple similar elements exist

### 3. Backward Compatibility

**Decision**: Keep existing `id` and `aria-label` attributes

**Rationale**:
- Test IDs complement, don't replace, accessibility attributes
- Maintains HTML5 form field associations
- Ensures screen reader compatibility
- Follows separation of concerns (testing vs. accessibility)

**Example**:
```tsx
<input
  id="ticker"                           // Keep for <label> association
  data-testid="trade-form-ticker-input" // Add for testing
  aria-label="Symbol"                   // Keep for accessibility
/>
```

### 4. Portfolio Navigation Flow

**Decision**: Tests explicitly navigate to portfolio detail page after creation

**Rationale**:
- Dashboard's CreatePortfolioForm uses `onSuccess` callback that closes modal
- App stays on dashboard after portfolio creation (doesn't auto-navigate)
- Matches actual user workflow: create → see dashboard → click "Trade Stocks"

**Implementation**:
```typescript
// Create portfolio
await page.getByTestId('submit-portfolio-form-btn').click()

// Wait for dashboard
await expect(page.getByRole('heading', { name: 'Trading Portfolio' })).toBeVisible()

// Navigate to detail page
await page.getByTestId('dashboard-trade-stocks-link').click()

// Now on detail page
await expect(page.getByTestId('portfolio-detail-name')).toHaveText('Trading Portfolio')
```

## Benefits Achieved

### 1. **Reliability**
- Tests no longer break when button text changes from "Buy" to "Purchase"
- Label changes don't require test updates
- Reduced false positives from selector ambiguity

### 2. **Clarity**
- Test intent is explicit: `getByTestId('trade-form-buy-button')`
- No confusion between accessibility testing and element targeting
- Easy to understand what element is being tested

### 3. **Debuggability**
- Failures clearly indicate which test ID couldn't be found
- Can quickly locate the element in component code
- No ambiguity about which "Submit" button failed

### 4. **Maintainability**
- Consistent naming convention across all components
- Easy to add new test IDs following established patterns
- Documentation provides clear guidelines for future development

## Testing Strategy

### Test ID Placement

**Added test IDs to**:
- ✅ Form inputs (name, deposit, ticker, quantity)
- ✅ Action buttons (submit, buy, sell, cancel)
- ✅ Navigation links (back, trade stocks)
- ✅ Data display elements (portfolio name, holdings, transactions)
- ✅ List items (holding rows, transaction rows)

**Did NOT add test IDs to**:
- ❌ Elements not used in E2E tests
- ❌ Static text/headings (use role-based selectors)
- ❌ Elements already uniquely identifiable by role

### Selector Strategy

**Use test IDs for**:
- Interactive elements (buttons, inputs, links)
- Specific data verification (portfolio name, holdings)
- Dynamic content (list items)

**Keep role-based selectors for**:
- Headings (verify page structure)
- Generic content verification
- Accessibility validation

**Example Mix**:
```typescript
// Navigation - test ID
await page.getByTestId('dashboard-trade-stocks-link').click()

// Page structure - role
await expect(page.getByRole('heading', { name: 'Execute Trade' })).toBeVisible()

// Form input - test ID
await page.getByTestId('trade-form-ticker-input').fill('IBM')

// Submit - test ID
await page.getByTestId('trade-form-buy-button').click()

// Verification - test ID
await expect(page.getByTestId('holding-symbol-IBM')).toBeVisible()
```

## Files Changed

### Documentation
- ✅ `docs/TESTING_CONVENTIONS.md` (new) - Test ID conventions and guidelines

### Components
- ✅ `frontend/src/components/features/portfolio/CreatePortfolioForm.tsx`
- ✅ `frontend/src/components/features/portfolio/TradeForm.tsx`
- ✅ `frontend/src/components/features/portfolio/HoldingsTable.tsx`
- ✅ `frontend/src/components/features/portfolio/TransactionList.tsx`
- ✅ `frontend/src/pages/Dashboard.tsx`
- ✅ `frontend/src/pages/PortfolioDetail.tsx`

### Tests
- ✅ `frontend/tests/e2e/portfolio-creation.spec.ts` (4 tests migrated)
- ✅ `frontend/tests/e2e/trading.spec.ts` (3 tests migrated)

## Validation Results

### TypeScript Type Checking
```bash
cd frontend && npm run typecheck
# ✅ No errors
```

### E2E Test Results
```bash
cd frontend && npm run test:e2e

# Run 1
Running 7 tests using 1 worker
·······
  7 passed (21.6s)

# Run 2
Running 7 tests using 1 worker
·······
  7 passed (21.3s)

# Run 3
Running 7 tests using 1 worker
·······
  7 passed (21.4s)
```

### Test Coverage
- ✅ Portfolio creation flow (4 tests)
- ✅ Trading flow with market data (3 tests)
- ✅ Validation errors
- ✅ Holdings display
- ✅ Transaction history

## Known Issues

None. All tests pass consistently.

## Follow-up Tasks

### Immediate (Out of Scope for This Task)
None required. Task is complete.

### Future Enhancements
1. Add test IDs to remaining components as they're used in new E2E tests
2. Consider adding test IDs to unit test components if beneficial
3. Update CI/CD documentation to include test ID conventions

## Lessons Learned

### 1. Navigation Flow Understanding Critical

**Issue**: Initially updated tests to expect `portfolio-detail-name` immediately after portfolio creation

**Discovery**: Dashboard's CreatePortfolioForm uses `onSuccess` callback, not default navigation

**Resolution**: Added explicit navigation step using `dashboard-trade-stocks-link`

**Lesson**: Always verify actual app behavior before updating tests

### 2. Test ID Naming Consistency Matters

**Pattern**: Established early, followed consistently

**Benefit**: No confusion about where to find test IDs or what to name new ones

**Example**: All form inputs follow `{component}-{field}-input` pattern

### 3. Mix of Selectors Still Valid

**Realization**: Not everything needs a test ID

**Strategy**: 
- Test IDs for interactive elements and specific data
- Role-based selectors for page structure and accessibility
- Text-based selectors for generic content

**Benefit**: Tests remain readable while being stable

## Success Metrics

✅ **All 7 E2E tests migrated** to use test IDs  
✅ **0 TypeScript errors** introduced  
✅ **100% test pass rate** across 3 runs  
✅ **~21 second runtime** (no performance degradation)  
✅ **Clear documentation** for future test ID usage  
✅ **Consistent naming** across all components  

## Summary

Task 045 successfully migrated all E2E tests from fragile text/role-based selectors to stable `data-testid` attributes. The migration:

1. **Established clear conventions** in `docs/TESTING_CONVENTIONS.md`
2. **Added test IDs** to 6 components/pages
3. **Updated 7 E2E tests** to use new selectors
4. **Validated stability** with 3 consecutive passing runs
5. **Maintained performance** with 21-second test suite runtime

Tests are now more reliable, easier to debug, and better prepared for future UI changes. The documentation ensures consistency for future development.
