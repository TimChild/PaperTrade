# Clerk Authentication Implementation Guide

**Last Updated**: January 4, 2026
**Status**: Working implementation with E2E tests

---

## Overview

This project uses Clerk for authentication in both frontend (React) and backend (FastAPI). This document captures critical implementation details and common pitfalls discovered during integration.

## Architecture

### Frontend Stack
- `@clerk/clerk-react` v6.x - React components and hooks
- `@clerk/testing` v4.x - Playwright E2E testing support

### Backend Stack
- `clerk-backend-api` v4.2.0 - Python SDK for JWT validation
- FastAPI with custom auth dependency

---

## Critical Implementation Details

### 1. Backend JWT Validation (MOST IMPORTANT)

#### ❌ WRONG - This method doesn't exist:
```python
from clerk_backend_api import Clerk

clerk = Clerk(bearer_auth=secret_key)
request_state = clerk.verify_token(token)  # ❌ NO SUCH METHOD
```

#### ✅ CORRECT - Use authenticate_request():
```python
from clerk_backend_api import Clerk
from clerk_backend_api.security.types import AuthenticateRequestOptions

class SimpleRequest:
    def __init__(self, token: str) -> None:
        # Must have both cases - Clerk checks both
        self.headers = {
            "authorization": f"Bearer {token}",
            "Authorization": f"Bearer {token}",
        }

clerk = Clerk(bearer_auth=secret_key)
request = SimpleRequest(token)
request_state = clerk.authenticate_request(
    request=request,
    options=AuthenticateRequestOptions()
)

# User ID is in the JWT payload 'sub' claim
if request_state.payload:
    user_id = request_state.payload.get('sub')
```

**Key Points:**
- The Clerk Python SDK does NOT have a `verify_token()` method
- Must use `authenticate_request()` which expects a request-like object
- The request object must have `.headers` dictionary with Authorization header
- User ID comes from `request_state.payload['sub']`, NOT `request_state.user_id`
- The `request_state` has properties: `status`, `reason`, `token`, `payload`
- Check `request_state.status == AuthStatus.SIGNED_IN` for successful auth

### 2. Environment Variables

#### Backend Requirements:
```bash
CLERK_SECRET_KEY=sk_test_xxx...  # Required for JWT validation
```

#### Frontend Requirements:
```bash
VITE_CLERK_PUBLISHABLE_KEY=pk_test_xxx...  # Required for Clerk client
```

#### E2E Test Requirements:
```bash
CLERK_SECRET_KEY=sk_test_xxx...           # For creating sign-in tokens
E2E_CLERK_USER_EMAIL=test@example.com     # Test user email
E2E_CLERK_USER_PASSWORD=xxx               # Not used with email-based sign-in
```

**Critical:** The backend Docker container MUST have `CLERK_SECRET_KEY` in its environment. Add to `docker-compose.yml`:

```yaml
backend:
  environment:
    CLERK_SECRET_KEY: ${CLERK_SECRET_KEY}
```

### 3. E2E Testing with Clerk

#### ❌ WRONG - Password strategy triggers 2FA:
```typescript
await clerk.signIn({
  page,
  signInParams: {
    strategy: 'password',
    identifier: email,
    password: password,
  },
})
```

This fails because:
- Clerk instances may require email verification as a second factor
- The "magic code" 424242 doesn't work for all Clerk instances
- Tests will timeout waiting for email verification

#### ✅ CORRECT - Email-based sign-in creates temporary tokens:
```typescript
import { clerk, clerkSetup, setupClerkTestingToken } from '@clerk/testing/playwright'

// 1. In global-setup.ts:
await clerkSetup()  // Must be called FIRST

// 2. In fixtures.ts:
export const test = base.extend({
  page: async ({ page }, use) => {
    await setupClerkTestingToken({ page })
    await use(page)
  },
})

// 3. In tests:
const email = process.env.E2E_CLERK_USER_EMAIL

// Navigate FIRST - Clerk must be loaded
await page.goto('/')
await page.waitForLoadState('networkidle')

// THEN sign in using email (creates sign-in token automatically)
await clerk.signIn({
  page,
  emailAddress: email,  // Not signInParams!
})

// User is now signed in - check URL or wait for navigation
if (page.url().includes('/dashboard')) {
  // Already redirected
} else {
  await page.waitForURL('**/dashboard', { timeout: 10000 })
}
```

