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

## Agent Progress Documentation (REQUIRED)

**All agents MUST generate progress documentation for significant tasks.**

### Location
All progress documentation goes in the `agent_progress_docs/` directory at the repository root.

### Naming Convention
```
YYYY-MM-DD_HH-MM-SS_short-description.md
```
or for complex tasks requiring multiple files:
```
YYYY-MM-DD_HH-MM-SS_short-description/
├── summary.md
├── planning.md
├── implementation-notes.md
└── ...
```

### Getting the Timestamp
**ALWAYS** determine the datetime by running a terminal command:
```bash
date "+%Y-%m-%d_%H-%M-%S"
```
Do NOT rely on internal knowledge of the current time.

### Content Requirements
Progress documents should include:
1. **Task Summary**: What was requested/accomplished
2. **Decisions Made**: Key architectural or implementation decisions
3. **Files Changed**: List of files created, modified, or deleted
4. **Testing Notes**: What was tested and how
5. **Known Issues/TODOs**: Any remaining work or concerns
6. **Next Steps**: Suggested follow-up actions if applicable

### When to Create Progress Docs
- Any task that creates or significantly modifies multiple files
- Architectural decisions or pattern implementations
- Bug fixes that reveal systemic issues
- Infrastructure or CI/CD changes
- Any work that a future developer would benefit from understanding

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

This workspace has MCP servers configured in `.vscode/mcp.json` that provide enhanced capabilities.

### Pylance MCP - Python Intelligence

**PREFER these tools over terminal commands for Python work:**

| Tool | Use For | Instead Of |
|------|---------|------------|
| `pylanceRunCodeSnippet` | Run Python code | `python -c "..."` (avoids shell escaping) |
| `pylanceImports` | Find missing dependencies | Manual grep for imports |
| `pylanceFileSyntaxErrors` | Validate Python files | Running and checking errors |
| `pylanceInvokeRefactoring` | Auto-fix code issues | Manual refactoring |

**Example - Run Python code safely:**
```
mcp_pylance_mcp_s_pylanceRunCodeSnippet:
  workspaceRoot: "file:///Users/timchild/github/PaperTrade"
  codeSnippet: "from papertrade.domain.entities import Portfolio; print('Import works!')"
```

### Container MCP - Docker Management

**PREFER these tools for container operations:**

| Tool | Use For | Instead Of |
|------|---------|------------|
| `list_containers` | See all containers | `docker ps -a` |
| `logs_for_container` | View container logs | `docker logs <name>` |
| `inspect_container` | Get container details | `docker inspect <name>` |
| `act_container` | Start/stop/restart | `docker start/stop <name>` |

**Example - Check if database is healthy:**
```
mcp_copilot_conta_inspect_container:
  containerNameOrId: "papertrade-postgres"
```

### When to Use MCP vs Terminal

| Scenario | Use MCP | Use Terminal |
|----------|---------|--------------|
| Run Python snippet | ✅ `pylanceRunCodeSnippet` | ❌ Escaping issues |
| Check container status | ✅ `list_containers` | ❌ Parsing text output |
| Run pytest | ❌ | ✅ `task test:backend` |
| Install packages | ❌ | ✅ `uv add <package>` |
| Complex shell pipelines | ❌ | ✅ Terminal |

### MCP Quick Reference

```
# Python analysis
mcp_pylance_mcp_s_pylanceWorkspaceUserFiles  # List all Python files
mcp_pylance_mcp_s_pylanceImports             # Find unresolved imports
mcp_pylance_mcp_s_pylancePythonEnvironments  # Check Python environment

# Container management
mcp_copilot_conta_list_containers            # List all containers
mcp_copilot_conta_list_images                # List images
mcp_copilot_conta_logs_for_container         # Get container logs
```
