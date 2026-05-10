/**
 * E2E for the exploration-tasks dashboard (Phase H1).
 *
 * Covers the happy path: navigate to the queue → create a task → verify it
 * appears in the list → click into the detail → verify content.
 *
 * Uses the same Clerk-authenticated fixture as other E2E tests so the
 * backend treats the request as a real human submission.
 */
import { test, expect } from './fixtures'

test.describe('Exploration Tasks Dashboard', () => {
  test('creates an exploration task and renders it in list + detail', async ({
    page,
  }) => {
    // 1. Navigate to the queue.
    await page.goto('/exploration-tasks')
    await page.waitForLoadState('networkidle')

    // The page header renders.
    await expect(
      page.getByRole('heading', { name: /^Exploration tasks$/, level: 1 })
    ).toBeVisible()

    // 2. Open the create form via the header CTA.
    await page.getByTestId('exploration-task-new-btn').click()
    await expect(page.getByTestId('exploration-task-create-form')).toBeVisible({
      timeout: 5000,
    })

    // 3. Fill the form with a unique title so we can assert on it.
    const taskTitle = `E2E exploration task ${Date.now()}`
    const taskBody =
      'Investigate mean-reversion candidates on AAPL/MSFT and report the strongest variant.'

    await page.getByTestId('exploration-task-create-title-input').fill(taskTitle)
    await page
      .getByTestId('exploration-task-create-prompt-input')
      .fill(taskBody)
    await page
      .getByTestId('exploration-task-create-tickers-input')
      .fill('AAPL, MSFT')

    // 4. Gate on the network response. The POST is the authoritative
    //    success signal; toast / cache invalidation happens after.
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

    // 5. The form navigates to the detail view on success.
    await page.waitForURL('**/exploration-tasks/*', { timeout: 10000 })
    await expect(page.getByTestId('exploration-task-detail-page')).toBeVisible()
    await expect(page.getByTestId('exploration-task-detail-title')).toHaveText(
      taskTitle
    )
    // Status badge should be OPEN since the task was just created.
    await expect(
      page.getByTestId('exploration-task-status-OPEN')
    ).toBeVisible()
    // Body content surfaces in the prompt panel.
    await expect(page.getByTestId('exploration-task-detail-prompt')).toContainText(
      'mean-reversion candidates'
    )

    // 6. Navigate back to the list and confirm the task is visible.
    await page.getByTestId('exploration-task-detail-back-link').click()
    await page.waitForURL('**/exploration-tasks', { timeout: 10000 })
    await page.waitForLoadState('networkidle')

    // The new task's row exists in the table — find it by test-id pattern,
    // then assert the visible title.
    const taskRow = page
      .locator('[data-testid^="exploration-task-list-row-"]')
      .filter({ hasText: taskTitle })
    await expect(taskRow).toBeVisible({ timeout: 5000 })

    // 7. Click into the task again from the list.
    await taskRow.click()
    await page.waitForURL('**/exploration-tasks/*', { timeout: 10000 })
    await expect(page.getByTestId('exploration-task-detail-title')).toHaveText(
      taskTitle
    )
  })
})
