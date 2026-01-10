import { clerk } from '@clerk/testing/playwright'
import { test, expect } from './fixtures'

test.describe('Visual Regression', () => {
  test.beforeEach(async ({ page }) => {
    const email = process.env.E2E_CLERK_USER_EMAIL || 'test-e2e@papertrade.dev'

    // Navigate to app and authenticate
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    await clerk.signIn({ page, emailAddress: email })
    await page.waitForURL('**/dashboard', { timeout: 10000 })
  })

  test('Dashboard light mode screenshot', async ({ page }) => {
    await page.goto('/dashboard')
    await page.waitForLoadState('networkidle')

    // Set light mode
    await page.getByTestId('theme-toggle-light').click()
    await page.waitForTimeout(300) // Wait for theme transition

    await expect(page).toHaveScreenshot('dashboard-light.png', {
      fullPage: true,
      animations: 'disabled',
      mask: [
        // Mask dynamic content that changes between runs
        page.locator('text=/Portfolio.*\\d+/i').first(),
      ],
    })
  })

  test('Dashboard dark mode screenshot', async ({ page }) => {
    await page.goto('/dashboard')
    await page.waitForLoadState('networkidle')

    // Set dark mode
    await page.getByTestId('theme-toggle-dark').click()
    await page.waitForTimeout(300) // Wait for theme transition

    await expect(page).toHaveScreenshot('dashboard-dark.png', {
      fullPage: true,
      animations: 'disabled',
      mask: [
        // Mask dynamic content that changes between runs
        page.locator('text=/Portfolio.*\\d+/i').first(),
      ],
    })
  })

  test('Portfolio Detail light mode screenshot', async ({ page }) => {
    await page.goto('/dashboard')
    await page.waitForLoadState('networkidle')

    // Create portfolio
    const headerButton = page.getByTestId('create-portfolio-header-btn')
    const emptyStateButton = page.getByTestId('create-first-portfolio-btn')
    const createButton = (await headerButton.isVisible()) ? headerButton : emptyStateButton
    await createButton.click()

    const portfolioName = `Visual Test Light ${Date.now()}`
    await page.getByTestId('create-portfolio-name-input').fill(portfolioName)
    await page.getByTestId('create-portfolio-deposit-input').fill('10000')
    await page.getByTestId('submit-portfolio-form-btn').click()

    // Wait for navigation
    await page.waitForURL('**/portfolio/*', { timeout: 10000 })
    await page.waitForLoadState('networkidle')

    // Set light mode
    await page.getByTestId('theme-toggle-light').click()
    await page.waitForTimeout(300)

    await expect(page).toHaveScreenshot('portfolio-detail-light.png', {
      fullPage: true,
      animations: 'disabled',
      mask: [
        // Mask portfolio name which includes timestamp
        page.getByTestId('portfolio-detail-name'),
      ],
    })
  })

  test('Portfolio Detail dark mode screenshot', async ({ page }) => {
    await page.goto('/dashboard')
    await page.waitForLoadState('networkidle')

    // Create portfolio
    const headerButton = page.getByTestId('create-portfolio-header-btn')
    const emptyStateButton = page.getByTestId('create-first-portfolio-btn')
    const createButton = (await headerButton.isVisible()) ? headerButton : emptyStateButton
    await createButton.click()

    const portfolioName = `Visual Test Dark ${Date.now()}`
    await page.getByTestId('create-portfolio-name-input').fill(portfolioName)
    await page.getByTestId('create-portfolio-deposit-input').fill('10000')
    await page.getByTestId('submit-portfolio-form-btn').click()

    // Wait for navigation
    await page.waitForURL('**/portfolio/*', { timeout: 10000 })
    await page.waitForLoadState('networkidle')

    // Set dark mode
    await page.getByTestId('theme-toggle-dark').click()
    await page.waitForTimeout(300)

    await expect(page).toHaveScreenshot('portfolio-detail-dark.png', {
      fullPage: true,
      animations: 'disabled',
      mask: [
        // Mask portfolio name which includes timestamp
        page.getByTestId('portfolio-detail-name'),
      ],
    })
  })

  test('Theme toggle component screenshot', async ({ page }) => {
    await page.goto('/dashboard')
    await page.waitForLoadState('networkidle')

    // Screenshot just the theme toggle area
    const themeToggle = page.locator('[data-testid*="theme-toggle"]').first().locator('..')
    await expect(themeToggle).toHaveScreenshot('theme-toggle.png', {
      animations: 'disabled',
    })
  })
})
