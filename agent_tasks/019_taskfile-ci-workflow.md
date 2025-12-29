# Task 019: Taskfile-Based CI Workflow

**Agent**: quality-infra  
**Created**: 2025-12-28  
**Duration**: 2-3 hours  
**Dependencies**: Task 015 (Workflow improvements - merged)  
**Phase**: Infrastructure - CI/CD improvements

## Context

Currently, our PR workflow (`.github/workflows/pr.yml`) runs CI checks by directly invoking tools (ruff, pytest, npm, etc.) in GitHub Actions. This creates a divergence between what developers run locally and what runs in CI.

**Problem**: When CI fails, agents and developers must:
1. Translate GitHub Actions commands to local equivalents
2. Figure out the exact flags and arguments used
3. Deal with environment differences between local and CI

**Goal**: Create a unified CI workflow that uses **Taskfile commands** for all checks, ensuring local and CI environments behave identically.

## Objectives

1. Create new `.github/workflows/ci.yml` workflow
2. Use `task` commands for all quality checks
3. Add missing Taskfile tasks for CI-specific operations
4. Keep existing `pr.yml` during transition (delete later)
5. Document the new CI workflow for agents
6. Ensure easy local debugging of CI failures

## Requirements

### 1. Create ci.yml Workflow (~1 hour)

Create `.github/workflows/ci.yml` that mirrors `pr.yml` but uses Taskfile commands.

#### Trigger Conditions
```yaml
on:
  pull_request:
    branches:
      - main
  push:
    branches:
      - main  # Also run on direct pushes to main
```

#### Jobs Structure

**Job: backend-checks**
- Install Task runner
- Run `task lint:backend`
- Run `task test:backend`
- Upload coverage to Codecov

**Job: frontend-checks**
- Install Task runner
- Run `task lint:frontend`
- Run `task test:frontend`
- Run `task build:frontend` (check that build works)
- Upload coverage to Codecov

**Job: e2e-tests** (needs: [backend-checks, frontend-checks])
- Start Docker services with `task docker:up`
- Start backend with `task dev:backend` (background)
- Run `task test:e2e`
- Upload Playwright reports

#### Key Principles
1. **Task-first**: Every check must go through a task command
2. **Parallel where possible**: Backend and frontend checks run concurrently
3. **Fast feedback**: Linting before tests
4. **Clear naming**: Job names match what they do
5. **Artifacts**: Always upload test reports and coverage

### 2. Add Missing Taskfile Tasks (~45 minutes)

Add tasks to `Taskfile.yml` that CI needs but don't currently exist:

#### Task: build
```yaml
build:
  desc: "Build all production artifacts"
  cmds:
    - task: build:backend
    - task: build:frontend
```

#### Task: build:backend
```yaml
build:backend:
  desc: "Build backend (check import structure, no syntax errors)"
  dir: "{{.BACKEND_DIR}}"
  cmds:
    - echo "Checking backend imports and structure..."
    - uv run python -m compileall -q .
    - echo "✓ Backend build check passed"
```

#### Task: build:frontend
```yaml
build:frontend:
  desc: "Build frontend for production"
  dir: "{{.FRONTEND_DIR}}"
  cmds:
    - echo "Building frontend..."
    - npm run build
    - echo "✓ Frontend built successfully"
```

#### Task: test:e2e
```yaml
test:e2e:
  desc: "Run end-to-end tests with Playwright"
  dir: "{{.FRONTEND_DIR}}"
  cmds:
    - echo "Running E2E tests..."
    - npm run test:e2e
  preconditions:
    - sh: test -f package.json
      msg: "Frontend not found"
```

#### Task: ci
```yaml
ci:
  desc: "Run all CI checks locally (same as GitHub Actions)"
  cmds:
    - task: lint
    - task: test
    - task: build
    - echo "✓ All CI checks passed!"
```

This `task ci` command lets developers run the **exact same checks** that CI runs.

### 3. Install Task Runner in CI

Add this step to all jobs in `ci.yml`:

```yaml
- name: Install Task
  uses: arduino/setup-task@v2
  with:
    version: 3.x
    repo-token: ${{ secrets.GITHUB_TOKEN }}
```

### 4. Update Documentation (~30 minutes)

#### Update AGENT_ORCHESTRATION.md

Add section on debugging CI failures:

```markdown
## Debugging CI Failures

When CI fails on a PR, you can reproduce the failure locally:

### Quick Reproduction
```bash
# Run ALL CI checks locally
task ci

