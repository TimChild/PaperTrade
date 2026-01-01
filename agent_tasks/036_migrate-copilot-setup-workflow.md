# Task 036: Migrate to GitHub's Official Copilot Setup Workflow

**Agent**: quality-infra  
**Priority**: HIGH  
**Created**: 2026-01-01  
**Status**: Not Started

## Objective

Migrate our current `copilot-setup.yml` workflow to GitHub's official `copilot-setup-steps.yml` format to properly configure Copilot coding agent environments.

## Problem

We currently have `.github/workflows/copilot-setup.yml` which was created for manual/CI testing, but GitHub Copilot coding agents **require** a specific file named `.github/workflows/copilot-setup-steps.yml` with a job named `copilot-setup-steps`.

**Documentation**: https://docs.github.com/en/enterprise-cloud@latest/copilot/how-tos/use-copilot-agents/coding-agent/customize-the-agent-environment

## Key Requirements from GitHub Docs

### 1. File Must Be Named Exactly
- **Required**: `.github/workflows/copilot-setup-steps.yml`
- ❌ **Wrong**: `copilot-setup.yml` (our current name)

### 2. Job Must Be Named Exactly
- **Required**: Job name must be `copilot-setup-steps`
- ❌ **Wrong**: `setup` (our current job name)

### 3. Limited Customization
You can ONLY customize these settings:
- `steps` ✅
- `permissions` ✅
- `runs-on` ✅
- `services` ✅
- `snapshot` ✅
- `timeout-minutes` ✅ (max: 59)

All other settings will be ignored by Copilot.

### 4. Workflow Triggers
Should include:
- `workflow_dispatch` - Manual testing
- `push` on paths to the file itself - Auto-validation when changed
- `pull_request` on paths to the file itself - PR validation

### 5. Permissions
Set to **lowest needed**. Copilot gets its own token.
- `contents: read` - If you checkout the repo
- If you don't checkout, Copilot will do it automatically

### 6. fetch-depth Override
The `fetch-depth` option of `actions/checkout` will be overridden by GitHub to allow commit rollbacks.

## Implementation Plan

### Step 1: Rename and Restructure Workflow

Create `.github/workflows/copilot-setup-steps.yml`:

```yaml
name: "Copilot Setup Steps"

# Auto-run when this file changes for validation
# Allow manual testing via Actions tab
on:
  workflow_dispatch:
  push:
    paths:
      - .github/workflows/copilot-setup-steps.yml
  pull_request:
    paths:
      - .github/workflows/copilot-setup-steps.yml

jobs:
  # Job MUST be called `copilot-setup-steps` or Copilot won't use it
  copilot-setup-steps:
    runs-on: ubuntu-latest
    
    # Minimal permissions - Copilot gets its own token
    permissions:
      contents: read  # For actions/checkout
    
    # Maximum timeout for setup
    timeout-minutes: 30
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v5
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'  # Match README
      
      - name: Install uv
        uses: astral-sh/setup-uv@v4
        with:
          version: "latest"
      
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json
      
      - name: Cache uv dependencies
        uses: actions/cache@v4
        with:
          path: ~/.cache/uv
          key: ${{ runner.os }}-uv-${{ hashFiles('backend/uv.lock') }}
          restore-keys: |
            ${{ runner.os }}-uv-
      
      - name: Install Task
        uses: arduino/setup-task@v2
        with:
          version: 3.x
          repo-token: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Install pre-commit
        run: |
          python3 -m pip install --user pre-commit
          pre-commit install
      
      - name: Setup backend dependencies
        run: task setup:backend
      
      - name: Setup frontend dependencies
        run: task setup:frontend
      
      - name: Start Docker services
        run: task docker:up
      
      - name: Wait for services
        run: sleep 5
      
      - name: Verify Docker services healthy
        run: |
          if docker compose ps | grep -q "Up"; then
            echo "✅ Docker services running"
          else
            echo "⚠️  Docker services may not be healthy"
            docker compose ps
          fi
      
      - name: Verify backend imports
        working-directory: backend
        run: |
          if uv run python -c "import papertrade" 2>/dev/null; then
            echo "✅ Backend imports work"
          else
            echo "⚠️  Backend imports failed"
            exit 0  # Don't fail setup
          fi
      
      - name: Summary
        run: |
          echo "=== Copilot Environment Ready ==="
          task --version
          uv --version
          pre-commit --version
          python --version
          node --version
          echo ""
          echo "✅ All setup steps completed!"
```

### Step 2: Delete Old Workflow

Remove `.github/workflows/copilot-setup.yml` since it's not used by Copilot agents and is now redundant.

### Step 3: Update Documentation

Update `.github/copilot-instructions.md` MCP Tools section to reference the new workflow name.

### Step 4: Test the Workflow

1. Create PR with changes
2. Verify workflow runs successfully on PR
3. Manually trigger via Actions tab to validate
4. Merge to main
5. Test by creating a new agent task and verifying environment is pre-configured

## Expected Benefits

1. **Automatic Setup**: Copilot agents will have all dependencies pre-installed
2. **Faster Agent Start**: No trial-and-error dependency installation
3. **Reliable Builds**: Consistent environment every time
4. **Better Agent Experience**: Agents can immediately start working instead of setting up
5. **Reduced API Calls**: No network failures from trying to download tools

## Success Criteria

- ✅ File named `copilot-setup-steps.yml` exists
- ✅ Job named `copilot-setup-steps` exists
- ✅ Workflow runs successfully in GitHub Actions
- ✅ Manual trigger works from Actions tab
- ✅ Old `copilot-setup.yml` deleted
- ✅ Documentation updated
- ✅ Copilot agents can successfully work with pre-configured environment

## Notes

- The `.github/copilot-setup.sh` shell script is still useful for human developers and local setup
- This workflow is specifically for Copilot coding agents running in GitHub Actions
- Once merged to main, all future Copilot agent sessions will use this setup automatically
- If setup steps fail (non-zero exit), Copilot skips remaining steps and continues with partial setup

## Related Files

- `.github/workflows/copilot-setup.yml` (to be deleted)
- `.github/workflows/copilot-setup-steps.yml` (to be created)
- `.github/copilot-instructions.md` (to be updated)
- `.github/copilot-setup.sh` (unchanged - still useful for humans)

## References

- [GitHub Docs: Customize Copilot Agent Environment](https://docs.github.com/en/enterprise-cloud@latest/copilot/how-tos/use-copilot-agents/coding-agent/customize-the-agent-environment)
- [GitHub Actions Workflow Syntax](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions)
