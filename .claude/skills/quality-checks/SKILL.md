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
| `task docker:down` | Stop |
| `task docker:logs[:backend|:frontend]` | Tail logs |
| `task docker:restart[:backend|:frontend]` | Restart services |
| `task docker:clean` | Stop + remove volumes (deletes data) |

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
task ci                    # all checks (== GitHub Actions)
task ci:fast               # lint only, skip tests
```

**Don't mark work complete until all checks pass.** CI runs the same commands.

## All tasks

```bash
task --list
```
