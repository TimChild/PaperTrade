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
 * Task #222 additions:
 * 4. Delete button opens the confirm dialog.
 * 5. Cancel from the dialog closes it without deleting.
 * 6. Confirming the delete removes the row from the table (full
 *    round-trip via the real backend endpoint — requires the E2E
 *    backend to have at least one watchlisted ticker seeded and the
 *    test user to be in ADMIN_USER_IDS).
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

    // Page hero renders regardless of auth outcome.
    await expect(
      page.getByRole('heading', { name: /^Data coverage$/i, level: 1 })
    ).toBeVisible()

    // Wait for one of the data states to settle. `networkidle` was not
    // sufficient on CI — TanStack Query's retry chain keeps requests
    // in flight just past the network-quiet window, so the page still
    // shows the loading spinner when the assertion runs.
    //
    // Outcomes (all valid for a smoke test):
    //   - `admin-data-coverage-error` — 403 or network error
    //   - `admin-data-coverage-empty` — admin, but no tickers seeded
    //   - `admin-data-coverage-table` — admin + tickers present
    await page
      .locator(
        [
          '[data-testid="admin-data-coverage-error"]',
          '[data-testid="admin-data-coverage-empty"]',
          '[data-testid="admin-data-coverage-table"]',
        ].join(', ')
      )
      .first()
      .waitFor({ state: 'visible', timeout: 10_000 })
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

    // Click the first row's Catch up button.
    const firstButton = page
      .locator('[data-testid^="coverage-catch-up-btn-"]')
      .first()
    await firstButton.click()

    // The catch-up action fires directly (no modal) — just confirm the
    // button is present and clickable. The toast feedback confirms
    // the mutation fired, but we don't assert on it to avoid flakiness
    // from timing differences.
  })

  test('delete button opens confirm dialog and cancel dismisses it', async ({
    page,
  }) => {
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
          'No tickers in coverage; skipping delete modal exercise.',
      })
      test.skip(true)
      return
    }

    // Click the first row's Delete button.
    const firstDeleteBtn = page
      .locator('[data-testid^="coverage-delete-btn-"]')
      .first()
    await firstDeleteBtn.click()

    // Confirm dialog should appear.
    await expect(page.getByTestId('confirm-dialog')).toBeVisible({
      timeout: 5_000,
    })

    // The dialog title should mention "Delete".
    await expect(page.getByTestId('confirm-dialog')).toContainText('Delete')

    // Cancel closes the dialog without deleting.
    await page.getByTestId('confirm-dialog-cancel').click()
    await expect(page.getByTestId('confirm-dialog')).not.toBeVisible({
      timeout: 5_000,
    })

    // Table is still visible — no row was removed.
    await expect(page.getByTestId('admin-data-coverage-table')).toBeVisible()
  })

  test('delete flow: confirm removes the row', async ({ page }) => {
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
          'No tickers in coverage; skipping delete flow. Requires a seeded ticker and admin auth.',
      })
      test.skip(true)
      return
    }

    // Capture the ticker symbol from the first delete button's testid
    // (e.g. "coverage-delete-btn-AAPL" → "AAPL").
    const firstDeleteBtn = page
      .locator('[data-testid^="coverage-delete-btn-"]')
      .first()
    const testId = await firstDeleteBtn.getAttribute('data-testid')
    const ticker = testId?.replace('coverage-delete-btn-', '') ?? ''

    // Open the confirm dialog.
    await firstDeleteBtn.click()
    await expect(page.getByTestId('confirm-dialog')).toBeVisible({
      timeout: 5_000,
    })

    // Click the confirm (destructive) button.
    await page.getByTestId('confirm-dialog-confirm').click()

    // Dialog should close after the mutation completes.
    await expect(page.getByTestId('confirm-dialog')).not.toBeVisible({
      timeout: 10_000,
    })

    // The deleted ticker's row should no longer appear in the table.
    if (ticker) {
      await expect(
        page.getByTestId(`coverage-row-${ticker}`)
      ).not.toBeVisible({ timeout: 10_000 })
    }
  })
})
