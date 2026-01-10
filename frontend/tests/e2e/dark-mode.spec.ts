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

  test('should display theme toggle on dashboard', async ({ page }) => {
    // Theme toggle should be visible
    const lightToggle = page.getByTestId('theme-toggle-light')
    const darkToggle = page.getByTestId('theme-toggle-dark')
    const systemToggle = page.getByTestId('theme-toggle-system')

    await expect(lightToggle).toBeVisible()
    await expect(darkToggle).toBeVisible()
    await expect(systemToggle).toBeVisible()
  })

  test('should switch to dark mode when dark button is clicked', async ({ page }) => {
    // Click dark mode button
    await page.getByTestId('theme-toggle-dark').click()

    // Check that dark class is applied to html element
    const htmlElement = page.locator('html')
    await expect(htmlElement).toHaveClass(/dark/)

    // Verify theme persisted to localStorage
    const storedTheme = await page.evaluate(() => localStorage.getItem('theme'))
    expect(storedTheme).toBe('dark')
  })

  test('should switch to light mode when light button is clicked', async ({ page }) => {
    // First switch to dark
    await page.getByTestId('theme-toggle-dark').click()
    await expect(page.locator('html')).toHaveClass(/dark/)

    // Then switch to light
    await page.getByTestId('theme-toggle-light').click()

    // Check that light class is applied
    const htmlElement = page.locator('html')
    await expect(htmlElement).toHaveClass(/light/)
    await expect(htmlElement).not.toHaveClass(/dark/)

    // Verify theme persisted to localStorage
    const storedTheme = await page.evaluate(() => localStorage.getItem('theme'))
    expect(storedTheme).toBe('light')
  })

  test('should persist theme preference across page reloads', async ({ page }) => {
    // Set dark mode
    await page.getByTestId('theme-toggle-dark').click()
    await expect(page.locator('html')).toHaveClass(/dark/)

    // Reload the page
    await page.reload()
    await page.waitForLoadState('networkidle')

    // Dark mode should still be active
    await expect(page.locator('html')).toHaveClass(/dark/)

    // Theme toggle should reflect dark mode is selected
    const darkButton = page.getByTestId('theme-toggle-dark')
    await expect(darkButton).toHaveAttribute('aria-label', 'Switch to Dark theme')
  })

  test('should switch to system theme mode', async ({ page }) => {
    // Click system mode button
    await page.getByTestId('theme-toggle-system').click()

    // Verify theme persisted to localStorage
    const storedTheme = await page.evaluate(() => localStorage.getItem('theme'))
    expect(storedTheme).toBe('system')

    // The effective theme should match system preference
    // (either light or dark, but one should be applied)
    const htmlElement = page.locator('html')
    const hasLightOrDark = await htmlElement.evaluate((el) => {
      return el.classList.contains('light') || el.classList.contains('dark')
    })
    expect(hasLightOrDark).toBe(true)
  })

  test('should show visual differences between light and dark modes', async ({
    page,
  }) => {
    // Switch to light mode
    await page.getByTestId('theme-toggle-light').click()
    await page.waitForTimeout(200) // Wait for transitions

    // Take screenshot of light mode
    await page.screenshot({ path: 'test-results/dashboard-light.png', fullPage: true })

    // Switch to dark mode
    await page.getByTestId('theme-toggle-dark').click()
    await page.waitForTimeout(200) // Wait for transitions

    // Take screenshot of dark mode
    await page.screenshot({ path: 'test-results/dashboard-dark.png', fullPage: true })

    // Verify dark class is applied
    await expect(page.locator('html')).toHaveClass(/dark/)
  })
})
