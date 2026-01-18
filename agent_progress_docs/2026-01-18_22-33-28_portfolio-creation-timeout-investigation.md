# Agent Progress Documentation

**Date**: 2026-01-18  
**Time**: 22:33:28 UTC  
**Agent**: backend-swe  
**Task**: Task 161 - Investigate Portfolio Creation Timeout Issue  
**Status**: Investigation Complete - Awaiting Test Validation

---

## Executive Summary

Investigated critical issue where ALL portfolio creation requests timeout in E2E tests. The issue is **not** a timeout per se, but authentication failures (401 Unauthorized) that prevent successful POST requests. Added comprehensive diagnostic logging throughout the authentication flow to identify the exact failure point. The issue likely stems from Clerk session state not being properly initialized when E2E tests run.

---

## Problem Statement

### Symptoms
- E2E Tests: 15/22 tests fail with `TimeoutError: page.waitForURL: Timeout 10000ms exceeded`
- Backend logs show: "Clerk auth status: AuthStatus.SIGNED_OUT" for POST requests
- Frontend shows 2 timeout alerts in create portfolio dialog  
- GET requests work perfectly (<1s response time)
- POST requests fail with 401 Unauthorized

### Evidence
```
# Backend logs
method=POST path=/api/v1/portfolios
Clerk auth status: AuthStatus.SIGNED_OUT
status_code=401 duration_seconds=0.017
```

```
# E2E test error
TimeoutError: page.waitForURL: Timeout 10000ms exceeded.
waiting for navigation to "**/portfolio/*" until "load"
```

The "timeout" is actually the test waiting for navigation that never happens because the POST request fails with 401.

---

## Investigation Process

### 1. Authentication Architecture Review

**Backend Flow:**
```
POST /api/v1/portfolios
  ↓
FastAPI HTTPBearer security (requires Authorization header)
  ↓
get_current_user dependency
  ↓
ClerkAuthAdapter.verify_token()
  ↓
Clerk.authenticate_request() → Returns SIGNED_OUT status
  ↓
401 Unauthorized
```

**Frontend Flow:**
```
User submits form
  ↓
API client interceptor calls tokenGetter()
  ↓
tokenGetter() calls useAuth().getToken()
  ↓
Clerk React SDK retrieves session token
  ↓
Token added to Authorization: Bearer {token} header
  ↓
Request sent to backend
```

**E2E Test Setup:**
```
global-setup.ts: Creates Clerk testing token via API
  ↓
auth.setup.ts: Uses clerk.signIn() to create real Clerk session
  ↓
Saves storage state (cookies + localStorage) to playwright/.auth/user.json
  ↓
Tests load storage state before running
  ↓
fixtures.ts: Calls setupClerkTestingToken() for each page
  ↓
App should detect session from storage and initialize Clerk
```

### 2. Key Findings

**Finding #1: Token Retrieval Likely Failing**
- Backend logs show requests ARE reaching auth code (not failing in middleware)
- Clerk is returning `SIGNED_OUT`, meaning token is invalid or missing
- Most likely: `useAuth().getToken()` is returning `null`

**Finding #2: Timing Issues**
- AuthProvider sets up tokenGetter in useEffect
- Original code didn't wait for `isLoaded` before setting up getter
- Token might be requested before Clerk fully initializes

**Finding #3: Session State Questions**
- Clerk session created during auth.setup.ts should persist in storage state
- When tests load storage state, Clerk should detect the session
- But `isSignedIn` may be `false` if session not properly loaded

**Finding #4: GET vs POST Mystery**
- Both endpoints require authentication (`current_user: CurrentUserDep`)
- GET /api/v1/portfolios works, POST fails
- Suggests timing issue: GET happens when Clerk is ready, POST happens too early
- OR: GET requests don't actually get called (tests might not verify this)

### 3. Backend Integration Tests Comparison

Backend integration tests work by:
```python
# Override auth dependency with InMemoryAuthAdapter
app.dependency_overrides[get_auth_port] = get_test_auth_port

# Use known test token
auth_headers = {"Authorization": "Bearer test-token-default"}
```

E2E tests cannot override dependencies - they run against the real backend with real Clerk authentication.

---

## Changes Implemented

### Frontend: AuthProvider Enhancement
**File**: `frontend/src/components/AuthProvider.tsx`

**Changes:**
1. Wait for `isLoaded=true` before setting up token getter
2. Check `isSignedIn` before attempting token retrieval
3. Add comprehensive diagnostic logging:
   - Clerk initialization status
   - Sign-in state
   - Token retrieval attempts and results
   - Specific error conditions

