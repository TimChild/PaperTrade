# Task 154: Fix E2E Test Flakiness from Clerk Rate Limiting

**Agent**: quality-infra
**Priority**: HIGH
**Date**: 2026-01-18
**Related**: E2E testing, PR #146 (Mobile responsive layout)

## Problem Statement

E2E tests are failing with navigation timeouts, likely due to **Clerk authentication rate limiting**. The error pattern:

```
TimeoutError: page.waitForURL: Timeout 10000ms exceeded.
waiting for navigation to "**/portfolio/*" until "load"
```

### Root Cause

Each E2E test authenticates via Clerk using `clerk.signIn()` in the `beforeEach` hook:

```typescript
test.beforeEach(async ({ page }) => {
  await page.goto('/')
  await page.waitForLoadState('networkidle')

  // Sign in using email-based approach
  await clerk.signIn({
    page,
    emailAddress: email,
  })

  // Wait for redirect to dashboard
  await page.waitForURL('**/dashboard', { timeout: 10000 })
})
```

**Problem**: With ~14 E2E tests, this creates **14+ authentication requests in quick succession**, hitting Clerk's rate limits.

### Symptoms

1. Tests that create portfolios time out waiting for navigation
2. Intermittent failures (works sometimes, fails other times)
3. Slowness in CI/CD when running full E2E suite
4. Same tests pass when run individually but fail when run together

## Objective

Implement **authentication state sharing** across E2E tests to reduce Clerk API calls from ~14 to 1-2 per test run.

## Requirements

### 1. Create Shared Authentication Setup

**File**: `frontend/tests/e2e/setup/auth.setup.ts` (NEW)

```typescript
import { test as setup, expect } from '@playwright/test'
import { clerk } from '@clerk/testing/playwright'

const authFile = 'playwright/.auth/user.json'

setup('authenticate', async ({ page }) => {
  const email = process.env.E2E_CLERK_USER_EMAIL
  if (!email) {
    throw new Error('E2E_CLERK_USER_EMAIL environment variable must be set')
  }

  // Navigate to app
  await page.goto('/')
  await page.waitForLoadState('networkidle')

  // Sign in using Clerk
  await clerk.signIn({
    page,
    emailAddress: email,
  })

  // Wait for successful authentication and redirect
  await page.waitForURL('**/dashboard', { timeout: 15000 })

  // Verify we're authenticated
  await expect(page.getByText('Portfolio Dashboard')).toBeVisible()

  // Save authentication state
  await page.context().storageState({ path: authFile })

  console.log('✓ Authentication state saved to', authFile)
})
```

### 2. Update Playwright Configuration

**File**: `frontend/playwright.config.ts` (MODIFY)

```typescript
import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',

  // Global setup project - runs once before all tests
  projects: [
    // Setup project - authenticate once and save state
    {
      name: 'setup',
      testMatch: /.*\.setup\.ts/,
    },

    // Test projects - use saved authentication state
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        storageState: 'playwright/.auth/user.json', // Reuse auth state
      },
      dependencies: ['setup'], // Run setup first
    },
    {
      name: 'firefox',
      use: {
        ...devices['Desktop Firefox'],
        storageState: 'playwright/.auth/user.json',
      },
      dependencies: ['setup'],
    },
    {
      name: 'webkit',
      use: {
        ...devices['Desktop Safari'],
        storageState: 'playwright/.auth/user.json',
      },
      dependencies: ['setup'],
    },
  ],

  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
  },

  // Web server configuration remains the same
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
  },
})
```

### 3. Simplify Test Setup

**File**: `frontend/tests/e2e/trading.spec.ts` (MODIFY)

Remove the `beforeEach` authentication block since we're now using shared state:

```typescript
import { test, expect } from './fixtures'

test.describe('Trading Flow', () => {
  // Remove the beforeEach hook - authentication already handled by setup project
  // test.beforeEach async ({ page }) => { ... } ← DELETE THIS

  test('should execute buy trade and update portfolio', async ({ page }) => {
    // Start directly at dashboard - already authenticated via storageState
    await page.goto('/dashboard')
    await page.waitForLoadState('networkidle')

    // Rest of test remains the same...
    const headerButton = page.getByTestId('create-portfolio-header-btn')
    const emptyStateButton = page.getByTestId('create-first-portfolio-btn')
    const createButton = (await headerButton.isVisible()) ? headerButton : emptyStateButton
    await createButton.click()

    // ... rest of test
  })

  // Other tests also remove beforeEach and start with page.goto('/')
})
```

### 4. Update All E2E Test Files

Apply the same pattern to all E2E specs:

**Files to modify**:
- `frontend/tests/e2e/trading.spec.ts`
- `frontend/tests/e2e/portfolio.spec.ts`
- `frontend/tests/e2e/authentication.spec.ts` (if separate auth tests exist)
- Any other `*.spec.ts` files in `frontend/tests/e2e/`

**Pattern**:
```typescript
// Before (OLD - DO NOT USE):
test.beforeEach(async ({ page }) => {
  await clerk.signIn({ page, emailAddress: email })
  await page.waitForURL('**/dashboard')
})

// After (NEW - CORRECT):
// (no beforeEach - authentication via storageState)

test('test name', async ({ page }) => {
  await page.goto('/dashboard')  // Or whatever starting page
  // ... test code
})
```

