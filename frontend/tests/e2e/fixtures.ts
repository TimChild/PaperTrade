import { test as base } from '@playwright/test'
import { setupClerkTestingToken } from '@clerk/testing/playwright'

/**
 * Custom Playwright test with Clerk authentication setup.
 *
 * This extends the base test to automatically set up Clerk testing tokens
 * for each test, allowing tests to sign in users without hitting bot protection.
 */
export const test = base.extend({
  page: async ({ page }, use) => {
    // Set up Clerk testing token for this page
    await setupClerkTestingToken({ page })

    // Use the page in the test (this is Playwright's use(), not a React hook)
    // eslint-disable-next-line react-hooks/rules-of-hooks
    await use(page)
  },
})

// Re-export expect from Playwright
export { expect } from '@playwright/test'
