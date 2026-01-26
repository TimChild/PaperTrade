# Task 043: Add E2E Tests for Trading Flow

**Status**: Open
**Priority**: High
**Agent**: frontend-swe
**Estimated Effort**: 2-3 hours

## Context

After fixing timezone issues in the backend (commits dae1e19 & 9ed3446) that prevented trading functionality from working, we discovered that our E2E test suite does not adequately cover the trading flow. Manual testing with Playwright MCP confirmed that buying stocks works correctly, but the automated E2E tests in `frontend/tests/e2e/trading.spec.ts` are failing.

**Manual Testing That Worked**:
- Created portfolio with $50,000
- Successfully bought 2 shares of IBM at $291.50 each
- Portfolio correctly updated (cash balance, holdings, transaction history)
- All backend datetime/timezone handling working correctly

**E2E Test Issues**:
The existing trading E2E tests timeout when trying to locate the trade form inputs:
- Tests expect `#ticker` and `#quantity` inputs to be visible after portfolio creation
- Tests timeout waiting for these inputs (10 second timeout)
- Portfolio creation tests pass and successfully show the portfolio heading
- The trade form is supposedly on the portfolio detail page but isn't found

## Problem

The E2E tests in `trading.spec.ts` cannot locate the trade form on the portfolio detail page after creating a portfolio. Three tests are failing:
1. "should execute buy trade and update portfolio"
2. "should show error when buying with insufficient funds"
3. "should display portfolio holdings after trade"

All fail with: `Error: expect(locator).toBeVisible() failed - Locator: locator('#ticker')`

## Objective

**First**, manually test the complete trading flow using Playwright MCP to understand the current behavior and validate that everything works end-to-end. **Then**, fix/create the E2E tests to properly test this workflow, which would have caught the timezone bugs that prevented trading from working in production.

## Requirements

### Functional Requirements
1. **Test Complete Trading Flow**:
   - Create portfolio with initial deposit
   - Navigate to/verify we're on portfolio detail page
   - Execute a BUY trade successfully
   - Verify portfolio updates:
     - Cash balance decreases
     - Holdings table shows purchased stock
     - Transaction history shows buy transaction
   - Verify trade dialog success message

2. **Test Error Handling**:
   - Test insufficient funds error
   - Verify error dialog displays appropriately

3. **Test Holdings Display**:
   - Verify holdings table shows correct data after trade

### Technical Requirements
1. Use correct selectors for the trade form (inspect actual DOM if needed)
2. Handle async state updates and loading states properly
3. Wait for elements appropriately (no arbitrary timeouts)
4. Follow existing E2E test patterns from `portfolio-creation.spec.ts`
5. Use `page.waitForEvent('dialog')` for alert dialogs
6. Ensure tests run reliably in CI environment

## Investigation Needed

1. **Inspect Portfolio Detail Page**:
   - What route does portfolio creation redirect to?
   - Is the trade form actually on that page?
   - Are there loading states or lazy loading that delay the form?
   - What are the actual selectors for the form inputs?

2. **Review UI Components**:
   - Check `TradeForm.tsx` for correct element IDs and structure
   - Check `PortfolioDetail.tsx` for page layout
   - Verify trade form is rendered on portfolio detail page

3. **Compare Working Test**:
   - `portfolio-creation.spec.ts` successfully creates portfolios and sees the heading
   - What's different about waiting for the trade form?

## Current Test Code Issues

Located in `frontend/tests/e2e/trading.spec.ts`:

```typescript
// Creates portfolio successfully
await expect(page.getByRole('heading', { name: 'Trading Portfolio' })).toBeVisible({
  timeout: 10000,
})

// But then this fails to find the ticker input
const symbolInput = page.locator('#ticker')
await expect(symbolInput).toBeVisible({ timeout: 10000 }) // TIMES OUT
```

**Known Information**:
- `#ticker` input exists in `TradeForm.tsx` (confirmed by code review)
- `#quantity` input exists in `TradeForm.tsx`
- TradeForm is rendered with heading "Execute Trade" (h3 element)
- Portfolio creation redirects to portfolio detail page (heading shows correctly)

