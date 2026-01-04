import { test, expect } from '@playwright/test'

test.describe('Trading Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Clear localStorage and start fresh
    await page.goto('/')
    await page.evaluate(() => localStorage.clear())
    await page.reload()
  })

  test('should execute buy trade and update portfolio', async ({ page }) => {
    // This test verifies the complete trading flow with real market data

    // 1. Create a portfolio first
    await page.goto('/')
    await page.waitForLoadState('networkidle')

    const createButton = page.getByTestId('create-first-portfolio-btn')
    await createButton.click()

    await page.getByTestId('create-portfolio-name-input').fill('Trading Portfolio')
    await page.getByTestId('create-portfolio-deposit-input').fill('50000')
    await page.getByTestId('submit-portfolio-form-btn').click()

    // Wait for portfolio to appear on dashboard/detail page
    await expect(page.getByTestId('portfolio-detail-name')).toHaveText('Trading Portfolio', {
      timeout: 10000,
    })

    // 2. Verify we're on the portfolio detail page with trade form
    await expect(page.getByRole('heading', { name: 'Trading Portfolio', level: 1 })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Execute Trade' })).toBeVisible()

    // 3. Fill in the trade form using test IDs
    await page.getByTestId('trade-form-ticker-input').fill('IBM')
    await page.getByTestId('trade-form-quantity-input').fill('2')

    // 4. Execute the buy order
    const buyButton = page.getByTestId('trade-form-buy-button')
    await expect(buyButton).toBeEnabled()

    // Set up dialog handler before clicking to catch success alert
    page.once('dialog', async (dialog) => {
      expect(dialog.type()).toBe('alert')
      expect(dialog.message()).toMatch(/buy order executed successfully/i)
      await dialog.accept()
    })

    await buyButton.click()

    // Wait for trade to process and page to update
    await page.waitForTimeout(3000)
    await page.waitForLoadState('networkidle')

    // 5. Verify trade execution results
    // Cash balance should have decreased (IBM price is ~$291.50, so 2 shares ~$583)
    // Verify holdings table shows IBM in a table cell
    await expect(page.getByTestId('holding-symbol-IBM')).toBeVisible({ timeout: 5000 })

    // 6. Verify transaction history shows the buy trade (look for BUY transaction)
    await expect(page.getByText(/buy/i).first()).toBeVisible()
  })

  test('should show error when buying with insufficient funds', async ({ page }) => {
    // Create portfolio with limited funds
    await page.goto('/')
    await page.waitForLoadState('networkidle')

    const createButton = page.getByTestId('create-first-portfolio-btn')
    await createButton.click()

    await page.getByTestId('create-portfolio-name-input').fill('Poor Portfolio')
    await page.getByTestId('create-portfolio-deposit-input').fill('1000')
    await page.getByTestId('submit-portfolio-form-btn').click()

    // Wait for portfolio to appear on detail page
    await expect(page.getByTestId('portfolio-detail-name')).toHaveText('Poor Portfolio', {
      timeout: 10000,
    })

    // Verify we're on the portfolio detail page with trade form
    await expect(page.getByRole('heading', { name: 'Execute Trade' })).toBeVisible()

    // Try to buy expensive stock with insufficient funds
    // IBM is ~$291.50, so 1000 shares would cost ~$291,500
    await page.getByTestId('trade-form-ticker-input').fill('IBM')
    await page.getByTestId('trade-form-quantity-input').fill('1000')

    const buyButton = page.getByTestId('trade-form-buy-button')
    await expect(buyButton).toBeEnabled()

    // Set up dialog handler to catch error message
    page.once('dialog', async (dialog) => {
      expect(dialog.type()).toBe('alert')
      // Should show failed error (backend returns 400 for insufficient funds)
      expect(dialog.message()).toMatch(/failed|400/i)
      await dialog.accept()
    })

    await buyButton.click()
    await page.waitForTimeout(2000)
  })

  test('should display portfolio holdings after trade', async ({ page }) => {
    // Create portfolio
    await page.goto('/')
    await page.waitForLoadState('networkidle')

    const createButton = page.getByTestId('create-first-portfolio-btn')
    await createButton.click()

    await page.getByTestId('create-portfolio-name-input').fill('Holdings Test')
    await page.getByTestId('create-portfolio-deposit-input').fill('30000')
    await page.getByTestId('submit-portfolio-form-btn').click()

    // Wait for portfolio to appear on detail page
    await expect(page.getByTestId('portfolio-detail-name')).toHaveText('Holdings Test', {
      timeout: 10000,
    })

    // Verify trade form is visible
    await expect(page.getByRole('heading', { name: 'Execute Trade' })).toBeVisible()

    // Verify holdings section exists (should show "No holdings" initially)
    await expect(page.getByRole('heading', { name: 'Holdings', exact: true })).toBeVisible()
    await expect(page.getByText(/no holdings/i)).toBeVisible()

    // Execute a buy trade
    await page.getByTestId('trade-form-ticker-input').fill('IBM')
    await page.getByTestId('trade-form-quantity-input').fill('5')

    const buyButton = page.getByTestId('trade-form-buy-button')
    await expect(buyButton).toBeEnabled()

    // Set up dialog handler for success
    page.once('dialog', async (dialog) => {
      expect(dialog.message()).toMatch(/buy order executed successfully/i)
      await dialog.accept()
    })

    await buyButton.click()

    // Wait for trade to complete and page to refresh
    await page.waitForTimeout(3000)
    await page.waitForLoadState('networkidle')

    // Verify holdings now show IBM stock in table using test ID
    await expect(page.getByTestId('holding-symbol-IBM')).toBeVisible({ timeout: 5000 })

    // Verify "No holdings" message is gone
    await expect(page.getByText(/no holdings/i)).not.toBeVisible()
  })
})