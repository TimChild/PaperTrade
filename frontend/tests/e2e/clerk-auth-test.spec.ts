import { test, expect } from './fixtures'

test.describe('Clerk Auth Test', () => {
  test('should authenticate with Clerk and access protected API', async ({ page }) => {
    // Navigate to dashboard - already authenticated via shared state
    await page.goto('/dashboard')
    await page.waitForLoadState('networkidle')

    // Verify user is authenticated in Clerk
    const clerkUserState = await page.evaluate(() => {
      const clerkWindow = window as unknown as { Clerk?: { user?: { id: string } } }
      return {
        hasUser: clerkWindow.Clerk?.user !== null && clerkWindow.Clerk?.user !== undefined,
        userId: clerkWindow.Clerk?.user?.id,
      }
    })
    expect(clerkUserState.hasUser).toBe(true)
    expect(clerkUserState.userId).toBeTruthy()

    // Verify the page loaded successfully (no auth errors)
    const pageContent = await page.textContent('body')
    expect(pageContent).not.toContain('Not authenticated')
  })
})
