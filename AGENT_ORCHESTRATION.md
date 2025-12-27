# Agent Orchestration Workflow

This document describes the workflow for orchestrating AI agents to develop PaperTrade. The orchestrator (you, in VS Code Copilot Chat) coordinates background coding agents via the GitHub CLI.

## Quick Start for New Sessions

### 1. Get Up to Speed

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

### 2. Check Running Agent Tasks

```bash
# List recent agent tasks
gh agent-task list

# View details of a specific task (by PR number)
gh agent-task view <PR_NUMBER>
```

### 3. Pull Latest Changes

```bash
git checkout main
git pull origin main
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

Agents can work simultaneously on independent tasks:

```bash
# Example: Start domain work and UI work in parallel
gh agent-task create --custom-agent architect -F agent_tasks/004_domain-entities.md
gh agent-task create --custom-agent frontend-swe -F agent_tasks/005_portfolio-ui.md
```

**Rules for parallelization:**
- ✅ Tasks that don't modify the same files
- ✅ Frontend (mock data) + Backend (domain layer)
- ✅ Different features in different directories
- ❌ Tasks where one depends on another's output
- ❌ Both modifying the same configuration files

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
