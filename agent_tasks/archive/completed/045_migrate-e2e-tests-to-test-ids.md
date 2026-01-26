# Task 045: Migrate E2E Tests to Test IDs

**Status**: Open
**Priority**: Medium
**Agent**: frontend-swe
**Estimated Effort**: 8-12 hours
**Created**: 2026-01-03

## Context

Current E2E tests use brittle text-based selectors (`.getByText()`, `.getByRole()` with name matching) that break when UI copy changes and make it difficult to target specific elements reliably. This became evident during task 043 when tests failed due to selector issues.

**Current Problems**:
- Tests rely on exact text matching which breaks with minor copy changes
- Difficult to distinguish between similar elements (multiple buttons with same text)
- Selector intent unclear (is this testing accessibility or just finding elements?)
- Hard to debug test failures (which "Submit" button did it try to click?)

**Solution**: Add `data-testid` attributes throughout frontend and migrate all E2E tests to use `.getByTestId()`.

## Problem

From recent E2E test debugging (task 043):
- Tests timed out looking for `#ticker` and `#quantity` inputs
- Had to replace with role-based selectors: `getByRole('textbox', { name: /symbol/i })`
- This works but is still fragile to label text changes
- Test intent is unclear - testing accessibility or just finding elements?

**Industry Best Practices**:
- Playwright docs recommend test IDs for stable, explicit element targeting
- Testing Library advocates data-testid for implementation-independent tests
- Test IDs make test intent clear and failures easy to debug

## Objective

Systematically migrate all E2E tests to use `data-testid` attributes and establish conventions for future test development.

**Goals**:
1. Add test IDs to all interactive elements used in tests
2. Update all existing E2E tests to use test IDs
3. Document test ID naming conventions
4. Ensure tests are more reliable and maintainable

## Requirements

### Phase 1: Establish Test ID Conventions (30 minutes)

Create `docs/TESTING_CONVENTIONS.md` with test ID naming standards:

**Naming Pattern**: `{component}-{element}-{variant?}`

Examples:
- `portfolio-card-{id}` - Portfolio card in list
- `portfolio-card-name-{id}` - Portfolio name within card
- `trade-form-ticker-input` - Ticker input in trade form
- `trade-form-quantity-input` - Quantity input
- `trade-form-buy-button` - Buy button
- `trade-form-sell-button` - Sell button
- `portfolio-list-create-button` - Create portfolio button
- `portfolio-detail-trade-link` - Trade stocks link on detail page
- `nav-dashboard-link` - Dashboard navigation link

**Guidelines**:
- Use kebab-case
- Start with component/page name
- Be specific but not overly verbose
- Use semantic names (what it is, not what it does)
- For dynamic lists, include ID: `portfolio-card-${portfolio.id}`

### Phase 2: Add Test IDs to Frontend Components (4-6 hours)

Add `data-testid` attributes to all components used in E2E tests:

#### Portfolio Components
**File**: `frontend/src/components/PortfolioCard.tsx`
```tsx
// Add test IDs to card and interactive elements
<div data-testid={`portfolio-card-${portfolio.id}`}>
  <h3 data-testid={`portfolio-card-name-${portfolio.id}`}>
    {portfolio.name}
  </h3>
  <Link
    to={`/portfolio/${portfolio.id}`}
    data-testid={`portfolio-card-link-${portfolio.id}`}
  >
    View Details
  </Link>
</div>
```

**File**: `frontend/src/components/CreatePortfolioForm.tsx`
```tsx
<input
  data-testid="create-portfolio-name-input"
  name="name"
  // ...
/>
<input
  data-testid="create-portfolio-deposit-input"
  name="initial_deposit"
  // ...
/>
<button
  data-testid="create-portfolio-submit-button"
  type="submit"
>
  Create Portfolio
</button>
```

