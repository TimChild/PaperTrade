# Agent Orchestration Workflow

This document describes the workflow for orchestrating AI agents to develop PaperTrade. The orchestrator (you, in VS Code Copilot Chat) coordinates background coding agents via the GitHub CLI.

## Quick Start for New Sessions

### 1. Set Up Your Environment

**IMPORTANT**: Before starting any work, run the setup script to configure your environment:

```bash
# Option 1: Use the setup script (recommended for agents)
./.github/copilot-setup.sh

# Option 2: Use Taskfile (if you have Task installed)
task setup
```

This will:
- Install pre-commit hooks (run on push, not commit)
- Sync backend dependencies with uv
- Install frontend dependencies with npm
- Start Docker services (PostgreSQL, Redis)

**Why this matters**: Without proper setup, you'll have:
- Missing dependencies
- No pre-commit hooks
- No Docker services running
- Tests may fail unexpectedly

### 2. Get Up to Speed

Read these files to understand current project state:

```bash
# Project overview and architecture
cat README.md
cat project_strategy.md
cat project_plan.md

# Check what tasks exist and their status
ls -la agent_tasks/

# Check recent agent progress
ls -la agent_progress_docs/

# See what PRs are open/in progress
gh pr list
```

### 3. Check Running Agent Tasks

```bash
# List recent agent tasks
gh agent-task list

# View details of a specific task (by PR number)
gh agent-task view <PR_NUMBER>
```

### 4. Pull Latest Changes

```bash
git checkout main
git pull origin main
```

---

## Pre-commit Hooks

Pre-commit hooks are configured to run on **push** (not commit) to prevent the "double commit" problem where auto-formatters require you to commit twice.

### How It Works

```bash
# Commit works immediately (no auto-fixes)
git commit -m "feat: add new feature"

# Push triggers formatters and type checking
git push  # Runs ruff, ruff-format, pyright, etc.
```

If the pre-push hooks make changes, you'll need to:
1. Review the changes
2. Commit them: `git commit -am "style: apply auto-formatting"`
3. Push again: `git push`

### Skipping Hooks

If you need to skip hooks (not recommended):
```bash
git push --no-verify
```

### Running Hooks Manually

```bash
# Run all hooks on all files
pre-commit run --all-files

# Or use Taskfile
task precommit:run
```

---

## The Orchestration Workflow

### Overview

```
┌─────────────────────────────────────────────────────────────┐
│                   VS Code Copilot Chat                      │
│                    (The Orchestrator)                       │
│                                                             │
│  • Reads project context                                    │
│  • Creates task definitions in agent_tasks/                 │
│  • Starts background agents via `gh agent-task create`      │
│  • Reviews completed PRs                                    │
│  • Verifies locally with `task dev`, browser preview        │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ gh agent-task create
                              │ --custom-agent <agent>
                              │ -F <task-file>
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              GitHub Copilot Coding Agents                   │
│                  (Background Workers)                       │
│                                                             │
│  • architect        - Domain design, Clean Architecture     │
│  • backend-swe      - Python/FastAPI implementation         │
│  • frontend-swe     - React/TypeScript implementation       │
│  • quality-infra    - CI/CD, Docker, testing infra          │
│  • refactorer       - Code quality improvements             │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ Creates PRs with changes
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    GitHub Pull Requests                     │
│                                                             │
│  • Review agent's work                                      │
│  • Request changes if needed                                │
│  • Merge when ready                                         │
└─────────────────────────────────────────────────────────────┘
```

### Step-by-Step Process

#### 1. Identify Next Tasks

Review `project_plan.md` to see what needs to be done next. Consider:
- What phase are we in?
- What tasks are blocked vs. can run in parallel?
- Which agent is best suited for each task?

#### 2. Create Task Definition

Create a detailed task file in `agent_tasks/`:

```bash
# Naming convention: NNN_short-description.md
agent_tasks/006_implement-portfolio-api.md
```

Task files should include:
- **Objective**: Clear goal
- **Context**: Why this task, what phase
- **Requirements**: Detailed specs, code examples
- **File Structure**: Expected output structure
- **Testing Requirements**: What tests to write
- **Success Criteria**: Checkboxes for completion
- **References**: Links to relevant agent docs

#### 3. Commit Task to Main

```bash
git add agent_tasks/NNN_task-name.md
git commit -m "chore: add task NNN for <description>"
git push origin main
```

