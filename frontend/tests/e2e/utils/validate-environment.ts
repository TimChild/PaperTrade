/**
 * Environment validation script for E2E tests
 *
 * This script validates that all required services and configuration
 * are properly set up before running E2E tests. It should be run as
 * part of Playwright's globalSetup.
 *
 * Validates:
 * - Environment variables are set
 * - Backend is healthy and responding
 * - Frontend is accessible
 * - PostgreSQL is accessible (via backend)
 * - Redis is accessible (via backend)
 * - Clerk authentication is working
 */

import axios from 'axios'

interface ValidationResult {
  success: boolean
  message: string
  details?: unknown
}

interface ValidationReport {
  passed: ValidationResult[]
  failed: ValidationResult[]
  warnings: ValidationResult[]
}

/**
 * Validate that all required environment variables are set
 */
function validateEnvironmentVariables(): ValidationResult {
  const required = {
    CLERK_SECRET_KEY: process.env.CLERK_SECRET_KEY,
    CLERK_PUBLISHABLE_KEY: process.env.CLERK_PUBLISHABLE_KEY,
    E2E_CLERK_USER_EMAIL: process.env.E2E_CLERK_USER_EMAIL,
  }

  const missing: string[] = []
  const present: string[] = []

  for (const [key, value] of Object.entries(required)) {
    if (!value) {
      missing.push(key)
    } else {
      present.push(key)
    }
  }

  if (missing.length > 0) {
    return {
      success: false,
      message: `Missing required environment variables: ${missing.join(', ')}`,
      details: {
        missing,
        present,
      },
    }
  }

  return {
    success: true,
    message: 'All required environment variables are set',
    details: { variables: present },
  }
}

/**
 * Check if backend is healthy and responding
 */
async function validateBackendHealth(): Promise<ValidationResult> {
  const backendUrl = process.env.VITE_API_BASE_URL || 'http://localhost:8000'
  const healthUrl = `${backendUrl}/health`

  try {
    const response = await axios.get(healthUrl, {
      timeout: 5000,
      validateStatus: () => true, // Don't throw on any status
    })

    if (response.status === 200) {
      return {
        success: true,
        message: 'Backend health check passed',
        details: { url: healthUrl, status: response.status, data: response.data },
      }
    } else {
      return {
        success: false,
        message: `Backend health check failed with status ${response.status}`,
        details: { url: healthUrl, status: response.status, data: response.data },
      }
    }
  } catch (error) {
    if (axios.isAxiosError(error)) {
      return {
        success: false,
        message: `Backend health check failed: ${error.message}`,
        details: {
          url: healthUrl,
          error: error.message,
          code: error.code,
          response: error.response?.data,
        },
      }
    }
    return {
      success: false,
      message: 'Backend health check failed with unknown error',
      details: { url: healthUrl, error: String(error) },
    }
  }
}

/**
 * Check if frontend is accessible
 */
async function validateFrontendAccess(): Promise<ValidationResult> {
  const frontendUrl = process.env.BASE_URL || 'http://localhost:5173'

  try {
    const response = await axios.get(frontendUrl, {
      timeout: 5000,
      validateStatus: () => true,
    })

    if (response.status === 200) {
      return {
        success: true,
        message: 'Frontend is accessible',
        details: { url: frontendUrl, status: response.status },
      }
    } else {
      return {
        success: false,
        message: `Frontend returned status ${response.status}`,
        details: { url: frontendUrl, status: response.status },
      }
    }
  } catch (error) {
    if (axios.isAxiosError(error)) {
      return {
        success: false,
        message: `Frontend is not accessible: ${error.message}`,
        details: {
          url: frontendUrl,
          error: error.message,
          code: error.code,
        },
      }
    }
    return {
      success: false,
      message: 'Frontend check failed with unknown error',
      details: { url: frontendUrl, error: String(error) },
    }
  }
}

/**
 * Test authenticated API request using Clerk testing token
 */
async function validateAuthenticatedRequest(): Promise<ValidationResult> {
  const backendUrl = process.env.VITE_API_BASE_URL || 'http://localhost:8000'
  const apiUrl = `${backendUrl}/api/v1/portfolios`
  const testingToken = process.env.CLERK_TESTING_TOKEN

  if (!testingToken) {
    return {
      success: false,
      message: 'CLERK_TESTING_TOKEN not set (should be set by global-setup.ts)',
      details: { note: 'This validation should run after global-setup.ts' },
    }
  }

  try {
    const response = await axios.get(apiUrl, {
      headers: {
        Authorization: `Bearer ${testingToken}`,
      },
      timeout: 5000,
      validateStatus: () => true,
    })

    // We expect either 200 (portfolios exist) or 200 with empty array
    if (response.status === 200) {
      return {
        success: true,
        message: 'Authenticated API request succeeded',
        details: {
          url: apiUrl,
          status: response.status,
          portfoliosCount: Array.isArray(response.data) ? response.data.length : 'N/A',
        },
      }
    } else if (response.status === 401) {
      return {
        success: false,
        message: 'Authentication failed - Clerk token not accepted by backend',
        details: {
          url: apiUrl,
          status: response.status,
          data: response.data,
          tokenPrefix: testingToken.substring(0, 8) + '...',
        },
      }
    } else {
      return {
        success: false,
        message: `Authenticated request returned unexpected status ${response.status}`,
        details: {
          url: apiUrl,
          status: response.status,
          data: response.data,
        },
      }
    }
  } catch (error) {
    if (axios.isAxiosError(error)) {
      return {
        success: false,
        message: `Authenticated request failed: ${error.message}`,
        details: {
          url: apiUrl,
          error: error.message,
          code: error.code,
          status: error.response?.status,
          data: error.response?.data,
        },
      }
    }
    return {
      success: false,
      message: 'Authenticated request failed with unknown error',
      details: { url: apiUrl, error: String(error) },
    }
  }
}

