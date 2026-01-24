# Task 169: Add Terminal Reporter for E2E Tests

**Agent**: frontend-swe  
**Priority**: MEDIUM (Developer Experience)  
**Estimated Effort**: 30 minutes

## Objective

Configure Playwright to show test results in the terminal while still preserving the HTML reporter for local development and debugging.

## Problem

Currently, E2E tests open an HTML report page which blocks the terminal until manually closed with Ctrl+C. This prevents:
- Seeing test results immediately in terminal
- Running tests in CI/automated workflows
- Quick iteration during development

**Current Configuration** (`frontend/playwright.config.ts` line 27):
```typescript
reporter: 'html',
```

## Solution

Use conditional reporter configuration based on environment:

```typescript
reporter: process.env.CI 
  ? [['list'], ['html']]  // CI: terminal output + HTML artifact
  : 'html',               // Local: HTML UI only
```

**Alternative** (more granular control):
```typescript
reporter: process.env.CI
  ? [
      ['list'],  // Terminal output
      ['json', { outputFile: 'test-results/results.json' }],  // Machine-readable
      ['html', { open: 'never' }]  // HTML artifact without auto-open
    ]
  : [
      ['html', { open: 'on-failure' }]  // Local: only open on failures
    ],
```

## Benefits

✅ **CI/Automation**: Terminal output shows pass/fail status immediately  
✅ **Local Development**: HTML UI still available via `npm run test:e2e:ui` or manually opening `playwright-report/index.html`  
✅ **Best of Both**: Terminal for quick feedback, HTML for detailed debugging

## Implementation

**File**: `frontend/playwright.config.ts`

```typescript
import { defineConfig, devices } from '@playwright/test'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

export default defineConfig({
  testDir: './tests/e2e',
  globalSetup: path.resolve(__dirname, './tests/e2e/global-setup.ts'),
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  
  /* Reporter configuration - terminal in CI, HTML for local */
  reporter: process.env.CI
    ? [
        ['list'],  // Terminal list output
        ['html', { open: 'never' }]  // HTML artifact without auto-open
      ]
    : [
        ['html', { open: 'on-failure' }]  // Local: open HTML on failures only
      ],

  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
  },

  projects: [
    {
      name: 'setup',
      testMatch: /.*\.setup\.ts/,
    },
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        storageState: 'playwright/.auth/user.json',
      },
      dependencies: ['setup'],
    },
  ],
})
```

## Taskfile Integration

The existing `task test:e2e` command will automatically use the correct reporter based on environment:

```bash
# Local development - HTML UI
task test:e2e

# Explicitly set CI mode for terminal output
CI=1 task test:e2e

# Or use the UI mode when you want interactive debugging
task test:e2e:ui
```

## Testing

### Verify Terminal Output
```bash
# Should show terminal list output
CI=1 task test:e2e

# Output should look like:
# Running 14 tests using 1 worker
# 
#   ✓  auth.setup.ts:5:5 › authenticate (2s)
#   ✓  dashboard.spec.ts:10:5 › should display portfolios (1s)
#   ...
# 
# 14 passed (15s)
```

### Verify HTML Reporter Still Works
```bash
# Should open HTML report on failures (if any)
task test:e2e

# Or explicitly open HTML UI
task test:e2e:ui
```

### CI Workflow
Verify GitHub Actions shows terminal output in workflow logs:
```bash
# .github/workflows/ci.yml should show test results inline
```

## Quality Standards

- ✅ No changes to test logic or behavior
- ✅ Works in both local and CI environments
- ✅ HTML report still generated for debugging
- ✅ Terminal output is readable and informative

## Success Criteria

1. ✅ `task test:e2e` shows terminal output without blocking
2. ✅ HTML report still generated in `playwright-report/`
3. ✅ `task test:e2e:ui` still launches interactive UI
4. ✅ CI workflows show test results in logs
5. ✅ No breaking changes to existing test commands

## References

- **Playwright Reporters**: https://playwright.dev/docs/test-reporters
- **Current Config**: `frontend/playwright.config.ts`
- **User Request**: Terminal output blocked by auto-opening HTML report
- **Related Task**: `Taskfile.yml` test:e2e command (lines 87-107)
