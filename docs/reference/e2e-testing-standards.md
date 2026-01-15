# E2E Testing Standards

## Overview

This document establishes guidelines for when and how to write End-to-End (E2E) tests in the PaperTrade project. Following these standards ensures we maintain a healthy test pyramid with fast, reliable tests at appropriate abstraction levels.

## The Testing Pyramid

```
        /\
       /  \   E2E (~20 tests) - Critical user journeys
      /    \  - 5-8 min runtime
     /------\  Integration (~50 tests) - Component interactions
    /--------\ - 1-2 min runtime
   /----------\ Unit (~200+ tests) - Pure logic, components
  /------------\ - <10s runtime
```

**Key Principle**: The higher up the pyramid, the fewer tests you should have. E2E tests are expensive to maintain and slow to run.

## When to Write E2E Tests

### ✅ DO write E2E tests for:

1. **Critical User Journeys**
   - Core workflows that, if broken, would severely impact users
   - Example: User creates portfolio → buys stock → sells stock → sees profit

2. **Third-Party Integrations**
   - External services that require real integration testing
   - Example: Clerk authentication flow, payment gateways

3. **Multi-Step Workflows**
   - Complex flows that span multiple pages/components
   - Example: Complete trading flow with navigation and state management

4. **Features Spanning Multiple Pages**
   - User actions that require navigation and state persistence
   - Example: Portfolio creation → navigate to detail → verify data persists

5. **Happy Path + Critical Error Paths**
   - Main success scenario and important failure cases
   - Example: Successful trade + insufficient funds error

### ❌ DON'T write E2E tests for:

1. **CSS/Styling**
   - Use Tailwind utilities as-is
   - If visual regression needed, use Storybook + Chromatic/Percy
   - Example: ~~Testing hover states, responsive breakpoints~~

2. **Accessibility**
   - Use `jest-axe` in component tests (fast, in jsdom)
   - Example: ~~E2E test checking WCAG compliance~~
   - Instead: Component test with `axe(container)`

3. **Interactive States**
   - Use `@testing-library/user-event` in component tests
   - Example: ~~E2E test for button hover, focus states~~
   - Instead: Component test with `user.hover(button)`

4. **Simple Routes/Pages**
   - Use React Router tests for navigation
   - Example: ~~E2E test for 404 page links~~
   - Instead: Component test with `<MemoryRouter>`

5. **Form Validation**
   - Use component tests with controlled inputs
   - Example: ~~E2E test for required field errors~~
   - Instead: Component test rendering form with invalid data

6. **Theme Switching**
   - Use context/component tests
   - Example: ~~E2E test for dark mode toggle~~
   - Instead: ThemeContext unit test + one E2E smoke test

## E2E Test Checklist

Before writing an E2E test, ask yourself:

1. ☑️ **Does this test a critical user journey?**
   - If no → component test

2. ☑️ **Does this require backend integration?**
   - If no → component test with MSW mocks

3. ☑️ **Does this span multiple pages?**
   - If no → component test

4. ☑️ **Is this a third-party integration?**
   - If no → consider component test

**If you answered "no" to all → Don't write an E2E test**

## Examples

### ✅ Good E2E Tests

```typescript
// ✅ GOOD: Critical user journey with backend integration
test('User creates portfolio → buys stock → sells stock → sees profit', async ({ page }) => {
  // Create portfolio
  await page.getByTestId('create-portfolio-btn').click()
  await page.getByTestId('portfolio-name-input').fill('Test Portfolio')
  await page.getByTestId('initial-deposit-input').fill('10000')
  await page.getByTestId('submit-portfolio-btn').click()

  // Buy stock
  await page.getByTestId('trade-form-ticker-input').fill('AAPL')
  await page.getByTestId('trade-form-quantity-input').fill('10')
  await page.getByTestId('trade-form-buy-button').click()
  await expect(page.getByText('Trade executed successfully')).toBeVisible()

  // Sell stock
  await page.getByTestId('trade-form-action-sell').click()
  await page.getByTestId('trade-form-ticker-input').fill('AAPL')
  await page.getByTestId('trade-form-quantity-input').fill('10')
  await page.getByTestId('trade-form-sell-button').click()

  // Verify profit shown
  await expect(page.getByTestId('portfolio-total-gain-loss')).toContainText('$')
})

// ✅ GOOD: Third-party integration
test('Clerk authentication flow works', async ({ page }) => {
  await clerk.signIn({ page, emailAddress: 'test@example.com' })
  await page.waitForURL('**/dashboard')
  await expect(page.getByTestId('user-profile-button')).toBeVisible()
})

// ✅ GOOD: Multi-portfolio workflow
test('User switches between portfolios and data isolates correctly', async ({ page }) => {
  // Create two portfolios
  // Switch between them
  // Verify data doesn't leak between portfolios
})
```

### ❌ Bad E2E Tests (Use Component Tests Instead)

