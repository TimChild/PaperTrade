# Task 034: Fix CI Workflows and Add Copilot Environment Setup

## Priority

**HIGH** - Broken CI is blocking PR validation

## Problem

Multiple issues with GitHub Actions workflows:

1. **ci.yml has syntax error**:
   ```yaml
   if: hashFiles('frontend/package.json') != ''
   # ERROR: hashFiles must be in expression context ${{ }}
   ```

2. **Redundant workflows**: `main.yml` and `pr.yml` duplicate what `ci.yml` already does
   - All three workflows run linting and tests
   - `ci.yml` uses Task commands (preferred)
   - `main.yml` and `pr.yml` use direct `uv run` commands
   - Maintaining three workflows is error-prone

3. **Missing Copilot environment setup workflow**:
   - When Copilot coding agents start, they need task and pre-commit installed
   - Currently this is manual via `.github/copilot-setup.sh`
   - Should be automated via GitHub Actions workflow

## Objectives

1. ✅ Fix `ci.yml` syntax errors
2. ✅ Remove redundant `main.yml` and `pr.yml` workflows
3. ✅ Add comprehensive validation to CI workflow
4. ✅ Create `.github/workflows/copilot-setup.yml` for agent environment setup
5. ✅ Ensure workflows follow GitHub Actions best practices
6. ✅ Use latest action versions
7. ✅ Continue using Task commands for consistency

## Requirements

### 1. Fix ci.yml

**Syntax Errors to Fix**:
```yaml
# WRONG:
if: hashFiles('frontend/package.json') != ''

# CORRECT:
if: ${{ hashFiles('frontend/package.json') != '' }}
```

**Additional Improvements**:
- Validate workflow syntax before committing
- Add matrix testing for multiple Python versions (if needed)
- Add proper failure handling
- Add status badges to README
- Optimize caching strategy

### 2. Remove Redundant Workflows

Delete:
- `.github/workflows/main.yml` (duplicates ci.yml for push to main)
- `.github/workflows/pr.yml` (duplicates ci.yml for PRs)

**Rationale**:
- `ci.yml` already handles both `push` and `pull_request` events
- Single source of truth is easier to maintain
- Task-based approach is more flexible

### 3. Enhance ci.yml

Add missing checks:
- [ ] Docker compose services start successfully
- [ ] Database migrations apply cleanly
- [ ] Integration tests run (if different from unit tests)
- [ ] Security scanning (bandit for Python, npm audit for frontend)
- [ ] Dependency vulnerability checks

Optional enhancements:
- [ ] Parallel job execution for speed
- [ ] Skip checks if no relevant files changed
- [ ] Artifact uploads for failed tests
- [ ] Slack/Discord notifications on failure

### 4. Create copilot-setup.yml

New workflow: `.github/workflows/copilot-setup.yml`

**Trigger**: Manual dispatch (for Copilot agents to run)

**Purpose**:
- Install system dependencies (task, pre-commit, etc.)
- Set up Python and Node.js environments
- Install project dependencies
- Configure development tools

**Example**:
```yaml
name: Copilot Environment Setup

on:
  workflow_dispatch:  # Manual trigger

jobs:
  setup:
    name: Setup Development Environment
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.13'

      - name: Install uv
        uses: astral-sh/setup-uv@v4
        with:
          version: "latest"

      - name: Install Task
        uses: arduino/setup-task@v2
        with:
          version: 3.x
          repo-token: ${{ secrets.GITHUB_TOKEN }}

      - name: Install pre-commit
        run: pip install pre-commit

      - name: Setup environment
        run: task setup

      - name: Verify installation
        run: |
          task --version
          pre-commit --version
          uv --version

      - name: Environment ready
        run: echo "✅ Development environment is ready!"
```

**Note**: This might require repo permissions that Copilot agents don't have. If so, document the limitation and suggest alternatives (like keeping the shell script).

## Implementation Checklist

### Phase 1: Fix Immediate Issues

- [ ] Fix `hashFiles` syntax error in ci.yml (line 71)
- [ ] Test workflow locally with `act` or GitHub's workflow validator
- [ ] Validate all expressions use proper `${{ }}` syntax
- [ ] Update action versions to latest

### Phase 2: Clean Up

- [ ] Delete `main.yml`
- [ ] Delete `pr.yml`
- [ ] Update documentation references to removed workflows
- [ ] Verify ci.yml covers all use cases from deleted workflows

### Phase 3: Enhance CI

- [ ] Add security scanning
- [ ] Add dependency vulnerability checks
- [ ] Add Docker service health checks
- [ ] Optimize job parallelization
- [ ] Add clear failure messages

