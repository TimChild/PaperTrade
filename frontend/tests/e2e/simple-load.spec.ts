import { test, expect } from '@playwright/test'

// This test does NOT use the setup dependency
test.describe.configure({ mode: 'parallel' })

test('app loads without authentication', async ({ page }) => {
  // Navigate to app
  await page.goto('/')
  
  // Wait for page to load
  await page.waitForLoadState('networkidle')
  
  // Check page title
  await expect(page).toHaveTitle('Zebu')
  
  // Check if we get redirected to sign-in or see the app
  const url = page.url()
  console.log('Current URL:', url)
  
  // Take screenshot
  await page.screenshot({ path: '/tmp/app-no-auth.png', fullPage: true })
  
  // Check console for errors
  const logs: string[] = []
  page.on('console', msg => {
    logs.push(`${msg.type()}: ${msg.text()}`)
  })
  
  // Wait a bit to collect logs
  await page.waitForTimeout(2000)
  
  console.log('Console logs:', logs.join('\n'))
})
