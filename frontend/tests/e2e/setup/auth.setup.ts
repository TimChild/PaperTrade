import { test as setup, expect } from '@playwright/test'
import { clerk } from '@clerk/testing/playwright'
import { setupClerkTestingToken } from '@clerk/testing/playwright'

const authFile = 'playwright/.auth/user.json'

setup('authenticate', async ({ page }) => {
  // Check if E2E test mode is enabled
  const e2eMode = process.env.E2E_TEST_MODE?.toLowerCase() === 'true' ||
                  process.env.VITE_E2E_TEST_MODE?.toLowerCase() === 'true'
  
  if (e2eMode) {
    console.log('E2E_TEST_MODE enabled - navigating directly to dashboard (using static tokens)')
    
    // Navigate directly to dashboard - backend accepts static token via InMemoryAuthAdapter
    await page.goto('/dashboard')
    await page.waitForLoadState('networkidle')
    
    // Verify we're on the dashboard
    await expect(page.getByText('Portfolio Dashboard')).toBeVisible()
    
    // Save authentication state
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