## Acceptance Criteria

- [ ] **Manual testing completed** using Playwright MCP browser tools
  - [ ] Portfolio creation works
  - [ ] Can execute a buy trade successfully
  - [ ] Portfolio updates correctly (cash, holdings, transactions)
  - [ ] Documented exact selectors and flow
- [ ] All three trading E2E tests pass locally with `task test:e2e`
- [ ] Tests pass in CI environment (GitHub Actions)
- [ ] Tests properly wait for elements without arbitrary timeouts
- [ ] Tests verify complete trading workflow including:
  - [ ] Successful trade execution
  - [ ] Portfolio balance updates
  - [ ] Holdings table updates
  - [ ] Transaction history updates
  - [ ] Success dialog appears
- [ ] Tests handle error cases (insufficient funds)
- [ ] No flaky test behavior (run 3 times successfully)
- [ ] Follow established E2E test patterns

## Implementation Approach

### Phase 1: Manual Testing & Investigation (Required First)

Use the Playwright MCP browser tools to manually test the trading flow:

1. **Start the application**: Ensure Docker services are running (`task docker:up:all`)
2. **Navigate and test manually**:
   ```
   - Navigate to http://localhost:5173
   - Create a portfolio (e.g., "Test Portfolio", $10,000)
   - Observe what URL you're redirected to
   - Locate the trade form on the page
   - Fill in ticker (e.g., "IBM") and quantity (e.g., "2")
   - Execute the trade
   - Verify portfolio updates correctly
   ```
3. **Document your findings**:
   - What URL/route is the portfolio detail page?
   - What are the exact selectors for form inputs?
   - Are there any loading states or delays?
   - What is the exact structure of the trade form?
   - How do success/error dialogs appear?

### Phase 2: Fix/Create E2E Tests

Based on your manual testing findings, update the E2E tests in `frontend/tests/e2e/trading.spec.ts`:

1. **Use correct selectors** from your manual testing
2. **Handle navigation properly** to the portfolio detail page
3. **Wait for elements appropriately** (no arbitrary timeouts)
4. **Test the complete flow** verified manually
5. **Verify all success criteria**

## Implementation Hints

1. **Debug First**: Run tests in headed mode to see what's happening:
   ```bash
   cd frontend && npx playwright test --headed --grep "should execute buy trade"
   ```

2. **Check Page State**: Use Playwright inspector or screenshots:
   ```typescript
   await page.screenshot({ path: 'debug-screenshot.png' })
   console.log(await page.url())
   console.log(await page.content()) // See full HTML
   ```

3. **Review TradeForm Location**: The form might be:
   - In a collapsed/hidden section initially
   - Requiring scroll into view
   - On a different route than expected
   - Behind a loading state

4. **Pattern to Follow**: Look at how `portfolio-creation.spec.ts` waits for elements

5. **Manual Test Reference**: The Playwright MCP session that worked:
   - Navigated to `http://localhost:5173/portfolio/{id}`
   - Form was immediately visible
   - Used `page.getByRole('textbox', { name: /symbol/i })` successfully
   - Filled form and clicked "Execute Buy Order" button

## Related Files

- `frontend/tests/e2e/trading.spec.ts` - Tests to fix
- `frontend/tests/e2e/portfolio-creation.spec.ts` - Working reference
- `frontend/src/components/features/portfolio/TradeForm.tsx` - Form component
- `frontend/src/pages/PortfolioDetail.tsx` - Page layout
- Backend timezone fixes: commits `dae1e19` & `9ed3446`
- Docker Redis fix: commit `5e76f05`

## Success Metrics

- 7/7 E2E tests passing (4 portfolio creation + 3 trading)
- CI pipeline green on E2E workflow
- Trading flow properly tested to catch future regressions

## Notes

- Manual testing confirmed all backend functionality works correctly
- This would have caught the timezone issues that broke trading earlier
- Portfolio creation E2E tests are working fine, use as reference
- Consider if the dashboard shows portfolios and we need to click through vs. direct navigation
