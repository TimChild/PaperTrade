import { test, expect } from '@playwright/test'

test.describe('Portfolio Creation Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Clear localStorage to start fresh
    await page.goto('/')
    await page.evaluate(() => localStorage.clear())
    await page.reload()
  })

  test('should create portfolio and show it in dashboard', async ({ page }) => {
    // This test verifies Bug #2 fix (balance endpoint) and Bug #1 (user ID persistence)
    // would have caught the portfolio creation workflow issues

    // 1. Navigate to app
    await page.goto('/')

    // 2. Should see empty state or dashboard
    await page.waitForLoadState('networkidle')

    // 3. Click create portfolio button
    const createButton = page.getByTestId('create-first-portfolio-btn')
    await createButton.click()

    // 4. Fill out form
    await page.getByTestId('create-portfolio-name-input').fill('My Test Portfolio')
    await page.getByTestId('create-portfolio-deposit-input').fill('10000')

    // 5. Submit
    await page.getByTestId('submit-portfolio-form-btn').click()

    // 6. Wait for navigation or success (portfolio should appear)
    // Give it time to create and redirect
    await page.waitForTimeout(2000)

    // 7. Verify portfolio appears by checking for portfolio name heading
    await expect(page.getByTestId('portfolio-detail-name')).toHaveText('My Test Portfolio', {
      timeout: 10000,
    })
  })


  test('should persist portfolio after page refresh', async ({ page }) => {
    // This test would have caught Bug #1 (user ID persistence) from Task 016

    // Create portfolio
    await page.goto('/')
    await page.waitForLoadState('networkidle')

    const createButton = page.getByTestId('create-first-portfolio-btn')
    await createButton.click()

    await page.getByTestId('create-portfolio-name-input').fill('Persistent Portfolio')
    await page.getByTestId('create-portfolio-deposit-input').fill('25000')
    await page.getByTestId('submit-portfolio-form-btn').click()

    // Wait for portfolio to be created
    await page.waitForTimeout(2000)

    // Refresh page
    await page.reload()
    await page.waitForLoadState('networkidle')

    // Portfolio should still be visible by checking for heading
    await expect(page.getByTestId('portfolio-detail-name')).toHaveText('Persistent Portfolio', {
      timeout: 10000,
    })
  })


  test('should show validation error for empty portfolio name', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')

    const createButton = page.getByTestId('create-first-portfolio-btn')
    await createButton.click()

    // Try to submit without entering name
    await page.getByTestId('create-portfolio-deposit-input').fill('10000')
    await page.getByTestId('submit-portfolio-form-btn').click()

    // Should see validation error or form should not submit
    // HTML5 validation should kick in
    await expect(page.getByTestId('create-portfolio-name-input')).toBeFocused()
  })

  test('should show validation error for invalid deposit amount', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')

    const createButton = page.getByTestId('create-first-portfolio-btn')
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
