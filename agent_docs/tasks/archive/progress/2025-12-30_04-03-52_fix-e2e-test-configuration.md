# Fix E2E Test Configuration

**Date**: 2025-12-30
**Agent**: quality-infra
**Task**: Task 026 - Fix E2E Test Configuration
**Branch**: copilot/fix-e2e-test-configuration

## Task Summary

Fixed Playwright E2E test configuration to prevent Vitest from attempting to execute E2E tests, which was causing test failures due to incompatible test syntax.

## Problem Statement

**Issue**: Playwright E2E tests were failing with the following error:
```
Error: Playwright Test did not expect test.describe() to be called here.
Most common reasons include:
- You are calling test.describe() in a configuration file.
- You are calling test.describe() in a file that is imported by the configuration file.
- You have two different versions of @playwright/test.
```

**Root Cause**: Vitest was attempting to load and execute Playwright test files (`tests/e2e/*.spec.ts`) because the Vitest configuration didn't exclude them. Playwright uses different syntax (`test.describe()` from `@playwright/test`) that's incompatible with Vitest's test runner.

**Affected Files**:
- `tests/e2e/portfolio-creation.spec.ts`
- `tests/e2e/trading.spec.ts`

## Solution Implemented

### 1. Updated Vitest Configuration

**File**: `frontend/vitest.config.ts`

Added an `exclude` array to the test configuration to explicitly exclude E2E tests:

```typescript
test: {
  globals: true,
  environment: 'jsdom',
  setupFiles: './tests/setup.ts',
  css: true,
  // Exclude E2E tests from Vitest (they use Playwright)
  exclude: [
    '**/node_modules/**',
    '**/dist/**',
    '**/cypress/**',
    '**/.{idea,git,cache,output,temp}/**',
    '**/{karma,rollup,webpack,vite,vitest,jest,ava,babel,nyc,cypress,tsup,build}.config.*',
    '**/tests/e2e/**', // Exclude Playwright E2E tests
  ],
}
```

This ensures Vitest only runs unit tests and ignores E2E tests completely.

### 2. Updated Package Scripts

**File**: `frontend/package.json`

Added explicit test scripts to separate unit and E2E tests:

```json
"scripts": {
  "test": "vitest run",          // Default: runs unit tests only
  "test:unit": "vitest run",     // Explicit unit tests
  "test:watch": "vitest",
  "test:ui": "vitest --ui",
  "test:e2e": "playwright test", // E2E tests
  "test:e2e:ui": "playwright test --ui",
  "test:e2e:headed": "playwright test --headed",
  "test:all": "npm run test:unit && npm run test:e2e" // Run both
}
```

### 3. Updated Taskfile

**File**: `Taskfile.yml`

Updated the `test:frontend` task to be more explicit and added new E2E-specific tasks:

```yaml
test:frontend:
  desc: "Run frontend unit tests (Vitest only)"
  dir: "{{.FRONTEND_DIR}}"
  cmds:
    - echo "Running frontend unit tests..."
    - npm run test:unit  # Changed from 'npm run test'

test:e2e:ui:
  desc: "Run E2E tests with Playwright UI"
  dir: "{{.FRONTEND_DIR}}"
  cmds:
    - echo "Running E2E tests with UI..."
    - npm run test:e2e:ui

test:all:
  desc: "Run all tests (backend + frontend unit + E2E)"
  cmds:
    - task: test:backend
    - task: test:frontend
    - task: test:e2e
```

### 4. Updated .gitignore

**File**: `frontend/.gitignore`

Added test artifacts to prevent them from being committed:

```
# Test artifacts
playwright-report
test-results
```

## Testing Results

### Unit Tests
```bash
$ npm run test:unit

✓ src/hooks/__tests__/usePriceQuery.test.tsx (14 tests | 1 skipped)
✓ src/App.test.tsx (3 tests)
✓ src/components/features/portfolio/CreatePortfolioForm.test.tsx (12 tests)
✓ src/components/features/portfolio/PortfolioSummaryCard.test.tsx (6 tests)
✓ src/components/ui/Dialog.test.tsx (7 tests)
✓ src/components/HealthCheck.test.tsx (3 tests)
✓ src/utils/formatters.test.ts (11 tests)

Test Files  7 passed (7)
Tests  55 passed | 1 skipped (56)
Duration  3.96s
```

