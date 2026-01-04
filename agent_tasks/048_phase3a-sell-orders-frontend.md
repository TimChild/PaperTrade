# Task 048: Phase 3a SELL Orders - Frontend Implementation

**Agent**: frontend-swe
**Priority**: HIGH
**Estimated Effort**: 3-4 days
**Dependencies**: Task #047 (Backend) should complete API layer first
**Parallel Work**: Can start UI work while backend develops domain/application layers

---

## Objective

Implement SELL order functionality in the frontend to enable users to sell stocks they own through the UI. This includes updating the trade form, adding quick-sell buttons to the holdings table, and handling SELL-specific validation and error messages.

## Context

**What Currently Exists**:
- ✅ Trade form with BUY functionality
- ✅ Holdings table showing current positions
- ✅ Real-time price fetching and display
- ✅ Form validation for BUY orders
- ✅ TanStack Query for state management
- ✅ 81 passing frontend tests

**What's Missing**:
- ❌ SELL action in trade form dropdown
- ❌ SELL-specific client validation
- ❌ Quick Sell button in holdings table
- ❌ Error handling for insufficient holdings
- ❌ Visual feedback for owned quantity

**Critical**: Before implementing, **CHECK FOR EXISTING CODE** that might already support SELL functionality. Look for:
- Action dropdown options in trade form component
- SELL-related TypeScript types or enums
- Holdings-related action buttons
- Validation logic for sell orders

## Architecture Reference

**Primary Specification**: [`architecture_plans/phase3-refined/phase3a-sell-orders.md`](../architecture_plans/phase3-refined/phase3a-sell-orders.md)

**Key Sections**:
- Frontend Changes (lines 227-264)
- API Changes (lines 154-225) - for understanding backend contract
- Testing Strategy (lines 322-350) - E2E requirements

## Requirements

### 1. Trade Form Updates (1.5 days)

**File**: `frontend/src/components/features/portfolio/TradeForm.tsx` (or similar)

**Action Dropdown**:
- [ ] Update action select to include both "BUY" and "SELL" options
- [ ] Default to "BUY" (maintain current behavior)
- [ ] Add proper TypeScript type: `type TradeAction = "BUY" | "SELL"`

**Dynamic Validation**:
- [ ] When SELL selected:
  - Fetch current holdings for the portfolio
  - Show owned quantity below ticker input: "You own X shares of {ticker}"
  - Client-side hint: quantity <= owned (server is authoritative)
- [ ] When BUY selected:
  - Keep existing cash validation

**Visual Feedback**:
- [ ] Add holdings display when ticker + SELL selected
- [ ] Show helpful message if user doesn't own stock: "You don't own any shares of {ticker}"
- [ ] Disable submit button with tooltip if no holdings (UX improvement)

**Error Handling**:
- [ ] Handle 400 INSUFFICIENT_HOLDINGS error from API
- [ ] Display error message: "You only own X shares of {ticker}"
- [ ] Suggest maximum sellable quantity

### 2. Holdings Table Enhancement (1 day)

**File**: `frontend/src/components/features/portfolio/HoldingsTable.tsx` (or similar)

**Add Actions Column**:
- [ ] New column: "Actions" (right-most column)
- [ ] "Quick Sell" button for each holding row
- [ ] Button design: Secondary/outline style, small size
- [ ] Test ID: `holdings-quick-sell-{ticker}` (lowercase, kebab-case)

**Quick Sell Behavior**:
- [ ] On click:
  1. Pre-fill trade form ticker with holding's ticker
  2. Pre-fill quantity with owned quantity (user can adjust)
  3. Set action to "SELL"
  4. Scroll to/focus trade form
- [ ] Visual feedback: Button shows loading state while form updates

