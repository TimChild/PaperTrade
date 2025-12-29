# Manual Testing Bug Report - Phase 1 Application

**Date**: 2025-12-28 18:55 PST
**Tester**: User (TimChild) + Copilot Assistant
**Environment**: Local development (backend: SQLite, frontend: Vite dev server)
**Scope**: End-to-end user workflow testing

---

## Executive Summary

**Critical Bugs Found**: 3
**Severity**: BLOCKING - Application is currently unusable for end users

Attempted user workflow:
1. ✅ Navigate to application
2. ⚠️ Create portfolio with initial deposit → **BUG #1**: Frontend not sending proper user ID
3. ❌ View portfolio balance → **BUG #2**: Backend crashes with AttributeError
4. ❌ Buy stocks → **BUG #3**: "Broken page" (likely 404 or similar error)

**Status**: Phase 1 is NOT production-ready despite all tests passing. Critical integration issues between frontend and backend.

---

## Test Environment Setup

### Backend
```bash
cd backend && uv run uvicorn papertrade.main:app --host 0.0.0.0 --port 8000
```
- **Status**: Started successfully ✅
- **Database**: SQLite (`papertrade.db`) - initially empty
- **API Base**: http://localhost:8000/api/v1

### Frontend
```bash
cd frontend && npm run dev
```
- **Status**: Started successfully ✅
- **Dev Server**: http://localhost:5173
- **Hot Reload**: Working

---

## Bug #1: Frontend Uses Wrong User ID (P0 - CRITICAL)

### Description
Frontend uses a hardcoded user ID (`00000000-0000-0000-0000-000000000001`) that doesn't match any portfolios created by the user during testing.

### Evidence

