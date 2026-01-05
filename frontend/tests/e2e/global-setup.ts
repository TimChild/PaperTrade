/**
 * Global setup for Playwright E2E tests
 * Configures Clerk testing tokens for authenticated E2E tests
 *
 * References:
 * - https://clerk.com/docs/testing/playwright
 * - https://github.com/clerk/clerk-playwright-nextjs
 */
import { clerkSetup } from '@clerk/testing/playwright'
import { config } from 'dotenv'
import { resolve, dirname } from 'path'
import { fileURLToPath } from 'url'

const __dirname = dirname(fileURLToPath(import.meta.url))

export default async function globalSetup() {
  // Load environment variables from .env file in project root
  // This works locally; in CI, env vars are already set and take precedence
  config({ path: resolve(__dirname, '../../../.env') })

  // Check if Clerk testing credentials are available
  const secretKey = process.env.CLERK_SECRET_KEY

  if (!secretKey) {
    console.log('Playwright global setup: CLERK_SECRET_KEY not set, skipping Clerk setup')
    console.log('Tests requiring authentication will be skipped')
    return
  }

  // Initialize Clerk testing - this obtains a Testing Token
  // that allows tests to bypass Clerk's bot detection
  await clerkSetup()

  console.log('Playwright global setup: Clerk testing configured')
}
