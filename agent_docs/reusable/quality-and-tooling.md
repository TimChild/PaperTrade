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

## Environment Validation

| Task | Description |
|------|-------------|
| `task validate:env` | Validate complete environment setup |
| `task validate:secrets` | Check required secrets/env vars |
| `task health:all` | Check all services are healthy |
| `task health:wait` | Wait for services to be ready |

**When to use**:
- **First time setup**: Run `task validate:env` to ensure everything is configured
- **Before E2E tests**: Automatically run by `task test:e2e`
- **Debugging issues**: Use `task health:all` to check service status
- **In CI**: Automatically run during setup

**Example output**:
```bash
$ task validate:env
=== Environment Validation ===
✓ uv: 0.9.24
✓ npm: 10.8.2
✓ Python 3.13 (>= 3.12 required)
✓ Docker services running
✓ Backend imports working
✅ All required checks passed!
```

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
