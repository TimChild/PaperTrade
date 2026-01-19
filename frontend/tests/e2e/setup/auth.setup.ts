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
    console.log('E2E_TEST_MODE enabled - mocking Clerk session state with static token')
    
    // Navigate to the app first
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    
    // Mock Clerk session in browser storage
    // This makes Clerk think the user is signed in, allowing React to render authenticated routes
    await page.evaluate(() => {
      // Set Clerk session data to make isSignedIn return true
      const sessionData = {
        object: 'client',
        id: 'client_e2e_test',
        sessions: [
          {
            object: 'session',
            id: 'sess_e2e_test',
            status: 'active',
            last_active_at: Date.now(),
            expire_at: Date.now() + 86400000, // 24 hours from now
            abandon_at: Date.now() + 604800000, // 7 days from now
            user: {
              id: 'user_e2e_test',
              primary_email_address_id: 'email_e2e_test',
              email_addresses: [
                {
                  id: 'email_e2e_test',
                  email_address: 'test-e2e@papertrade.dev',
                },
              ],
            },
            last_active_token: {
              object: 'token',
              jwt: 'e2e-test-token',
            },
          },
        ],
        sign_in: null,
        sign_up: null,
        last_active_session_id: 'sess_e2e_test',
      }
      
      // Store in the format Clerk expects
      sessionStorage.setItem('__clerk_client', JSON.stringify(sessionData))
      localStorage.setItem('__clerk_db_jwt', 'e2e-test-token')
    })
    
    // Reload page to pick up the mocked session
    await page.reload()
    await page.waitForLoadState('networkidle')
    
    // Now the app should redirect to dashboard since Clerk thinks we're signed in
    await page.waitForURL('**/dashboard', { timeout: 15000 })
    
    // Verify we can see the dashboard
    await expect(page.getByText('Portfolio Dashboard')).toBeVisible()
    
    // Save authentication state (includes the mocked Clerk session)
    await page.context().storageState({ path: authFile })
    
    console.log('✓ E2E authentication state with mocked Clerk session saved to', authFile)
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