#### 4. Start the Agent

```bash
gh agent-task create \
  --custom-agent <agent-name> \
  -F agent_tasks/NNN_task-name.md
```

Available agents (defined in `.github/agents/`):
| Agent | Use For |
|-------|---------|
| `architect` | Domain design, interfaces, architectural decisions |
| `backend-swe` | Python/FastAPI implementation, backend tests |
| `frontend-swe` | React/TypeScript UI, frontend tests |
| `quality-infra` | CI/CD, Docker, Taskfile, pre-commit |
| `refactorer` | Code cleanup, smell removal, structure improvements |

#### 5. Monitor Progress

```bash
# List your agent tasks
gh agent-task list

# View specific task logs
gh agent-task view <session-id-or-pr-number>

# Or check the PR directly
gh pr view <PR_NUMBER> --web
```

#### 6. Review and Merge

Once the agent completes:
1. Review the PR on GitHub
2. Pull the branch locally to test if needed:
   ```bash
   gh pr checkout <PR_NUMBER>
   task dev  # Start services
   # Test in browser
   ```
3. Merge when satisfied

#### 7. Repeat

Continue with the next task!

---

## Running Multiple Agents in Parallel

Agents can work simultaneously on independent tasks. This is a **powerful technique** that significantly speeds up development.

### Successful Parallel Patterns

**Pattern 1: Quick Fixes + Major Work** ✅ (Proven Dec 28, 2025)
```bash
# Start cleanup/refinements (1 hour)
gh agent-task create --custom-agent backend-swe -F agent_tasks/008_domain-layer-refinements.md

# Start major feature work (7-9 hours)
gh agent-task create --custom-agent backend-swe -F agent_tasks/007b_implement-application-layer.md
```
**Result**: Quick fixes merge first, major work continues unaffected. Both agents work independently.

**Pattern 2: Frontend + Backend (Independent Layers)**
```bash
# Backend domain layer (pure logic, no UI dependencies)
gh agent-task create --custom-agent backend-swe -F agent_tasks/007_implement-domain-layer.md

# Frontend with mock data (no backend dependencies yet)
gh agent-task create --custom-agent frontend-swe -F agent_tasks/005_portfolio-dashboard-ui.md
```
**Result**: Both work with mocked boundaries, integrate later.

**Pattern 3: Architecture + Infrastructure**
```bash
# Architect designs the domain model
gh agent-task create --custom-agent architect -F agent_tasks/004_domain-architecture-design.md

# Quality/infra improves CI pipeline
gh agent-task create --custom-agent quality-infra -F agent_tasks/003_setup-cicd.md
```
**Result**: Different concerns, no conflicts.

### Rules for Safe Parallelization

✅ **DO run in parallel when:**
- Tasks modify different layers (domain vs adapters vs infrastructure)
- One task is quick cleanup/docs, other is major feature work
- Tasks work on completely separate features/modules
- Tasks are in different tech stacks (backend Python vs frontend TypeScript)
- Tasks have mocked boundaries (frontend mocks API, backend mocks DB)

❌ **DON'T run in parallel when:**
- One task depends on another's output (adapters need application layer ports)
- Both modify the same files or modules
- Sequential work is inherently required by architecture
- Both modify shared configuration (though usually handled by git merge)

### Managing Parallel Work

**Before Starting**:
1. Merge any completed PRs to main first
2. Commit task files to main
3. Start agents in quick succession

**During Execution**:
```bash
# Monitor all active tasks
gh agent-task list --limit 5

# Check specific task progress
gh pr view <PR_NUMBER> --web
```

**After Completion**:
1. Merge quick tasks first (less merge conflict risk)
2. Pull main before merging longer tasks
3. Resolve any conflicts in longer task's PR if needed

### Real Example (December 28, 2025)

Started in parallel:
- **PR #13**: Domain refinements (linting, docs) - ~1 hour
- **PR #14**: Application layer (commands, queries) - 7-9 hours

**Result**: PR #13 merged quickly, PR #14 continues independently. Zero conflicts because they modified different parts of the codebase.

**Throughput gain**: Instead of 10 total hours sequential, we get 9 hours wall time (10% improvement). More importantly, we get immediate value from quick fixes while major work proceeds.

---

## MCP Tools (Model Context Protocol)

The workspace has MCP servers configured in `.vscode/mcp.json` that provide enhanced capabilities for the orchestrator.

