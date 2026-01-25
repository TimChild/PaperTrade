# Task 035: Development Environment & Tooling Audit

**Agent**: quality-infra
**Priority**: MEDIUM
**Created**: 2026-01-01
**Status**: Not Started

## Objective

Conduct a comprehensive audit of all development environment setup procedures, tooling, and automation to assess quality, identify gaps, and document improvements needed.

## Scope

Evaluate the following areas:

### 1. Environment Setup Procedures
- `.github/copilot-setup.sh` - Manual setup script
- `.github/workflows/copilot-setup.yml` - Automated workflow
- `README.md` - Developer onboarding documentation
- Verify both work correctly for new developers/agents

### 2. Pre-commit Hooks
- `.pre-commit-config.yaml` - Configuration completeness
- Hook execution reliability (lint, format, type check)
- Integration with CI/CD workflows
- Test pre-commit on staged changes

### 3. CI/CD Workflows
- `.github/workflows/ci.yml` - Main CI pipeline
- Task integration (lint, test, build commands)
- Cache effectiveness and performance
- Coverage reporting accuracy

### 4. Task Automation
- `Taskfile.yml` - Command completeness and correctness
- Cross-platform compatibility
- Error handling and user feedback
- Documentation quality

### 5. Testing Infrastructure
- Backend: pytest configuration, fixtures, coverage
- Frontend: Vitest configuration, test organization
- E2E: Playwright setup and reliability
- Test isolation and determinism

### 6. Development Tools
- Python: uv package management, virtual environments
- Node.js: npm scripts, dependency management
- Docker: docker-compose services, health checks
- Git: branch protection, commit conventions

### 7. Documentation Quality
- Setup instructions clarity
- Troubleshooting guides
- Architecture documentation
- Code comments and docstrings

## Deliverables

### 1. Comprehensive Audit Report
Create `docs/development-environment-audit-2026-01-01.md` with:

- **Executive Summary**: Overall health rating (1-10), critical issues
- **Detailed Findings**: Section-by-section analysis with examples
- **Issues Identified**: Categorized by severity (Critical/High/Medium/Low)
- **Recommendations**: Prioritized list of improvements
- **Testing Evidence**: Command outputs, screenshots, logs

### 2. Issue Tracking
For each HIGH or CRITICAL issue found:
- Create a GitHub issue with reproduction steps
- Add to BACKLOG.md with appropriate priority
- Tag with relevant labels (bug, documentation, enhancement)

### 3. Quick Wins Implementation
If simple fixes are identified (typos, broken links, missing documentation):
- Implement directly in this PR
- Document changes in progress doc

## Testing Methodology

### Fresh Environment Simulation
```bash
# 1. Test automated setup workflow
gh workflow run copilot-setup.yml

# 2. Test manual setup script
.github/copilot-setup.sh

# 3. Verify all dependencies installed
which task uv python node npm docker

# 4. Verify services start correctly
task docker:up
task dev:backend  # in separate terminal
task dev:frontend # in separate terminal
```

### Pre-commit Testing
```bash
# 1. Install pre-commit
pre-commit install

# 2. Test on all files
pre-commit run --all-files

# 3. Test on staged changes
git add <test-file>
pre-commit run

# 4. Verify hooks match CI checks
```

### CI/CD Validation
```bash
# 1. Create test branch
git checkout -b test/audit-validation

# 2. Make intentional lint error
# Add to backend/src/papertrade/main.py: x=1  # Missing spaces

# 3. Commit and push
git add -A && git commit -m "test: intentional lint error"
git push -u origin test/audit-validation

# 4. Create PR and verify CI catches error
gh pr create --fill

# 5. Fix error and verify CI passes
# Fix: x = 1
git add -A && git commit -m "fix: correct spacing"
git push

# 6. Close test PR
gh pr close --delete-branch
```

### Task Command Testing
```bash
# Test every task command in Taskfile.yml
task --list-all

# Backend tasks
task setup:backend
task lint:backend
task test:backend
task dev:backend  # (background)

# Frontend tasks
task setup:frontend
task lint:frontend
task test:frontend
task build:frontend
task dev:frontend  # (background)

# E2E tasks
task test:e2e

# Docker tasks
task docker:up
task docker:down
task docker:logs
```

### E2E Testing Framework
```bash
# Test orchestrator procedures
cd /Users/timchild/github/PaperTrade

# 1. Manual checklist
cat docs/ai-agents/procedures/manual_e2e_testing.md
# Execute each scenario manually

# 2. Automated script
./scripts/quick_e2e_test.sh

# 3. Playwright framework (if ready)
cd backend
uv run python ../scripts/e2e_validation.py
```

## Success Criteria

- ✅ All setup procedures work without errors
- ✅ Pre-commit hooks execute correctly and match CI
- ✅ All CI workflows pass on test PRs
- ✅ All task commands execute successfully
- ✅ E2E tests run reliably
- ✅ Documentation is accurate and complete
- ✅ Audit report delivered with actionable recommendations
- ✅ Critical issues have GitHub issues created

## Technical Approach

### 1. Automated Testing First
- Run all commands programmatically
- Capture output and exit codes
- Compare expected vs actual behavior

### 2. Manual Validation
- Follow documentation as a new developer would
- Note unclear instructions or missing steps
- Test error scenarios and edge cases

### 3. Code Review
- Review configuration files for best practices
- Check for hardcoded values or brittle logic
- Verify error handling and user feedback

### 4. Documentation Analysis
- Check for outdated information
- Verify examples are accurate
- Ensure troubleshooting guides are complete

## Notes

- This is a **comprehensive audit**, not a bug fix task
- Focus on **documenting findings** rather than fixing everything
- **Quick wins** (simple fixes) can be included in PR
- **Major improvements** should be separate tasks
- Generate **evidence** for all findings (logs, screenshots, command output)
- Be **objective** and **specific** in recommendations

## Related Issues

- Discovered during E2E testing (docs/ai-agents/procedures/)
- Follows successful merge of PR #40 (trade API fix)
- Follows successful merge of PR #41 (CI workflow fixes)

## Expected Output

A detailed audit report that gives the orchestrator agent and development team:
1. Clear understanding of current tooling quality
2. Prioritized list of improvements needed
3. Evidence-based recommendations
4. Confidence that critical workflows are reliable