### Phase 4: Copilot Setup

- [ ] Create `copilot-setup.yml` workflow
- [ ] Test workflow dispatch trigger
- [ ] Document any permission limitations
- [ ] Update `.github/copilot-instructions.md` to reference new workflow
- [ ] Decide if `.github/copilot-setup.sh` should be kept or removed

## GitHub Actions Best Practices

### 1. Use Latest Actions

```yaml
# Check and update:
actions/checkout@v4         # Latest: v4
actions/setup-python@v5     # Latest: v5
actions/setup-node@v4       # Latest: v4
actions/cache@v4            # Latest: v4
arduino/setup-task@v2       # Latest: v2
astral-sh/setup-uv@v4       # Latest: v4
```

### 2. Expression Syntax

```yaml
# ALWAYS use ${{ }} for expressions
if: ${{ expression }}

# Even for simple ones:
if: ${{ github.event_name == 'push' }}

# NOT:
if: github.event_name == 'push'  # ❌ Won't work
```

### 3. Caching Best Practices

```yaml
# Cache key should include all relevant files
key: ${{ runner.os }}-${{ hashFiles('**/lockfile') }}

# Restore keys for partial matches
restore-keys: |
  ${{ runner.os }}-
```

### 4. Job Dependencies

```yaml
jobs:
  lint:
    runs-on: ubuntu-latest
    steps: [...]

  test:
    needs: lint  # Wait for lint to pass
    runs-on: ubuntu-latest
    steps: [...]
```

### 5. Conditional Execution

```yaml
# Run only if files changed
if: ${{ contains(github.event.head_commit.modified, 'backend/') }}

# Skip draft PRs
if: ${{ github.event.pull_request.draft == false }}
```

## Validation

Before committing workflow changes:

1. **Lint workflow files**:
   ```bash
   # Use actionlint
   brew install actionlint  # or: go install github.com/rhysd/actionlint@latest
   actionlint .github/workflows/*.yml
   ```

2. **Test locally** (optional):
   ```bash
   # Use act
   brew install act
   act pull_request --list  # List jobs
   act pull_request -j backend-checks  # Run specific job
   ```

3. **GitHub's validator**: Push to a branch and check Actions tab for syntax errors

## Success Criteria

- [ ] All workflow files pass `actionlint` validation
- [ ] CI runs successfully on a test PR
- [ ] No redundant workflows remain
- [ ] Copilot setup workflow can be manually triggered
- [ ] All Task commands work in CI
- [ ] Workflow uses latest action versions
- [ ] Clear failure messages when checks fail
- [ ] Documentation updated

## Permission Issues

If Copilot agents hit permission issues (likely scenarios):

### Issue 1: Cannot push workflow file changes
**Symptom**: Agent can create files but not push to `.github/workflows/`

**Solution**:
- Agent should create workflow in a different location first
- Agent creates PR with changes
- Human reviewer approves and merges
- Document in PR: "Note: Workflow changes require manual review"

### Issue 2: Cannot trigger workflows
**Symptom**: `workflow_dispatch` doesn't work for agents

**Solution**:
- Keep `.github/copilot-setup.sh` as fallback
- Document: "Use `./. github/copilot-setup.sh` for manual setup"
- Workflow is for humans to trigger on agent's behalf

### Issue 3: Secrets access
**Symptom**: `GITHUB_TOKEN` or `CODECOV_TOKEN` not available

**Solution**:
- Document required secrets in README
- Use `secrets: inherit` in workflow calls
- Fail gracefully if secrets missing (mark as optional)

## Files to Change

- [ ] `.github/workflows/ci.yml` - Fix syntax and enhance
- [ ] `.github/workflows/main.yml` - DELETE
- [ ] `.github/workflows/pr.yml` - DELETE
- [ ] `.github/workflows/copilot-setup.yml` - CREATE
- [ ] `.github/copilot-instructions.md` - Update workflow references
- [ ] `README.md` - Update CI badge, document workflows
- [ ] `.github/workflows/README.md` - Create if doesn't exist

## Testing Plan

1. Create test branch with fixes
2. Open PR to verify CI runs
3. Check all jobs pass
4. Manually trigger copilot-setup workflow
5. Verify no regressions from deleted workflows

## References

- [GitHub Actions Syntax](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions)
- [Expression Syntax](https://docs.github.com/en/actions/learn-github-actions/expressions)
- [Workflow Commands](https://docs.github.com/en/actions/using-workflows/workflow-commands-for-github-actions)
- [actionlint](https://github.com/rhysd/actionlint)

---

**Created**: January 1, 2026
**Estimated Time**: 3-4 hours
**Agent**: quality-infra
