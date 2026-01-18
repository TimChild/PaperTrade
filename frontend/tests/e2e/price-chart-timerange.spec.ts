import { test, expect } from './fixtures'

test.describe('Price Chart Time Range Selection', () => {
  let portfolioId: string

  test.beforeEach(async ({ page }) => {
    // Create a test portfolio
    await page.goto('/dashboard')
    await page.waitForLoadState('networkidle')

    // Click create portfolio button
    const headerButton = page.getByTestId('create-portfolio-header-btn')
    const emptyStateButton = page.getByTestId('create-first-portfolio-btn')
    const createButton = (await headerButton.isVisible())
      ? headerButton
      : emptyStateButton
    await createButton.click()

    const portfolioName = `Price Chart Test ${Date.now()}`
    await page.getByTestId('create-portfolio-name-input').fill(portfolioName)
    await page.getByTestId('create-portfolio-deposit-input').fill('10000')
    await page.getByTestId('submit-portfolio-form-btn').click()

    // Wait for navigation to portfolio detail
    await page.waitForURL('**/portfolio/*', { timeout: 10000 })

    // Extract portfolio ID from URL
    const url = page.url()
    const match = url.match(/\/portfolio\/([^/]+)/)
    if (match) {
      portfolioId = match[1]
    }

    // Buy some stock to have holdings with price charts
    await page.getByTestId('trade-ticker-input').fill('AAPL')
    await page.getByTestId('trade-quantity-input').fill('10')
    await page.getByTestId('trade-action-buy-btn').click()
    await page.getByTestId('trade-submit-btn').click()

    // Wait for trade to complete
    await page.waitForTimeout(2000)
  })

  test('should switch between time ranges without rate limit errors', async ({
    page,
  }) => {
    // Scroll to holdings section to see price charts
    await page.getByTestId('holdings-table').scrollIntoViewIfNeeded()

    // Wait for price chart to load
    await expect(page.getByTestId('price-chart-AAPL')).toBeVisible({
      timeout: 10000,
    })

    // Rapidly click through all time ranges to test rate limiting behavior
    const timeRanges = ['1D', '1W', '1M', '3M', '1Y', 'ALL']

    for (const range of timeRanges) {
      console.log(`Testing time range: ${range}`)

      // Click the time range button
      await page.getByTestId(`time-range-${range}`).click()

      // Wait a moment for the request to complete
      await page.waitForTimeout(500)

      // Check that we don't get a rate limit error
      const errorElement = page.getByTestId('price-chart-error')
      const isErrorVisible = await errorElement.isVisible().catch(() => false)

      if (isErrorVisible) {
        const errorText = await errorElement.textContent()
        console.log(`Error text for ${range}:`, errorText)

        // If there's an error, it should not be a rate limit error
        // Instead, the chart should show stale data or a helpful message
        expect(errorText).not.toContain('too many requests')
        expect(errorText).not.toContain('rate limit')
      }

      // Verify the chart is still visible (either with data or loading state)
      await expect(page.getByTestId('price-chart-AAPL')).toBeVisible()
    }
  })

  test('should display selected time range button as active', async ({
    page,
  }) => {
    // Scroll to holdings section
    await page.getByTestId('holdings-table').scrollIntoViewIfNeeded()

    // Wait for price chart
    await expect(page.getByTestId('price-chart-AAPL')).toBeVisible({
      timeout: 10000,
    })

    // Default should be 1M
    await expect(page.getByTestId('time-range-1M')).toHaveClass(/active|selected/)

    // Click 3M
    await page.getByTestId('time-range-3M').click()
    await page.waitForTimeout(500)

    // 3M should now be active
    await expect(page.getByTestId('time-range-3M')).toHaveClass(/active|selected/)
  })

  test('should handle rapid time range switching gracefully', async ({
    page,
  }) => {
    // Scroll to holdings section
    await page.getByTestId('holdings-table').scrollIntoViewIfNeeded()

    // Wait for price chart
    await expect(page.getByTestId('price-chart-AAPL')).toBeVisible({
      timeout: 10000,
    })

    // Rapidly switch between ranges without waiting
    await page.getByTestId('time-range-1W').click()
    await page.getByTestId('time-range-3M').click()
    await page.getByTestId('time-range-1Y').click()
    await page.getByTestId('time-range-1M').click()

    // Wait for final request to settle
    await page.waitForTimeout(1000)

    // Chart should still be functional and visible
    await expect(page.getByTestId('price-chart-AAPL')).toBeVisible()

    // No rate limit error should be shown
    const errorElement = page.getByTestId('price-chart-error')
    const isErrorVisible = await errorElement.isVisible().catch(() => false)

    if (isErrorVisible) {
      const errorText = await errorElement.textContent()
      expect(errorText).not.toContain('too many requests')
      expect(errorText).not.toContain('rate limit')
    }
  })
})
