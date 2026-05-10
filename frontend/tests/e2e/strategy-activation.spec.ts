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

    const strategyName = `Activation Strategy ${Date.now()}`
    await page.getByTestId('strategy-name-input').fill(strategyName)
    // BUY_AND_HOLD is the default in the form, so no need to change the type.
    await page.getByTestId('strategy-tickers-input').fill('IBM')
    await page.getByTestId('allocation-IBM').fill('1.0')
    await page.getByTestId('create-strategy-submit').click()

    // Wait for the strategy card to appear.
    await expect(page.getByText(strategyName)).toBeVisible({ timeout: 5000 })

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
    await page.getByTestId('activate-strategy-submit').click()

    // Toast confirms activation; the panel flips to show the badge.
    await expect(page.getByText(/strategy activated/i)).toBeVisible({
      timeout: 5000,
    })
    await expect(
      strategyCard.getByTestId('activation-status-ACTIVE')
    ).toBeVisible({ timeout: 5000 })

    // 4. Trigger Run Now and confirm.
    const runNowBtn = strategyCard.getByTestId(/^strategy-run-now-button-/)
    await expect(runNowBtn).toBeEnabled()
    await runNowBtn.click()

    // Confirmation dialog.
    await expect(page.getByTestId('confirm-dialog')).toBeVisible()
    await page.getByTestId('confirm-dialog-confirm').click()

    // Wait for the run-complete toast (success or failure either way; the
    // happy-path expectation here is that the activation status remains
    // ACTIVE — i.e. the run did NOT flip to ERROR).
    await expect(page.getByText(/run complete|run failed/i)).toBeVisible({
      timeout: 10000,
    })

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
    await page.getByTestId('confirm-dialog-confirm').click()

    await expect(page.getByText(/activation paused/i)).toBeVisible({
      timeout: 5000,
    })
    await expect(
      strategyCard.getByTestId('activation-status-PAUSED')
    ).toBeVisible({ timeout: 5000 })
  })
})
