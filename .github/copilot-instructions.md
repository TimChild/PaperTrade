# Copilot Instructions for PaperTrade

## Overview

PaperTrade is a stock market emulation platform where users can practice trading strategies without risking real money. We follow **Modern Software Engineering** principles (Dave Farley) with a focus on Clean Architecture, testability, and iterative development.

## Core Principles

> 📖 **See**: [agent_tasks/reusable/architecture-principles.md](../agent_tasks/reusable/architecture-principles.md)

The reusable chunk covers:
- Modern Software Engineering mindset (iterative, empirical, managing complexity)
- Clean Architecture principles (dependency rule, pure domain, composition over inheritance)
- Testing philosophy (behavior over implementation, sociable tests, persistence ignorance)

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

> 📖 **See**: [agent_tasks/reusable/agent-progress-docs.md](../agent_tasks/reusable/agent-progress-docs.md)

**For PR-based coding agents only** (not for orchestration sessions).

The reusable chunk covers:
- When documentation is required vs. optional
- File naming format and timestamp generation
- Content template with all required sections
- Best practices for writing progress docs


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

> 📖 **See**: [agent_tasks/reusable/git-workflow.md](../agent_tasks/reusable/git-workflow.md)

**All agents MUST use git and the GitHub CLI (`gh`) appropriately.**

The reusable chunk covers:
- Branch management (checking status, creating feature branches)
- Committing changes (conventional commit format)
- Pull request creation via GitHub CLI
- GitHub CLI best practices (using `GH_PAGER=""` to prevent hangs)
- Keeping branches up to date

### Environment Setup for Copilot Agents

If you need to set up or verify your development environment, you can use:

- **Shell script** (recommended for local setup): `./.github/copilot-setup.sh`
- **Task command**: `task setup` (uses Taskfile)
- **GitHub Actions workflow**: `.github/workflows/copilot-setup-steps.yml` (for Copilot agents)

The setup process installs:
- Python 3.12+ and uv (package manager)
- Node.js 20 and npm
- Task (task runner)
- pre-commit hooks
- Docker services (PostgreSQL, Redis)

### Required Repository Secrets

The following secrets should be configured in the repository for CI/CD and Copilot agents:

- **`ALPHA_VANTAGE_API_KEY`**: API key for market data integration (Phase 2+)
  - Get a free key at: https://www.alphavantage.co/support/#api-key
  - Free tier: 5 API calls/min, 500 calls/day
  - Required for: Market data tests, integration tests with real APIs
  - Configure at: Repository Settings → Secrets and variables → Actions → New repository secret

**Note**: For local development, copy `.env.example` to `.env` and add your own API key. For production deployments, use `.env.production.example` as a template and configure appropriate secrets management (AWS Secrets Manager, etc.).

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