**Alternative Design** (if Quick Sell button doesn't fit):
- [ ] Add "Sell" link/icon in ticker column
- [ ] Opens modal with pre-filled SELL form
- [ ] Choose approach that best fits existing UI patterns

### 3. TypeScript Types & API Integration (0.5 days)

**Update API Types**:
- [ ] Ensure `TradeRequest` type includes:
  ```typescript
  interface TradeRequest {
    ticker: string;
    quantity: number;
    action: "BUY" | "SELL";  // Add SELL
  }
  ```
- [ ] Ensure `Transaction` type includes SELL:
  ```typescript
  type TransactionType = "DEPOSIT" | "BUY" | "SELL";
  ```

**Error Response Types**:
- [ ] Add error codes for SELL validation:
  ```typescript
  type TradeErrorCode =
    | "INSUFFICIENT_FUNDS"
    | "INSUFFICIENT_HOLDINGS"
    | "NO_HOLDINGS"
    | "INVALID_QUANTITY";
  ```

**TanStack Query Updates**:
- [ ] Ensure trade mutation invalidates holdings query
- [ ] Cache invalidation works for SELL (should already work)

### 4. Testing (1 day)

**Component Tests**:
- [ ] `TradeForm.test.tsx`:
  - Test SELL action dropdown option exists
  - Test holdings display when SELL + ticker selected
  - Test client validation for SELL
  - Test error handling for insufficient holdings
  - Minimum 6 new test cases

- [ ] `HoldingsTable.test.tsx`:
  - Test Quick Sell button renders
  - Test Quick Sell pre-fills form
  - Test Quick Sell with multiple holdings
  - Minimum 4 new test cases

**E2E Tests** (using Playwright):
- [ ] File: `frontend/tests/e2e/trading.spec.ts`
- [ ] New test: "Complete buy-sell trading loop"
  1. Create portfolio with $10,000
  2. BUY 10 shares of AAPL
  3. Verify holding shows 10 shares
  4. SELL 5 shares of AAPL
  5. Verify holding shows 5 shares
  6. Verify cash balance increased
- [ ] New test: "SELL error - insufficient holdings"
  1. Create portfolio
  2. Attempt to SELL stock without owning it
  3. Verify error message displays

**Test ID Standards** (from `docs/TESTING_CONVENTIONS.md`):
- Format: `{component}-{element}-{variant?}` (kebab-case)
- Examples:
  - `trade-form-action-select`
  - `trade-form-sell-button`
  - `holdings-quick-sell-{ticker}`
  - `trade-error-insufficient-holdings`

## Testing Requirements

**Quality Standards**:
- All 81 existing tests still pass (no regressions)
- Minimum 10 new component tests (6 TradeForm + 4 HoldingsTable)
- Minimum 2 new E2E tests
- ESLint + TypeScript compiler pass
- Follow testing conventions from `docs/TESTING_CONVENTIONS.md`

**Run Tests**:
```bash
task test:frontend         # All frontend tests
task test:e2e             # E2E tests (requires Docker services)
task lint:frontend        # ESLint + Prettier
```

## Success Criteria

- [ ] Trade form has SELL action dropdown
- [ ] SELL form shows owned quantity when ticker selected
- [ ] Holdings table has Quick Sell button
- [ ] Quick Sell pre-fills trade form correctly
- [ ] Client-side validation hints for SELL
- [ ] Error messages display for insufficient holdings
- [ ] All 93+ tests pass (81 existing + 12 new minimum)
- [ ] E2E test validates complete buy-sell loop
- [ ] No regressions in BUY functionality
- [ ] UI is responsive and accessible
- [ ] All test IDs follow kebab-case conventions

## Implementation Sequence

**Recommended Order**:

**Option A: Wait for Backend API** (lower risk):
1. Backend completes API layer (Task #047)
2. Update TypeScript types to match API
3. Implement trade form SELL option
4. Add holdings table Quick Sell
5. Write component tests
6. Write E2E tests

**Option B: Parallel Work** (faster, slightly higher risk):
1. **While backend works on Domain/Application**:
   - Create TypeScript types based on architecture spec
   - Build SELL UI components (form dropdown, quick sell button)
   - Write component tests with mocked API
2. **After backend completes API**:
   - Integrate with real API
   - Update types if API contract changed
   - Write E2E tests
   - Fix any integration issues

**Recommended**: **Option B** - The API contract is well-defined in the architecture spec, so parallel work is safe. Worst case: minor type adjustments needed.

**Commit Strategy**:
- Commit 1: `feat(ui): add SELL action to trade form dropdown`
- Commit 2: `feat(ui): add holdings display and validation for SELL`
- Commit 3: `feat(ui): add Quick Sell button to holdings table`
- Commit 4: `test: add SELL order component and E2E tests`

## Coordination with Backend

**API Contract** (from architecture spec):

**Request**:
```json
POST /api/v1/portfolios/{id}/trades
{
  "ticker": "IBM",
  "quantity": 10,
  "action": "SELL"
}
```

**Success Response** (201):
```json
{
  "id": "uuid",
  "portfolio_id": "uuid",
  "type": "SELL",
  "ticker": "IBM",
  "quantity": 10,
  "price": 185.50,
  "total": 1855.00,
  "timestamp": "2026-01-04T12:34:56Z"
}
```

**Error Responses**:
- 400 INSUFFICIENT_HOLDINGS: "Insufficient holdings for {ticker}"
- 400 NO_HOLDINGS: "No holdings found for {ticker}"

**If API differs**: Update types to match actual backend implementation, not spec.

## Autonomy & Flexibility

**You Have Autonomy To**:
- Choose Quick Sell button design (button vs link vs icon)
- Decide exact wording of validation messages
- Choose form focus/scroll behavior
- Add UX improvements beyond minimum requirements
- Decide where to place holdings display in form

**You Must Follow**:
- Test ID naming conventions (kebab-case from `docs/TESTING_CONVENTIONS.md`)
- Existing component patterns and styles
- TanStack Query patterns for state management
- Accessibility best practices (ARIA labels)
- Architecture spec API contract

**Ask for Clarification** (via PR comments) if:
- Backend API doesn't match spec
- Existing UI patterns conflict with requirements
- Unclear how to handle edge cases

## Risk Mitigation

**Potential Issues**:
1. **Backend API not ready**: Use Option A (wait) or mock API responses
2. **API contract changes**: Architecture spec is well-defined, low risk
3. **State management complexity**: Use existing TanStack Query patterns
4. **E2E test flakiness**: Follow existing E2E test patterns, use proper test IDs

## References

- **Architecture Spec**: `architecture_plans/phase3-refined/phase3a-sell-orders.md`
- **Testing Conventions**: `docs/TESTING_CONVENTIONS.md`
- **Existing Trade Form**: `frontend/src/components/features/portfolio/` (find exact file)
- **E2E Test Patterns**: `frontend/tests/e2e/portfolio.spec.ts`
- **Test ID Standards**: `.github/agents/frontend-swe.md`

## Notes

- **Backend coordination**: Backend task #047 handles domain/application/API
- **Can start early**: UI components can be built before API is ready
- **E2E tests require backend**: Wait for backend API completion before E2E tests
- **Phase 3b next**: Authentication will come after Phase 3a completes

---

**Ready to Start**: Once committed, use `gh agent-task create --custom-agent frontend-swe -F agent_tasks/048_phase3a-sell-orders-frontend.md`
