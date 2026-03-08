# E2E QA Validation Task

**Task Type**: Reusable QA Template
**Agent**: qa
**Priority**: High (when executed)
**Estimated Effort**: 30-45 minutes

## Objective

Perform comprehensive end-to-end quality assurance testing of the Zebu application to validate critical user workflows, identify bugs, and ensure the application meets quality standards before release or after significant changes.

## Context

This is a reusable task template that can be referenced by the orchestrator whenever comprehensive QA validation is needed. The QA agent should execute all test scenarios systematically and produce a detailed test report.

**When to use this task**:
- After merging multiple PRs affecting core features
- Before deploying to production
- After major refactoring or architecture changes
- When user-reported issues suggest broader quality concerns
- Periodically (e.g., weekly) as part of quality maintenance

## Test Scenarios to Execute

### Scenario 1: New User Onboarding ⭐ Critical

**User Story**: As a new user, I want to create my first portfolio so I can start tracking investments.

**Steps**:
1. Navigate to application at http://localhost:5173
2. Verify dashboard loads (may show empty state or demo data)
3. Click "Create Portfolio" button
4. Fill portfolio creation form:
   - Name: "QA Test Portfolio [DATE]"
   - Initial Deposit: $10,000.00
5. Submit form
6. Verify modal closes
7. Verify new portfolio appears in dashboard
8. Verify cash balance shows $10,000.00
9. Verify no console errors

**Expected Results**:
- ✅ Modal opens without errors
- ✅ Form validation works (try invalid inputs first)
- ✅ Portfolio created successfully
- ✅ Portfolio appears in list immediately (no refresh needed)
- ✅ Cash balance accurate
- ✅ Clean console (no errors or warnings)

**Failure Modes to Test**:
- Submit empty form (should show validation)
- Submit negative deposit (should reject)
- Submit with special characters in name

---

### Scenario 2: Stock Trading Workflow ⭐ Critical

**User Story**: As an investor, I want to buy stocks so I can build my portfolio.

**Prerequisites**: Portfolio with available cash balance

**Steps**:
1. Select portfolio from dashboard
2. Navigate to "Trade Stocks" page
3. Fill trade form:
   - Symbol: IBM (known to work reliably)
   - Quantity: 10
   - Order Type: Buy
4. Click "Execute Buy Order"
5. Verify trade confirmation message
6. Navigate back to portfolio dashboard
7. Verify holdings table shows:
   - IBM position with 10 shares
   - Current price or fallback indicator
   - Total value
8. Verify cash balance reduced correctly
9. Navigate to transaction history
10. Verify trade appears in history

**Expected Results**:
- ✅ Trade executes without errors (or clear error message if rate limited)
- ✅ Confirmation modal shows success
- ✅ Holdings table updates immediately
- ✅ Cash balance calculation correct
- ✅ Transaction history accurate
- ✅ Average cost basis calculated

**Failure Modes to Test**:
- Invalid ticker (e.g., "INVALID") - should show error
- Zero quantity - should prevent trade
- Insufficient funds - should block trade
- Rate limiting - should handle gracefully

---

### Scenario 3: Portfolio Value Tracking ⭐ Critical

**User Story**: As an investor, I want to see my portfolio's current value and performance.

**Prerequisites**: Portfolio with at least one position

**Steps**:
1. Navigate to portfolio dashboard
2. Verify portfolio summary displays:
   - Total portfolio value
   - Cash balance
   - Invested amount
   - Gains/losses (if any)
3. Examine holdings table:
   - All positions listed
   - Quantities correct
   - Prices display (or fallback message)
   - Position values calculated
4. Check price charts (if implemented):
   - Charts render without errors
   - No $NaN values
   - Reasonable data shown

**Expected Results**:
- ✅ All monetary values formatted correctly ($X,XXX.XX)
- ✅ No $NaN, undefined, or null displayed
- ✅ Calculations accurate (spot check manually)
- ✅ Fallback messages when price unavailable
- ✅ Charts render or show appropriate message

**Edge Cases**:
- Rate limited ticker (should show fallback)
- Multiple positions (calculations aggregate correctly)
- Zero-value positions

---

### Scenario 4: Multiple Portfolios ⭐ High

**User Story**: As an investor, I want to manage multiple portfolios independently.

**Steps**:
1. Create second portfolio:
   - Name: "QA Test Portfolio 2 [DATE]"
   - Initial Deposit: $5,000.00
2. Execute trade in Portfolio 2:
   - Symbol: AAPL
   - Quantity: 5
   - Order: Buy
3. Switch back to first portfolio
4. Verify first portfolio state unchanged
5. Switch to Portfolio 2
6. Verify AAPL position appears
7. Create third portfolio (test limits if any)

**Expected Results**:
- ✅ Can create multiple portfolios
- ✅ Portfolios isolated (no data leakage)
- ✅ Switching portfolios maintains state
- ✅ Each portfolio tracks independently
- ✅ No confusion in UI about which is active

