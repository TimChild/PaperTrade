# Phase B1 Audit Summary

**Date**: 2026-05-09
**Scope**: 12 parallel audit dimensions per `docs/planning/agent-platform-proposal.md` §B1
**Total findings**: 137 (P0: 24 / P1: 56 / P2: 47 / P3: 10)

The 12 individual reports in this directory are the source of truth. This summary consolidates and prioritizes for execution.

---

## TL;DR

The codebase is in **better shape than feared on the inside, worse than expected on the edges**.

**Inside (good news)**:

- Frontend code quality — zero `any`, zero ESLint suppressions, zero `@ts-ignore`, no setState-in-useEffect anti-patterns. Frontend P0 count: 0.
- Domain layer is mostly pure and well-formed (no Domain → Infra leaks, invariants enforced where they exist). Domain P0: 0.
- Auth and SQL hygiene at the standard endpoints — Pydantic validation everywhere, parameterized SQL, ownership checks on the user-facing routes that have auth.

**Edges (bad news)**:

- **Two unauthenticated admin endpoints exposed to the internet right now** — `POST /api/v1/analytics/prices/refresh` and `POST /api/v1/analytics/snapshots/daily` callable by anyone. (`security.md` P0-1, `api-design.md` P0-2.)
- Backfill endpoint takes `CurrentUserDep` but **ignores it** — User A can backfill User B's snapshots. (`security.md` P0-2.)
- The full `prices` and `debug` routers lack auth. (`api-design.md` P0-1, P0-3.)
- Critical Clerk SDK CVE: middleware-based route-protection bypass. Plus 9 high CVEs across `cryptography`, `urllib3`, `pyjwt`, `mako`. (`dependencies.md` P0-1, P0-2.)
- `engine = create_async_engine(..., echo=True)` hardcoded in production — full SQL queries logged on every request. (`database.md` P0-1.)
- Zero foreign-key constraints across the whole schema. (`database.md` P0-2.)
- README onboarding flow **broken end-to-end** — points at deleted `./.github/copilot-setup.sh`, wrong import path `papertrade.main:app` (should be `zebu.main:app`), dead links. A fresh dev or agent cannot complete setup. (`documentation.md` P0-1 through P0-4.)
- `architecture_plans/` referenced as a real directory by `architect.md`, `backend-swe.md`, and the `before-starting-work` skill — **the directory doesn't exist**, so any architect dispatch silently writes to a path divorced from convention. (`claude-infra.md` P0-1.)
- E2E hits the live Alpha Vantage `demo` API key (5/min, 25/day, only `IBM` works), explaining most of the "auth flakiness" Tim flagged. The Clerk path was iteratively fixed by PR #171; the demo-key path was never the suspect. (`test-quality.md` P0-1.)

**Structural debt themes (Phase B foundation work)**:

1. **`dict[str, Any]` propagation** — `Strategy.parameters` and `BacktestRun.strategy_snapshot` are typed `dict[str, Any]`, propagating opacity through executor, API, and (soon) MCP layers. Forces runtime `isinstance` validation. Blocker for typed agent-facing schemas. (`backend-code-quality.md` P0-1, `domain-model.md` P1-2.)
2. **Domain → Application import cycle** — strategy modules import `PricePoint` from `zebu.application.dtos`, creating a real upward dependency. Will compound as Phase C / F add live and trigger executors. (`architecture.md` P0-1, P0-2.)
3. **Missing value objects** in `TradeSignal`, `Allocation`, monetary fields — primitive obsession on the highest-traffic agent path. (`domain-model.md` P1-1 through P1-5.)
4. **Inconsistent error-response shape** — `detail` field sometimes `str`, sometimes structured `dict`, frontend can't reliably parse. Phase D MCP needs a single shape. (`api-design.md` P1-1.)
5. **N+1 query patterns** in `BacktestExecutor` and `SnapshotJobService.run_daily_snapshot`. (`database.md` P1-2, P1-3.)
6. **Missing pagination** on list endpoints that will grow under Phase E (`list_strategies`, `list_backtests`, `get_all_balances`). (`api-design.md` P1-3.)

