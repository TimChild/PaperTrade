# Task 098: Refactor E2E Test Suite to Proper Abstraction Levels

**Status**: Not Started
**Agent**: quality-infra
**Priority**: High (Blocking CI, impacts all future development)
**Estimated Effort**: Medium (2-3 hours)
**Dependencies**: None
**Created**: 2026-01-11

## Context

PR #114 added comprehensive testing but at the **wrong abstraction level**. We now have 60 E2E tests when we should have ~20. Many tests are checking CSS, accessibility, and component behavior via slow, brittle E2E tests instead of fast unit/component tests.

**Current Situation**:
- 60 E2E tests across 11 files (1,657 lines)
- E2E runtime: 10-15 minutes
- Many tests are wrong abstraction level (testing CSS via full browser)
- Missing dependency: `@axe-core/playwright` not installed

**Problem**:
- ❌ Slow CI (10-15 min per PR)
- ❌ Brittle tests (screenshots, timing, CSS)
- ❌ High maintenance burden
- ❌ Wrong test pyramid (too many E2E, not enough unit)

## Goals

**Refactor E2E suite to follow proper testing best practices**:
1. Reduce E2E tests from 60 → ~20 (critical user journeys only)
2. Move 40 tests to appropriate levels (component, unit, or delete)
3. Fix remaining E2E test failures
4. Establish E2E testing standards
5. Result: Faster CI, easier maintenance, better test pyramid

## Success Criteria

- [ ] E2E test count: 18-20 tests (down from 60)
- [ ] E2E runtime: 5-8 minutes (down from 10-15)
- [ ] All remaining E2E tests pass locally and in CI
- [ ] Component tests added for accessibility (using `jest-axe`)
- [ ] E2E testing standards documented
- [ ] Test pyramid properly balanced

## Implementation Plan

### Phase 1: Delete Wrong-Level Tests (60 min)

#### 1.1 Delete Accessibility E2E Tests (10 tests)

**File**: `frontend/tests/e2e/accessibility.spec.ts`

**Why Delete**:
- Accessibility should be tested at component level
- E2E tests are slow (full browser + auth + navigation)
- `jest-axe` works perfectly in jsdom/vitest

**Action**: ❌ DELETE entire file

**Replacement**: Add to `frontend/tests/setup.ts`:
```typescript
// Install jest-axe
// npm install -D jest-axe @axe-core/react

// Add to setup.ts
import { toHaveNoViolations } from 'jest-axe'
expect.extend(toHaveNoViolations)
```

Then add to component tests:
```typescript
import { axe, toHaveNoViolations } from 'jest-axe'

test('Dashboard has no accessibility violations', async () => {
  const { container } = render(<Dashboard />)
  const results = await axe(container)
  expect(results).toHaveNoViolations()
})
```

---

#### 1.2 Delete Interactive States Tests (7 tests)

**File**: `frontend/tests/e2e/interactive-states.spec.ts`

**Why Delete**:
- Testing CSS hover/focus states via E2E is overkill
- These are Tailwind utility concerns, not app logic
- Component tests with `@testing-library/user-event` sufficient

**Action**: ❌ DELETE entire file

**Replacement**: OPTIONAL - Add spot checks to component tests if desired:
```typescript
import userEvent from '@testing-library/user-event'

test('Button responds to hover', async () => {
  const user = userEvent.setup()
  const { getByRole } = render(<Button>Click</Button>)
  await user.hover(getByRole('button'))
  // Most CSS hover states are visual, trust Tailwind
})
```

**Decision**: Don't replace - trust CSS framework.

---

#### 1.3 Delete Responsive Design Tests (9 tests)

**File**: `frontend/tests/e2e/responsive.spec.ts`

**Why Delete**:
- Testing viewport-specific CSS via E2E is wrong level
- Tailwind handles responsive utilities
- Visual regression tools (Chromatic, Percy) better for this

**Action**: ❌ DELETE entire file

**Replacement**: OPTIONAL - Add to component tests:
```typescript
test('Component is responsive', () => {
  global.innerWidth = 375 // Mobile
  const { container } = render(<Dashboard />)
  // Check component adapts to viewport
})
```