---

### Scenario 5: Selling Positions ⭐ High

**User Story**: As an investor, I want to sell stocks to realize gains or rebalance.

**Prerequisites**: Portfolio with existing position (from Scenario 2)

**Steps**:
1. Navigate to Trade page
2. Select SELL order type
3. Choose IBM ticker
4. Enter quantity: 5 (partial position)
5. Execute sell order
6. Verify confirmation
7. Check holdings table:
   - IBM quantity reduced to 5
   - Cash balance increased
8. Verify transaction history shows both buy and sell

**Expected Results**:
- ✅ Sell executes successfully
- ✅ Position quantity decreases
- ✅ Cash balance increases
- ✅ Average cost basis unchanged
- ✅ Gain/loss calculated if displayed

**Failure Modes**:
- Sell more than owned - should error
- Sell zero shares - should prevent
- Sell from wrong portfolio - should prevent

---

### Scenario 6: Error Handling & Edge Cases ⭐ Medium

**User Story**: As a user, I want clear error messages when things go wrong.

**Test Cases**:

1. **Invalid Ticker**:
   - Try to trade "NOTREAL" ticker
   - Expected: Clear error message, no state corruption

2. **Network Issues**:
   - Simulate by trading during rate limit
   - Expected: Graceful degradation, retry logic

3. **Insufficient Funds**:
   - Try to buy $100,000 of stock with $10,000 balance
   - Expected: Validation error before API call

4. **Concurrent Actions**:
   - Rapidly click trade button multiple times
   - Expected: Debouncing prevents duplicate trades

5. **Browser Refresh**:
   - Refresh page mid-workflow
   - Expected: State recovers, no data loss

**Expected Results**:
- ✅ All errors have user-friendly messages
- ✅ Technical details hidden (no stack traces to user)
- ✅ User can recover from errors
- ✅ No state corruption
- ✅ Errors logged to console for debugging

---

### Scenario 7: Responsive Design (if time permits) ⭐ Low

**Steps**:
1. Resize browser window to mobile width (375px)
2. Navigate through key pages
3. Test critical workflows on mobile layout

**Expected Results**:
- ✅ Layout adapts to smaller screens
- ✅ All functionality accessible
- ✅ No horizontal scrolling
- ✅ Touch targets adequately sized

---

## Test Execution Guidelines

### Setup

```bash
# Ensure services are running
cd /Users/timchild/github/Zebu

# Start Docker services
task docker:up

# Start backend in background
mkdir -p temp
cd backend && uv run uvicorn src.main:app --reload > ../temp/backend.log 2>&1 &
echo $! > ../temp/backend.pid
cd ..

# Start frontend in background
cd frontend && npm run dev > ../temp/frontend.log 2>&1 &
echo $! > ../temp/frontend.pid
cd ..

# Wait for services
sleep 5

# Verify health
curl http://localhost:8000/health
curl -I http://localhost:5173/
```

### Execution

1. Use Playwright MCP tools for browser automation
2. Document each step with timestamps
3. Capture screenshots for:
   - Initial state
   - After each major action
   - Any errors or unexpected behavior
4. Save console logs after each scenario
5. Note network requests for failed operations

### Evidence Collection

For each scenario, capture:
- **Screenshots**: Before/after key actions
- **Console Logs**: `mcp_microsoft_pla_browser_console_messages()`
- **Network Traces**: `mcp_microsoft_pla_browser_network_requests()`
- **Page State**: `mcp_microsoft_pla_browser_snapshot()` when relevant

### Cleanup

```bash
# Stop services
kill $(cat temp/backend.pid) 2>/dev/null || true
kill $(cat temp/frontend.pid) 2>/dev/null || true

# Review logs if needed
# cat temp/backend.log
# cat temp/frontend.log
```

## Deliverable: Test Report

Create a comprehensive test report in `agent_docs/progress/` following this format:

