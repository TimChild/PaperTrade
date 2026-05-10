import { test, expect } from './fixtures'

/**
 * E2E coverage for the Settings → API Keys page (Phase H3).
 *
 * The fixture authenticates via Clerk Bearer JWT, which is full-trust on
 * the API-key endpoints (the Clerk-gated path), so no extra setup is
 * needed. Each test uses a unique label so re-runs don't collide.
 */

test.describe('Settings → API Keys', () => {
  test('mints, lists, and revokes an API key', async ({ page }) => {
    const label = `e2e-${Date.now()}`

    // 1. Navigate to the settings page via the top nav
    await page.goto('/dashboard')
    await page.waitForLoadState('networkidle')

    await page.getByRole('link', { name: 'Settings' }).first().click()
    await page.waitForURL('**/settings/api-keys', { timeout: 10_000 })

    // 2. Open the create dialog (page may show empty state or table)
    const headerCreate = page.getByTestId('api-key-create-btn')
    const emptyCreate = page.getByTestId('api-key-empty-create-btn')
    const createButton = (await emptyCreate.isVisible())
      ? emptyCreate
      : headerCreate
    await createButton.click()

    // 3. Fill the form
    await page.getByTestId('api-key-create-label-input').fill(label)
    // Defaults already include read+trade; submit as-is.
    await page.getByTestId('api-key-create-submit-btn').click()

    // 4. Mint result view appears with the raw secret
    await expect(page.getByTestId('api-key-mint-result')).toBeVisible({
      timeout: 10_000,
    })
    const secret = await page
      .getByTestId('api-key-mint-result-value')
      .textContent()
    expect(secret).toBeTruthy()
    expect(secret?.startsWith('zk_')).toBe(true)

    // 5. Acknowledge / close
    await page.getByTestId('api-key-mint-result-done-btn').click()

    // 6. The list now contains a row whose label matches
    await expect(page.getByText(label)).toBeVisible({ timeout: 10_000 })

    // 7. Find the revoke button on that row and click it
    const row = page
      .locator('[data-testid^="api-key-list-row-"]')
      .filter({ hasText: label })
    await expect(row).toHaveCount(1)
    await row.getByRole('button', { name: /revoke/i }).click()

    // 8. Confirm the revoke
    await expect(page.getByTestId('confirm-dialog')).toBeVisible()
    await page.getByTestId('confirm-dialog-confirm').click()

    // 9. Row's status flips to Revoked (we keep the row in the table for audit)
    await expect(row).toHaveCount(1)
    await expect(row.getByText(/revoked/i)).toBeVisible({ timeout: 10_000 })
    // The revoke button is gone for inactive keys
    await expect(row.getByRole('button', { name: /revoke/i })).toHaveCount(0)
  })

  test('validates the form when label is empty', async ({ page }) => {
    await page.goto('/settings/api-keys')
    await page.waitForLoadState('networkidle')

    const headerCreate = page.getByTestId('api-key-create-btn')
    const emptyCreate = page.getByTestId('api-key-empty-create-btn')
    const createButton = (await emptyCreate.isVisible())
      ? emptyCreate
      : headerCreate
    await createButton.click()

    // Click submit without a label
    await page.getByTestId('api-key-create-submit-btn').click()

    await expect(page.getByTestId('api-key-create-label-error')).toBeVisible()
  })
})
