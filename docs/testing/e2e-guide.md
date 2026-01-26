# End-to-End Testing Guide

This guide covers E2E testing procedures for Zebu, including manual testing, Playwright automation, and QA workflows.

## Table of Contents

- [Manual Testing Procedure](#manual-testing-procedure)
- [Playwright E2E Testing](#playwright-e2e-testing)
- [Playwright MCP Usage](#playwright-mcp-usage)
- [QA Validation Workflow](#qa-validation-workflow)
- [Automated E2E Scripts](#automated-e2e-scripts)

---

## Manual Testing Procedure

**Purpose**: Manual validation of core functionality before releases or after significant changes.

**Last Updated**: January 1, 2026

### Prerequisites

1. **Start Services**:
   ```bash
   # Terminal 1: Docker services
   task docker:up
   
   # Terminal 2: Backend
   cd backend && task dev:backend
   
   # Terminal 3: Frontend
   cd frontend && npm run dev
   ```

2. **Note URLs**:
   - Frontend: http://localhost:5173 (or 5174 if port in use)
   - Backend API Docs: http://localhost:8000/docs
   - Backend Health: http://localhost:8000/health

### Test Scenarios

#### 1. Backend Health Check

**Objective**: Verify backend is running and database is accessible.

**Steps**:
1. Navigate to http://localhost:8000/health
2. Verify response: `{"status": "healthy"}`
3. Navigate to http://localhost:8000/docs
4. Verify Swagger UI loads with all endpoints

**Expected Result**: ✅ Both endpoints respond successfully

---

#### 2. Portfolio Creation

**Objective**: Create a new portfolio.

**Steps**:
1. Navigate to http://localhost:5173
2. Look for "Create Portfolio" button or form
3. Enter portfolio name: "Test Portfolio [timestamp]"
4. Click Submit/Create
5. Verify portfolio appears in list

**Expected Results**:
- ✅ Form submits without errors
- ✅ Portfolio appears in the UI
- ✅ Portfolio shows initial cash balance

---

#### 3. Deposit Funds

**Objective**: Add cash to portfolio.

**Steps**:
1. Select/open the portfolio created in Test 2
2. Click "Deposit" or similar button
3. Enter amount: `10000`
4. Submit the deposit
5. Verify balance updates

**Expected Results**:
- ✅ Deposit form accepts amount
- ✅ Cash balance updates to $10,000.00
- ✅ Transaction appears in history as "DEPOSIT"

---

#### 4. Buy Stock

**Objective**: Purchase shares of a stock.

**Steps**:
1. From portfolio view, click "Buy" or "Trade"
2. Enter symbol: `AAPL`
3. Enter shares: `10`
4. Submit the purchase
5. Wait for price fetch (may take 1-2 seconds)
6. Verify stock appears in holdings

**Expected Results**:
- ✅ Buy form accepts symbol and quantity
- ✅ Current price is fetched from Alpha Vantage
- ✅ Stock appears in holdings with symbol, shares, price, cost basis, P&L
- ✅ Cash balance decreases by (price × shares)
- ✅ Transaction appears in history as "BUY"

---

#### 5. Portfolio Valuation

**Objective**: Verify real-time portfolio valuation displays correctly.

**Steps**:
1. View the portfolio with holdings
2. Verify the following data displays:
   - Total portfolio value
   - Cash balance
   - Stock holdings value
   - Individual stock prices (current)
   - P&L for each holding
3. Note the timestamp/age of price data

**Expected Results**:
- ✅ Portfolio shows total value = cash + (shares × current price)
- ✅ Each holding shows current price, shares, value, P&L, change indicator
- ✅ Price data is fresh (within 15 minutes) or labeled as stale

---

#### 6. Sell Stock

**Objective**: Sell shares of a stock.

**Steps**:
1. From portfolio with AAPL holdings, click "Sell"
2. Enter symbol: `AAPL`
3. Enter shares: `5`
4. Submit the sale
5. Verify holdings and balance update

**Expected Results**:
- ✅ Sell form accepts symbol and quantity
- ✅ Holdings update: AAPL now shows 5 shares (down from 10)
- ✅ Cash balance increases by (current price × 5)
- ✅ Transaction appears in history as "SELL"
- ✅ P&L is calculated on the sold shares

---

#### 7. Transaction History

**Objective**: Verify complete transaction ledger.

**Steps**:
1. View transaction history for the portfolio
2. Verify all transactions appear in chronological order

**Expected Results**:
- ✅ All transactions are listed (DEPOSIT, WITHDRAW, BUY, SELL)
- ✅ Each transaction shows type, amount/symbol, shares, price, timestamp
- ✅ Transactions are immutable (no edit/delete buttons)
- ✅ Balance after each transaction is correct

---

#### 8. Withdraw Funds

**Objective**: Remove cash from portfolio.

**Steps**:
1. From portfolio view, click "Withdraw"
2. Enter amount: `1000`
3. Submit the withdrawal
4. Verify balance updates

**Expected Results**:
- ✅ Withdrawal form accepts amount
- ✅ Cash balance decreases by $1,000.00
- ✅ Transaction appears in history as "WITHDRAW"
- ✅ Cannot withdraw more than available cash (validation error)

---

#### 9. Price Caching

**Objective**: Verify 3-tier caching works correctly.

**Steps**:
1. Buy a stock (e.g., MSFT) - price fetched from API
2. Refresh the page - price should come from Redis (< 100ms)
3. Wait for Redis to expire (or clear: `docker exec -it zebu-redis redis-cli FLUSHALL`)
4. Refresh again - price should come from PostgreSQL cache
5. Wait for PostgreSQL cache to expire or clear it
6. Refresh again - price should be re-fetched from API

**Expected Results**:
- ✅ First fetch: ~1-2 seconds (API call)
- ✅ Subsequent fetches within 15 min: < 100ms (Redis)
- ✅ After Redis expiry: < 500ms (PostgreSQL)
- ✅ After all cache expiry: ~1-2 seconds (API refetch)
- ✅ Price timestamp/age is displayed correctly

---

#### 10. Error Handling

**Objective**: Verify graceful degradation and error handling.

**Steps**:
1. Try to buy invalid symbol: `INVALID123`
2. Try to buy with insufficient funds
3. Try to sell more shares than owned
4. Try to withdraw more cash than available
5. Stop Redis: `docker stop zebu-redis` and try to view prices
6. Stop backend and observe frontend behavior

**Expected Results**:
- ✅ Invalid symbol: Clear error message
- ✅ Insufficient funds: Clear error, transaction prevented
- ✅ Oversell: Clear error, transaction prevented
- ✅ Over-withdraw: Clear error, transaction prevented
- ✅ Redis down: Prices still work (falls back to PostgreSQL/API)
- ✅ Backend down: Frontend shows connection error, not crash

---

### Checklist Summary

Use this checklist for quick validation:

- [ ] Backend health check passes
- [ ] Can create portfolio
- [ ] Can deposit funds
- [ ] Can buy stock with real price
- [ ] Portfolio valuation displays correctly
- [ ] Can sell stock
- [ ] Transaction history is complete and accurate
- [ ] Can withdraw funds
- [ ] Price caching works (3-tier)
- [ ] Error handling is graceful

---

### Troubleshooting

**Backend not responding**:
```bash
lsof -i :8000  # Check what's on port 8000
kill -9 <PID>  # Kill if needed
cd backend && task dev:backend  # Restart
```

**Frontend not loading**:
```bash
lsof -i :5173  # Check port
cd frontend && npm run dev  # Restart
```

**Database issues**:
```bash
task docker:down
task docker:up
cd backend && task dev:backend  # Restart to recreate tables
```

**Redis issues**:
```bash
docker exec -it zebu-redis redis-cli PING  # Should return PONG
docker exec -it zebu-redis redis-cli FLUSHALL  # Clear cache if needed
```

---

## Playwright E2E Testing

**Purpose**: Interactive browser automation for testing full workflows.

**Last Updated**: January 1, 2026

### Prerequisites

1. **MCP Server Configured**: Playwright MCP server in `.vscode/mcp.json`
2. **Services Running**: Backend, frontend, PostgreSQL, Redis
3. **Environment Variables**: Backend has access to `.env` file

### Setup Steps

#### Start Required Services

**Option A: Using Taskfile (Recommended)**

```bash
# Start Docker services
task docker:up

# Start backend (terminal 1)
task dev:backend

# Start frontend (terminal 2)
task dev:frontend
```

**Option B: Background Processes (for Automated Testing)**

```bash
# Ensure temp directory exists (in .gitignore)
mkdir -p temp

# Start backend in background
cd backend && uv run uvicorn src.main:app --reload > ../temp/backend.log 2>&1 &
echo $! > ../temp/backend.pid

# Start frontend in background
cd frontend && npm run dev > ../temp/frontend.log 2>&1 &
echo $! > ../temp/frontend.pid

# Wait for services to be ready
sleep 5
curl http://localhost:8000/health  # Should return {"status":"healthy"}
curl -I http://localhost:5173/      # Should return HTTP 200
```

**Cleanup after testing**:
```bash
# Stop services using saved PIDs
kill $(cat temp/backend.pid) 2>/dev/null || true
kill $(cat temp/frontend.pid) 2>/dev/null || true

# Remove PID files
rm -f temp/backend.pid temp/frontend.pid
```

**Why temp/ instead of /tmp/**:
- No additional permissions needed
- Automatically excluded via .gitignore
- Easier to access logs for debugging
- PID files stay with project context

### Playwright Tools Available

Check if tools are accessible (prefixed with `mcp_microsoft_pla_browser_*`):
- `browser_navigate` - Navigate to URLs
- `browser_click` - Click elements
- `browser_type` - Fill in forms
- `browser_snapshot` - Capture page state
- `browser_console_messages` - View console output
- `browser_network_requests` - Monitor network calls

### Testing Workflow

#### Step 1: Navigate to Application

```typescript
mcp_microsoft_pla_browser_navigate({
  url: "http://localhost:5173"
})
```

#### Step 2: Take Initial Snapshot

```typescript
mcp_microsoft_pla_browser_snapshot()
```

Review page structure to understand available elements and their refs.

#### Step 3: Test Portfolio Creation

```typescript
// Click create portfolio button
mcp_microsoft_pla_browser_click({
  element: "Create Portfolio button",
  ref: "e15"  // Use actual ref from snapshot
})

// Fill portfolio name
mcp_microsoft_pla_browser_type({
  element: "Portfolio Name textbox",
  ref: "e22",
  text: "Test Portfolio 2026"
})

// Submit form
mcp_microsoft_pla_browser_click({
  element: "Create Portfolio button",
  ref: "e32"
})
```

#### Step 4: Test Trade Execution

**Note**: Use IBM ticker (demo API key only supports IBM)

```typescript
// Navigate to trade page
mcp_microsoft_pla_browser_click({
  element: "Trade Stocks link",
  ref: "e75"
})

// Fill trade form with IBM ticker
mcp_microsoft_pla_browser_type({
  element: "Symbol textbox",
  ref: "e130",
  text: "IBM"  // Must use IBM for demo API key
})

mcp_microsoft_pla_browser_type({
  element: "Quantity spinbutton",
  ref: "e133",
  text: "5"
})

// Execute trade
mcp_microsoft_pla_browser_click({
  element: "Execute Buy Order button",
  ref: "e138"
})
```

#### Step 5: Verify Results

Check console for errors:
```typescript
mcp_microsoft_pla_browser_console_messages()
```

Check network requests:
```typescript
mcp_microsoft_pla_browser_network_requests()
```

Take final snapshot:
```typescript
mcp_microsoft_pla_browser_snapshot()
```

### Common Issues

**"Ticker not found" Error**: The Alpha Vantage `demo` API key only supports IBM ticker. Use `IBM` instead of `AAPL`.

**Dialog/Alert Handling**: Handle explicitly:
```typescript
mcp_microsoft_pla_browser_handle_dialog({
  accept: true
})
```

**Element Reference Not Found**:
1. Take a fresh snapshot to get current refs
2. Element refs change when page updates
3. Use descriptive element names

### Best Practices

1. **Always Take Snapshots First** - Before interacting with elements
2. **Check Console and Network** - After critical operations
3. **Handle Asynchronous Updates** - Take new snapshot after state changes
4. **Use Known-Good Tickers** - IBM ticker only for demo API key
5. **Monitor Rate Limits** - Alpha Vantage free tier: 5 calls/min, 500/day

---

## Playwright MCP Usage

**Purpose**: Detailed guide for using Playwright MCP tools in the Zebu project.

### Prerequisites

1. Docker services running: `task docker:up:all`
2. Frontend accessible: http://localhost:5173
3. Backend accessible: http://localhost:8000

### Authentication

**Test User Credentials**:
- Email: `orchestrator+clerk_test@papertrade.dev`
- Password: `test-clerk-password`
- 2FA Code: `424242` (test account uses fixed code)

**Sign-In Flow**:
1. Navigate to http://localhost:5173
2. Enter email in "Email address" field
3. Click "Continue"
4. On password page, enter password
5. Click "Continue"
6. If 2FA prompted, enter "424242"
7. Wait for redirect to /dashboard

### Common Operations

**Taking Screenshots**:
```typescript
mcp_microsoft_pla_browser_take_screenshot({
  filename: "temp/my_screenshot.png",
  type: "png"
})
```

For full page:
```typescript
mcp_microsoft_pla_browser_take_screenshot({
  filename: "temp/full_page.png",
  type: "png",
  fullPage: true
})
```

**Getting Page Snapshot** (Accessibility Tree):
```typescript
mcp_microsoft_pla_browser_snapshot()
```

Returns YAML representation with element refs (e.g., `ref=e123`)

**Checking Network Requests**:
```typescript
mcp_microsoft_pla_browser_network_requests({
  includeStatic: false
})
```

**Getting Console Messages**:
```typescript
mcp_microsoft_pla_browser_console_messages({
  level: "error"  // or "warning", "info", "debug"
})
```

### Debugging React Components

**Inspecting Component Props via React Fiber**:
```javascript
async (page) => {
  const result = await page.evaluate(() => {
    function findReactFiber(dom) {
      const key = Object.keys(dom).find(key =>
        key.startsWith('__reactFiber$') ||
        key.startsWith('__reactInternalInstance$')
      );
      return key ? dom[key] : null;
    }
    
    const element = document.querySelector('.my-component');
    const fiber = findReactFiber(element);
    
    // Walk up fiber tree
    let current = fiber;
    for (let i = 0; i < 20 && current; i++) {
      if (current.memoizedProps?.data) {
        return current.memoizedProps.data;
      }
      current = current.return;
    }
    return null;
  });
  return JSON.stringify(result, null, 2);
}
```

### Common Patterns

**Wait for Navigation**:
```javascript
await page.waitForURL('**/dashboard**', { timeout: 15000 });
```

**Wait for Element**:
```javascript
await page.waitForSelector('[data-testid="portfolio-card"]');
```

**Click with Exact Match**:
```javascript
await page.getByRole('button', { name: 'Continue', exact: true }).click();
```

### Troubleshooting

- **"Password compromised" Error**: Use test password `test-clerk-password`
- **2FA Prompt**: Use TOTP code `424242`
- **Browser Not Installed**: Run `mcp_microsoft_pla_browser_install`
- **Element Not Found**: Take snapshot first, find correct `ref` value
- **Timeout Errors**: Increase timeout, check Docker services

### Best Practices

1. Always get a snapshot first before interacting
2. Use `ref` values from snapshots rather than guessing selectors
3. Save screenshots to `temp/` directory (gitignored)
4. Check network requests when debugging API issues
5. Close browser when done: `mcp_microsoft_pla_browser_close`

---

## QA Validation Workflow

**Purpose**: Guide orchestrator through comprehensive E2E quality assurance testing.

**Last Updated**: January 2, 2026

### When to Run QA Validation

**Regular Cadence**:
- Weekly routine quality maintenance
- Pre-release before any production deployment
- Post-integration after merging 3+ significant PRs

**Event-Triggered**:
- After major refactoring or architecture changes
- When multiple features merged in short timespan
- After critical bug fixes (regression testing)
- Before demonstrating to stakeholders

**Signs QA is Needed**:
- Multiple recent PRs affecting same areas
- Unclear integration status between features
- Long time since last comprehensive test
- New deployment environment validation

### Prerequisites

Before initiating QA validation:
1. ✅ All services can start successfully
2. ✅ Recent changes merged to main branch
3. ✅ No known critical blockers in current build
4. ✅ Playwright MCP tools available
5. ✅ Database migrations up to date

### Procedure

#### Step 1: Assess Current State

Check recent activity:

```bash
# Recent merges
git log --oneline --since="7 days ago" | head -20

# Open PRs
gh pr list --state open

# Known issues
cat BACKLOG.md | grep -A 3 "Critical\|High Priority"
```

**Decision Point**:
- Critical blockers exist → Fix them first
- Environment unstable → Stabilize before QA
- Otherwise → Proceed to Step 2

#### Step 2: Prepare QA Task

Reusable template: `agent_tasks/reusable/e2e_qa_validation.md`

**Option A: Use Template Directly**:
```bash
gh agent-task create --custom-agent qa -F agent_tasks/reusable/e2e_qa_validation.md
```

**Option B: Create Customized Task** (specific focus):

```bash
cat > agent_tasks/042_qa-validation-post-pr-merges.md << 'EOF'
# QA Validation - Post PR Merges #47-49

**Priority**: High
**Agent**: qa
**Context**: After merging Docker (#47), $NaN fixes (#48), SQLAlchemy (#49)

## Objective

Execute comprehensive E2E QA testing focusing on:
1. Docker containerization doesn't break functionality
2. Price display fallbacks working correctly
3. No regressions from SQLAlchemy migration

## Instructions

Follow standard QA: `agent_tasks/reusable/e2e_qa_validation.md`

**Additional Focus Areas**:
- Verify price fallbacks show asterisk and tooltip
- Test rate limiting scenarios (503 handling)
- Check for database-related errors

Report all findings in standard format.
EOF

gh agent-task create --custom-agent qa -F agent_tasks/042_qa-validation-post-pr-merges.md
```

#### Step 3: Monitor QA Execution

The QA agent will:
1. Start backend and frontend services
2. Execute all test scenarios via Playwright
3. Document findings in `agent_tasks/progress/`
4. Create follow-up tasks for critical issues
5. Clean up services

**Typical Duration**: 30-45 minutes

#### Step 4: Review QA Report

```bash
# Find latest QA report
ls -lt agent_tasks/progress/ | grep qa | head -1

# Read report
cat agent_tasks/progress/YYYY-MM-DD_HH-MM-SS_e2e-qa-report.md
```

**Look for**:
- Summary table with pass/fail/warning counts
- Severity assessment of failures
- Evidence (screenshots, logs, console errors)
- Recommended action items

#### Step 5: Triage Findings

**Critical Issues** (Application Unusable):
- Action: Stop all work, create P0 task immediately
- Timeline: Fix within hours

**High Issues** (Major Feature Impaired):
- Action: Create high-priority task, address before next release
- Timeline: Fix within 1-2 days

**Medium Issues** (UX Affected):
- Action: Add to backlog or create task if simple
- Timeline: Fix in next sprint

**Low Issues** (Cosmetic):
- Action: Add to BACKLOG.md
- Timeline: When convenient

#### Step 6: Create Follow-up Tasks

For each critical/high issue:

```bash
# Check tasks created by QA agent
ls -lt agent_tasks/ | head -10

# Assign to appropriate agent
gh agent-task create --custom-agent backend-swe -F agent_tasks/043_fix-issue.md
```

#### Step 7: Update Project Tracking

Document the QA session in PROGRESS.md:

```markdown
## Quality Assurance - [DATE]

**QA Report**: agent_tasks/progress/YYYY-MM-DD_HH-MM-SS_e2e-qa-report.md

**Summary**: Comprehensive E2E testing after PRs #47, #48, #49

**Results**:
- 7 scenarios tested
- 5 passed, 1 failed (critical), 1 warning (medium)
- Created Task #043 (trading 503 error) - P0
- Created Task #044 (improve error messages) - Medium

**Next Steps**:
- Fix critical trading issue (Task #043)
- Rerun QA after fix to verify
```

#### Step 8: Schedule Next QA

Determine timing:
- **After Critical Fix**: Immediately (regression test)
- **Regular Cadence**: Weekly or bi-weekly
- **Before Release**: Always

### Common Issues

**QA Agent Can't Start Services**:
```bash
# Check Docker
docker ps

# Check logs
tail -100 temp/backend.log
tail -100 temp/frontend.log

# Try manually
task dev:backend
task dev:frontend
```

**Playwright Tools Not Available**:
- Check `.vscode/mcp.json` for Playwright MCP
- Restart VS Code if needed
- Run `mcp_microsoft_pla_browser_install`

**All Tests Timing Out**:
```bash
curl http://localhost:8000/health
curl http://localhost:5173/
```

**Rate Limiting Blocking Tests**:
- Expected with Alpha Vantage free tier (5 calls/min)
- Wait between tests
- Use known cached tickers (IBM)
- Note in QA report as expected behavior

### Best Practices

1. **Don't Over-Test** - Focus on critical paths
2. **Context is Key** - Tell QA agent what changed recently
3. **Trust but Verify** - Verify severity assessment
4. **Regression Testing** - After fixing critical bugs, rerun QA
5. **Continuous Improvement** - Update procedures when needed

### Metrics to Track

| Metric | Target | Purpose |
|--------|--------|---------|
| Pass Rate | > 90% | Overall quality health |
| Critical Failures | 0 | Release readiness |
| Time to Fix Critical | < 24 hrs | Response capability |
| Regression Rate | < 5% | Code stability |
| QA Session Duration | 30-45 min | Efficiency |

---

## Automated E2E Scripts

### Quick E2E API Test

**File**: `scripts/quick_e2e_test.sh`

**Purpose**: Automated API testing for rapid validation.

**Usage**:
```bash
# Start backend first
task dev:backend

# Run script
./scripts/quick_e2e_test.sh
```

**Tests**:
1. Create Portfolio
2. Get Portfolio
3. Buy Stock (AAPL - 10 shares)
4. Get Holdings
5. Get Transaction History
6. Sell Stock (AAPL - 5 shares)
7. Withdraw Funds ($1000)
8. Error Handling (Invalid Symbol)
9. Final Portfolio State

**Output**: JSON responses with ✅/❌ status indicators

---

## Related Documentation

- [Testing Guide](./README.md) - General testing philosophy and running tests
- [Testing Standards](./standards.md) - Best practices, conventions, accessibility

---

**Last Updated**: January 26, 2026 (Consolidated from procedures and reference docs)
