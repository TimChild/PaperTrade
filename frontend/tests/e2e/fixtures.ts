/**
 * Playwright test fixtures with Clerk authentication support
 *
 * Uses @clerk/testing to properly handle authentication in E2E tests:
 * - setupClerkTestingToken() injects testing tokens to bypass bot detection
 * - clerk.signIn() signs in a test user programmatically
 *
 * References:
 * - https://clerk.com/docs/testing/playwright
 */
import { test as base, expect } from '@playwright/test'
import { clerk, setupClerkTestingToken } from '@clerk/testing/playwright'

/**
 * Extended test fixture that sets up Clerk testing token
 * This allows tests to authenticate properly with Clerk
 */
export const test = base.extend({
  page: async ({ page }, use) => {
    // Only set up Clerk testing token if credentials are configured
    // If not, tests will need to skip themselves
    if (process.env.CLERK_SECRET_KEY) {
      await setupClerkTestingToken({ page })
    }
    await use(page)
  },
})

export { expect, clerk }
