/**
 * Global setup for Playwright E2E tests.
 * This runs once before all tests.
 * 
 * Creates a Clerk testing token manually since clerkSetup() has issues
 * with Cloudflare when using Node's fetch API.
 */
export default async function globalSetup() {
  // Clerk requires CLERK_PUBLISHABLE_KEY (not VITE_CLERK_PUBLISHABLE_KEY)
  // Set it from VITE_CLERK_PUBLISHABLE_KEY if not already set
  if (!process.env.CLERK_PUBLISHABLE_KEY && process.env.VITE_CLERK_PUBLISHABLE_KEY) {
    process.env.CLERK_PUBLISHABLE_KEY = process.env.VITE_CLERK_PUBLISHABLE_KEY
  }

  console.log('Environment variables check:')
  console.log('CLERK_PUBLISHABLE_KEY:', process.env.CLERK_PUBLISHABLE_KEY ? 'SET' : 'NOT SET')
  console.log('CLERK_SECRET_KEY:', process.env.CLERK_SECRET_KEY ? 'SET' : 'NOT SET')

  // Manually create testing token using curl (works around Cloudflare issues)
  if (process.env.CLERK_SECRET_KEY && !process.env.CLERK_TESTING_TOKEN) {
    try {
      const { execSync } = await import('child_process')
      
      const result = execSync(
        `curl -s -X POST "https://api.clerk.com/v1/testing_tokens" \\
          -H "Authorization: Bearer ${process.env.CLERK_SECRET_KEY}" \\
          -H "Content-Type: application/json"`,
        { encoding: 'utf8' }
      )
      
      const data = JSON.parse(result)
      if (data.token) {
        process.env.CLERK_TESTING_TOKEN = data.token
        // Also set the CLERK_FAPI environment variable that Clerk uses
        if (process.env.CLERK_PUBLISHABLE_KEY) {
          const domain = process.env.CLERK_PUBLISHABLE_KEY.split('$')[1] || 'clerk.accounts.dev'
          process.env.CLERK_FAPI = `https://${domain}`
        }
        console.log('✓ Clerk testing token created successfully')
      } else {
        throw new Error(`Failed to create testing token: ${result}`)
      }
    } catch (error) {
      console.error('Failed to create testing token:', error)
      throw error
    }
  } else if (process.env.CLERK_TESTING_TOKEN) {
    console.log('✓ Clerk testing token already set')
  }
}
