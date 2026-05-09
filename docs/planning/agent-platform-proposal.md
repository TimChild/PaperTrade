# Proposal: Agent Platform — Modernizing Zebu for Agent-Driven Trading

**Status**: Draft (proposal) — **Phase A complete (2026-05-09)**
**Author**: Tim Child (with Claude Opus 4.7)
**Created**: 2026-05-09
**Supersedes**: `roadmap.md` § "Phase 5: Automation & Advanced Analytics" (loose sketch)

> **Status update — 2026-05-09**: Phase A (Claude infra modernization) has shipped in this same session.
>
> - `CLAUDE.md` bootstrapped at the repo root
> - 7 specialist agents migrated to `.claude/agents/`
> - 6 procedural skills created under `.claude/skills/` (`before-starting-work`, `quality-checks`, `git-workflow`, `e2e-qa-validation`, `docs-tidy`, `orchestrate-zebu`)
> - Architecture principles extracted to `docs/architecture/principles.md`
> - Project memory bootstrapped (6 entries under `~/.claude/projects/-Users-timchild-github-PaperTrade/memory/`)
> - Old Copilot infra removed: `.github/copilot-instructions.md`, `.github/agents/`, `agent_docs/reusable/`, `agent_docs/orchestration-guide.md`
> - Stale-state cleanup: `resume-from-here.md` deleted, test counts reconciled to 831/311/1142, roadmap restructured (Phase 4 → ✅ complete; Phase 5 → this proposal)
>
> **Next**: §8 recommends Phase C (read-only MCP prototype) next, but Phase B (Task #210 + API-key auth + ExplorationTask) is the alternative starting point if you'd rather land write-side capability first.

---

## TL;DR

Zebu is a healthy, deployed v1.0.0 platform with strong agent-orchestrated dev practices — but those practices were built for **GitHub Copilot Coding Agents** (PR-by-PR work), not for **Claude Code** (interactive, MCP-aware, scheduled). To get to "long-running agents trying out trading strategies, with the app as the human-facing GUI," we need three workstreams that can run loosely in parallel:

1. **Modernize Claude infrastructure** (1–2 sessions) — bootstrap `CLAUDE.md`, migrate `.github/agents/` → `.claude/agents/`, codify reusable chunks as skills, fix internal staleness.
2. **Implement live strategy execution + machine identity** (Task #210, plus an API-key auth path) — already scoped in `agent_docs/tasks/210_live_strategy_execution.md`; extend it so agents can drive it, not just the scheduler.
3. **Build the agent-facing surface** — an MCP server on top of the existing FastAPI backend, plus a new "exploration task" concept so the human queues "go try X" via the GUI and agents pick those up.

Once those land we get the loop the user described: **human in GUI → "explore strategies for AAPL/MSFT"** → **looped/scheduled agents pick up tasks via MCP** → **agents iterate strategies, run backtests, optionally activate live** → **human reviews progress in GUI**.

This doc is the plan. It's structured as phases A–F so it can be picked off incrementally.

---

## 1. Where We Are (May 2026)

### Production state

- **Live**: zebutrader.com (Proxmox VM, `192.168.4.112`)
- **Version**: v1.0.0, Phase 4 (trading strategies + backtesting) complete
- **CD**: push-to-main auto-deploys via self-hosted runner `papertrade-proxmox`
- **Tests**: 831 backend + 311 frontend = 1,146 (March 8, 2026)
- **Open PRs / issues**: zero

### Code map (relevant to this proposal)

- API routers — `backend/src/zebu/adapters/inbound/api/{strategies,backtests,portfolios,prices,analytics,transactions}.py`
- Strategy entity — `backend/src/zebu/domain/entities/strategy.py`
- Strategy execution protocol — `backend/src/zebu/domain/services/strategies/protocol.py`
- BacktestExecutor (the "loop over days" pattern that live execution will mirror) — `backend/src/zebu/application/services/backtest_executor.py`
- Auth — `backend/src/zebu/adapters/auth/{clerk_adapter,in_memory_adapter}.py` (Bearer-only; no API keys)
- Scheduler — `backend/src/zebu/infrastructure/scheduler.py` (APScheduler, daily jobs already wired)

### Agent / dev infrastructure

| Lives in | What it is | Status |
|---|---|---|
| `.github/copilot-instructions.md` | Top-level instruction file for Copilot agents | Functional, but Copilot-flavored |
| `.github/agents/{architect,backend-swe,frontend-swe,qa,quality-infra,refactorer,docs-refactorer,copilot-instructions-updater}.md` | 7 role-specialist agent specs | Detailed but Copilot-flavored |
| `agent_docs/orchestration-guide.md` | The "think like a CTO" orchestration playbook | Strong content; lives away from Claude conventions |
| `agent_docs/reusable/*.md` (11 files) | Shared chunks: architecture-principles, before-starting-work, quality-and-tooling, etc. | Equivalent of skills; not loaded as skills |
| `agent_docs/tasks/*.md` (18 active + archive) | Numbered task specs (200, 202, 203, 204, 207, 208, 209, **210**) | Strong workflow; manual lifecycle |
| `agent_docs/progress/*.md` | Dated session reports | Equivalent of work-report partials |
| `agent_docs/mcp-tools.md` | MCP tools currently configured for Pylance/Container/GitHub | No backend MCP server yet |
| `.vscode/mcp.json` | MCP client config | VSCode-local |
| **No `CLAUDE.md`, no `.claude/`** | — | **Gap** |

### Velocity signals

- 444 commits in 6 months (Nov 2025 → May 2026)
- Production deployed in ~30 days from project start
- Zero open issues / PRs after March 8 — indicates **a 2-month dormancy gap**, which is exactly what the user described
- `BACKLOG.md` is short and accurate (March 8); `roadmap.md` was last updated Jan 26 and still lists Phase 4 as "Q2-Q4 2026 in progress" while `PROGRESS.md` says it's complete — **internal inconsistency**

---

## 2. The Vision

> Long-running (or looped / scheduled) agents try out various trading strategies via the API / MCP server. The app becomes the human-facing GUI — humans set things up, understand strategies, and see progress. Agents handle the strategy work and call the backend for the context they need.

Concretely, the daily loop should look like:

1. **Human (GUI)**: "I want to explore mean-reversion strategies on AAPL/MSFT/NVDA, with paper-trading portfolio P." → adds an `ExplorationTask` to the queue.
2. **Looped agent (Claude Code)**: wakes up, calls MCP `list_open_exploration_tasks`, picks one.
3. **Agent**: calls `get_price_history` / `get_portfolio_state` for context, designs a strategy variant, calls `run_backtest`, evaluates results.
4. **Agent**: if backtest looks good, optionally calls `activate_strategy` to put it into live paper-trading rotation; logs findings via `submit_exploration_finding`.
5. **Human (GUI)**: opens dashboard, sees: "Agent X tried 3 variants of MA-crossover on AAPL last night; #2 had 14% return vs 9% baseline; live-active on portfolio P."

That loop is the bare minimum the user described, and it has clean phase boundaries we can ship incrementally.

---

## 3. Gap Analysis — What Stops Us Today

### 3.1 Claude infra gap

There's no `CLAUDE.md`, no `.claude/`. Every Claude Code session starts cold with no project conventions loaded. The existing agent docs (`.github/agents/`, `agent_docs/reusable/`) are good content but not in the locations Claude Code surfaces automatically.

**Cost of inaction**: every session re-discovers the codebase; agent role specialization (backend-swe, frontend-swe, etc.) doesn't carry over; orchestration-guide is referenced but not loaded.

### 3.2 Programmatic-access gap

All API endpoints are gated by Clerk Bearer JWTs. There's no API-key path. Machine-to-machine Clerk is possible but awkward and would require either:

- Each agent obtaining a Clerk JWT via the M2M flow (operationally heavy), **or**
- A new auth path (API key) alongside Clerk

**Cost of inaction**: agents can't call the backend at all without a logged-in human's token, which defeats "long-running agents."

### 3.3 Live execution gap

Task #210 (`agent_docs/tasks/210_live_strategy_execution.md`) covers the scheduler-driven live execution path. It does **not** explicitly cover agent-driven execution (manual activation by an agent) or the "exploration task queue" concept. We should fold those into #210 or add a sibling task.

### 3.4 Strategy authorability gap

Today, only three hard-coded strategy types exist (`BUY_AND_HOLD`, `DOLLAR_COST_AVERAGING`, `MOVING_AVERAGE_CROSSOVER`). For agents to "try various strategies," either we expand the hard-coded set, or — more interestingly — we let agents author parameter combinations within an existing type *and* propose new strategy types as code (which then go through the normal PR pipeline). The first lane unlocks 80% of the value with 20% of the work.

### 3.5 Agent-observability gap

Grafana Cloud is wired for production logs but there's no view of "what has each agent tried, and how did it do." We need an agent-history view in the GUI fed by an `agent_runs` / `exploration_runs` table.

### 3.6 Stale-state markers (small but worth fixing)

- `resume-from-here.md` (March 8) — explicitly marked "delete after reading" but still present
- `roadmap.md` lists Phase 4 as in-progress when it's complete
- `PROGRESS.md` calls out 831 tests; `README.md` says 835+; `roadmap.md` says 796 — pick a source of truth
- BACKLOG admin-auth TODOs (analytics endpoints) — relevant once agents can hit the API

---

## 4. The Plan — Six Phases

Phases A–F. **A and the early parts of B/C can run in parallel** if you want (I'll flag where).

### Phase A — Modernize Claude infrastructure

**Goal**: Make a fresh Claude Code session productive in seconds, with role specialization and shared conventions auto-loaded.

**Tasks**:

A1. **Bootstrap `CLAUDE.md`** (project root) — single source of truth that links to:
- Architecture overview (delegates to `docs/architecture/README.md`)
- Tooling (`task` commands)
- Test layout
- Conventions (commit format, no `Any` / `any`, etc.)
- Where everything lives

A2. **Migrate `.github/agents/*` → `.claude/agents/*`**:
- Convert each role file (architect, backend-swe, frontend-swe, qa, quality-infra, refactorer, docs-refactorer) to a Claude Code agent definition with proper YAML frontmatter (name, description, model, tools).
- Trim Copilot-specific bits (e.g., `COPILOT_AGENT_ENVIRONMENT` checks); replace with Claude-Code-specific tool restrictions.
- Keep the architectural-compliance content — it's repo-agnostic gold.
- Leave `.github/agents/` for Copilot agents if you still use them; reference both from `CLAUDE.md`. **Don't delete eagerly.**

A3. **Promote `agent_docs/reusable/*` → `.claude/skills/`**:
- Each reusable chunk becomes a small skill with a `SKILL.md`.
- High value: `before-starting-work`, `quality-and-tooling`, `git-workflow`, `e2e_qa_validation`.
- These then auto-surface in the skill picker.

A4. **Codify the orchestration playbook** as a skill — `.claude/skills/orchestrate-zebu/SKILL.md`. Wraps the relevant parts of `agent_docs/orchestration-guide.md` (the rejection criteria, the parallel-execution safety rules, the task-creation workflow) so the orchestrator behavior is invokable, not just readable.

A5. **Fix staleness**:
- Delete `resume-from-here.md` (it explicitly says to)
- Reconcile test counts across PROGRESS / README / roadmap
- Update `roadmap.md` to reflect Phase 4 complete + this proposal as Phase 5

A6. **Add a project memory bootstrap** — write the first round of `~/.claude/projects/-Users-timchild-github-PaperTrade/memory/` entries so future sessions have user/project/reference memories pre-loaded (architecture choice rationale, prod URL, agent-doc conventions).

**Effort**: 1 working session (an afternoon).
**Owner**: Claude Code (interactive, with you steering).
**Risk**: Low — additive; nothing breaks.
**Parallelizable with**: Phase B early steps.

### Phase B — Live strategy execution + machine identity

**Goal**: Land Task #210 *and* give agents a way to authenticate.

**Tasks**:

B1. **Implement Task #210 as currently scoped** — domain entity, repo, scheduler job, API endpoints, frontend UI.
- Per the existing task file, this is 4 phases inside #210. Backend SWE first, then frontend.

B2. **Add API-key auth path** alongside Clerk:
- New `AuthPort` implementation `ApiKeyAuthAdapter` that maps a hashed key → `AuthenticatedUser`
- Stored in a new `api_keys` table (Alembic migration)
- The middleware tries `Authorization: Bearer <jwt>` (Clerk) first, falls back to `Authorization: ApiKey <key>` or `X-API-Key: <key>`
- New endpoints (Clerk-gated) for the human to mint/revoke keys: `POST /api-keys`, `GET /api-keys`, `DELETE /api-keys/{id}`
- Each key carries a label and scopes — at minimum `read`, `trade`, `admin`

B3. **Manual `run-now` endpoint surfaces an "agent-triggered" path** — Task #210 already includes `POST /activations/{id}/run-now`; ensure it's invokable with API-key auth (not just Clerk).

B4. **`ExplorationTask` entity & queue** (the new thing this proposal adds beyond #210):
- A new domain entity representing "human-queued exploration request" — fields: `id`, `created_by`, `target_portfolio_id`, `tickers`, `notes` (free-form prompt for the agent), `constraints` (e.g., "MA-crossover only", "max 5 backtests"), `status` (`open|in_progress|done|abandoned`), `claimed_by` (agent identifier), timestamps.
- Endpoints: `POST/GET/DELETE /exploration-tasks`, `POST /exploration-tasks/{id}/claim`, `POST /exploration-tasks/{id}/findings`.
- This is **the** key new abstraction — without it, agents have no input from the human.

**Effort**: ~1–2 weeks (Task #210 alone is multi-day; B2/B4 add ~3–4 days).
**Owner**: Backend SWE agent (parallel sub-tasks: #210 in flight, B2 + B4 as new sibling tasks).
**Risk**: Medium — touches auth and adds a new domain concept.
**Parallelizable with**: Phase A; parts of Phase C can begin once B2 lands.

### Phase C — MCP server

**Goal**: Expose the backend as named MCP tools so Claude Code agents can call it directly.

**Tasks**:

C1. **Decide MCP topology**. Options:

| Option | What | Pros | Cons |
|---|---|---|---|
| **In-tree** | MCP server inside the existing FastAPI repo as a separate process (`backend/src/zebu/adapters/inbound/mcp/`) | Shares domain code, single deploy | Adds runtime complexity to a stable service |
| **Sidecar repo** | A small standalone repo (`zebu-mcp`) that calls the backend via HTTP using API key | Clean separation, can be developed independently, easy to deploy as a `*.apps.exowatt.com`-style internal app | Two services to deploy |
| **Thin local-only MCP** | Stdio-based MCP that runs on the developer's machine and proxies to `https://zebutrader.com` with a personal API key | Zero infra change; instantly usable | Can't be shared, no central state |

**Recommendation**: start **(c) thin local-only**, graduate to **(b) sidecar** once we know what tools we actually want. (a) is over-engineering until proven.

C2. **MCP tools** (first cut — the surface area an agent actually needs):

Read tools:

- `list_supported_tickers`
- `get_price_history(ticker, start, end, interval)`
- `get_portfolio_state(portfolio_id)`
- `list_strategies()`, `get_strategy(id)`
- `list_backtests(strategy_id)`, `get_backtest_result(id)`
- `list_active_strategies()`
- `list_exploration_tasks(status?)`, `get_exploration_task(id)`

Write tools:

- `create_strategy(type, params, tickers, name)`
- `run_backtest(strategy_id, start, end, initial_cash)`
- `activate_strategy(strategy_id, portfolio_id, frequency)` / `deactivate_strategy(activation_id)`
- `claim_exploration_task(task_id)` / `submit_exploration_finding(task_id, summary, links)`
- `note(text)` — freeform note attached to an exploration run, for the human dashboard

C3. **Build it with the `claude-api` skill** patterns and document the auth flow (uses an API key minted in B2).

C4. **Integration test** — a smoke test that runs the MCP server locally, connects from Claude Code, lists supported tickers, and runs one backtest end-to-end.

**Effort**: 2–3 days.
**Owner**: Claude Code (you + me) — this is the kind of work that benefits from interactive iteration.
**Risk**: Low — additive, behind an API key, doesn't affect production traffic.
**Parallelizable with**: tail end of Phase B.

### Phase D — Agent-authored strategies (parameter sweep first)

**Goal**: Let agents actually generate value by exploring within the existing strategy types.

**Tasks**:

D1. **Parameter sweep in the existing strategy types** — agents propose `(fast_window, slow_window, invest_fraction)` combinations for MA-crossover; `(frequency_days, amount_per_period, allocation)` combinations for DCA; etc. Run backtests, compare. This is *just* using existing APIs — no new domain code.

D2. **Strategy comparison report** as a new `submit_exploration_finding` payload type — structured output the GUI can render.

D3. **Optional**: define a "strategy proposal" workflow where an agent that wants to try a *new* strategy type drafts a PR (using the backend-swe role agent from Phase A) that adds a new `StrategyType` enum value + handler. Goes through the normal review pipeline. This naturally bounds agent capability — they can iterate freely on parameters but new strategy types still get human review.

**Effort**: 1 week of agent-loop time (mostly running, not coding).
**Owner**: Looped Claude Code agent.
**Risk**: Low — bounded by the existing strategy types and backtest engine.
**Depends on**: Phase B (#210 + ExplorationTask) and Phase C (MCP).

### Phase E — Long-running agent harness

**Goal**: Decide how the agents *actually* run on a recurring basis.

**Tasks**:

E1. **Pick a runtime model**. Options:

- **`/loop` interval** on a developer machine — quickest to set up, ties up that machine
- **`/loop` dynamic** with `ScheduleWakeup` — model-paced, better for "check back later when something is queued"
- **Scheduled remote agent** (`/schedule`) on Anthropic infrastructure — runs without local machine; this is closest to the user's "long running agent" intent
- **Cron-driven local Claude Code via Claude Agent SDK** — most control, more setup

**Recommendation**: scheduled remote agents (`/schedule`) for the production loop, with `/loop` for ad-hoc local runs while iterating.

E2. **First scheduled agent**: `zebu-strategy-explorer`
- Runs every 6 hours (or daily after market close)
- Pulls open `ExplorationTask`s from the MCP, claims one, executes parameter sweep, submits findings
- On error, surfaces it via `note()` so the human sees it next time they open the GUI

E3. **Concurrency / safety guardrails**:
- Tasks must be `claim`ed (atomic) so two agents don't fight for the same one
- Per-agent rate limits on backtest creation (so a runaway agent doesn't fill the DB)
- A "kill switch" env var or admin endpoint that disables `claim_exploration_task`

**Effort**: 2–3 days once Phase D works.
**Owner**: Claude Code + you (deciding cadence and guardrails).
**Risk**: Medium — first time we have non-interactive agents writing data into the system, even if it's paper money.

### Phase F — GUI for agent observability

**Goal**: Close the loop — the human can see what agents have done.

**Tasks**:

F1. **Agent-runs view** in the frontend — list `ExplorationTask`s, their status, the agent that claimed each, and the findings.

F2. **Strategy comparison view** — already exists for backtests (PR #207). Extend it to show "this strategy was authored by agent X exploring task Y" so the provenance is visible.

F3. **Activity timeline** — for a given portfolio, show all agent-driven actions chronologically. Backed by existing transaction history + new agent-runs metadata.

F4. **Manual "ask an agent" button** — file an `ExplorationTask` directly from the GUI without going through MCP. This makes the human ↔ agent loop tight.

**Effort**: 1 week of frontend work.
**Owner**: Frontend SWE agent.
**Depends on**: Phases B + D for data; Phase A for the `.claude/agents/frontend-swe` to be in good shape.

---

## 5. Quick Wins (this session, if you want)

These are small, low-risk, and unblock everything else:

- [ ] **Delete `resume-from-here.md`** — it explicitly says to delete after reading.
- [ ] **Bootstrap `CLAUDE.md`** at the repo root (Phase A1).
- [ ] **Create the first project memory entries** (Phase A6).
- [ ] **Update `roadmap.md`** to mark Phase 4 complete and link to this proposal as Phase 5 candidate.
- [ ] **Reconcile test counts** in PROGRESS / README (one source of truth).
- [ ] **Add this proposal to the docs site nav** (`mkdocs.yml`).

If we do nothing else today, those six are an hour of work and leave the project measurably cleaner.

---

## 6. Open Questions / Decisions for You

These are real choice points — I have a recommendation on each but want your call before committing:

1. **MCP topology** — local-stdio first, sidecar later? *(my rec: yes)*
2. **API-key vs M2M Clerk** for agent auth? *(my rec: API key — simpler, single-user app)*
3. ~~Should `.github/agents/*` stay or be deleted after migration to `.claude/agents/`?~~ **DECIDED 2026-05-09**: deleted, along with `.github/copilot-instructions.md`. Single source of truth in `.claude/`.
4. **Agent runtime**: scheduled remote agents vs. local `/loop`? *(my rec: remote for production, local for iteration)*
5. **Open-source plan** — `roadmap.md` mentions possibly OSS in 2027. Should the agent platform be designed with that in mind (avoid hard-coding personal API keys, etc.)? *(my rec: design as if OSS-ready; it's mostly free)*
6. **Proxmox vs apps.exowatt.com** for the MCP sidecar (when we get to Phase C option b) — do you want it in your existing Proxmox setup, or deployed as a `*.apps.exowatt.com` internal app?
7. **Scope of "exploration tasks"** — should they be user-defined free-form prompts ("agent, do something interesting") or constrained to a known schema (ticker list + strategy-type whitelist + budget)? *(my rec: constrained schema first; expand later)*

---

## 7. Refactor Map (Phase A specifics)

For when we sit down to do Phase A, here's the move map:

| From | To | Notes |
|---|---|---|
| `.github/copilot-instructions.md` | `CLAUDE.md` (new) + keep original for Copilot | Cross-link |
| `.github/agents/architect.md` | `.claude/agents/architect.md` | Add YAML frontmatter, trim Copilot bits |
| `.github/agents/backend-swe.md` | `.claude/agents/backend-swe.md` | Same |
| `.github/agents/frontend-swe.md` | `.claude/agents/frontend-swe.md` | Same |
| `.github/agents/qa.md` | `.claude/agents/qa.md` | Same |
| `.github/agents/quality-infra.md` | `.claude/agents/quality-infra.md` | Same |
| `.github/agents/refactorer.md` | `.claude/agents/refactorer.md` | Same |
| `.github/agents/docs-refactorer.md` | `.claude/agents/docs-refactorer.md` | Same |
| `.github/agents/copilot-instructions-updater.md` | drop or refactor as `.claude/agents/instructions-updater.md` | Was Copilot-meta; could become a skill |
| `agent_docs/reusable/architecture-principles.md` | `.claude/skills/architecture-principles/SKILL.md` | |
| `agent_docs/reusable/before-starting-work.md` | `.claude/skills/before-starting-work/SKILL.md` | |
| `agent_docs/reusable/quality-and-tooling.md` | `.claude/skills/quality-checks/SKILL.md` | |
| `agent_docs/reusable/git-workflow.md` | `.claude/skills/git-workflow/SKILL.md` | |
| `agent_docs/reusable/e2e_qa_validation.md` | `.claude/skills/e2e-qa-validation/SKILL.md` | |
| `agent_docs/reusable/agent-progress-docs.md` | `.claude/skills/progress-docs/SKILL.md` | |
| `agent_docs/reusable/session_handoff.md` | replace with project-memory entries | Native equivalent |
| `agent_docs/reusable/integration-plan.md` | keep in `agent_docs/` (cross-cutting reference) | |
| `agent_docs/reusable/docs_tidy.md` | `.claude/skills/docs-tidy/SKILL.md` | |
| `agent_docs/orchestration-guide.md` | `.claude/skills/orchestrate-zebu/SKILL.md` (subset) + keep doc | Keep the long-form doc; skill is the executable subset |
| `agent_docs/tasks/` | keep as-is | Mature workflow; don't disrupt |
| `agent_docs/progress/` | optional alignment with `work-report:partial-report` skill | Low priority |

Migration policy: **copy first, delete later** — don't remove `.github/agents/*` until we've used the `.claude/` versions for a few sessions and confirmed they work.

---

## 8. What I'd Start With (recommendation)

**Phase A is done** as of 2026-05-09 (see status callout at the top). The next session can pick up either of two starting points:

- **Phase C (MCP read-only prototype)** — *recommended*. A thin local-stdio MCP exposing the read tools (`list_strategies`, `get_portfolio_state`, `get_price_history`, `list_backtests`) lets us validate the agent-loop ergonomics with zero risk *before* Task #210 lands write capabilities. That feedback should shape #210's API.
- **Phase B (Task #210 + API-key auth + ExplorationTask)** — if you'd rather get the live-execution machinery done first and then layer the MCP on top.

Personal pick: **Phase C → Phase B → Phase D → Phase E → Phase F**.

---

## Appendix — Key file pointers

- This proposal: `docs/planning/agent-platform-proposal.md`
- Existing phase plan template: `docs/planning/phase4-technical-plan.md`
- Live-exec task spec: `agent_docs/tasks/210_live_strategy_execution.md`
- Auth code: `backend/src/zebu/adapters/auth/`, `backend/src/zebu/adapters/inbound/api/dependencies.py`
- Strategy domain: `backend/src/zebu/domain/entities/strategy.py`, `backend/src/zebu/domain/services/strategies/protocol.py`
- Backtest engine: `backend/src/zebu/application/services/backtest_executor.py`
- Scheduler: `backend/src/zebu/infrastructure/scheduler.py`