**Frontend Configuration** ([client.ts](frontend/src/services/api/client.ts#L12)):
```typescript
const DEFAULT_USER_ID = '00000000-0000-0000-0000-000000000001'

export const apiClient = axios.create({
  headers: {
    'X-User-Id': DEFAULT_USER_ID,
  },
})
```

**Backend Logs** (portfolio creation attempts):
```
INFO: 127.0.0.1:53999 - "POST /api/v1/portfolios HTTP/1.1" 400 Bad Request
INFO: 127.0.0.1:54012 - "POST /api/v1/portfolios HTTP/1.1" 400 Bad Request
INFO: 127.0.0.1:54014 - "POST /api/v1/portfolios HTTP/1.1" 400 Bad Request
```

Frontend kept failing to create portfolios because the UI doesn't capture or set the user ID properly.

**When tested with curl** using a different user ID:
```bash
curl -X POST http://localhost:8000/api/v1/portfolios \
  -H "X-User-Id: 12345678-1234-1234-1234-123456789012" \
  -d '{"name": "Test Portfolio", "initial_deposit": "10000.00", "currency": "USD"}'

# Response: {"portfolio_id":"7772468c-b775-4a92-92b7-38f0f6ea735f", "transaction_id":"..."}
```

Portfolio created successfully, but frontend can't see it because it's querying with a different user ID.

### Impact
- Users can create portfolios but can't see them in the UI
- Dashboard shows "No portfolios found" even after successful creation
- All portfolio API calls return 404 because user ID mismatch

### Root Cause
Frontend and backend use different user IDs:
- **Frontend**: `00000000-0000-0000-0000-000000000001` (hardcoded in client.ts)
- **Backend**: Accepts any valid UUID in `X-User-Id` header
- **No coordination**: When user creates portfolio, they use one ID, but frontend queries with another

### Reproduction Steps
1. Open application at http://localhost:5173
2. Click "Create Portfolio"
3. Fill in "My Portfolio" and "$10,000" initial deposit
4. Click "Create Portfolio"
5. Modal closes, but portfolio doesn't appear in dashboard
6. Backend logs show 400 error for POST request
7. User sees empty state again

### Expected Behavior
- Frontend should use a consistent user ID across all requests
- OR frontend should store user ID in localStorage/state
- Portfolio created with user ID X should be visible when querying with same user ID X

### Recommended Fix
**Option 1** (Quick Fix for Phase 1):
```typescript
// frontend/src/services/api/client.ts
// Generate a stable user ID on first visit, store in localStorage
function getUserId(): string {
  const stored = localStorage.getItem('mockUserId')
  if (stored) return stored

  const newId = crypto.randomUUID()
  localStorage.setItem('mockUserId', newId)
  return newId
}

const DEFAULT_USER_ID = getUserId()
```

**Option 2** (Proper Fix for Phase 2):
- Implement real authentication
- User logs in, gets JWT token
- Token contains user ID
- All API calls include token
- Backend validates token and extracts user ID

**Estimated Fix Time**: 30 minutes (Option 1), 4-6 hours (Option 2)

---

## Bug #2: Portfolio Balance Endpoint Crashes (P0 - CRITICAL)

### Description
GET `/api/v1/portfolios/{id}/balance` endpoint crashes with `AttributeError` when trying to return balance data.

### Evidence

**Backend Error**:
```
INFO: 127.0.0.1:54032 - "GET /api/v1/portfolios/7772468c-b775-4a92-92b7-38f0f6ea735f/balance HTTP/1.1" 500 Internal Server Error
ERROR: Exception in ASGI application
Traceback (most recent call last):
  ...
  File "/Users/timchild/github/PaperTrade/backend/src/papertrade/adapters/inbound/api/portfolios.py", line 320, in get_balance
    amount=str(result.balance.amount),
               ^^^^^^^^^^^^^^
AttributeError: 'GetPortfolioBalanceResult' object has no attribute 'balance'
```

### Root Cause

**Handler Returns** ([get_portfolio_balance.py](backend/src/papertrade/application/queries/get_portfolio_balance.py#L26-L40)):
```python
@dataclass(frozen=True)
class GetPortfolioBalanceResult:
    portfolio_id: UUID
    cash_balance: Money  # ← Field is named 'cash_balance'
    currency: str
    as_of: datetime
```

**API Tries to Access** ([portfolios.py](backend/src/papertrade/adapters/inbound/api/portfolios.py#L320)):
```python
return BalanceResponse(
    amount=str(result.balance.amount),  # ← Tries to access 'balance' (doesn't exist!)
    currency=result.balance.currency,
    as_of=result.as_of.isoformat(),
)
```

Field mismatch: `cash_balance` vs `balance`

### Impact
- Users cannot view their portfolio balance
- Dashboard fails to load (crashes when fetching balance)
- 500 Internal Server Error returned to frontend
- User sees error message instead of portfolio data

### Reproduction Steps
1. Create a portfolio via API (or fix Bug #1 first)
2. Navigate to `/portfolio/{portfolio_id}`
3. API call to `/api/v1/portfolios/{id}/balance` is made
4. Backend crashes with 500 error
5. Frontend shows error state

### Expected Behavior
API should return balance successfully:
```json
{
  "amount": "10000.00",
  "currency": "USD",
  "as_of": "2025-12-28T18:54:55.566768"
}
```

### Recommended Fix
**Update API handler** ([portfolios.py](backend/src/papertrade/adapters/inbound/api/portfolios.py#L320)):
```python
return BalanceResponse(
    amount=str(result.cash_balance.amount),      # ← Fix: use 'cash_balance'
    currency=result.cash_balance.currency,       # ← Fix: use 'cash_balance'
    as_of=result.as_of.isoformat(),
)
```

**Estimated Fix Time**: 5 minutes

### Why Tests Didn't Catch This
Looking at test coverage, we likely have:
- ✅ Unit tests for `GetPortfolioBalanceHandler` (pass because handler works correctly)
- ✅ Unit tests for API endpoint (probably mock the handler, so they don't catch the field mismatch)
- ❌ Integration tests that call the actual endpoint end-to-end

**Recommendation**: Add integration test that makes real HTTP call to balance endpoint and verifies response structure.

---

## Bug #3: Stock Trading Page Broken (P0 - CRITICAL)

### Description
User reported: "when I tried to buy stocks etc. it took me to a broken page"

### Evidence
- User tested the application manually
- Clicked through to buy stocks functionality
- Page was broken (exact error not captured, but likely 404 or crash)

### Investigation Needed
Need to test the trade execution flow:
1. Navigate to `/portfolio/{id}`
2. Find "Trade Stocks" button or similar
3. Fill in trade form
4. Submit trade
5. Check if page crashes, shows 404, or has other issues

**Hypothesis**: Similar issue to Bug #2, likely one of:
- API endpoint crashes with AttributeError (field mismatch)
- Route doesn't exist (404)
- Frontend component has runtime error
- Missing data causes crash

### Potential Root Causes

**Option A**: Trade execution endpoint has similar field mismatch bug
```python
# Probably something like:
result = handler.execute(command)
return TradeResponse(
    transaction_id=result.id,           # ← Might be wrong field name
    amount=result.total_cost.amount,    # ← Might crash here
)
```

**Option B**: Frontend route not configured properly
- `/portfolio/:id/trade` route missing
- Component crashes on render
- Missing prop validation

**Option C**: Backend endpoint missing
- API route not registered
- 404 error when trying to POST /api/v1/portfolios/{id}/trades

### Reproduction Steps
*Need to test manually to confirm exact error*
1. Open portfolio detail page
2. Click "Trade Stocks" or similar button
3. Fill in trade form (symbol, quantity, price)
4. Click "Buy" or "Sell"
5. Observe error

### Expected Behavior
- Trade form should be accessible
- User can enter trade details
- Submit button executes trade
- Success message shown
- Portfolio balance and holdings updated

### Recommended Fix
*Depends on exact cause - need investigation*

**Estimated Investigation Time**: 30 minutes
**Estimated Fix Time**: 30 minutes - 2 hours (depends on complexity)

---

## Additional Issues Found

### Issue #4: Database Always Empty on Fresh Start (P2 - IMPORTANT)

**Description**: Every time backend restarts, database is empty. No seed data.

**Impact**:
- Users need to create portfolios from scratch each time
- Testing is tedious (must recreate data after every restart)
- No example data to demonstrate features

**Recommendation**: Add seed data script or test fixtures

**Estimated Fix Time**: 1 hour

---

### Issue #5: Frontend Can't See Portfolios from Different User IDs (P1 - HIGH)

**Description**: This is a consequence of Bug #1, but worth noting separately.

**Impact**:
- If user creates portfolio with one user ID (e.g., via curl), frontend can't see it
- No way to "switch users" in the UI
- Testing with multiple user accounts is impossible

**Recommendation**: Fix Bug #1 first, then add user ID persistence

---

## Summary of Required Fixes

| Bug | Severity | Effort | Impact | Status |
|-----|----------|--------|--------|--------|
| #1: Wrong User ID | P0 | 30 min | BLOCKING | Not Fixed |
| #2: Balance Crashes | P0 | 5 min | BLOCKING | Not Fixed |
| #3: Trading Broken | P0 | 2 hours | BLOCKING | Needs Investigation |
| #4: No Seed Data | P2 | 1 hour | QoL | Not Fixed |
| #5: No User Switching | P1 | 30 min | Testing | Not Fixed |

**Total Estimated Time to Fix Blocking Issues**: ~3 hours

---

## Testing Gaps Identified

### Why Did Tests Pass But App is Broken?

1. **Unit Tests Pass**: Each component works in isolation
   - `GetPortfolioBalanceHandler` works correctly ✅
   - API endpoint handler works correctly ✅
   - But integration between them is broken ❌

2. **Mocking Hides Issues**: Tests mock dependencies
   - API tests mock the handler, so they don't call real code
   - Handler tests don't call API layer
   - Field mismatch not caught

3. **No End-to-End Tests**: No tests that simulate real user workflows
   - No test that starts servers and makes HTTP calls
   - No test that creates portfolio → fetches balance → buys stock
   - Integration issues only found during manual testing

### Recommendations for Better Testing

1. **Add Integration Tests** (P0)
   - Tests that make real HTTP calls to running server
   - Tests that use real database (SQLite in-memory)
   - Test end-to-end workflows:
     ```python
     def test_create_portfolio_and_fetch_balance():
         # POST /api/v1/portfolios
         response = client.post("/api/v1/portfolios", ...)
         portfolio_id = response.json()["portfolio_id"]

         # GET /api/v1/portfolios/{id}/balance
         balance_response = client.get(f"/api/v1/portfolios/{portfolio_id}/balance")
         assert balance_response.status_code == 200
         assert balance_response.json()["amount"] == "10000.00"
     ```

2. **Add Frontend E2E Tests** (P1)
   - Playwright or Cypress tests
   - Test user workflows:
     - Create portfolio
     - View balance
     - Buy stock
     - View holdings
     - View transaction history

3. **Add Contract Tests** (P2)
   - Verify API responses match expected schemas
   - Catch field name mismatches before deployment
   - Use Pydantic validation on API layer

---

## Verification Database State

**After Manual Testing**:

```bash
$ cd backend && uv run python -c "
from sqlmodel import Session, create_engine, select
from papertrade.adapters.outbound.database.models import PortfolioModel, TransactionModel

engine = create_engine('sqlite:///papertrade.db')
with Session(engine) as session:
    portfolios = session.exec(select(PortfolioModel)).all()
    print(f'Portfolios ({len(portfolios)}):')
    for p in portfolios:
        print(f'  {p.name} - ID: {p.id}, User: {p.user_id}')

    transactions = session.exec(select(TransactionModel)).all()
    print(f'\nTransactions ({len(transactions)}):')
    for t in transactions:
        print(f'  {t.transaction_type}: {t.cash_change_amount} {t.cash_change_currency}')
"

# Output:
Portfolios (1):
  Test Portfolio - ID: 7772468c-b775-4a92-92b7-38f0f6ea735f, User: 12345678-1234-1234-1234-123456789012

Transactions (1):
  DEPOSIT: 10000.00 USD
```

**Observations**:
- ✅ Portfolio created successfully via curl
- ✅ Initial deposit transaction recorded correctly
- ✅ Database persistence working
- ❌ Frontend can't see this portfolio (user ID mismatch)
- ❌ Balance endpoint crashes when queried

---

## Next Steps

### Immediate Actions (Must Do Before Phase 1 Release)
1. **Fix Bug #2** (5 minutes) - Balance endpoint crash
   - One-line fix in `portfolios.py`
   - Critical for basic functionality

2. **Fix Bug #1** (30 minutes) - User ID persistence
   - Use localStorage to persist mock user ID
   - Ensures consistent user ID across sessions
   - Unblocks portfolio creation workflow

3. **Investigate Bug #3** (30 minutes) - Trading page broken
   - Manually test trade execution
   - Identify exact error
   - Document reproduction steps

4. **Fix Bug #3** (1-2 hours) - Trading page broken
   - Fix identified issue
   - Test end-to-end trade workflow

5. **Add Integration Tests** (2-3 hours)
   - Create portfolio + fetch balance test
   - Execute trade + verify holdings test
   - Prevent regression of these issues

### Medium Priority (Should Do Before Phase 2)
- Add seed data script
- Add E2E tests with Playwright
- Add contract tests for API

### Long Term (Phase 2+)
- Implement real authentication
- Remove mock user ID
- Add user management

---

## Lessons Learned

1. **Testing Philosophy Gap**: We have excellent unit tests (218 passing!) but missing integration tests. Modern Software Engineering emphasizes "testing behavior, not implementation" - we need tests that verify the system works as a whole.

2. **Clean Architecture Trade-off**: Layers are well-separated (good!), but this means unit tests can pass while integration fails (bad!). Need tests at multiple levels:
   - Unit tests (component isolation) ✅
   - Integration tests (components working together) ❌
   - E2E tests (user workflows) ❌

3. **Field Name Consistency**: Domain models, DTOs, and API responses use different field names (`cash_balance` vs `balance`). This causes runtime errors that tests don't catch. Consider:
   - Use same field names across layers
   - Use Pydantic validation to catch mismatches
   - Add integration tests to verify mappings

4. **Mock User ID Pitfall**: Hardcoding a user ID worked fine for unit tests, but creates issues in real usage. Need to think through how mock authentication works end-to-end.

---

## Impact on Phase 1 Completion

**Previous Assessment**: ✅ Phase 1 Complete - 218 tests passing, 0 vulnerabilities

**Revised Assessment**: ⚠️ Phase 1 Incomplete - Critical integration bugs prevent basic usage

**Recommendation**: Create "Task 016: Fix Critical Integration Bugs" before declaring Phase 1 complete.

This is a valuable lesson: **Tests passing ≠ System working**. We need multiple levels of testing to ensure the system actually works for users.
