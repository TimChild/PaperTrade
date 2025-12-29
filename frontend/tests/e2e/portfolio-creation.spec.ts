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
    const createButton = page.getByRole('button', { name: /create.*portfolio/i })
    await createButton.click()

    // 4. Fill out form
    await page.getByLabel(/portfolio name/i).fill('My Test Portfolio')
    await page.getByLabel(/initial deposit/i).fill('10000')

    // 5. Submit
    await page.getByRole('button', { name: /create portfolio/i }).last().click()

    // 6. Wait for navigation or success (portfolio should appear)
    // Give it time to create and redirect
    await page.waitForTimeout(2000)

    // 7. Verify portfolio appears (either in list or we're on detail page)
    await expect(
      page.getByText('My Test Portfolio').or(page.getByText(/\$10,000/))
    ).toBeVisible({ timeout: 10000 })
  })

  test('should persist portfolio after page refresh', async ({ page }) => {
    // This test would have caught Bug #1 (user ID persistence) from Task 016

    // Create portfolio
    await page.goto('/')
    await page.waitForLoadState('networkidle')

    const createButton = page.getByRole('button', { name: /create.*portfolio/i })
    await createButton.click()

    await page.getByLabel(/portfolio name/i).fill('Persistent Portfolio')
    await page.getByLabel(/initial deposit/i).fill('25000')
    await page.getByRole('button', { name: /create portfolio/i }).last().click()

    // Wait for portfolio to be created
    await page.waitForTimeout(2000)

    // Refresh page
    await page.reload()
    await page.waitForLoadState('networkidle')

    // Portfolio should still be visible
    await expect(page.getByText('Persistent Portfolio').or(page.getByText(/\$25,000/))).toBeVisible({
      timeout: 10000,
    })
  })

  test('should show validation error for empty portfolio name', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')

    const createButton = page.getByRole('button', { name: /create.*portfolio/i })
    await createButton.click()

    // Try to submit without entering name
    await page.getByLabel(/initial deposit/i).fill('10000')
    await page.getByRole('button', { name: /create portfolio/i }).last().click()

    // Should see validation error or form should not submit
    // HTML5 validation should kick in
    await expect(page.getByLabel(/portfolio name/i)).toBeFocused()
  })

  test('should show validation error for invalid deposit amount', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')

    const createButton = page.getByRole('button', { name: /create.*portfolio/i })
    await createButton.click()

    await page.getByLabel(/portfolio name/i).fill('Test Portfolio')
    await page.getByLabel(/initial deposit/i).fill('-1000')
    await page.getByRole('button', { name: /create portfolio/i }).last().click()

    // Should see validation error
    await expect(page.getByText(/positive number/i).or(page.getByText(/error/i))).toBeVisible({
      timeout: 5000,
    })
  })
})
