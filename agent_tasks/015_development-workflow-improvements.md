# Task 015: Development Workflow & Tooling Improvements

**Created**: 2025-12-28 18:35 PST
**Priority**: P2 - IMPORTANT (improves developer & agent experience)
**Estimated Effort**: 2-3 hours
**Agent**: Refactorer

## Objective

Improve development workflow and tooling to make it easier for both human developers and Copilot agents to work efficiently. Address pain points with pre-commit hooks and set up proper agent environment configuration.

## Context

### Current Issues

1. **Pre-commit Friction**: Auto-fixes (trailing whitespace, line endings, ruff format) require developers to write commit messages twice - once before auto-fix, once after
2. **Agent Environment**: Copilot agents start with unconfigured environments (no pre-commit, no synced dependencies)
3. **Missing Documentation**: No clear setup instructions for agents in repository

### Quality Assessment Context

From Task 010 (Code Quality Assessment), we identified these as P3 workflow improvements that would benefit the team.

## Requirements

### 1. Improve Pre-commit Hook Workflow (~45 minutes)

**Problem**: Developer writes commit message → hooks auto-fix files → commit aborted → developer writes message again

**Current Behavior**:
```bash
$ git commit -m "fix: update portfolio logic"
Trim trailing whitespace.................................................Failed
- hook id: trailing-whitespace
- exit code: 1
- files were modified by this hook

$ # Now have to commit again with same message
$ git commit -m "fix: update portfolio logic"
[main abc123] fix: update portfolio logic
```

**Goal**: Make auto-fixes seamless, don't require double commit

**Options to Evaluate**:

1. **Move formatters to `pre-push` stage** (Recommended)
   ```yaml
   - id: trailing-whitespace
     stages: [push]  # Run on push instead of commit
   ```
   - Pros: Commits work immediately, fixes happen before push
   - Cons: Pushes slower, may push unfixed code then fix it

2. **Use `--no-verify` flag with documentation**
   - Pros: Simple, developers have control
   - Cons: Easy to forget, inconsistent formatting

3. **Create git alias for commit-after-fix**
   ```bash
   git config alias.cf '!f() { git commit -m "$1" || git commit -m "$1"; }; f'
   # Usage: git cf "my commit message"
   ```
   - Pros: One command handles both attempts
   - Cons: Requires setup, not obvious to new developers

**Task**: Research best practices and implement the most developer-friendly solution

**Deliverables**:
- [ ] Updated `.pre-commit-config.yaml` with improved workflow
- [ ] Documentation in README or CONTRIBUTING.md explaining the approach
- [ ] Test the workflow (make a commit with trailing whitespace and verify)

### 2. Create Copilot Agent Environment Setup (~1 hour)

**Problem**: When Copilot agents start work, they have:
- No pre-commit hooks installed
- No backend dependencies synced (uv not run)
- No frontend dependencies installed (npm not run)
- No Docker services running

**Goal**: Provide a setup script that agents (and humans) can run to get a fully-configured environment

**Approach 1: Single Setup Script** (Recommended)

Create `.github/copilot-setup.sh`:
```bash
#!/bin/bash
set -e

echo "🚀 Setting up Zebu development environment..."

# 1. Install pre-commit hooks
echo "📋 Installing pre-commit hooks..."
pre-commit install

# 2. Backend setup
echo "🐍 Setting up backend (Python + uv)..."
cd backend
uv sync --all-extras
cd ..

# 3. Frontend setup
echo "⚛️ Setting up frontend (Node + npm)..."
cd frontend
npm ci
cd ..

# 4. Docker services
echo "🐳 Starting Docker services (PostgreSQL + Redis)..."
docker-compose up -d

echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "  - Backend: cd backend && uv run uvicorn zebu.main:app --reload"
echo "  - Frontend: cd frontend && npm run dev"
echo "  - Tests: cd backend && uv run pytest"
```

**Approach 2: Use Taskfile** (Alternative)

Add to `Taskfile.yml`:
```yaml
setup:
  desc: "Complete development environment setup"
  cmds:
    - task: precommit:install
    - task: backend:sync
    - task: frontend:install
    - task: docker:up
```

**Recommendation**: Use Approach 2 (Taskfile) if `task setup` already exists, otherwise create Approach 1 script

**Deliverables**:
- [ ] Setup script (`.github/copilot-setup.sh` or Taskfile task)
- [ ] Make script executable: `chmod +x .github/copilot-setup.sh`
- [ ] Test the script in a fresh clone
- [ ] Update AGENT_ORCHESTRATION.md with setup instructions
- [ ] Update README.md with setup command

### 3. Agent Environment Documentation (~30 minutes)

**Goal**: Document how Copilot agents should set up their environment

**Create/Update Files**:

1. **Update AGENT_ORCHESTRATION.md**:
   ```markdown
   ## Agent Environment Setup

   Before starting work, run the setup script:
   ```bash
   ./.github/copilot-setup.sh
   # OR
   task setup
   ```

   This will:
   - Install pre-commit hooks
   - Sync backend dependencies (uv)
   - Install frontend dependencies (npm)
   - Start Docker services (PostgreSQL, Redis)

   ## Pre-commit Hooks

   Pre-commit hooks run automatically on push (not commit) to format code.
   If you need to skip them: `git push --no-verify`
   ```

