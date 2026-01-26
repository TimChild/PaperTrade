# Testing Standards

Testing standards, best practices, and conventions for Zebu.

## E2E Testing Standards

### The Testing Pyramid

```
        /\
       /  \   E2E (~20 tests) - Critical user journeys
      /    \  - 5-8 min runtime
     /------\  Integration (~50 tests) - Component interactions
    /--------\ - 1-2 min runtime
   /----------\ Unit (~550+ tests) - Pure logic, components
  /------------\ - <10s runtime
```

**Key Principle**: The higher up the pyramid, the fewer tests. E2E tests are expensive to maintain and slow to run.

### When to Write E2E Tests

#### ✅ DO write E2E tests for:

1. **Critical User Journeys** - Core workflows (e.g., create portfolio → buy → sell → see profit)
2. **Third-Party Integrations** - External services (e.g., Clerk auth, payment gateways)
3. **Multi-Step Workflows** - Complex flows spanning pages/components
4. **Features Spanning Pages** - Navigation with state persistence
5. **Happy Path + Critical Errors** - Success scenarios + important failures

#### ❌ DON'T write E2E tests for:

1. **CSS/Styling** - Trust Tailwind or use Storybook
2. **Accessibility** - Use `jest-axe` in component tests
3. **Interactive States** - Use `@testing-library/user-event` in component tests
4. **Simple Routes/Pages** - Use React Router tests
5. **Form Validation** - Use component tests with controlled inputs
6. **Theme Switching** - Use context/component tests

### E2E Test Checklist

Before writing an E2E test:

1. ☑️ **Does this test a critical user journey?** → If no, use component test
2. ☑️ **Does this require backend integration?** → If no, use component test with MSW
3. ☑️ **Does this span multiple pages?** → If no, use component test
4. ☑️ **Is this a third-party integration?** → If no, consider component test

**If you answered "no" to all → Don't write an E2E test**

### Good vs Bad Examples

```typescript
// ✅ GOOD: Critical journey with backend
test('User creates portfolio → buys stock → sells stock → sees profit', async ({ page }) => {
  await page.getByTestId('create-portfolio-btn').click()
  await page.getByTestId('portfolio-name-input').fill('Test Portfolio')
  // ... full user workflow
})

// ❌ BAD: Testing CSS
test('Button shows hover state', async ({ page }) => {
  await page.hover('[data-testid="trade-button"]')
})

// ✅ BETTER: Component test for styling
test('Button applies hover styles', async () => {
  const { getByRole } = render(<Button>Trade</Button>)
  await user.hover(getByRole('button'))
})
```

### Running E2E Tests

```bash
# All tests
task test:e2e

# Interactive mode
npm run test:e2e:ui

# Debug
npx playwright test --debug

# Specific test
npx playwright test tests/e2e/trading.spec.ts
```

---

## Testing Conventions

### Test ID Naming

**Format**: `{component}-{element}-{variant?}`

**Rules:**
- Use kebab-case
- Start with component/page name
- Be specific but concise
- For lists: include ID (e.g., `portfolio-card-${id}`)

**Examples:**

```tsx
// Portfolio Components
<input data-testid="create-portfolio-name-input" />
<button data-testid="create-portfolio-submit-button" />
<div data-testid={`portfolio-card-${portfolio.id}`} />

// Trading Components
<input data-testid="trade-form-ticker-input" />
<button data-testid="trade-form-buy-button" />
<button data-testid="trade-form-sell-button" />

// Holdings
<table data-testid="holdings-table" />
<tr data-testid={`holding-row-${symbol}`} />
<td data-testid={`holding-symbol-${symbol}`} />
```

### Usage in Tests

```typescript
// Locate and interact
await page.getByTestId('create-portfolio-submit-button').click()
await page.getByTestId('trade-form-ticker-input').fill('IBM')

// Assert
await expect(page.getByTestId('portfolio-detail-name')).toHaveText('My Portfolio')

// Dynamic
await page.getByTestId(`portfolio-card-${portfolioId}`).click()
```

### Best Practices

