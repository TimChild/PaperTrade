import { test, expect, clerk } from './fixtures'

test.describe('Trading Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Check for credentials first - fail if not available
    const username = process.env.E2E_CLERK_USER_USERNAME
    const password = process.env.E2E_CLERK_USER_PASSWORD

    if (!username || !password) {
      throw new Error(
        'E2E_CLERK_USER_USERNAME and E2E_CLERK_USER_PASSWORD environment variables are required. ' +
          'Please set them in your environment or GitHub repository variables.'
      )
    }

    // Navigate to app first
    await page.goto('/')

    // Sign in programmatically using Clerk testing helper
    await clerk.signIn({
      page,
      signInParams: {
        strategy: 'password',
        identifier: username,
        password: password,
      },
    })

    // After sign in, go to dashboard
    await page.goto('/dashboard')

    // Clear localStorage and start fresh (portfolios)
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

    // Wait for portfolio to appear on dashboard
    await expect(page.getByRole('heading', { name: 'Trading Portfolio' })).toBeVisible({
      timeout: 10000,
    })

    // 2. Navigate to portfolio detail page to access trade form
    await page.getByTestId('dashboard-trade-stocks-link').click()
    await page.waitForLoadState('networkidle')

    // Verify we're on the portfolio detail page
    await expect(page.getByTestId('portfolio-detail-name')).toHaveText('Trading Portfolio')
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

    // Wait for portfolio to appear on dashboard
    await expect(page.getByRole('heading', { name: 'Poor Portfolio' })).toBeVisible({
      timeout: 10000,
    })

    // Navigate to portfolio detail page
    await page.getByTestId('dashboard-trade-stocks-link').click()
    await page.waitForLoadState('networkidle')

    // Verify we're on the portfolio detail page with trade form
    await expect(page.getByTestId('portfolio-detail-name')).toHaveText('Poor Portfolio')
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

    // Wait for portfolio to appear on dashboard
    await expect(page.getByRole('heading', { name: 'Holdings Test' })).toBeVisible({
      timeout: 10000,
    })

    // Navigate to portfolio detail page
    await page.getByTestId('dashboard-trade-stocks-link').click()
    await page.waitForLoadState('networkidle')

    // Verify we're on the portfolio detail page
    await expect(page.getByTestId('portfolio-detail-name')).toHaveText('Holdings Test')
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

  test('should execute complete buy-sell trading loop', async ({ page }) => {
    // This test verifies the complete trading flow: BUY → SELL

    // Capture console logs for debugging
    page.on('console', msg => {
      console.log(`[Browser ${msg.type()}]:`, msg.text())
    })

    // Capture page errors
    page.on('pageerror', error => {
      console.error('[Browser Error]:', error)
    })

    // 1. Create a portfolio
    await page.goto('/')
    await page.waitForLoadState('networkidle')

    const createButton = page.getByTestId('create-first-portfolio-btn')
    await createButton.click()

    await page.getByTestId('create-portfolio-name-input').fill('Buy-Sell Portfolio')
    await page.getByTestId('create-portfolio-deposit-input').fill('100000')
    await page.getByTestId('submit-portfolio-form-btn').click()

    // Wait for portfolio to appear on dashboard
    await expect(page.getByRole('heading', { name: 'Buy-Sell Portfolio' })).toBeVisible({
      timeout: 10000,
    })

    // 2. Navigate to portfolio detail page
    await page.getByTestId('dashboard-trade-stocks-link').click()
    await page.waitForLoadState('networkidle')

    // Verify we're on the portfolio detail page
    await expect(page.getByTestId('portfolio-detail-name')).toHaveText('Buy-Sell Portfolio')
    await expect(page.getByRole('heading', { name: 'Execute Trade' })).toBeVisible()

    // 3. Execute a BUY order (buy 10 shares of IBM)
    // Note: Using IBM because the Alpha Vantage demo API key only supports IBM ticker
    await page.getByTestId('trade-form-ticker-input').fill('IBM')
    await page.getByTestId('trade-form-quantity-input').fill('10')

    const buyButton = page.getByTestId('trade-form-buy-button')
    await expect(buyButton).toBeEnabled()

    // Set up dialog handler for buy success
    page.once('dialog', async (dialog) => {
      expect(dialog.message()).toMatch(/buy order executed successfully/i)
      await dialog.accept()
    })

    await buyButton.click()

    // Wait for trade to complete
    await page.waitForTimeout(3000)
    await page.waitForLoadState('networkidle')

    // 4. Verify holding shows 10 shares
    await expect(page.getByTestId('holding-symbol-IBM')).toBeVisible({ timeout: 5000 })
    await expect(page.getByTestId('holding-quantity-IBM')).toHaveText('10')

    // 5. Execute a SELL order (sell 5 shares of IBM)
    // Switch to SELL action
    await page.getByTestId('trade-form-action-sell').click()

    // Fill in ticker and quantity
    await page.getByTestId('trade-form-ticker-input').fill('IBM')
    await page.getByTestId('trade-form-quantity-input').fill('5')

    // Verify holdings info is displayed
    await expect(page.getByTestId('trade-form-holdings-info')).toBeVisible()
    await expect(page.getByText(/You own.*10.*shares of IBM/i)).toBeVisible()

    const sellButton = page.getByTestId('trade-form-sell-button')
    await expect(sellButton).toBeEnabled()

    // Set up dialog handler for sell success
    page.once('dialog', async (dialog) => {
      expect(dialog.message()).toMatch(/sell order executed successfully/i)
      await dialog.accept()
    })

    await sellButton.click()

    // Wait for trade to complete
    await page.waitForTimeout(3000)
    await page.waitForLoadState('networkidle')

    // 6. Verify holding now shows 5 shares
    await expect(page.getByTestId('holding-symbol-IBM')).toBeVisible({ timeout: 5000 })
    await expect(page.getByTestId('holding-quantity-IBM')).toHaveText('5')

    // 7. Verify transaction history shows both BUY and SELL
    await expect(page.getByText(/buy/i).first()).toBeVisible()
    await expect(page.getByText(/sell/i).first()).toBeVisible()
  })

  test('should show error when trying to sell stock not owned', async ({ page }) => {
    // This test verifies SELL validation: can't sell what you don't own

    // 1. Create a portfolio
    await page.goto('/')
    await page.waitForLoadState('networkidle')

    const createButton = page.getByTestId('create-first-portfolio-btn')
    await createButton.click()

    await page.getByTestId('create-portfolio-name-input').fill('Empty Portfolio')
    await page.getByTestId('create-portfolio-deposit-input').fill('50000')
    await page.getByTestId('submit-portfolio-form-btn').click()

    // Wait for portfolio to appear on dashboard
    await expect(page.getByRole('heading', { name: 'Empty Portfolio' })).toBeVisible({
      timeout: 10000,
    })

    // 2. Navigate to portfolio detail page
    await page.getByTestId('dashboard-trade-stocks-link').click()
    await page.waitForLoadState('networkidle')

    // 3. Try to SELL stock without owning it
    await page.getByTestId('trade-form-action-sell').click()
    await page.getByTestId('trade-form-ticker-input').fill('TSLA')
    await page.getByTestId('trade-form-quantity-input').fill('10')

    // Should show "You don't own any shares" message
    await expect(page.getByTestId('trade-form-no-holdings')).toBeVisible()
    await expect(page.getByText(/You don't own any shares of TSLA/i)).toBeVisible()

    // Submit button should be disabled
    const sellButton = page.getByTestId('trade-form-sell-button')
    await expect(sellButton).toBeDisabled()
  })

  test('should use Quick Sell to pre-fill trade form', async ({ page }) => {
    // This test verifies Quick Sell functionality

    // 1. Create a portfolio and buy some stock
    await page.goto('/')
    await page.waitForLoadState('networkidle')

    const createButton = page.getByTestId('create-first-portfolio-btn')
    await createButton.click()

    await page.getByTestId('create-portfolio-name-input').fill('Quick Sell Test')
    await page.getByTestId('create-portfolio-deposit-input').fill('100000')
    await page.getByTestId('submit-portfolio-form-btn').click()

    await expect(page.getByRole('heading', { name: 'Quick Sell Test' })).toBeVisible({
      timeout: 10000,
    })

    await page.getByTestId('dashboard-trade-stocks-link').click()
    await page.waitForLoadState('networkidle')

    // Buy 20 shares of MSFT
    await page.getByTestId('trade-form-ticker-input').fill('MSFT')
    await page.getByTestId('trade-form-quantity-input').fill('20')

    const buyButton = page.getByTestId('trade-form-buy-button')

    page.once('dialog', async (dialog) => {
      await dialog.accept()
    })

    await buyButton.click()
    await page.waitForTimeout(3000)
    await page.waitForLoadState('networkidle')

    // 2. Click Quick Sell button
    const quickSellButton = page.getByTestId('holdings-quick-sell-msft')
    await expect(quickSellButton).toBeVisible({ timeout: 5000 })
    await quickSellButton.click()

    // 3. Verify form is pre-filled
    await page.waitForTimeout(500) // Wait for form to update

    // Should switch to SELL action
    const sellActionButton = page.getByTestId('trade-form-action-sell')
    await expect(sellActionButton).toHaveClass(/bg-negative/)

    // Should pre-fill ticker and quantity
    const tickerInput = page.getByTestId('trade-form-ticker-input')
    const quantityInput = page.getByTestId('trade-form-quantity-input')

    await expect(tickerInput).toHaveValue('MSFT')
    await expect(quantityInput).toHaveValue('20')

    // Should show holdings info
    await expect(page.getByTestId('trade-form-holdings-info')).toBeVisible()
    await expect(page.getByText(/You own.*20.*shares of MSFT/i)).toBeVisible()
  })
})