### Available MCP Servers

| Server | Purpose | Status |
|--------|---------|--------|
| **Pylance** | Python code analysis, execution, refactoring | ✅ Active |
| **Container** | Docker container management | ✅ Active |
| **Playwright** | Browser automation | Configured |
| **GitHub** | GitHub API integration | Configured (needs PAT) |
| **PostgreSQL** | Direct database access | Configured |
| **Filesystem** | Enhanced file operations | Configured |
| **Memory** | Persistent memory | Configured |
| **Sequential Thinking** | Complex reasoning | Configured |

### Key MCP Tools for Orchestrators

**Python Development** (Pylance MCP):
```bash
# Run Python code without shell escaping issues
pylanceRunCodeSnippet(workspaceRoot, codeSnippet)

# Check for missing imports
pylanceImports(workspaceRoot)

# Validate Python file syntax
pylanceFileSyntaxErrors(workspaceRoot, fileUri)

# List all Python files in project
pylanceWorkspaceUserFiles(workspaceRoot)
```

**Container Management** (Container MCP):
```bash
# Check container status
list_containers()

# View logs
logs_for_container(containerNameOrId)

# Get detailed info
inspect_container(containerNameOrId)

# Start/stop containers
act_container(containerNameOrId, action)  # action: start, stop, restart, remove
```

### When to Use MCP vs Terminal

| Task | Use MCP | Use Terminal |
|------|---------|--------------|
| Run Python snippet | ✅ `pylanceRunCodeSnippet` | ❌ Shell escaping issues |
| Check container health | ✅ `inspect_container` | ❌ Parse docker output |
| Run tests | ❌ | ✅ `task test:backend` |
| Git operations | ❌ | ✅ `gh pr list`, `git commit` |
| Install dependencies | ❌ | ✅ `uv add`, `npm install` |

### Current Container Status

Quick health check for PaperTrade:
- `papertrade-postgres` - PostgreSQL database (port 5432)
- `papertrade-redis` - Redis cache (port 6379)

Use `list_containers()` MCP tool or `task docker:status` to verify.

---

## Local Development & Verification

### Start Development Environment

```bash
task docker:up     # Start PostgreSQL, Redis
task dev:backend   # Start FastAPI (port 8000)
task dev:frontend  # Start Vite (port 5173)

# Or all at once:
task dev
```

### Verify in Browser

The orchestrator can preview URLs:
- Frontend: http://localhost:5173
- Backend API docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health

### Run Tests

```bash
task test           # All tests
task test:backend   # Backend only
task test:frontend  # Frontend only
task lint           # All linters
```

---

## Key Files Reference

| File | Purpose |
|------|---------|
| `project_plan.md` | Development phases and task checklists |
| `project_strategy.md` | Architecture decisions and tech stack |
| `agent_tasks/*.md` | Task definitions for agents |
| `agent_progress_docs/*.md` | Agent work documentation |
| `.github/agents/*.md` | Agent instruction files |
| `.github/copilot-instructions.md` | General instructions for all agents |
| `Taskfile.yml` | Available commands (`task --list`) |

---

## Best Practices (Lessons Learned)

### Task Creation

**✅ DO**:
- Create detailed task files with clear success criteria
- Include code examples and file structures
- Reference architecture plans explicitly
- Commit tasks to main before starting agents
- Number tasks sequentially (001, 002, 003...)

**❌ DON'T**:
- Give vague instructions ("make it better")
- Assume agent knows implicit context
- Start agents without committed task files
- Skip documentation of expected outputs

### Agent Review

**✅ DO**:
- Review PRs critically - agents aren't perfect
- Test locally when possible (pull branch, run tests)
- Check adherence to architecture plans
- Verify no forbidden dependencies (domain layer purity)
- Score agent work objectively (0-10 scale)

**❌ DON'T**:
- Merge without review
- Assume tests passing = good design
- Skip checking for architectural violations
- Ignore code quality metrics

### Workflow Efficiency

**✅ DO**:
- Run independent tasks in parallel
- Merge quick wins immediately
- Create BACKLOG.md for minor improvements
- Prepare next task while agents work
- Use PROGRESS.md to track completed work

**❌ DON'T**:
- Wait for one agent when you could start another
- Let minor issues block major work
- Forget to document agent decisions
- Skip updating project status

### Communication with Agents

