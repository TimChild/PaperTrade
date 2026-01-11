import { clerk } from '@clerk/testing/playwright'
import { test, expect } from './fixtures'

test.describe('Dark Mode Toggle', () => {
  test.beforeEach(async ({ page }) => {
    const email = process.env.E2E_CLERK_USER_EMAIL || 'test-e2e@papertrade.dev'

    // Navigate to app and authenticate
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    await clerk.signIn({ page, emailAddress: email })
    await page.waitForURL('**/dashboard', { timeout: 10000 })
  })

  test('Theme toggle changes theme correctly', async ({ page }) => {
    // Click dark mode button
    await page.getByTestId('theme-toggle-dark').click()

    // Check that dark class is applied to html element
    const htmlElement = page.locator('html')
    await expect(htmlElement).toHaveClass(/dark/)

    // Verify theme persisted to localStorage
    const storedTheme = await page.evaluate(() => localStorage.getItem('theme'))
    expect(storedTheme).toBe('dark')
  })

  test('Theme persists across page reloads', async ({ page }) => {
    // Set dark mode
    await page.getByTestId('theme-toggle-dark').click()
    await expect(page.locator('html')).toHaveClass(/dark/)

    // Reload the page
    await page.reload()
    await page.waitForLoadState('networkidle')

    // Dark mode should still be active
    await expect(page.locator('html')).toHaveClass(/dark/)
  })
})
