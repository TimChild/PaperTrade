---
name: quality-checks
description: Quality / lint / test / Docker task reference for Zebu. Backend (ruff, pyright, pytest), frontend (eslint, tsc, vitest), and Docker / Compose / health-check commands.
---

# Quality Checks & Tooling

Quick reference for running the same checks CI runs.

## Setup (once per machine / branch)

```bash
task setup                # deps + Docker services + pre-commit hooks
```

## Backend

| Task | What |
|---|---|
| `task format:backend` | Ruff format |
| `task lint:backend` | Ruff lint + Pyright (strict) |
| `task test:backend` | Pytest with coverage |
| `task quality:backend` | All of the above |

Requirements: complete type hints (no `Any`), docstrings on public APIs, tests for new functionality.

Common fixes:

- "Would reformat" → `task format:backend`
- Pyright errors → add explicit type, read the error
- ImportError → check spelling, run `uv sync --all-extras` in `backend/`

## Frontend

| Task | What |
|---|---|
| `task format:frontend` | Prettier |
| `task lint:frontend` | ESLint + tsc |
| `task test:frontend` | Vitest unit tests |
| `task quality:frontend` | All of the above |

Requirements: TS strict (no `any`), explicit return types, `data-testid` on interactive elements.

Common fixes:

- "Code style issues" → `task format:frontend`
- TS errors → add explicit types, check return types
- JSX namespace → `import type { JSX } from 'react'`

## Docker

| Task | What |
|---|---|
| `task docker:up` | Postgres + Redis only |
| `task docker:up:all` | Full stack (db + redis + backend + frontend) |
| `task docker:up:ci` | CI-isolated stack — db/redis only on docker network, no host 5432/6379 |
| `task docker:down` | Stop the dev stack |
| `task docker:down:ci` | Stop the CI-isolated stack |
| `task docker:logs[:backend|:frontend]` | Tail logs |
| `task docker:restart[:backend|:frontend]` | Restart services |
| `task docker:clean` | Stop + remove dev volumes (deletes data) |
| `task docker:clean:ci` | Stop the CI stack + remove its volumes |

The CI stack (`docker-compose.ci.yml`) runs under `COMPOSE_PROJECT_NAME=papertrade-ci` and omits the host bindings for `db` / `redis`. This is what `task ci` / `task ci:e2e` use locally so they don't collide with a developer's dev Postgres on host port 5432. The dev stack is unaffected — both can run side by side.

Status / debugging:

```bash
docker compose ps
task docker:logs                  # all logs
task docker:logs:backend          # backend only
```

Common issues:

- Port in use → `lsof -ti:5432 | xargs kill -9` (after verifying with `lsof -i:5432`)
- Container won't start → `task docker:logs`
- DB issues → `task docker:clean && task docker:up` (data loss)

## Environment validation

| Task | What |
|---|---|
| `task validate:env` | Full env validation (Python version, npm, Docker, imports) |
| `task validate:secrets` | Check required env vars / secrets |
| `task health:all` | All-services health check |
| `task health:wait` | Block until services healthy |

## Pre-completion checklist

Before marking work complete:

```bash
task quality:backend       # backend changes
task quality:frontend      # frontend changes
task test:e2e              # if UI changed
```

Or run the full CI:

```bash
task ci                    # all checks (== GitHub Actions); uses the CI-isolated docker stack
task ci:fresh              # tear down any running dev/CI stacks first, then `task ci` (destructive)
```

The CI suite brings up its own isolated Postgres / Redis (no host port bindings) so it doesn't collide with a running dev stack. Backend (8000) and frontend (5173) still bind to default host ports because Playwright needs to reach them — if those collide with a running dev backend / frontend, use `task ci:fresh` to tear the dev stack down first.

**Don't mark work complete until all checks pass.** CI runs the same commands.

## All tasks

```bash
task --list
```
