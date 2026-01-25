import { test } from '@playwright/test'
import { setupClerkTestingToken } from '@clerk/testing/playwright'

test('debug clerk loading in browser', async ({ page }) => {
  console.log('=== Environment Variables ===')
  console.log('CLERK_FAPI:', process.env.CLERK_FAPI || 'NOT SET')
  console.log('CLERK_TESTING_TOKEN:', process.env.CLERK_TESTING_TOKEN ? 'SET (length=' + process.env.CLERK_TESTING_TOKEN.length + ')' : 'NOT SET')
  console.log('VITE_CLERK_PUBLISHABLE_KEY:', process.env.VITE_CLERK_PUBLISHABLE_KEY || 'NOT SET')
  
  // Set up Clerk testing token
  console.log('\n=== Setting up Clerk testing token ===')
  await setupClerkTestingToken({ page })
  console.log('✓ Setup complete')
  
  // Navigate to app
  console.log('\n=== Navigating to app ===')
  await page.goto('/')
  console.log('✓ Page loaded')
  
  // Wait for initial load
  await page.waitForLoadState('networkidle')
  console.log('✓ Network idle')
  
  // Check what's in the browser
  const browserState = await page.evaluate(() => {
    return {
      hasWindow: typeof window !== 'undefined',
      hasClerk: typeof (window as any).Clerk !== 'undefined',
      clerkType: typeof (window as any).Clerk,
      clerkKeys: (window as any).Clerk ? Object.keys((window as any).Clerk) : [],
      hasClerkLoaded: (window as any).Clerk?.loaded !== undefined,
      clerkLoaded: (window as any).Clerk?.loaded,
      hasClerkUser: (window as any).Clerk?.user !== undefined,
      clerkUser: (window as any).Clerk?.user,
      envKeyFromImportMeta: (import.meta as any).env?.VITE_CLERK_PUBLISHABLE_KEY,
      documentTitle: document.title,
      bodyText: document.body.innerText.substring(0, 200),
    }
  })
  
  console.log('\n=== Browser State ===')
  console.log(JSON.stringify(browserState, null, 2))
  
  // Take a screenshot
  await page.screenshot({ path: '/tmp/clerk-debug.png', fullPage: true })
  console.log('\n✓ Screenshot saved to /tmp/clerk-debug.png')
  
  // If Clerk exists but not loaded, wait a bit
  if (browserState.hasClerk && !browserState.clerkLoaded) {
    console.log('\n=== Waiting for Clerk to load ===')
    try {
      await page.waitForFunction(() => (window as any).Clerk?.loaded, { timeout: 10000 })
      console.log('✓ Clerk loaded successfully')
    } catch (e) {
      console.log('✗ Clerk failed to load within 10 seconds')
      console.log('Error:', e)
    }
  }
})
