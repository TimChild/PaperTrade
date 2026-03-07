# Task 125: Validate Backend Agent Environment

**Agent**: backend-swe
**Priority**: HIGH
**Related PR**: #125

## Objective

Validate that the backend coding agent environment is properly set up and can run all tests (unit, integration, E2E) successfully. This is a validation task to ensure the environment consolidation work in PR #125 is complete and agents have everything they need.

## Context

We've just consolidated environment setup and validation across all workflows. This task validates that a backend agent can:
1. Validate its environment is set up correctly
2. Run all backend tests successfully
3. Run E2E tests successfully
4. Access all required secrets/environment variables

## Requirements

### 1. Environment Validation

Run the new validation task and verify everything passes:

```bash
task validate:env
```

**Expected**: All checks pass, including:
- Required tools (uv, npm, task, docker, python, node, git)
- Python >= 3.12, Node >= 18
- Docker services running (db, redis)
- Backend dependencies installed
- Backend imports working
- Services healthy

**Report**: Copy the full output of this command.

### 2. Secret Validation

Verify all required secrets are accessible:

```bash
task validate:secrets
```

**Expected**: All Clerk secrets are set for E2E tests.

**Report**: Copy the output (secrets will show as "SET" not actual values).

### 3. Backend Tests

Run all backend tests:

```bash
task test:backend
```

**Expected**: All tests pass with 100% coverage.

**Report**:
- Number of tests passed/failed
- Coverage percentage
- Any errors encountered

### 4. Health Checks

Verify all services are healthy before running E2E tests:

```bash
task health:all
```

**Expected**: Docker services, backend API, and frontend all report healthy.

**Report**: Copy the output.

### 5. E2E Tests

Run the complete E2E test suite:

```bash
task test:e2e
```

**Expected**: All E2E tests pass.

**Report**:
- Number of E2E tests passed/failed
- Any timeouts or service issues
- Screenshots/traces if any failures

### 6. Full CI Simulation

Run the complete CI suite locally:

```bash
task ci
```

**Expected**: All quality checks and tests pass.

**Report**: Overall pass/fail status.

## Success Criteria

- [x] `task validate:env` passes
- [x] `task validate:secrets` confirms secrets are set
- [x] `task test:backend` passes (100% coverage)
- [x] `task health:all` reports all services healthy
- [x] `task test:e2e` passes all tests
- [x] `task ci` passes completely
- [x] No errors accessing environment variables
- [x] No Docker service issues

## Failure Reporting

If ANY check fails, report:
1. **What failed**: Exact command and error message
2. **Environment details**: Output of `task validate:env`
3. **Logs**: Relevant Docker logs, test output, traces
4. **Suspected cause**: Best guess at what's wrong

## Deliverable

Create a comment on PR #125 with:

```markdown
## Backend Agent Environment Validation Report

**Agent**: backend-swe
**Date**: [timestamp]

### Environment Validation
[paste output or ✅/❌]

### Secret Validation
[paste output or ✅/❌]

### Backend Tests
- Tests: X passed, Y failed
- Coverage: Z%
- Status: ✅/❌

### Health Checks
[paste output or ✅/❌]

### E2E Tests
- Tests: X passed, Y failed
- Status: ✅/❌

### Full CI
- Status: ✅/❌

### Summary
[Overall pass/fail with any issues encountered]

### Recommendation
[APPROVE / REQUEST CHANGES / NEEDS INVESTIGATION]
```

## Notes

- This is a **validation task**, not an implementation task
- The goal is to **verify the environment works**, not to fix issues
- If you encounter failures, **report them clearly** but don't try to fix them
- Run all commands from the repository root
- Make sure Docker services are running (`task docker:up:all`)
