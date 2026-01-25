# Task 133: Verify E2E Tests in GitHub Agent Environment

**Status**: Not Started
**Agent**: quality-infra
**Priority**: Medium
**Estimated Effort**: 30-60 minutes
**Created**: 2026-01-14

## Context

PRs #126 and #127 validated that backend and frontend unit tests work in the GitHub agent environment, but encountered Docker build performance issues (215s npm install) that prevented E2E test validation.

**What we know**:
- ✅ Unit tests: 545 backend + 197 frontend tests passing
- ✅ Environment validation: All tools and secrets configured
- ✅ Docker base services: PostgreSQL and Redis running
- ❌ E2E tests: Not validated due to Docker build slowness
- ❌ Full CI: Could not complete due to E2E dependency

**Question**: Can E2E tests actually run in the agent environment, or is there a blocker?

## Objective

Verify whether E2E tests can successfully run in the GitHub agent environment, or document specific blockers preventing them.

**This is a diagnostic task** - we need to know if agents can run E2E tests autonomously or if there are infrastructure limitations.

## Requirements

### 1. Attempt to Run E2E Tests

Try to execute the E2E test suite:

```bash
task test:e2e
```

**Expected behavior**: One of three outcomes:
1. ✅ Tests pass (success!)
2. ❌ Tests fail due to Docker build timeout/slowness (known issue)
3. ❌ Tests fail due to other issues (needs investigation)

### 2. Diagnostic Information

If tests fail, collect diagnostic info:

```bash
# Check Docker build performance
time docker compose build frontend 2>&1 | tee build-timing.log

# Check if services can start
task docker:up:all
docker compose ps

# Check health endpoints
task health:all

# Check if Playwright is available
npx playwright --version

# Check Clerk secrets are accessible
task validate:secrets
```

### 3. Determine Root Cause

Analyze what's blocking E2E tests:

**Possible causes**:
- Docker build timeout (GitHub Actions runner network constraints)
- Playwright browser download blocked by firewall
- Frontend container not accessible from test runner
- Clerk authentication issues
- Missing environment variables

### 4. Report Findings

Document in agent progress doc:

**If E2E tests pass**:
- ✅ E2E tests work in agent environment
- Number of tests passed
- Execution time
- Recommendation: Agent can autonomously run E2E tests

**If E2E tests fail**:
- Root cause analysis
- Specific error messages
- Whether this is a temporary issue (retry-able) or permanent blocker
- Recommendation: Either fix is needed OR E2E tests can only run locally/in main CI

## Success Criteria

- [x] Attempt to run `task test:e2e`
- [x] Document outcome (pass/fail + details)
- [x] If failed: Provide root cause analysis
- [x] Clear recommendation on whether agents can run E2E tests

## References

- PR #126: Backend agent validation (unit tests ✅, E2E ❌)
- PR #127: Frontend agent validation (unit tests ✅, E2E ❌)
- Task #067: Previous E2E verification attempt
- `.github/workflows/copilot-setup-steps.yml`: Agent environment setup

## Notes

- **Don't try to fix issues** - this is diagnostic only
- If Docker build is too slow, that's a valid finding (report it)
- If E2E tests can't run in agent environment, that's okay - we can run them in main CI
- The goal is to **know the current state**, not necessarily to make everything work

## Acceptance

Agent progress doc that clearly states:
- ✅ E2E tests work in agent environment (agents can validate E2E changes autonomously)
- OR ❌ E2E tests don't work in agent environment due to [specific reason] (agents use unit tests only, E2E validation happens in main CI)