**Claude infra opportunity (B7)**: two clear gap skills surfaced:

1. **`audit-mode` skill** — "audit mode" was invoked 3 times in the proposal and 12 times in this very session, but is undefined anywhere in `.claude/`. Codifying it makes every future Phase-B-style cycle cheaper. (`claude-infra.md` GAP-1.)
2. **`claude-infra-sync` skill** — already named in §B7, this audit produced its concrete spec. (`claude-infra.md` GAP-2.)

---

## Counts by dimension

| Dimension | P0 | P1 | P2 | P3 | Total |
|---|---:|---:|---:|---:|---:|
| Architecture | 2 | 5 | 5 | 2 | 14 |
| Backend code quality | 3 | 4 | 4 | 2 | 13 |
| Frontend code quality | 0 | 3 | 4 | 2 | 9 |
| Test quality & flakiness | 2 | 5 | 4 | 1 | 12 |
| CI infrastructure | 1 | 4 | 3 | 2 | 10 |
| Domain model | 0 | 5 | 5 | 2 | 12 |
| API design | 3 | 5 | 4 | 2 | 14 |
| Security | 2 | 4 | 4 | 1 | 11 |
| Database | 2 | 5 | 5 | 2 | 14 |
| Documentation | 4 | 6 | 5 | 2 | 17 |
| Dependencies | 2 | 5 | 4 | 1 | 12 |
| Claude infrastructure | 3 | 5 | 4 | 2 | 14 |
| **Totals** | **24** | **56** | **47** | **21** | **148** |

Per-finding detail and reproduction in the matching `<dimension>.md` file.

---

## Execution plan — five waves

I'm running these as separate PRs so each is small, independently reviewable, and can land in parallel where dependencies allow. Wave 1 is production-urgency (real exposed risk on prod today) and ships first.

### Wave 1 — production-urgency fixes (parallel, ASAP)

| PR | Title | Closes findings |
|---|---|---|
| W1-A | `sec: gate unauthenticated admin endpoints + fix backfill ownership` | `sec.P0-1`, `sec.P0-2`, `api.P0-1`, `api.P0-2`, `api.P0-3` |
| W1-B | `chore(deps): upgrade Clerk SDK chain + critical CVEs` | `deps.P0-1`, `deps.P0-2` |
| W1-C | `fix(db): disable SQL echo in production engine` | `db.P0-1` |
| W1-D | `docs: fix broken README onboarding (deleted setup script, wrong import path, dead links)` | `docs.P0-1` through `docs.P0-4` |

These four can ship independently. Estimated ~1–2 days total of agent time; Wave 1 should be in main within the next session.

### Wave 2 — fast wins, bigger surface (parallel after Wave 1)

| PR | Title | Closes |
|---|---|---|
| W2-A | `fix(claude-infra): create architecture_plans/, fix CLAUDE.md inconsistencies, drop stale Copilot refs in agent files` | `claude.P0-1`, `claude.P0-2`, `claude.P0-3` |
| W2-B | `ci: add concurrency cancellation + path filters + dependency audit` | `ci.P0-1`, `ci.P1-1`, `ci.P1-2`, `ci.P1-4`, `deps.P2-3` |
| W2-C | `test(e2e): replace Alpha Vantage demo key with deterministic price fixtures` | `test.P0-1` |
| W2-D | `docs: aggressive deletion of stale archive material + fix broken cross-links` | `docs.P0-onwards`, `docs.P1-2`, `docs.P1-3` (8 outright deletions per docs-refactorer) |

### Wave 3 — foundation refactors (mostly sequential — touch core code)

