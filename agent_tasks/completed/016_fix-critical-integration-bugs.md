# Task 016: Fix Critical Integration Bugs (Phase 1 Blocker)

**Created**: 2025-12-28 18:55 PST
**Priority**: P0 - CRITICAL BLOCKER (prevents Phase 1 release)
**Estimated Effort**: 3-4 hours
**Agent**: Backend-SWE (primary), Frontend-SWE (supporting)

## Objective

Fix critical integration bugs discovered during manual testing that prevent the application from being usable. These bugs passed all unit tests but fail in real-world usage, demonstrating a gap in our testing strategy.

## Context

### Discovery
During manual end-to-end testing, the user found:
1. ✅ Can navigate to application
2. ❌ Portfolio creation fails (frontend uses wrong user ID)
3. ❌ Balance endpoint crashes with AttributeError
4. ❌ Trading page is broken

### Root Cause
**Unit tests passed** but **integration failed** because:
- Tests mock dependencies, hiding field name mismatches
- No end-to-end integration tests
- Frontend and backend not tested together

See [Manual Testing Bug Report](../agent_tasks/progress/2025-12-28_18-55-40_manual-testing-bug-report.md) for full details.

---

## Bug #1: Portfolio Balance Endpoint Crashes (P0)

### Problem
GET `/api/v1/portfolios/{id}/balance` returns 500 Internal Server Error

**Error**:
```python
AttributeError: 'GetPortfolioBalanceResult' object has no attribute 'balance'
```

### Root Cause
Field name mismatch between handler result and API response:

**Handler Returns**:
```python
@dataclass(frozen=True)
class GetPortfolioBalanceResult:
    portfolio_id: UUID
    cash_balance: Money  # ← Field is 'cash_balance'
    currency: str
    as_of: datetime
```

**API Accesses**:
```python
return BalanceResponse(
    amount=str(result.balance.amount),    # ← Tries 'balance' (doesn't exist!)
    currency=result.balance.currency,
    as_of=result.as_of.isoformat(),
)
```

### Fix
**File**: `backend/src/zebu/adapters/inbound/api/portfolios.py` (line ~320)

**Change From**:
```python
return BalanceResponse(
    amount=str(result.balance.amount),
    currency=result.balance.currency,
    as_of=result.as_of.isoformat(),
)
```

**Change To**:
```python
return BalanceResponse(
    amount=str(result.cash_balance.amount),
    currency=result.cash_balance.currency,
    as_of=result.as_of.isoformat(),
)
```

### Testing
**Integration Test** (add to `backend/tests/integration/test_api.py`):
```python
def test_get_portfolio_balance(client: TestClient, default_user_id: UUID) -> None:
    """Test GET /api/v1/portfolios/{id}/balance returns balance correctly."""
    # Create portfolio with initial deposit
    response = client.post(
        "/api/v1/portfolios",
        headers={"X-User-Id": str(default_user_id)},
        json={"name": "Test Portfolio", "initial_deposit": "10000.00", "currency": "USD"},
    )
    assert response.status_code == 201
    portfolio_id = response.json()["portfolio_id"]

    # Get balance
    response = client.get(
        f"/api/v1/portfolios/{portfolio_id}/balance",
        headers={"X-User-Id": str(default_user_id)},
    )
    assert response.status_code == 200

    data = response.json()
    assert "amount" in data
    assert "currency" in data
    assert "as_of" in data
    assert data["amount"] == "10000.00"
    assert data["currency"] == "USD"
```

---

## Bug #2: Frontend Uses Inconsistent User ID (P0)

### Problem
Frontend uses hardcoded user ID `00000000-0000-0000-0000-000000000001` but creates portfolios with different user IDs, causing portfolios to disappear after creation.

**Symptom**: User creates portfolio → modal closes → portfolio doesn't appear in dashboard

### Root Cause
No user ID persistence mechanism. Each portfolio creation might use a different ID than the one used for querying.

### Fix
**File**: `frontend/src/services/api/client.ts`

**Change From**:
```typescript
const DEFAULT_USER_ID = '00000000-0000-0000-0000-000000000001'

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
    'X-User-Id': DEFAULT_USER_ID,
  },
})
```

**Change To**:
```typescript
/**
 * Get or create a stable mock user ID for Phase 1.
 * Stored in localStorage to persist across sessions.
 *
 * TODO: Replace with real authentication in Phase 2
 */
function getMockUserId(): string {
  const STORAGE_KEY = 'zebu_mock_user_id'

  // Check localStorage for existing ID
  const stored = localStorage.getItem(STORAGE_KEY)
  if (stored) {
    return stored
  }

  // Generate new ID and store it
  const newId = crypto.randomUUID()
  localStorage.setItem(STORAGE_KEY, newId)
  return newId
}

const MOCK_USER_ID = getMockUserId()

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
    'X-User-Id': MOCK_USER_ID,
  },
})
```

### Testing
**Manual Test**:
1. Open application (new user ID generated)
2. Create portfolio "My Portfolio" with $10,000 deposit
3. Verify portfolio appears in dashboard immediately
4. Refresh page
5. Verify portfolio still appears (user ID persisted in localStorage)
6. Open DevTools → Application → Local Storage
7. Verify `zebu_mock_user_id` is present

