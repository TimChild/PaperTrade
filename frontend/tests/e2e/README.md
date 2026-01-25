# E2E Testing with Playwright

This directory contains end-to-end (E2E) tests for the Zebu application using [Playwright](https://playwright.dev/).

## Overview

E2E tests validate the complete user workflow from the frontend through to the backend, ensuring that:
- Authentication works correctly
- Users can create and manage portfolios
- Trading functionality works end-to-end
- Analytics and reporting are accurate
- UI components behave correctly

## Prerequisites

Before running E2E tests, ensure:

1. **Docker services are running**: PostgreSQL, Redis, Backend, Frontend
   ```bash
   task docker:up:all
   ```

2. **Environment variables are set** (in `frontend/.env.development` or as environment variables):
   - `CLERK_SECRET_KEY` - Clerk API secret key
   - `CLERK_PUBLISHABLE_KEY` or `VITE_CLERK_PUBLISHABLE_KEY` - Clerk publishable key
   - `E2E_CLERK_USER_EMAIL` - Email of test user in Clerk

3. **Playwright browsers installed**:
   ```bash
   cd frontend
   npx playwright install chromium
   ```

## Running Tests

### Run all E2E tests
```bash
# From project root
task test:e2e

# Or from frontend directory
cd frontend
npm run test:e2e
```

### Validate E2E environment (without running tests)
```bash
# From project root  
task test:e2e:validate

# Or from frontend directory
cd frontend
npx tsx tests/e2e/utils/test-validation.ts
```

This validates that all services and configuration are correct before running tests.

### Debug authentication issues
```bash
# From project root
task test:e2e:debug-auth

# Or from frontend directory
cd frontend
npx tsx tests/e2e/utils/debug-auth.ts
```

This runs a detailed authentication diagnostic showing token info and API requests.

### Run tests with UI (interactive mode)
```bash
task test:e2e:ui

# Or from frontend directory
npm run test:e2e:ui
```

### Run tests in headed mode (see browser)
```bash
cd frontend
npm run test:e2e:headed
```

### Run specific test file
```bash
cd frontend
npx playwright test portfolio-creation.spec.ts
```

### Run specific test by name
```bash
cd frontend
npx playwright test -g "should create portfolio"
```

## Test Structure

```
tests/e2e/
├── setup/
│   └── auth.setup.ts          # Authentication setup (runs first)
├── utils/
│   ├── validate-environment.ts # Environment validation
│   └── debug-auth.ts           # Authentication debugging
├── fixtures.ts                 # Shared test fixtures
├── helpers.ts                  # Shared helper functions
├── global-setup.ts             # Global setup (Clerk token creation)
├── *.spec.ts                   # Test files
└── README.md                   # This file
```

### Test Execution Flow

1. **Global Setup** (`global-setup.ts`)
   - Validates environment variables
   - Checks backend/frontend health
   - Creates Clerk testing token
   - Validates authenticated API access

2. **Setup Project** (`setup/auth.setup.ts`)
   - Authenticates test user via Clerk
   - Saves authentication state to `playwright/.auth/user.json`

3. **Test Projects** (Chromium, Firefox, Safari)
   - Load saved authentication state
   - Run tests in parallel (configurable)
   - Use shared fixtures and helpers

## Environment Validation

The E2E test suite includes comprehensive environment validation that runs before tests start:

### Validation Checks

✅ **Environment Variables**: Ensures all required Clerk variables are set  
✅ **Backend Health**: Verifies backend is running and responding  
✅ **Frontend Access**: Confirms frontend is accessible  
✅ **Clerk Token**: Validates testing token structure and format  
✅ **Authenticated Request**: Tests that backend accepts Clerk token  

### Validation Output

When validation passes:
```
================================================================================
E2E ENVIRONMENT VALIDATION REPORT
================================================================================

✅ PASSED (5 checks)
  ✓ All required environment variables are set
  ✓ Backend health check passed
  ✓ Frontend is accessible
  ✓ Clerk testing token is present and appears valid
  ✓ Authenticated API request succeeded

================================================================================
SUMMARY: 5 passed, 0 warnings, 0 failed
================================================================================
```

When validation fails:
```
================================================================================
E2E ENVIRONMENT VALIDATION REPORT
================================================================================

❌ FAILED (1 checks)
  ✗ Backend health check failed: connect ECONNREFUSED 127.0.0.1:8000
    {
      "url": "http://localhost:8000/health",
      "error": "connect ECONNREFUSED 127.0.0.1:8000",
      "code": "ECONNREFUSED"
    }

================================================================================
SUMMARY: 4 passed, 0 warnings, 1 failed
================================================================================
```

## Debugging Test Failures

### 1. Check Environment Validation

The environment validation runs automatically during test setup. Look for the validation report in the test output.

Common validation failures:
- **Missing environment variables**: Set required Clerk variables
- **Backend not running**: Start backend with `task docker:up:all`
- **Frontend not running**: Frontend should auto-start in Docker
- **Authentication failed**: Check Clerk secret key is correct

### 2. Enable Debug Logging

E2E tests automatically enable detailed logging in the API client. Look for `[API Client Debug]` messages in the console output:

```
[API Client Debug] Request starting { method: 'POST', url: '/portfolios', ... }
[API Client Debug] Auth token attached { tokenPrefix: 'eyJhbGc...', ... }
[API Client Debug] Response received { status: 201, ... }
```

### 3. Run Authentication Debug Utility

To diagnose authentication issues:

```bash
cd frontend
npx tsx tests/e2e/utils/debug-auth.ts
```

This will:
- Check if Clerk testing token is set
- Validate JWT structure
- Test backend health
- Make authenticated API request
- Display detailed request/response information

### 4. View Test Artifacts

When tests fail, Playwright automatically captures:

- **Screenshots**: `frontend/test-results/*/screenshot.png`
- **Videos**: `frontend/test-results/*/video.webm`
- **Traces**: `frontend/test-results/*/trace.zip`

View the HTML report:
```bash
cd frontend
npx playwright show-report
```

### 5. Check Backend Logs

View backend logs to see if requests are reaching the API:

```bash
docker logs papertrade-backend-1 -f
```

Look for:
- Request logs showing method, path, status code
- Authentication errors (401 Unauthorized)
- Application errors (500 Internal Server Error)

### 6. Common Issues and Solutions

#### Issue: "timeout of 10000ms exceeded"

**Symptoms**: Form submission times out, no API request visible in backend logs

**Possible causes**:
1. Backend not running or not reachable
2. Authentication token not attached to request
3. CORS blocking request
4. Network configuration issue

**Solutions**:
1. Verify backend health: `curl http://localhost:8000/health`
2. Check environment validation passed
3. Run auth debug utility
4. Check Docker network: `docker network inspect zebu-network`

#### Issue: "401 Unauthorized"

**Symptoms**: API request returns 401 status

**Possible causes**:
1. Clerk testing token expired or invalid
2. Backend Clerk configuration mismatch
3. Token not properly formatted in Authorization header

**Solutions**:
1. Verify `CLERK_SECRET_KEY` matches between frontend and backend
2. Check token is present: `echo $CLERK_TESTING_TOKEN`
3. Run auth debug utility to see full request/response
4. Verify backend Clerk middleware is configured correctly

#### Issue: "ERR_CONNECTION_REFUSED"

**Symptoms**: Frontend or backend not accessible

**Possible causes**:
1. Services not running
2. Port already in use
3. Docker container failed to start

**Solutions**:
1. Check Docker services: `docker ps`
2. Check service health: `docker ps --format "table {{.Names}}\t{{.Status}}"`
3. View logs: `docker logs <container-name>`
4. Restart services: `task docker:down && task docker:up:all`

## Test Best Practices

### 1. Use Test IDs

Always use `data-testid` attributes for selecting elements:

```tsx
// Component
<button data-testid="submit-portfolio-form-btn">Submit</button>

// Test
await page.getByTestId('submit-portfolio-form-btn').click()
```

### 2. Use Unique Names

Avoid test data conflicts by using timestamps:

```typescript
const portfolioName = `Test Portfolio ${Date.now()}`
```

### 3. Wait for Network Idle

After navigation, wait for network to settle:

```typescript
await page.goto('/dashboard')
await page.waitForLoadState('networkidle')
```

### 4. Handle Both States

Some buttons appear in different locations based on state:

```typescript
const headerButton = page.getByTestId('create-portfolio-header-btn')
const emptyStateButton = page.getByTestId('create-first-portfolio-btn')
const createButton = (await headerButton.isVisible()) ? headerButton : emptyStateButton
await createButton.click()
```

### 5. Use Fixtures

Leverage shared fixtures for common setup:

```typescript
import { test } from './fixtures'

test('my test', async ({ page }) => {
  // Authentication already handled by fixture
  await page.goto('/dashboard')
  // ...
})
```

## Configuration

### Playwright Config (`playwright.config.ts`)

Key settings:
- **baseURL**: `http://localhost:5173` (frontend)
- **globalSetup**: Runs once before all tests
- **workers**: 1 in CI, parallel locally
- **retries**: 2 in CI, 0 locally
- **timeout**: 30 seconds per test

### Environment Variables

Tests automatically load from:
1. `frontend/.env.development` (for local development)
2. Environment variables (for CI)

Required variables:
- `CLERK_SECRET_KEY`
- `CLERK_PUBLISHABLE_KEY` or `VITE_CLERK_PUBLISHABLE_KEY`
- `E2E_CLERK_USER_EMAIL`

Optional variables:
- `VITE_API_BASE_URL` (default: `http://localhost:8000`)
- `BASE_URL` (default: `http://localhost:5173`)

## Continuous Integration

In CI (GitHub Actions), E2E tests:
1. Use 1 worker (sequential execution)
2. Retry failed tests up to 2 times
3. Generate HTML report artifact
4. Run only on Chromium browser

## Troubleshooting Checklist

Before opening an issue, check:

- [ ] All Docker services are running and healthy
- [ ] Environment variables are set correctly
- [ ] Playwright browsers are installed
- [ ] Environment validation passes
- [ ] Backend health endpoint returns 200
- [ ] Frontend is accessible in browser
- [ ] Authentication debug utility shows valid token
- [ ] Backend logs show incoming requests

## Additional Resources

- [Playwright Documentation](https://playwright.dev/docs/intro)
- [Clerk Testing Documentation](https://clerk.com/docs/testing/overview)
- [Zebu Architecture Documentation](../../../docs/architecture/)

## Getting Help

If tests are failing:

1. Run environment validation to identify the issue
2. Check test output for validation failures
3. Run authentication debug utility if auth-related
4. Review test artifacts (screenshots, videos, traces)
5. Check backend logs for errors
6. Consult this README for common issues

If the issue persists, open a GitHub issue with:
- Environment validation output
- Authentication debug output
- Test failure screenshots/logs
- Backend logs
- Steps to reproduce
