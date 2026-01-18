# E2E Test Authentication Setup

This directory contains setup scripts that run once before all E2E tests.

## How It Works

1. `auth.setup.ts` authenticates with Clerk **once** at the start of the test run
2. Saves authentication state to `playwright/.auth/user.json`
3. All tests reuse this state instead of authenticating individually
4. Reduces Clerk API calls from ~14 (one per test) to 1 per test run

## Benefits

- **Faster tests**: No repeated authentication delays
- **No rate limiting**: Single authentication avoids Clerk rate limits
- **More reliable**: Eliminates flaky auth-related timeouts

## Running Tests

```bash
# Runs setup + all tests
npm run test:e2e

# Run specific test (still uses shared auth)
npx playwright test trading.spec.ts
```

## Troubleshooting

If tests fail with "not authenticated" errors:

1. Delete auth state: `rm -rf playwright/.auth/`
2. Re-run tests: `npm run test:e2e`

The setup will regenerate the auth state.
