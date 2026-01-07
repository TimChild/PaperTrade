# Task 063: Debug Copilot Agent E2E Clerk Authentication Failures

**Status**: Not Started
**Priority**: HIGH
**Depends On**: None
**Estimated Effort**: 2-4 hours

## Objective

Investigate and fix why GitHub Copilot coding agents cannot run E2E tests with Clerk authentication, even though they should have access to all repository secrets and variables.

## Problem Statement

When GitHub Copilot agents (backend-swe, frontend-swe, etc.) run in the background to create PRs, the E2E tests fail during their workflow execution. However:
- The same E2E tests pass in the main CI workflow
- Local development E2E tests pass
- The agents should have access to the same `CLERK_SECRET_KEY` secret and `E2E_CLERK_USER_EMAIL` variable

## Background Context

### Current Working Setup
From `clerk-implementation-info.md`:
- E2E tests use `@clerk/testing` package for authentication
- Required environment variables:
  - `CLERK_SECRET_KEY` (secret) - for creating sign-in tokens
  - `E2E_CLERK_USER_EMAIL` (variable) - test user email
- Tests use email-based sign-in (not password) to avoid 2FA issues
- Docker Compose backend container needs `CLERK_SECRET_KEY` in environment

### CI Configuration
From `.github/workflows/ci.yml` (lines 167-194):
```yaml
env:
  CLERK_SECRET_KEY: ${{ secrets.CLERK_SECRET_KEY }}
  E2E_CLERK_USER_EMAIL: ${{ vars.E2E_CLERK_USER_EMAIL }}
```

### Repository Secrets/Vars Status
Run `gh secret list` and `gh variable list` to verify:
- ✅ `CLERK_SECRET_KEY` exists in repository secrets
- ✅ `E2E_CLERK_USER_EMAIL` exists in repository variables

## Investigation Steps

### Step 1: Verify Secret/Variable Access in Agent Workflows
1. Check if Copilot agent workflows have different permissions than main CI
2. Look for workflow file differences in access patterns
3. Test if agents are running in a different GitHub Actions context (e.g., fork-based)

### Step 2: Check Docker Environment Variable Propagation
1. Verify `docker-compose.yml` has `CLERK_SECRET_KEY` mapping:
   ```yaml
   backend:
     environment:
       CLERK_SECRET_KEY: ${CLERK_SECRET_KEY}
   ```
2. Check if Docker Compose services are started with correct environment
3. Verify backend container has access to the secret during agent runs

### Step 3: Analyze E2E Test Failure Logs
1. Get recent failed agent PR logs (if available)
2. Look for specific Clerk error messages:
   - "Missing CLERK_SECRET_KEY" → environment not passed
   - "Invalid token" → wrong secret value
   - "User not found" → wrong email or Clerk instance mismatch
3. Check timing: does it fail at setup (global-setup.ts) or during test execution?

### Step 4: Test Environment Variable Visibility
Create a debugging workflow or PR to log (redacted) environment status:
```yaml
- name: Debug Environment
  run: |
    echo "CLERK_SECRET_KEY present: ${{ secrets.CLERK_SECRET_KEY != '' }}"
    echo "E2E_CLERK_USER_EMAIL: ${{ vars.E2E_CLERK_USER_EMAIL }}"
    docker-compose exec backend env | grep CLERK || echo "CLERK_SECRET_KEY not in backend container"
```

### Step 5: Compare Workflow Triggers
Check if agent workflows use different trigger events that affect secret access:
- `pull_request` from fork → secrets NOT available
- `pull_request_target` → secrets available but runs on base branch
- `workflow_run` → may have different secret access

### Step 6: Check Playwright Global Setup
Verify `frontend/tests/e2e/global-setup.ts`:
- Is `clerkSetup()` being called correctly?
- Does it have access to `CLERK_SECRET_KEY` during agent runs?
- Are there any timing issues with Docker services starting?

## Potential Root Causes

### Hypothesis 1: Workflow Trigger Differences
Agent workflows may use different triggers that don't pass secrets/vars.

**Test**: Compare workflow trigger events between main CI and agent workflows.

**Fix**: Update agent workflow triggers to match main CI pattern.

### Hypothesis 2: Docker Compose Environment Not Set
Secrets may not be propagating to Docker Compose services during agent runs.

**Test**: Add debug logging to verify environment variables in containers.

**Fix**: Ensure `docker-compose up` inherits shell environment or explicitly pass vars.

### Hypothesis 3: Playwright Configuration Mismatch
Agent environment may have different Playwright/Node.js setup affecting Clerk integration.

**Test**: Check Node.js version, package versions in agent runs vs local.

**Fix**: Pin versions or update global-setup to handle environment differences.

### Hypothesis 4: Clerk Instance/API Key Mismatch
Agents may be using a different Clerk instance or have wrong API key format.

**Test**: Verify secret value starts with `sk_test_` and matches the frontend `pk_test_` instance.

**Fix**: Update repository secret if wrong key is stored.

### Hypothesis 5: Timing/Race Condition
Backend Docker container may not be fully ready when E2E tests start during agent runs.

**Test**: Add explicit health checks or longer wait times before running tests.

**Fix**: Update workflow to wait for backend health endpoint before starting E2E tests.

## Deliverables

### 1. Investigation Report
Document findings in `agent_progress_docs/TIMESTAMP_debug-copilot-agent-e2e-clerk-auth.md`:
- What you tested
- What you found (logs, error messages, configuration differences)
- Root cause identification
- Proposed solution

### 2. Fix Implementation
Apply the fix based on root cause:
- Update workflow files if trigger/permissions issue
- Update docker-compose.yml if environment propagation issue
- Update global-setup.ts if Playwright configuration issue
- Update repository secrets if wrong key stored

### 3. Validation
- Create a test PR from an agent workflow
- Verify E2E tests pass in the agent's PR checks
- Confirm all 14 E2E tests execute successfully

## Success Criteria

- [ ] Root cause identified and documented
- [ ] Fix implemented and committed
- [ ] E2E tests pass in agent-generated PR workflows
- [ ] All existing E2E tests still pass in main CI
- [ ] Documentation updated with findings

## Files to Investigate

- `.github/workflows/ci.yml` - Main CI configuration
- `.github/workflows/*.yml` - Agent workflow configurations
- `docker-compose.yml` - Environment variable mapping
- `frontend/tests/e2e/global-setup.ts` - Clerk setup
- `frontend/tests/e2e/fixtures.ts` - Test fixtures
- `frontend/playwright.config.ts` - Playwright configuration
- `clerk-implementation-info.md` - Known working patterns

## Commands

```bash
# Check repository secrets/variables
gh secret list
gh variable list

# View recent workflow runs
gh run list --limit 20

# Get logs from a failed run
gh run view <RUN_ID> --log-failed

# Test Docker environment locally
docker-compose up -d
docker-compose exec backend env | grep CLERK
docker-compose down

# Run E2E tests locally
task test:e2e
```

## References

- [GitHub Actions: Encrypted Secrets](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [GitHub Actions: Variables](https://docs.github.com/en/actions/learn-github-actions/variables)
- [Clerk Testing Package](https://clerk.com/docs/testing/playwright)
- `clerk-implementation-info.md` - Critical implementation patterns

## Notes

- Do NOT expose actual secret values in logs or documentation
- Use redacted output (e.g., "sk_test_***") when logging secret presence
- This is blocking agent autonomy - high priority fix