### 5. Add .gitignore Entry

**File**: `.gitignore` (MODIFY)

```gitignore
# Playwright
/playwright/.auth/
playwright-report/
test-results/
```

### 6. Update CI/CD Workflow

**File**: `.github/workflows/ci.yml` (MODIFY - E2E Tests section)

Ensure the auth setup runs in CI:

```yaml
- name: Run E2E tests
  run: |
    docker compose up -d
    npm run test:e2e  # This now includes the setup project
  env:
    E2E_CLERK_USER_EMAIL: ${{ vars.E2E_CLERK_USER_EMAIL }}
    CLERK_SECRET_KEY: ${{ secrets.CLERK_SECRET_KEY }}
    # ... other env vars
```

### 7. Create README for Authentication Setup

**File**: `frontend/tests/e2e/setup/README.md` (NEW)

```markdown
# E2E Test Authentication Setup

This directory contains setup scripts that run once before all E2E tests.

## How It Works

1. `auth.setup.ts` authenticates with Clerk **once** at the start of the test run
2. Saves authentication state to `playwright/.auth/user.json`
3. All tests reuse this state instead of authenticating individually
4. Reduces Clerk API calls from ~14 (one per test) to 1 per test run

## Benefits

- **Faster tests**: No repeated authentication delays
- **No rate limiting**: Single authentication avoids Clerk rate limits
- **More reliable**: Eliminates flaky auth-related timeouts

## Running Tests

```bash
# Runs setup + all tests
npm run test:e2e

# Run specific test (still uses shared auth)
npx playwright test trading.spec.ts
```

## Troubleshooting

If tests fail with "not authenticated" errors:

1. Delete auth state: `rm -rf playwright/.auth/`
2. Re-run tests: `npm run test:e2e`

The setup will regenerate the auth state.
```

## Success Criteria

1. ✅ Authentication setup runs once before all tests
2. ✅ Auth state saved to `playwright/.auth/user.json`
3. ✅ All E2E tests pass without authentication-related timeouts
4. ✅ Clerk API calls reduced from ~14 to 1-2 per test run
5. ✅ Tests run faster (measured improvement in CI)
6. ✅ No flaky failures due to rate limiting
7. ✅ All existing E2E tests still pass (0 regressions)

## Testing Strategy

### Local Testing

1. **Clean slate test**:
   ```bash
   rm -rf playwright/.auth/
   npm run test:e2e
   ```
   Verify setup runs and creates auth file.

2. **Verify auth state reuse**:
   ```bash
   npm run test:e2e
   npm run test:e2e  # Second run should be faster
   ```

3. **Individual test**:
   ```bash
   npx playwright test trading.spec.ts --headed
   ```
   Verify test doesn't re-authenticate.

### CI Testing

1. Run CI workflow and verify:
   - Setup project completes successfully
   - All E2E tests pass
   - Total E2E time reduced (compare before/after)

2. Check for Clerk rate limit errors in logs

## Implementation Notes

### Auth State Expiration

Clerk auth tokens typically last 1 hour. For long-running test suites:

```typescript
// In auth.setup.ts - refresh if needed
const authFile = 'playwright/.auth/user.json'
const authExists = fs.existsSync(authFile)
const authAge = authExists
  ? Date.now() - fs.statSync(authFile).mtimeMs
  : Infinity

// Refresh if older than 30 minutes
if (authAge > 30 * 60 * 1000) {
  console.log('Auth state expired, re-authenticating...')
  // Proceed with authentication
} else {
  console.log('Using cached auth state')
  test.skip()
}
```

### Parallel Execution

With `fullyParallel: true`, multiple tests may try to read auth state simultaneously. This is safe because:
- All tests read the same file
- No concurrent writes (setup runs once before tests)
- Playwright handles this gracefully

### Test Isolation

Each test should still:
- Navigate to starting page explicitly
- Clean up data it creates (or use unique names)
- Not depend on order of execution

## Related Files

- `frontend/tests/e2e/setup/auth.setup.ts` (NEW)
- `frontend/tests/e2e/setup/README.md` (NEW)
- `frontend/playwright.config.ts` (MODIFY)
- `frontend/tests/e2e/trading.spec.ts` (MODIFY)
- `frontend/tests/e2e/portfolio.spec.ts` (MODIFY - if exists)
- `.gitignore` (MODIFY)
- `.github/workflows/ci.yml` (VERIFY)

## Future Enhancements (Out of Scope)

- Multiple auth states for different user roles
- Auth state caching across CI runs (using cache action)
- Automatic auth refresh for very long test runs

## Definition of Done

- [ ] `auth.setup.ts` created and working
- [ ] Playwright config updated with setup project
- [ ] All E2E test files updated to use shared auth
- [ ] `.gitignore` updated to exclude auth state
- [ ] README created in setup directory
- [ ] All E2E tests pass locally (3 runs minimum)
- [ ] All E2E tests pass in CI (2 runs minimum)
- [ ] No Clerk rate limit errors in logs
- [ ] Test execution time reduced (before/after comparison documented)
- [ ] PR includes before/after metrics in description
