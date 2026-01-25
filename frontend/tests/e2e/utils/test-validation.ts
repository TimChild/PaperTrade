#!/usr/bin/env tsx
/**
 * Standalone test script to verify environment validation works
 *
 * This script can be run without Playwright to test the validation logic.
 * Usage: npx tsx test-validation.ts
 */

import { validateEnvironment } from './validate-environment'

console.log('Testing E2E Environment Validation Script')
console.log('==========================================\n')

console.log('Current environment variables:')
console.log('  CLERK_SECRET_KEY:', process.env.CLERK_SECRET_KEY ? 'SET' : 'NOT SET')
console.log('  CLERK_PUBLISHABLE_KEY:', process.env.CLERK_PUBLISHABLE_KEY ? 'SET' : 'NOT SET')
console.log('  E2E_CLERK_USER_EMAIL:', process.env.E2E_CLERK_USER_EMAIL || 'NOT SET')
console.log('  VITE_API_BASE_URL:', process.env.VITE_API_BASE_URL || 'NOT SET (using default)')
console.log('  BASE_URL:', process.env.BASE_URL || 'NOT SET (using default)')
console.log('')

validateEnvironment()
  .then((success) => {
    if (success) {
      console.log('\n✅ Validation completed successfully!')
      console.log('The E2E environment is properly configured and ready to run tests.')
      process.exit(0)
    } else {
      console.log('\n❌ Validation failed!')
      console.log('Please fix the issues above before running E2E tests.')
      process.exit(1)
    }
  })
  .catch((error) => {
    console.error('\n💥 Validation crashed with error:')
    console.error(error)
    process.exit(1)
  })
