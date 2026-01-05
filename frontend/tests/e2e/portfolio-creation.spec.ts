import { test, expect, clerk } from './fixtures'
import type { Page } from '@playwright/test'

/**
 * Helper function to click the create portfolio button
 * Works whether user has existing portfolios or not
 */
async function clickCreatePortfolioButton(page: Page) {
  const headerButton = page.getByTestId('create-portfolio-header-btn')
  const firstTimeButton = page.getByTestId('create-first-portfolio-btn')

  // Try header button first (always visible if portfolios exist)
  const isHeaderVisible = await headerButton.isVisible({ timeout: 1000 }).catch(() => false)
  if (isHeaderVisible) {
    await headerButton.click()
  } else {
    await firstTimeButton.click()
  }
}

test.describe('Portfolio Creation Flow', () => {
  test.beforeEach(async ({ page }) => {
    const email = process.env.E2E_CLERK_USER_EMAIL
    const password = process.env.E2E_CLERK_USER_PASSWORD

    if (!email || !password) {
      throw new Error(
        'E2E_CLERK_USER_EMAIL and E2E_CLERK_USER_PASSWORD environment variables are required. ' +
          'Please set them in your environment or GitHub repository variables.'
      )
    }

    // Navigate to app first (Clerk must be loaded before signIn can work)
    await page.goto('/')
    await page.waitForLoadState('networkidle')

    // Sign in with Clerk using email (creates sign-in token automatically)
    await clerk.signIn({
      page,
      emailAddress: email,
    })

    // Wait for redirect to dashboard after sign-in
    await page.waitForURL('/dashboard', { timeout: 10000 })
    await page.waitForLoadState('networkidle')
  })

  test('should display create portfolio button', async ({ page }) => {
    // Wait for either create button (header or first-time)
    const headerButton = page.getByTestId('create-portfolio-header-btn')
    const firstTimeButton = page.getByTestId('create-first-portfolio-btn')

    // One of them should be visible
    await expect(headerButton.or(firstTimeButton)).toBeVisible({ timeout: 10000 })
  })

  test('should open create portfolio modal when clicking create button', async ({
    page,
  }) => {
    await clickCreatePortfolioButton(page)

    // Modal should appear
    const modal = page.getByRole('dialog')
    await expect(modal).toBeVisible()
  })

  test('should create a new portfolio successfully', async ({ page }) => {
    await clickCreatePortfolioButton(page)

    // Fill in portfolio name
    const nameInput = page.getByLabel(/name/i)
    await nameInput.fill('Test Portfolio')

    // Fill in initial cash balance
    const cashInput = page.getByLabel(/cash|balance/i)
    await cashInput.fill('10000')

    // Submit the form
    const submitButton = page.getByRole('button', { name: /create/i })
    await submitButton.click()

    // Should see the new portfolio in the list
    await expect(page.getByText('Test Portfolio')).toBeVisible({ timeout: 10000 })
  })

  test('should show validation error for empty portfolio name', async ({ page }) => {
    await clickCreatePortfolioButton(page)

    // Leave name empty and try to submit
    const submitButton = page.getByRole('button', { name: /create/i })
    await submitButton.click()

    // Should see validation error
    await expect(page.getByText(/name.*required|required.*name/i)).toBeVisible()
  })
})
