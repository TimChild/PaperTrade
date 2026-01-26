# Testing Standards

This document establishes testing standards, best practices, and conventions for the Zebu project.

## Table of Contents

- [E2E Testing Standards](#e2e-testing-standards)
- [Testing Conventions](#testing-conventions)
- [Accessibility Testing](#accessibility-testing)

---

## E2E Testing Standards

**Purpose**: Guidelines for when and how to write End-to-End (E2E) tests.

Following these standards ensures we maintain a healthy test pyramid with fast, reliable tests at appropriate abstraction levels.

### The Testing Pyramid

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

### When to Write E2E Tests

#### ✅ DO write E2E tests for:

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

#### ❌ DON'T write E2E tests for:

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

### E2E Test Checklist

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

### Examples

#### ✅ Good E2E Tests

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

#### ❌ Bad E2E Tests (Use Component Tests Instead)

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
```

### E2E Test Structure

#### Naming Conventions

Use descriptive names that explain the user journey:

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

#### Test Organization

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

#### Use Test IDs for Stability

Always use `data-testid` attributes for reliable element selection:

```typescript
// ✅ GOOD: Stable test IDs
await page.getByTestId('trade-form-buy-button').click()
await page.getByTestId('portfolio-summary-card').click()

// ❌ BAD: Fragile selectors
await page.getByText('Buy').click() // Breaks if text changes
await page.locator('.btn-primary').click() // Breaks if CSS changes
```

See [Testing Conventions](#testing-conventions) for complete test ID naming guidelines.

### Current E2E Test Suite

As of January 2026, we maintain ~21 E2E tests:

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

### Migration Guide

If you find yourself writing an E2E test, ask:

1. **Can this be a component test?** → Use Vitest + Testing Library
2. **Is this testing CSS/styling?** → Trust Tailwind or use Storybook
3. **Is this testing accessibility?** → Use `jest-axe` in component tests
4. **Is this a critical user journey?** → E2E test is appropriate

### Running E2E Tests

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

### Debugging E2E Tests

```bash
# Debug mode (step through test)
npx playwright test --debug

# Trace viewer (inspect after run)
npx playwright test --trace on
npx playwright show-trace trace.zip

# Run single test
npx playwright test -g "should execute buy trade"
```

### Best Practices

1. **Keep E2E tests focused** - Test one user journey per test
2. **Use proper waits** - `waitForLoadState('networkidle')`, `waitForURL()`
3. **Clean up after tests** - Delete test data if possible
4. **Run serially for Clerk** - Parallel Clerk auth can conflict
5. **Use environment variables** - Don't hardcode credentials
6. **Retry on CI** - E2E tests can be flaky, retry 2x on CI
7. **Meaningful assertions** - Test user-visible outcomes, not implementation

---

## Testing Conventions

**Purpose**: Naming standards and conventions for test IDs and test functions.

### Test ID Conventions

Test IDs (`data-testid` attributes) provide stable, explicit element targeting for E2E tests using Playwright.

#### Purpose

Test IDs make tests:
- **Reliable**: Don't break when UI copy changes
- **Clear**: Test intent is obvious from the selector
- **Debuggable**: Easy to identify which element a test is targeting
- **Maintainable**: Consistent naming makes updates easier

#### When to Use Test IDs

**Use test IDs for**:
- Interactive elements in E2E tests (buttons, inputs, links)
- Dynamic content that needs verification (portfolio names, balances)
- Elements difficult to target with role-based selectors

**Don't use test IDs for**:
- Unit/component tests (use Testing Library queries)
- Accessibility testing (use role-based selectors)
- Elements already uniquely identifiable by role + name

#### Naming Pattern

**Format**: `{component}-{element}-{variant?}`

**Rules**:
- Use kebab-case (lowercase with hyphens)
- Start with component or page name
- Be specific but not overly verbose
- Use semantic names (what it is, not what it does)
- For dynamic lists, include ID: `portfolio-card-${portfolio.id}`

#### Examples by Component

**Portfolio Components**:

```tsx
// CreatePortfolioForm
<input data-testid="create-portfolio-name-input" />
<input data-testid="create-portfolio-deposit-input" />
<button data-testid="create-portfolio-submit-button" />
<button data-testid="create-portfolio-cancel-button" />

// Dashboard
<button data-testid="create-first-portfolio-btn" />
<button data-testid="create-portfolio-header-btn" />
<div data-testid={`portfolio-card-${id}`} />
<a data-testid={`portfolio-card-link-${id}`} />

// PortfolioDetail
<h1 data-testid="portfolio-detail-name" />
<div data-testid="portfolio-detail-cash" />
<div data-testid="portfolio-detail-total-value" />
<a data-testid="portfolio-detail-trade-link" />
```

**Trading Components**:

```tsx
// TradeForm
<input data-testid="trade-form-ticker-input" />
<input data-testid="trade-form-quantity-input" />
<input data-testid="trade-form-price-input" />
<button data-testid="trade-form-buy-button" />
<button data-testid="trade-form-sell-button" />
<button data-testid="trade-form-action-buy" />
<button data-testid="trade-form-action-sell" />
```

**Holdings & Transactions**:

```tsx
// HoldingsTable
<table data-testid="holdings-table" />
<tr data-testid={`holding-row-${symbol}`} />
<td data-testid={`holding-symbol-${symbol}`} />
<td data-testid={`holding-quantity-${symbol}`} />
<td data-testid={`holding-value-${symbol}`} />

// TransactionList
<div data-testid="transaction-history-table" />
<div data-testid={`transaction-row-${idx}`} />
<span data-testid={`transaction-type-${idx}`} />
<span data-testid={`transaction-symbol-${idx}`} />
```

#### Usage in Components

**React/TypeScript Example**:

```tsx
// Static test ID
<button data-testid="create-portfolio-submit-button" type="submit">
  Create Portfolio
</button>

// Dynamic test ID with variable
<div data-testid={`portfolio-card-${portfolio.id}`}>
  <h3 data-testid={`portfolio-card-name-${portfolio.id}`}>
    {portfolio.name}
  </h3>
</div>

// Test ID with conditional rendering
{onCancel && (
  <button
    data-testid="create-portfolio-cancel-button"
    onClick={onCancel}
  >
    Cancel
  </button>
)}
```

#### Usage in E2E Tests

**Playwright Example**:

```typescript
// Locate by test ID
await page.getByTestId('create-portfolio-submit-button').click()

// Type into input
await page.getByTestId('trade-form-ticker-input').fill('IBM')

// Assert visibility
await expect(page.getByTestId('portfolio-detail-name')).toHaveText('My Portfolio')

// Wait for element
await page.getByTestId('holdings-table').waitFor({ state: 'visible' })

// Dynamic test ID
const portfolioId = '123'
await page.getByTestId(`portfolio-card-${portfolioId}`).click()
```

#### Best Practices

1. **Keep test IDs stable**: Don't change unless component structure changes
2. **Don't use implementation details**: Avoid `portfolio-card-div-wrapper-inner`
3. **Be consistent**: Follow the naming pattern across all components
4. **Document deviations**: If you deviate, document why
5. **Maintain accessibility**: Test IDs complement, don't replace, semantic HTML

#### Common Patterns

**Form inputs**:
```tsx
<input
  id="portfolio-name"                    // Keep for accessibility
  data-testid="create-portfolio-name-input"  // Add for testing
  aria-label="Portfolio Name"            // Keep for screen readers
/>
```

**Buttons with multiple states**:
```tsx
<button
  data-testid="trade-form-buy-button"
  disabled={action !== 'BUY'}
>
  {isSubmitting ? 'Processing...' : 'Execute Buy Order'}
</button>
```

**Dynamic lists**:
```tsx
{holdings.map(holding => (
  <tr key={holding.symbol} data-testid={`holding-row-${holding.symbol}`}>
    <td data-testid={`holding-symbol-${holding.symbol}`}>{holding.symbol}</td>
    <td data-testid={`holding-quantity-${holding.symbol}`}>{holding.quantity}</td>
  </tr>
))}
```

---

## Accessibility Testing

**Purpose**: Guidelines for ensuring WCAG 2.1 AA compliance and accessible UX.

### Automated Testing

#### Running All Tests

```bash
# Run all quality checks
task quality:frontend

# Run specific test suites
npm run test:unit          # Unit tests
npm run test:e2e           # E2E tests (requires services running)
npm run test:e2e:ui        # E2E tests with UI mode
```

#### Test Coverage

Current test coverage:
- **Unit Tests**: 225+ tests across 20+ test files
- **E2E Tests**: 21 tests covering critical user journeys
- **Accessibility Tests**: WCAG 2.1 AA compliance

#### Accessibility Test Suite

Located in `tests/e2e/accessibility.spec.ts`:

1. **WCAG 2.1 AA Compliance**
   - Dashboard page violations check
   - Portfolio Detail page violations check
   - Analytics page violations check

2. **Color Contrast**
   - Light mode contrast validation
   - Dark mode contrast validation

3. **Keyboard Navigation**
   - Tab order verification
   - Focus indicator visibility
   - All interactive elements accessible

4. **Screen Reader Support**
   - ARIA landmarks present
   - Form labels properly associated
   - Images have alt text

### Manual Accessibility Testing

#### Screen Reader Testing

**macOS with VoiceOver**:
1. Enable VoiceOver: `Cmd + F5`
2. Navigate:
   - `Tab` to move between elements
   - `Control + Option + Arrow Keys` to read content
3. Verify all interactive elements announced
4. Check form labels read correctly

**Windows with NVDA**:
1. Download from https://www.nvaccess.org/
2. Navigate:
   - `Tab` to move between elements
   - Arrow keys to read content
3. Verify all content accessible

#### Keyboard Navigation Testing

Test that all functionality is accessible without a mouse:

**Tab Order**:
- [ ] Theme toggle buttons
- [ ] Create portfolio button
- [ ] Form inputs (name, deposit)
- [ ] Submit buttons
- [ ] Portfolio cards
- [ ] Navigation links

**Focus Indicators**:
- [ ] All interactive elements show visible focus ring
- [ ] Focus ring has sufficient contrast (3:1 minimum)
- [ ] Focus order is logical

**Interactive Elements**:
- [ ] Buttons activated with `Enter` or `Space`
- [ ] Links activated with `Enter`
- [ ] Forms submitted with `Enter`
- [ ] Dialogs closed with `Escape`

#### Color Contrast Testing

**Chrome DevTools**:
1. Open DevTools → Elements
2. Inspect text elements
3. Check "Contrast ratio" in Styles panel
4. Minimum ratios:
   - Normal text: 4.5:1
   - Large text (18pt+): 3:1
   - UI components: 3:1

**Online Tools**:
- WebAIM Contrast Checker: https://webaim.org/resources/contrastchecker/
- Coolors Contrast Checker: https://coolors.co/contrast-checker

### Responsive Design Testing

#### Viewport Sizes to Test

1. **Mobile**: 375×667 (iPhone SE)
2. **Tablet**: 768×1024 (iPad)
3. **Desktop**: 1920×1080 (Full HD)
4. **Large Desktop**: 2560×1440 (QHD)

#### Responsive Test Checklist

For each viewport:
- [ ] No horizontal scrolling
- [ ] Text readable without zooming
- [ ] Buttons at least 44×44px (touch target)
- [ ] Form inputs appropriately sized
- [ ] Navigation accessible
- [ ] Content hierarchy maintained

### Cross-Browser Testing

#### Browsers to Test

Configured in `playwright.config.ts`:
1. **Chromium** (Chrome, Edge, Opera)
2. **Firefox**
3. **WebKit** (Safari)

#### Running Cross-Browser Tests

```bash
# Run all browsers
npm run test:e2e

# Run specific browser
npm run test:e2e -- --project=firefox
npm run test:e2e -- --project=webkit
```

### Performance Testing

#### Lighthouse CI

Configuration in `.lighthouserc.js`:

```bash
# Build production bundle
npm run build

# Run Lighthouse
npm run preview &
npx lighthouse http://localhost:4173/ --view
```

#### Performance Targets

- **Performance**: ≥90
- **Accessibility**: ≥95
- **Best Practices**: ≥90
- **SEO**: ≥90

### Pre-Release Accessibility Checklist

Before deploying to production:

**Accessibility**:
- [ ] WCAG 2.1 AA automated tests pass
- [ ] Manual keyboard navigation tested
- [ ] Manual screen reader testing completed
- [ ] Color contrast verified in both themes
- [ ] Form labels and ARIA attributes correct

**Cross-Browser**:
- [ ] Chrome/Chromium tested
- [ ] Firefox tested
- [ ] Safari/WebKit tested

**Responsive Design**:
- [ ] Mobile (375px) tested
- [ ] Tablet (768px) tested
- [ ] Desktop (1920px) tested
- [ ] No horizontal scroll on any viewport

### Resources

#### Tools
- [axe DevTools](https://www.deque.com/axe/devtools/) - Browser extension
- [Lighthouse](https://developers.google.com/web/tools/lighthouse) - Auditing
- [WebAIM Contrast Checker](https://webaim.org/resources/contrastchecker/)

#### Guidelines
- [WCAG 2.1 Quick Reference](https://www.w3.org/WAI/WCAG21/quickref/)
- [MDN Accessibility](https://developer.mozilla.org/en-US/docs/Web/Accessibility)
- [A11y Project Checklist](https://www.a11yproject.com/checklist/)

---

## Related Documentation

- [Testing Guide](./README.md) - General testing philosophy and running tests
- [E2E Testing Guide](./e2e-guide.md) - Manual testing, Playwright, QA procedures

---

**Last Updated**: January 26, 2026 (Consolidated from reference and procedures docs)
