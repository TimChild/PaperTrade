# Quality Checks & Development Tooling

Quick reference for running quality checks, managing Docker, and pre-completion validation.

## Setup

Run once per session (if not already done):
```bash
task setup              # Installs all dependencies + starts Docker
```

## Backend Quality Checks

| Task | Description |
|------|-------------|
| `task format:backend` | Auto-format code (ruff) |
| `task lint:backend` | Lint + type check (ruff, pyright) |
| `task test:backend` | Run tests with coverage |
| `task quality:backend` | **All of the above** |

**Requirements**: Complete type hints (no `Any`), docstrings for public APIs, tests for new functionality.

**Common Fixes**:
- "Would reformat" → `task format:backend`
- Type errors → Add explicit type hints, read error message
- Import errors → Check spelling, add import

## Frontend Quality Checks

| Task | Description |
|------|-------------|
| `task format:frontend` | Auto-format code (prettier) |
| `task lint:frontend` | Lint + type check (eslint, tsc) |
| `task test:frontend` | Run unit tests (vitest) |
| `task quality:frontend` | **All of the above** |

**Requirements**: TypeScript strict mode (no `any`), explicit return types, `data-testid` on interactive elements.

**Common Fixes**:
- "Code style issues" → `task format:frontend`
- Type errors → Add explicit types, check return types
- JSX namespace → `import type { JSX } from 'react'`

## Docker Commands

| Task | Description |
|------|-------------|
| `task docker:up` | Start PostgreSQL, Redis |
| `task docker:up:all` | Start full stack (db, redis, backend, frontend) |
| `task docker:down` | Stop all services |
| `task docker:logs` | Tail all service logs |
| `task docker:restart` | Restart all services |
| `task docker:clean` | Stop + remove volumes (**deletes data**) |

**Status & Debugging**:
```bash
docker compose ps               # Service status
task docker:logs                # All logs
task docker:logs:backend        # Backend only
```

**Common Issues**:
- Port in use → `lsof -ti:5432 | xargs kill -9`
- Container won't start → `task docker:logs`
- Database issues → `task docker:clean && task docker:up`

## Pre-Completion Checklist

**Run before marking work complete to prevent CI failures:**

```bash
task quality:backend    # Backend: format + lint + test
task quality:frontend   # Frontend: format + lint + test
task test:e2e           # If UI changes (starts full stack automatically)
```

Or run everything:
```bash
task ci                 # All CI checks (same as GitHub Actions)
```

**DO NOT mark work complete until all checks pass!**