# Or run specific checks
task lint:backend
task test:frontend
task build
```

### Step-by-Step Debugging
1. Pull the PR branch: `gh pr checkout <PR_NUMBER>`
2. Run the failing job: `task <command>` (from CI logs)
3. Fix the issue
4. Verify fix: `task ci` (runs all checks)
5. Commit and push

### CI Job to Task Mapping
- `backend-checks` → `task lint:backend && task test:backend`
- `frontend-checks` → `task lint:frontend && task test:frontend && task build:frontend`
- `e2e-tests` → `task docker:up && task test:e2e`
```

#### Update README.md

Add CI section to "Development" area:

```markdown
### Running CI Checks Locally

Before pushing, you can run the same checks that CI runs:

```bash
# Run all CI checks (lint + test + build)
task ci

# Or run specific checks
task lint           # All linters
task test           # All tests
task build          # Build checks
```

**Why this matters**: These are the **exact same commands** that run in GitHub Actions CI. If `task ci` passes locally, CI should pass too.
```

## Implementation Details

### ci.yml Structure

```yaml
name: CI

on:
  pull_request:
    branches: [main]
  push:
    branches: [main]

jobs:
  backend-checks:
    name: Backend Checks
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.13'
      
      - name: Install uv
        uses: astral-sh/setup-uv@v4
      
      - name: Install Task
        uses: arduino/setup-task@v2
      
      - name: Install dependencies
        run: task setup:backend
      
      - name: Run linters
        run: task lint:backend
      
      - name: Run tests with coverage
        run: task test:backend
      
      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          files: ./backend/coverage.xml
          flags: backend

  frontend-checks:
    name: Frontend Checks
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      
      - name: Install Task
        uses: arduino/setup-task@v2
      
      - name: Install dependencies
        run: task setup:frontend
      
      - name: Run linters
        run: task lint:frontend
      
      - name: Run tests
        run: task test:frontend
      
      - name: Build check
        run: task build:frontend
      
      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          files: ./frontend/coverage/coverage-final.json
          flags: frontend

  e2e-tests:
    name: E2E Tests
    runs-on: ubuntu-latest
    needs: [backend-checks, frontend-checks]
    
    steps:
      - uses: actions/checkout@v4
      
      # Setup Python, Node, uv, Task...
      
      - name: Start services
        run: task docker:up
      
      - name: Run E2E tests
        run: task test:e2e
      
      - name: Upload Playwright report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: playwright-report
          path: frontend/playwright-report/
```

### Key Differences from pr.yml

| Aspect | pr.yml (old) | ci.yml (new) |
|--------|-------------|--------------|
| **Commands** | Direct tool invocation (`uv run pytest`) | Task commands (`task test:backend`) |
| **Consistency** | CI-specific commands | Same as local development |
| **Debugging** | Hard to reproduce | Easy: `task <command>` |
| **Maintenance** | Duplicate command definitions | Single source of truth (Taskfile) |
| **Setup** | Manual uv sync, npm ci | `task setup:backend`, `task setup:frontend` |

### Coverage Report Configuration

Update `task test:backend` and `task test:frontend` to generate coverage in formats CI needs:

**Backend** (already good):
```yaml
test:backend:
  cmds:
    - uv run pytest --cov=papertrade --cov-report=term --cov-report=html --cov-report=xml
```

**Frontend** (verify coverage output):
```yaml
test:frontend:
  cmds:
    - npm run test -- --coverage --coverage-reporter=json
```

## Testing Requirements

### Manual Testing Checklist

Before submitting PR:

- [ ] `task ci` passes locally
- [ ] `task lint` passes (both backend and frontend)
- [ ] `task test` passes (both backend and frontend)
- [ ] `task build` passes (both backend and frontend)
- [ ] `task test:e2e` passes (with docker services running)

### CI Testing

After PR created:

- [ ] All CI jobs pass in GitHub Actions
- [ ] Coverage reports uploaded to Codecov
- [ ] Job logs are clear and helpful
- [ ] Failure messages point to the correct task command

### Debugging Test

Intentionally break something and verify debugging workflow:

1. Add a linting error to backend code
2. Push to PR
3. CI fails on `backend-checks` job
4. Locally run: `task lint:backend`
5. See same error
6. Fix error
7. Verify: `task lint:backend` passes
8. Push and verify CI passes

## Success Criteria