| PR | Title | Closes |
|---|---|---|
| W3-A | `refactor(arch): lift PricePoint to domain, eliminate Domain→Application cycle` | `arch.P0-1`, `arch.P0-2`, `arch.P1-1`, `arch.P1-2` |
| W3-B | `refactor(domain): typed Strategy params (replace dict[str, Any] with per-type dataclasses)` | `bcode.P0-1`, `domain.P1-2`, `api.P1-4` |
| W3-C | `refactor(domain): TradeSignal as proper value object with invariants + Allocation VO` | `domain.P1-1`, `domain.P1-3`, `domain.P1-4` |
| W3-D | `fix(db): add foreign keys + cascades + (portfolio_id, snapshot_date) unique` | `db.P0-2`, `db.P1-3`, `db.P1-4` |
| W3-E | `fix(market-data): un-swallow exceptions in MarketDataPort hot path` | `bcode.P0-2`, `bcode.P0-3` |
| W3-F | `fix(perf): eliminate N+1 in BacktestExecutor and SnapshotJobService` | `db.P1-1`, `db.P1-2` |
| W3-G | `feat(api): standardize error response shape + add list-endpoint pagination` | `api.P1-1`, `api.P1-3`, `api.P1-5` |

### Wave 4 — test + infra hardening

| PR | Title | Closes |
|---|---|---|
| W4-A | `test: unit tests for both auth adapters + parameterize for upcoming API-key auth path` | `test.P0-2`, `test.P1-1`, `test.P1-2` |
| W4-B | `chore(runner): harden self-hosted runner (auto-prune, structured logs, workspace isolation), then move CI` | `ci.P1-3` |
| W4-C | `test: convert implementation-focused tests to behavior-focused on critical paths` | `test.P1-3`, `test.P1-4`, `test.P1-5` |

### Wave 5 — Claude infra refresh (B7)

| PR | Title | Closes |
|---|---|---|
| W5-A | `feat(skill): add audit-mode skill (codify what this very audit demonstrated)` | `claude.GAP-1`, `claude.P1-1` |
| W5-B | `feat(skill): add claude-infra-sync skill (drift detection + freshness checks)` | `claude.GAP-2` |
| W5-C | `refactor(.claude): tighten agent definitions per audit findings; merge / split where needed` | remaining `claude.P1-*`, `claude.P2-*` |

---

## What I'm explicitly DEFERRING (P2 / P3)

**Pushed to a `Phase B deferred` backlog** in `agent_docs/audits/2026-05-09/DEFERRED.md` (will create at end of Phase B):

- All P3 findings (10 items) — defer to a future cleanup pass
- P2 cleanups that don't materially impact Phase C–G — defer
- License-compatibility deep dive on dependencies (the `Q5` OSS-readiness flag means we'll want this eventually, but not on the critical path)

**Out of scope for Phase B entirely**:

- Adding new feature surface (Phase C onwards)
- Migrations of test data (we'll reset test DBs)
- Documentation rewrites for parts of the codebase that will be heavily refactored in Phase C anyway

---

## Risk register (for transparency)

- **Foreign-key migration (W3-D)** is the single highest-risk PR. Touches every existing FK column, requires data validation pass before hard constraints can land. Plan: ship alongside an Alembic migration that adds constraints in a separate transaction, validate data first, fail safely if orphan rows exist.
- **Strategy parameter typing (W3-B)** changes the JSON shape stored in `BacktestRun.strategy_snapshot`. Need a data-migration pass for existing rows or accept lossy conversion — TBD per environment (prod has zero deployed agent activations, just human-created strategies, so risk is bounded).
- **Auth fixes (W1-A)** add 401 / 403 responses where currently there were 200s on admin endpoints. Anything in production calling those endpoints anonymously will break — but per audit findings, nothing should be (those endpoints are admin-only by intent, just not by enforcement).

---

## Phase B effort revised

Original estimate: 2–4 weeks. With 24 P0 findings and the breadth of structural debt surfaced, **revised estimate: 3–4 weeks** of orchestrator + parallel agent time. Wave 1 + 2 are the bulk of immediate-value work and should land within the next 2–3 sessions; Waves 3–5 will span multiple sessions thereafter.

Tim's input gate: per his guidance, I'm proceeding without prioritization signoff. I'll surface anything genuinely ambiguous as I go.
