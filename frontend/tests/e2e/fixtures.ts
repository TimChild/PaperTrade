/**
 * Playwright test fixtures with E2E test mode support
 */
import { test as base } from '@playwright/test'

/**
 * Extended test fixture that adds e2e-test query parameter to bypass Clerk auth
 */
export const test = base.extend({
  page: async ({ page }, use) => {
    // Override goto to automatically add e2e-test=true query parameter
    const originalGoto = page.goto.bind(page)
    page.goto = async (url: string, options?: Parameters<typeof originalGoto>[1]) => {
      // Add e2e-test=true parameter to bypass Clerk authentication
      const urlWithParam = url.includes('?') 
        ? `${url}&e2e-test=true` 
        : `${url}?e2e-test=true`
      
      return originalGoto(urlWithParam, options)
    }

    await use(page)
  },
})

export { expect } from '@playwright/test'
