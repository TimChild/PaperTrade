import { test, expect, clerk } from './fixtures'

test.describe('Portfolio Creation Flow', () => {
  test.beforeEach(async ({ page }) => {
    const username = process.env.E2E_CLERK_USER_USERNAME
    const password = process.env.E2E_CLERK_USER_PASSWORD

    if (!username || !password) {
      throw new Error(
        'E2E_CLERK_USER_USERNAME and E2E_CLERK_USER_PASSWORD environment variables are required. ' +
          'Please set them in your environment or GitHub repository variables.'
      )
    }

    // Sign in with Clerk
    await clerk.signIn({
      page,
      signInParams: {
        strategy: 'password',
        identifier: username,
        password: password,
      },
    })

    // Navigate to home page after sign-in
    await page.goto('/')
    await page.waitForLoadState('networkidle')
  })

  test('should display create portfolio button when no portfolios exist', async ({
    page,
  }) => {
    // Wait for the create portfolio button
    const createButton = page.getByTestId('create-first-portfolio-btn')
    await expect(createButton).toBeVisible({ timeout: 10000 })
  })

  test('should open create portfolio modal when clicking create button', async ({
    page,
  }) => {
    // Click create portfolio button
    const createButton = page.getByTestId('create-first-portfolio-btn')
    await createButton.click()

    // Modal should appear
    const modal = page.getByRole('dialog')
    await expect(modal).toBeVisible()
  })

  test('should create a new portfolio successfully', async ({ page }) => {
    // Click create portfolio button
    const createButton = page.getByTestId('create-first-portfolio-btn')
    await createButton.click()

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
    // Click create portfolio button
    const createButton = page.getByTestId('create-first-portfolio-btn')
    await createButton.click()

    // Leave name empty and try to submit
    const submitButton = page.getByRole('button', { name: /create/i })
    await submitButton.click()

    // Should see validation error
    await expect(page.getByText(/name.*required|required.*name/i)).toBeVisible()
  })
})
