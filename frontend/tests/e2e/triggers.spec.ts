/**
 * E2E for the trigger configuration UI (Phase G-1).
 *
 * Covers the happy path:
 *
 *   create portfolio → create strategy → activate → navigate to activation
 *   detail → attach a trigger → see it in the list → view fires (empty
 *   state) → pause → resume → delete.
 *
 * Builds on the same pattern as `strategy-activation.spec.ts` — the CI E2E
 * backend uses the deterministic mock market data adapter so the activation
 * exists for the trigger to attach to.
 */
import { test, expect } from './fixtures'

test.describe('Trigger Configuration Flow', () => {
  // Multi-step flow: portfolio → strategy → activation → trigger CRUD.
  // Default 60s isn't enough; bump to 180s.
  test.setTimeout(180_000)

  test('attaches, pauses, and deletes a trigger on an activation', async ({
    page,
  }) => {
    // 1. Create a paper-trading portfolio.
    await page.goto('/dashboard')
    await page.waitForLoadState('networkidle')

    const headerButton = page.getByTestId('create-portfolio-header-btn')
    const emptyStateButton = page.getByTestId('create-first-portfolio-btn')
    const createButton = (await headerButton.isVisible())
      ? headerButton
      : emptyStateButton
    await createButton.click()

    const portfolioName = `Trigger Portfolio ${Date.now()}`
    await page.getByTestId('create-portfolio-name-input').fill(portfolioName)
    await page.getByTestId('create-portfolio-deposit-input').fill('100000')
    await page.getByTestId('submit-portfolio-form-btn').click()

    await page.waitForURL('**/portfolio/*', { timeout: 10000 })
    await expect(page.getByTestId('portfolio-detail-name')).toHaveText(
      portfolioName
    )

    // 2. Create a buy-and-hold strategy.
    await page.goto('/strategies')
    await page.waitForLoadState('networkidle')
    await page.getByTestId('create-strategy-button').click()

    await expect(page.getByTestId('create-strategy-form')).toBeVisible({
      timeout: 5000,
    })
    const strategyName = `Trigger Strategy ${Date.now()}`
    await page.getByTestId('strategy-name-input').fill(strategyName)
    await page.getByTestId('strategy-tickers-input').fill('IBM')
    await expect(page.getByTestId('allocation-IBM')).toBeVisible({
      timeout: 5000,
    })
    await page.getByTestId('allocation-IBM').fill('1.0')

    const createResponsePromise = page.waitForResponse(
      (response) =>
        /\/strategies(\?|$)/.test(response.url()) &&
        response.request().method() === 'POST'
    )
    await page.getByTestId('create-strategy-submit').click()
    const createResponse = await createResponsePromise
    if (!createResponse.ok()) {
      const body = await createResponse.text()
      throw new Error(
        `POST /strategies failed: ${createResponse.status()} ${createResponse.statusText()} - ${body}`
      )
    }
    await page.waitForLoadState('networkidle')

    // 3. Activate the strategy against the portfolio.
    const strategyCard = page
      .locator('[data-testid^="strategy-card-"]')
      .filter({ hasText: strategyName })
    await expect(strategyCard).toBeVisible()
    const activateBtn = strategyCard.getByTestId(/^strategy-activate-button-/)
    await activateBtn.click()
    await expect(page.getByTestId('activate-strategy-dialog')).toBeVisible()
    await page.getByTestId('activate-portfolio-select').selectOption({
      label: portfolioName,
    })
    const activateResponsePromise = page.waitForResponse(
      (response) =>
        /\/strategies\/[^/]+\/activate(\?|$)/.test(response.url()) &&
        response.request().method() === 'POST'
    )
    await page.getByTestId('activate-strategy-submit').click()
    const activateResponse = await activateResponsePromise
    if (!activateResponse.ok()) {
      const body = await activateResponse.text()
      throw new Error(
        `POST activate failed: ${activateResponse.status()} ${activateResponse.statusText()} - ${body}`
      )
    }
    await expect(
      strategyCard.getByTestId('activation-status-ACTIVE')
    ).toBeVisible({ timeout: 5000 })

    // 4. Navigate to the activations list, then click into the new
    //    activation to reach the detail page.
    await page.goto('/activations')
    await page.waitForLoadState('networkidle')
    const activationRow = page
      .locator('[data-testid^="activation-row-"]')
      .filter({ hasText: strategyName })
    await expect(activationRow).toBeVisible()
    await activationRow.click()

    // Detail page is reached. The triggers section is rendered.
    await page.waitForURL('**/activations/*', { timeout: 10000 })
    await expect(page.getByTestId('activation-detail-page')).toBeVisible()
    await expect(
      page.getByTestId('activation-triggers-section')
    ).toBeVisible()

    // 5. Open the create-trigger dialog (empty state CTA).
    const emptyAttachBtn = page.getByTestId('trigger-empty-attach-btn')
    await expect(emptyAttachBtn).toBeVisible({ timeout: 5000 })
    await emptyAttachBtn.click()
    await expect(page.getByTestId('trigger-create-dialog')).toBeVisible()

    // 6. Fill the form. Defaults give us a DRAWDOWN_THRESHOLD trigger;
    //    we just need a valid agent prompt.
    await page
      .getByTestId('trigger-create-agent-prompt')
      .fill('Investigate the drawdown carefully and decide what to do.')

    await page.getByTestId('trigger-create-submit-btn').click()
    await page.waitForLoadState('networkidle')

    // 7. The trigger row appears in the table with status ACTIVE.
    //    (The previous version of this test used waitForResponse to gate
    //    on the POST, but the response predicate was racy under CI
    //    concurrency — relying on the row showing up + the dialog
    //    closing is the better behavior-focused check.)
    const triggerRow = page.locator('[data-testid^="trigger-list-row-"]').first()
    await expect(triggerRow).toBeVisible({ timeout: 15_000 })
    await expect(triggerRow.getByTestId('trigger-status-ACTIVE')).toBeVisible()

    // 8. Visit the fire-log (empty state). The View fires button navigates
    //    to /triggers/:id/fires.
    const viewFiresBtn = triggerRow.locator(
      '[data-testid^="trigger-view-fires-btn-"]'
    )
    await viewFiresBtn.click()
    await page.waitForURL('**/triggers/*/fires', { timeout: 10000 })
    await expect(page.getByTestId('trigger-fire-log-page')).toBeVisible()
    // No fires yet, so the empty state renders.
    await expect(page.getByTestId('trigger-fires-empty')).toBeVisible()

    // 9. Back to the activation detail. Pause the trigger via the row action.
    await page.getByTestId('trigger-fire-log-back-link').click()
    await page.waitForURL('**/activations/*', { timeout: 10000 })
    await expect(page.getByTestId('activation-triggers-section')).toBeVisible()

    const pauseBtn = page.locator('[data-testid^="trigger-pause-btn-"]').first()
    await expect(pauseBtn).toBeVisible()
    await pauseBtn.click()
    await expect(
      page.locator('[data-testid="trigger-status-PAUSED"]').first()
    ).toBeVisible({ timeout: 15_000 })

    // 10. Resume.
    const resumeBtn = page
      .locator('[data-testid^="trigger-resume-btn-"]')
      .first()
    await resumeBtn.click()
    await expect(
      page.locator('[data-testid="trigger-status-ACTIVE"]').first()
    ).toBeVisible({ timeout: 15_000 })

    // 11. Delete (expire). Confirm the modal then assert the row is gone
    //     (or transitions to EXPIRED — both are valid outcomes per the
    //     soft-delete contract).
    const deleteBtn = page
      .locator('[data-testid^="trigger-delete-btn-"]')
      .first()
    await deleteBtn.click()
    await expect(page.getByTestId('confirm-dialog')).toBeVisible()
    await page.getByTestId('confirm-dialog-confirm').click()
    // After soft-delete the trigger transitions to EXPIRED — the row stays
    // in the list (terminal-state row).
    await expect(
      page.locator('[data-testid="trigger-status-EXPIRED"]').first()
    ).toBeVisible({ timeout: 5000 })
  })
})
