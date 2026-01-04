/**
 * Global setup for Playwright E2E tests
 * Configures mock Clerk authentication
 */

export default function globalSetup() {
  // Set test mode environment variable
  process.env.VITE_E2E_TEST_MODE = 'true'
  
  console.log('Playwright global setup: E2E test mode enabled')
}
