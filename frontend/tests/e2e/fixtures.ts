import { test as base } from '@playwright/test'
import { setupClerkTestingToken } from '@clerk/testing/playwright'

/**
 * Custom Playwright test with Clerk authentication setup.
 *
 * This extends the base test to automatically set up Clerk testing tokens
 * for each test, allowing tests to sign in users without hitting bot protection.
 *
 * In E2E test mode, skips Clerk setup since we use static tokens instead.
 */
export const test = base.extend({
  page: async ({ page }, use) => {
    // Check if running in E2E test mode (static tokens)
    const e2eMode =
      process.env.E2E_TEST_MODE?.toLowerCase() === 'true' ||
      process.env.VITE_E2E_TEST_MODE?.toLowerCase() === 'true'

    if (!e2eMode) {
      // Set up Clerk testing token for this page (only when not in E2E mode)
      await setupClerkTestingToken({ page })
    }

    // Use the page in the test (this is Playwright's use(), not a React hook)
    // eslint-disable-next-line react-hooks/rules-of-hooks
    await use(page)
  },
})

// Re-export expect from Playwright
export { expect } from '@playwright/test'
