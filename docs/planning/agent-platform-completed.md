# Agent Platform — What Shipped (Phases A–D Wave 2)

**Status**: Historical record — what landed between 2026-05-09 and 2026-05-10.
**Picks up from**: [`archive/agent-platform-proposal-2026-05-09.md`](archive/agent-platform-proposal-2026-05-09.md) — the original seven-phase plan (A→G).
**Hands off to**: [`agent-platform-proposal.md`](agent-platform-proposal.md) — the forward plan from the current state.

---

## TL;DR

In two days of orchestrated multi-agent work, Zebu went from "deployed v1.0.0 with no agent infra" to "live agent-driven trading platform with MCP server end-to-end smoke-tested against prod." Phases A through D Wave 2 are done. Plus a frontend revamp that wasn't in the original plan.

| Phase | Original goal | Shipped | PR refs |
|---|---|---|---|
| A | Modernize Claude infrastructure | Done 2026-05-09 | #210 |
| B | Codebase health audit + foundation refactor | 22 PRs across 5 waves | #211–#234 |
| C | Live strategy execution + machine identity (API-key auth) + ExplorationTask | 5 PRs | #235, #236, #237, #238, #239 |
| D Wave 1 | MCP server foundation + read tools | Done 2026-05-10 | #241 |
| D Wave 2 | MCP write tools | Done 2026-05-10 | #242 |
| (extra) | Frontend revamp — editorial dark theme | 2 waves, full app coverage | #247, #248 |
| (extra) | Production stabilisation fixes | Various | #240, #243, #244, #246 |

End-to-end smoke test against production passed on 2026-05-10: API-key auth + 23 MCP tools + read+write paths all working.

---

## Phase A — Claude infrastructure modernization (2026-05-09)

Bootstrapped the project for Claude Code. Replaced the old GitHub Copilot agent infrastructure (`.github/agents/`, `agent_docs/reusable/`, `agent_docs/orchestration-guide.md`) with native Claude conventions.

**Shipped**:

- `CLAUDE.md` at repo root
- 7 specialist agents in `.claude/agents/` — `architect`, `backend-swe`, `frontend-swe`, `qa`, `quality-infra`, `refactorer`, `docs-refactorer`
- 6 procedural skills in `.claude/skills/` — `before-starting-work`, `quality-checks`, `git-workflow`, `e2e-qa-validation`, `docs-tidy`, `orchestrate-zebu`
- `docs/architecture/principles.md` — Clean Architecture rules promoted from agent docs to a published doc
- 6 project-memory entries under `~/.claude/projects/-Users-timchild-github-PaperTrade/memory/`
- Old Copilot infra deleted: `.github/copilot-instructions.md`, `.github/agents/`, `agent_docs/reusable/`, `agent_docs/orchestration-guide.md`
- Stale-state cleanup: `resume-from-here.md` deleted, test counts reconciled, roadmap restructured (Phase 4 → ✅ complete)

