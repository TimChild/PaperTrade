/**
 * Global teardown for Playwright E2E tests.
 * This runs once after all tests complete.
 *
 * Provides a summary of test data created during the run.
 * In development, you may want to periodically clean up test portfolios
 * using the database command:
 *
 *   docker exec papertrade-db-1 psql -U papertrade -d papertrade_dev -c \
 *     "DELETE FROM portfolios WHERE name LIKE 'Test Portfolio %' OR name LIKE 'Persistent %';"
 */
export default async function globalTeardown(): Promise<void> {
  console.log('')
  console.log('=== E2E Test Global Teardown ===')
  console.log('Tests complete!')
  console.log('')
  console.log('TIP: If test portfolios accumulate in your dev database, clean them up with:')
  console.log(
    '  docker exec papertrade-db-1 psql -U papertrade -d papertrade_dev -c "DELETE FROM portfolios WHERE name LIKE \'Test Portfolio %\' OR name LIKE \'Persistent %\' OR name LIKE \'Analytics Test %\';"'
  )
  console.log('=== Teardown Complete ===')
}
