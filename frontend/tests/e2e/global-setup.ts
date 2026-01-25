import { clerkSetup } from '@clerk/testing/playwright'
import { execSync } from 'child_process'

/**
 * Clean up test portfolios from previous runs.
 * This prevents tests from failing due to accumulated data.
 */
function cleanupTestPortfolios(): void {
  const patterns = [
    "Test Portfolio %",
    "Persistent %",
    "Analytics Test %",
    "Multi Test Portfolio%",
  ]
  const whereClause = patterns.map((p) => `name LIKE '${p}'`).join(' OR ')
  const sql = `DELETE FROM portfolios WHERE ${whereClause}`

  try {
    const result = execSync(
      `docker exec papertrade-db-1 psql -U papertrade -d papertrade_dev -c "${sql}" 2>&1`,
      { encoding: 'utf-8', timeout: 10000 }
    )
    const match = result.match(/DELETE (\d+)/)
    if (match && parseInt(match[1]) > 0) {
      console.log(`✓ Cleaned up ${match[1]} test portfolios from previous runs`)
    }
  } catch {
    // Database might not be accessible (e.g., CI environment with fresh DB)
    // This is fine - we only need cleanup for local dev with accumulated data
    console.log('ℹ Test portfolio cleanup skipped (database not accessible or empty)')
  }
}

/**
 * Global setup for Playwright E2E tests.
 * This runs once before all tests.
 *
 * Uses Clerk's clerkSetup() to create a Testing Token that allows
 * tests to bypass bot detection. The testing token is shared via
 * environment variables.
 *
 * NOTE: Each test then uses clerk.signIn({ emailAddress }) to get
 * fresh authentication, since Clerk session tokens expire in 60 seconds.
 */
export default async function globalSetup(): Promise<void> {
  // Map VITE_CLERK_PUBLISHABLE_KEY to CLERK_PUBLISHABLE_KEY if needed
  if (!process.env.CLERK_PUBLISHABLE_KEY && process.env.VITE_CLERK_PUBLISHABLE_KEY) {
    process.env.CLERK_PUBLISHABLE_KEY = process.env.VITE_CLERK_PUBLISHABLE_KEY
  }

  // Log environment setup for debugging
  console.log('=== E2E Test Global Setup ===')

  // Clean up test portfolios from previous runs first
  cleanupTestPortfolios()

  console.log('CLERK_PUBLISHABLE_KEY:', process.env.CLERK_PUBLISHABLE_KEY ? 'SET' : 'NOT SET')
  console.log('CLERK_SECRET_KEY:', process.env.CLERK_SECRET_KEY ? 'SET' : 'NOT SET')
  console.log('E2E_CLERK_USER_EMAIL:', process.env.E2E_CLERK_USER_EMAIL || 'NOT SET')

  // Validate required environment variables
  if (!process.env.CLERK_SECRET_KEY) {
    throw new Error('CLERK_SECRET_KEY environment variable is required')
  }
  if (!process.env.CLERK_PUBLISHABLE_KEY) {
    throw new Error('CLERK_PUBLISHABLE_KEY environment variable is required')
  }
  if (!process.env.E2E_CLERK_USER_EMAIL) {
    throw new Error('E2E_CLERK_USER_EMAIL environment variable is required')
  }

  // Create Clerk testing token (for bot detection bypass)
  await clerkSetup()

  console.log('✓ Clerk testing token created')
  console.log('=== Global Setup Complete ===')
}