**✅ DO**:
- Be specific about requirements
- Provide architecture documents
- Set clear success criteria
- Reference existing patterns to follow
- Give agents examples of good code

**❌ DON'T**:
- Assume agents remember previous context
- Use ambiguous language
- Change requirements mid-task
- Expect agents to "figure it out"

### Quality Gates

**Before Merging**:
- [ ] All tests pass
- [ ] Type checking passes (pyright/tsc)
- [ ] Linting passes (ruff/eslint)
- [ ] Code follows architecture plan
- [ ] No forbidden dependencies
- [ ] Progress documented

**Exception**: Minor linting warnings (E501 line-too-long) can be fixed in follow-up if non-blocking.

### Critical Review Process

When reviewing agent work:

1. **Check Alignment**: Does it match the architecture plan?
2. **Test Quality**: Are tests comprehensive? Do they test behavior, not implementation?
3. **Code Quality**: Is it readable, maintainable, idiomatic?
4. **Dependencies**: Are layers properly isolated?
5. **Documentation**: Is the agent's work self-documenting?

**Scoring Guide**:
- 10/10: Perfect, production-ready
- 9/10: Excellent, minor cosmetic issues
- 7-8/10: Good, needs improvements before merge
- 5-6/10: Acceptable, significant refactoring needed
- <5/10: Needs major rework

### Real Example: Domain Layer Review (Dec 28, 2025)

**Task**: Implement domain layer (task 007)
**Agent**: backend-swe
**PR**: #12

**Review Process**:
1. ✅ Ran tests: 158/158 passing
2. ✅ Checked dependencies: `grep` for forbidden imports
3. ✅ Verified architecture: Compared to domain-layer.md spec
4. ✅ Reviewed code quality: Immutability, validation, error handling
5. ⚠️ Found minor issues: 15 E501 linting warnings, Holding equality semantics

**Score**: 9/10 - Excellent foundation

**Action**: Merged PR, created task 008 for minor fixes to run in parallel with next major work.

---

## Debugging CI Failures

When CI fails on a PR, you can reproduce the failure locally using the Taskfile commands that CI uses.

### Quick Reproduction

```bash
# Run ALL CI checks locally (same as GitHub Actions)
task ci

# Or run specific checks
task lint:backend
task test:frontend
task build
```

### Step-by-Step Debugging

1. **Pull the PR branch:**
   ```bash
   gh pr checkout <PR_NUMBER>
   ```

2. **Run the failing job:**
   Look at the CI logs to see which task failed, then run it locally:
   ```bash
   # Example: backend linting failed
   task lint:backend
   
   # Example: frontend tests failed
   task test:frontend
   ```

3. **Fix the issue:**
   Make your changes to fix the failing tests or linting errors.

4. **Verify the fix:**
   ```bash
   # Run just the task that was failing
   task lint:backend
   
   # Or run all CI checks to be sure
   task ci
   ```

5. **Commit and push:**
   ```bash
   git add .
   git commit -m "fix: resolve CI failure"
   git push
   ```

### CI Job to Task Mapping

Our CI workflow uses Taskfile commands, so local and CI environments are identical:

| CI Job | Runs These Tasks | Local Command |
|--------|------------------|---------------|
| `backend-checks` | `task lint:backend && task test:backend` | Same |
| `frontend-checks` | `task lint:frontend && task test:frontend && task build:frontend` | Same |
| `e2e-tests` | `task docker:up && task test:e2e` | Same |

### Quick CI Checks

Before pushing, run a quick lint check:

```bash
# Fast checks (lint only, skip tests)
task ci:fast

# Full CI suite (takes longer)
task ci
```

### Common CI Failures

**Linting errors:**
```bash
# Auto-fix most linting issues
task format

# Then verify
task lint
```

**Test failures:**
```bash
# Run tests with verbose output
cd backend && uv run pytest -vv

# Or for frontend
cd frontend && npm run test
```

**Build failures:**
```bash
# Check backend imports
task build:backend

# Check frontend build
task build:frontend
```

---

## Troubleshooting

### Agent Task Fails to Start

```bash
# Check if agent exists
ls .github/agents/

# Verify task file is committed
git log --oneline agent_tasks/NNN_task-name.md

# Check gh CLI is authenticated
gh auth status
```

### PR Has Conflicts

```bash
# Pull latest main
git checkout main
git pull origin main

# Rebase PR branch
git checkout <branch-name>
git rebase main

# If agent created the PR, may need to force push (be careful)
git push --force-with-lease
```

