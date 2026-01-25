import { test as setup, expect } from '@playwright/test'
import { clerk } from '@clerk/testing/playwright'
import { setupClerkTestingToken } from '@clerk/testing/playwright'

const authFile = 'playwright/.auth/user.json'

setup('authenticate', async ({ page }) => {
  const email = process.env.E2E_CLERK_USER_EMAIL
  if (!email) {
    throw new Error('E2E_CLERK_USER_EMAIL environment variable must be set')
  }

  // Set up Clerk testing token for this page
  await setupClerkTestingToken({ page })

  // Navigate to app
  await page.goto('/')
  await page.waitForLoadState('networkidle')

  // Sign in using Clerk
  await clerk.signIn({
    page,
    emailAddress: email,
  })

  // Wait for successful authentication and redirect
  await page.waitForURL('**/dashboard', { timeout: 15000 })

  // Verify we're authenticated
  await expect(page.getByText('Portfolio Dashboard')).toBeVisible()

  // Save authentication state
  await page.context().storageState({ path: authFile })

  console.log('✓ Authentication state saved to', authFile)
})
