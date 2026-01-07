# GitHub Actions Workflows

This directory contains the CI/CD pipeline definitions for PaperTrade.

## Workflows

### `ci.yml` - Continuous Integration

**Triggers:**
- Pull requests to `main` (opened, synchronized, reopened, ready_for_review)
- Pushes to `main`

**Jobs:**

1. **backend-checks**
   - Lint: `task lint:backend` (ruff check, ruff format, pyright)
   - Test: `task test:backend` (pytest with coverage)
   - Coverage: Upload to Codecov

2. **frontend-checks**
   - Lint: `task lint:frontend` (ESLint, TypeScript type check)
   - Test: `task test:frontend` (Vitest)
   - Build: `task build:frontend` (production build check)
   - Security: `npm audit` (dependency vulnerability scan)
   - Coverage: Upload to Codecov

3. **e2e-tests** (runs after backend-checks and frontend-checks pass)
   - Start Docker services (PostgreSQL, Redis)
   - Start backend server
   - Run Playwright E2E tests: `task test:e2e`
   - Upload Playwright reports as artifacts

**Key Features:**
- Uses Task commands for consistency with local development
- Parallel execution of backend and frontend checks for speed
- Security scanning with npm audit
- Comprehensive coverage reporting
- E2E tests only run if unit tests pass

### `copilot-setup-steps.yml` - Development Environment Setup

**Triggers:**
- Manual dispatch (workflow_dispatch)
- Push to this workflow file (auto-validation)
- Pull request modifying this workflow file

**Purpose:**
Sets up a complete development environment for GitHub Copilot coding agents.

**What it configures:**
- Python 3.12 and uv (package manager)
- Node.js 20 and npm
- Task (task runner)
- pre-commit hooks
- Project dependencies (backend and frontend)
- Docker services (PostgreSQL, Redis)
- **`.env` file with Clerk authentication secrets** (for E2E tests)

**Environment variables configured:**
- `CLERK_SECRET_KEY` (from GitHub Secrets) - for backend JWT validation
- `CLERK_PUBLISHABLE_KEY` (from GitHub Secrets) - for frontend/E2E tests
- `VITE_CLERK_PUBLISHABLE_KEY` (from GitHub Secrets) - for Vite frontend
- `E2E_CLERK_USER_EMAIL` (from GitHub Variables) - for E2E test user

**When to use:**
- Automatically runs when Copilot agents start work
- Manually trigger for testing: `gh workflow run copilot-setup-steps.yml`
- Verifying environment setup works correctly

**Alternative methods:**
- Shell script: `./.github/copilot-setup.sh`
- Task command: `task setup`

## Best Practices

### Running CI Locally

Before pushing, run the same checks locally:

```bash
# Run all CI checks (lint + test + build)
task ci

# Or run specific checks
task lint:backend
task lint:frontend
task test:backend
task test:frontend
task build:frontend
task test:e2e
```

### Debugging CI Failures

1. **Check which job failed** in the GitHub Actions UI
2. **Look at the failing step** to see which task command failed
3. **Run the same task locally**:
   ```bash
   task <failing-command>
   ```
4. **Fix the issue** and verify locally
5. **Push again** and verify CI passes

### CI Job to Task Mapping

| CI Job | Task Commands |
|--------|---------------|
| `backend-checks` | `task setup:backend && task lint:backend && task test:backend` |
| `frontend-checks` | `task setup:frontend && task lint:frontend && task test:frontend && task build:frontend` |
| `e2e-tests` | `task docker:up && task test:e2e` |

## Workflow Maintenance

### Action Versions

All actions are pinned to specific major versions for stability while receiving patches:

- `actions/checkout@v4`
- `actions/setup-python@v5`
- `actions/setup-node@v4`
- `actions/cache@v4`
- `arduino/setup-task@v2`
- `astral-sh/setup-uv@v4`
- `codecov/codecov-action@v4`
- `actions/upload-artifact@v4`

Update these periodically by checking for new releases.

### Adding New Checks

When adding new quality checks:

1. **Add to Taskfile first**: Create a task command (e.g., `task security:backend`)
2. **Test locally**: Run `task <new-command>` to verify it works
3. **Add to ci.yml**: Add a step that runs the task
4. **Update documentation**: Update this README and main README.md
5. **Test in CI**: Create a PR to verify the new check works in CI

