import { clerk } from '@clerk/testing/playwright'
import { test, expect } from './fixtures'

test.describe('Clerk Auth Test', () => {
  test('should authenticate with Clerk using test email', async ({ page }) => {
    console.log('Starting Clerk auth test...')
    
    // Navigate to app
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    console.log('Page loaded')

    // Take screenshot before sign-in attempt
    await page.screenshot({ path: '/tmp/clerk-before-signin.png' })
    
    // Check if Clerk is loaded
    const clerkLoaded = await page.evaluate(() => {
      return {
        windowClerk: typeof (window as any).Clerk !== 'undefined',
        clerkLoaded: (window as any).Clerk?.loaded,
      }
    })
    console.log('Clerk load status:', clerkLoaded)

    // Sign in using Clerk testing
    // Using the actual test user email (not +clerk_test) since the user exists
    const email = process.env.E2E_CLERK_USER_EMAIL || 'test-e2e@papertrade.dev'
    const password = process.env.E2E_CLERK_USER_PASSWORD || 'test-clerk-password'
    
    console.log(`Attempting to sign in with email: ${email}`)

    await clerk.signIn({
      page,
      signInParams: {
        strategy: 'password',
        identifier: email,
        password: password,
      },
    }, { timeout: 60000 }) // Increase timeout to 60 seconds
    
    console.log('Sign in completed')

    // Wait a bit for redirect
    await page.waitForTimeout(3000)
    
    // Check if we're authenticated (should see dashboard or user button)
    const url = page.url()
    console.log(`Current URL: ${url}`)
    
    // Take a screenshot for debugging
    await page.screenshot({ path: '/tmp/clerk-after-signin.png' })
    
    // Verify we're signed in (should be on a page that requires auth)
    // Could be dashboard or the app homepage if signed in
    const isAuthenticated = url.includes('/dashboard') || await page.locator('[data-testid="user-button"]').isVisible().catch(() => false)
    expect(isAuthenticated).toBeTruthy()
  })
})
