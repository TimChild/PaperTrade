import { clerk } from '@clerk/testing/playwright'
import { test, expect, devices } from '@playwright/test'

const viewports = {
  mobile: devices['iPhone 12'],
  tablet: devices['iPad Pro'],
  desktop: { viewport: { width: 1920, height: 1080 } },
}

for (const [deviceName, deviceConfig] of Object.entries(viewports)) {
  test.describe(`Responsive Design - ${deviceName}`, () => {
    test.use(deviceConfig)

    test.beforeEach(async ({ page }) => {
      const email = process.env.E2E_CLERK_USER_EMAIL || 'test-e2e@papertrade.dev'

      // Navigate to app and authenticate
      await page.goto('/')
      await page.waitForLoadState('networkidle')
      await clerk.signIn({ page, emailAddress: email })
      await page.waitForURL('**/dashboard', { timeout: 10000 })
    })

    test(`Dashboard renders correctly on ${deviceName}`, async ({ page }) => {
      await page.goto('/dashboard')
      await page.waitForLoadState('networkidle')

      // Verify key elements visible
      await expect(page.getByText(/My Portfolios/i).or(page.getByText(/Portfolio/i))).toBeVisible()

      // Verify theme toggle visible
      const themeToggle = page.getByTestId('theme-toggle-light')
      await expect(themeToggle).toBeVisible()

      // Verify no horizontal scroll
      const bodyWidth = await page.evaluate(() => document.body.scrollWidth)
      const viewportWidth = page.viewportSize()!.width
      expect(bodyWidth).toBeLessThanOrEqual(viewportWidth + 1) // +1 for rounding
    })

    test(`Portfolio Detail renders correctly on ${deviceName}`, async ({ page }) => {
      await page.goto('/dashboard')
      await page.waitForLoadState('networkidle')

      // Create portfolio
      const headerButton = page.getByTestId('create-portfolio-header-btn')
      const emptyStateButton = page.getByTestId('create-first-portfolio-btn')
      const createButton = (await headerButton.isVisible()) ? headerButton : emptyStateButton
      await createButton.click()

      const portfolioName = `Responsive ${deviceName} ${Date.now()}`
      await page.getByTestId('create-portfolio-name-input').fill(portfolioName)
      await page.getByTestId('create-portfolio-deposit-input').fill('10000')
      await page.getByTestId('submit-portfolio-form-btn').click()

      // Wait for navigation to portfolio detail page
      await page.waitForURL('**/portfolio/*', { timeout: 10000 })
      await page.waitForLoadState('networkidle')

      // Verify key sections visible
      await expect(page.getByTestId('portfolio-detail-name')).toBeVisible()
      await expect(page.getByTestId('portfolio-cash-balance')).toBeVisible()

      // Verify no horizontal scroll
      const bodyWidth = await page.evaluate(() => document.body.scrollWidth)
      const viewportWidth = page.viewportSize()!.width
      expect(bodyWidth).toBeLessThanOrEqual(viewportWidth + 1) // +1 for rounding
    })

    test(`Theme toggle works on ${deviceName}`, async ({ page }) => {
      await page.goto('/dashboard')
      await page.waitForLoadState('networkidle')

      // Toggle to dark mode
      await page.getByTestId('theme-toggle-dark').click()
      await page.waitForTimeout(200)

      // Verify dark mode applied
      const htmlElement = page.locator('html')
      await expect(htmlElement).toHaveClass(/dark/)

      // Toggle back to light
      await page.getByTestId('theme-toggle-light').click()
      await page.waitForTimeout(200)

      await expect(htmlElement).not.toHaveClass(/dark/)
    })
  })
}
