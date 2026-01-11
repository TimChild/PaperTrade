import { defineConfig, devices } from '@playwright/test'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

/**
 * Playwright E2E testing configuration
 *
 * See https://playwright.dev/docs/test-configuration
 */
export default defineConfig({
  testDir: './tests/e2e',
  /* Global setup for Clerk testing */
  globalSetup: path.resolve(__dirname, './tests/e2e/global-setup.ts'),
  /* Enable parallel execution for faster tests */
  fullyParallel: true,
  /* Fail the build on CI if you accidentally left test.only in the source code. */
  forbidOnly: !!process.env.CI,
  /* Retry on CI only */
  retries: process.env.CI ? 2 : 0,
  /* Use 3 workers for parallel execution (2 in CI to reduce resource usage) */
  workers: process.env.CI ? 2 : 3,
  /* Reporter to use. See https://playwright.dev/docs/test-reporters */
  reporter: 'html',

  /* Set reasonable timeouts */
  timeout: 30000, // 30 seconds per test
  expect: {
    timeout: 10000, // 10 seconds for assertions
  },

  /* Shared settings for all the projects below. See https://playwright.dev/docs/api/class-testoptions. */
  use: {
    /* Base URL to use in actions like `await page.goto('/')`. */
    baseURL: 'http://localhost:5173',

    /* Collect trace when retrying the failed test. See https://playwright.dev/docs/trace-viewer */
    trace: 'on-first-retry',
  },

  /* Configure projects for major browsers */
  /* Primary browser: chromium (covers Chrome, Edge, Brave, Opera - most users) */
  /* Multi-browser testing can be enabled for pre-release testing by uncommenting firefox/webkit */
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    // Uncomment to run multi-browser tests (increases test time significantly):
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
