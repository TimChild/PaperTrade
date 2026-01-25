import { defineConfig, devices } from '@playwright/test'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

/**
 * Playwright E2E testing configuration
 *
 * Authentication Strategy:
 * - Each test uses clerk.signIn({ emailAddress }) for fresh authentication
 * - This creates a sign-in token valid for 5 minutes per test
 * - No storage state sharing (Clerk session tokens expire in 60 seconds)
 *
 * See https://playwright.dev/docs/test-configuration
 */
export default defineConfig({
  testDir: './tests/e2e',
  /* Global setup creates Clerk testing token for bot detection bypass */
  globalSetup: path.resolve(__dirname, './tests/e2e/global-setup.ts'),
  /* Global teardown shows cleanup tips */
  globalTeardown: path.resolve(__dirname, './tests/e2e/global-teardown.ts'),
  /* Run tests in parallel - each test handles its own auth */
  fullyParallel: true,
  /* Fail the build on CI if you accidentally left test.only in the source code. */
  forbidOnly: !!process.env.CI,
  /* Retry on CI only */
  retries: process.env.CI ? 2 : 0,
  /* Limit workers on CI to avoid rate limiting */
  workers: process.env.CI ? 1 : 3,
  /* Reporter - list format for terminal output */
  reporter: 'list',
  /* Timeout - increase for auth operations */
  timeout: 60000,
  expect: {
    timeout: 10000,
  },

  /* Shared settings for all the projects below. See https://playwright.dev/docs/api/class-testoptions. */
  use: {
    /* Base URL to use in actions like `await page.goto('/')`. */
    baseURL: 'http://localhost:5173',

    /* Collect trace when retrying the failed test. See https://playwright.dev/docs/trace-viewer */
    trace: 'on-first-retry',

    /* Capture screenshot on failure */
    screenshot: 'only-on-failure',

    /* Video recording - only on retry to save resources */
    video: 'on-first-retry',
  },

  /* Configure projects for major browsers */
  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
      },
    },
    // Add other browsers when needed:
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
