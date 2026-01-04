# Testing Conventions

This document outlines the testing conventions for the PaperTrade project, including test ID naming standards for E2E tests.

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

### Migration Guidelines

When migrating existing tests:

1. **Add test IDs first**: Add `data-testid` attributes to components
2. **Update tests**: Replace fragile selectors with `getByTestId()`
3. **Keep existing attributes**: Don't remove `id`, `aria-label`, or other attributes
4. **Run tests**: Verify all tests pass after migration
5. **Document changes**: Note any test ID naming decisions in PR

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

## Other Testing Conventions

See [testing.md](./testing.md) for:
- Test philosophy and pyramid
- Running tests
- Writing tests (Arrange-Act-Assert)
- Naming conventions for test functions
- Common issues and solutions

## References

- [Playwright: Locate by test ID](https://playwright.dev/docs/locators#locate-by-test-id)
- [Testing Library: ByTestId](https://testing-library.com/docs/queries/bytestid/)
- [Playwright Best Practices](https://playwright.dev/docs/best-practices#use-locators)
