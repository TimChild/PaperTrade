# Testing Standards and Best Practices

This document consolidates testing standards, conventions, and best practices for the Zebu project, including when to write E2E tests, test ID naming patterns, and accessibility requirements.

## Table of Contents

- [When to Write E2E Tests](#when-to-write-e2e-tests)
- [Test ID Conventions](#test-id-conventions)
- [Accessibility Testing](#accessibility-testing)
- [Quality Standards](#quality-standards)

---

## When to Write E2E Tests

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

### ✅ DO Write E2E Tests For

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

### ❌ DON'T Write E2E Tests For

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

### Good vs Bad E2E Tests

#### ✅ Good E2E Test Example

```typescript
// ✅ GOOD: Critical user journey with backend integration
test('User creates portfolio → buys stock → sells stock → sees profit', async ({ page }) => {
  // Create portfolio
  await page.getByTestId('create-portfolio-btn').click()
  await page.getByTestId('portfolio-name-input').fill('Test Portfolio')
  await page.getByTestId('initial-deposit-input').fill('10000')
  await page.getByTestId('submit-portfolio-btn').click()

  // Buy stock
  await page.getByTestId('trade-form-ticker-input').fill('IBM')
  await page.getByTestId('trade-form-quantity-input').fill('10')
  await page.getByTestId('trade-form-buy-button').click()
  await expect(page.getByText('Trade executed successfully')).toBeVisible()

  // Sell stock
  await page.getByTestId('trade-form-action-sell').click()
  await page.getByTestId('trade-form-ticker-input').fill('IBM')
  await page.getByTestId('trade-form-quantity-input').fill('10')
  await page.getByTestId('trade-form-sell-button').click()

  // Verify profit shown
  await expect(page.getByTestId('portfolio-total-gain-loss')).toContainText('$')
})
```

#### ❌ Bad E2E Test Examples

```typescript
// ❌ BAD: Testing CSS hover state via E2E
test('Button shows hover state', async ({ page }) => {
  await page.hover('[data-testid="trade-button"]')
  // Don't test CSS in E2E!
})

// ✅ GOOD: Use component test instead
test('Button applies hover styles', async () => {
  const user = userEvent.setup()
  const { getByRole } = render(<Button>Trade</Button>)
  await user.hover(getByRole('button'))
  // Component test is faster and sufficient
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

### Test Naming Conventions

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

---

## Test ID Conventions

### Purpose

Test IDs (`data-testid` attributes) provide stable, explicit element targeting for E2E tests using Playwright. They make tests:
- **Reliable**: Don't break when UI copy changes
- **Clear**: Test intent is obvious from the selector
- **Debuggable**: Easy to identify which element a test is targeting
- **Maintainable**: Consistent naming makes updates easier

### When to Use Test IDs

**Use test IDs for**:
- Interactive elements in E2E tests (buttons, inputs, links)
- Dynamic content that needs verification (portfolio names, balances)
- Elements that are difficult to target with role-based selectors

**Don't use test IDs for**:
- Unit/component tests (use Testing Library queries)
- Accessibility testing (use role-based selectors)
- Elements already uniquely identifiable by role + name

### Naming Pattern

**Format**: `{component}-{element}-{variant?}`

**Rules**:
- Use kebab-case (lowercase with hyphens)
- Start with component or page name
- Be specific but not overly verbose
- Use semantic names (what it is, not what it does)
- For dynamic lists, include ID: `portfolio-card-${portfolio.id}`

### Examples by Component

#### Portfolio Components

**CreatePortfolioForm**:
- `create-portfolio-name-input` - Portfolio name input field
- `create-portfolio-deposit-input` - Initial deposit input field
- `create-portfolio-submit-button` - Submit button
- `create-portfolio-cancel-button` - Cancel button (when present)

**Dashboard**:
- `create-first-portfolio-btn` - Create first portfolio button (empty state)
- `create-portfolio-header-btn` - Create portfolio button in header
- `portfolio-card-{id}` - Portfolio card in list
- `portfolio-card-name-{id}` - Portfolio name within card
- `portfolio-card-link-{id}` - Link to portfolio details

**PortfolioDetail**:
- `portfolio-detail-name` - Portfolio name heading
- `portfolio-detail-cash` - Cash balance display
- `portfolio-detail-total-value` - Total portfolio value
- `portfolio-detail-trade-link` - Link to trade form
- `portfolio-detail-back-link` - Back to dashboard link

#### Trading Components

**TradeForm**:
- `trade-form-ticker-input` - Stock symbol input
- `trade-form-quantity-input` - Quantity input
- `trade-form-price-input` - Price per share input (optional)
- `trade-form-buy-button` - Buy button
- `trade-form-sell-button` - Sell button
- `trade-form-action-buy` - Buy action toggle button
- `trade-form-action-sell` - Sell action toggle button

#### Holdings & Transactions

**HoldingsTable**:
- `holdings-table` - Holdings table container
- `holding-row-{symbol}` - Row for specific holding
- `holding-symbol-{symbol}` - Symbol cell
- `holding-quantity-{symbol}` - Quantity cell
- `holding-value-{symbol}` - Market value cell

**TransactionList**:
- `transaction-history-table` - Transaction list container
- `transaction-row-{idx}` - Transaction row (use index for uniqueness)
- `transaction-type-{idx}` - Transaction type cell
- `transaction-symbol-{idx}` - Symbol cell
- `transaction-amount-{idx}` - Amount cell

#### Navigation

**Navigation**:
- `nav-dashboard-link` - Dashboard navigation link
- `nav-portfolios-link` - Portfolios navigation link
- `nav-settings-link` - Settings navigation link

### Usage in Components

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

### Usage in E2E Tests

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

### Best Practices

1. **Keep test IDs stable**: Don't change test IDs unless component structure changes significantly
2. **Don't use implementation details**: Avoid test IDs like `portfolio-card-div-wrapper-inner`
3. **Be consistent**: Follow the naming pattern across all components
4. **Document deviations**: If you must deviate from the pattern, document why
5. **Maintain accessibility**: Test IDs complement, don't replace, semantic HTML and ARIA

### Common Patterns

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

### Automated Testing

#### Running Accessibility Tests

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
- **Unit Tests**: 194 tests across 20 test files
- **E2E Tests**: 10+ test files covering critical user journeys
- **Accessibility Tests**: WCAG 2.1 AA compliance

#### Accessibility Test Suite

Located in `tests/e2e/accessibility.spec.ts`, includes:

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

**macOS with VoiceOver**

1. **Enable VoiceOver**: `Cmd + F5`
2. **Navigate the app**:
   - Use `Tab` to move between elements
   - Use `Control + Option + Arrow Keys` to read content
   - Verify all interactive elements are announced
   - Check form labels are read correctly

**Windows with NVDA**

1. **Start NVDA**: Download from https://www.nvaccess.org/
2. **Navigate the app**:
   - Use `Tab` to move between elements
   - Use arrow keys to read content
   - Verify all content is accessible

#### Keyboard Navigation Testing

Test that all functionality is accessible without a mouse:

1. **Tab Order**:
   - [ ] Theme toggle buttons
   - [ ] Create portfolio button
   - [ ] Form inputs (name, deposit)
   - [ ] Submit buttons
   - [ ] Portfolio cards
   - [ ] Navigation links

2. **Focus Indicators**:
   - [ ] All interactive elements show visible focus ring
   - [ ] Focus ring has sufficient contrast (3:1 minimum)
   - [ ] Focus order is logical

3. **Interactive Elements**:
   - [ ] Buttons activated with `Enter` or `Space`
   - [ ] Links activated with `Enter`
   - [ ] Forms can be submitted with `Enter`
   - [ ] Dialogs can be closed with `Escape`

#### Color Contrast Testing

Use browser DevTools or online tools:

1. **Chrome DevTools**:
   - Open DevTools → Elements
   - Inspect text elements
   - Check "Contrast ratio" in Styles panel
   - Minimum ratios:
     - Normal text: 4.5:1
     - Large text (18pt+): 3:1
     - UI components: 3:1

2. **Online Tools**:
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
- [ ] Text is readable without zooming
- [ ] Buttons are at least 44×44px (touch target size)
- [ ] Form inputs are appropriately sized
- [ ] Navigation is accessible
- [ ] Content hierarchy is maintained

#### Browser DevTools Testing

Chrome/Edge/Firefox:
1. Open DevTools (`F12`)
2. Click device toolbar icon (or `Cmd/Ctrl + Shift + M`)
3. Select device from dropdown
4. Test all features on each device size

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

---

## Quality Standards

### Pre-Release Checklist

Before deploying to production:

#### Code Quality
- [ ] All unit tests passing (194+)
- [ ] All E2E tests passing
- [ ] Linting passes (0 errors)
- [ ] TypeScript compilation successful
- [ ] No console errors in production build

#### Accessibility
- [ ] WCAG 2.1 AA automated tests pass
- [ ] Manual keyboard navigation tested
- [ ] Manual screen reader testing completed
- [ ] Color contrast verified in both themes
- [ ] Form labels and ARIA attributes correct

#### Performance
- [ ] Production build size ≤500KB gzipped
- [ ] Lighthouse Performance ≥90
- [ ] Lighthouse Accessibility ≥95
- [ ] No unnecessary re-renders
- [ ] Images optimized

#### Cross-Browser
- [ ] Chrome/Chromium tested
- [ ] Firefox tested
- [ ] Safari/WebKit tested
- [ ] Edge tested (if possible)

#### Responsive Design
- [ ] Mobile (375px) tested
- [ ] Tablet (768px) tested
- [ ] Desktop (1920px) tested
- [ ] No horizontal scroll on any viewport

#### Visual Polish
- [ ] All states have proper styling (hover, focus, active, disabled)
- [ ] Transitions are smooth
- [ ] Loading states show skeletons/spinners
- [ ] Empty states are informative
- [ ] Error states are clear and actionable

#### User Experience
- [ ] All user flows tested end-to-end
- [ ] Navigation is intuitive
- [ ] Forms provide clear feedback
- [ ] Error messages are helpful
- [ ] Success messages are clear

### Performance Testing

#### Lighthouse CI

Configuration in `.lighthouserc.js`. Run locally:

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

#### Bundle Size Monitoring

```bash
# Build and check sizes
npm run build

# View detailed bundle analysis
npx vite-bundle-visualizer

# Current bundle size (as of latest build)
# - JavaScript: 265KB gzipped
# - CSS: 6.13KB gzipped
# - Total: ~271KB gzipped
```

### Error State Testing

#### Error Scenarios to Test

1. **Network Errors**:
   - [ ] Offline mode gracefully handled
   - [ ] Failed API requests show error messages
   - [ ] Retry mechanisms work

2. **Form Validation**:
   - [ ] Empty required fields show errors
   - [ ] Invalid formats show specific errors
   - [ ] Error messages are accessible (announced to screen readers)

3. **404 Not Found**:
   - [ ] Invalid routes show 404 page
   - [ ] 404 page is styled correctly
   - [ ] "Go Back" button works
   - [ ] "Return to Dashboard" button works

### CI/CD Integration

#### GitHub Actions Workflow

Located in `.github/workflows/ci.yml`:

1. **Backend Checks**: Runs on every PR
2. **Frontend Checks**: Runs on every PR
3. **E2E Tests**: Runs after backend/frontend checks pass

#### Local CI Simulation

Run all CI checks locally:

```bash
# Run all quality checks
task quality

# Run E2E tests (requires Docker services)
task docker:up
task test:e2e
```

### Troubleshooting

#### Common Issues

1. **E2E Tests Fail to Start**:
   - Check Docker services running: `docker compose ps`
   - Verify environment variables in `.env`
   - Check ports 5173 (frontend) and 8000 (backend) are available

2. **Accessibility Violations**:
   - Run axe DevTools browser extension for details
   - Check console for specific violations
   - Refer to WCAG 2.1 guidelines for fixes

3. **Visual Regression Failures**:
   - Review diff images in `test-results/`
   - Update baselines if changes are intentional
   - Check for timing issues (animations, loading states)

### Resources

#### Tools
- [axe DevTools](https://www.deque.com/axe/devtools/) - Browser extension for accessibility testing
- [Lighthouse](https://developers.google.com/web/tools/lighthouse) - Performance and accessibility auditing
- [WebAIM Contrast Checker](https://webaim.org/resources/contrastchecker/) - Color contrast validation

#### Guidelines
- [WCAG 2.1 Quick Reference](https://www.w3.org/WAI/WCAG21/quickref/)
- [MDN Accessibility](https://developer.mozilla.org/en-US/docs/Web/Accessibility)
- [A11y Project Checklist](https://www.a11yproject.com/checklist/)

#### Testing Documentation
- [Playwright Testing](https://playwright.dev/docs/intro)
- [Vitest Documentation](https://vitest.dev/)
- [Testing Library](https://testing-library.com/)

---

## Related Documentation

- [Testing README](./README.md) - General testing philosophy and quick reference
- [E2E Testing Guide](./e2e-guide.md) - Complete E2E testing procedures
