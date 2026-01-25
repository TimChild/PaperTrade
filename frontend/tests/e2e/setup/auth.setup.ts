import { test as setup } from '@playwright/test'

const authFile = 'playwright/.auth/user.json'

/**
 * E2E authentication setup using in-memory auth adapter.
 * 
 * This bypasses Clerk authentication due to firewall restrictions in CI
 * that block access to Clerk's tenant subdomains (*.clerk.accounts.dev).
 * 
 * The backend is configured to use InMemoryAuthAdapter when CLERK_SECRET_KEY=test,
 * which accepts a pre-configured test token.
 */
setup('authenticate', async ({ page }) => {
  const email = process.env.E2E_CLERK_USER_EMAIL
  if (!email) {
    throw new Error('E2E_CLERK_USER_EMAIL environment variable must be set')
  }

  const testToken = process.env.E2E_TEST_TOKEN || 'test-token-12345'

  // Navigate to app - we'll manually set auth state
  await page.goto('/')
  
  // Wait for page to load
  await page.waitForLoadState('networkidle')

  // Inject authentication token directly into browser storage
  // This simulates being authenticated without Clerk
  await page.evaluate((token) => {
    // Store token in localStorage for API client to use
    localStorage.setItem('e2e_test_token', token)
  }, testToken)

  // Save authentication state
  await page.context().storageState({ path: authFile })

  console.log('✓ E2E authentication state saved (using in-memory auth)')
})
