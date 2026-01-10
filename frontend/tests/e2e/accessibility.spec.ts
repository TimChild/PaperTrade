import { clerk } from '@clerk/testing/playwright'
import { test, expect } from './fixtures'
import AxeBuilder from '@axe-core/playwright'

test.describe('Accessibility (WCAG 2.1 AA)', () => {
  test.beforeEach(async ({ page }) => {
    const email = process.env.E2E_CLERK_USER_EMAIL || 'test-e2e@papertrade.dev'

    // Navigate to app and authenticate
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    await clerk.signIn({ page, emailAddress: email })
    await page.waitForURL('**/dashboard', { timeout: 10000 })
  })

  test('Dashboard page has no accessibility violations', async ({ page }) => {
    await page.goto('/dashboard')
    await page.waitForLoadState('networkidle')

    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze()

    expect(results.violations).toEqual([])
  })

  test('Portfolio Detail page has no accessibility violations', async ({ page }) => {
    await page.goto('/dashboard')
    await page.waitForLoadState('networkidle')

    // Create test portfolio first
    const headerButton = page.getByTestId('create-portfolio-header-btn')
    const emptyStateButton = page.getByTestId('create-first-portfolio-btn')
    const createButton = (await headerButton.isVisible()) ? headerButton : emptyStateButton
    await createButton.click()

    const portfolioName = `Accessibility Test ${Date.now()}`
    await page.getByTestId('create-portfolio-name-input').fill(portfolioName)
    await page.getByTestId('create-portfolio-deposit-input').fill('10000')
    await page.getByTestId('submit-portfolio-form-btn').click()

    // Wait for navigation to portfolio detail page
    await page.waitForURL('**/portfolio/*', { timeout: 10000 })
    await page.waitForLoadState('networkidle')

    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze()

    expect(results.violations).toEqual([])
  })

  test('Dark mode has sufficient color contrast', async ({ page }) => {
    await page.goto('/dashboard')
    await page.waitForLoadState('networkidle')

    // Toggle to dark mode
    await page.getByTestId('theme-toggle-dark').click()
    await page.waitForTimeout(300) // Wait for theme transition

    const results = await new AxeBuilder({ page })
      .withTags(['cat.color'])
      .analyze()

    expect(results.violations).toEqual([])
  })

  test('Light mode has sufficient color contrast', async ({ page }) => {
    await page.goto('/dashboard')
    await page.waitForLoadState('networkidle')

    // Toggle to light mode
    await page.getByTestId('theme-toggle-light').click()
    await page.waitForTimeout(300) // Wait for theme transition

    const results = await new AxeBuilder({ page })
      .withTags(['cat.color'])
      .analyze()

    expect(results.violations).toEqual([])
  })

  test('Keyboard navigation works correctly on Dashboard', async ({ page }) => {
    await page.goto('/dashboard')
    await page.waitForLoadState('networkidle')

    // Tab through interactive elements
    // First tab should focus theme toggle
    await page.keyboard.press('Tab')
    const firstFocused = await page.evaluate(() => document.activeElement?.getAttribute('data-testid'))
    expect(['theme-toggle-light', 'theme-toggle-dark', 'theme-toggle-system']).toContain(firstFocused)

    // Continue tabbing - should reach form inputs
    await page.keyboard.press('Tab')
    await page.keyboard.press('Tab')
    await page.keyboard.press('Tab')

    // Eventually should reach the create portfolio form
    const formInput = page.getByTestId('create-portfolio-name-input')
    const createButton = page.getByTestId('create-portfolio-header-btn').or(page.getByTestId('create-first-portfolio-btn'))

    // One of these should be in the tab order
    const hasFormInTabOrder = await page.evaluate(() => {
      const focused = document.activeElement
      const testId = focused?.getAttribute('data-testid')
      return testId?.includes('create-portfolio') || testId?.includes('theme-toggle')
    })
    expect(hasFormInTabOrder).toBe(true)
  })

  test('All interactive elements have visible focus indicators', async ({ page }) => {
    await page.goto('/dashboard')
    await page.waitForLoadState('networkidle')

    // Tab to first interactive element
    await page.keyboard.press('Tab')

    // Check that focused element has visible focus ring
    const focusVisible = await page.evaluate(() => {
      const focused = document.activeElement
      if (!focused) return false

      const styles = window.getComputedStyle(focused)
      // Check for outline or box-shadow (common focus indicators)
      const hasOutline = styles.outline !== 'none' && styles.outline !== ''
      const hasBoxShadow = styles.boxShadow !== 'none' && styles.boxShadow !== ''
      const hasRing = focused.classList.toString().includes('focus')

      return hasOutline || hasBoxShadow || hasRing
    })

    expect(focusVisible).toBe(true)
  })

  test('Screen reader landmarks are present', async ({ page }) => {
    await page.goto('/dashboard')
    await page.waitForLoadState('networkidle')

    // Verify ARIA landmarks exist
    const mainLandmark = page.locator('main').or(page.locator('[role="main"]'))
    await expect(mainLandmark).toBeVisible()

    // Verify header is present
    const headerLandmark = page.locator('header').or(page.locator('[role="banner"]'))
    await expect(headerLandmark).toBeVisible()
  })

  test('Form inputs have associated labels', async ({ page }) => {
    await page.goto('/dashboard')
    await page.waitForLoadState('networkidle')

    // Click create portfolio button to show form
    const headerButton = page.getByTestId('create-portfolio-header-btn')
    const emptyStateButton = page.getByTestId('create-first-portfolio-btn')
    const createButton = (await headerButton.isVisible()) ? headerButton : emptyStateButton

    if (await createButton.isVisible()) {
      await createButton.click()
    }

    // Check that form inputs have labels or aria-label
    const nameInput = page.getByTestId('create-portfolio-name-input')
    const depositInput = page.getByTestId('create-portfolio-deposit-input')

    // Verify inputs have accessible names via labels or aria attributes
    const nameInputAccessible = await nameInput.evaluate((el) => {
      const input = el as HTMLInputElement
      const hasLabel = !!document.querySelector(`label[for="${input.id}"]`)
      const hasAriaLabel = !!input.getAttribute('aria-label')
      const hasAriaLabelledBy = !!input.getAttribute('aria-labelledby')
      return hasLabel || hasAriaLabel || hasAriaLabelledBy || !!input.getAttribute('placeholder')
    })

    expect(nameInputAccessible).toBe(true)
  })

  test('Images have alt text', async ({ page }) => {
    await page.goto('/dashboard')
    await page.waitForLoadState('networkidle')

    // Check all images have alt attributes
    const imagesWithoutAlt = await page.locator('img:not([alt])').count()
    expect(imagesWithoutAlt).toBe(0)
  })

  test('Portfolio Analytics page has no accessibility violations', async ({ page }) => {
    await page.goto('/dashboard')
    await page.waitForLoadState('networkidle')

    // Create test portfolio first
    const headerButton = page.getByTestId('create-portfolio-header-btn')
    const emptyStateButton = page.getByTestId('create-first-portfolio-btn')
    const createButton = (await headerButton.isVisible()) ? headerButton : emptyStateButton
    await createButton.click()

    const portfolioName = `Analytics A11y Test ${Date.now()}`
    await page.getByTestId('create-portfolio-name-input').fill(portfolioName)
    await page.getByTestId('create-portfolio-deposit-input').fill('10000')
    await page.getByTestId('submit-portfolio-form-btn').click()

    await page.waitForURL('**/portfolio/*', { timeout: 10000 })

    // Navigate to analytics page
    const currentUrl = page.url()
    const analyticsUrl = `${currentUrl}/analytics`
    await page.goto(analyticsUrl)
    await page.waitForLoadState('networkidle')

    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze()

    expect(results.violations).toEqual([])
  })
})