**PR**: [#210](https://github.com/TimChild/PaperTrade/pull/210)

---

## Phase B — Codebase health audit + foundation refactor (2026-05-09)

Five waves covering 22 PRs. Treated like a "team of senior SWEs joins the project" pass — surfaced structural debt, fixed P0/P1 critical findings, deferred the rest as documented backlog.

### Wave 1 — Audit ([#211](https://github.com/TimChild/PaperTrade/pull/211))

12-dimension multi-agent audit producing prioritized findings under `agent_docs/audits/2026-05-09/`. Each dimension dispatched as a parallel specialist agent (architect, backend-swe audit-mode, frontend-swe audit-mode, quality-infra, etc.) producing a P0/P1/P2/P3 calibrated report.

### Wave 2 — Critical fixes (P0)

| PR | What |
|---|---|
| [#212](https://github.com/TimChild/PaperTrade/pull/212) | Disable SQL echo in production engine |
| [#213](https://github.com/TimChild/PaperTrade/pull/213) | Fix broken README onboarding (deleted setup script, wrong import path, dead links) |
| [#214](https://github.com/TimChild/PaperTrade/pull/214) | Upgrade Clerk SDK + critical Python CVE deps |
| [#215](https://github.com/TimChild/PaperTrade/pull/215) | Gate unauthenticated admin endpoints + backfill ownership check |
| [#216](https://github.com/TimChild/PaperTrade/pull/216) | Remove `Debug.tsx` page (admin-only on backend) |
| [#217](https://github.com/TimChild/PaperTrade/pull/217) | Drop `architecture_plans/` refs, reconcile `CLAUDE.md`, gitignore worktrees |
| [#218](https://github.com/TimChild/PaperTrade/pull/218) | CI hardening: concurrency cancellation, path filters, pip-audit, secret scan |
| [#219](https://github.com/TimChild/PaperTrade/pull/219) | Aggressive docs deletion pass + reconcile test counts |
| [#220](https://github.com/TimChild/PaperTrade/pull/220) | Replace Alpha Vantage demo key with deterministic mock adapter for E2E |
| [#221](https://github.com/TimChild/PaperTrade/pull/221) | Lift `PricePoint` to domain, eliminate `Domain → Application` cycle |

### Wave 3 — Foundation refactors

| PR | What |
|---|---|
| [#222](https://github.com/TimChild/PaperTrade/pull/222) | Un-swallow exceptions in `MarketDataPort` hot path |
| [#223](https://github.com/TimChild/PaperTrade/pull/223) | Eliminate N+1 queries in `BacktestExecutor` and `SnapshotJobService` |
| [#224](https://github.com/TimChild/PaperTrade/pull/224) | DB foreign key constraints, snapshot unique, `pool_pre_ping` (required Tim authorization) |
| [#225](https://github.com/TimChild/PaperTrade/pull/225) | `TradeSignal` value object with invariants + `Allocation` VO |
| [#227](https://github.com/TimChild/PaperTrade/pull/227) | Typed `Strategy` parameters per strategy type |
| [#228](https://github.com/TimChild/PaperTrade/pull/228) | Standardize error envelope + paginate list endpoints |

### Wave 4 — Test + CI quality

| PR | What |
|---|---|
| [#231](https://github.com/TimChild/PaperTrade/pull/231) | Harden self-hosted runner config + add runbook |
| [#232](https://github.com/TimChild/PaperTrade/pull/232) | Auth adapter unit tests + Phase C-ready fixture |
| [#233](https://github.com/TimChild/PaperTrade/pull/233) | Convert critical-path tests to behavior-focused |

### Wave 5 — Claude-infra refresh + sync skill

| PR | What |
|---|---|
| [#229](https://github.com/TimChild/PaperTrade/pull/229) | Add `audit-mode` skill |
| [#230](https://github.com/TimChild/PaperTrade/pull/230) | Add `claude-infra-sync` skill |
| [#234](https://github.com/TimChild/PaperTrade/pull/234) | Drift fixes from `claude-infra-sync` (Phase A migration was "good enough"; re-tuned to current state, including Python 3.13 alignment) |

---

## Phase C — Live strategy execution + machine identity (2026-05-09 to 2026-05-10)

Brought together the live-execution path (Task #210), API-key auth for machine identity, and the ExplorationTask queue for the agent ↔ human feedback channel. Five PRs with sequential migration rebases (each migration's `down_revision` had to be re-pointed at the latest landed head).

| PR | What |
|---|---|
| [#235](https://github.com/TimChild/PaperTrade/pull/235) | `StrategyActivation` entity + repository + Alembic migration (Task #210 Phase 1) |
| [#236](https://github.com/TimChild/PaperTrade/pull/236) | `ExplorationTask` entity + queue endpoints (`POST/GET/DELETE /exploration-tasks`, `claim`, `findings`) — the agent-input channel |
| [#237](https://github.com/TimChild/PaperTrade/pull/237) | API-key authentication path: HMAC-SHA256 hashed keys, `read`/`trade`/`admin` scopes, both `Authorization: ApiKey <key>` and `X-API-Key: <key>` accepted; agents authenticate by minting at `POST /api/v1/api-keys` (Clerk-gated) |
| [#238](https://github.com/TimChild/PaperTrade/pull/238) | Live strategy execution service + endpoints (Task #210 Phases 2/3) — daily scheduler job, `POST /activations/{id}/run-now` for agent-triggered execution |
| [#239](https://github.com/TimChild/PaperTrade/pull/239) | Live strategy activation UI (Task #210 Phase 4) |

**Note**: PR #239 surfaced an E2E flakiness root cause — `MARKET_DATA_PROVIDER=mock` wasn't being set on the E2E test step (compose recreated the container with the default `alpha_vantage`, hitting the public demo key's IBM-only restriction). Fixed in workflow + test.

---

## Phase D Waves 1+2 — MCP server (2026-05-10)

Built `zebu-mcp`, a FastMCP-based stdio server that exposes the Zebu backend as named tools to Claude Code agents. In-tree at `mcp/` (Q6 resolved: never company infra; personal Proxmox for sidecar deploy if/when we extract).

### Wave 1 — Foundation + read tools ([#241](https://github.com/TimChild/PaperTrade/pull/241))

13 read tools, all paginated where applicable, all surfacing `total` / `limit` / `offset` / `has_more`:

- Trading data: `list_supported_tickers`, `get_current_price`, `get_price_history`, `list_portfolios`, `get_portfolio_state`, `list_strategies`, `get_strategy`, `list_backtests`, `get_backtest_result`, `list_active_strategies`, `get_activation`, `list_exploration_tasks`, `get_exploration_task`

The server is a stdio process — no network listener, no central state. Auths via `X-API-Key` against a deployed Zebu backend.

### Wave 2 — Write tools ([#242](https://github.com/TimChild/PaperTrade/pull/242))

10 write tools that close the loop:

- Strategy lifecycle: `create_strategy`, `run_backtest` (synchronous, polls until terminal), `activate_strategy`, `deactivate_activation`, `run_activation_now`
- Exploration-task queue: `create_exploration_task`, `claim_exploration_task` (atomic — agent intake), `submit_exploration_finding` (transitions to DONE), `abandon_exploration_task` (creator-only)
- Local: `note` (echo of a thought; suggests the right persistent path)

Total surface: **23 tools** under the `mcp__zebu__` namespace.

### Smoke test (2026-05-10)

End-to-end verified against `https://zebutrader.com`:

- API key minted via `POST /api/v1/api-keys` from a Clerk JWT
- Configured into a fresh Claude Code session via `~/.claude.json` `mcpServers.zebu` entry
- Tools loaded under `mcp__zebu__*`
- Read tools confirmed: `list_portfolios` returned existing portfolios, `get_current_price` returned latest tick with `is_stale: true` (2-day-old Friday close — markets closed Saturday/Sunday — surfaced correctly)
- Write tools confirmed: `create_strategy` (BUY_AND_HOLD on AAPL) + `create_exploration_task` (free-form prompt) — both visible in subsequent list calls

---

## Frontend revamp Waves 1+2 (2026-05-10)

Not in the original Phase A–G plan; emerged from real-world UX issues during Phase C. Replaced the legacy shadcn/Card aesthetic with a "dark-mode refined editorial" theme — Bloomberg Businessweek meets Stripe documentation.

### Wave 1 — Foundation + lighthouse PortfolioDetail ([#247](https://github.com/TimChild/PaperTrade/pull/247))

- Design tokens (`--canvas` `#0c1116`, paper-warm ink, amber accent, muted gain/loss, cool chart palette) in `frontend/src/index.css` + `frontend/tailwind.config.ts`
- Self-hosted fonts: **Fraunces Variable** (display), **IBM Plex Sans Variable** (body), **IBM Plex Mono** (numerics)
- 6 reusable primitives in `frontend/src/components/ui/`: `MetricStat`, `DataRow`+`DataTable`, `SectionHeader`, `Eyebrow`, `Caption`, `Panel`
- `PortfolioDetail.tsx` rewritten as the lighthouse application of the system

### Wave 2 — Spread across remaining surface ([#248](https://github.com/TimChild/PaperTrade/pull/248))

- 8 pages rewritten: Dashboard, Strategies, Activations, Backtests, BacktestResult, CompareBacktests, PortfolioAnalytics, NotFound
- 15 feature components retuned (portfolio/strategies/backtests/analytics)
- 8 shared primitives retuned (EmptyState, Dialog, ConfirmDialog, ErrorDisplay, LoadingSpinner, input, label, DataRow `onClick`)
- Heading-order accessibility fix surfaced and resolved (Dashboard's `<h3>` PortfolioCard names demoted to `<h2>` under page `<h1>`)

**Open issue carried forward**: Tim flagged on 2026-05-10 that Fraunces at `opsz: 144` is too hard to read on numeric display values (e.g. `+24.44%` in the RETURN MetricStat). Resolved in next forward proposal — see [`agent-platform-proposal.md`](agent-platform-proposal.md).

**Test deltas**: 358 → 386 unit tests passing; all E2E green; 0 lint errors.

---

## Production stabilization fixes (2026-05-10)

Side-quests that surfaced during Phase C / D landings:

| PR | What |
|---|---|
| [#240](https://github.com/TimChild/PaperTrade/pull/240) | Align production runtime COPY paths with `python:3.13` base (Dockerfile line 68 was hardcoded to `python3.12` after the Phase B Python upgrade in #234) |
| [#243](https://github.com/TimChild/PaperTrade/pull/243) | Propagate `API_KEY_HMAC_SECRET` to backend container (caused 500s on prod when missing — fail-fast worked correctly) |
| [#244](https://github.com/TimChild/PaperTrade/pull/244) | Show loading state on price chart (was flashing "Data Not Found" empty-state during refetch) — also lifted timeframe to a shared Zustand store with persist middleware so all charts share the selected range |
| [#245](https://github.com/TimChild/PaperTrade/pull/245) | `frontend-swe` agent references the `frontend-design` skill |
| [#246](https://github.com/TimChild/PaperTrade/pull/246) | Align portfolio total-value across detail / analytics / composition views (live balance vs daily-snapshot were drifting) |

---

## Decisions resolved during execution

These were Q1–Q7 in the original proposal — included here for the record:

| # | Question | Resolution |
|---|---|---|
| Q1 | MCP topology — local-stdio first? | ✅ **YES** — shipped as in-tree stdio under `mcp/`. Sidecar on personal Proxmox is the next step if remote attach is needed |
| Q2 | API-key vs M2M Clerk for agent auth? | ✅ **API key** — Clerk-gated mint at `POST /api/v1/api-keys`, HMAC-SHA256 hashed, `read`/`trade`/`admin` scopes |
| Q3 | Should `.github/agents/*` stay or be deleted after migration? | ✅ **DELETED** in Phase A |
| Q4 | Agent runtime: scheduled remote vs. local `/loop`? | Deferred; resolved in next proposal — manual today, scheduled tomorrow |
| Q5 | OSS-readiness for agent-platform design? | ✅ Designed accordingly — no hard-coded secrets, env-var config |
| Q6 | Where to host MCP sidecar — personal Proxmox or `*.apps.exowatt.com`? | ✅ **Personal Proxmox ONLY**. Codified in `user_zebu_is_personal.md` |
| Q7 | `ExplorationTask` scope — free-form prompts or constrained schema? | ✅ Free-form prompts; constraints are optional structured guardrails |

---

## What's still open

What's NOT done from the original plan:

- **Phase D Wave 3** — research-context tools (`web_search`, `fetch_news`, etc.). Recommended in next proposal: defer in favour of attaching existing third-party MCPs (Brave, Tavily, etc.) rather than building our own.
- **Phase E** — agent-authored strategies (parameter sweeps + new types via PR). Mostly agent behavior, light infra.
- **Phase F** — long-running scheduled-agent harness + `StrategyConditionTrigger` (agent-in-the-loop strategies).
- **Phase G** — GUI for agent observability.

Plus new gaps that surfaced during this work:

- **Agent loop UX**: `ExplorationTask` UI page, recent-activity feed on dashboard, API-key minting page (so we don't need the JWT-from-console dance), agent operating manual.
- **Multi-agent identity**: separate API keys per agent role (explorer / backtester / strategist) with the API-key label surfaced everywhere.
- **Display font tweak**: Fraunces at `opsz: 144` is hard to read for numerics.

These are the inputs to the new proposal in [`agent-platform-proposal.md`](agent-platform-proposal.md).
