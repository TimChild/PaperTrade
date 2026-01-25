# Task 171: Fix E2E Testing Infrastructure & Make Failures Debuggable (v2)

**Priority**: HIGH (blocking further development)
**Agent**: frontend-swe
**Estimated effort**: 2-3 hours
**Created**: 2026-01-24
**Updated**: 2026-01-24 (v2 - focused on fix-first approach)

## Problem Statement

**15 out of 22 E2E tests are failing** with backend request timeouts.

**CRITICAL**: First PR attempt (PR #168) added 1700+ lines of infrastructure without fixing the actual problem. This version focuses on **FIX FIRST, minimal infrastructure second**.

## MANDATORY First Steps (Do NOT Skip!)

### Step 1: Run Tests and Read Output (15 min)
```bash
cd /Users/timchild/github/PaperTrade
task test:e2e 2>&1 | tee test-output.log
```

**Read the output**. What do the errors actually say? Don't assume - read the logs.

### Step 2: Diagnose Root Cause (30 min)
Based on test output, investigate:
- What specific error messages appear?
- Check backend logs: `docker logs papertrade-backend-1 --tail 100`
- Is it authentication? Network? Environment?
- Test manually: `curl` the failing endpoints with auth tokens

**Document your findings** before writing any code.

### Step 3: Fix the Actual Problem (1 hour)
Fix whatever is broken. Don't build infrastructure until the tests pass.

### Step 4: Verify Fix (15 min)
```bash
task test:e2e  # Run 1 - must show 22/22 passing
task test:e2e  # Run 2 - confirm stability
task test:e2e  # Run 3 - confirm stability
```

**ALL THREE RUNS MUST SHOW 22/22 PASSING**

### Step 5: Add Minimal Validation (30 min, OPTIONAL)
Only if needed to prevent regression:
- Simple pre-test check (< 100 lines)
- Add to existing global-setup.ts
- No new files unless absolutely necessary

## Known Information (From Prior Investigation)

**DO NOT trust this - verify yourself by running tests**:
- 15/22 tests fail with "timeout of 10000ms exceeded"
- Backend receives no POST requests during tests (only health checks)
- Manual testing works fine
- Authentication test (#1) passes
- PR #168's validation found: "TOKEN_INVALID" - Clerk token rejected by backend

**Likely root cause**: Clerk testing token generation or backend verification issue

## CODE LIMITS (Strictly Enforced)

- **Maximum new lines**: 300 (total across all files)
- **New files**: Maximum 2 (only if absolutely necessary)
- **No new dependencies** without explicit justification
- **No markdown documentation files** (findings go in progress doc only)

If you need more than 300 lines, you're over-engineering.

## Required Fixes

### 1. Pre-Test Environment Validation ⭐ CRITICAL
What You Should Actually Do

### Phase 1: Understand the Problem (45 min)

1. **Run the tests** - see what actually fails
2. **Check backend logs** - what errors does the backend log?
3. **Test auth manually** - does the Clerk token work outside of E2E tests?
4. **Read the code** - how is global-setup.ts creating the token?
5. **Document findings** in progress doc (NOT a new markdown file)

### Phase 2: Fix the Root Cause (1 hour)

Based on your diagnosis, fix the actual issue. Likely candidates:

**If Clerk token is invalid**:
- Check token creation in `frontend/tests/e2e/global-setup.ts`
- Verify token format matches what backend expects
- Check if token needs specific claims or format
- Test token manually: `curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/portfolios`

**If backend auth middleware is broken**:
- Check `backend/zebu/infrastructure/middleware/clerk_auth.py`
- Verify it handles testing tokens correctly
- Check environment variable configuration

**If it's environment setup**:
- Verify Taskfile.yml correctly loads environment variables
- Check that test token is being passed to browser/requests

### Phase 3: Add Minimal Safety (30 min, OPTIONAL)

**Only if absolutely necessary**, add simple validation:

Example (add to `global-setup.ts`, ~30 lines):
```typescript
// At end of global-setup.ts, before returning
console.log('Validating E2E setup...')
try {
  const response = await axios.get('http://localhost:8000/api/v1/portfolios', {
    headers: { Authorization: `Bearer ${process.env.CLERK_TESTING_TOKEN}` }
  })
  console.log('✅ Auth validation passed')
} catch (err) {
  console.error('❌ Auth validation failed:', err.response?.data || err.message)
  throw new Error('Setup validation failed - check backend logs')
}
```

That's it. No separate files, no 400-line validation scripts
1. ✅ All 22 E2E tests pass consistently (run 3 times to confirm)
2. ✅ Validation script catches configuration errors BEFORE tests run
3. ✅ When a test fails, logs clearly show:
   - What request was made
   - What authentication was used
   - What response/error occurred
   - What the backend logged (or didn't log)
4. ✅ Documentation updated with:
   - How to run E2E tests
   - How to debug E2E test failures
   - Common failure modes and solutions
5. ✅ CI pipeline updated to use validation script

## Implementation Approach

### Phase 1: Diagnosis (1-2 hours)
1. Create validation script (`validate-environment.ts`)
2. Create auth debugging utility (`debug-auth.ts`)
3. Run validation and capture detailed output
4. Identify EXACT failure point (e.g., "Clerk token not in request headers")

### Phase 2: Fix Root Cause (1-2 hours)
Based on diagnosis:
- Fix authentication token attachment
- Fix backend CORS/routing
- Fix environment variable loading
- Fix test isolation

### Phase 3: Enhanced Logging (1 hour)
1. Add debug logging to API client (test env only)
2. Add logging to test helpers
3. Update Playwright config to show all logs
4. Update backend to log failed auth attempts

### Phase 4: Validation & Documentation (1 hour)
1. Run full test su (ALL Required)

1. ✅ **All 22 E2E tests pass** - Run `task test:e2e` three times, all show 22/22 passing
2. ✅ **Root cause identified** - Progress doc explains what was broken and how you fixed it
3. ✅ **Minimal code changes** - Total additions < 300 lines
4. ✅ **No new dependencies** - Use existing tools/packages
5. ✅ **Tests run fast** - No slowdown from validation overhead

**Nice to have** (but NOT required for merge):
- Simple validation in global-setup.ts to catch future issues
- Brief debugging notes in progress doc
- `frontend/playwright.config.ts` - Integrate validation script
- `Anti-Patterns to Avoid

❌ **Don't create new files** unless fixing the issue requires it
❌ **Don't write documentation files** (use progress doc only)
❌ **Don't build infrastructure before fixing the bug**
❌ **Don't add logging frameworks** (use console.log if needed)
❌ **Don't create validation scripts** until tests pass
❌ **Don't assume** - run the tests and read the actual errors

## Examples of Good vs Bad Approaches

### ❌ Bad (What PR #168 Did)
1. Assume the problem is lack of validation
2. Build 400-line validation script
3. Build 130-line debug utility
4. Write 400-line README
5. Never actually run tests to see if problem is fixed
6. Result: +1700 lines, tests still fail, problem not solved

### ✅ Good (What You Should Do)
1. Run `task test:e2e` and read actual error
2. See "TOKEN_INVALID" in backend logs
3. Investigate why token is invalid (check global-setup.ts, backend auth middleware)
4. Fix token creation or backend verification (maybe 20-50 lines changed)
5. Run tests 3x - all pass
6. Optionally add simple validation to global-setup.ts (~30 lines)
7. Result: ~100 lines changed, problem solved
## Notes for Agent
Likely Files to Modify (Based on TOKEN_INVALID Issue)

**Primary suspects**:
- `frontend/tests/e2e/global-setup.ts` - Token creation/configuration
- `backend/zebu/infrastructure/middleware/clerk_auth.py` - Token verification
- `.env` file - Environment variable configuration

**Maybe needed**:
- `frontend/tests/e2e/global-setup.ts` - Add simple validation at end (~30 lines)

**Should NOT need to create**:
- ❌ New validation files
- ❌ New debug utilities
- ❌ Documentation files
- ❌ Test helper files
- What checks should (Before Submitting PR)

**MANDATORY** (must all be checked):
- [ ] `task test:e2e` - Run 1: Shows 22/22 passing
- [ ] `task test:e2e` - Run 2: Shows 22/22 passing
- [ ] `task test:e2e` - Run 3: Shows 22/22 passing
- [ ] Progress doc explains what was broken and how you fixed it
- [ ] Total lines added < 300
- [ ] No new npm packages added

**OPTIONAL** (nice to have):
- [ ] Simple validation added to global-setup.ts
- [ ] Backend logs show successful auth for E2E tests
- [ ] Tests run in ~same time as before (no slowdown)`
- Auth setup: `frontend/tests/e2e/global-setup.ts`
- API client: `frontend/src/services/api/client.ts`
- Backend logging: `backend/zebu/infrastructure/middleware/logging_middleware.py`
 - READ THIS CAREFULLY

**This is version 2 of the task because version 1 (PR #168) failed**. It added 1700 lines without fixing the problem.

**Your job**: Fix the bug. That's it.

**Not your job**: Build validation infrastructure, write documentation, create debug utilities.

**How to succeed**:
1. Run the actual tests first (`task test:e2e`)
2. Read the actual error messages (don't assume)
3. Check backend logs (`docker logs papertrade-backend-1`)
4. Fix the actual problem (probably authentication token issue)
5. Verify tests pass 3 times
6. Submit minimal PR (<300 lines)

**How to fail**:
1. Assume you know the problem without running tests
2. Build elaborate validation infrastructure
3. Write hundreds of lines of documentation
4. Never verify tests actually pass
5. Submit PR with 1000+ lines

**Remember**: PR #168 found the issue (TOKEN_INVALID) but didn't fix it. You need to actually **fix** the token issue, not just detect it better.

**Time budget**:
- Diagnosis: 45 min
- Fix: 1 hour
- Verification: 15 min
- Optional validation: 30 min
- **Total: ~2.5 hours**

If you're spending more time than this, you're over-engineering.
