# Task 097: Fix E2E Test Failures from PR #114

**Status**: Not Started
**Agent**: quality-infra
**Priority**: High (Blocking CI)
**Estimated Effort**: Small (30-45 min)
**Dependencies**: None
**Created**: 2026-01-11

## Context

PR #114 ("Add comprehensive QA infrastructure") merged with test failures:
- `@axe-core/playwright` dependency not installed (import error)
- `responsive.spec.ts` uses forbidden `test.use()` pattern inside `test.describe()`
- E2E tests run across 3 browsers (180+ tests) taking 50+ minutes

**Current State:**
- ❌ `task test:all` fails locally
- ❌ `task test:e2e` fails in CI
- ✅ Unit tests (194) passing
- ✅ Backend tests (489+) passing

**Root Cause:**
PR #114 added E2E test infrastructure without ensuring tests pass before merge.

## Problem Analysis

### Issue 1: Missing Dependency ❌
```
Error: Cannot find package '@axe-core/playwright'
```
- PR #114 added `accessibility.spec.ts` importing `@axe-core/playwright`
- Package listed in `package.json` devDependencies
- But `npm ci` was never run post-merge to install it

### Issue 2: Playwright Structural Error ❌
```
Cannot use({ defaultBrowserType }) in a describe group
```
- `responsive.spec.ts` uses `test.use(deviceConfig)` inside `test.describe()`
- Playwright forbids this pattern (forces new workers mid-describe)
- Must use `setViewportSize()` in `beforeEach` instead

### Issue 3: Excessive Test Execution ⚠️
```yaml
# Current config (main branch)
fullyParallel: false
workers: 1
browsers: [chromium, firefox, webkit]
# Result: 60 tests × 3 browsers × serial = 50+ minutes
```

## Goals

**Fix all E2E test failures so `task test:all` and CI pass.**

Focus: Minimal surgical fixes only. No scope creep.

## Success Criteria

- [ ] `task test:e2e` completes successfully (all E2E tests pass)
- [ ] `task test:all` completes successfully (backend + frontend + E2E)
- [ ] CI E2E job passes on PR
- [ ] No import errors for `@axe-core/playwright`
- [ ] No Playwright structural errors in `responsive.spec.ts`
- [ ] E2E runtime ≤15 minutes (down from 50+ minutes)

## Implementation Plan

### 1. Install Missing Dependency (5 min)

The dependency is already in `package.json`, just needs installation:

```bash
cd frontend
npm ci  # Clean install all dependencies including @axe-core/playwright
```

**Verification:**
```bash
npm list @axe-core/playwright
# Should show: @axe-core/playwright@4.11.0
```

### 2. Fix responsive.spec.ts Structure (10 min)

**Current (BROKEN):**
```typescript
for (const [deviceName, deviceConfig] of Object.entries(viewports)) {
  test.describe(`Responsive Design - ${deviceName}`, () => {
    test.use(deviceConfig)  // ❌ NOT ALLOWED inside describe

    test.beforeEach(async ({ page }) => {
      // ...
    })
  })
}
```

**Fixed:**
```typescript
for (const [deviceName, deviceConfig] of Object.entries(viewports)) {
  test.describe(`Responsive Design - ${deviceName}`, () => {
    test.beforeEach(async ({ page }) => {
      // Set viewport size before navigation
      if ('viewport' in deviceConfig) {
        await page.setViewportSize(deviceConfig.viewport)
      }

      const email = process.env.E2E_CLERK_USER_EMAIL || 'test-e2e@zebu.dev'
      // ... rest of beforeEach
    })
  })
}
```

**File:** `frontend/tests/e2e/responsive.spec.ts`

### 3. Optimize Playwright Configuration (15 min)

**Current Performance Issue:**
- 3 browsers × ~60 tests = ~180 test executions
- Serial execution (workers: 1) = very slow
- Multi-browser testing valuable but not for every PR

**Recommended Fix:**

