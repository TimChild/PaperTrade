# Task 062: Critical UX Fixes - Multi-Portfolio Access & Trade Execution

**Status**: Not Started
**Priority**: CRITICAL
**Depends On**: None (blocking user functionality)
**Estimated Effort**: 1-2 days

## Objective

Fix two critical UX bugs discovered during manual testing that make key features unusable:
1. Multiple portfolios not accessible from dashboard
2. Trade execution failing with 400 error

## Issue #1: Multiple Portfolios Not Accessible from Dashboard

### Problem
When a user has multiple portfolios, the dashboard only shows the FIRST portfolio created. Other portfolios are completely hidden from view with no way to access them through the UI.

### Steps to Reproduce
1. Sign in to the app
2. Create first portfolio (e.g., "Tech Growth Portfolio" with $1,000)
3. Create second portfolio (e.g., "Value Investing Portfolio" with $5,000)
4. Return to dashboard

### Expected Behavior
- Dashboard should show ALL portfolios, or
- There should be a dropdown/selector to switch between portfolios, or
- There should be a list view showing all portfolios

### Actual Behavior
- Dashboard shows message "You have 2 portfolios"
- Only the first portfolio is displayed
- Second portfolio is completely hidden
- No UI element to switch between or view other portfolios
- The second portfolio IS accessible via direct URL (`/portfolio/{id}`), but there's no way to get there from the UI

### Root Cause Analysis
Check `frontend/src/pages/Dashboard.tsx` - likely using `portfolios[0]` or similar single-portfolio access pattern instead of mapping over all portfolios.

### Solution
Update Dashboard to display all portfolios:
- Option A: Grid/list view of all portfolio cards
- Option B: Tabs/dropdown to select portfolio
- Option C: Summary cards with links to each portfolio

### Files to Modify
- `frontend/src/pages/Dashboard.tsx` - Main fix location
- `frontend/src/components/features/portfolio/PortfolioCard.tsx` - May need updates for multi-card layout
- Tests: Add E2E test for multi-portfolio display

---

## Issue #2: Trade Execution Failing with 400 Error

### Problem
Attempting to execute a BUY trade fails with a 400 Bad Request error.

### Steps to Reproduce
1. Navigate to portfolio detail page
2. Enter trade details:
   - Symbol: AAPL
   - Quantity: 5
   - Action: BUY
3. Click "Execute Buy Order"

### Expected Behavior
Trade should execute successfully and appear in transaction history.

### Actual Behavior
- Browser alert: "Failed to execute trade: Request failed with status code 400"
- Console error: "Failed to load resource: the server responded with a status of 400 (Bad Request)"
- API endpoint: `POST http://localhost:8000/api/v1/portfolios/{id}/trades`

### Root Cause Analysis
Investigate:
1. Frontend `TradeForm.tsx` - Check request payload format
2. Backend `portfolios.py` trade endpoint - Check validation
3. Possible causes:
   - Missing required field in request
   - Invalid field format (e.g., quantity as string vs number)
   - Market data unavailable for ticker
   - Authentication token issue

### Debugging Steps
1. Check browser network tab for exact request/response
2. Check backend logs for validation error details
3. Compare request payload with API schema

### Files to Investigate
- `frontend/src/components/features/portfolio/TradeForm.tsx`
- `backend/src/zebu/adapters/inbound/api/portfolios.py`
- `frontend/src/services/api/portfolios.ts`

---

## Success Criteria

- [ ] Dashboard displays ALL user portfolios (not just the first one)
- [ ] User can click on any portfolio to view its details
- [ ] Trade execution works for BUY orders
- [ ] Trade execution works for SELL orders
- [ ] New E2E tests verify multi-portfolio display
- [ ] New E2E tests verify trade execution
- [ ] All existing tests still pass

## Testing

### Manual Testing
1. Create 3+ portfolios, verify all visible on dashboard
2. Execute BUY trade on portfolio with sufficient cash
3. Execute SELL trade on portfolio with holdings
4. Verify transactions appear in history

### E2E Tests to Add
```typescript
// Multi-portfolio test
test('should display all user portfolios on dashboard', async ({ page }) => {
  // Create multiple portfolios
  // Verify all are visible on dashboard
  // Click each one to verify navigation works
})

// Trade execution test
test('should successfully execute BUY trade', async ({ page }) => {
  // Navigate to portfolio
  // Fill trade form
  // Submit and verify success
})
```

## Commands

```bash
# Run E2E tests
task test:e2e

# Run frontend tests
task test:frontend

# Check backend API
curl -X POST http://localhost:8000/api/v1/portfolios/{id}/trades \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{"ticker": "AAPL", "quantity": 5, "action": "BUY"}'
```

## Notes

- These bugs make the app essentially unusable for real users
- Fix ASAP before continuing with new features
- Consider adding smoke tests to catch similar regressions
