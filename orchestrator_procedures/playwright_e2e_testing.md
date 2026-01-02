# Playwright E2E Testing Procedure

**Last Updated**: January 1, 2026

## Overview

This procedure guides the orchestrator through using the Playwright MCP server to test the full application stack interactively. This is useful for verifying feature integration, catching UI bugs, and validating complete user workflows.

## Prerequisites

1. **MCP Server Configured**: Playwright MCP server must be enabled in `.vscode/mcp.json`
2. **Services Running**: Backend, frontend, PostgreSQL, and Redis all running
3. **Environment Variables**: Backend must have access to `.env` file (via symlink or Docker)

## Setup Steps

### 1. Start Required Services

```bash
# Start Docker services (PostgreSQL, Redis)
task docker:up

# Start backend (in terminal 1)
task dev:backend

# Start frontend (in terminal 2)
task dev:frontend
```

**Verify services are running**:
```bash
curl http://localhost:8000/health  # Should return {"status":"healthy"}
curl -I http://localhost:5173/      # Should return HTTP 200
```

### 2. Verify Playwright MCP Tools Available

Check if Playwright tools are accessible by looking for tools prefixed with `mcp_microsoft_pla_browser_*`:
- `browser_navigate` - Navigate to URLs
- `browser_click` - Click elements
- `browser_type` - Fill in forms
- `browser_snapshot` - Capture page state
- `browser_console_messages` - View console output
- `browser_network_requests` - Monitor network calls

**Activate navigation tools** if needed:
```
activate_browser_navigation_tools()
```

### 3. Environment Variable Configuration

The backend requires the `.env` file to be accessible. Two approaches:

**Development (Local)**:
```bash
cd backend
ln -s ../.env .env
```

**Production (Docker)**:
- Ensure `docker-compose.yml` mounts or passes environment variables
- Variables can be set in docker-compose or loaded from root `.env`

## Testing Workflow

### Step 1: Navigate to Application

```typescript
mcp_microsoft_pla_browser_navigate({
  url: "http://localhost:5173"
})
```

This should redirect to `/dashboard` and show the portfolio dashboard.

### Step 2: Take Initial Snapshot

```typescript
mcp_microsoft_pla_browser_snapshot()
```

Review the page structure to understand available elements and their refs.

### Step 3: Test Portfolio Creation

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

// Fill initial deposit
mcp_microsoft_pla_browser_type({
  element: "Initial Deposit spinbutton",
  ref: "e28",
  text: "10000.00"
})

// Submit form
mcp_microsoft_pla_browser_click({
  element: "Create Portfolio button",
  ref: "e32"
})
```

**Expected**: Modal closes, portfolio appears in dashboard with $10,000 balance.

### Step 4: Test Trade Execution

```typescript
// Navigate to trade page
mcp_microsoft_pla_browser_click({
  element: "Trade Stocks link",
  ref: "e75"
})

// Fill trade form
mcp_microsoft_pla_browser_type({
  element: "Symbol textbox",
  ref: "e130",
  text: "IBM"
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

**Expected**: Alert shows "Buy order executed successfully!", holdings updated, cash balance reduced.

### Step 5: Verify Results

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

## Common Issues and Debugging

### Issue: "Ticker not found" Error

**Symptom**: Trade fails with 404 error saying "Ticker not found: AAPL"

**Causes**:
1. Alpha Vantage API key not configured
2. Rate limit exceeded (5 calls/min free tier)
3. Backend can't access `.env` file

**Debugging**:
```bash
# Check if .env is accessible
cd backend && cat .env | grep ALPHA_VANTAGE_API_KEY

# Test API directly
curl "https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=IBM&apikey=YOUR_KEY"

# Check backend logs for rate limit messages
# Look for: "Rate limit exceeded. No cached data available."
```

**Resolution**:
1. Ensure `backend/.env` symlink exists: `ln -s ../.env backend/.env`
2. Restart backend to pick up environment variables
3. Wait 1 minute if rate limited, or use cached ticker (IBM)

### Issue: Dialog/Alert Handling

**Symptom**: Test gets stuck when alert appears

**Solution**: Handle the dialog explicitly:
```typescript
mcp_microsoft_pla_browser_handle_dialog({
  accept: true
})
```

### Issue: Current Price Shows $NaN

**Symptom**: Holdings table and price charts display `$NaN` for prices

**Causes**:
1. No historical price data exists yet
2. Current price fetch hits rate limit
3. Frontend trying to fetch price that hasn't been cached

**Current Status**: Known issue - see task #039 for fix

### Issue: Element Reference Not Found

**Symptom**: Click or type action fails with "element not found"

**Solution**:
1. Take a fresh snapshot to get current refs
2. Element refs change when page updates
3. Use descriptive element names to help tool find the right element

## Best Practices

### 1. Always Take Snapshots First

Before interacting with elements, take a snapshot to:
- Verify page loaded correctly
- Get current element refs
- Understand page structure

### 2. Check Console and Network

After critical operations (form submits, trades), check:
- Console messages for errors
- Network requests for failed API calls
- Response codes (200, 404, 503, etc.)

### 3. Handle Asynchronous Updates

Some operations trigger re-renders:
- Take a new snapshot after state changes
- Element refs may change after updates
- Wait for network requests to complete

### 4. Use Known-Good Tickers

For testing trades, use tickers that are likely to work:
- **IBM**: Usually works (established company)
- **AAPL**: May hit rate limits if testing multiple times
- Avoid obscure tickers that might not exist in Alpha Vantage

### 5. Monitor Rate Limits

Alpha Vantage free tier: 5 calls/minute, 500/day
- First ticker fetch: Consumes 1 API call
- Subsequent requests: Served from cache (1 hour TTL)
- Plan test sequences to avoid rate limits

## Test Scenarios

### Scenario 1: New User Flow

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

### Scenario 2: Multiple Trades

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

### Scenario 3: Error Handling

1. Try to trade non-existent ticker (e.g., "INVALID")
2. Try to sell stock not owned
3. Try to buy with insufficient funds

**Success Criteria**:
- Appropriate error messages shown
- No trades executed
- Portfolio state unchanged

## Reporting Issues

When filing issues found during E2E testing:

1. **Capture Evidence**:
   - Page snapshot showing the issue
   - Console error messages
   - Network request failures
   - Element refs if relevant

2. **Document Steps**:
   - Exact sequence to reproduce
   - Initial portfolio state
   - Expected vs actual behavior

3. **Create Task File**:
   - Place in `agent_tasks/`
   - Include reproduction steps
   - Reference this procedure
   - Assign to appropriate agent (frontend-swe, backend-swe)

4. **Add to Backlog**:
   - Minor UI issues → `BACKLOG.md`
   - Critical bugs → Immediate task + PR

## Integration with CI/CD

Future enhancement: Automated Playwright tests
- Convert manual procedures to automated test scripts
- Run on PR creation
- Capture screenshots on failure
- See `orchestrator_procedures/e2e_validation.py` (WIP)

## References

- [Playwright MCP Documentation](https://github.com/microsoft/playwright-mcp)
- [Alpha Vantage API Docs](https://www.alphavantage.co/documentation/)
- [.vscode/MCP_CONFIGURATION.md](.vscode/MCP_CONFIGURATION.md) - MCP server setup
- [AGENT_ORCHESTRATION.md](../AGENT_ORCHESTRATION.md) - General orchestration guide
