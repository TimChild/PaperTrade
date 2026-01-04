# Task 026: Fix E2E Test Configuration

**Created**: 2025-12-29
**Agent**: quality-infra
**Estimated Effort**: 1 hour
**Dependencies**: None
**Phase**: Quality Improvement

## Objective

Fix Playwright E2E test configuration so they run properly without conflicting with Vitest unit tests.

## Context

Frontend E2E tests (Playwright) are failing to load because Vitest is trying to execute them. Playwright uses different syntax (`test.describe()` from `@playwright/test`) that's incompatible with Vitest.

**Current Issue**:
```
Error: Playwright Test did not expect test.describe() to be called here.
Most common reasons include:
- You are calling test.describe() in a configuration file.
- You are calling test.describe() in a file that is imported by the configuration file.
- You have two different versions of @playwright/test.
```

**Affected Files**:
- `tests/e2e/portfolio-creation.spec.ts`
- `tests/e2e/trading.spec.ts`

## Success Criteria

- [ ] Playwright E2E tests excluded from Vitest
- [ ] E2E tests run successfully with Playwright
- [ ] Separate test commands for unit vs E2E tests
- [ ] Taskfile updated with `test:e2e` command
- [ ] All tests (unit + E2E) passing
- [ ] CI workflow updated if needed

## Implementation Details

### 1. Update Vitest Configuration

**File**: `frontend/vite.config.ts`

**Add Test Exclusion**:
```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/health': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  test: {
    // Vitest configuration
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    // Exclude E2E tests from Vitest (they use Playwright)
    exclude: [
      '**/node_modules/**',
      '**/dist/**',
      '**/cypress/**',
      '**/.{idea,git,cache,output,temp}/**',
      '**/{karma,rollup,webpack,vite,vitest,jest,ava,babel,nyc,cypress,tsup,build}.config.*',
      '**/tests/e2e/**',  // ✅ Exclude Playwright E2E tests
    ],
  },
})
```

### 2. Create Playwright Configuration

