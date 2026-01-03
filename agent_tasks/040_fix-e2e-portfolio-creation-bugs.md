# Task 040: Fix E2E Portfolio Creation Bugs

**Status**: 🔴 Not Started
**Priority**: HIGH
**Agent**: backend-swe / full-stack
**Estimated Time**: 2-4 hours
**Created**: 2026-01-03

## Context

PR #55 successfully fixed all E2E test **infrastructure** issues (port conflicts, server management, test selectors). The E2E tests now run correctly and connect to backend/frontend services via Docker Compose.

However, the tests are now **correctly revealing real application bugs** in the portfolio creation workflow. This is GOOD - it means our E2E infrastructure is working properly!

## Problem Statement

**4 out of 7 E2E tests are failing** due to portfolio creation not working correctly:

### Failing Tests

1. **`portfolio-creation.spec.ts` - "should create portfolio and show it in dashboard"**
   - User creates portfolio "My Test Portfolio" with $10,000
   - Portfolio form submits successfully
   - ❌ Portfolio does NOT appear in dashboard (should show name or balance)

2. **`portfolio-creation.spec.ts` - "should persist portfolio after page refresh"**
   - User creates portfolio "Persistent Portfolio" with $25,000
   - Page refreshes
   - ❌ Portfolio does NOT persist (should still be visible after refresh)

3. **`portfolio-creation.spec.ts` - "should show validation error for empty portfolio name"**
   - User tries to submit form without entering portfolio name
   - ❌ Form submit button stays disabled and times out
   - Expected: HTML5 validation should focus the empty name field

4. **`portfolio-creation.spec.ts` - "should show validation error for invalid deposit amount"**
   - User enters negative deposit amount (-1000)
   - ❌ No validation error appears
   - Expected: Should show error message about positive numbers

### Passing Tests

- 3 trading tests are **skipped** (they check for trade form visibility first, skip if not found)
- This is acceptable - trading tests will work once portfolio creation is fixed

## Technical Details

### E2E Test Infrastructure (WORKING ✅)

The E2E setup is now correct:
- Docker Compose runs full stack: PostgreSQL, Redis, Backend, Frontend
- Playwright connects to http://localhost:5173 (frontend) and http://localhost:8000 (backend)
- Test selectors use unique test IDs: `data-testid="create-first-portfolio-btn"`, `data-testid="submit-portfolio-form-btn"`
- No port conflicts or infrastructure issues

### Portfolio Creation Flow

**Frontend Components:**
- [src/pages/Dashboard.tsx](../frontend/src/pages/Dashboard.tsx) - Shows portfolios list and "Create Portfolio" buttons
- [src/components/features/portfolio/CreatePortfolioForm.tsx](../frontend/src/components/features/portfolio/CreatePortfolioForm.tsx) - Form component with name/deposit fields
- [src/hooks/usePortfolio.ts](../frontend/src/hooks/usePortfolio.ts) - `useCreatePortfolio()` mutation hook

**Backend API:**
- POST `/api/portfolios/` - Creates new portfolio
- GET `/api/portfolios/` - Lists all portfolios for user
- GET `/api/portfolios/{id}/balance` - Gets portfolio balance

**User ID Management (Critical!):**
- Frontend stores `userId` in localStorage: `localStorage.getItem('user_id')`
- If no userId exists, frontend generates one: `crypto.randomUUID()`
- Backend requires `user_id` in request body when creating portfolio
- **Known Issue from Task 016**: User ID persistence issues were reported

### Suspected Root Causes

Based on test failures and previous bug reports (Task 016 manual testing):

1. **User ID not being sent correctly**
   - Frontend might not be including `user_id` in create portfolio request
   - Or localStorage might not be persisting between page loads

2. **Portfolio creation succeeding but not reflecting in UI**
   - Backend might create portfolio successfully
   - But frontend query cache not invalidating properly
   - Or GET `/api/portfolios/` not returning newly created portfolio

3. **Form validation not working**
   - CreatePortfolioForm might have incorrect validation logic
   - HTML5 validation attributes might be missing (required, min, etc.)

4. **Modal/routing issues**
   - After creating portfolio, modal might not close
   - Or page might not refresh to show new portfolio

## Acceptance Criteria

### Must Have

- [ ] All 4 failing E2E tests pass locally
- [ ] Portfolio creation persists across page refreshes
- [ ] Portfolio appears in dashboard immediately after creation
- [ ] Form validation works for empty name (HTML5 required attribute)
- [ ] Form validation works for invalid deposit amounts (negative/zero)
- [ ] User ID is correctly generated and persisted in localStorage
- [ ] Backend tests still pass (no regressions)
- [ ] Frontend tests still pass (no regressions)

### Should Have

- [ ] Clear error messages for validation failures
- [ ] Loading states during portfolio creation
- [ ] Success feedback after portfolio creation

### Nice to Have

- [ ] Unit tests for portfolio creation flow
- [ ] Better error handling for network failures

## Investigation Steps

### 1. Reproduce Locally

```bash
# Start full stack
task docker:up:all

# In separate terminal, run E2E tests
cd frontend
npm run test:e2e:ui  # Opens Playwright UI for debugging
```

### 2. Debug Portfolio Creation Request

**Check Network Tab:**
- Does POST `/api/portfolios/` get called?
- What's in the request body? Is `user_id` included?
- What's the response? Success or error?