- [ ] `.github/workflows/ci.yml` created and uses task commands
- [ ] All CI checks use Taskfile tasks (no direct tool invocation)
- [ ] `task ci` command runs all CI checks locally
- [ ] Missing tasks added to Taskfile: `build`, `build:backend`, `build:frontend`, `test:e2e`, `ci`
- [ ] CI passes on a test PR
- [ ] Documentation updated in AGENT_ORCHESTRATION.md and README.md
- [ ] Coverage reports still upload to Codecov correctly
- [ ] Playwright reports upload on E2E test failures
- [ ] Debugging workflow is smooth (break something, run task locally, fix, verify)

## Future Enhancements (Not in This Task)

These can be follow-up tasks:

1. **Branch Protection**: Enable "Require status checks to pass before merging"
2. **Delete pr.yml**: Once ci.yml proven stable, remove old workflow
3. **Matrix Testing**: Test against multiple Python/Node versions
4. **Caching**: Improve uv and npm caching for faster CI
5. **Parallel E2E**: Split E2E tests into parallel jobs

## Notes for Quality-Infra Agent

1. **Task Installation**: Use `arduino/setup-task@v2` action (official)
2. **Working Directories**: Task handles this via `dir:` in Taskfile
3. **Environment Variables**: May need to pass through to task commands
4. **Docker Services**: E2E tests need `docker compose up -d` via `task docker:up`
5. **Coverage Paths**: Ensure coverage files are in expected locations for upload
6. **Artifact Retention**: Keep Playwright reports for 30 days (debugging)

## Architecture Compliance

This task follows **Modern Software Engineering** principles:

- **Feedback Loops**: Fast, local feedback before CI
- **Automation**: Same commands work everywhere
- **Simplicity**: Single source of truth (Taskfile)
- **Testability**: Easy to test CI changes locally

## Definition of Done

1. `ci.yml` created and all jobs passing
2. All Taskfile tasks added and working
3. `task ci` runs complete check suite locally
4. Documentation updated
5. Test PR created and CI passes
6. Agent can debug CI failures using task commands
7. Code reviewed and merged
8. Progress doc created

## Additional Considerations

You raised a great question about whether this makes sense and if there's anything else to add. Here are my thoughts:

### ✅ This Approach Makes Sense Because:

1. **Agent-Friendly**: Agents can test locally with same commands
2. **DX Improvement**: Developers run `task ci` before pushing
3. **Maintenance**: Change CI behavior by editing Taskfile, not YAML
4. **Consistency**: Local and CI environments are identical
5. **Debugging**: CI failures are trivial to reproduce

### 💡 Additional Recommendations:

#### 1. Add `task ci:fast` for Quick Checks
```yaml
ci:fast:
  desc: "Run fast CI checks (lint only, skip tests)"
  cmds:
    - task: lint
    - echo "✓ Fast checks passed. Run 'task ci' for full suite."
```

Useful for quick iterations before committing.

#### 2. Add `task ci:debug` for Verbose Output
```yaml
ci:debug:
  desc: "Run CI with verbose output for debugging"
  cmds:
    - task: lint:backend
    - task: lint:frontend  
    - task: test:backend -- -vv
    - task: test:frontend -- --verbose
```

Helps when CI fails mysteriously.

#### 3. Consider Adding Health Checks

Before running tests, verify environment:

```yaml
ci:check-env:
  desc: "Verify environment is ready for CI"
  cmds:
    - docker compose ps
    - uv --version
    - node --version
    - npm --version
```

#### 4. Add Timing Information

Help agents understand which checks are slow:

```yaml
ci:
  desc: "Run all CI checks with timing"
  cmds:
    - echo "⏱️  Starting CI checks..."
    - time task lint
    - time task test
    - time task build
    - echo "✓ All CI checks passed!"
```

### 🎯 Should These Be In This Task?

I recommend:
- **Yes, include**: `task ci`, `task build`, `task test:e2e` (core functionality)
- **Yes, include**: `task ci:fast` (immediate value)
- **Maybe include**: `task ci:debug` (nice to have, low effort)
- **Future task**: Health checks, timing (separate "CI observability" task)

The core task as described is already valuable. The extras are enhancements that could be added incrementally.

---

**Estimated Duration Breakdown**:
- Create ci.yml: 1 hour
- Add Taskfile tasks: 45 minutes
- Update documentation: 30 minutes
- Testing and debugging: 30 minutes
- **Total**: 2-3 hours