**File**: `frontend/playwright.config.ts` (create if doesn't exist)

```typescript
import { defineConfig, devices } from '@playwright/test'

/**
 * Playwright configuration for E2E tests.
 * See https://playwright.dev/docs/test-configuration.
 */
export default defineConfig({
  testDir: './tests/e2e',

  /* Run tests in files in parallel */
  fullyParallel: true,

  /* Fail the build on CI if you accidentally left test.only in the source code. */
  forbidOnly: !!process.env.CI,

  /* Retry on CI only */
  retries: process.env.CI ? 2 : 0,

  /* Opt out of parallel tests on CI. */
  workers: process.env.CI ? 1 : undefined,

  /* Reporter to use. See https://playwright.dev/docs/test-reporters */
  reporter: 'html',

  /* Shared settings for all the projects below. See https://playwright.dev/docs/api/class-testoptions. */
  use: {
    /* Base URL to use in actions like `await page.goto('/')`. */
    baseURL: 'http://localhost:5173',

    /* Collect trace when retrying the failed test. See https://playwright.dev/docs/trace-viewer */
    trace: 'on-first-retry',
  },

  /* Configure projects for major browsers */
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    // Uncomment to test in more browsers:
    // {
    //   name: 'firefox',
    //   use: { ...devices['Desktop Firefox'] },
    // },
    // {
    //   name: 'webkit',
    //   use: { ...devices['Desktop Safari'] },
    // },
  ],

  /* Run your local dev server before starting the tests */
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
    timeout: 120 * 1000,
  },
})
```

### 3. Update package.json Scripts

**File**: `frontend/package.json`

**Add Separate Test Commands**:
```json
{
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview",
    "lint": "eslint .",
    "test": "vitest",
    "test:unit": "vitest run",  // ✅ Explicit unit test command
    "test:e2e": "playwright test",  // ✅ Explicit E2E test command
    "test:e2e:ui": "playwright test --ui",  // ✅ E2E with UI
    "test:e2e:debug": "playwright test --debug",  // ✅ E2E debug mode
    "test:all": "npm run test:unit && npm run test:e2e"  // ✅ Run all tests
  }
}
```

### 4. Update Taskfile

**File**: `Taskfile.yml` (root)

**Add E2E Test Tasks**:
```yaml
tasks:
  # ... existing tasks ...

  test:frontend:
    desc: "Run frontend unit tests"
    dir: frontend
    cmds:
      - npm run test:unit

  test:e2e:
    desc: "Run E2E tests with Playwright"
    dir: frontend
    deps:
      - docker:up
      - dev:backend  # Backend must be running
    cmds:
      - npm run test:e2e

  test:e2e:ui:
    desc: "Run E2E tests with Playwright UI"
    dir: frontend
    deps:
      - docker:up
      - dev:backend
    cmds:
      - npm run test:e2e:ui

  test:all:
    desc: "Run all tests (backend + frontend unit + E2E)"
    deps:
      - docker:up
    cmds:
      - task: test:backend
      - task: test:frontend
      - task: test:e2e
```

**Update Existing test:frontend Task** (if it exists):
```yaml
test:frontend:
  desc: "Run frontend unit tests (Vitest only)"
  dir: frontend
  cmds:
    - npm run test:unit  # Changed from 'npm test'
```

### 5. Update CI Workflow (if needed)

**File**: `.github/workflows/ci.yml`

**Check if E2E tests are included**:
```yaml
jobs:
  frontend-checks:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json

      - name: Install dependencies
        run: npm ci
        working-directory: frontend

      - name: Lint
        run: npm run lint
        working-directory: frontend

      - name: Type check
        run: npm run type-check
        working-directory: frontend

      - name: Unit tests
        run: npm run test:unit  # ✅ Explicit unit tests only
        working-directory: frontend

      - name: Build
        run: npm run build
        working-directory: frontend

  e2e-tests:
    runs-on: ubuntu-latest
    needs: [backend-checks, frontend-checks]
    steps:
      - uses: actions/checkout@v4

      # Setup Node, Python, Docker, etc.

      - name: Install Playwright browsers
        run: npx playwright install --with-deps chromium
        working-directory: frontend

      - name: Start services
        run: task docker:up

      - name: Start backend
        run: task dev:backend &

      - name: Wait for backend
        run: timeout 60 bash -c 'until curl -f http://localhost:8000/health; do sleep 2; done'

      - name: Run E2E tests
        run: npm run test:e2e
        working-directory: frontend

      - name: Upload Playwright report
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: playwright-report
          path: frontend/playwright-report/
```

## Testing Checklist

- [ ] Unit tests run successfully:
  ```bash
  cd frontend
  npm run test:unit
  ```

- [ ] E2E tests run successfully:
  ```bash
  cd frontend
  npm run test:e2e
  ```

- [ ] Taskfile commands work:
  ```bash
  task test:frontend  # Unit tests only
  task test:e2e       # E2E tests
  task test:all       # All tests
  ```

- [ ] Verify Vitest no longer tries to load Playwright tests:
  ```bash
  npm test -- --run  # Should only run unit tests
  ```

- [ ] Check Playwright report generated:
  ```bash
  ls -la playwright-report/
  ```

## Files to Create/Modify

### Modified Files
1. `frontend/vite.config.ts` - Add test.exclude for E2E tests
2. `frontend/package.json` - Add separate test:unit, test:e2e scripts
3. `Taskfile.yml` - Add test:e2e tasks
4. `.github/workflows/ci.yml` - Separate E2E test job (if not already present)

### New Files
1. `frontend/playwright.config.ts` - Playwright configuration (if doesn't exist)

## Manual Testing

```bash
# 1. Ensure backend is running
task docker:up
task dev:backend

# 2. In separate terminal, run E2E tests
cd frontend
npm run test:e2e

# Expected: Tests run in Playwright, not Vitest
# Expected: Both portfolio-creation and trading specs execute

# 3. Run with UI for debugging
npm run test:e2e:ui

# 4. Run unit tests to verify separation
npm run test:unit

# Expected: Only unit tests run, no E2E tests attempted
```

## Definition of Done

- [ ] Vitest excludes E2E tests from test discovery
- [ ] Playwright E2E tests run successfully
- [ ] Both E2E test files pass (portfolio-creation, trading)
- [ ] Separate npm scripts for unit vs E2E tests
- [ ] Taskfile commands for E2E testing
- [ ] CI workflow updated (if needed)
- [ ] PR created with clear description
- [ ] Progress document created

## Impact

**Risk**: LOW - Configuration-only changes, no code changes
**Priority**: MEDIUM - Unblocks E2E testing capability
**Effort**: 1 hour (configuration updates)

## Notes

- Playwright tests require backend to be running
- E2E tests are slower than unit tests (use sparingly in CI)
- Consider running E2E tests only on PRs, not every push
- Playwright UI mode (`--ui`) is helpful for debugging

## References

- [Playwright Configuration](https://playwright.dev/docs/test-configuration)
- [Vitest Configuration](https://vitest.dev/config/)
- [Taskfile Documentation](https://taskfile.dev/)