**Check Backend Logs:**
```bash
docker compose logs -f backend
```
- Does portfolio creation endpoint get hit?
- Any errors in backend logs?

**Check Database:**
```bash
docker compose exec db psql -U papertrade -d papertrade_dev -c "SELECT * FROM portfolio;"
```
- Does portfolio get created in database?
- What's the `user_id` value?

### 3. Debug Frontend State

**Check localStorage:**
```javascript
// In browser console
localStorage.getItem('user_id')
```

**Check React Query Cache:**
```javascript
// In React DevTools → Components → find QueryClientProvider
// Inspect query cache for 'portfolios' key
```

**Check useCreatePortfolio hook:**
- Does `onSuccess` callback get called?
- Does it call `queryClient.invalidateQueries(['portfolios'])`?

### 4. Debug Form Validation

**Check CreatePortfolioForm.tsx:**
- Does name input have `required` attribute?
- Does deposit input have `type="number"` and `min="0.01"` attributes?
- Is form using HTML5 validation or custom validation?

## Implementation Approach

### Phase 1: Identify Root Cause (30-60 min)

1. Run failing tests in Playwright UI
2. Use browser DevTools to inspect network requests
3. Check backend logs for errors
4. Verify database state after attempted creation
5. Document findings

### Phase 2: Fix Core Issues (1-2 hours)

Likely fixes (prioritize based on Phase 1 findings):

**Fix 1: User ID Management**
```typescript
// In CreatePortfolioForm or usePortfolio hook
const getUserId = () => {
  let userId = localStorage.getItem('user_id')
  if (!userId) {
    userId = crypto.randomUUID()
    localStorage.setItem('user_id', userId)
  }
  return userId
}
```

**Fix 2: Include user_id in Request**
```typescript
// In useCreatePortfolio mutation
mutationFn: async (data) => {
  const userId = getUserId()
  return apiClient.post('/api/portfolios/', {
    ...data,
    user_id: userId,  // Ensure this is included!
  })
}
```

**Fix 3: Invalidate Queries After Creation**
```typescript
// In useCreatePortfolio onSuccess callback
onSuccess: () => {
  queryClient.invalidateQueries(['portfolios'])
  queryClient.invalidateQueries(['portfolio-balance'])
  // Close modal, show success message, etc.
}
```

**Fix 4: Add Form Validation Attributes**
```tsx
<input
  type="text"
  name="name"
  required  // HTML5 validation
  minLength={1}
  {...}
/>

<input
  type="number"
  name="initialDeposit"
  required
  min="0.01"
  step="0.01"
  {...}
/>
```

### Phase 3: Verify & Test (30-60 min)

1. Run all E2E tests: `npm run test:e2e`
2. Run backend tests: `task test:backend`
3. Run frontend tests: `task test:frontend`
4. Manual testing:
   - Create portfolio
   - Refresh page
   - Verify portfolio persists
   - Try invalid inputs
   - Verify validation errors

## Files to Review/Modify

### Frontend (Likely Changes)

- `frontend/src/components/features/portfolio/CreatePortfolioForm.tsx` - Form validation and submission
- `frontend/src/hooks/usePortfolio.ts` - `useCreatePortfolio()` hook
- `frontend/src/pages/Dashboard.tsx` - Portfolio display after creation
- `frontend/src/lib/api-client.ts` - API client (if user_id needs to be added globally)

### Backend (Possible Changes)

- `backend/src/papertrade/adapters/inbound/api/routes/portfolio_routes.py` - Portfolio creation endpoint
- `backend/src/papertrade/application/use_cases/portfolio/create_portfolio.py` - Business logic

### Tests

- `frontend/tests/e2e/portfolio-creation.spec.ts` - E2E tests (should pass after fixes)
- Consider adding unit tests for user ID management

## Success Metrics

**Before:**
- E2E: 3 passed, 4 failed, 3 skipped
- Infrastructure issues: FIXED ✅
- Application issues: BROKEN ❌

**After:**
- E2E: 7 passed (or 4 passed, 3 skipped if trading tests still skip)
- Infrastructure issues: FIXED ✅
- Application issues: FIXED ✅
- CI: ALL TESTS PASSING ✅

## Notes

- The E2E infrastructure is working perfectly now (PR #55)
- Test failures are **real bugs**, not test flakes
- User ID persistence was a known issue from Task 016
- Focus on fixing the bugs, not the tests
- Tests are correct - they're revealing broken functionality

## Related

- PR #55: E2E infrastructure fixes (merged)
- Task 016: Manual testing that revealed user ID issues
- BACKLOG.md: Task #039 for skipped scheduler tests (separate issue)

## Definition of Done

- [ ] All 4 failing E2E tests pass
- [ ] No regressions in backend tests (418 passed, 4 skipped)
- [ ] No regressions in frontend tests (81 passed, 1 skipped)
- [ ] CI passes completely (all jobs green)
- [ ] Code reviewed for quality
- [ ] Changes committed with clear messages
- [ ] PR created and description explains fixes
- [ ] Documentation updated if needed

---

**Agent Notes:**

You have full context on the E2E infrastructure (it's working!). Your job is to fix the application bugs that the tests are now correctly revealing. Start by reproducing the failures in Playwright UI, then use browser DevTools and backend logs to understand what's going wrong. The most likely culprit is user ID management - make sure the frontend is generating, storing, and sending the user_id correctly with portfolio creation requests.

Good luck! 🚀
