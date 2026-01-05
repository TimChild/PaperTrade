import { clerkSetup } from '@clerk/testing/playwright'

/**
 * Global setup for Playwright E2E tests.
 * This runs once before all tests.
 */
export default async function globalSetup() {
  // Initialize Clerk testing - MUST be called before setupClerkTestingToken
  await clerkSetup()
  console.log('✓ Clerk testing setup complete')
}