**Key Points:**
- `clerkSetup()` MUST be called before `setupClerkTestingToken()`
- Navigate to the app BEFORE calling `clerk.signIn()` - Clerk needs to be loaded
- Use `emailAddress` parameter, NOT `signInParams` with password
- This creates a temporary sign-in token via Clerk API (requires `CLERK_SECRET_KEY`)
- The sign-in is instantaneous - no email verification needed

### 4. Clerk Testing Token Flow

When using `emailAddress` parameter, here's what happens:

```typescript
// Clerk's @clerk/testing library does this internally:
const clerkClient = createClerkClient({ secretKey: CLERK_SECRET_KEY })
const users = await clerkClient.users.getUserList({ emailAddress: [email] })
const user = users.data[0]

// Creates a temporary sign-in token (like a magic link)
const signInToken = await clerkClient.signInTokens.createSignInToken({
  userId: user.id,
  expiresInSeconds: 300,
})

// Then signs in using the token (strategy: 'ticket')
await page.evaluate(() => {
  await window.Clerk.client.signIn.create({
    strategy: 'ticket',
    ticket: signInToken.token,
  })
})
```

This bypasses email verification and 2FA entirely.

### 5. Common Error Messages and Solutions

#### "RequestState status=SIGNED_OUT, reason=SESSION_TOKEN_MISSING"
**Problem:** Clerk can't find the Authorization header
**Solution:** Check that `SimpleRequest.headers` includes both `"authorization"` and `"Authorization"` keys

#### "'Clerk' object has no attribute 'verify_token'"
**Problem:** Using non-existent method
**Solution:** Use `authenticate_request()` instead

#### "The Clerk Frontend API URL is required to bypass bot protection"
**Problem:** `clerkSetup()` not called before `setupClerkTestingToken()`
**Solution:** Ensure global-setup.ts calls `clerkSetup()` first

#### "Test timeout waiting for clerk.signIn()"
**Problem:** Either:
1. Page not loaded before sign-in (Clerk not initialized)
2. Using password strategy instead of email-based sign-in

**Solution:**
1. Navigate to app first: `await page.goto('/')`
2. Use `emailAddress` parameter: `clerk.signIn({ page, emailAddress })`

#### "page.waitForURL: Timeout waiting for /dashboard"
**Problem:** Using exact path instead of glob pattern
**Solution:** Use `await page.waitForURL('**/dashboard')` or check `page.url().includes('/dashboard')`

### 6. Test User Setup

Create a test user in Clerk Dashboard or via API:

```bash
# Using Clerk API
curl -X POST https://api.clerk.com/v1/users \
  -H "Authorization: Bearer $CLERK_SECRET_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "email_address": ["test-e2e@zebu.dev"],
    "password": "test-password",
    "skip_password_requirement": true
  }'
```

**Important:**
- User should NOT have 2FA enabled
- Use a test email (e.g., `+clerk_test` subaddress or dedicated test domain)
- Password is not needed for email-based sign-in in tests

### 7. Debugging Clerk Issues

#### Check if Clerk is loaded:
```typescript
await page.evaluate(() => ({
  clerkExists: typeof window.Clerk !== 'undefined',
  clerkLoaded: window.Clerk?.loaded,
  hasClient: !!window.Clerk?.client,
}))
```

#### Check authentication status:
```typescript
const sessionToken = await page.evaluate(() =>
  window.Clerk.session?.lastActiveToken?.getRawString()
)
console.log('Token:', sessionToken?.substring(0, 50))
```

