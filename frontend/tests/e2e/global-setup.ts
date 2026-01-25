import axios from 'axios'
import { validateEnvironment } from './utils/validate-environment'
import { debugAuthentication } from './utils/debug-auth'

/**
 * Global setup for Playwright E2E tests.
 * This runs once before all tests.
 *
 * Creates a Clerk testing token using direct API call with axios.
 * NOTE: Using axios instead of @clerk/backend SDK due to compatibility issues
 * with the SDK's testing token endpoint in version 2.29.0.
 */
export default async function globalSetup() {
  // Clerk requires CLERK_PUBLISHABLE_KEY (not VITE_CLERK_PUBLISHABLE_KEY)
  // Set it from VITE_CLERK_PUBLISHABLE_KEY if not already set
  if (!process.env.CLERK_PUBLISHABLE_KEY && process.env.VITE_CLERK_PUBLISHABLE_KEY) {
    process.env.CLERK_PUBLISHABLE_KEY = process.env.VITE_CLERK_PUBLISHABLE_KEY
  }

  console.log('🔧 Starting E2E Global Setup...\n')
  console.log('Environment variables check:')
  console.log('CLERK_PUBLISHABLE_KEY:', process.env.CLERK_PUBLISHABLE_KEY ? 'SET' : 'NOT SET')
  console.log('CLERK_SECRET_KEY:', process.env.CLERK_SECRET_KEY ? 'SET' : 'NOT SET')
  console.log('E2E_CLERK_USER_EMAIL:', process.env.E2E_CLERK_USER_EMAIL || 'NOT SET')

  // Step 1: Validate environment BEFORE creating Clerk token
  console.log('\n📋 Step 1: Validating environment (pre-token checks)...')

  // Set debug flag for E2E tests
  process.env.VITE_E2E_DEBUG = 'true'

  const preValidation = await validateEnvironment()
  if (!preValidation) {
    throw new Error('❌ Pre-token environment validation failed. Check output above for details.')
  }

  const secretKey = process.env.CLERK_SECRET_KEY
  const publishableKey = process.env.CLERK_PUBLISHABLE_KEY

  if (!secretKey) {
    throw new Error('CLERK_SECRET_KEY environment variable is required')
  }
  if (!publishableKey) {
    throw new Error('CLERK_PUBLISHABLE_KEY environment variable is required')
  }

  // Extract frontend API URL from publishable key
  // Format: pk_test_<base64> where base64 decodes to "<frontend-api>#<key>"
  const base64Part = publishableKey.replace(/^pk_(test|live)_/, '')
  const decoded = Buffer.from(base64Part, 'base64').toString('utf-8')
  const frontendApi = decoded.split('#')[0]

  console.log('Creating Clerk testing token via API...')

  try {
    // Call Clerk API directly using axios (which handles Cloudflare better than fetch)
    const response = await axios.post(
      'https://api.clerk.com/v1/testing_tokens',
      {},
      {
        headers: {
          Authorization: `Bearer ${secretKey}`,
          'Content-Type': 'application/json',
        },
      }
    )

    const testingToken = response.data.token

    // Set environment variables for Playwright tests to use
    process.env.CLERK_FAPI = frontendApi
    process.env.CLERK_TESTING_TOKEN = testingToken

    console.log('✓ Clerk testing token created successfully')
    console.log('Frontend API:', frontendApi)
    console.log('Token preview:', testingToken.substring(0, 8) + '...' + testingToken.substring(testingToken.length - 8))

    // Step 2: Validate environment AFTER creating Clerk token
    console.log('\n📋 Step 2: Validating environment (post-token checks)...')
    const postValidation = await validateEnvironment()
    if (!postValidation) {
      console.error('❌ Post-token environment validation failed')
      console.log('\n🔍 Running authentication debug utility...')
      await debugAuthentication()
      throw new Error('Environment validation failed. Check output above for details.')
    }

    console.log('\n✅ All environment validations passed - ready to run tests!')
  } catch (error) {
    console.error('✗ Failed to create Clerk testing token:')
    if (axios.isAxiosError(error)) {
      console.error('Status:', error.response?.status)
      console.error('Data:', JSON.stringify(error.response?.data, null, 2))
      console.error('Headers:', error.response?.headers)

      // Check for rate limiting
      if (error.response?.status === 429) {
        console.error('⚠️  RATE LIMIT DETECTED - Clerk API rate limit exceeded')
        console.error('This typically happens when creating too many testing tokens in a short period.')
        console.error('Solutions:')
        console.error('  1. Wait a few minutes before retrying')
        console.error('  2. Use fewer parallel workers in Playwright config')
        console.error('  3. Implement token caching if possible')
      }
    } else if (error instanceof Error) {
      console.error('Error:', error.message)
      console.error('Stack:', error.stack)
    } else {
      console.error('Unknown error:', error)
    }
    throw error
  }
}