**Rationale:**
- Prevents race condition where token is requested before Clerk is ready
- Provides clear diagnostics for debugging
- Fails fast with informative error messages

```typescript
// Before
useEffect(() => {
  setAuthTokenGetter(async () => {
    return await getToken()
  })
}, [getToken, isLoaded, isSignedIn])

// After
useEffect(() => {
  if (!isLoaded) {
    console.log('[AuthProvider] Waiting for Clerk to load...')
    return
  }
  
  setAuthTokenGetter(async () => {
    if (!isSignedIn) {
      console.error('[AuthProvider] User not signed in...')
      return null
    }
    return await getToken()
  })
}, [getToken, isLoaded, isSignedIn])
```

### Frontend: API Client Diagnostics
**File**: `frontend/src/services/api/client.ts`

**Changes:**
1. Enhanced logging with token preview (security-safe)
2. Escalated warnings to errors for critical failures
3. Added specific guidance in error messages
4. Log method and URL for each request

**Rationale:**
- Makes it immediately obvious when token retrieval fails
- Helps identify which requests fail and why
- Security-conscious (only logs first/last 10 chars of tokens)

### Backend: ClerkAuthAdapter Diagnostics
**File**: `backend/src/zebu/adapters/auth/clerk_adapter.py`

**Changes:**
1. Log token preview before verification
2. Log Clerk's `request_state.reason` and `message` fields
3. Enhanced error context

**Rationale:**
- Reveals exactly why Clerk rejects tokens
- Helps distinguish between expired, invalid, and missing tokens
- Critical for debugging E2E test failures

**Key Addition:**
```python
logger.info(
    f"Clerk auth status: {request_state.status}, "
    f"reason: {request_state.reason}, "
    f"message: {request_state.message}"
)
```

### Backend: Dependency Injection Logging
**File**: `backend/src/zebu/adapters/inbound/api/dependencies.py`

**Changes:**
1. Log which auth adapter is being used
2. Log authentication attempts and results
3. Better error messages for failed authentication

**Rationale:**
- Confirms correct auth adapter is loaded
- Shows authentication flow in logs
- Helps correlate frontend and backend issues

---

## Root Cause Hypotheses

Based on investigation, the issue is likely ONE of the following:

### Hypothesis #1: Clerk Not Fully Initialized (Most Likely)
**Symptoms**: `isLoaded=false` or `isSignedIn=false` when token requested  
**Cause**: Storage state loads but Clerk SDK hasn't finished initializing  
**Fix**: Wait for Clerk to be ready (implemented in AuthProvider)  
**Validation**: Logs will show `[AuthProvider] Waiting for Clerk to load...`

### Hypothesis #2: Session Not in Storage State
**Symptoms**: `isLoaded=true` but `isSignedIn=false`  
**Cause**: auth.setup.ts didn't save session properly, or cookies expired  
**Fix**: Verify storage state includes necessary cookies, check session expiration  
**Validation**: Logs will show `[AuthProvider] User not signed in`

### Hypothesis #3: getToken() Returning Null Despite Sign-In
**Symptoms**: `isLoaded=true`, `isSignedIn=true`, but `getToken()` returns null  
**Cause**: Clerk SDK bug or session token refresh failure  
**Fix**: May need to manually refresh token or use different Clerk method  
**Validation**: Logs will show `[AuthProvider] getToken() returned null despite isSignedIn=true`

### Hypothesis #4: Invalid Clerk Configuration
**Symptoms**: Clerk rejects valid tokens  
**Cause**: Clerk secret key mismatch or publishable key configuration issue  
**Fix**: Verify env vars match Clerk dashboard  
**Validation**: Backend logs will show specific Clerk error in `reason`/`message`

---

## Testing Instructions

### Step 1: Run Single E2E Test with Logging
```bash
cd /home/runner/work/PaperTrade/PaperTrade

# Start Docker services
task docker:up

# Run backend in one terminal
cd backend
uv run python -m zebu.main

# Run frontend dev server in another terminal
cd frontend  
npm run dev

# Run single portfolio creation test
npm run test:e2e -- tests/e2e/portfolio-creation.spec.ts
```

### Step 2: Analyze Logs

**Frontend Console Logs** (look for):
```
[AuthProvider] Waiting for Clerk to load...          → Clerk initializing
[AuthProvider] Clerk loaded. isSignedIn: true        → Success
[AuthProvider] User not signed in                    → Hypothesis #2
[API Client] Token retrieved for POST ...            → Token available
[API Client] CRITICAL: No token available            → Hypothesis #1 or #3
```

