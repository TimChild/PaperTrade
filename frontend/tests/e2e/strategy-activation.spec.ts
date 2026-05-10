/**
 * E2E test for the live-strategy-activation flow (Phase C1.4).
 *
 * Covers the happy path:
 *
 *   create portfolio → create strategy → activate → run-now → deactivate.
 *
 * The CI E2E backend uses the deterministic mock market data adapter
 * (MARKET_DATA_PROVIDER=mock) so any valid ticker returns prices.
 */
import { test, expect } from './fixtures'

test.describe('Live Strategy Activation Flow', () => {
  test('should activate, run, and deactivate a strategy', async ({ page }) => {
    // 1. Create a paper-trading portfolio with enough cash to buy.
    await page.goto('/dashboard')
    await page.waitForLoadState('networkidle')

    const headerButton = page.getByTestId('create-portfolio-header-btn')
    const emptyStateButton = page.getByTestId('create-first-portfolio-btn')
    const createButton = (await headerButton.isVisible())
      ? headerButton
      : emptyStateButton
    await createButton.click()

    const portfolioName = `Activation Portfolio ${Date.now()}`
    await page.getByTestId('create-portfolio-name-input').fill(portfolioName)
    await page.getByTestId('create-portfolio-deposit-input').fill('100000')
    await page.getByTestId('submit-portfolio-form-btn').click()

    await page.waitForURL('**/portfolio/*', { timeout: 10000 })
    await expect(page.getByTestId('portfolio-detail-name')).toHaveText(
      portfolioName
    )

    // 2. Create a buy-and-hold strategy with a single ticker for predictability.
    await page.goto('/strategies')
    await page.waitForLoadState('networkidle')

    await page.getByTestId('create-strategy-button').click()

    // Wait for the form to mount before filling. The form is conditionally
    // rendered behind `{showForm && (...)}` so we need to wait for the
    // `data-testid="create-strategy-form"` element to appear before relying
    // on its inputs being editable.
    await expect(page.getByTestId('create-strategy-form')).toBeVisible({
      timeout: 5000,
    })

    const strategyName = `Activation Strategy ${Date.now()}`
    await page.getByTestId('strategy-name-input').fill(strategyName)
    // BUY_AND_HOLD is the default in the form, so no need to change the type.
    await page.getByTestId('strategy-tickers-input').fill('IBM')
    // The allocation input only renders once the parsed `tickers` array
    // contains the symbol — wait for it before filling.
    await expect(page.getByTestId('allocation-IBM')).toBeVisible({
      timeout: 5000,
    })
    await page.getByTestId('allocation-IBM').fill('1.0')

    // Gate on the actual network response rather than the success toast.
    // The toast goes through React state → Toaster portal → DOM paint, which
    // adds enough latency that asserting on the toast-text loses the race
    // under CI's resource pressure (the assertion's 10s budget elapsed on
    // every retry). The POST is the authoritative signal that the strategy
    // exists; once we see a 2xx, we can wait for the cache invalidation to
    // settle and assert on the rendered card.
    //
    // If the POST returns a non-2xx we surface the detail in the failure
    // message so the next investigator doesn't have to guess.
    const createResponsePromise = page.waitForResponse(
      (response) =>
        // Match `POST /api/v1/strategies` exactly — the URL must end at
        // `/strategies` (optionally with a query string) so we don't pick up
        // `/strategies/{id}/activate` etc.
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

    // Wait for the in-flight `useStrategies` refetch (triggered by
    // `invalidateQueries(['strategies'])`) to settle before checking the DOM.
    await page.waitForLoadState('networkidle')

    // Now the strategy card should be in the grid.
    await expect(page.getByText(strategyName)).toBeVisible({ timeout: 10000 })

    // 3. Find the strategy card and activate the strategy.
    // We use the heading text to locate the card, then scope subsequent
    // queries to its enclosing test-id attribute.
    const strategyCard = page
      .locator('[data-testid^="strategy-card-"]')
      .filter({ hasText: strategyName })
    await expect(strategyCard).toBeVisible()

    const activateBtn = strategyCard.getByTestId(/^strategy-activate-button-/)
    await expect(activateBtn).toBeVisible({ timeout: 5000 })
    await activateBtn.click()

    // Activation dialog opens. Pick the portfolio.
    await expect(page.getByTestId('activate-strategy-dialog')).toBeVisible()
    await page.getByTestId('activate-portfolio-select').selectOption({
      label: portfolioName,
    })

    // Same pattern as the create call: gate on the network response for the
    // activation POST and surface details on failure. The endpoint is
    // `POST /strategies/{id}/activate`.
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

    // The panel flips to show the badge once the activation cache settles.
    await expect(
      strategyCard.getByTestId('activation-status-ACTIVE')
    ).toBeVisible({ timeout: 5000 })

    // 4. Trigger Run Now and confirm.
    const runNowBtn = strategyCard.getByTestId(/^strategy-run-now-button-/)
    await expect(runNowBtn).toBeEnabled()
    await runNowBtn.click()

    // Confirmation dialog.
    await expect(page.getByTestId('confirm-dialog')).toBeVisible()

    // Gate on the run-now POST response. We don't assert on success vs.
    // failure of the run itself — either outcome proves the wiring works
    // (a 200 response is what matters; the body says succeeded/error).
    const runNowResponsePromise = page.waitForResponse(
      (response) =>
        /\/activations\/[^/]+\/run-now(\?|$)/.test(response.url()) &&
        response.request().method() === 'POST'
    )
    await page.getByTestId('confirm-dialog-confirm').click()
    const runNowResponse = await runNowResponsePromise
    if (!runNowResponse.ok()) {
      const body = await runNowResponse.text()
      throw new Error(
        `POST run-now failed: ${runNowResponse.status()} ${runNowResponse.statusText()} - ${body}`
      )
    }

    // The status badge should still be visible (ACTIVE for a successful run;
    // ERROR if mock market data didn't cover the ticker — both prove the
    // wiring works).
    await expect(
      strategyCard.locator('[data-testid^="activation-status-"]')
    ).toBeVisible()

    // 5. Deactivate.
    const deactivateBtn = strategyCard.getByTestId(
      /^strategy-deactivate-button-/
    )
    await expect(deactivateBtn).toBeVisible()
    await deactivateBtn.click()

    await expect(page.getByTestId('confirm-dialog')).toBeVisible()

    const deactivateResponsePromise = page.waitForResponse(
      (response) =>
        /\/activations\/[^/]+\/deactivate(\?|$)/.test(response.url()) &&
        response.request().method() === 'POST'
    )
    await page.getByTestId('confirm-dialog-confirm').click()
    const deactivateResponse = await deactivateResponsePromise
    if (!deactivateResponse.ok()) {
      const body = await deactivateResponse.text()
      throw new Error(
        `POST deactivate failed: ${deactivateResponse.status()} ${deactivateResponse.statusText()} - ${body}`
      )
    }

    await expect(
      strategyCard.getByTestId('activation-status-PAUSED')
    ).toBeVisible({ timeout: 5000 })
  })
})
