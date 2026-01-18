# Task 161: Investigate Portfolio Creation Timeout Issue

**Agent**: backend-swe
**Priority**: Critical
**Created**: 2026-01-18
**Context**: During E2E testing of weekend price fetching fixes (PR #153), discovered that ALL portfolio creation requests timeout. This appears to be a separate issue from the weekend price logic.

## Problem Summary

POST requests to `/api/v1/portfolios` timeout after 10 seconds (now 60s workaround), never reaching the backend endpoint. This affects ALL E2E tests that create portfolios.

### Symptoms

1. **E2E Tests**: 15/22 tests fail with `TimeoutError: page.waitForURL: Timeout 10000ms exceeded`
2. **Backend Logs**: Show "Clerk auth status: AuthStatus.SIGNED_OUT" for POST requests
3. **Frontend**: Shows 2 timeout alerts in create portfolio dialog
4. **GET Requests**: Work perfectly fine (<1s response time)
5. **POST Requests**: Never complete, hang indefinitely

### Evidence

**Backend logs show POST arrives but auth fails:**
```
2026-01-18T22:14:30.971411Z [info] Request started
  method=POST path=/api/v1/portfolios
Clerk auth status: AuthStatus.SIGNED_OUT
2026-01-18T22:14:30.988570Z [info] Request completed
  status_code=401 duration_seconds=0.017
```

**E2E test error:**
```
TimeoutError: page.waitForURL: Timeout 10000ms exceeded.
waiting for navigation to "**/portfolio/*" until "load"
```

**Manual curl test (from main branch):**
```bash
curl -X POST "http://localhost:8000/api/v1/portfolios" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <clerk-key>" \
  -d '{"name":"Test","description":"Test"}' \
  --max-time 15
# Returns: 401 Unauthorized after 0.029s
```

### Timeline

- **Earlier today**: User reports "this was working and all E2E tests were passing earlier today"
- **Current state**: All portfolio creation fails, on both main branch and PR #153 branch
- **Scope**: Issue is NOT related to weekend price changes (verified on main branch)

## Investigation Scope

You have **full authority** to investigate this thoroughly:

1. **Authentication Layer**
   - Why does Clerk auth return `AuthStatus.SIGNED_OUT` for POST requests?
   - Check ClerkAuthAdapter token verification logic
   - Compare GET vs POST request authentication flow
   - Review how E2E tests obtain and send JWT tokens

2. **Request Flow**
   - Trace exact path from frontend → nginx (if any) → backend
   - Check if middleware is blocking/delaying POST requests
   - Review CORS configuration for POST requests
   - Examine FastAPI dependency injection for auth

3. **E2E Test Setup**
   - Review `frontend/tests/e2e/global-setup.ts` - Clerk testing token creation
   - Review `frontend/tests/e2e/setup/auth.setup.ts` - Authentication state
   - Check if auth cookies/tokens are properly stored/loaded
   - Verify Clerk testing token configuration

4. **Docker Networking**
   - Check if frontend container can reach backend properly
   - Verify no network policies blocking POST specifically
   - Review docker-compose networking configuration

5. **Recent Changes**
   - Search git history for recent changes to auth, middleware, or portfolio creation
   - Check if any dependency updates broke Clerk integration
   - Review recent commits to auth-related files

## Success Criteria

1. **Root Cause Identified**: Clear explanation of WHY POST requests fail authentication
2. **Replication Steps**: Exact curl/test commands that reproduce the issue
3. **Fix Implemented**: Portfolio creation works in E2E tests
4. **Tests Pass**: All 22 E2E tests pass, including portfolio creation flows
5. **Documentation**: Clear explanation in agent progress doc

## Testing Requirements

**Must verify:**
- Portfolio creation via E2E test: `task test:e2e -- tests/e2e/portfolio-creation.spec.ts`
- Manual API test: `curl -X POST http://localhost:8000/api/v1/portfolios ...`
- All E2E tests: `task test:e2e`
- Backend logs show successful POST with status 200/201

## Key Files to Investigate

```
backend/src/zebu/adapters/auth/clerk_adapter.py          # Auth verification
backend/src/zebu/adapters/inbound/api/dependencies.py    # DI setup
backend/src/zebu/adapters/inbound/api/v1/portfolios.py   # POST endpoint
backend/src/zebu/infrastructure/middleware/              # Middleware
frontend/src/services/api/client.ts                      # API client
frontend/tests/e2e/global-setup.ts                       # Clerk token setup
frontend/tests/e2e/setup/auth.setup.ts                   # Auth state
docker-compose.yml                                       # Networking
```

## Important Notes

- **GET requests work fine** - This suggests selective authentication failure for POST
- **Issue exists on main branch** - NOT introduced by weekend price changes
- **Temporary workaround**: Timeout increased to 60s in frontend client (still fails)
- **User context**: "This was working earlier today" - suggests recent regression
- **Clerk auth status**: Returns `SIGNED_OUT` instead of `SIGNED_IN` for POST requests

## Constraints

- Must not break existing authentication for GET requests
- Must maintain Clerk integration (don't replace with mock auth)
- Must work in both local Docker and CI environments
- Solution must be production-ready (no test-only hacks)

## Deliverables

1. **Agent Progress Doc**: `agent_progress_docs/YYYY-MM-DD_HH-MM-SS_portfolio-creation-timeout-fix.md`
2. **Pull Request**: Fix with clear explanation and test coverage
3. **Replication Steps**: Document exact issue reproduction
4. **Root Cause Analysis**: Clear technical explanation

## Environment

- Backend: Python 3.13+, FastAPI, Clerk Backend SDK
- Frontend: React 18+, TypeScript, Clerk React SDK
- Auth: Clerk with testing tokens for E2E
- Database: PostgreSQL (papertrade_dev)
- Test User: test-e2e@papertrade.dev

## Questions to Answer

1. Why does `AuthStatus.SIGNED_OUT` appear for POST but not GET?
2. What changed between "working earlier today" and now?
3. How do E2E tests obtain JWT tokens from Clerk?
4. Is the Clerk testing token being properly included in POST requests?
5. Does the auth middleware handle POST differently than GET?

---

**You have full authority to investigate independently. Follow the evidence wherever it leads. Document your findings thoroughly.**
