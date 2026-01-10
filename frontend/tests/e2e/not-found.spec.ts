import { clerk } from '@clerk/testing/playwright'
import { test, expect } from './fixtures'

test.describe('NotFound Page', () => {
  test.beforeEach(async ({ page }) => {
    const email = process.env.E2E_CLERK_USER_EMAIL || 'test-e2e@papertrade.dev'

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

  test('should have working "Go Back" button', async ({ page }) => {
    // Start at dashboard
    await page.goto('/dashboard')
    await page.waitForLoadState('networkidle')

    // Navigate to invalid route
    await page.goto('/invalid-route')
    await page.waitForLoadState('networkidle')

    // Click "Go Back" button
    await page.getByRole('button', { name: /go back/i }).click()

    // Should return to dashboard
    await page.waitForURL('**/dashboard', { timeout: 5000 })
  })

  test('should have working "Return to Dashboard" button', async ({ page }) => {
    // Navigate to invalid route
    await page.goto('/some-invalid-page')
    await page.waitForLoadState('networkidle')

    // Click "Return to Dashboard" button
    await page.getByRole('button', { name: /return to dashboard/i }).click()

    // Should navigate to dashboard
    await page.waitForURL('**/dashboard', { timeout: 5000 })
  })

  test('should display helpful links', async ({ page }) => {
    await page.goto('/not-a-real-page')
    await page.waitForLoadState('networkidle')

    // Should see helpful links section
    await expect(page.getByText(/looking for something specific/i)).toBeVisible()
    await expect(page.getByText(/view your portfolios/i)).toBeVisible()
  })

  test('should be accessible', async ({ page }) => {
    await page.goto('/invalid-route')
    await page.waitForLoadState('networkidle')

    // Check for proper heading structure
    const h1 = page.locator('h1')
    await expect(h1).toBeVisible()

    // Check for buttons
    const buttons = page.locator('button')
    expect(await buttons.count()).toBeGreaterThan(0)
  })
})