```typescript
// ❌ BAD: Testing CSS hover state via E2E
test('Button shows hover state', async ({ page }) => {
  await page.hover('[data-testid="trade-button"]')
  // Don't test CSS in E2E!
})

// ✅ GOOD: Trust Tailwind or use component test
test('Button applies hover styles', async () => {
  const user = userEvent.setup()
  const { getByRole } = render(<Button>Trade</Button>)
  await user.hover(getByRole('button'))
  // Component test is faster and sufficient
})

// ❌ BAD: Testing accessibility via E2E
test('Dashboard is accessible', async ({ page }) => {
  const results = await new AxeBuilder({ page }).analyze()
  expect(results.violations).toEqual([])
})

// ✅ GOOD: Use jest-axe in component test
test('Dashboard has no accessibility violations', async () => {
  const { container } = render(<Dashboard />)
  const results = await axe(container)
  expect(results).toHaveNoViolations()
})

// ❌ BAD: Testing form validation via E2E
test('Shows error when portfolio name is empty', async ({ page }) => {
  await page.getByTestId('create-portfolio-btn').click()
  await page.getByTestId('submit-portfolio-btn').click()
  await expect(page.getByText('Portfolio name is required')).toBeVisible()
})

// ✅ GOOD: Component test for validation
test('Shows error when portfolio name is empty', async () => {
  const user = userEvent.setup()
  const { getByTestId, getByText } = render(<CreatePortfolioForm />)
  await user.click(getByTestId('submit-portfolio-btn'))
  expect(getByText('Portfolio name is required')).toBeInTheDocument()
})

// ❌ BAD: Testing responsive design via E2E
test('Dashboard is responsive on mobile', async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 667 })
  // Don't test Tailwind responsive utilities in E2E!
})

// ✅ GOOD: Trust Tailwind or use visual regression tool
// No test needed - trust Tailwind's responsive utilities
// If visual regression needed, use Storybook + Chromatic
```

## E2E Test Structure

### Naming Conventions

- Use descriptive names that explain the user journey
- Focus on behavior, not implementation
- Include success and failure scenarios

```typescript
// ✅ GOOD
test('User can buy stock with sufficient funds')
test('User sees error when buying stock with insufficient funds')
test('User can create multiple portfolios and switch between them')

// ❌ BAD
test('Buy button works')
test('API returns 200')
test('Trade form submits')
```

### Test Organization

```typescript
test.describe('Trading Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Setup: authenticate and navigate to starting point
    await clerk.signIn({ page, emailAddress: 'test@example.com' })
    await page.waitForURL('**/dashboard')
  })

  test('should execute buy trade and update portfolio', async ({ page }) => {
    // Arrange: Create portfolio if needed
    // Act: Execute trade
    // Assert: Verify portfolio updated
  })

  test('should show error when buying with insufficient funds', async ({ page }) => {
    // Arrange: Set up portfolio with low balance
    // Act: Attempt to buy expensive stock
    // Assert: Verify error message
  })
})
```

### Use Test IDs for Stability

Always use `data-testid` attributes for reliable element selection:

```typescript
// ✅ GOOD: Stable test IDs
await page.getByTestId('trade-form-buy-button').click()
await page.getByTestId('portfolio-summary-card').click()

// ❌ BAD: Fragile selectors
await page.getByText('Buy').click() // Breaks if text changes
await page.locator('.btn-primary').click() // Breaks if CSS changes
```

See [testing-conventions.md](./testing-conventions.md) for complete test ID naming guidelines.

## Current E2E Test Suite

As of this refactoring (Task 098), we maintain ~21 E2E tests:

| File | Tests | Purpose |
|------|-------|---------|
| `trading.spec.ts` | 6 | Core trading functionality |
| `portfolio-creation.spec.ts` | 4 | Portfolio CRUD operations |
| `multi-portfolio.spec.ts` | 3 | Multi-portfolio workflows |
| `analytics.spec.ts` | 4 | Analytics integration |
| `dark-mode.spec.ts` | 2 | Theme persistence (smoke test) |
| `not-found.spec.ts` | 1 | 404 routing (smoke test) |
| `clerk-auth-test.spec.ts` | 1 | Clerk integration |

**Total**: 21 tests, ~5-8 min runtime

## Migration Guide

If you find yourself writing an E2E test, ask:

1. **Can this be a component test?** → Use Vitest + Testing Library
2. **Is this testing CSS/styling?** → Trust Tailwind or use Storybook
3. **Is this testing accessibility?** → Use `jest-axe` in component tests
4. **Is this a critical user journey?** → E2E test is appropriate

## Running E2E Tests

```bash
# Run all E2E tests
npm run test:e2e

# Run in UI mode (interactive debugging)
npm run test:e2e:ui

# Run in headed mode (see browser)
npm run test:e2e:headed

# Run specific test file
npx playwright test tests/e2e/trading.spec.ts
```

## Debugging E2E Tests

```bash
# Debug mode (step through test)
npx playwright test --debug

# Trace viewer (inspect after run)
npx playwright test --trace on
npx playwright show-trace trace.zip

# Run single test
npx playwright test -g "should execute buy trade"
```

## Best Practices

1. **Keep E2E tests focused** - Test one user journey per test
2. **Use proper waits** - `waitForLoadState('networkidle')`, `waitForURL()`
3. **Clean up after tests** - Delete test data if possible
4. **Run serially for Clerk** - Parallel Clerk auth can conflict
5. **Use environment variables** - Don't hardcode credentials
6. **Retry on CI** - E2E tests can be flaky, retry 2x on CI
7. **Meaningful assertions** - Test user-visible outcomes, not implementation

## Related Documentation

- [Testing Conventions](./testing-conventions.md) - Test ID naming patterns
- [Testing Guide](./testing.md) - Quick reference for running tests
- [QA Accessibility Guide](./qa-accessibility-guide.md) - Accessibility testing
- [Contributing Guide](../CONTRIBUTING.md) - General testing guidelines
- [Playwright Docs](https://playwright.dev/) - Playwright API reference

## Questions?

If unsure whether to write an E2E test, ask:
> "Would a component test catch this bug just as well?"

If yes → Write a component test instead.
