import { clerk } from '@clerk/testing/playwright'
import type { Page } from '@playwright/test'

/**
 * Shared E2E test helpers for common operations
 */

/**
 * Authenticate a user using Clerk email-based sign-in
 * @param page - Playwright page object
 */
export async function authenticateUser(page: Page): Promise<void> {
  const email = process.env.E2E_CLERK_USER_EMAIL
  if (!email) {
    throw new Error('E2E_CLERK_USER_EMAIL environment variable must be set')
  }

  // Navigate to app first - Clerk needs to be loaded
  await page.goto('/')
  await page.waitForLoadState('networkidle')

  // Sign in using email-based approach (creates sign-in token via backend API)
  await clerk.signIn({
    page,
    emailAddress: email,
  })

  // Wait for authentication to complete and redirect to dashboard
  await page.waitForURL('**/dashboard', { timeout: 10000 })
}

/**
 * Click the create portfolio button (handles both header and empty state buttons)
 * @param page - Playwright page object
 */
export async function clickCreatePortfolioButton(page: Page): Promise<void> {
  const headerButton = page.getByTestId('create-portfolio-header-btn')
  const emptyStateButton = page.getByTestId('create-first-portfolio-btn')
  const createButton = (await headerButton.isVisible())
    ? headerButton
    : emptyStateButton
  await createButton.click()
}
