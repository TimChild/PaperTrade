---
name: e2e-qa-validation
description: Comprehensive E2E QA test scenarios + report template for Zebu. Run before major releases, after multi-PR merges, or as periodic regression. Use with the qa agent.
---

# E2E QA Validation

Comprehensive QA test plan for Zebu. ~30–45 minutes per run.

## When to run

- After multiple PRs affecting core features
- Before deploying to production
- After major refactoring or architecture changes
- When user-reported issues suggest broader concerns
- Periodic (e.g., weekly)

## Setup

```bash
task docker:up:all
docker compose ps                 # verify healthy
curl -s http://localhost:8000/health
curl -sI http://localhost:5173/
```

## Test scenarios

### 1. New User Onboarding (Critical)

1. Navigate to `http://localhost:5173`
2. Verify dashboard loads
3. Click "Create Portfolio"
4. Fill form: name "QA Test [DATE]", initial deposit $10,000
5. Submit, verify portfolio appears, cash balance correct, no console errors

Failure modes: empty form, negative deposit, special characters in name.

### 2. Stock Trading (Critical)

Pre: portfolio with cash.

1. Select portfolio → Trade Stocks
2. Symbol: IBM, qty: 10, type: Buy
3. Execute, verify confirmation
4. Check holdings: IBM with 10 shares, current price
5. Verify cash balance reduced
6. Check transaction history

Failure modes: invalid ticker, zero qty, insufficient funds, rate limiting.

### 3. Portfolio Value Tracking (Critical)

Pre: portfolio with at least one position.

1. Verify summary: total value, cash, invested, gains/losses
2. Holdings table: positions, qty, prices, value
3. Charts: render without errors, no `$NaN`

Edge cases: rate-limited ticker, multiple positions, zero-value positions.

### 4. Multiple Portfolios (High)

1. Create second portfolio (different name + deposit)
2. Trade in #2
3. Switch back to #1, verify unchanged
4. Switch to #2, verify trade visible
5. Verify isolation (no data leakage)

### 5. Selling Positions (High)

Pre: portfolio with existing position.

1. Trade page → SELL
2. Enter qty < held quantity
3. Execute, verify confirmation
4. Holdings: qty reduced, cash increased
5. Transaction history: both buy and sell shown

Failure modes: sell more than owned, sell zero, sell from wrong portfolio.

### 6. Error Handling (Medium)

- Invalid ticker `NOTREAL` → clear error, no state corruption
- Rate-limit hit → graceful degradation
- Insufficient funds for $100k buy on $10k balance → validation error before API call
- Rapid-click trade button → debouncing prevents duplicates
- Browser refresh mid-workflow → state recovers

### 7. Responsive Design (Low, time-permitting)

- Resize to 375px mobile width
- Navigate key pages
- Test critical flows on mobile

## Evidence to capture per scenario

- Screenshots before/after key actions
- `browser_console_messages()`
- `browser_network_requests()`
- `browser_snapshot()` when state matters

## Severity rubric

| Severity | Meaning |
|---|---|
| Critical | Core feature broken, data-loss risk |
| High | Major feature impaired, hard workarounds |
| Medium | Partial functionality, usability impacted |
| Low | Cosmetic, minor UX |

## Report template

Save under `agent_docs/progress/YYYY-MM-DD_HH-MM-SS_e2e-qa-report.md`:

```markdown
# E2E QA Test Report — YYYY-MM-DD

**Tester**: QA Agent | **Commit**: <hash> | **Environment**: dev (local)
**Duration**: HH:MM–HH:MM

## Summary
Total: X | Passed: Y | Failed: Z | Blocked: W

## Results
| Scenario | Status | Severity | Duration | Notes |
|---|---|---|---|---|
| Onboarding | ✅ Pass | Critical | 3m | clean |
| Trading | ❌ Fail | Critical | 5m | 503 on execute |

## Detailed findings

### ❌ FAIL: Trading workflow (Critical)
**Steps**: 1. ... 2. ... 3. ...
**Expected**: trade executes successfully
**Actual**: 503 Service Unavailable
**Evidence**: console: "...", network: POST /api/.../trades → 503, screenshot ref
**Root-cause hypothesis**: Alpha Vantage rate limit
**Recommendation**: file backend-swe task — retry + cached-price fallback

## Action items
1. **Critical**: Task NNN — fix trading 503 → backend-swe
```

## Cleanup

```bash
# Stop services if started for this run only
# (otherwise leave running for the next agent / dev)
task docker:down
```

## Follow-up

For each FAIL with severity ≥ Medium, write a task spec at `agent_docs/tasks/NNN_<short_name>.md` with: priority, agent assignment, reproducible steps, expected vs actual, acceptance criteria.

## Success criteria

- All scenarios executed
- Evidence captured for each finding
- Report written to `agent_docs/progress/`
- Severity assigned to every finding
- Follow-up tasks created for Critical / High issues
- Services cleaned up
