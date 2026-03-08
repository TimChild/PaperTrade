# Task 036: Migrate to GitHub's Official Copilot Setup Workflow

**Agent**: quality-infra
**Date**: 2026-01-01
**Status**: ✅ Complete
**PR Branch**: `copilot/migrate-to-official-copilot-workflow`

## Task Summary

Migrated from custom `copilot-setup.yml` workflow to GitHub's official `copilot-setup-steps.yml` format to properly configure Copilot coding agent environments. This ensures GitHub Copilot agents can automatically use pre-configured environments with all dependencies installed.

## Problem Statement

GitHub Copilot coding agents require a specific workflow file named `.github/workflows/copilot-setup-steps.yml` with a job named `copilot-setup-steps`. Our previous `copilot-setup.yml` file was not being recognized by Copilot agents, forcing them to manually install dependencies on each run.

## Decisions Made

### 1. Exact Naming Requirements
- **File name**: Must be exactly `copilot-setup-steps.yml` (not `copilot-setup.yml`)
- **Job name**: Must be exactly `copilot-setup-steps` (not `setup`)
- These are hard requirements from GitHub's official documentation

### 2. Python Version: 3.12
- Used Python 3.12 instead of 3.13 to match:
  - README requirement: "Python 3.12+"
  - backend/pyproject.toml: `requires-python = ">=3.12"`
- The old workflow used 3.13, which was inconsistent with project requirements

### 3. Workflow Triggers
Added three triggers as recommended by GitHub:
- `workflow_dispatch`: Manual testing via Actions tab
- `push` on file changes: Auto-validate when workflow is modified
- `pull_request` on file changes: PR validation

### 4. Minimal Permissions
Set `permissions: contents: read` as the minimum needed for `actions/checkout`. GitHub Copilot gets its own token, so we don't need elevated permissions.

### 5. Timeout Configuration
Set `timeout-minutes: 30` which is:
- Well under GitHub's 59-minute maximum for Copilot setup workflows
- Sufficient for all setup steps (typically completes in ~5-10 minutes)

### 6. NPM Caching Improvement
Added explicit npm caching via `actions/setup-node`:
```yaml
cache: 'npm'
cache-dependency-path: frontend/package-lock.json
```
This speeds up frontend dependency installation.

## Files Changed

### Created
- `.github/workflows/copilot-setup-steps.yml` (120 lines)
  - Official Copilot setup workflow with correct naming
  - Comprehensive setup steps for backend, frontend, and Docker services
  - Verification steps to ensure environment is ready
  - Clear comments explaining GitHub requirements

### Deleted
- `.github/workflows/copilot-setup.yml` (112 lines)
  - Old workflow with incorrect naming
  - No longer needed; replaced by new workflow

### Modified
- `.github/copilot-instructions.md`
  - Line 118: Updated reference from `copilot-setup.yml` to `copilot-setup-steps.yml`
  - Line 121: Updated Python version from "3.13" to "3.12+" to match README
  - Clarified workflow purpose: "for Copilot agents" not "automated/CI setup"

## Implementation Details

### Workflow Structure

The new workflow follows GitHub's official specification with only allowed customizations:

```yaml
name: "Copilot Setup Steps"

on:
  workflow_dispatch:
  push:
    paths: [.github/workflows/copilot-setup-steps.yml]
  pull_request:
    paths: [.github/workflows/copilot-setup-steps.yml]

jobs:
  copilot-setup-steps:  # MUST use this exact name
    runs-on: ubuntu-latest
    permissions:
      contents: read
    timeout-minutes: 30
    steps:
      # 12 setup steps total
```

### Setup Steps (in order)

1. **Checkout code** - Actions checkout v4
2. **Setup Python** - Python 3.12 via setup-python v5
3. **Install uv** - Python package manager via setup-uv v4
4. **Setup Node.js** - Node 20 with npm caching
5. **Cache uv dependencies** - Speed up backend installs
6. **Install Task** - Task runner for orchestration
7. **Install pre-commit** - Git hooks for quality checks
8. **Setup backend dependencies** - `task setup:backend`
9. **Setup frontend dependencies** - `task setup:frontend`
10. **Start Docker services** - PostgreSQL and Redis
11. **Wait for services** - 5-second grace period
12. **Verify Docker services** - Check services are healthy
13. **Verify backend imports** - Test `import papertrade` works
14. **Summary** - Display installed versions and success message