#### Test backend API directly:
```typescript
const response = await page.evaluate(async (token) => {
  const res = await fetch('http://localhost:8000/api/v1/portfolios', {
    headers: { 'Authorization': `Bearer ${token}` },
  })
  return {
    status: res.status,
    body: await res.text(),
  }
}, sessionToken)
```

### 8. Backend Error Logging

Add detailed logging to debug token validation:

```python
import logging
logger = logging.getLogger(__name__)

try:
    request_state = self._clerk.authenticate_request(request, options)
    logger.info(f"Auth status: {request_state.status}")
    logger.info(f"Payload: {request_state.payload}")
except Exception as e:
    logger.error(f"Auth failed: {str(e)}")
    raise
```

Check logs:
```bash
docker logs zebu-backend --tail 100 | grep -i "auth\|clerk"
```

---

## Testing Checklist

When implementing or debugging Clerk authentication:

- [ ] Backend has `CLERK_SECRET_KEY` in environment
- [ ] Backend uses `authenticate_request()`, not `verify_token()`
- [ ] Backend extracts user ID from `payload['sub']`
- [ ] Backend `SimpleRequest` has both header cases
- [ ] Frontend has `VITE_CLERK_PUBLISHABLE_KEY`
- [ ] E2E global-setup calls `clerkSetup()` first
- [ ] E2E fixtures call `setupClerkTestingToken({ page })`
- [ ] E2E tests navigate before calling `clerk.signIn()`
- [ ] E2E tests use `emailAddress` parameter (not password strategy)
- [ ] Test user exists in Clerk with correct email
- [ ] Test user does NOT have 2FA enabled

---

## Working Example

See the complete working implementation:
- Backend: `backend/src/zebu/adapters/auth/clerk_adapter.py`
- Frontend fixtures: `frontend/tests/e2e/fixtures.ts`
- Global setup: `frontend/tests/e2e/global-setup.ts`
- Example test: `frontend/tests/e2e/portfolio-creation.spec.ts`

---

## Performance Notes

- Sign-in with email-based tokens is fast (<2 seconds)
- Backend token validation adds ~50-100ms per request
- Clerk's testing mode doesn't count against rate limits

---

## Known Limitations

1. **Test data persistence**: Portfolios created during tests persist in the database. Either:
   - Clear database before test runs: `docker exec zebu-postgres psql -U zebu -d zebu_dev -c "TRUNCATE TABLE transactions, portfolios CASCADE;"`
   - Make tests independent (don't expect specific UI states)

2. **Parallel test execution**: Tests run in parallel, creating multiple portfolios. Dashboard shows the first one, not necessarily the one just created by that test.

3. **Clerk development keys**: Warning message appears in browser console. This is expected and can be ignored in development.

---

## Additional Resources

- Clerk Playwright Testing: https://clerk.com/docs/testing/playwright
- Clerk Python SDK: https://github.com/clerk/clerk-sdk-python
- Backend API Reference: https://clerk.com/docs/reference/backend-api

---

## Troubleshooting Quick Reference

| Symptom | Likely Cause | Solution |
|---------|-------------|----------|
| 401 Unauthorized from backend | Missing CLERK_SECRET_KEY | Add to docker-compose.yml |
| "'Clerk' object has no attribute 'verify_token'" | Wrong SDK method | Use `authenticate_request()` |
| "Invalid or expired token" | User ID extraction wrong | Get from `payload['sub']` |
| "SESSION_TOKEN_MISSING" | Header format wrong | Add both header cases |
| Test timeout at `clerk.signIn()` | Page not loaded first | Navigate before sign-in |
| 2FA/email verification required | Using password strategy | Use email-based sign-in |
| "Clerk Frontend API URL required" | Setup order wrong | Call `clerkSetup()` first |

---

*This document is based on actual debugging of PR #71 and represents the working implementation as of January 4, 2026.*
