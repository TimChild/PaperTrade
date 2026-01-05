import { clerk } from '@clerk/testing/playwright'
import { test, expect } from './fixtures'

test.describe('Clerk Auth Test', () => {
  test('should authenticate with Clerk and access protected API', async ({ page }) => {
    const email = process.env.E2E_CLERK_USER_EMAIL || 'test-e2e@papertrade.dev'
    
    // Navigate to app first - Clerk must be loaded before signIn
    await page.goto('/')
    await page.waitForLoadState('networkidle')

    // Sign in using email-based approach (creates sign-in token via backend API)
    await clerk.signIn({
      page,
      emailAddress: email,
    })

    // Wait for navigation to dashboard after successful sign-in
    await page.waitForURL('**/dashboard', { timeout: 10000 })
    
    // Verify user is authenticated in Clerk
    const clerkUserState = await page.evaluate(() => {
      return {
        hasUser: (window as any).Clerk?.user !== null && (window as any).Clerk?.user !== undefined,
        userId: (window as any).Clerk?.user?.id,
      }
    })
    expect(clerkUserState.hasUser).toBe(true)
    expect(clerkUserState.userId).toBeTruthy()

    // Verify the page loaded successfully (no auth errors)
    const pageContent = await page.textContent('body')
    expect(pageContent).not.toContain('Not authenticated')
  })
})
