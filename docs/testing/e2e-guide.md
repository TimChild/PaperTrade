# End-to-End Testing Guide

This comprehensive guide covers E2E testing in Zebu, including Playwright automation, MCP usage for AI agents, manual QA procedures, and QA orchestration.

## Table of Contents

- [Quick Start](#quick-start)
- [Automated E2E Testing with Playwright](#automated-e2e-testing-with-playwright)
- [Playwright MCP for AI Agents](#playwright-mcp-for-ai-agents)
- [Manual QA Testing](#manual-qa-testing)
- [API-Level E2E Testing](#api-level-e2e-testing)
- [QA Orchestration for Agents](#qa-orchestration-for-agents)

---

## Quick Start

### Prerequisites

1. **Docker services running**: `task docker:up`
2. **Backend running**: `task dev:backend` (port 8000)
3. **Frontend running**: `task dev:frontend` (port 5173)

### Run E2E Tests

```bash
# Automated Playwright tests
npm run test:e2e            # Headless
npm run test:e2e:ui         # Interactive UI mode
npm run test:e2e:headed     # See browser

# Quick API-level test
./scripts/quick_e2e_test.sh

# Full validation script
uv run --directory backend python scripts/e2e_validation.py
```

---

## Automated E2E Testing with Playwright

### Setup

#### Option A: Using Taskfile (Recommended)

```bash
# Start Docker services (PostgreSQL, Redis)
task docker:up

# Start backend (in terminal 1)
task dev:backend

# Start frontend (in terminal 2)
task dev:frontend
```

#### Option B: Background Processes (for Automated Testing)

For orchestrator agents running automated E2E tests, you can start services in the background:

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

# Logs remain in temp/ for debugging if needed
```

**Why temp/ instead of /tmp/**:
- No additional permissions needed (stays in project root)
- Automatically excluded via .gitignore
- Easier to access logs for debugging
- PID files stay with project context

### Running Playwright Tests

```bash
# Run all E2E tests
npm run test:e2e

# Run in UI mode (interactive debugging)
npm run test:e2e:ui

# Run in headed mode (see browser)
npm run test:e2e:headed

# Run specific test file
npx playwright test tests/e2e/trading.spec.ts

# Debug mode (step through test)
npx playwright test --debug

# Run single test
npx playwright test -g "should execute buy trade"
```

### Debugging E2E Tests

```bash
# Trace viewer (inspect after run)
npx playwright test --trace on
npx playwright show-trace trace.zip

# Generate trace for failures only
npx playwright test --trace on-first-retry
```

### Test Scenarios

#### Scenario 1: New User Flow

1. Navigate to dashboard (empty state)
2. Create first portfolio with initial deposit
3. Execute first trade
4. Verify holdings appear
5. Check transaction history

**Success Criteria**:
- Portfolio created successfully
- Cash balance updated correctly
- Holdings table shows position
- Transaction history shows deposit + trade

#### Scenario 2: Multiple Trades

1. Use existing portfolio
2. Execute buy for ticker A
3. Execute buy for ticker B (wait 15s to avoid rate limit)
4. Execute sell for ticker A (partial position)
5. Verify portfolio value calculations

**Success Criteria**:
- All trades execute successfully
- Cash balance tracks correctly
- Average cost basis calculated properly
- Gains/losses displayed

#### Scenario 3: Error Handling

1. Try to trade non-existent ticker (e.g., "INVALID")
2. Try to sell stock not owned
3. Try to buy with insufficient funds

**Success Criteria**:
- Appropriate error messages shown
- No trades executed
- Portfolio state unchanged

### Important: Use IBM Ticker for Tests

**CRITICAL**: E2E tests must use **IBM ticker only**.

The Alpha Vantage `demo` API key (used in CI) only supports IBM:
- **IBM**: ✅ Works with demo key
- **AAPL**: ❌ Returns "demo key is for demo purposes only" error
- Other tickers: ❌ Not supported with demo key

When writing E2E tests, always use `IBM` for ticker symbols to ensure CI compatibility.

### Common Issues

#### Issue: "Ticker not found" Error

**Symptom**: Trade fails with 404 error saying "Ticker not found: AAPL"

**Cause**: The Alpha Vantage `demo` API key only supports IBM ticker.

**Resolution**: Use `IBM` ticker instead of `AAPL` in E2E tests.

#### Issue: Element Reference Not Found

**Symptom**: Click or type action fails with "element not found"

**Solution**:
1. Take a fresh snapshot to get current refs
2. Element refs change when page updates
3. Use descriptive element names to help tool find the right element

### Best Practices

1. **Keep E2E tests focused** - Test one user journey per test
2. **Use proper waits** - `waitForLoadState('networkidle')`, `waitForURL()`
3. **Clean up after tests** - Delete test data if possible
4. **Run serially for Clerk** - Parallel Clerk auth can conflict
5. **Use environment variables** - Don't hardcode credentials
6. **Retry on CI** - E2E tests can be flaky, retry 2x on CI
7. **Meaningful assertions** - Test user-visible outcomes, not implementation

---

## Playwright MCP for AI Agents

The Playwright MCP (Model Context Protocol) server allows AI agents to control a browser programmatically for manual testing, UI debugging, and documentation.

### Authentication

#### Test User Credentials
- **Email**: `orchestrator+clerk_test@papertrade.dev`
- **Password**: `test-clerk-password`
- **2FA Code** (if prompted): `424242` (test account uses fixed code)

#### Sign-In Flow

Clerk uses a two-step sign-in process:

```
1. Navigate to http://localhost:5173
2. Enter email in "Email address" field
3. Click "Continue"
4. On password page, enter password
5. Click "Continue"
6. If 2FA prompted, enter "424242"
7. Wait for redirect to /dashboard
```

**Example using Playwright MCP:**
```
1. browser_navigate: url="http://localhost:5173"
2. browser_type: ref=<email_field>, text="orchestrator+clerk_test@papertrade.dev"
3. browser_click: ref=<continue_button>
4. Wait for password page, then:
5. browser_type: ref=<password_field>, text="test-clerk-password"
6. browser_click: ref=<continue_button>
7. If 2FA page appears:
   browser_type: ref=<totp_field>, text="424242"
   browser_click: ref=<continue_button>
```

### Common MCP Operations

#### Taking Screenshots
```
browser_take_screenshot:
  filename: "temp/my_screenshot.png"
  type: "png"
```

For full page screenshots:
```
browser_take_screenshot:
  filename: "temp/full_page.png"
  type: "png"
  fullPage: true
```

#### Getting Page Snapshot (Accessibility Tree)
More useful than screenshots for understanding page structure:
```
browser_snapshot
```

Returns a YAML representation of the page with element references (e.g., `ref=e123`) that can be used for clicking, typing, etc.

#### Checking Network Requests
```
browser_network_requests
```

Returns all API calls made by the page, useful for debugging backend integration.

#### Getting Console Messages
```
browser_console_messages
```

### Troubleshooting MCP

#### Browser Not Installed
Run: `browser_install`

#### Element Not Found
1. Take a snapshot first: `browser_snapshot`
2. Find the correct `ref` value
3. Use that ref in subsequent operations

#### Timeout Errors
- Increase timeout in `waitForURL` or similar calls
- Check if Docker services are running: `task docker:ps`
- Check backend logs: `task docker:logs:backend`

### MCP Best Practices

1. **Always get a snapshot first** before interacting with elements
2. **Use `ref` values** from snapshots rather than guessing selectors
3. **Save screenshots to `temp/`** directory (gitignored)
4. **Check network requests** when debugging API integration issues
5. **Close browser when done**: `browser_close`

---

## Manual QA Testing

This section outlines manual testing procedures for validating Zebu's core functionality.

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
1. Navigate to http://localhost:5173 (or 5174)
2. Look for "Create Portfolio" button or form
3. Enter portfolio name: "Test Portfolio [timestamp]"
4. Click Submit/Create
5. Verify portfolio appears in list

**Expected Results**:
- ✅ Form submits without errors
- ✅ Portfolio appears in the UI
- ✅ Portfolio shows initial cash balance of $0.00

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
2. Enter symbol: `IBM` (use IBM for test API key)
3. Enter shares: `10`
4. Submit the purchase
5. Wait for price fetch (may take 1-2 seconds)
6. Verify stock appears in holdings

**Expected Results**:
- ✅ Buy form accepts symbol and quantity
- ✅ Current price is fetched from Alpha Vantage
- ✅ Stock appears in holdings with symbol, shares, price, cost basis, total value, P&L
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
- ✅ Each holding shows current price with timestamp, shares, total value, P&L, price change indicator
- ✅ Price data is fresh (within last 15 minutes for market hours)

---

#### 6. Sell Stock

**Objective**: Sell shares of a stock.

**Steps**:
1. From portfolio with IBM holdings, click "Sell"
2. Enter symbol: `IBM`
3. Enter shares: `5`
4. Submit the sale
5. Verify holdings and balance update

**Expected Results**:
- ✅ Sell form accepts symbol and quantity
- ✅ Holdings update: IBM now shows 5 shares (down from 10)
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
- ✅ All transactions are listed (DEPOSIT, BUY, SELL)
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
1. Buy a stock (e.g., IBM) - price fetched from API
2. Refresh the page - price should come from Redis (< 100ms)
3. Wait for Redis to expire or clear Redis: `docker exec -it zebu-redis redis-cli FLUSHALL`
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

### Quick Validation Checklist

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

### Troubleshooting

#### Backend not responding
```bash
lsof -i :8000  # Check what's on port 8000
kill -9 <PID>  # Kill if needed
cd backend && task dev:backend  # Restart
```

#### Frontend not loading
```bash
lsof -i :5173  # Check port
cd frontend && npm run dev  # Restart
```

#### Database issues
```bash
task docker:down
task docker:up
cd backend && task dev:backend  # Restart to recreate tables
```

#### Redis issues
```bash
docker exec -it zebu-redis redis-cli PING  # Should return PONG
docker exec -it zebu-redis redis-cli FLUSHALL  # Clear cache if needed
```

---

## API-Level E2E Testing

For quick API-level validation, use the `quick_e2e_test.sh` script:

```bash
# Start services first
task docker:up
task dev:backend

# Run API tests
./scripts/quick_e2e_test.sh
```

This script tests:
1. ✅ Create Portfolio
2. ✅ Get Portfolio
3. ✅ Buy Stock (IBM - 10 shares)
4. ✅ Get Holdings
5. ✅ Get Transaction History
6. ✅ Sell Stock (IBM - 5 shares)
7. ✅ Withdraw Funds ($1000)
8. ✅ Error Handling (Invalid Symbol)
9. ✅ Final Portfolio State

### Manual API Testing

```bash
# Create portfolio
curl -X POST http://localhost:8000/api/v1/portfolios \
  -H "Content-Type: application/json" \
  -H "X-User-Id: 00000000-0000-0000-0000-000000000001" \
  -d '{"name": "Test", "initial_deposit": 10000.00, "currency": "USD"}'

# Get balance (replace {id} with portfolio_id from response)
curl http://localhost:8000/api/v1/portfolios/{id}/balance \
  -H "X-User-Id: 00000000-0000-0000-0000-000000000001"
```

---

## QA Orchestration for Agents

This section guides orchestrator agents through initiating comprehensive QA validation sessions.

### When to Run QA Validation

#### Regular Cadence
- **Weekly**: As part of routine quality maintenance
- **Pre-Release**: Before any production deployment
- **Post-Integration**: After merging 3+ significant PRs

#### Event-Triggered
- After major refactoring or architecture changes
- When multiple features merged in short timespan
- After critical bug fixes (regression testing)
- When user-reported issues suggest broader problems
- Before demonstrating to stakeholders

### QA Procedure for Orchestrators

#### Step 1: Assess Current State

Check recent activity and open PRs:

```bash
# Check what's been merged recently
git log --oneline --since="7 days ago" | head -20

# Check open PRs
gh pr list --state open

# Check for known issues
cat BACKLOG.md | grep -A 3 "Critical\|High Priority"
```

**Decision Point**:
- If critical blockers exist → Fix them first
- If environment unstable → Stabilize before QA
- Otherwise → Proceed to Step 2

#### Step 2: Prepare QA Task

The reusable QA task template is at: `agent_tasks/reusable/e2e_qa_validation.md`

**Option A: Use Template Directly** (simple QA run)
```bash
gh agent-task create --custom-agent qa -F agent_tasks/reusable/e2e_qa_validation.md
```

**Option B: Create Customized Task** (specific focus areas)

Create a specific task file referencing the reusable template with additional context.

#### Step 3: Monitor QA Execution

The QA agent will:
1. Start backend and frontend services
2. Execute all test scenarios via Playwright
3. Document findings in `agent_tasks/progress/`
4. Create follow-up tasks for critical issues
5. Clean up services

**Typical Duration**: 30-45 minutes

**What to Watch For**:
- Agent getting stuck (may need help with Playwright refs)
- Rate limiting from Alpha Vantage (expected, should handle gracefully)
- Service startup failures (database/Redis not running)

#### Step 4: Review QA Report

Once the QA agent completes, review the test report in `agent_tasks/progress/`:

```bash
# Find the latest QA report
ls -lt agent_tasks/progress/ | grep qa | head -1

# Read the report
cat agent_tasks/progress/YYYY-MM-DD_HH-MM-SS_e2e-qa-report.md
```

**Look for**:
- Summary table with pass/fail/warning counts
- Severity assessment of failures
- Evidence (screenshots, logs, console errors)
- Recommended action items

#### Step 5: Triage Findings

Categorize findings by severity:

| Severity | Action | Timeline |
|----------|--------|----------|
| **Critical** (app unusable) | Stop all other work, create P0 task immediately | Fix within hours |
| **High** (major feature impaired) | Create high-priority task, address before next release | Fix within 1-2 days |
| **Medium** (UX affected) | Add to backlog or create task if simple fix | Fix in next sprint |
| **Low** (cosmetic) | Add to BACKLOG.md for future improvement | When convenient |

### Common QA Issues

#### Issue: QA Agent Can't Start Services

**Debug**:
```bash
# Check Docker services
docker ps

# Check logs
tail -100 temp/backend.log
tail -100 temp/frontend.log

# Try manually
task dev:backend
task dev:frontend
```

**Resolution**: Fix environment issues before retrying QA

#### Issue: All Tests Timing Out

**Debug**:
```bash
curl http://localhost:8000/health
curl http://localhost:5173/
```

**Resolution**: Services not running, check startup logs

#### Issue: Rate Limiting Blocking Tests

**Expected**: This is normal with Alpha Vantage free tier (5 calls/min)

**Resolution**:
- Wait between tests
- Use known cached tickers (IBM)
- Note in QA report as expected behavior

### QA Best Practices

1. **Don't Over-Test** - Focus on critical user paths
2. **Context is Key** - Tell QA agent what changed recently
3. **Trust but Verify** - Verify severity assessment
4. **Regression Testing** - After fixing critical bugs, rerun QA
5. **Continuous Improvement** - Update template if scenarios missing

---

## Related Documentation

- [Testing Standards](./standards.md) - Best practices, naming conventions, accessibility
- [Testing README](./README.md) - General testing philosophy and quick reference
- [Playwright Docs](https://playwright.dev/) - Playwright API reference
- [Alpha Vantage API Docs](https://www.alphavantage.co/documentation/)
