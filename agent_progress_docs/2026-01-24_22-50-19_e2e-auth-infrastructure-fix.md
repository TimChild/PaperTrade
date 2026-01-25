# E2E Authentication Infrastructure Fix

**Date**: 2026-01-24
**Agent**: quality-infra
**Related PR**: #171

## Task Summary

Fixed intermittent E2E test failures caused by Clerk session token expiration. Replaced the storage state authentication approach with per-test `clerk.signIn()` calls that generate fresh authentication for each test.

## Problem Analysis

The E2E tests were failing intermittently with authentication errors. Investigation revealed:

1. **Storage State Approach**: The previous implementation saved Clerk authentication to `playwright/.auth/user.json` via a setup project
2. **60-Second Session Tokens**: Clerk session tokens expire in 60 seconds (confirmed in Clerk docs)
3. **Race Condition**: Tests that ran after the setup project often used expired tokens
4. **Symptom**: Tests passed when run quickly but failed in CI or with parallel workers

### Evidence from Testing

On `main` branch:
- **First run** (fresh storage state created): 20/21 tests passed
- **Second run** (~2 minutes later, reusing storage state): 12 failures

## Decisions Made

1. **Per-Test Authentication**: Use `clerk.signIn({ page, emailAddress })` at the start of each test
   - Each test gets fresh, valid authentication
   - Eliminates race conditions between tests
   - Works reliably in parallel execution

2. **Remove Setup Project**: Deleted `tests/e2e/setup/` entirely
   - No longer need a separate authentication setup phase
   - Simplifies test configuration

3. **Email-Based Auth**: Continue using `emailAddress` parameter (not password strategy)
   - Password auth triggers 2FA in our Clerk instance
   - Documented in our architecture docs

4. **Add Cleanup Infrastructure**: Created `test:e2e:cleanup` task
   - E2E tests create portfolios that accumulate over time
   - Cleanup prevents database bloat and API timeouts
   - CI now runs cleanup before tests automatically

## Files Changed

- `frontend/playwright.config.ts` - Removed storage state config, added global teardown, set 3 workers
- `frontend/tests/e2e/fixtures.ts` - Completely rewritten to use `clerk.signIn()` per test
- `frontend/tests/e2e/global-setup.ts` - Simplified to only call `clerkSetup()`
- `frontend/tests/e2e/global-teardown.ts` - New file with cleanup tips
- `Taskfile.yml` - Added `test:e2e:cleanup` task, updated `ci:e2e` to include cleanup

### Deleted Files
- `frontend/tests/e2e/setup/auth.setup.ts`
- `frontend/tests/e2e/setup/README.md`
- `frontend/playwright/.auth/user.json`

## Testing Notes

- All 20 E2E tests pass consistently (1 intentionally skipped)
- Tests run in parallel (3 workers) without auth conflicts
- Verified consecutive runs pass (no token expiration issues)
- Runtime: ~1.1-2.2 minutes

## Technical Details

### Clerk Authentication Flow

```
Previous (broken):
1. Setup project runs first
2. Calls clerk.signIn() and saves storage state
3. Session token expires in 60 seconds
4. Later tests use expired token → FAIL

New (working):
1. Each test extends from authenticated fixture
2. Fixture calls clerk.signIn({ page, emailAddress })
3. Fresh session created for each test
4. Test runs with valid auth → PASS
```

### Key Code Pattern

```typescript
// fixtures.ts
export const test = base.extend({
  page: async ({ page }, use) => {
    const email = process.env.E2E_CLERK_USER_EMAIL;
    await setupClerkTestingToken({ page });
    await page.goto('/');
    await clerk.signIn({ page, emailAddress: email });
    await page.waitForURL('**/dashboard', { timeout: 15000 });
    await use(page);
  },
});
```

## Rate Limit Consideration

Per-test auth means 20 API calls per run. This is acceptable because:
- Clerk's rate limits are per-second/per-minute, not per-day
- Tests take ~5 seconds each, well under rate limits
- Testing with one user doesn't impact MAU limits

## Known Issues/Next Steps

- Monitor CI runs to confirm reliability improvement
- Consider adding test data isolation (unique portfolio names per test)
- May want periodic cleanup job if database grows large