2. **Update README.md** (Quick Start section):
   ```markdown
   ## Quick Start

   ### First Time Setup
   ```bash
   # Run setup script (installs dependencies, starts services)
   ./.github/copilot-setup.sh
   # OR
   task setup
   ```

   ### Daily Development
   ```bash
   # Start backend
   cd backend && uv run uvicorn zebu.main:app --reload

   # Start frontend (new terminal)
   cd frontend && npm run dev
   ```
   ```

**Deliverables**:
- [ ] Updated AGENT_ORCHESTRATION.md with setup instructions
- [ ] Updated README.md with setup command
- [ ] Clear, concise instructions that work for both humans and agents

### 4. Additional Code Quality Fixes (~30 minutes)

While we're improving workflows, also address these minor issues from BACKLOG:

**4.1 Fix Remaining Ruff Warnings** (~10 minutes)
- 3 warnings remaining:
  - `B904`: Exception chaining in `dependencies.py`
  - `B007`: Unused loop variable in test
  - `E501`: Line too long in test docstring
- Files: `adapters/inbound/api/dependencies.py`, test files
- Command: `cd backend && uv run ruff check --fix`

**4.2 Fix API Test Failure** (~15 minutes)
- Test expects `/api/v1/` but we have `/`
- Either update test or add `/api/v1/` root endpoint
- File: `backend/tests/integration/test_api.py`
- Recommendation: Update test to match actual API (root at `/`)

**Deliverables**:
- [ ] All ruff warnings resolved
- [ ] API test passing
- [ ] Run full test suite to verify no regressions

## Files to Create/Modify

### New Files
- `.github/copilot-setup.sh` - Agent environment setup script

### Modified Files
- `.pre-commit-config.yaml` - Improved hook configuration
- `AGENT_ORCHESTRATION.md` - Add setup instructions
- `README.md` - Add quick start setup command
- `backend/src/zebu/adapters/inbound/api/dependencies.py` - Fix exception chaining
- `backend/tests/integration/test_api.py` - Fix test expectation
- Possibly: `Taskfile.yml` - Add setup task if using Taskfile approach

## Testing Requirements

### Pre-commit Workflow Testing
1. Make a file with trailing whitespace
2. Commit it with a message
3. Verify workflow is smooth (no double commit required)
4. Verify formatting is applied

### Setup Script Testing
1. Clone repo to new directory (or use Docker container)
2. Run setup script
3. Verify:
   - Pre-commit hooks installed: `pre-commit run --all-files`
   - Backend dependencies synced: `cd backend && uv run python -c "import zebu"`
   - Frontend dependencies installed: `cd frontend && npm list`
   - Docker services running: `docker-compose ps`
4. Run tests: `cd backend && uv run pytest` (should pass)

### Code Quality Testing
1. Run `uv run ruff check` - should show 0 warnings
2. Run `uv run pytest` - all tests should pass
3. Run `npm test` - all tests should pass

## Success Criteria

- [ ] Pre-commit hooks work smoothly (no double commit required)
- [ ] Setup script works in fresh clone
- [ ] Documentation is clear and complete
- [ ] All ruff warnings resolved (0 remaining)
- [ ] All tests passing (218 total: 195 backend + 23 frontend)
- [ ] AGENT_ORCHESTRATION.md updated with setup instructions
- [ ] README.md updated with quick start command

## Constraints

1. **Backward Compatible**: Existing developer workflows should still work
2. **Cross-Platform**: Setup script should work on macOS and Linux
3. **No Breaking Changes**: Don't change behavior of pre-commit hooks in ways that break existing commits
4. **Fast**: Setup script should complete in <3 minutes

## Notes

### Pre-commit Hook Research

Check these resources for best practices:
- https://pre-commit.com/#usage
- https://pre-commit.com/#confining-hooks-to-run-at-certain-stages
- https://ljvmiranda921.github.io/notebook/2018/06/21/precommits-using-black-and-flake8/

### Taskfile Reference

Current tasks in `Taskfile.yml`:
- `task precommit:install`
- `task docker:up`
- (Check file for other available tasks)

### Alternative: GitHub Codespaces

For future consideration: Create `.devcontainer/devcontainer.json` for GitHub Codespaces with pre-configured environment. This would give agents (and developers) a fully-configured container.

## Related Issues

From BACKLOG.md:
- Development Workflow Improvements section
- Code Quality & Linting section (ruff warnings)

## Future Enhancements

After this task:
1. Consider adding `lefthook` or `husky` for faster pre-commit hooks
2. Add commit message linting (conventional commits)
3. Add automatic dependency updates (Renovate or Dependabot)
4. Consider GitHub Codespaces for zero-setup development

---

**This task improves the development experience for both humans and Copilot agents!** The goal is to make setup painless and pre-commit hooks helpful instead of frustrating.
