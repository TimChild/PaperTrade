# Copilot Instructions for Zebu

## Overview

Zebu is a stock market emulation platform where users can practice trading strategies without risking real money. We follow **Modern Software Engineering** principles (Dave Farley) with a focus on Clean Architecture, testability, and iterative development.

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

## Git & GitHub Workflows

> 📖 **See**: [agent_tasks/reusable/git-workflow.md](../agent_tasks/reusable/git-workflow.md)

**Environment-Specific Workflows:**

**GitHub Copilot Agents** (running in `copilot-setup-steps.yml` environment):
- Use GitHub MCP server for all GitHub interactions
- Git operations use standard git commands
- Check `COPILOT_AGENT_ENVIRONMENT=true` env var to detect this environment

**Local VSCode Agents:**
- Use git CLI for version control
- Use `gh` CLI for GitHub interactions (PRs, issues)
- **Always** prefix `gh` commands with `GH_PAGER=""` to prevent hangs
- See git-workflow.md for details on branch management, commits, PR creation

## Environment Setup

**Local development**: `task setup` installs all dependencies and starts Docker services.

**GitHub Copilot agents**: Environment is configured via `.github/workflows/copilot-setup-steps.yml` automatically.

## Repository Secrets & Variables

Configured secrets for CI/CD and Copilot agents:

| Secret/Variable | Type | Purpose |
|-----------------|------|----------|
| `ALPHA_VANTAGE_API_KEY` | Secret | Market data API (free tier: 5/min, 500/day) |
| `CLERK_SECRET_KEY` | Secret | Clerk authentication (backend) |
| `CLERK_PUBLISHABLE_KEY` | Secret | Clerk authentication (frontend) |
| `E2E_CLERK_USER_EMAIL` | Variable | E2E test user email |

## Available Agents

Refer to individual agent files in `.github/agents/` for specific role instructions:
- `architect.md` - Clean Architecture and design integrity
- `backend-swe.md` - Python backend implementation
- `frontend-swe.md` - TypeScript frontend implementation
- `quality-infra.md` - Testing, CI/CD, and infrastructure
- `refactorer.md` - Code quality and refactoring
- `copilot-instructions-updater.md` - Meta-agent for improving these instructions

## MCP Tools (Model Context Protocol)

Configuration: `.vscode/mcp.json` | Full reference: `docs/ai-agents/mcp-tools.md`

### Session Setup (Required)

Pylance may default to global Python. At session start:
```
pylancePythonEnvironments(workspaceRoot: "file:///Users/timchild/github/PaperTrade")
# ICommon Development Tasks

For detailed quality checks, Docker management, and pre-completion checklists:

> 📖 **See**: [agent_tasks/reusable/quality-and-tooling.md](../agent_tasks/reusable/quality-and-tooling.md)

**Quick reference**:
- `task quality:backend` - Format + lint + test backend
- `task quality:frontend` - Format + lint + test frontend
- `task ci` - Run all CI checks locally
- `task docker:up` - Start PostgreSQL, Redis
- All tasks: `task --list`

## MCP Tools (Model Context Protocol)

Configuration: `.vscode/mcp.json` | Full reference: `docs/ai-agents/mcp-tools.md`

**Quick reference**:

| Tool | Purpose | Output |
|------|---------|--------|
| Container logs | `logs_for_container` | Clean output |
| PR details | `activePullRequest` | Full PR context |

### When to Use Terminal Instead

- Running tests: `task test:backend`
- Installing packages: `uv add`, `npm install`
- Git operations: `git`, `gh`
- Complex shell pipelines