**Unit Test** (add to `frontend/src/services/api/client.test.ts`):
```typescript
describe('apiClient user ID persistence', () => {
  it('generates and stores user ID in localStorage', () => {
    // Clear localStorage
    localStorage.clear()

    // Import client (will trigger getUserId)
    const { apiClient } = require('./client')

    // Verify user ID is stored
    const stored = localStorage.getItem('zebu_mock_user_id')
    expect(stored).toBeTruthy()
    expect(stored).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i)

    // Verify header is set
    expect(apiClient.defaults.headers['X-User-Id']).toBe(stored)
  })

  it('reuses existing user ID from localStorage', () => {
    const existingId = '12345678-1234-1234-1234-123456789012'
    localStorage.setItem('zebu_mock_user_id', existingId)

    // Re-import to trigger getUserId again
    jest.resetModules()
    const { apiClient } = require('./client')

    // Verify same ID is used
    expect(apiClient.defaults.headers['X-User-Id']).toBe(existingId)
  })
})
```

---

## Bug #3: Investigate & Fix Broken Trading Page (P0)

### Problem
User reported: "when I tried to buy stocks etc. it took me to a broken page"

### Investigation Steps
1. Navigate to `/portfolio/{id}` in running application
2. Locate "Trade Stocks" button or similar
3. Click button and observe behavior
4. Check for:
   - 404 errors (missing route/endpoint)
   - Runtime errors (console logs)
   - API errors (network tab)
   - Component crashes

### Likely Root Causes
Based on Bug #1 pattern, probably similar field name mismatch:
- `ExecuteTradeResult` has field X
- API tries to access field Y
- AttributeError at runtime

**Check Files**:
- `backend/src/zebu/application/commands/execute_trade.py`
- `backend/src/zebu/adapters/inbound/api/portfolios.py` (execute_trade endpoint)
- `frontend/src/pages/PortfolioDetail.tsx`
- `frontend/src/components/features/portfolio/TradeForm.tsx`

### Fix (TBD after investigation)
*Depends on exact cause*

### Testing
Add integration test:
```python
def test_execute_buy_trade(client: TestClient, default_user_id: UUID) -> None:
    """Test POST /api/v1/portfolios/{id}/trades for BUY action."""
    # Create portfolio with cash
    response = client.post(
        "/api/v1/portfolios",
        headers={"X-User-Id": str(default_user_id)},
        json={"name": "Trading Portfolio", "initial_deposit": "50000.00", "currency": "USD"},
    )
    portfolio_id = response.json()["portfolio_id"]

    # Execute buy trade
    response = client.post(
        f"/api/v1/portfolios/{portfolio_id}/trades",
        headers={"X-User-Id": str(default_user_id)},
        json={
            "action": "BUY",
            "ticker": "AAPL",
            "quantity": "10",
            "price": "150.00",
        },
    )
    assert response.status_code == 201

    data = response.json()
    assert "transaction_id" in data

    # Verify holdings updated
    holdings_response = client.get(
        f"/api/v1/portfolios/{portfolio_id}/holdings",
        headers={"X-User-Id": str(default_user_id)},
    )
    assert holdings_response.status_code == 200
    holdings = holdings_response.json()["holdings"]
    assert len(holdings) == 1
    assert holdings[0]["ticker"] == "AAPL"
    assert holdings[0]["quantity"] == "10.0000"
```

---

## Additional Integration Tests Required

### Portfolio Creation Flow
```python
def test_create_portfolio_and_list(client: TestClient, default_user_id: UUID) -> None:
    """Test portfolio appears in list after creation."""
    # Create portfolio
    response = client.post(
        "/api/v1/portfolios",
        headers={"X-User-Id": str(default_user_id)},
        json={"name": "New Portfolio", "initial_deposit": "5000.00", "currency": "USD"},
    )
    assert response.status_code == 201
    portfolio_id = response.json()["portfolio_id"]

    # List portfolios
    response = client.get(
        "/api/v1/portfolios",
        headers={"X-User-Id": str(default_user_id)},
    )
    assert response.status_code == 200
    portfolios = response.json()
    assert len(portfolios) == 1
    assert portfolios[0]["id"] == portfolio_id
    assert portfolios[0]["name"] == "New Portfolio"
```