```markdown
# E2E QA Test Report - [DATE]

**Tester**: QA Agent
**Build/Commit**: [git commit hash]
**Environment**: Development (local)
**Test Duration**: [start time] - [end time]

## Executive Summary

Brief overview of testing session - overall health, major issues found, recommendations.

## Test Results Summary

| Scenario | Status | Severity | Duration | Notes |
|----------|--------|----------|----------|-------|
| New User Onboarding | ✅ Pass | Critical | 3 min | No issues |
| Stock Trading | ❌ Fail | Critical | 5 min | 503 error on trade |
| Portfolio Value | ⚠️ Warning | Critical | 4 min | Intermittent $NaN |
| Multiple Portfolios | ✅ Pass | High | 6 min | Works correctly |
| Selling Positions | 🚫 Blocked | High | - | Blocked by trading issue |
| Error Handling | ✅ Pass | Medium | 8 min | Good error messages |
| Responsive Design | ⏭️ Skipped | Low | - | Time constraint |

**Legend**:
- ✅ Pass: All expected results met
- ⚠️ Warning: Works but has issues
- ❌ Fail: Critical functionality broken
- 🚫 Blocked: Cannot test due to dependency
- ⏭️ Skipped: Not tested this session

## Detailed Findings

### ❌ FAIL: Stock Trading Workflow (Critical)

**Summary**: Trade execution fails with 503 Service Unavailable

**Severity**: Critical - core feature completely broken

**Steps to Reproduce**:
1. [exact steps]
2. [with specific values]
3. [...]

**Expected Behavior**: Trade executes successfully, holdings updated

**Actual Behavior**: Modal displays "Request failed with status code 503"

**Evidence**:
- Console Error: `[exact error message]`
- Network Request: `POST /api/portfolios/{id}/trades` → 503
- Screenshot: [describe what's shown]

**Root Cause Analysis**:
[Your analysis of why this might be happening]

**Impact**: Users cannot execute any trades. This blocks the primary use case.

**Recommendation**: Create high-priority task for backend-swe to investigate Alpha Vantage rate limiting and implement better retry logic.

### ⚠️ WARNING: Portfolio Value Tracking (Medium)

[Similar detailed format for warnings]

## Environment Details

- **Backend**: localhost:8000 (PID: XXXXX)
- **Frontend**: localhost:5173 (PID: XXXXX)
- **Database**: PostgreSQL 14 on localhost:5432
- **Redis**: localhost:6379
- **API**: Alpha Vantage (Free tier, 5 calls/min)
- **Browser**: [from Playwright config]

## Statistics

- **Total Test Cases**: X
- **Passed**: Y
- **Failed**: Z
- **Warnings**: W
- **Blocked/Skipped**: V
- **Test Coverage**: ~X% of critical user flows

## Action Items

### Immediate (Critical)
1. **Task #XXX**: Fix trading 503 error - assign to backend-swe
2. [...]

### High Priority
1. **Task #XXX**: Resolve $NaN display issue - may be addressed by PR #48
2. [...]

### Medium Priority
1. [...]

### Recommendations for Next QA Session
1. Retest trading workflow after fix
2. Add performance testing for large portfolios
3. Test with multiple concurrent users

## Attachments

- Console logs: `temp/backend.log`, `temp/frontend.log`
- Screenshots: [if saved separately]
- Network traces: [if captured]
```

## Follow-up Actions

For each **FAIL** finding:
1. Create a task in `agent_docs/tasks/` with format `XXX_[issue-description].md`
2. Include:
   - Link to QA report
   - Reproducible steps
   - Expected vs actual behavior
   - Suggested agent (backend-swe, frontend-swe, etc.)
   - Priority based on severity

Example task file:
```markdown
# Fix Trade Execution 503 Error

**Priority**: P0 (Critical)
**Agent**: backend-swe
**Related QA Report**: agent_docs/progress/YYYY-MM-DD_HH-MM-SS_e2e-qa-report.md

## Issue

Trading workflow fails with 503 Service Unavailable error, blocking all trade execution.

## Steps to Reproduce

1. Navigate to Trade page
2. Enter: Symbol=AAPL, Quantity=5, Order=Buy
3. Click Execute
4. Observe: 503 error modal

## Analysis

From QA testing: [summary from report]

Likely causes:
- Alpha Vantage rate limiting (5 calls/min free tier)
- Missing retry logic
- Cache not being checked before API call

## Expected Behavior

Trade should either:
- Execute successfully if price available
- Queue for retry if rate limited
- Use cached price if recent enough
- Show clear message if temporarily unavailable

## Acceptance Criteria

- [ ] Trade executes successfully with available price
- [ ] Rate limit errors handled gracefully
- [ ] User sees clear message during rate limit
- [ ] Cached prices used when available
- [ ] Retry logic implemented for transient failures
```

## Success Criteria

This QA task is complete when:
- ✅ All test scenarios executed
- ✅ Comprehensive test report created in `agent_docs/progress/`
- ✅ All failures documented with evidence
- ✅ Follow-up tasks created for critical/high issues
- ✅ Severity assessment provided for all findings
- ✅ Actionable recommendations given
- ✅ Services cleaned up properly

## Notes

- **Test Data**: Use prefix "QA Test" in portfolio names for easy identification and cleanup
- **Timing**: Allow 30-45 minutes for comprehensive testing
- **Rate Limits**: Be mindful of Alpha Vantage limits - wait between tests if needed
- **Mock User**: Use existing mock user ID or create new test user if needed
- **Repeatability**: Document exact conditions so tests can be replicated

## References

- [.github/agents/qa.md](../../.github/agents/qa.md) - QA Agent definition
- [docs/testing/e2e-guide.md](../../docs/testing/e2e-guide.md) - Technical testing guide and QA workflow