#### Trading Components
**File**: `frontend/src/components/TradeForm.tsx`
```tsx
<input
  data-testid="trade-form-ticker-input"
  id="ticker"
  name="symbol"
  // ...
/>
<input
  data-testid="trade-form-quantity-input"
  id="quantity"
  name="quantity"
  // ...
/>
<button
  data-testid="trade-form-buy-button"
  type="submit"
  disabled={tradeType !== 'BUY'}
>
  Execute Buy Order
</button>
<button
  data-testid="trade-form-sell-button"
  type="submit"
  disabled={tradeType !== 'SELL'}
>
  Execute Sell Order
</button>
```

#### Portfolio Detail Components
**File**: `frontend/src/pages/PortfolioDetail.tsx`
```tsx
<h1 data-testid="portfolio-detail-name">{portfolio?.name}</h1>
<div data-testid="portfolio-detail-cash">Cash: ${portfolio?.cash_balance}</div>
<Link
  to={`/portfolio/${id}/trade`}
  data-testid="portfolio-detail-trade-link"
>
  Trade Stocks
</Link>
```

#### Holdings & Transactions
**File**: `frontend/src/components/HoldingsTable.tsx`
```tsx
<table data-testid="holdings-table">
  <tbody>
    {holdings.map(holding => (
      <tr
        key={holding.symbol}
        data-testid={`holding-row-${holding.symbol}`}
      >
        <td data-testid={`holding-symbol-${holding.symbol}`}>
          {holding.symbol}
        </td>
        <td data-testid={`holding-quantity-${holding.symbol}`}>
          {holding.quantity}
        </td>
        // ...
      </tr>
    ))}
  </tbody>
</table>
```

**File**: `frontend/src/components/TransactionHistory.tsx`
```tsx
<table data-testid="transaction-history-table">
  <tbody>
    {transactions.map((tx, idx) => (
      <tr
        key={tx.id}
        data-testid={`transaction-row-${idx}`}
      >
        <td data-testid={`transaction-type-${idx}`}>{tx.type}</td>
        <td data-testid={`transaction-symbol-${idx}`}>{tx.symbol}</td>
        // ...
      </tr>
    ))}
  </tbody>
</table>
```

#### Navigation Components
**File**: `frontend/src/components/Navigation.tsx` (if exists)
```tsx
<nav data-testid="main-nav">
  <Link to="/" data-testid="nav-dashboard-link">Dashboard</Link>
  <Link to="/portfolios" data-testid="nav-portfolios-link">Portfolios</Link>
</nav>
```

### Phase 3: Update E2E Tests (3-4 hours)

Migrate all E2E test files to use test IDs:

#### File: `frontend/tests/e2e/portfolio-creation.spec.ts`

**Before**:
```typescript
await page.getByRole('link', { name: /create portfolio/i }).click()
await page.getByLabel(/portfolio name/i).fill('Test Portfolio')
await page.getByLabel(/initial deposit/i).fill('10000')
await page.getByRole('button', { name: /create/i }).click()
await expect(page.getByRole('heading', { name: 'Test Portfolio' })).toBeVisible()
```

**After**:
```typescript
await page.getByTestId('portfolio-list-create-button').click()
await page.getByTestId('create-portfolio-name-input').fill('Test Portfolio')
await page.getByTestId('create-portfolio-deposit-input').fill('10000')
await page.getByTestId('create-portfolio-submit-button').click()
await expect(page.getByTestId('portfolio-detail-name')).toHaveText('Test Portfolio')
```

#### File: `frontend/tests/e2e/trading.spec.ts`

**Before**:
```typescript
await page.getByRole('link', { name: /trade stocks/i }).click()
await page.getByRole('textbox', { name: /symbol/i }).fill('IBM')
await page.getByRole('spinbutton', { name: /quantity/i }).fill('2')
await page.getByRole('button', { name: /execute buy order/i }).click()
```

**After**:
```typescript
await page.getByTestId('portfolio-detail-trade-link').click()
await page.getByTestId('trade-form-ticker-input').fill('IBM')
await page.getByTestId('trade-form-quantity-input').fill('2')
await page.getByTestId('trade-form-buy-button').click()
```

