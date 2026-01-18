import { test, expect } from './fixtures'

test.describe('NotFound Page', () => {
  test('should display 404 page for invalid route', async ({ page }) => {
    // Navigate to non-existent route
    await page.goto('/this-route-does-not-exist')
    await page.waitForLoadState('networkidle')

    // Should see 404 error
    await expect(page.getByText('404')).toBeVisible()
    await expect(page.getByText(/page not found/i)).toBeVisible()
  })
})
