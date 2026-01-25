import { clerkSetup } from '@clerk/testing/playwright'

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