#### All Test Files to Update:
- `frontend/tests/e2e/portfolio-creation.spec.ts` (4 tests)
- `frontend/tests/e2e/trading.spec.ts` (3 tests)
- Any other `frontend/tests/e2e/*.spec.ts` files

### Phase 4: Validation & Documentation (1 hour)

1. **Run E2E Tests**:
   ```bash
   task test:e2e
   ```
   All 7+ tests should pass with new test IDs

2. **Update Documentation**:
   - Add test ID section to `docs/TESTING_CONVENTIONS.md`
   - Update `frontend/README.md` with test ID usage
   - Document in `agent_tasks/progress/`

3. **Verify Test Stability**:
   - Run tests 3x to ensure no flakiness
   - Test in CI environment
   - Verify test failure messages are clear

## Technical Requirements

1. **TypeScript Compliance**:
   - No type errors introduced
   - Proper typing for component props if needed

2. **No Functional Changes**:
   - Only add test IDs and update tests
   - No behavior changes to components
   - No UI/UX changes

3. **Backward Compatibility**:
   - Keep existing `id` attributes (e.g., `id="ticker"`)
   - Keep existing ARIA labels
   - Only add test IDs, don't remove other attributes

4. **Consistent Naming**:
   - Follow naming conventions in all files
   - Use same pattern for similar elements
   - Document any deviations from standard pattern

## Success Criteria

- [ ] `docs/TESTING_CONVENTIONS.md` created with test ID guidelines
- [ ] Test IDs added to all components used in E2E tests:
  - [ ] PortfolioCard
  - [ ] CreatePortfolioForm
  - [ ] TradeForm
  - [ ] PortfolioDetail page
  - [ ] HoldingsTable
  - [ ] TransactionHistory
  - [ ] Navigation components
- [ ] All E2E tests updated to use test IDs:
  - [ ] portfolio-creation.spec.ts (4 tests)
  - [ ] trading.spec.ts (3 tests)
- [ ] All E2E tests pass locally: `task test:e2e`
- [ ] All E2E tests pass in CI
- [ ] Tests run 3x without flakiness
- [ ] No TypeScript errors: `npm run type-check`
- [ ] No functional changes to application
- [ ] Documentation updated
- [ ] Progress documented in `agent_tasks/progress/`

## Out of Scope

- Adding test IDs to components NOT used in E2E tests
- Creating new E2E tests (separate task)
- Accessibility improvements (separate concern)
- Component refactoring
- Styling changes

## References

**Playwright Best Practices**:
- https://playwright.dev/docs/locators#locate-by-test-id
- https://playwright.dev/docs/best-practices#use-locators

**Testing Library Philosophy**:
- https://testing-library.com/docs/queries/bytestid/

**Current E2E Tests**:
- `frontend/tests/e2e/portfolio-creation.spec.ts` - 4 tests
- `frontend/tests/e2e/trading.spec.ts` - 3 tests

**Recent Context**:
- Task 043: E2E trading tests fixed with role-based selectors
- Issue: Fragile selectors that break with text changes
- Note: Alpha Vantage demo key available for testing

## Agent Notes

**Approach**:
1. Start with documentation (test ID conventions)
2. Add test IDs component by component
3. Update tests file by file
4. Validate after each major change
5. Final validation with full test suite

**Testing Strategy**:
- Test after each component updated
- Run full suite after all components done
- Run 3x to catch flakiness
- Verify in CI environment

**Common Pitfalls to Avoid**:
- Don't remove existing accessibility attributes
- Don't change component logic
- Don't introduce TypeScript errors
- Don't break existing functionality
- Don't make test IDs too specific (avoid implementation details)

**Expected Challenges**:
- Finding all test-related components
- Ensuring consistent naming across large codebase
- Avoiding regressions in test coverage
- Keeping test IDs synchronized with component updates

**Communication**:
- Document any naming convention deviations
- Note any components that were difficult to add IDs to
- Flag any tests that couldn't be migrated (if any)
