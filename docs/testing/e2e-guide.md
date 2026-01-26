# End-to-End Testing Guide

Complete guide for E2E testing in Zebu: manual testing, Playwright automation, and QA workflows.

## Quick Start

```bash
# Start all services
task docker:build && task docker:up:all

# Or start services individually
task docker:up              # PostgreSQL, Redis only
task dev:backend            # Backend server
task dev:frontend           # Frontend dev server
```

**Service URLs:**
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

---

## Manual Testing Checklist

Quick validation checklist for releases or after major changes:

### Core Workflows

1. **Backend Health** → Verify http://localhost:8000/health returns `{"status": "healthy"}`
2. **Portfolio Creation** → Create portfolio with initial deposit
3. **Buy Stock** → Purchase shares (use AAPL or IBM)
4. **Portfolio Valuation** → Verify total value = cash + holdings
5. **Sell Stock** → Sell partial position, verify P&L
6. **Transaction History** → All transactions logged correctly
7. **Price Caching** → Verify 3-tier cache (Redis → PostgreSQL → API)
8. **Error Handling** → Invalid symbols, insufficient funds show clear errors

### Test Data
- **Valid Symbols**: AAPL, IBM (IBM required for demo API key in CI)
- **Test Portfolios**: Use timestamp in name: "Test Portfolio 2026-01-26"
- **Initial Deposit**: $10,000 typical test amount

### Troubleshooting

```bash
# Check services
task health:docker
task status

# View logs
task docker:logs
task docker:logs:backend

# Restart services
task docker:restart
task docker:clean  # WARNING: Deletes data
```

---

## Playwright E2E Testing

### Setup

1. **Install Playwright** (if needed):
   ```bash
   cd frontend
   npx playwright install
   ```

2. **Start Services**:
   ```bash
   task docker:build && task docker:up:all
   ```

3. **Run Tests**:
   ```bash
   # Headless
   task test:e2e

   # With browser UI
   npm run test:e2e:headed

   # Interactive mode
   npm run test:e2e:ui

   # Specific test
   npx playwright test tests/e2e/trading.spec.ts
   ```

### Using Playwright MCP (for AI Agents)

Playwright MCP server enables browser automation via Model Context Protocol.

**Prerequisites:**
- MCP configured in `.vscode/mcp.json`
- Services running: `task docker:up:all`

**Common Operations:**

```typescript
// Navigate
mcp_microsoft_pla_browser_navigate({ url: "http://localhost:5173" })

// Take snapshot (get element refs)
mcp_microsoft_pla_browser_snapshot()

// Interact with elements
mcp_microsoft_pla_browser_click({ element: "Create Portfolio button", ref: "e15" })
mcp_microsoft_pla_browser_type({ element: "Portfolio Name", ref: "e22", text: "Test" })

// Verify
mcp_microsoft_pla_browser_console_messages()
mcp_microsoft_pla_browser_network_requests()
```

**Test User Credentials:**
- Email: `orchestrator+clerk_test@papertrade.dev`
- Password: `test-clerk-password`
- 2FA: `424242`

**Tips:**
- Always take snapshot before interacting (gets current element refs)
- Use IBM ticker for demo API key compatibility
- Check console/network after critical operations
- Element refs change after page updates

---

## QA Validation Workflow

For orchestrators running comprehensive QA sessions.

### When to Run QA

**Regular:**
- Weekly quality checks
- Before releases
- After merging 3+ significant PRs

**Event-Triggered:**
- Major refactoring
- Critical bug fixes
- User-reported issues

### QA Procedure

1. **Assess State**
   ```bash
   git log --oneline --since="7 days ago" | head -20
   gh pr list --state open
   ```

2. **Run QA Task**
   ```bash
   # Use reusable template
   gh agent-task create --custom-agent qa \
     -F agent_tasks/reusable/e2e_qa_validation.md

   # Or create custom task focusing on recent changes
   ```

3. **Monitor** (30-45 min typical duration)

4. **Review Report**
   ```bash
   ls -lt agent_tasks/progress/ | grep qa | head -1
   cat agent_tasks/progress/YYYY-MM-DD_HH-MM-SS_e2e-qa-report.md
   ```

5. **Triage Findings**
   - **Critical** (P0): Stop all work, fix immediately
   - **High** (P1): Fix before next release
   - **Medium**: Add to backlog or next sprint
   - **Low**: Add to BACKLOG.md

6. **Create Follow-up Tasks** for critical/high issues

7. **Update PROGRESS.md** with QA summary

### Common Issues

| Issue | Solution |
|-------|----------|
| Services won't start | `task docker:clean && task docker:build && task docker:up:all` |
| Playwright tools unavailable | Check `.vscode/mcp.json`, restart VS Code |
| Tests timeout | Verify services: `curl http://localhost:8000/health` |
| Rate limiting (503) | Expected with free tier (5 calls/min), use cached tickers |

### QA Metrics

| Metric | Target |
|--------|--------|
| Pass Rate | > 90% |
| Critical Failures | 0 |
| Time to Fix Critical | < 24 hrs |
| QA Duration | 30-45 min |

---

## Automated E2E Scripts

### Quick API Test

**Purpose**: Rapid API validation via curl

```bash
# Start backend
task dev:backend

# Run script
./scripts/quick_e2e_test.sh
```

**Tests**: Portfolio creation, trades (buy/sell), deposits, withdrawals, error handling

---

## Related Documentation

- [Testing Philosophy](./README.md) - General testing approach
- [Testing Standards](./standards.md) - E2E standards, conventions, accessibility

---

**Last Updated**: January 26, 2026
