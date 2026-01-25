import { test, expect } from './fixtures'

test.describe('Portfolio Creation Flow', () => {
  test('should create portfolio and navigate to portfolio detail page', async ({ page }) => {
    // This test verifies the portfolio creation flow and navigation to the new portfolio

    // 1. Navigate to dashboard
    await page.goto('/dashboard')
    await page.waitForLoadState('networkidle')

    // 2. Click create portfolio button (header button if portfolios exist, otherwise empty state button)
    const headerButton = page.getByTestId('create-portfolio-header-btn')
    const emptyStateButton = page.getByTestId('create-first-portfolio-btn')
    const createButton = (await headerButton.isVisible()) ? headerButton : emptyStateButton
    await createButton.click()

    // Use unique name to avoid conflicts with previous test runs
    const portfolioName = `Test Portfolio ${Date.now()}`

    // 3. Fill out form
    await page.getByTestId('create-portfolio-name-input').fill(portfolioName)
    await page.getByTestId('create-portfolio-deposit-input').fill('10000')

    // Log current URL before submission
    console.log('[TEST] URL before submit:', page.url())

    // 4. Submit
    await page.getByTestId('submit-portfolio-form-btn').click()

    // Wait a moment for the submission to process
    await page.waitForTimeout(1000)
    console.log('[TEST] URL after submit:', page.url())

    // Check for any error messages
    const errorElements = await page.locator('[role="alert"]').all()
    if (errorElements.length > 0) {
      for (const error of errorElements) {
        const text = await error.textContent()
        console.log('[TEST] Error message found:', text)
      }
    }

    // 5. Should navigate to the new portfolio's detail page
    await page.waitForURL('**/portfolio/*', { timeout: 10000 })

    // 6. Verify we're on the portfolio detail page with the correct name
    await expect(page.getByTestId('portfolio-detail-name')).toHaveText(portfolioName, {
      timeout: 10000,
    })

    // 7. Verify the initial deposit is reflected in the cash balance
    await expect(page.getByTestId('portfolio-cash-balance')).toHaveText('$10,000.00', {
      timeout: 5000,
    })
  })


  test('should persist portfolio after page refresh', async ({ page }) => {
    // This test verifies portfolio data persists correctly

    // Create portfolio from dashboard
    await page.goto('/dashboard')
    await page.waitForLoadState('networkidle')

    // Click create portfolio button (header button if portfolios exist, otherwise empty state button)
    const headerButton = page.getByTestId('create-portfolio-header-btn')
    const emptyStateButton = page.getByTestId('create-first-portfolio-btn')
    const createButton = (await headerButton.isVisible()) ? headerButton : emptyStateButton
    await createButton.click()

    // Use unique name to avoid conflicts with previous test runs
    const portfolioName = `Persistent ${Date.now()}`

    await page.getByTestId('create-portfolio-name-input').fill(portfolioName)
    await page.getByTestId('create-portfolio-deposit-input').fill('25000')
    await page.getByTestId('submit-portfolio-form-btn').click()

    // Wait for navigation to portfolio detail page
    await page.waitForURL('**/portfolio/*', { timeout: 10000 })

    // Verify we're on the correct portfolio page
    await expect(page.getByTestId('portfolio-detail-name')).toHaveText(portfolioName)

    // Refresh page
    await page.reload()
    await page.waitForLoadState('networkidle')

    // Portfolio should still be visible with the same name after refresh
    await expect(page.getByTestId('portfolio-detail-name')).toHaveText(portfolioName, {
      timeout: 10000,
    })

    // Verify the balance persisted
    await expect(page.getByTestId('portfolio-cash-balance')).toHaveText('$25,000.00', {
      timeout: 5000,
    })
  })


  test('should show validation error for empty portfolio name', async ({ page }) => {
    await page.goto('/dashboard')
    await page.waitForLoadState('networkidle')

    // Click create portfolio button (header button if portfolios exist, otherwise empty state button)
    const headerButton = page.getByTestId('create-portfolio-header-btn')
    const emptyStateButton = page.getByTestId('create-first-portfolio-btn')
    const createButton = (await headerButton.isVisible()) ? headerButton : emptyStateButton
    await createButton.click()

    // Try to submit without entering name
    await page.getByTestId('create-portfolio-deposit-input').fill('10000')
    await page.getByTestId('submit-portfolio-form-btn').click()

    // Should see validation error or form should not submit
    // HTML5 validation should kick in
    await expect(page.getByTestId('create-portfolio-name-input')).toBeFocused()
  })

  test('should show validation error for invalid deposit amount', async ({ page }) => {
    await page.goto('/dashboard')
    await page.waitForLoadState('networkidle')

    // Click create portfolio button (header button if portfolios exist, otherwise empty state button)
    const headerButton = page.getByTestId('create-portfolio-header-btn')
    const emptyStateButton = page.getByTestId('create-first-portfolio-btn')
    const createButton = (await headerButton.isVisible()) ? headerButton : emptyStateButton
    await createButton.click()

    await page.getByTestId('create-portfolio-name-input').fill('Test Portfolio')
    await page.getByTestId('create-portfolio-deposit-input').fill('-1000')
    await page.getByTestId('submit-portfolio-form-btn').click()

    // Should see validation error
    await expect(page.getByText(/positive number/i).or(page.getByText(/error/i))).toBeVisible({
      timeout: 5000,
    })
  })
})
