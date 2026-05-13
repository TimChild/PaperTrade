# Zebu — Project Conventions for Claude

Zebu (repo: `TimChild/PaperTrade`) is a stock-market paper-trading platform — practice trading without real money. **Phase J complete**, v1.0.0 deployed to `https://zebutrader.com` (Proxmox VM, self-hosted CD pipeline). The agent-platform plan has shipped end-to-end through Phase J — see `docs/planning/agent-platform-completed.md` (historical) and `docs/planning/agent-platform-next-steps.md` (active forward plan: multi-provider invocation + agent-driven backtests).

## Tech stack

**Backend** — Python 3.13+, FastAPI, SQLModel, Pyright (strict), Ruff, Pytest. Postgres prod, SQLite dev. Redis cache. APScheduler. Dual auth — Clerk Bearer JWT for humans, API key for machine identities (see the **Auth** entry under "Things to remember" for the full dual-auth pattern).

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
| `mcp/` | `zebu-mcp` MCP server — exposes Zebu read tools to Claude Code agents (Phase D, Wave 1). See `mcp/README.md` for install + Claude Code attach instructions. |

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
| `audit-mode` | "Audit mode" report format, P-tier calibration, multi-agent audit dispatch pattern |
| `claude-infra-sync` | Detect drift in `CLAUDE.md`/`.claude/` against the actual repo (run at the end of every major Phase or Wave) |

## Task workflow

For multi-step work, write a numbered task spec under `agent_docs/tasks/NNN_short_name.md` (the next number is **214** — most recent is `213_queue_mode_triggers.md`, shipped in Phase J).

Task specs include: Overview, Context (what exists), Architecture (new domain concepts, flow, endpoints), Implementation Plan (phases), Testing Strategy, Success Criteria, Agent Assignment, References. After completion, write a progress doc to `agent_docs/progress/YYYY-MM-DD_HH-MM-SS_short-description.md`.

## Forward plan

The agent-platform plan (Phases A–J) has shipped end-to-end. The historical record is in `docs/planning/agent-platform-completed.md`; the active forward plan is `docs/planning/agent-platform-next-steps.md` (multi-provider invocation, agent-driven backtests, plus a follow-up sweep). **Read the next-steps doc before scoping significant new work.**

## Things to remember

- **Naming**: product is "Zebu", repo is `PaperTrade`, import path is `zebu`. All three refer to the same thing.
- **Auth**: two paths coexist — Clerk Bearer JWT for humans, and API key (Phase C2) for machine identities (agents, scheduled tasks, MCP servers). Agents authenticate by minting a key at `POST /api/v1/api-keys` (Clerk-gated) and presenting it via `Authorization: ApiKey <key>` or `X-API-Key: <key>`. Both schemes resolve to the same `AuthenticatedUser` shape — route handlers don't care which path was used. Scope enforcement (`require_scope`) is wired but not applied broadly yet — that's a Phase D sweep.
- **Hot paths**: `backend/src/zebu/application/services/backtest_executor.py` (backtest loop) and `backend/src/zebu/application/services/strategy_execution_service.py` (live executor — mirrors the backtest loop's "iterate, generate signals, execute trades" shape). Both are canonical references for any new strategy-execution work.
- **CD is live**: pushing to `main` deploys to production. Add `[skip deploy]` in the commit message to skip.
- **Pre-commit runs on push**, not commit. So commits are fast; push is where formatters run.
- **Run `claude-infra-sync` at the end of every major Phase or Wave**: the skill at `.claude/skills/claude-infra-sync/SKILL.md` audits `CLAUDE.md` + `.claude/` for drift against the actual repo. Run it before the next agent dispatch cycle (or as the closeout of a Wave) and address BLOCKERs in the same PR.

## Don't

- Don't introduce `Any` / `any` to silence the type checker. Fix the type instead.
- Don't add a `useEffect` to sync props to state — use the `key` prop pattern (see `.claude/agents/frontend-swe.md`).
- Don't import from `infrastructure` in `domain`. The dependency rule is enforced by review.
- Don't run `git add -A` blindly — be specific to avoid catching stray secrets.
- Don't create new docs without considering whether they could fit in an existing one. The `docs-refactorer` skill describes the deletion-vs-archive policy.
