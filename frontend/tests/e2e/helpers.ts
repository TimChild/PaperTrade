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

  console.log('[E2E Helper] Starting authentication...')
  console.log('[E2E Helper] Email:', email)

  // Navigate to app first - Clerk needs to be loaded
  console.log('[E2E Helper] Navigating to homepage...')
  await page.goto('/')
  await page.waitForLoadState('networkidle')

  // Sign in using email-based approach (creates sign-in token via backend API)
  console.log('[E2E Helper] Calling clerk.signIn...')
  await clerk.signIn({
    page,
    emailAddress: email,
  })

  // Wait for authentication to complete and redirect to dashboard
  console.log('[E2E Helper] Waiting for redirect to dashboard...')
  await page.waitForURL('**/dashboard', { timeout: 10000 })
  console.log('[E2E Helper] Authentication complete!')
}

/**
 * Click the create portfolio button (handles both header and empty state buttons)
 * @param page - Playwright page object
 */
export async function clickCreatePortfolioButton(page: Page): Promise<void> {
  console.log('[E2E Helper] Looking for create portfolio button...')
  const headerButton = page.getByTestId('create-portfolio-header-btn')
  const emptyStateButton = page.getByTestId('create-first-portfolio-btn')

  const headerVisible = await headerButton.isVisible()
  console.log('[E2E Helper] Header button visible:', headerVisible)

  const createButton = headerVisible ? headerButton : emptyStateButton
  console.log('[E2E Helper] Clicking create portfolio button...')
  await createButton.click()
  console.log('[E2E Helper] Button clicked!')
}