**Decision**: Don't replace - trust Tailwind responsive utilities.

---

#### 1.4 Delete Visual Regression Tests (5 tests)

**File**: `frontend/tests/e2e/visual-regression.spec.ts`

**Why Delete**:
- Screenshot comparison is brittle without proper tooling
- Masks defeat the purpose (masking timestamps, etc.)
- Proper visual regression needs Chromatic/Percy/Storybook

**Action**: ❌ DELETE entire file

**Replacement**: FUTURE - Set up Storybook + Chromatic if visual regression needed.

**Decision**: Delete for now, revisit when we have proper tooling.

---

#### 1.5 Delete Most Not Found Tests (4 of 5 tests)

**File**: `frontend/tests/e2e/not-found.spec.ts`

**Why Reduce**:
- 404 page is a simple route/component
- Doesn't need 5 E2E tests
- Component test with React Router sufficient

**Action**: ⚠️ REDUCE to 1 smoke test, DELETE 4 tests

**Keep ONE test**:
```typescript
test('should display 404 page for invalid route', async ({ page }) => {
  await page.goto('/invalid-route')
  await expect(page.getByText('404')).toBeVisible()
})
```

**Delete**:
- "Go Back" button test → Component test
- "Return to Dashboard" button test → Component test
- "Helpful links" test → Component test
- "Accessibility" test → Already covered by component a11y tests

---

#### 1.6 Reduce Dark Mode Tests (6 → 2 tests)

**File**: `frontend/tests/e2e/dark-mode.spec.ts`

**Why Reduce**:
- Theme switching is component/context logic
- E2E tests are overkill for testing localStorage + CSS class

**Action**: ⚠️ REDUCE to 2 smoke tests

**Keep TWO tests**:
```typescript
test('Theme toggle changes theme correctly', async ({ page }) => {
  await page.getByTestId('theme-toggle-dark').click()
  await expect(page.locator('html')).toHaveClass(/dark/)
})

test('Theme persists across page reloads', async ({ page }) => {
  await page.getByTestId('theme-toggle-dark').click()
  await page.reload()
  await expect(page.locator('html')).toHaveClass(/dark/)
})
```

**Delete**:
- Individual toggle button tests → Component tests
- System theme test → Component test
- Theme sync test → Component test

**Replacement**: Add component tests for theme context.

---

### Phase 2: Keep Critical E2E Tests (30 min)

These tests SHOULD be E2E - they test critical user journeys and integrations.

#### 2.1 Keep Trading Tests ✅ (6 tests)

**File**: `frontend/tests/e2e/trading.spec.ts`

**Why Keep**:
- Critical user journey
- Tests backend integration
- Price fetching from Alpha Vantage
- Order execution

**Action**: ✅ KEEP all tests

---

#### 2.2 Keep Portfolio Creation Tests ✅ (4 tests)

**File**: `frontend/tests/e2e/portfolio-creation.spec.ts`

**Why Keep**:
- Core feature
- Tests form validation
- API integration
- Navigation flow

**Action**: ✅ KEEP all tests

---

#### 2.3 Keep Multi-Portfolio Tests ✅ (3 tests)

**File**: `frontend/tests/e2e/multi-portfolio.spec.ts`

**Why Keep**:
- User workflow
- Tests data isolation
- Navigation between portfolios

**Action**: ✅ KEEP all tests

---

#### 2.4 Keep Analytics Tests ✅ (4 tests)

**File**: `frontend/tests/e2e/analytics.spec.ts`

**Why Keep**:
- Integration test for charts
- Backend aggregation
- UI rendering with real data

**Action**: ✅ KEEP all tests

---

#### 2.5 Keep Auth Test ✅ (1 test)

**File**: `frontend/tests/e2e/clerk-auth-test.spec.ts`

**Why Keep**:
- Third-party integration (Clerk)
- Critical for production

**Action**: ✅ KEEP

---

### Phase 3: Fix Remaining Test Failures (45 min)

After deleting wrong-level tests, fix the ~20 remaining tests.

#### 3.1 Install Missing Dependencies (If Needed)

Check if any remaining tests need dependencies:
```bash
cd frontend
npm list  # Verify all deps installed
```