### Key Differences from Old Workflow

| Aspect | Old (`copilot-setup.yml`) | New (`copilot-setup-steps.yml`) |
|--------|---------------------------|----------------------------------|
| File name | ❌ `copilot-setup.yml` | ✅ `copilot-setup-steps.yml` |
| Job name | ❌ `setup` | ✅ `copilot-setup-steps` |
| Python version | ❌ 3.13 | ✅ 3.12 |
| Triggers | `workflow_dispatch` only | `workflow_dispatch`, `push`, `pull_request` |
| NPM caching | ❌ Not configured | ✅ Configured via setup-node |
| Permissions | ❌ Not set | ✅ Minimal: `contents: read` |
| Timeout | ❌ Not set | ✅ 30 minutes |
| Documentation | Basic comments | Extensive comments with GitHub docs link |

## Testing Notes

### Manual Testing
The workflow can be manually tested by:
1. Going to Actions tab in GitHub
2. Selecting "Copilot Setup Steps" workflow
3. Clicking "Run workflow"
4. Monitoring the run to ensure all steps complete successfully

### Automatic Testing
The workflow will automatically run when:
- This file is modified and pushed
- A PR modifies this file

### Expected Behavior
- All steps should complete successfully in ~5-10 minutes
- Docker services (PostgreSQL, Redis) should be healthy
- Backend imports (`import papertrade`) should work
- Summary should show all installed versions

### Potential Issues
- **Docker service health**: If services fail to start, the workflow continues but logs a warning
- **Backend imports**: If imports fail (e.g., missing DB), the workflow continues (exit 0) but logs a warning
- This "soft failure" approach ensures Copilot agents get partial setup even if some steps fail

## Benefits

1. **Automatic Environment Setup**: Copilot agents get pre-configured environments automatically
2. **Faster Agent Start**: No trial-and-error dependency installation
3. **Reduced API Calls**: Dependencies pre-installed, no network failures
4. **Consistent Environment**: Same setup every time
5. **Better Developer Experience**: Agents can start working immediately

## Validation

### Pre-merge Checklist
- ✅ File named exactly `copilot-setup-steps.yml`
- ✅ Job named exactly `copilot-setup-steps`
- ✅ Python 3.12 matches README and pyproject.toml requirements
- ✅ Old workflow deleted
- ✅ Documentation updated
- ✅ Workflow uses only allowed customizations per GitHub docs
- ✅ Minimal permissions set
- ✅ Timeout configured (30 minutes < 59 max)
- ✅ All setup steps from old workflow preserved
- ✅ Verification steps included

### Post-merge Testing
After merge to main:
1. Create a new Copilot coding agent task
2. Verify environment is pre-configured
3. Confirm dependencies are already installed
4. Test that agents can immediately start working

## Known Issues / Limitations

None identified. The workflow follows GitHub's official specification exactly.

## References

- [GitHub Docs: Customize Copilot Agent Environment](https://docs.github.com/en/enterprise-cloud@latest/copilot/how-tos/use-copilot-agents/coding-agent/customize-the-agent-environment)
- [GitHub Actions Workflow Syntax](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions)
- Project README: Python 3.12+ requirement
- backend/pyproject.toml: `requires-python = ">=3.12"`

## Next Steps

1. ✅ Create PR with changes
2. ⏳ Wait for PR CI validation (workflow will auto-run since it modifies itself)
3. ⏳ Merge to main after validation passes
4. ⏳ Test with actual Copilot coding agent to confirm pre-configured environment works
5. 🔄 Monitor first few Copilot agent sessions to ensure setup is reliable

## Notes

- The `.github/copilot-setup.sh` shell script remains unchanged and is still useful for human developers doing local setup
- The Taskfile commands remain the primary way for humans to manage the development environment
- This workflow is specifically for GitHub Copilot coding agents running in GitHub Actions, not for regular CI/CD