### Caching Strategy

The workflows use caching for faster runs:

- **uv dependencies**: `~/.cache/uv` keyed by `backend/uv.lock`
- **npm dependencies**: Built-in Node.js cache using `package-lock.json`

If dependencies aren't updating correctly, check the cache keys.

## Security Scanning

### Current Security Checks

1. **npm audit** (frontend)
   - Runs on every CI build
   - Set to `continue-on-error: true` (warns but doesn't fail)
   - Check audit results in CI logs
   - Upgrade vulnerable dependencies manually

### Future Security Enhancements

Planned additions:
- [ ] Bandit (Python security linter)
- [ ] Dependency vulnerability scanning (Dependabot)
- [ ] Secret scanning (prevent accidental commits)
- [ ] SAST (Static Application Security Testing)

## Secrets and Environment Variables

Required secrets (set in GitHub repository settings → Secrets and variables → Actions):

**Secrets:**
- `CLERK_SECRET_KEY` - Clerk API secret key for JWT validation (required for E2E tests)
- `CLERK_PUBLISHABLE_KEY` - Clerk publishable key for frontend/E2E tests (required for E2E tests)
- `CODECOV_TOKEN` - For uploading coverage reports to Codecov (optional, fails gracefully)
- `GITHUB_TOKEN` - Automatically provided by GitHub Actions

**Variables:**
- `E2E_CLERK_USER_EMAIL` - Email address of test user in Clerk (required for E2E tests)

**Note**: The `copilot-setup-steps.yml` workflow creates a `.env` file with these secrets for Copilot agents to use during their work sessions.

## Performance Optimization

Current optimizations:
- ✅ Parallel job execution (backend and frontend checks run concurrently)
- ✅ Dependency caching (uv and npm)
- ✅ E2E tests only run after basic checks pass
- ✅ Use of Task commands (no duplicate command definitions)

Potential future optimizations:
- [ ] Matrix testing across multiple Python/Node versions
- [ ] Split E2E tests into parallel jobs
- [ ] Conditional job execution based on changed files
- [ ] Self-hosted runners for faster execution

## Troubleshooting

### Common Issues

**Issue**: CI passes locally but fails in GitHub Actions
- **Cause**: Different environment or cached state
- **Solution**: Check action logs for differences, clear caches if needed

**Issue**: npm audit reports vulnerabilities
- **Cause**: Dependencies have known security issues
- **Solution**: Review audit report, update dependencies, or suppress false positives

**Issue**: E2E tests fail intermittently
- **Cause**: Timing issues or test flakiness
- **Solution**: Add proper waits, check service health before tests

**Issue**: Coverage upload fails
- **Cause**: Missing CODECOV_TOKEN or network issues
- **Solution**: Check secret configuration, verify Codecov is accessible

## Related Documentation

- Main project README: `../../README.md`
- Agent orchestration guide: `../../AGENT_ORCHESTRATION.md`
- Copilot instructions: `../.github/copilot-instructions.md`
- Taskfile reference: `../../Taskfile.yml`
- Quality & Infrastructure agent: `../agents/quality-infra.md`

## Changelog

### 2026-01-07: Fixed Copilot Agent E2E Test Failures
- **Fixed**: `copilot-setup-steps.yml` now creates `.env` file with Clerk secrets
- **Added**: Environment variable verification step for debugging
- **Added**: Clerk authentication secrets passed to Docker services
- **Impact**: Copilot agents can now successfully run E2E tests with Clerk authentication
- **Files**: `.github/workflows/copilot-setup-steps.yml`, updated workflow README

### 2026-01-01: Major Workflow Cleanup
- Fixed syntax error in ci.yml (removed invalid hashFiles condition)
- Removed redundant `main.yml` and `pr.yml` workflows
- Created `copilot-setup-steps.yml` for automated environment setup
- Added npm audit security scanning to frontend checks
- Fixed shellcheck warnings
- All workflows validated with actionlint
- Updated documentation across the project

### 2025-12-29: Taskfile-Based CI
- Created ci.yml using Task commands for consistency
- Added E2E testing job with Playwright
- Implemented parallel job execution
- Added coverage reporting to Codecov
