# Zebu — Project Conventions for Claude

Zebu (repo: `TimChild/PaperTrade`) is a stock-market paper-trading platform — practice trading without real money. **Phase 4 complete, v1.0.0 deployed** to `https://zebutrader.com` (Proxmox VM, self-hosted CD pipeline). See `docs/planning/agent-platform-proposal.md` for the active forward plan (agent-driven trading, Phase 5).

## Tech stack

**Backend** — Python 3.13+, FastAPI, SQLModel, Pyright (strict), Ruff, Pytest. Postgres prod, SQLite dev. Redis cache. APScheduler. Clerk auth (Bearer JWT only — no API key path yet).

**Frontend** — TypeScript strict, React + Vite, TanStack Query, Zustand, Tailwind. Vitest + Playwright.

**Infra** — Docker Compose, AWS CDK (Python), GitHub Actions CD via self-hosted runner `papertrade-proxmox`. Push to `main` auto-deploys.

## Architecture (Clean Architecture, hard rule)

```
Domain  →  Application  →  Adapters  →  Infrastructure
```

Dependencies point inward only. Domain has **no I/O, no side effects**. Repository ports defined in Application; adapters in `adapters/outbound`. See `docs/architecture/principles.md` for the full rules.

## Code quality bar (non-negotiable)

- **No `Any`** in Python, **no `any`** in TypeScript. No type-checker suppressions without a documented reason.
- Behavior-focused tests. Mock only at architectural boundaries — never internal logic.
- Tests pass before marking work complete. CI runs `task ci`; the same locally.
- Conventional commits: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `ci`.
- One PR = one concern. Bundle related changes together (don't micro-split coupled work).

## How to run things

```bash
task setup                # First-time: deps + Docker
task dev:backend          # Backend on http://localhost:8000
task dev:frontend         # Frontend on http://localhost:5173
task quality:backend      # format + lint + test (backend)
task quality:frontend     # format + lint + test (frontend)
task ci                   # All CI checks (mirror of GitHub Actions)
task docs:serve           # Serve mkdocs locally on http://localhost:8000
task --list               # Everything else
```

For test runs and Docker management, see `.claude/skills/quality-checks/SKILL.md`.

## Where things live

| Path | What |
|---|---|
| `backend/src/zebu/` | All backend code (note: directory is `zebu`, not `papertrade`) |
| `backend/src/zebu/domain/` | Pure domain (entities, value objects, services) |
| `backend/src/zebu/application/` | Use cases (commands, queries, ports) |
| `backend/src/zebu/adapters/inbound/api/` | FastAPI routers |
| `backend/src/zebu/adapters/outbound/` | DB/market-data adapters |
| `backend/src/zebu/infrastructure/` | Scheduler, DB config, cache |
| `backend/tests/{unit,integration}/` | Tests (test pyramid) |
| `frontend/src/` | React app |
| `docs/` | Human-facing (MkDocs site) |
| `agent_docs/tasks/` | Numbered task specs (`NNN_short_name.md`) |
| `agent_docs/progress/` | Dated session reports |
| `.claude/agents/` | Role-specialist agent definitions |
| `.claude/skills/` | Project-local skills (procedural knowledge) |

## Specialist agents (`.claude/agents/`)

Use the `Agent` tool with the matching `subagent_type` (or have the user invoke them).

| Agent | When |
|---|---|
| `architect` | Design entities, interfaces, contracts. **Produces structured specs only — no code.** |
| `backend-swe` | Python/FastAPI implementation, Clean Architecture compliance |
| `frontend-swe` | React/TypeScript UI, TanStack Query, accessibility |
| `quality-infra` | CI/CD, Docker, testing infra, AWS CDK |
| `refactorer` | Code-smell elimination, no behavior change |
| `qa` | E2E testing with Playwright, severity-tagged reports |
| `docs-refactorer` | Documentation consolidation, deletion-vs-archive |

## Project skills (`.claude/skills/`)

| Skill | Use for |
|---|---|
| `before-starting-work` | Pre-work checklist (recent activity, open PRs, architecture docs) |
| `quality-checks` | Backend/frontend/Docker quality task reference |
| `git-workflow` | Branches, commits, PR creation conventions |
| `e2e-qa-validation` | Comprehensive QA test scenarios + report template |
| `docs-tidy` | BACKLOG / PROGRESS / README maintenance |
| `orchestrate-zebu` | PR-review criteria, parallel-execution safety, task scoping |

## Task workflow

For multi-step work, write a numbered task spec under `agent_docs/tasks/NNN_short_name.md` (the next number is **211** — most recent is `210_live_strategy_execution.md`, scoped but not started).

Task specs include: Overview, Context (what exists), Architecture (new domain concepts, flow, endpoints), Implementation Plan (phases), Testing Strategy, Success Criteria, Agent Assignment, References. After completion, write a progress doc to `agent_docs/progress/YYYY-MM-DD_HH-MM-SS_short-description.md`.

## Forward plan

The active proposal is `docs/planning/agent-platform-proposal.md` — six phases (A–F) to evolve Zebu into an agent-driven trading platform with the app as human GUI and looped/scheduled agents executing strategies via API/MCP. **Read it before doing significant new work.**

Status: Phase A (this Claude infra migration) is in progress as of 2026-05-09. Phase B is Task #210 + API-key auth + `ExplorationTask` queue.

## Things to remember

- **Naming**: product is "Zebu", repo is `PaperTrade`, import path is `zebu`. All three refer to the same thing.
- **Auth**: every API endpoint sits behind Clerk Bearer JWT. There's no API-key path. Adding one is part of Phase B in the proposal.
- **Hot paths**: `backend/src/zebu/application/services/backtest_executor.py` is the canonical "iterate over days, generate signals, execute trades" loop — Task #210's live executor will mirror its structure.
- **CD is live**: pushing to `main` deploys to production. Add `[skip deploy]` in the commit message to skip.
- **Pre-commit runs on push**, not commit. So commits are fast; push is where formatters run.

## Don't

- Don't introduce `Any` / `any` to silence the type checker. Fix the type instead.
- Don't add a `useEffect` to sync props to state — use the `key` prop pattern (see `.claude/agents/frontend-swe.md`).
- Don't import from `infrastructure` in `domain`. The dependency rule is enforced by review.
- Don't run `git add -A` blindly — be specific to avoid catching stray secrets.
- Don't create new docs without considering whether they could fit in an existing one. The `docs-refactorer` skill describes the deletion-vs-archive policy.