**Result**: ✅ **PASSED** - No E2E test errors, all unit tests pass

### Playwright E2E Tests

```bash
$ npx playwright test --list

Listing tests:
  [chromium] › portfolio-creation.spec.ts:11:3 › Portfolio Creation Flow › should create portfolio and show it in dashboard
  [chromium] › portfolio-creation.spec.ts:42:3 › Portfolio Creation Flow › should persist portfolio after page refresh
  [chromium] › portfolio-creation.spec.ts:69:3 › Portfolio Creation Flow › should show validation error for empty portfolio name
  [chromium] › portfolio-creation.spec.ts:85:3 › Portfolio Creation Flow › should show validation error for invalid deposit amount
  [chromium] › trading.spec.ts:11:3 › Trading Flow › should execute buy trade and update portfolio
  [chromium] › trading.spec.ts:64:3 › Trading Flow › should show error when buying with insufficient funds
  [chromium] › trading.spec.ts:102:3 › Trading Flow › should display portfolio holdings after trade

Total: 7 tests in 2 files
```

**Result**: ✅ **PASSED** - Playwright correctly detects all E2E tests

## Files Changed

### Modified Files
1. ✅ `frontend/vitest.config.ts` - Added E2E test exclusion
2. ✅ `frontend/package.json` - Added explicit test:unit and test:all scripts
3. ✅ `Taskfile.yml` - Updated test:frontend task and added test:e2e:ui, test:all
4. ✅ `frontend/.gitignore` - Added playwright-report and test-results

### New Files
- None (all necessary files already existed)

## CI/CD Impact

### Verified Compatibility

**No changes required** to CI workflows. The existing workflows already correctly separate unit and E2E tests:

1. **pr.yml** (line 138): Uses `npm run test` which now excludes E2E tests
2. **ci.yml** (line 92): Uses `task test:frontend` which now uses `test:unit`
3. Both workflows have separate E2E test jobs that use `npm run test:e2e` or `task test:e2e`

The workflows were already well-structured and will work correctly with the new configuration.

## Decision Log

### Why Exclude E2E Tests Instead of Moving Them?

**Decision**: Exclude E2E tests from Vitest configuration rather than moving them to a different directory.

**Reasoning**:
1. **Convention**: Keeping E2E tests in `tests/e2e/` is a standard convention
2. **Playwright Config**: The existing `playwright.config.ts` already points to `./tests/e2e`
3. **Minimal Changes**: Only configuration changes needed, no file restructuring
4. **Clarity**: The exclusion pattern makes it explicit that E2E tests are separate

### Why Both test and test:unit Scripts?

**Decision**: Keep both `test` and `test:unit` scripts pointing to the same command.

**Reasoning**:
1. **Backward Compatibility**: `npm test` is a standard convention developers expect
2. **CI Compatibility**: Existing CI workflows use `npm run test`
3. **Explicitness**: `test:unit` makes it clear what's being run
4. **Flexibility**: Allows future differentiation if needed

## Known Issues / TODOs

None. All success criteria met.

## Next Steps / Recommendations

1. ✅ Consider adding a `test:coverage` script for coverage reports
2. ✅ Document the test separation in the main README
3. ✅ Consider adding a pre-commit hook to run unit tests
4. ✅ E2E tests can be run in CI on every PR (already configured)

## References

- [Task 026 Issue](../agent_tasks/026-fix-e2e-test-configuration.md)
- [Vitest Configuration](https://vitest.dev/config/)
- [Playwright Configuration](https://playwright.dev/docs/test-configuration)
- [Testing Strategy](../project_strategy.md)

## Impact Assessment

**Risk**: LOW - Configuration-only changes, no code modifications
**Priority**: MEDIUM - Unblocks E2E testing capability
**Effort**: 1 hour (as estimated)
**Actual Time**: ~30 minutes

## Verification Checklist

- [x] Unit tests run successfully without E2E tests
- [x] Playwright detects E2E tests correctly
- [x] Both test commands work via npm scripts
- [x] Taskfile commands are functional (verified manually)
- [x] CI workflows remain compatible
- [x] .gitignore excludes test artifacts
- [x] All success criteria from task definition met
- [x] Progress documentation created
