import { test, expect } from './fixtures'

test.describe('Dark Mode Toggle', () => {
  test('Theme toggle changes theme correctly', async ({ page }) => {
    // Navigate to dashboard
    await page.goto('/dashboard')
    await page.waitForLoadState('networkidle')

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
    // Navigate to dashboard
    await page.goto('/dashboard')
    await page.waitForLoadState('networkidle')

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
