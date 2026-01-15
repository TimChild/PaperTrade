import { clerk } from '@clerk/testing/playwright'
import { test, expect } from './fixtures'

test.describe('NotFound Page', () => {
  test.beforeEach(async ({ page }) => {
    const email = process.env.E2E_CLERK_USER_EMAIL || 'test-e2e@zebutrader.com'

    // Navigate to app and authenticate
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    await clerk.signIn({ page, emailAddress: email })
    await page.waitForURL('**/dashboard', { timeout: 10000 })
  })

  test('should display 404 page for invalid route', async ({ page }) => {
    // Navigate to non-existent route
    await page.goto('/this-route-does-not-exist')
    await page.waitForLoadState('networkidle')

    // Should see 404 error
    await expect(page.getByText('404')).toBeVisible()
    await expect(page.getByText(/page not found/i)).toBeVisible()
  })
})
