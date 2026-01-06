import { clerk } from '@clerk/testing/playwright'
import { test, expect } from './fixtures'

test.describe('Multi-Portfolio Display', () => {
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
  })

  test('should display all portfolios on dashboard', async ({ page }) => {
    // This test verifies that all portfolios are visible on the dashboard
    
    // Navigate to dashboard
    await page.goto('/dashboard')
    await page.waitForLoadState('networkidle')

    // Get initial portfolio count
    const initialText = await page.getByText(/You have \d+ portfolio/).textContent()
    const initialCount = initialText ? parseInt(initialText.match(/\d+/)?.[0] || '0') : 0

    // Create first test portfolio
    const createButton = page.getByTestId('create-portfolio-header-btn')
    await createButton.click()

    const portfolio1Name = `Multi Test Portfolio 1 ${Date.now()}`
    await page.getByTestId('create-portfolio-name-input').fill(portfolio1Name)
    await page.getByTestId('create-portfolio-deposit-input').fill('10000')
    await page.getByTestId('submit-portfolio-form-btn').click()

    // Wait for navigation to portfolio detail page
    await page.waitForURL('**/portfolio/*', { timeout: 10000 })

    // Go back to dashboard
    await page.goto('/dashboard')
    await page.waitForLoadState('networkidle')

    // Create second test portfolio
    await page.getByTestId('create-portfolio-header-btn').click()

    const portfolio2Name = `Multi Test Portfolio 2 ${Date.now()}`
    await page.getByTestId('create-portfolio-name-input').fill(portfolio2Name)
    await page.getByTestId('create-portfolio-deposit-input').fill('20000')
    await page.getByTestId('submit-portfolio-form-btn').click()

    // Wait for navigation to portfolio detail page
    await page.waitForURL('**/portfolio/*', { timeout: 10000 })

    // Go back to dashboard
    await page.goto('/dashboard')
    await page.waitForLoadState('networkidle')

    // Create third test portfolio
    await page.getByTestId('create-portfolio-header-btn').click()

    const portfolio3Name = `Multi Test Portfolio 3 ${Date.now()}`
    await page.getByTestId('create-portfolio-name-input').fill(portfolio3Name)
    await page.getByTestId('create-portfolio-deposit-input').fill('30000')
    await page.getByTestId('submit-portfolio-form-btn').click()

    // Wait for navigation to portfolio detail page
    await page.waitForURL('**/portfolio/*', { timeout: 10000 })

    // Go back to dashboard
    await page.goto('/dashboard')
    await page.waitForLoadState('networkidle')

    // Verify the portfolio count text
    const expectedCount = initialCount + 3
    await expect(page.getByText(`You have ${expectedCount} portfolio${expectedCount !== 1 ? 's' : ''}`)).toBeVisible()

    // Verify portfolio grid exists
    const portfolioGrid = page.getByTestId('portfolio-grid')
    await expect(portfolioGrid).toBeVisible()

    // Verify all three new portfolios are visible
    await expect(page.getByText(portfolio1Name)).toBeVisible()
    await expect(page.getByText(portfolio2Name)).toBeVisible()
    await expect(page.getByText(portfolio3Name)).toBeVisible()

    // Verify portfolio cards show expected values
    // Portfolio 1 should show $10,000
    await expect(page.locator(`text=${portfolio1Name}`).locator('..').locator('..').getByText('$10,000.00')).toBeVisible()
    
    // Portfolio 2 should show $20,000
    await expect(page.locator(`text=${portfolio2Name}`).locator('..').locator('..').getByText('$20,000.00')).toBeVisible()
    
    // Portfolio 3 should show $30,000
    await expect(page.locator(`text=${portfolio3Name}`).locator('..').locator('..').getByText('$30,000.00')).toBeVisible()
  })

  test('should navigate to portfolio detail when clicking portfolio card', async ({ page }) => {
    // This test verifies that clicking a portfolio card navigates to the detail page

    // Navigate to dashboard
    await page.goto('/dashboard')
    await page.waitForLoadState('networkidle')

    // Create a test portfolio
    const createButton = page.getByTestId('create-portfolio-header-btn')
    const emptyStateButton = page.getByTestId('create-first-portfolio-btn')
    const button = (await createButton.isVisible()) ? createButton : emptyStateButton
    await button.click()

    const portfolioName = `Click Test Portfolio ${Date.now()}`
    await page.getByTestId('create-portfolio-name-input').fill(portfolioName)
    await page.getByTestId('create-portfolio-deposit-input').fill('15000')
    await page.getByTestId('submit-portfolio-form-btn').click()

    // Wait for navigation to portfolio detail page
    await page.waitForURL('**/portfolio/*', { timeout: 10000 })
    const portfolioUrl = page.url()
    const portfolioId = portfolioUrl.split('/').pop()

    // Go back to dashboard
    await page.goto('/dashboard')
    await page.waitForLoadState('networkidle')

    // Click on the portfolio card
    const portfolioCard = page.getByTestId(`portfolio-card-${portfolioId}`)
    await expect(portfolioCard).toBeVisible()
    await portfolioCard.click()

    // Verify navigation to portfolio detail page
    await page.waitForURL(`**/portfolio/${portfolioId}`, { timeout: 10000 })
    await expect(page.getByTestId('portfolio-detail-name')).toHaveText(portfolioName)
  })

  test('should show empty state when no portfolios exist', async ({ page }) => {
    // Note: This test assumes the user might not have portfolios yet
    // In practice, with existing portfolios, we skip this test
    
    await page.goto('/dashboard')
    await page.waitForLoadState('networkidle')

    // Check if portfolios exist
    const hasPortfolios = await page.getByTestId('portfolio-grid').isVisible().catch(() => false)
    
    if (!hasPortfolios) {
      // Verify empty state is shown
      await expect(page.getByText(/No portfolios found/i)).toBeVisible()
      await expect(page.getByTestId('create-first-portfolio-btn')).toBeVisible()
    } else {
      // Skip test if portfolios already exist
      test.skip()
    }
  })
})
