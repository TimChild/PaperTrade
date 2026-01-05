import { clerkSetup } from '@clerk/testing/playwright'

/**
 * Global setup for Playwright E2E tests.
 * This runs once before all tests.
 *
 * Uses @clerk/testing's clerkSetup() to create a testing token.
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
  console.log('E2E_CLERK_USER_EMAIL:', process.env.E2E_CLERK_USER_EMAIL || 'NOT SET')

  // Initialize Clerk testing infrastructure
  await clerkSetup()
  console.log('✓ Clerk testing setup complete')
}
