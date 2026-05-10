/**
 * E2E for the "Ask an agent" workflow (Phase G-2.3).
 *
 * Covers the portfolio detail flow end-to-end: navigate to a portfolio,
 * click "Ask an agent", verify the dialog opens with the portfolio
 * pre-filled, submit a task, and confirm it appears in the exploration
 * tasks list.
 *
 * Uses the same Clerk-authenticated fixture as other E2E tests so the
 * backend treats the request as a real human submission.
 */
import { test, expect } from './fixtures'

test.describe('Ask an agent — Portfolio detail', () => {
  test('opens a pre-filled exploration task dialog and submits it', async ({
    page,
  }) => {
    // Land on the dashboard — fixture has already authenticated us there.
    await page.goto('/dashboard')
    await page.waitForLoadState('networkidle')

    // Navigate to the first portfolio card. The test environment
    // bootstraps with at least one portfolio.
    const firstCard = page
      .locator('[data-testid^="portfolio-card-"]')
      .first()
    await expect(firstCard).toBeVisible({ timeout: 10000 })
    await firstCard.click()

    // We should land on the portfolio detail page.
    await page.waitForURL(/\/portfolio\/[a-f0-9-]+$/, { timeout: 10000 })
    const portfolioId = page.url().split('/').pop() ?? ''
    expect(portfolioId.length).toBeGreaterThan(0)

    // The Ask-an-agent CTA is in the page header next to the analytics link.
    const askBtn = page.getByTestId('ask-an-agent-portfolio-btn')
    await expect(askBtn).toBeVisible()
    await askBtn.click()

    // The dialog opens hosting the exploration-task form.
    await expect(
      page.getByTestId('ask-an-agent-dialog-portfolio')
    ).toBeVisible({ timeout: 5000 })

    // The portfolio select should be pre-filled with this portfolio's id.
    const portfolioSelect = page.getByTestId(
      'exploration-task-create-portfolio-select'
    )
    await expect(portfolioSelect).toHaveValue(portfolioId)

    // Fill the prompt and submit. We rely on the POST response as the
    // authoritative success signal.
    const promptText = `Investigate strategies for this portfolio (${Date.now()}).`
    await page
      .getByTestId('exploration-task-create-prompt-input')
      .fill(promptText)

    const createResponsePromise = page.waitForResponse(
      (response) =>
        /\/exploration-tasks(\?|$)/.test(response.url()) &&
        response.request().method() === 'POST'
    )

    await page.getByTestId('exploration-task-create-submit-btn').click()

    const createResponse = await createResponsePromise
    if (!createResponse.ok()) {
      const body = await createResponse.text()
      throw new Error(
        `POST /exploration-tasks failed: ${createResponse.status()} ${createResponse.statusText()} - ${body}`
      )
    }

    // Navigate to the exploration tasks list and verify our task appears.
    await page.goto('/exploration-tasks')
    await page.waitForLoadState('networkidle')

    // We expect at least one row.
    const newRow = page
      .locator('[data-testid^="exploration-task-list-row-"]')
      .filter({ hasText: promptText })
    await expect(newRow).toBeVisible({ timeout: 5000 })
  })
})
