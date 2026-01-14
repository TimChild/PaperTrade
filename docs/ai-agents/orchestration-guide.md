# Agent Orchestration Workflow

Guide for orchestrating AI coding agents to develop PaperTrade (a stock market paper trading platform).

## Starting a New Session

1. **Read project context**: `.github/copilot-instructions.md` (includes MCP setup)
2. **Check current status**: `PROGRESS.md` (phases, recent work, next steps)
3. **Review open work**: `GH_PAGER="" gh pr list`

## Quick Start

```bash
# 1. Setup environment
task setup                           # Full development environment setup

# 2. Get current state
cat PROGRESS.md                      # Current status and next steps
cat docs/planning/project_plan.md    # Development phases
GH_PAGER="" gh pr list               # Open PRs

# 3. Pull latest
git checkout main && git pull origin main
```

## Creating Agent Tasks

### 1. Create Task File

```bash
# Naming: NNN_short-description.md
agent_tasks/029_implement-feature.md
```

Include: objective, context, requirements, file structure, success criteria, references.

### 2. Commit & Start Agent

```bash
git add agent_tasks/029_*.md
git commit -m "chore: add task 029"
git push origin main

gh agent-task create --custom-agent backend-swe -F agent_tasks/029_implement-feature.md
```

### Available Agents

| Agent | Use For |
|-------|---------|
| `architect` | Domain design, interfaces, architecture |
| `backend-swe` | Python/FastAPI implementation |
| `frontend-swe` | React/TypeScript UI |
| `quality-infra` | CI/CD, Docker, testing infrastructure |
| `refactorer` | Code cleanup, structure improvements |

### 3. Monitor & Review

```bash
GH_PAGER="" gh agent-task list          # Check status
GH_PAGER="" gh pr view <PR_NUMBER>      # Review PR
GH_PAGER="" gh pr checkout <PR_NUMBER>  # Test locally
gh pr merge <PR_NUMBER> --squash --delete-branch  # Merge
```

## Parallel Execution

Run independent tasks simultaneously:

```bash
# Quick fix + major work
gh agent-task create --custom-agent backend-swe -F agent_tasks/008_refinements.md
gh agent-task create --custom-agent backend-swe -F agent_tasks/007_major-feature.md
```

**Safe to parallelize**: Different layers, different tech stacks, quick fixes + major work.

**Don't parallelize**: Dependent tasks, same files/modules.

## MCP Tools

See [mcp-tools.md](mcp-tools.md) for full reference.

**Key tools**:
- `pylanceRunCodeSnippet` - Run Python without shell escaping
- `list_containers` / `inspect_container` - Docker management
- `pylanceImports` - Find missing dependencies

## Local Development

```bash
task docker:up      # Start PostgreSQL, Redis
task dev            # Start frontend + backend
task test           # Run all tests
task lint           # Run linters
```

**URLs**: Frontend http://localhost:5173 | Backend http://localhost:8000/docs

## Key Files

| File | Purpose |
|------|---------|
| `PROGRESS.md` | **Current status**, recent work, next steps |
| `.github/copilot-instructions.md` | Agent guidelines, MCP setup |
| `docs/planning/project_plan.md` | Development phases |
| `docs/planning/project_strategy.md` | Architecture decisions |
| `agent_tasks/*.md` | Task definitions |
| `.github/agents/*.md` | Role-specific agent instructions |
| `Taskfile.yml` | Commands (`task --list`) |
| `docs/ai-agents/mcp-tools.md` | MCP tools reference |
| `orchestrator_procedures/*.md` | Orchestrator testing and validation procedures |

## Best Practices

### Task Creation
- Detailed requirements with examples
- Clear success criteria
- Reference architecture plans
- Commit tasks before starting agents

### Reviewing Agent Work
- Check architecture compliance
- Verify test quality (behavior, not implementation)
- Look for forbidden dependencies
- Score 0-10 (merge at 9+)

**Requesting Changes from Agents**:
When you need the agent to fix issues in their PR, add comments starting with `@copilot`:

```bash
# Tag the agent in PR comments to request changes
GH_PAGER="" gh pr comment <PR_NUMBER> --body "@copilot Please fix the failing tests..."
```

This ensures the Copilot agent sees and responds to your feedback.

**GitHub CLI Best Practice**:
Always prefix gh commands with `GH_PAGER=""` to prevent interactive pager blocking:

```bash
# Good
GH_PAGER="" gh pr list
GH_PAGER="" gh pr view 47
GH_PAGER="" gh issue list

# Bad - may hang waiting for pager input
gh pr list
gh pr view 47
```

### Workflow
- Parallelize independent work
- Merge quick wins first
- Use `BACKLOG.md` for minor issues
- Update `PROGRESS.md` after phases complete

## Troubleshooting

### Long CLI Commands
Terminal hangs with long commands (e.g., PR bodies with multiple paragraphs). **Always use temp files with `-F` or `--body-file`**:

```bash
# 1. Use create_file tool to create temp file
# create_file: /path/to/repo/.tmp_pr_description.md

# 2. Create PR from temp file and clean up
GH_PAGER="" gh pr create \
  --title "fix: description" \
  --body-file .tmp_pr_description.md && rm .tmp_pr_description.md

# Same pattern for issues
GH_PAGER="" gh issue create \
  --title "title" \
  --body-file .tmp_issue_body.md && rm .tmp_issue_body.md

# For agent tasks
GH_PAGER="" gh agent-task create \
  --custom-agent backend-swe \
  -F agent_tasks/029_task.md
```

**Why**: Long command-line strings cause terminal parsing issues and quote escaping problems. Temp files avoid these issues entirely.

### GH CLI Hangs/Blocks
**Always use `GH_PAGER=""` prefix for gh commands** to prevent interactive pager from blocking:
```bash
GH_PAGER="" gh pr list
GH_PAGER="" gh pr view <PR_NUMBER>
GH_PAGER="" gh issue list
GH_PAGER="" gh agent-task list
```

### Agent Task Fails
```bash
ls .github/agents/       # Check agent exists
git log agent_tasks/     # Verify committed
gh auth status           # Check auth
```

### CI Failures
```bash
task ci                       # Reproduce locally
GH_PAGER="" gh pr checkout <PR>  # Test branch
task lint && task test        # Run specific checks
```

### Merge Conflicts
```bash
git checkout main && git pull
git checkout <branch> && git rebase main
git push --force-with-lease
```
