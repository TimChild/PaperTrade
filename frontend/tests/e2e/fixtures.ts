import { test as base } from '@playwright/test'
import { setupClerkTestingToken } from '@clerk/testing/playwright'

/**
 * Custom Playwright test with Clerk authentication setup.
 *
 * This extends the base test to automatically set up Clerk testing tokens
 * for each test, allowing tests to sign in users without hitting bot protection.
 *
 * Note: The ESLint disable is needed because Playwright's `use` function
 * triggers the react-hooks/rules-of-hooks rule, even though this is not React code.
 */
export const test = base.extend({
  page: async ({ page }, use) => {
    // Set up Clerk testing token for this page
    await setupClerkTestingToken({ page })

    // Use the page in the test
    await use(page)
  },
})

// Re-export expect from Playwright
export { expect } from '@playwright/test'