**Backend Logs** (look for):
```
Verifying token: eyJhbGc...abc123, length: 200       → Token received
Clerk auth status: SIGNED_IN                         → Success
Clerk auth status: SIGNED_OUT, reason: ...           → See reason
Authentication successful for user: user_xxx         → Success
Authentication failed: ...                           → See error
```

### Step 3: Determine Root Cause

| Frontend Log | Backend Log | Root Cause | Fix |
|--------------|-------------|------------|-----|
| "Waiting for Clerk" | No request | Clerk not loading | Check ClerkProvider setup |
| "User not signed in" | No request | Session not loaded | Check storage state |
| "No token available" | No request | getToken() failed | Check Clerk session |
| "Token retrieved" | "SIGNED_OUT" | Invalid token | Check Clerk config |

### Step 4: Implement Fix (Based on Root Cause)

**If Clerk not loading:**
- Check ClerkProvider is properly wrapping app
- Verify VITE_CLERK_PUBLISHABLE_KEY is set
- Add explicit wait in tests for Clerk to load

**If session not loaded:**
- Verify auth.setup.ts is creating session properly
- Check storage state file includes session cookies
- May need to adjust how storage state is saved/loaded

**If getToken() fails:**
- Add retry logic in AuthProvider
- Manually refresh token before calling getToken()
- Check Clerk session expiration settings

**If Clerk rejects token:**
- Verify CLERK_SECRET_KEY matches dashboard
- Check token audience/authorized parties
- Review Clerk SDK configuration

---

## Files Modified

1. `frontend/src/components/AuthProvider.tsx` - Wait for Clerk, check sign-in state
2. `frontend/src/services/api/client.ts` - Enhanced logging and error handling
3. `backend/src/zebu/adapters/auth/clerk_adapter.py` - Log Clerk rejection reasons
4. `backend/src/zebu/adapters/inbound/api/dependencies.py` - Log auth flow

---

## Next Steps

1. **Run E2E test** with new diagnostics to capture detailed logs
2. **Analyze logs** to confirm which hypothesis is correct
3. **Implement targeted fix** based on findings
4. **Validate fix** with full E2E test suite (all 22 tests should pass)
5. **Document solution** in this file

---

## Success Criteria

- [ ] Portfolio creation POST request succeeds (201 Created)
- [ ] Backend logs show `Clerk auth status: SIGNED_IN`
- [ ] Frontend logs show successful token retrieval
- [ ] All 22 E2E tests pass
- [ ] Manual curl test succeeds with valid Clerk token

---

## Notes for Next Developer

### If Logs Show "User not signed in"

The Clerk session from auth.setup.ts isn't persisting. Check:
```bash
# Verify storage state file exists and has content
cat frontend/playwright/.auth/user.json | jq '.cookies | length'

# Should show cookies including __clerk_db_jwt
```

If no cookies, the auth setup isn't working. Review `frontend/tests/e2e/setup/auth.setup.ts`.

### If Logs Show "getToken() returned null"

Clerk SDK issue. Possible solutions:
1. Call `await session.reload()` before `getToken()`
2. Use `await session.getToken({ template: "default" })`  
3. Check Clerk session expiration (default: 7 days, can be shorter)

### If All Else Fails: E2E Mode Workaround

Can implement E2E_TEST_MODE environment variable to use InMemoryAuthAdapter for E2E tests:
- Backend: Modify `get_auth_port()` to check `E2E_TEST_MODE` env var
- Frontend: Configure API client to send known test token
- Trade-off: Doesn't test real Clerk integration, but unblocks E2E tests

---

## Security Considerations

- All token logging uses safe previews (first/last 10 chars only)
- Logs never expose full tokens or secrets
- Diagnostic logging should be removed or made conditional (DEBUG mode) in production
- Consider using structlog for backend to filter sensitive data

---

## Conclusion

Implemented comprehensive diagnostic logging throughout the authentication flow. The next step is to run E2E tests and analyze the logs to confirm the root cause. Based on the most likely hypothesis (Clerk not fully initialized), the fix of waiting for `isLoaded` in AuthProvider should resolve the issue. If not, the detailed logs will reveal the actual problem for targeted fixing.

The changes are defensive and improve the robustness of the authentication flow even if they don't completely fix the issue. They will significantly speed up future debugging of authentication problems.