If missing deps for remaining tests, install them.

#### 3.2 Run E2E Tests Locally

```bash
task test:e2e
```

**Expected**: ~20 tests run, all pass

**If failures**: Debug one by one:
```bash
cd frontend
npx playwright test --headed  # Run with browser visible
npx playwright test --debug   # Run in debug mode
```

#### 3.3 Fix Playwright Configuration (If Needed)

Ensure `playwright.config.ts` is optimized:
- ✅ `fullyParallel: true`
- ✅ `workers: 3` (or 2 in CI)
- ✅ Timeout: 30s per test
- ✅ Chromium only (commented out firefox/webkit)

#### 3.4 Verify CI Passes

Push branch, check GitHub Actions pass.

---

### Phase 4: Add Component-Level Replacements (30 min)

#### 4.1 Add jest-axe for Accessibility

```bash
cd frontend
npm install -D jest-axe @axe-core/react
```

Update `frontend/tests/setup.ts`:
```typescript
import { toHaveNoViolations } from 'jest-axe'

expect.extend(toHaveNoViolations)
```

Add to key component tests:
```typescript
// Dashboard.test.tsx
import { axe } from 'jest-axe'

test('Dashboard has no accessibility violations', async () => {
  const { container } = render(<Dashboard />)
  const results = await axe(container)
  expect(results).toHaveNoViolations()
})
```

