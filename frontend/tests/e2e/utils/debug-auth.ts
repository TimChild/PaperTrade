/**
 * Authentication debugging utility for E2E tests
 *
 * This utility helps diagnose authentication issues by:
 * - Testing Clerk testing token directly
 * - Making authenticated API requests
 * - Logging detailed request/response information
 */

import axios from 'axios'

/**
 * Debug authentication token and make test API request
 */
export async function debugAuthentication(): Promise<void> {
  console.log('\n' + '='.repeat(80))
  console.log('AUTHENTICATION DEBUG UTILITY')
  console.log('='.repeat(80) + '\n')

  const testingToken = process.env.CLERK_TESTING_TOKEN
  const backendUrl = process.env.VITE_API_BASE_URL || 'http://localhost:8000'

  // Step 1: Check if token is set
  console.log('Step 1: Checking Clerk testing token...')
  if (!testingToken) {
    console.error('❌ CLERK_TESTING_TOKEN is not set')
    console.log('This token should be created by global-setup.ts')
    return
  }

  console.log('✓ CLERK_TESTING_TOKEN is set')
  console.log(`  Token length: ${testingToken.length}`)
  console.log(`  Token prefix: ${testingToken.substring(0, 8)}...`)
  console.log(`  Token suffix: ...${testingToken.substring(testingToken.length - 8)}`)

  // Step 2: Validate JWT structure
  console.log('\nStep 2: Validating JWT structure...')
  const parts = testingToken.split('.')
  if (parts.length !== 3) {
    console.error(`❌ Token does not have 3 parts (has ${parts.length})`)
    return
  }
  console.log('✓ Token has valid JWT structure (3 parts)')

  // Try to decode payload (without verification, just for debugging)
  try {
    const payload = JSON.parse(Buffer.from(parts[1], 'base64').toString('utf-8'))
    console.log('  Payload preview:', JSON.stringify(payload, null, 2))
  } catch (error) {
    console.warn('⚠ Could not decode JWT payload:', error)
  }

  // Step 3: Test backend health
  console.log('\nStep 3: Testing backend health...')
  try {
    const healthResponse = await axios.get(`${backendUrl}/health`, { timeout: 5000 })
    console.log(`✓ Backend is healthy (status ${healthResponse.status})`)
    console.log('  Response:', JSON.stringify(healthResponse.data, null, 2))
  } catch (error) {
    console.error('❌ Backend health check failed:', error)
    if (axios.isAxiosError(error)) {
      console.error('  Error code:', error.code)
      console.error('  Error message:', error.message)
    }
    return
  }

  // Step 4: Test authenticated request
  console.log('\nStep 4: Testing authenticated API request...')
  const apiUrl = `${backendUrl}/api/v1/portfolios`
  console.log(`  URL: ${apiUrl}`)
  console.log(`  Authorization: Bearer ${testingToken.substring(0, 8)}...`)

  try {
    const response = await axios.get(apiUrl, {
      headers: {
        Authorization: `Bearer ${testingToken}`,
        'Content-Type': 'application/json',
      },
      timeout: 5000,
      validateStatus: () => true, // Don't throw on any status
    })

    console.log(`\nResponse received:`)
    console.log(`  Status: ${response.status}`)
    console.log(`  Status Text: ${response.statusText}`)
    console.log(`  Headers:`, JSON.stringify(response.headers, null, 2))

    if (response.status === 200) {
      console.log('✓ Authenticated request succeeded')
      console.log('  Data:', JSON.stringify(response.data, null, 2))
    } else if (response.status === 401) {
      console.error('❌ Authentication failed - backend rejected token')
      console.error('  Response data:', JSON.stringify(response.data, null, 2))
      console.error('\nPossible causes:')
      console.error('  - Token expired or invalid')
      console.error('  - Backend Clerk configuration mismatch')
      console.error('  - Token not properly formatted in Authorization header')
    } else {
      console.warn(`⚠ Unexpected status code: ${response.status}`)
      console.log('  Data:', JSON.stringify(response.data, null, 2))
    }
  } catch (error) {
    console.error('❌ Authenticated request failed with error')
    if (axios.isAxiosError(error)) {
      console.error('  Error code:', error.code)
      console.error('  Error message:', error.message)
      console.error('  Response status:', error.response?.status)
      console.error('  Response data:', JSON.stringify(error.response?.data, null, 2))
    } else {
      console.error('  Error:', error)
    }
  }

  console.log('\n' + '='.repeat(80) + '\n')
}

/**
 * Main entry point when run directly
 */
if (import.meta.url.startsWith('file:')) {
  const modulePath = new URL(import.meta.url).pathname
  const scriptPath = process.argv[1]
  if (modulePath === scriptPath || modulePath.endsWith(scriptPath)) {
    debugAuthentication()
      .then(() => {
        console.log('Debug complete')
      })
      .catch((error) => {
        console.error('Debug failed:', error)
        process.exit(1)
      })
  }
}
