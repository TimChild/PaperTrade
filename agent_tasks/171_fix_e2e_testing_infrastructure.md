# Task 171: Fix E2E Testing Infrastructure & Make Failures Debuggable

**Priority**: HIGH (blocking further development)  
**Agent**: frontend-swe  
**Estimated effort**: 4-6 hours  
**Created**: 2026-01-24

## Problem Statement

**15 out of 22 E2E tests are failing** with backend request timeouts. This is a **pre-existing issue** that has persisted across multiple PRs. The root cause is unclear because:
- ❌ No helpful error messages in terminal output
- ❌ No validation that environment is correctly configured before tests run
- ❌ Backend requests timeout (10s) but backend receives no requests (no logs)
- ❌ Manual testing works fine, only automated E2E tests fail
- ❌ Authentication test passes, but portfolio creation POST requests fail

**This keeps happening and we need to STOP it from recurring.**

## Investigation Summary (So Far)

### What We Know
- **Failure pattern**: All 15 failures are portfolio creation flows timing out
- **Error message**: Form displays "timeout of 10000ms exceeded" (Axios timeout)
- **Backend behavior**: No POST requests logged during E2E tests (only health checks)
- **Manual testing**: Works perfectly via browser and Playwright MCP
- **Authentication**: Auth setup test (#1) passes
- **Test environment**: Running with 5 parallel workers locally (1 in CI)
- **Services**: All Docker containers healthy (PostgreSQL, Redis, Backend, Frontend)

### What We've Ruled Out
- ✅ Not a code issue - reverted all recent changes, still fails
- ✅ Not a resource issue - backend using only 12% memory
- ✅ Not a service health issue - all containers healthy
- ✅ Not navigation code - navigation works when API succeeds

### Likely Root Causes
1. **Clerk authentication tokens** not properly attached to POST requests in E2E environment
2. **Backend not receiving requests** due to routing, CORS, or network issues
3. **Environment variables** not properly loaded or configured
4. **Test isolation** issues with parallel workers

## Required Fixes

### 1. Pre-Test Environment Validation ⭐ CRITICAL

Create a validation script that runs BEFORE E2E tests start:

**File**: `frontend/tests/e2e/validate-environment.ts` (or similar)

Must validate:
- ✅ All required environment variables are set (CLERK_SECRET_KEY, CLERK_PUBLISHABLE_KEY, E2E_CLERK_USER_EMAIL)
- ✅ Backend is healthy and responding (`GET /health`)
- ✅ Backend accepts authenticated requests (`GET /api/v1/portfolios` with test token)
- ✅ PostgreSQL is accessible
- ✅ Redis is accessible
- ✅ Clerk testing token is valid and can be used for requests
- ✅ Frontend is serving correctly

**Integration**: Update `playwright.config.ts` to run this validation in `globalSetup`

### 2. Enhanced Logging & Error Messages ⭐ CRITICAL

**During test execution**, we need to see:
- What environment variables are set (redact secrets, show presence)
- What authentication token is being used (first/last 4 chars only)
- What backend URL requests are going to
- What HTTP status codes are returned (if any)
- What network errors occur (CORS, DNS, connection refused, etc.)

**Implementation areas**:
- `frontend/src/services/api/client.ts` - Add debug logging for requests/responses when in test environment
- `frontend/tests/e2e/helpers.ts` - Log each step of portfolio creation
- Test files - Add console.log statements before critical operations
- Playwright config - Ensure all console messages are captured and displayed

**Environment detection**: Use `process.env.PLAYWRIGHT_TEST` or similar to enable verbose logging only during tests

### 3. Authentication Token Debugging

Create a test utility that:
1. Retrieves the Clerk testing token
2. Makes a direct API call to backend with that token
3. Logs the full request/response (including headers)
4. Verifies token is accepted by backend

**File**: `frontend/tests/e2e/debug-auth.ts`

This should be run as part of environment validation.

### 4. Test Isolation & Cleanup

Ensure each test:
- Uses unique portfolio names (timestamps)
- Cleans up created resources (or uses separate test database)
- Doesn't interfere with parallel tests

Consider:
- Reducing parallel workers to 1 temporarily to rule out race conditions
- Adding test cleanup hooks
- Using separate database schemas per worker (if possible)

### 5. Backend Request Logging

**Backend side** (`backend/zebu/infrastructure/middleware/logging_middleware.py`):
- Ensure ALL requests are logged (even failed auth)
- Log request headers (sanitized)
- Log request body (sanitized)
- Log response status and time

**Check if**:
- Requests are being blocked before reaching logging middleware
- CORS is rejecting requests silently
- Authentication middleware is rejecting without logging

### 6. Network Connectivity Validation

Add a simple curl-based test that:
```bash
# From frontend container/process, can we reach backend?
curl -v http://localhost:8000/health
curl -v http://localhost:8000/api/v1/portfolios -H "Authorization: Bearer $TEST_TOKEN"
```

This should be in the validation script.

## Success Criteria

1. ✅ All 22 E2E tests pass consistently (run 3 times to confirm)
2. ✅ Validation script catches configuration errors BEFORE tests run
3. ✅ When a test fails, logs clearly show:
   - What request was made
   - What authentication was used
   - What response/error occurred
   - What the backend logged (or didn't log)
4. ✅ Documentation updated with:
   - How to run E2E tests
   - How to debug E2E test failures
   - Common failure modes and solutions
5. ✅ CI pipeline updated to use validation script

## Implementation Approach

### Phase 1: Diagnosis (1-2 hours)
1. Create validation script (`validate-environment.ts`)
2. Create auth debugging utility (`debug-auth.ts`)
3. Run validation and capture detailed output
4. Identify EXACT failure point (e.g., "Clerk token not in request headers")

### Phase 2: Fix Root Cause (1-2 hours)
Based on diagnosis:
- Fix authentication token attachment
- Fix backend CORS/routing
- Fix environment variable loading
- Fix test isolation

### Phase 3: Enhanced Logging (1 hour)
1. Add debug logging to API client (test env only)
2. Add logging to test helpers
3. Update Playwright config to show all logs
4. Update backend to log failed auth attempts

### Phase 4: Validation & Documentation (1 hour)
1. Run full test suite 3 times - all should pass
2. Document validation script usage
3. Document debugging process
4. Update CI to use validation
5. Create PR with comprehensive description

## Files to Modify/Create

### New Files
- `frontend/tests/e2e/validate-environment.ts` - Pre-test validation
- `frontend/tests/e2e/debug-auth.ts` - Auth debugging utility
- `frontend/tests/e2e/README.md` - E2E testing documentation

### Modified Files
- `frontend/playwright.config.ts` - Integrate validation script
- `frontend/src/services/api/client.ts` - Add debug logging
- `frontend/tests/e2e/global-setup.ts` - Enhanced error messages
- `frontend/tests/e2e/helpers.ts` - Add logging to helper functions
- `backend/zebu/infrastructure/middleware/logging_middleware.py` - Log failed auth
- `Taskfile.yml` - Maybe add `task test:e2e:validate` command

## Testing Checklist

Before marking complete:
- [ ] Run validation script standalone - should pass
- [ ] Run validation script with missing env var - should fail clearly
- [ ] Run validation script with backend down - should fail clearly
- [ ] Run single E2E test - should pass with clear logs
- [ ] Run full E2E suite - all 22 tests should pass
- [ ] Run E2E suite 3 times - should pass consistently
- [ ] Introduce intentional failure - logs should clearly show why
- [ ] Test in CI environment - should pass there too

## Expected Outcome

After this task:
1. **All E2E tests pass reliably** - no more mysterious timeouts
2. **Failures are self-diagnosing** - logs tell you exactly what went wrong
3. **Configuration errors caught early** - before wasting time on test runs
4. **Future debugging is fast** - clear logging shows what's happening
5. **This doesn't happen again** - validation prevents similar issues

## Notes for Agent

**Be systematic**:
- Don't guess at the problem - diagnose with logging first
- Don't fix multiple things at once - fix one, test, then next
- Don't assume environment is correct - validate everything

**Focus on debuggability**:
- Every failure should produce a clear error message
- Logs should tell the story of what happened
- Validation should catch problems before they cause failures

**Think prevention**:
- How do we prevent this from happening again?
- What assumptions were we making that turned out false?
- What checks should run automatically?

**Document your findings**:
- What was the actual root cause?
- What fixed it?
- How to debug similar issues in future?

## Related Files

- Error context: `frontend/test-results/portfolio-creation-Portfol-048a1-te-to-portfolio-detail-page-chromium/error-context.md`
- Current E2E config: `frontend/playwright.config.ts`
- Auth setup: `frontend/tests/e2e/global-setup.ts`
- API client: `frontend/src/services/api/client.ts`
- Backend logging: `backend/zebu/infrastructure/middleware/logging_middleware.py`
