# E2E Testing Guide

## Running Tests

```bash
# From project root
task test:e2e

# Or from frontend directory
cd frontend
npm run test:e2e
```

## Prerequisites

1. **Docker services running**: `task docker:up:all`
2. **Environment variables set** (in `.env` file):
   - `CLERK_SECRET_KEY` - Clerk API secret key
   - `CLERK_PUBLISHABLE_KEY` or `VITE_CLERK_PUBLISHABLE_KEY` - Clerk publishable key
   - `E2E_CLERK_USER_EMAIL` - Email of test user in Clerk

## Common Issues

### "TOKEN_INVALID" or authentication failures

The E2E tests use Clerk's testing framework which requires:
1. Valid `CLERK_SECRET_KEY` in environment
2. Test user email exists in your Clerk instance
3. Clerk's `@clerk/testing/playwright` package properly configured

**Check**: Run `task docker:logs:backend` to see auth errors in backend logs.

### Tests timeout waiting for API responses

1. Check backend is running: `curl http://localhost:8000/health`
2. Check frontend is running: `curl http://localhost:5173`
3. Check browser console in Playwright HTML report for errors

## Test Structure

- `setup/auth.setup.ts` - Authenticates once, saves state
- `fixtures.ts` - Extends Playwright test with Clerk testing token setup
- `*.spec.ts` - Individual test files

Tests use saved authentication state to avoid re-authenticating for each test.
