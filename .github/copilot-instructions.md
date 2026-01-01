# Copilot Instructions for PaperTrade

> ⚠️ **TEMPORARY**: This file is a placeholder and will be significantly improved by the `copilot-instructions-updater` agent once the project foundations are established.

## Overview

PaperTrade is a stock market emulation platform where users can practice trading strategies without risking real money. We follow **Modern Software Engineering** principles (Dave Farley) with a focus on Clean Architecture, testability, and iterative development.

## Core Principles

### 1. Modern Software Engineering Mindset
- **Iterative & Incremental**: Build the smallest valuable increment and evolve
- **Experimental & Empirical**: Make hypotheses, test them, use data to decide
- **Manage Complexity**: High cohesion, loose coupling, information hiding
- **Testability as Design**: If it's hard to test, the design is flawed

### 2. Clean Architecture
- **Dependency Rule**: Dependencies point inwards (Domain → Application → Adapters → Infrastructure)
- **Domain is Pure**: No I/O, no side effects in domain logic
- **Composition over Inheritance**: Favor object composition
- **Dependency Injection**: Manage external services via DI

### 3. Testing Philosophy
- **Behavior over Implementation**: Test what the system does, not how
- **Sociable Tests**: Exercise Use Cases and Domain together
- **No Mocking Internal Logic**: Only mock at architectural boundaries
- **Persistence Ignorance**: 90% of tests should run without a real database

## Technology Stack

### Backend (Python)
- Python 3.13+, FastAPI, SQLModel
- Ruff (linting/formatting), Pyright (strict typing)
- Pytest for testing

### Frontend (TypeScript)
- React + Vite, TypeScript
- TanStack Query, Zustand, Tailwind CSS
- ESLint, Prettier, Vitest

### Infrastructure
- PostgreSQL (prod), SQLite (dev)
- Redis for caching/pub-sub
- AWS CDK for infrastructure
- Docker Compose for local development
- GitHub Actions for CI/CD

## Agent Progress Documentation

**For PR-based coding agents only** (not for orchestration sessions).

### Purpose
When a coding agent creates a PR, it should document decisions and changes in `agent_progress_docs/`. This helps the orchestrator review work and provides context for future development.

### When Required
- Coding agents creating PRs (backend-swe, frontend-swe, etc.)
- Architectural decisions
- Complex bug fixes

### When NOT Required
- Orchestration sessions (direct conversations in VS Code)
- Simple questions or explorations
- Documentation-only changes

### Format
```
agent_progress_docs/YYYY-MM-DD_HH-MM-SS_short-description.md
```

Get timestamp: `date "+%Y-%m-%d_%H-%M-%S"`

### Content
1. Task Summary
2. Decisions Made
3. Files Changed
4. Testing Notes
5. Known Issues/Next Steps
6. (Optional) Next step suggestions -- Only if applicable


## Code Quality Standards

### Python
- Complete type hints on all functions (no `Any`)
- Docstrings for public APIs
- Maximum line length: 88 characters (ruff default)
- Follow PEP 8 conventions

### TypeScript
- Strict TypeScript configuration
- Explicit return types on functions
- Use interfaces for object shapes
- Prefer `const` over `let`

### Git Commits
- Use conventional commit format: `type(scope): description`
- Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `ci`
- Keep commits focused and atomic

## Pull Request Standards

- PRs should be focused on a single concern
- Include clear description of changes and motivation
- Reference related issues
- Ensure all CI checks pass
- Self-review before requesting review

## Git & GitHub CLI Workflow (REQUIRED)

**All agents MUST use git and the GitHub CLI (`gh`) appropriately.**

### Environment Setup for Copilot Agents

If you need to set up or verify your development environment, you can use:

- **Shell script** (recommended for local setup): `./.github/copilot-setup.sh`
- **Task command**: `task setup` (uses Taskfile)
- **GitHub Actions workflow**: `.github/workflows/copilot-setup.yml` (for automated/CI setup)

The setup process installs:
- Python 3.13 and uv (package manager)
- Node.js 20 and npm
- Task (task runner)
- pre-commit hooks
- Docker services (PostgreSQL, Redis)

### Branch Management
1. **Check current branch status** before starting work:
   ```bash
   git branch --show-current
   git status
   ```
2. **Create a feature branch** if on `main`:
   ```bash
   git checkout -b <type>/<short-description>
   ```
   Branch naming: `feat/add-portfolio-api`, `fix/trade-calculation`, `docs/update-readme`

### Committing Changes
1. **Stage changes** selectively:
   ```bash
   git add <specific-files>
   # or for all changes:
   git add -A
   ```
2. **Commit with conventional format**:
   ```bash
   git commit -m "type(scope): description"
   ```
3. **Push to remote**:
   ```bash
   git push -u origin <branch-name>
   ```

### Pull Request Creation
If not already on a branch with an open PR, use the GitHub CLI to create one:

```bash
# Check if PR already exists for current branch
gh pr view --web 2>/dev/null || gh pr create --fill
```

Or with more control:
```bash
gh pr create --title "feat(scope): description" --body "## Summary
- Change 1
- Change 2

## Related Issues
Closes #123"
```

### Keeping Up to Date
```bash
# Fetch latest changes
git fetch origin

# If on a feature branch, rebase on main when needed
git rebase origin/main
```

### Workflow Summary
1. Check/create feature branch
2. Make changes
3. Stage and commit (conventional commits)
4. Push to remote
5. Create PR via `gh pr create` if none exists
6. Update PR description if needed

## Available Agents

Refer to individual agent files in `.github/agents/` for specific role instructions:
- `architect.md` - Clean Architecture and design integrity
- `backend-swe.md` - Python backend implementation
- `frontend-swe.md` - TypeScript frontend implementation
- `quality-infra.md` - Testing, CI/CD, and infrastructure
- `refactorer.md` - Code quality and refactoring
- `copilot-instructions-updater.md` - Meta-agent for improving these instructions

## MCP Tools (Model Context Protocol)

Configuration: `.vscode/mcp.json` | Full reference: `docs/mcp-tools.md`

### Session Setup (Required)

Pylance may default to global Python. At session start:
```
pylancePythonEnvironments(workspaceRoot: "file:///Users/timchild/github/PaperTrade")
# If not using project venv, switch:
pylanceUpdatePythonEnvironment(workspaceRoot: ..., pythonEnvironment: "backend/.venv/bin/python")
```

### Key Tools

| Task | MCP Tool | Benefit |
|------|----------|---------|
| Run Python code | `pylanceRunCodeSnippet` | Avoids shell escaping |
| Check imports | `pylanceImports` | Find unresolved imports |
| Container health | `inspect_container` | Structured data |
| Container logs | `logs_for_container` | Clean output |
| PR details | `activePullRequest` | Full PR context |

### When to Use Terminal Instead

- Running tests: `task test:backend`
- Installing packages: `uv add`, `npm install`
- Git operations: `git`, `gh`
- Complex shell pipelines