```typescript
// frontend/playwright.config.ts
export default defineConfig({
  testDir: './tests/e2e',
  globalSetup: path.resolve(__dirname, './tests/e2e/global-setup.ts'),

  /* Enable parallel execution for faster tests */
  fullyParallel: true,

  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,

  /* Use 3 workers for parallel execution (was 1 serial) */
  workers: process.env.CI ? 2 : 3,

  reporter: 'html',

  /* Set reasonable timeouts */
  timeout: 30000, // 30 seconds per test
  expect: {
    timeout: 10000, // 10 seconds for assertions
  },

  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
  },

  /* Primary browser: chromium (can add others later if needed) */
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    // Firefox and WebKit can be enabled for pre-release testing
    // Uncomment to run multi-browser tests:
    // {
    //   name: 'firefox',
    //   use: { ...devices['Desktop Firefox'] },
    // },
    // {
    //   name: 'webkit',
    //   use: { ...devices['Desktop Safari'] },
    // },
  ],
})
```

**Rationale:**
- Chromium-only: Covers Chrome, Edge, Brave, Opera (most users)
- 3 workers: Parallel execution reduces runtime from 50+ min to ~10-15 min
- Can enable Firefox/WebKit for release testing

### 4. Verification & Testing (10 min)

**Step 1: Install and verify:**
```bash
cd frontend
npm ci
npm list @axe-core/playwright  # Should show version 4.11.0
```

**Step 2: Run E2E tests locally:**
```bash
cd ..  # Back to repo root
task docker:up  # Ensure services running
task test:e2e   # Should complete successfully
```

**Expected Output:**
```
Running 60 tests using 3 workers
  60 passed (10-15 minutes)
```

**Step 3: Run full test suite:**
```bash
task test:all
# Should run: backend + frontend unit + E2E
# All should pass
```

## Files to Modify

1. **frontend/tests/e2e/responsive.spec.ts** (10 lines changed)
   - Remove `test.use(deviceConfig)` from inside describe block
   - Add `setViewportSize()` in beforeEach hook

2. **frontend/playwright.config.ts** (15 lines changed)
   - Set `fullyParallel: true`
   - Set `workers: 3` (2 in CI)
   - Add timeout configurations
   - Comment out firefox/webkit projects
   - Add comments explaining multi-browser setup

3. **frontend/package-lock.json** (auto-updated by npm ci)

## Testing Strategy

**Local Testing:**
1. ✅ `npm ci` installs dependencies without errors
2. ✅ `task test:e2e` completes in ≤15 minutes
3. ✅ All E2E tests pass (60/60)
4. ✅ `task test:all` completes successfully

**CI Testing:**
1. ✅ E2E job passes in GitHub Actions
2. ✅ No import errors in CI logs
3. ✅ E2E runtime in CI ≤20 minutes

## Non-Goals (Out of Scope)

- ❌ Docker volume mount changes (separate concern - PR #115 already has this)
- ❌ New E2E test files
- ❌ Lighthouse CI setup
- ❌ Visual regression test fixes
- ❌ Backend test changes
- ❌ Major E2E infrastructure redesign

**If PR #115 is still open and you want to merge it:**
- Close PR #115 (it has scope creep)
- Cherry-pick just the Docker changes if needed as separate PR
- This task (097) handles the E2E test fixes properly

**If PR #115 should be kept:**
- This task focuses only on fixing main branch
- PR #115 can proceed with Docker improvements

## Expected Outcome

After this task:
- ✅ All tests passing (`task test:all`)
- ✅ CI green (E2E tests pass)
- ✅ E2E runtime: ~10-15 min local, ~15-20 min CI
- ✅ No breaking changes
- ✅ Development workflow unblocked

## Notes for Agent

**Keep it simple:**
- Just fix what's broken
- Don't add new features
- Don't refactor unrelated code
- Stay focused on the 3 issues above

**Verification before PR:**
- Run `task test:all` locally - must pass
- Check CI passes on your PR branch
- Confirm E2E runtime is reasonable

## References

- PR #114: Added E2E infrastructure (merged with broken tests)
- PR #115: Attempted fix but included scope creep
- Playwright docs: https://playwright.dev/docs/test-use-options#use-options-in-a-test
- `task test:e2e` - Run E2E tests
- `task test:all` - Run all test suites