- ✅ Keep test IDs stable (don't change unless component restructures)
- ✅ Use semantic names (what it is, not what it does)
- ✅ Complement accessibility (don't replace `aria-label`, roles)
- ❌ Avoid implementation details (`portfolio-card-div-wrapper-inner`)

---

## Accessibility Testing

### Automated Tests

Located in `frontend/tests/e2e/accessibility.spec.ts`:

1. **WCAG 2.1 AA Compliance** - Automated violation checks
2. **Color Contrast** - Light and dark mode validation
3. **Keyboard Navigation** - Tab order, focus indicators
4. **Screen Reader Support** - ARIA landmarks, labels

```bash
# Run accessibility tests
task test:e2e -- tests/e2e/accessibility.spec.ts
```

### Manual Testing

#### Keyboard Navigation

Test all functionality without mouse:

- [ ] Tab order is logical
- [ ] All interactive elements accessible
- [ ] Focus indicators visible (3:1 contrast minimum)
- [ ] Buttons work with `Enter`/`Space`
- [ ] Forms submit with `Enter`
- [ ] Dialogs close with `Escape`

#### Screen Readers

**macOS (VoiceOver):**
```bash
# Enable: Cmd + F5
# Navigate: Tab, Control + Option + Arrow Keys
```

**Windows (NVDA):**
- Download: https://www.nvaccess.org/
- Navigate: Tab, Arrow Keys

**Checklist:**
- [ ] All interactive elements announced
- [ ] Form labels read correctly
- [ ] Images have alt text
- [ ] ARIA landmarks present

#### Color Contrast

**Minimum Ratios:**
- Normal text: 4.5:1
- Large text (18pt+): 3:1
- UI components: 3:1

**Tools:**
- Chrome DevTools → Elements → Styles → Contrast ratio
- WebAIM Contrast Checker: https://webaim.org/resources/contrastchecker/

### Responsive Testing

**Viewports:**
1. Mobile: 375×667 (iPhone SE)
2. Tablet: 768×1024 (iPad)
3. Desktop: 1920×1080 (Full HD)

**Checklist (each viewport):**
- [ ] No horizontal scrolling
- [ ] Text readable without zoom
- [ ] Touch targets ≥ 44×44px
- [ ] Content hierarchy maintained

### Cross-Browser Testing

**Browsers (via Playwright):**
- Chromium (Chrome, Edge)
- Firefox
- WebKit (Safari)

```bash
# All browsers
task test:e2e

# Specific browser
npm run test:e2e -- --project=firefox
```

### Performance Targets

**Lighthouse Scores:**
- Performance: ≥90
- Accessibility: ≥95
- Best Practices: ≥90
- SEO: ≥90

```bash
# Run Lighthouse
npm run build
npm run preview &
npx lighthouse http://localhost:4173/ --view
```

### Pre-Release Checklist

**Accessibility:**
- [ ] WCAG 2.1 AA automated tests pass
- [ ] Manual keyboard navigation tested
- [ ] Screen reader tested
- [ ] Color contrast verified (light + dark)
- [ ] Form labels and ARIA correct

**Quality:**
- [ ] All tests passing (796+ tests)
- [ ] Linting clean (0 errors)
- [ ] TypeScript compiles
- [ ] No console errors in production

**Cross-Platform:**
- [ ] Chrome/Chromium tested
- [ ] Firefox tested
- [ ] Safari/WebKit tested
- [ ] Mobile responsive (375px)
- [ ] Desktop (1920px)

---

## Resources

### Tools
- [axe DevTools](https://www.deque.com/axe/devtools/) - Browser extension
- [Lighthouse](https://developers.google.com/web/tools/lighthouse) - Auditing
- [Playwright](https://playwright.dev/) - E2E testing

### Guidelines
- [WCAG 2.1](https://www.w3.org/WAI/WCAG21/quickref/) - Accessibility standards
- [Testing Library](https://testing-library.com/) - Component testing
- [A11y Project](https://www.a11yproject.com/checklist/) - Accessibility checklist

---

## Related Documentation

- [Testing Guide](./README.md) - Testing philosophy and running tests
- [E2E Testing Guide](./e2e-guide.md) - Manual testing and Playwright procedures

---

**Last Updated**: January 26, 2026