### Agent Output Doesn't Match Expectations

1. Review the task file - was it clear enough?
2. Check if agent followed instructions
3. Provide feedback in PR comments
4. Consider updating agent instructions in `.github/agents/`
5. If repeatedly problematic, refine task templates

### GitHub CLI Commands Hang (Interactive Pager)

**Problem**: Commands like `gh pr list`, `gh agent-task list` appear to produce no output and hang indefinitely.

**Cause**: The GitHub CLI uses an interactive pager (like `less`) by default, waiting for user input (press 'q' to quit).

**Solution**: Disable the pager by setting `GH_PAGER=""` environment variable:

```bash
# Single command
GH_PAGER="" gh pr list --state open --limit 5

# Multiple commands in a script
export GH_PAGER=""
gh pr list
gh agent-task list
gh pr view 15
```

**Best Practice for Agents/Automation**:
Always use `GH_PAGER=""` when running `gh` commands in scripts or automated workflows:

```bash
# ✅ CORRECT - Non-interactive
GH_PAGER="" gh pr list --json number,title,state

# ✅ CORRECT - With formatting
GH_PAGER="" gh agent-task list --limit 3

# ❌ WRONG - Will hang waiting for 'q' keypress
gh pr list  # Hangs in automation!
```

**Alternative**: Use `| cat` to force non-interactive mode:
```bash
gh pr list | cat
```

### Terminal Hangs on Long Commands

**Problem**: `gh agent-task create` with long arguments causes terminal to freeze.

**Solution**: Use temp files for long task descriptions:

```bash
# For very long task descriptions
cat > /tmp/task_description.txt << 'EOF'
[Long task description here...]
EOF

gh agent-task create --custom-agent backend-swe -F /tmp/task_description.txt
```

Or use the file-based approach (recommended):
```bash
# Always use -F with task files
gh agent-task create --custom-agent backend-swe -F agent_tasks/007_task-name.md
```

---

## Quick Reference Commands

### Long Command Workaround

**⚠️ CRITICAL**: The terminal hangs when executing very long commands directly.

**Solution**: Write long commands to a temporary file and use that file:

```bash
# DON'T do this (will hang):
# gh agent-task create --custom-agent architect -F <very-long-file-path-or-content>

# DO this instead:
cat > /tmp/task_cmd.txt << 'EOF'
gh agent-task create \
  --custom-agent architect \
  -F agent_tasks/very_long_filename.md
EOF

bash /tmp/task_cmd.txt
rm /tmp/task_cmd.txt
```

Or for heredoc content:
```bash
# Write content to temp file
cat > /tmp/temp_task.md << 'EOF'
[long task content here]
EOF

# Use the temp file
gh agent-task create --custom-agent architect -F /tmp/temp_task.md
rm /tmp/temp_task.md
```

**When to use this workaround:**
- Commands longer than ~200 characters
- Commands with heredocs or multi-line strings
- Any command that seems to "hang" without output

---

## Troubleshooting

### Agent task fails to start

```bash
# Check agent file exists and has frontmatter
cat .github/agents/<agent-name>.md | head -10

# Should have:
# ---
# name: Agent Name
# description: ...
# ---
```

### Agent creates PR but work is incomplete

1. Comment on the PR with additional instructions
2. Or close PR and create new task with more detail

### Merge conflicts between agent PRs

1. Merge one PR first
2. The other PR will need to be rebased or recreated

### Need to test agent's changes locally

```bash
gh pr checkout <PR_NUMBER>
task dev
# Test...
git checkout main
```

---

## Example Session

```bash
# 1. Start new session - get context
cat project_plan.md
gh pr list
gh agent-task list

# 2. See we need to implement API routes (Task 006)
# Create the task file...

# 3. Commit and push
git add agent_tasks/006_implement-api.md
git commit -m "chore: add task 006 for API implementation"
git push origin main

# 4. Start the agent
gh agent-task create --custom-agent backend-swe \
  -F agent_tasks/006_implement-api.md

# 5. While that runs, check if there's parallel work
# Maybe start a refactoring task...

# 6. Monitor
gh agent-task list
gh pr list

# 7. Review and merge completed PRs
gh pr view 9 --web
# ... review ...
gh pr merge 9
git pull origin main

# 8. Continue with next tasks!
```