### Holdings Calculation
```python
def test_holdings_after_multiple_trades(client: TestClient, default_user_id: UUID) -> None:
    """Test holdings are calculated correctly after buy and sell."""
    # Create portfolio
    response = client.post(
        "/api/v1/portfolios",
        headers={"X-User-Id": str(default_user_id)},
        json={"name": "Trading Portfolio", "initial_deposit": "100000.00", "currency": "USD"},
    )
    portfolio_id = response.json()["portfolio_id"]

    # Buy 100 shares of AAPL
    client.post(
        f"/api/v1/portfolios/{portfolio_id}/trades",
        headers={"X-User-Id": str(default_user_id)},
        json={"action": "BUY", "ticker": "AAPL", "quantity": "100", "price": "150.00"},
    )

    # Sell 30 shares of AAPL
    client.post(
        f"/api/v1/portfolios/{portfolio_id}/trades",
        headers={"X-User-Id": str(default_user_id)},
        json={"action": "SELL", "ticker": "AAPL", "quantity": "30", "price": "155.00"},
    )

    # Check holdings
    response = client.get(
        f"/api/v1/portfolios/{portfolio_id}/holdings",
        headers={"X-User-Id": str(default_user_id)},
    )
    holdings = response.json()["holdings"]
    assert len(holdings) == 1
    assert holdings[0]["ticker"] == "AAPL"
    assert holdings[0]["quantity"] == "70.0000"  # 100 - 30
```

---

## Files to Create/Modify

### Backend
- **Fix**: `backend/src/zebu/adapters/inbound/api/portfolios.py` - Balance endpoint field name
- **Add**: `backend/tests/integration/test_portfolio_api_integration.py` - New integration tests
- Possibly: `backend/src/zebu/adapters/inbound/api/portfolios.py` - Trade endpoint (TBD)

### Frontend
- **Fix**: `frontend/src/services/api/client.ts` - User ID persistence
- **Add**: `frontend/src/services/api/client.test.ts` - User ID tests

---

## Success Criteria

### Functional Requirements
- [ ] Balance endpoint returns 200 status code (not 500)
- [ ] Portfolio creation works and portfolio appears in dashboard
- [ ] User ID persists across page refreshes
- [ ] Trade execution works without crashes
- [ ] Can buy and sell stocks successfully
- [ ] Holdings update after trades

### Testing Requirements
- [ ] All existing tests still pass (218 tests)
- [ ] New integration tests pass (at least 5 new tests)
- [ ] Manual end-to-end test passes:
  1. Open application
  2. Create portfolio with $50,000
  3. View portfolio balance (shows $50,000)
  4. Buy 10 shares of AAPL at $150
  5. View holdings (shows 10 shares AAPL)
  6. View balance (shows $48,500)
  7. Sell 5 shares of AAPL at $155
  8. View holdings (shows 5 shares AAPL)
  9. View balance (shows $49,275)
  10. Refresh page (all data persists)

### Code Quality
- [ ] All new code has type hints
- [ ] Integration tests follow existing patterns
- [ ] No ruff warnings
- [ ] Pyright passes
- [ ] ESLint passes

---

## Testing Strategy Improvements

### Add to CI/CD Pipeline
1. **Integration Test Stage** (new)
   ```yaml
   integration-tests:
     runs-on: ubuntu-latest
     steps:
       - name: Start backend
         run: cd backend && uv run uvicorn zebu.main:app &
       - name: Run integration tests
         run: cd backend && uv run pytest tests/integration -v
   ```

2. **E2E Test Stage** (future)
   - Use Playwright to test frontend + backend together
   - Test real user workflows
   - Run in CI before merge

### Documentation
Update [PROGRESS.md](../PROGRESS.md):
- Document integration testing gap
- Add "Lessons Learned" section
- Update "Testing Philosophy" with integration test recommendations

---

## Constraints

1. **No Breaking Changes**: Fixes should not change API contracts
2. **Backward Compatible**: User ID persistence should work for new users and existing localStorage data
3. **Fast Execution**: Integration tests should run in <30 seconds
4. **Minimal Dependencies**: Don't add new testing libraries (use existing pytest, TestClient)

---

## Estimated Time Breakdown

| Task | Time | Agent |
|------|------|-------|
| Fix Bug #1 (Balance endpoint) | 15 min | Backend-SWE |
| Add balance integration test | 15 min | Backend-SWE |
| Fix Bug #2 (User ID persistence) | 30 min | Frontend-SWE |
| Add user ID tests | 15 min | Frontend-SWE |
| Investigate Bug #3 (Trading) | 30 min | Backend-SWE |
| Fix Bug #3 (Trading) | 1 hour | Backend-SWE |
| Add trade integration tests | 30 min | Backend-SWE |
| Add holdings integration test | 20 min | Backend-SWE |
| Manual end-to-end testing | 30 min | Both |
| Documentation updates | 15 min | Both |
| **Total** | **4 hours** | |

---

## Related Issues

- Manual Testing Bug Report: [2025-12-28_18-55-40_manual-testing-bug-report.md](../agent_tasks/progress/2025-12-28_18-55-40_manual-testing-bug-report.md)
- Task 010: Code Quality Assessment (identified need for integration tests)
- BACKLOG.md: Add integration tests (this task addresses it)

---

## Future Enhancements

After this task:
1. Add E2E tests with Playwright (Phase 2)
2. Add contract tests for API schemas (Phase 2)
3. Add performance tests for API endpoints (Phase 3)
4. Add visual regression tests for UI (Phase 3)

---

**This task is a BLOCKER for Phase 1 completion.** Without these fixes, the application is unusable by end users despite all unit tests passing. This demonstrates the critical importance of integration and E2E testing in Modern Software Engineering.