Add to:
- `Dashboard.test.tsx`
- `PortfolioDetail.test.tsx` (create if doesn't exist)
- `TradeForm.test.tsx` (already exists)

#### 4.2 Add Theme Context Tests (Optional)

If needed, add unit tests for theme context:
```typescript
// ThemeContext.test.tsx
test('Theme toggle updates localStorage', () => {
  const { result } = renderHook(() => useTheme())
  act(() => result.current.setTheme('dark'))
  expect(localStorage.getItem('theme')).toBe('dark')
})
```

#### 4.3 Add Route Tests for 404 (Optional)

```typescript
// App.test.tsx or routes.test.tsx
test('Shows NotFound for invalid route', () => {
  render(
    <MemoryRouter initialEntries={['/invalid']}>
      <App />
    </MemoryRouter>
  )
  expect(screen.getByText('404')).toBeInTheDocument()
})
```

---

### Phase 5: Documentation (15 min)

#### 5.1 Create E2E Testing Standards

Create `docs/E2E_TESTING_STANDARDS.md`:

```markdown
# E2E Testing Standards

## When to Write E2E Tests

✅ **DO write E2E tests for**:
- Critical user journeys (signup, login, checkout, trading)
- Third-party integrations (Clerk, payment gateways, APIs)
- Multi-step workflows (create → edit → delete)
- Features that span multiple pages/components
- Happy path + critical error paths

❌ **DON'T write E2E tests for**:
- CSS/styling (use Tailwind, visual regression in Storybook)
- Accessibility (use jest-axe in component tests)
- Interactive states (hover, focus) - use component tests
- Simple routes/pages (use React Router tests)
- Form validation (use component tests)
- Theme switching (use context/component tests)

## Test Pyramid

```
        /\
       /  \   E2E (~20 tests) - Critical paths
      /    \  - 5-8 min runtime
     /------\  Integration (~50 tests) - Component interactions
    /--------\ - 1-2 min runtime
   /----------\ Unit (~200+ tests) - Pure logic, components
  /------------\ - <10s runtime
```

## E2E Test Checklist

Before writing an E2E test, ask:
1. ☑️ Does this test a critical user journey? (If no → component test)
2. ☑️ Does this require backend integration? (If no → component test)
3. ☑️ Does this span multiple pages? (If no → component test)
4. ☑️ Is this a third-party integration? (If no → consider component test)

If you answered "no" to all → **Don't write E2E test**

## Examples

**Good E2E Tests**:
- User creates portfolio → buys stock → sells stock → sees profit
- User signs up → verifies email → logs in
- User switches portfolios → data isolation verified

**Bad E2E Tests** (use component tests instead):
- Theme toggle changes dark/light mode
- Form validation shows error messages
- Button shows hover state
- Page is accessible (WCAG compliant)
- Responsive layout on mobile
```

#### 5.2 Update CONTRIBUTING.md

Add section on testing strategy linking to E2E_TESTING_STANDARDS.md

---

## File Changes Summary

### Files to DELETE
1. ❌ `frontend/tests/e2e/accessibility.spec.ts` (209 lines)
2. ❌ `frontend/tests/e2e/interactive-states.spec.ts` (221 lines)
3. ❌ `frontend/tests/e2e/responsive.spec.ts` (93 lines)
4. ❌ `frontend/tests/e2e/visual-regression.spec.ts` (127 lines)

### Files to MODIFY
5. ⚠️ `frontend/tests/e2e/not-found.spec.ts` (74 → 20 lines) - Keep 1 test
6. ⚠️ `frontend/tests/e2e/dark-mode.spec.ts` (119 → 40 lines) - Keep 2 tests

### Files to KEEP (No Changes)
7. ✅ `frontend/tests/e2e/trading.spec.ts` (450 lines, 6 tests)
8. ✅ `frontend/tests/e2e/portfolio-creation.spec.ts` (170 lines, 4 tests)
9. ✅ `frontend/tests/e2e/multi-portfolio.spec.ts` (206 lines, 3 tests)
10. ✅ `frontend/tests/e2e/analytics.spec.ts` (153 lines, 4 tests)
11. ✅ `frontend/tests/e2e/clerk-auth-test.spec.ts` (38 lines, 1 test)

### Files to CREATE
12. ➕ `frontend/tests/Dashboard.test.tsx` (if doesn't exist) - Add a11y test
13. ➕ `frontend/tests/PortfolioDetail.test.tsx` (if doesn't exist) - Add a11y test
14. ➕ `docs/E2E_TESTING_STANDARDS.md` - New documentation

### Files to UPDATE
15. 🔧 `frontend/tests/setup.ts` - Add jest-axe support
16. 🔧 `frontend/package.json` - Add `jest-axe`, remove `@axe-core/playwright`

---

## Expected Outcome

**Before**:
- 60 E2E tests (11 files)
- 1,657 lines of E2E test code
- 10-15 min runtime
- Many tests at wrong abstraction level

**After**:
- ~20 E2E tests (6 files, 5 deleted, 2 reduced)
- ~1,000 lines of E2E test code
- 5-8 min runtime
- All tests at correct abstraction level
- Component tests for accessibility
- Clear E2E testing standards

**Benefits**:
- 🚀 **2x faster CI** (5-8 min vs 10-15 min)
- 🎯 **Focused tests** (critical paths only)
- 🔧 **Easier maintenance** (fewer brittle tests)
- ⚡ **Faster feedback** (unit/component tests are instant)
- 📚 **Clear standards** (when to use E2E vs component)

---

## Testing Strategy

**After each deletion**:
1. Run `task test:frontend` - Ensure unit tests pass
2. Run `task test:e2e` - Ensure remaining E2E tests pass
3. Commit incrementally

**Final validation**:
```bash
task test:all    # All tests pass
task ci          # Full CI simulation
```

---

## Notes for Agent

**Priorities**:
1. **DELETE first** - Remove wrong-level tests
2. **Fix remaining** - Get 20 critical tests passing
3. **Add replacements** - Component tests for accessibility
4. **Document standards** - Prevent future mistakes

**Keep commits atomic**:
- Commit 1: Delete accessibility tests
- Commit 2: Delete interactive-states tests
- Commit 3: Delete responsive tests
- Commit 4: Delete visual-regression tests
- Commit 5: Reduce not-found tests
- Commit 6: Reduce dark-mode tests
- Commit 7: Add jest-axe component tests
- Commit 8: Add E2E testing standards doc

**Verification**:
- All unit tests pass (194)
- All backend tests pass (545)
- All E2E tests pass (~20)
- CI passes
- Documentation complete

---

## References

- Test Pyramid: https://martinfowler.com/articles/practical-test-pyramid.html
- jest-axe: https://github.com/nickcolley/jest-axe
- Testing Library: https://testing-library.com/docs/react-testing-library/intro/
- Playwright Best Practices: https://playwright.dev/docs/best-practices
