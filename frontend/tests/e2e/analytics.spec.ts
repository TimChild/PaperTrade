import { clerk } from '@clerk/testing/playwright'
import { test, expect } from './fixtures'

test.describe('Portfolio Analytics', () => {
  let portfolioId: string

  test.beforeEach(async ({ page }) => {
    const email = process.env.E2E_CLERK_USER_EMAIL
    if (!email) {
      throw new Error('E2E_CLERK_USER_EMAIL environment variable must be set')
    }

    // Navigate to app first - Clerk needs to be loaded
    await page.goto('/')
    await page.waitForLoadState('networkidle')

    // Sign in using email-based approach
    await clerk.signIn({
      page,
      emailAddress: email,
    })

    // Wait for authentication to complete and redirect to dashboard
    await page.waitForURL('**/dashboard', { timeout: 10000 })

    // Create a test portfolio for analytics tests
    await page.goto('/dashboard')
    await page.waitForLoadState('networkidle')

    // Click create portfolio button
    const headerButton = page.getByTestId('create-portfolio-header-btn')
    const emptyStateButton = page.getByTestId('create-first-portfolio-btn')
    const createButton = (await headerButton.isVisible()) ? headerButton : emptyStateButton
    await createButton.click()

    const portfolioName = `Analytics Test ${Date.now()}`
    await page.getByTestId('create-portfolio-name-input').fill(portfolioName)
    await page.getByTestId('create-portfolio-deposit-input').fill('10000')
    await page.getByTestId('submit-portfolio-form-btn').click()

    // Wait for navigation to portfolio detail
    console.log('Waiting for navigation to portfolio detail page...')
    try {
      await page.waitForURL('**/portfolio/*', { timeout: 10000 })
      console.log('✓ Navigated to portfolio detail:', page.url())
    } catch (error) {
      console.error('✗ Failed to navigate to portfolio detail')
      console.error('Current URL:', page.url())
      console.error('Page title:', await page.title())
      // Take screenshot for debugging
      await page.screenshot({ path: 'test-results/portfolio-creation-timeout.png' })
      throw error
    }

    // Extract portfolio ID from URL
    const url = page.url()
    const match = url.match(/\/portfolio\/([^/]+)/)
    if (match) {
      portfolioId = match[1]
      console.log('✓ Portfolio ID extracted:', portfolioId)
    } else {
      console.error('✗ Failed to extract portfolio ID from URL:', url)
      throw new Error(`Failed to extract portfolio ID from URL: ${url}`)
    }
  })

  test('should navigate to analytics page from portfolio detail', async ({ page }) => {
    // Should be on portfolio detail page from beforeEach
    await expect(page.getByTestId('analytics-tab')).toBeVisible()

    // Click analytics link
    await page.getByTestId('analytics-tab').click()

    // Should navigate to analytics page
    await page.waitForURL(`**/portfolio/${portfolioId}/analytics`, { timeout: 5000 })

    // Verify analytics page is displayed
    await expect(page.getByTestId('portfolio-analytics')).toBeVisible({ timeout: 5000 })
  })

  test('should display analytics components when snapshot data exists', async ({ page }) => {
    // Navigate to analytics page
    await page.goto(`/portfolio/${portfolioId}/analytics`)
    await page.waitForLoadState('networkidle')

    // Verify analytics page loaded
    await expect(page.getByTestId('portfolio-analytics')).toBeVisible()

    // Note: These components may show empty/loading states if no snapshot data exists yet
    // The backend snapshot job needs to run first to populate data

    // Check that components render (even if showing empty states)
    const metricsCards = page
      .getByTestId('metrics-cards-loading')
      .or(page.getByTestId('metrics-cards-empty'))
      .or(page.getByTestId('metrics-cards-error'))
      .or(page.getByTestId('metrics-cards'))
    await expect(metricsCards).toBeVisible()

    const performanceChart = page
      .getByTestId('performance-chart-loading')
      .or(page.getByTestId('performance-chart-empty'))
      .or(page.getByTestId('performance-chart'))
    await expect(performanceChart).toBeVisible()

    const compositionChart = page
      .getByTestId('composition-chart-loading')
      .or(page.getByTestId('composition-chart-empty'))
      .or(page.getByTestId('composition-chart'))
    await expect(compositionChart).toBeVisible()
  })

  test('should display time range selector on performance chart', async ({ page }) => {
    // Navigate to analytics page
    await page.goto(`/portfolio/${portfolioId}/analytics`)
    await page.waitForLoadState('networkidle')

    // Wait for performance chart to load (may show empty state)
    const performanceChart = page
      .getByTestId('performance-chart-loading')
      .or(page.getByTestId('performance-chart-empty'))
      .or(page.getByTestId('performance-chart'))
    await expect(performanceChart).toBeVisible()

    // If chart has data (not empty), check for time range buttons
    const hasData = await page.getByTestId('performance-chart').isVisible()
    if (hasData) {
      await expect(page.getByTestId('range-1W')).toBeVisible()
      await expect(page.getByTestId('range-1M')).toBeVisible()
      await expect(page.getByTestId('range-3M')).toBeVisible()
      await expect(page.getByTestId('range-1Y')).toBeVisible()
      await expect(page.getByTestId('range-ALL')).toBeVisible()
    }
  })

  test('should navigate back to portfolio detail from analytics', async ({ page }) => {
    // Navigate to analytics page
    await page.goto(`/portfolio/${portfolioId}/analytics`)
    await page.waitForLoadState('networkidle')

    // Click back link
    await page.getByTestId('analytics-back-link').click()

    // Should navigate back to portfolio detail
    await page.waitForURL(`**/portfolio/${portfolioId}`, { timeout: 5000 })

    // Verify we're on portfolio detail page
    await expect(page.getByTestId('portfolio-detail-name')).toBeVisible()
  })
})
