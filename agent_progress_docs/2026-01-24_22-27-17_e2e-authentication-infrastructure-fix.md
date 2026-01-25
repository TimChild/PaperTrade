# E2E Authentication Infrastructure Fix

**Date**: 2026-01-24
**Agent**: quality-infra
**Related PR**: #171

## Task Summary

Fixed intermittent E2E test failures caused by Clerk session token expiration. Replaced the storage state authentication approach with per-test `clerk.signIn()` calls that generate longer-lived sign-in tokens.

## Problem Analysis

The E2E tests were failing intermittently with authentication errors. Investigation revealed:

1. **Storage State Approach**: The previous implementation saved Clerk authentication to `playwright/.auth/user.json` via a setup project
2. **60-Second Session Tokens**: Clerk session tokens expire in 60 seconds
3. **Race Condition**: Tests that ran after the setup project often used expired tokens
4. **Symptom**: Tests passed when run quickly but failed in CI or with parallel workers

## Decisions Made

1. **Per-Test Authentication**: Use `clerk.signIn({ page, emailAddress })` at the start of each test
   - Sign-in tokens last 5 minutes (vs 60-second session tokens)
   - Each test gets fresh, valid authentication
   - Eliminates race conditions between tests

2. **Remove Setup Project**: Deleted `tests/e2e/setup/` entirely
   - No longer need a separate authentication setup phase
   - Simplifies test configuration

3. **Add Cleanup Infrastructure**: Created `test:e2e:cleanup` task
   - E2E tests create portfolios that accumulate over time
   - Cleanup prevents database bloat and API timeouts
   - CI now runs cleanup before tests automatically

## Files Changed

- `frontend/playwright.config.ts` - Removed storage state config, added global teardown, set 3 workers
- `frontend/tests/e2e/fixtures.ts` - Completely rewritten to use `clerk.signIn()` per test
- `frontend/tests/e2e/global-setup.ts` - Simplified to only call `clerkSetup()`
- `frontend/tests/e2e/global-teardown.ts` - New file with cleanup tips
- `Taskfile.yml` - Added `test:e2e:cleanup` task, updated `ci:e2e` to include cleanup
- Deleted: `frontend/tests/e2e/setup/auth.setup.ts`, `frontend/tests/e2e/setup/README.md`
- Deleted: `frontend/playwright/.auth/user.json`

## Testing Notes

- All 20 E2E tests pass consistently
- Tests run in parallel (3 workers) without auth conflicts
- Verified cleanup task removes accumulated test portfolios
- Output is terminal-only (no HTML reports) for agent compatibility

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
3. Sign-in token valid for 5 minutes
4. Test runs with fresh auth → PASS
```

### Key Code Pattern

```typescript
// fixtures.ts
export const test = clerkTest.extend<AuthenticatedFixtures>({
  page: async ({ page, clerk }, use) => {
    const emailAddress = process.env.E2E_CLERK_USER_EMAIL;
    await clerk.signIn({ page, emailAddress });
    await use(page);
  },
});
```

## Known Issues/Next Steps

- Monitor CI runs to confirm reliability improvement
- Consider adding test data isolation (each test uses unique portfolio names)
- May want to add periodic cleanup job if database grows large
