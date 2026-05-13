/**
 * E2E for the admin data-coverage page (Phase J / Task #212 Layer 4).
 *
 * Smoke-only: the deep coverage of the gap-counting + idempotency logic
 * lives in the backend integration tests. Here we exercise the wire-
 * through:
 *
 * 1. Navigate to `/admin/data-coverage`.
 * 2. Page header renders + the table loads (or empty state shows).
 * 3. If at least one ticker is present, clicking the row's Backfill
 *    button opens the modal and the form is submittable.
 *
 * Note: the test signs in via the standard fixture (which signs in as
 * the E2E test user). For the admin endpoints to return 200 the test
 * user needs to be in `ADMIN_USER_IDS` on the local backend — if it
 * isn't, the page renders the auth-error block, which we also accept.
 */
import { test, expect } from './fixtures'

test.describe('Admin data-coverage', () => {
  test('renders the data-coverage page', async ({ page }) => {
    await page.goto('/admin/data-coverage')
    await page.waitForLoadState('networkidle')

    // Page hero renders regardless of auth outcome.
    await expect(
      page.getByRole('heading', { name: /^Data coverage$/i, level: 1 })
    ).toBeVisible()

    // One of: error block (non-admin user), empty state (no tickers
    // seeded), or the table (tickers present). All three are valid
    // smoke-test outcomes — we only assert the page rendered.
    const errorVisible = await page
      .getByTestId('admin-data-coverage-error')
      .isVisible()
      .catch(() => false)
    const emptyVisible = await page
      .getByTestId('admin-data-coverage-empty')
      .isVisible()
      .catch(() => false)
    const tableVisible = await page
      .getByTestId('admin-data-coverage-table')
      .isVisible()
      .catch(() => false)

    expect(errorVisible || emptyVisible || tableVisible).toBe(true)
  })

  test('opens the backfill modal when a row is present', async ({ page }) => {
    await page.goto('/admin/data-coverage')
    await page.waitForLoadState('networkidle')

    const tableVisible = await page
      .getByTestId('admin-data-coverage-table')
      .isVisible()
      .catch(() => false)

    if (!tableVisible) {
      test.info().annotations.push({
        type: 'skip-reason',
        description:
          'No tickers in coverage; skipping the modal exercise. The empty-state path is covered separately.',
      })
      test.skip(true)
      return
    }

    // Click the first row's Backfill button.
    const firstButton = page
      .locator('[data-testid^="coverage-backfill-btn-"]')
      .first()
    await firstButton.click()

    await expect(page.getByTestId('backfill-form')).toBeVisible({
      timeout: 5_000,
    })
    await expect(page.getByTestId('backfill-submit-btn')).toBeVisible()

    // Cancel out (we don't actually fire the mutation in this smoke).
    await page.getByTestId('backfill-cancel-btn').click()
    await expect(page.getByTestId('backfill-form')).not.toBeVisible({
      timeout: 5_000,
    })
  })
})
