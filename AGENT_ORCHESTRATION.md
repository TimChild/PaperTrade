# Agent Orchestration Workflow

Guide for orchestrating AI coding agents to develop PaperTrade.

## Quick Start

```bash
# 1. Setup environment
task setup                    # or ./.github/copilot-setup.sh

# 2. Get current state
cat project_plan.md           # Development phases
GH_PAGER="" gh pr list        # Open PRs
GH_PAGER="" gh agent-task list # Running agents

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
gh pr checkout <PR_NUMBER>               # Test locally
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

See [docs/mcp-tools.md](docs/mcp-tools.md) for full reference.

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
| `project_plan.md` | Development phases |
| `project_strategy.md` | Architecture decisions |
| `agent_tasks/*.md` | Task definitions |
| `.github/agents/*.md` | Agent instructions |
| `Taskfile.yml` | Commands (`task --list`) |

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

### Workflow
- Parallelize independent work
- Merge quick wins first
- Use `BACKLOG.md` for minor issues
- Update `PROGRESS.md` after phases complete

## Troubleshooting

### Long CLI Commands
Terminal hangs with long commands (e.g., PR bodies). Use the `create_file` tool to write content to a temp file first, then reference it:

```bash
# After using create_file to write .tmp_body.md
gh pr create --title "title" --body-file .tmp_body.md
rm .tmp_body.md
```

### GH CLI Hangs
```bash
GH_PAGER="" gh pr list   # Disable pager
```

### Agent Task Fails
```bash
ls .github/agents/       # Check agent exists
git log agent_tasks/     # Verify committed
gh auth status           # Check auth
```

### CI Failures
```bash
task ci                  # Reproduce locally
gh pr checkout <PR>      # Test branch
task lint && task test   # Run specific checks
```

### Merge Conflicts
```bash
git checkout main && git pull
git checkout <branch> && git rebase main
git push --force-with-lease
```