/**
 * Validate Clerk testing token format and basic properties
 */
function validateClerkTestingToken(): ValidationResult {
  const testingToken = process.env.CLERK_TESTING_TOKEN

  if (!testingToken) {
    return {
      success: false,
      message: 'CLERK_TESTING_TOKEN not set (should be set by global-setup.ts)',
      details: { note: 'This validation should run after global-setup.ts' },
    }
  }

  // Basic validation - Clerk tokens are JWTs with 3 parts
  const parts = testingToken.split('.')
  if (parts.length !== 3) {
    return {
      success: false,
      message: 'CLERK_TESTING_TOKEN does not appear to be a valid JWT',
      details: {
        tokenPrefix: testingToken.substring(0, 8) + '...',
        parts: parts.length,
      },
    }
  }

  return {
    success: true,
    message: 'Clerk testing token is present and appears valid',
    details: {
      tokenPrefix: testingToken.substring(0, 8) + '...',
      tokenSuffix: '...' + testingToken.substring(testingToken.length - 8),
      length: testingToken.length,
    },
  }
}

/**
 * Print validation report
 */
function printReport(report: ValidationReport): void {
  console.log('\n' + '='.repeat(80))
  console.log('E2E ENVIRONMENT VALIDATION REPORT')
  console.log('='.repeat(80))

  if (report.passed.length > 0) {
    console.log('\n✅ PASSED (' + report.passed.length + ' checks)')
    for (const result of report.passed) {
      console.log(`  ✓ ${result.message}`)
      if (result.details) {
        const formatted = JSON.stringify(result.details, null, 2).replace(/\n/g, '\n    ')
        console.log(`    ${formatted}`)
      }
    }
  }

  if (report.warnings.length > 0) {
    console.log('\n⚠️  WARNINGS (' + report.warnings.length + ' checks)')
    for (const result of report.warnings) {
      console.log(`  ⚠ ${result.message}`)
      if (result.details) {
        const formatted = JSON.stringify(result.details, null, 2).replace(/\n/g, '\n    ')
        console.log(`    ${formatted}`)
      }
    }
  }

  if (report.failed.length > 0) {
    console.log('\n❌ FAILED (' + report.failed.length + ' checks)')
    for (const result of report.failed) {
      console.log(`  ✗ ${result.message}`)
      if (result.details) {
        const formatted = JSON.stringify(result.details, null, 2).replace(/\n/g, '\n    ')
        console.log(`    ${formatted}`)
      }
    }
  }

  console.log('\n' + '='.repeat(80))
  console.log(
    `SUMMARY: ${report.passed.length} passed, ${report.warnings.length} warnings, ${report.failed.length} failed`
  )
  console.log('='.repeat(80) + '\n')
}

/**
 * Run all validation checks
 */
export async function validateEnvironment(): Promise<boolean> {
  console.log('\n🔍 Starting E2E environment validation...\n')

  const report: ValidationReport = {
    passed: [],
    failed: [],
    warnings: [],
  }

  // Check 1: Environment variables
  const envVarsResult = validateEnvironmentVariables()
  if (envVarsResult.success) {
    report.passed.push(envVarsResult)
  } else {
    report.failed.push(envVarsResult)
  }

  // Check 2: Backend health
  const backendResult = await validateBackendHealth()
  if (backendResult.success) {
    report.passed.push(backendResult)
  } else {
    report.failed.push(backendResult)
  }

  // Check 3: Frontend access
  const frontendResult = await validateFrontendAccess()
  if (frontendResult.success) {
    report.passed.push(frontendResult)
  } else {
    report.failed.push(frontendResult)
  }

  // Check 4: Clerk testing token (this is set by global-setup.ts)
  const tokenResult = validateClerkTestingToken()
  if (tokenResult.success) {
    report.passed.push(tokenResult)
  } else {
    // This might be a warning if running before global-setup
    report.warnings.push(tokenResult)
  }

  // Check 5: Authenticated request (only if we have a token)
  if (process.env.CLERK_TESTING_TOKEN) {
    const authResult = await validateAuthenticatedRequest()
    if (authResult.success) {
      report.passed.push(authResult)
    } else {
      report.failed.push(authResult)
    }
  }

  // Print report
  printReport(report)

  // Return success if no failures
  return report.failed.length === 0
}

/**
 * Main entry point when run directly
 */
if (import.meta.url.startsWith('file:')) {
  const modulePath = new URL(import.meta.url).pathname
  const scriptPath = process.argv[1]
  if (modulePath === scriptPath || modulePath.endsWith(scriptPath)) {
    validateEnvironment()
      .then((success) => {
        process.exit(success ? 0 : 1)
      })
      .catch((error) => {
        console.error('Validation failed with error:', error)
        process.exit(1)
      })
  }
}
