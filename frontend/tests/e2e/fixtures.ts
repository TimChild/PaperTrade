import { test as base, expect } from '@playwright/test'
import { clerk, setupClerkTestingToken } from '@clerk/testing/playwright'

/**
 * Custom Playwright test with Clerk authentication setup.
 *
 * Each test gets fresh authentication using clerk.signIn({ emailAddress }).
 * This creates a sign-in token valid for 5 minutes, avoiding the issue
 * of Clerk session tokens expiring after 60 seconds.
 *
 * The test fixture:
 * 1. Sets up Clerk testing token (for bot detection bypass)
 * 2. Signs in the user using email-based authentication
 * 3. Navigates to dashboard to ensure auth is complete
 */
export const test = base.extend({
  page: async ({ page }, use) => {
    const email = process.env.E2E_CLERK_USER_EMAIL
    if (!email) {
      throw new Error('E2E_CLERK_USER_EMAIL environment variable must be set')
    }

    // Step 1: Set up Clerk testing token (bypass bot detection)
    await setupClerkTestingToken({ page })

    // Step 2: Navigate to app (needed for clerk.signIn)
    await page.goto('/')
    await page.waitForLoadState('networkidle')

    // Step 3: Sign in using email-based authentication
    // This creates a fresh sign-in token valid for 5 minutes
    await clerk.signIn({
      page,
      emailAddress: email,
    })

    // Step 4: Wait for authentication to complete
    await page.waitForURL('**/dashboard', { timeout: 15000 })

    // Use the authenticated page in the test
    // eslint-disable-next-line react-hooks/rules-of-hooks
    await use(page)
  },
})

// Re-export expect from Playwright
export { expect }
