# Task 055: Clerk Authentication - Complete E2E Implementation

**Agent**: frontend-swe (with backend modification authority)
**Status**: Not Started
**Created**: 2026-01-04
**Effort**: 1-2 days
**Priority**: CRITICAL
**Replaces**: Task #054 (PR #71 has been problematic)

## Objective

Implement Clerk authentication that works end-to-end, including:
1. Frontend Clerk integration (React)
2. Backend JWT validation fixes (if needed)
3. **E2E tests that actually pass in CI**

**CRITICAL**: This task is NOT complete until E2E tests pass locally AND you've verified the implementation works end-to-end with real Clerk tokens.

## Background

Previous attempts (PR #71) failed because:
- E2E test setup was incorrect (wrong Clerk testing patterns)
- Backend JWT validation used non-existent SDK methods
- Test mode bypass approaches were fragile

**You have authority to modify backend code** if needed to fix authentication issues.

## Key Resources

### Documentation Access
- **You can access clerk.com directly** - Use their official docs:
  - Playwright testing: https://clerk.com/docs/testing/playwright
  - React quickstart: https://clerk.com/docs/quickstarts/react
  - Backend API: https://clerk.com/docs/reference/backend-api

### Local Reference Document
- `clerk-implementation-info.md` (root of repo) - Contains critical implementation details and common pitfalls discovered during debugging

### Environment Variables Available
```bash
# Frontend
VITE_CLERK_PUBLISHABLE_KEY=pk_test_...  # In frontend/.env.local

# Backend
CLERK_SECRET_KEY=sk_test_...  # In .env (root)

# E2E Testing
E2E_CLERK_USER_EMAIL=...  # Test user email (you may need to create this)
```

## Critical Implementation Details

### 1. Backend JWT Validation (READ CAREFULLY)

The `clerk-backend-api` Python SDK does NOT have a `verify_token()` method. You MUST use:

```python
from clerk_backend_api import Clerk
from clerk_backend_api.security.types import AuthenticateRequestOptions

class SimpleRequest:
    def __init__(self, token: str) -> None:
        self.headers = {
            "authorization": f"Bearer {token}",
            "Authorization": f"Bearer {token}",  # Both cases needed!
        }

clerk = Clerk(bearer_auth=secret_key)
request_state = clerk.authenticate_request(
    request=SimpleRequest(token),
    options=AuthenticateRequestOptions()
)

# User ID is in payload['sub'], NOT request_state.user_id
if request_state.payload:
    user_id = request_state.payload.get('sub')
```

**Check existing backend implementation** at `backend/src/zebu/adapters/auth/clerk_adapter.py` and fix if it uses wrong patterns.

### 2. E2E Testing with @clerk/testing

**DO NOT** use test bypass modes or mock Clerk. Use the official `@clerk/testing` package:

```bash
npm install -D @clerk/testing
```

**Global Setup** (`frontend/tests/e2e/global-setup.ts`):
```typescript
import { clerkSetup } from '@clerk/testing/playwright'

export default async function globalSetup() {
  await clerkSetup()  // MUST be called first
}
```

**Fixtures** (`frontend/tests/e2e/fixtures.ts`):
```typescript
import { test as base } from '@playwright/test'
import { setupClerkTestingToken } from '@clerk/testing/playwright'

export const test = base.extend({
  page: async ({ page }, use) => {
    await setupClerkTestingToken({ page })
    await use(page)
  },
})

export { expect } from '@playwright/test'
```

**In Tests** - Use email-based sign-in (NOT password):
```typescript
import { clerk } from '@clerk/testing/playwright'
import { test, expect } from './fixtures'

test('authenticated flow', async ({ page }) => {
  // Navigate FIRST - Clerk must be loaded
  await page.goto('/')
  await page.waitForLoadState('networkidle')

  // Sign in using email (creates temporary token via API)
  await clerk.signIn({
    page,
    emailAddress: process.env.E2E_CLERK_USER_EMAIL,  // NOT signInParams!
  })

  // Now user is authenticated
  await page.waitForURL('**/dashboard')
  // ... rest of test
})
```

**IMPORTANT**:
- Navigate to the app BEFORE calling `clerk.signIn()` - Clerk needs to be loaded first
- Use `emailAddress` parameter, NOT `signInParams` with password strategy
- Password strategy often triggers 2FA/email verification
- Email-based sign-in creates a temporary token instantly

### 3. Test User Setup

You need a test user in Clerk. Either:
1. Create via Clerk Dashboard
2. Create via API:
```bash
curl -X POST https://api.clerk.com/v1/users \
  -H "Authorization: Bearer $CLERK_SECRET_KEY" \
  -H "Content-Type: application/json" \
  -d '{"email_address": ["test-e2e@zebu.dev"]}'
```

The user should NOT have 2FA enabled.

## Implementation Steps

### Step 1: Verify/Fix Backend Auth

1. Check `backend/src/zebu/adapters/auth/clerk_adapter.py`
2. Ensure it uses `authenticate_request()` not `verify_token()`
3. Ensure user ID comes from `payload['sub']`
4. Ensure `SimpleRequest` has both header cases
5. Run backend tests: `task test:backend`

### Step 2: Frontend Clerk Integration

1. Ensure `@clerk/clerk-react` is installed
2. Wrap app in `<ClerkProvider>` in `main.tsx`
3. Use `<SignedIn>/<SignedOut>` guards in `App.tsx`
4. Add token injection to API requests via `useAuth().getToken()`
5. Run frontend tests: `task test:frontend`

### Step 3: E2E Test Setup

1. Install `@clerk/testing`: `npm install -D @clerk/testing`
2. Create/update `frontend/tests/e2e/global-setup.ts` with `clerkSetup()`
3. Create/update `frontend/tests/e2e/fixtures.ts` with `setupClerkTestingToken()`
4. Update `playwright.config.ts` to use global setup
5. Create test user in Clerk if needed
6. Set `E2E_CLERK_USER_EMAIL` environment variable

### Step 4: Update E2E Tests

1. Import `clerk` from `@clerk/testing/playwright`
2. Import `test` from your fixtures (not from `@playwright/test`)
3. Update each test to:
   - Navigate to app first
   - Call `clerk.signIn({ page, emailAddress })`
   - Wait for authentication to complete
   - Then run test assertions

### Step 5: Local Validation (REQUIRED)

**Before marking this task complete, you MUST:**

1. Start services: `task docker:up`
2. Start backend: `task dev:backend` (in one terminal)
3. Start frontend: `task dev:frontend` (in another terminal)
4. Run E2E tests: `task test:e2e`
5. **ALL E2E tests must pass**

Also run:
```bash
task lint:frontend
task test:frontend
task lint:backend
task test:backend
```

## Files to Modify/Create

### Frontend
- `frontend/package.json` - Add `@clerk/testing` dev dependency
- `frontend/src/main.tsx` - ClerkProvider wrapper
- `frontend/src/App.tsx` - SignedIn/SignedOut guards, auth UI
- `frontend/src/hooks/useAuthenticatedApi.ts` - Token injection
- `frontend/tests/e2e/global-setup.ts` - Clerk test setup
- `frontend/tests/e2e/fixtures.ts` - Test fixtures with auth
- `frontend/playwright.config.ts` - Global setup config
- `frontend/tests/e2e/*.spec.ts` - Update tests to use auth

### Backend (if fixes needed)
- `backend/src/zebu/adapters/auth/clerk_adapter.py` - JWT validation
- `backend/docker-compose.yml` - Ensure CLERK_SECRET_KEY in env

### Environment
- `frontend/.env.local` - VITE_CLERK_PUBLISHABLE_KEY (already exists)
- `.env` - CLERK_SECRET_KEY, E2E_CLERK_USER_EMAIL

## Success Criteria

- [ ] Backend validates Clerk JWT tokens correctly
- [ ] Frontend shows sign-in UI for unauthenticated users
- [ ] Frontend shows dashboard for authenticated users
- [ ] API requests include Bearer token
- [ ] `task test:backend` - All tests pass
- [ ] `task test:frontend` - All tests pass
- [ ] `task lint:backend` - No errors
- [ ] `task lint:frontend` - No errors
- [ ] **`task test:e2e` - ALL TESTS PASS** (most important!)

## What NOT to Do

1. ❌ Do NOT use test bypass modes (`?e2e-test=true` URL params)
2. ❌ Do NOT mock Clerk in E2E tests - use `@clerk/testing`
3. ❌ Do NOT use `clerk.verify_token()` - it doesn't exist
4. ❌ Do NOT use password sign-in strategy in E2E tests
5. ❌ Do NOT mark task complete until E2E tests pass locally

## Debugging Tips

If E2E tests fail:

1. Check if Clerk is loaded:
```typescript
await page.evaluate(() => ({
  clerkExists: typeof window.Clerk !== 'undefined',
  clerkLoaded: window.Clerk?.loaded,
}))
```

2. Check backend logs:
```bash
docker logs zebu-backend --tail 100 | grep -i "auth\|clerk"
```

3. Check if `CLERK_SECRET_KEY` is in backend container:
```bash
docker exec zebu-backend env | grep CLERK
```

4. Test backend API directly with a token

## References

- Clerk Playwright Testing: https://clerk.com/docs/testing/playwright
- Clerk React SDK: https://clerk.com/docs/quickstarts/react
- Local implementation notes: `clerk-implementation-info.md`
- Architecture: `architecture_plans/phase3-refined/phase3b-authentication.md`
