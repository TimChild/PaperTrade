import { test as setup, expect } from '@playwright/test'
import { clerk } from '@clerk/testing/playwright'
import { setupClerkTestingToken } from '@clerk/testing/playwright'

const authFile = 'playwright/.auth/user.json'

setup('authenticate', async ({ page }) => {
  // Check if running in E2E test mode (static tokens)
  const e2eMode =
    process.env.E2E_TEST_MODE?.toLowerCase() === 'true' ||
    process.env.VITE_E2E_TEST_MODE?.toLowerCase() === 'true'

  if (e2eMode) {
    console.log('E2E_TEST_MODE enabled - skipping Clerk authentication (using static tokens)')
    
    // In E2E mode, navigate to the app and verify it loads
    // The API client will automatically use the static test token
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    
    // Wait for successful authentication with static token
    // The backend's InMemoryAuthAdapter in permissive mode will accept any token
    await page.waitForURL('**/dashboard', { timeout: 15000 })
    
    // Verify we can see the dashboard
    await expect(page.getByText('Portfolio Dashboard')).toBeVisible()
    
    // Save authentication state (minimal, just for consistency)
    await page.context().storageState({ path: authFile })
    
    console.log('✓ E2E authentication state saved to', authFile)
    return
  }

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
