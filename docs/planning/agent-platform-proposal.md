# Proposal: Agent Platform — From "Plumbing Works" to "Daily Loop is Pleasant"

**Status**: Draft (proposal) — picks up from [`agent-platform-completed.md`](agent-platform-completed.md)  
**Author**: Tim Child (with Claude Opus 4.7)  
**Created**: 2026-05-10  
**Supersedes**: [`archive/agent-platform-proposal-2026-05-09.md`](archive/agent-platform-proposal-2026-05-09.md) (the original A→G plan)

---

## TL;DR

The plumbing is in place: API-key auth, 23 MCP tools, ExplorationTask queue, live execution, and an editorial-themed dashboard — all deployed and end-to-end smoke-tested against `https://zebutrader.com` on 2026-05-10. **An AI agent can already use Zebu via MCP today.**

What remains is the difference between "it technically works" and "the daily loop is pleasant enough that I actually use it":

- **Phase H** (new) — Agent loop UX: `ExplorationTask` page, recent-activity feed, API-key management UI, agent operating manual, multi-agent-identity prep
- **Phase I** (new) — Display font fix + minor UX polish surfaced during real use
- **Phase E** (carry-over) — Parameter-sweep agent behavior; lightly assisted by a small finding-listing API
- **Phase F** (carry-over) — Long-running scheduled-agent harness + `StrategyConditionTrigger` (agent-in-the-loop strategies)
- **Phase G** (carry-over) — Observability dashboard for agent activity (subsumed partially by Phase H)
- **Phase D Wave 3** (deferred) — Research-context tools — recommend attaching existing third-party MCPs rather than building our own

Recommended ordering: **H → I → E → F → G**. H is the fastest unlock — once it's in place we have a real daily loop, even if the agent is still manually triggered.

---

## 1. Where We Are (May 2026)

### What works today

- API-key auth: agent mints a key from a Clerk JWT (`POST /api/v1/api-keys`), authenticates via `X-API-Key`
- 23 MCP tools across read + write under `mcp__zebu__*` namespace — see [`agent-platform-completed.md`](agent-platform-completed.md)
- ExplorationTask backend: `POST /exploration-tasks`, `claim`, `findings`, `abandon` lifecycle
- Live strategy execution: scheduler tick + on-demand `run-now`
- Dashboard with editorial dark theme across all pages
- Production deployed at `https://zebutrader.com`

### Today's daily loop, manually triggered

1. Tim opens a Claude Code session attached to the `zebu` MCP server
2. Asks the agent for something: "explore momentum strategies on AAPL for 2024", "backtest these 5 variants", "activate the best one on portfolio P with $1000"
3. Agent calls MCP write tools → Zebu API → state changes
4. Tim opens `https://zebutrader.com` to see results

**This loop works as of 2026-05-10.** The friction points below are the things that slow it down or hide what's happening.

### Friction points surfaced during smoke test

1. **API-key minting via JWT-from-browser-console is awful.** Need a settings page in the dashboard.
2. **No `ExplorationTask` UI.** The agent ↔ human queue is the most important new abstraction we built and it has zero dashboard presence. Tim has to use the API or MCP to see what's queued.
3. **No "recent agent activity" view.** Tim can see *outcomes* (trades, backtests, activations) but can't tell "the agent ran these three things in the last hour" at a glance.
4. **No agent operating manual.** Each Claude Code session starts cold without a clear sense of "what is this agent supposed to do, with what guardrails, when should it ask vs proceed."
5. **Single-key-only identity.** Tim was clear we want separate keys per agent role eventually (explorer / backtester / strategist). Today everything routes to a single key labelled `claude-code-laptop-smoke`.
6. **Display font legibility.** Fraunces at `opsz: 144` is too hard to read on numeric values like `+24.44%` (Tim flagged on 2026-05-10).

### What's deferred from the original plan and why

- **Phase D Wave 3 (research-context tools)**: building our own `web_search` / `fetch_news` is reinventing wheels. Several mature MCP servers exist (Brave Search, Tavily, the Anthropic-hosted news/web tools). The agent can attach those alongside `zebu` and use them directly — no Zebu code required.
- **Phase F (long-running harness)**: Tim's preference is "manual today, loop soon." Daily scheduled remote agents come after Phase H makes the loop ergonomic.

---

## 2. The Daily Loop We're Building Toward

This is what should be true after Phases H–F land:

1. **Tim files an ExplorationTask via the dashboard** (no MCP needed): "Try mean-reversion variants on the FAANG basket for 2023–2024, paper-trade the best one on Mar-2026 portfolio with $5K."
2. **A scheduled agent (Phase F) wakes daily after market close**, claims open tasks, calls Zebu MCP tools to gather data, uses third-party MCPs (Brave / news) for context, runs backtest sweeps (Phase E), evaluates results.
3. **For interesting cases, the agent activates the strategy** with a `StrategyConditionTrigger` attached: "wake me up if drawdown > 5% over 3 days, or if NVDA earnings comes within 2 trading days — I'll decide whether to hold."
4. **Tim opens the dashboard at any time** and sees:
   - Open + claimed + done ExplorationTasks (Phase H)
   - Recent agent activity timeline (Phase H)
   - Active strategies and their attached triggers (Phase G)
   - Trigger-fire log: "Trigger fired 2026-05-12 09:42 UTC; agent decided HOLD because Q1 beat consensus by 8%" (Phase G)
5. **Tim files feature requests** via either:
   - GitHub Issues (the agent has `gh` CLI; Tim files in the browser) — for **platform / codebase improvements**
   - ExplorationTask (free-form prompt) — for **trading exploration requests**

The split between those two channels matters. ExplorationTasks are durable, dashboard-visible, and tied to specific portfolios / tickers. GH Issues are public, threaded, and tied to the codebase.

---

## 3. The Plan — Five Phases

### Phase H — Agent loop UX (NEW)

**Goal**: Make the agent ↔ human loop pleasant enough to use daily. This is the biggest near-term unlock.

**Tasks**:

H1. **`ExplorationTask` dashboard page**. List, filter (`open` / `claimed` / `done` / `abandoned`), create form, detail view showing prompt + claimed-by + findings. Both human and agent file tasks here. The agent claims and submits findings.

- Backend already exists; this is purely frontend.
- File a task → assign to a target portfolio / tickers / free-form prompt → save.
- Detail view shows the full lifecycle including the agent-submitted finding markdown when status transitions to DONE.
- **Owner**: `frontend-swe`.
- **Effort**: ~1 day.

H2. **Recent activity feed on dashboard home** (or a dedicated `/activity` page). Read-only aggregation of the last N events across:

- Trades executed (with the API-key label or "human" if Clerk-authenticated)
- Backtest runs created
- Strategies created / activated / deactivated
- Activations triggered (`run-now`)
- ExplorationTasks filed / claimed / done
- API keys minted / used
- The API-key label is the **identity column** — surfaces "agent activity" naturally if we name keys consistently (`claude-code-laptop-explorer`, etc.).
- **No new schema** — this is read-only over existing tables.
- **Owner**: `backend-swe` (small aggregation endpoint) + `frontend-swe`.
- **Effort**: ~1 day.

H3. **API-key management page** in dashboard settings. Mint, list, revoke. Replaces the JWT-from-console dance.

- `GET /api-keys` (already exists for listing — verify it's wired up)
- `POST /api-keys` from a settings page form (label + scope checkboxes)
- `DELETE /api-keys/{id}`
- Show `raw_key` exactly once after creation, with a clear "save now, won't be shown again" affordance.
- **Owner**: `frontend-swe` (small: re-uses existing endpoints).
- **Effort**: ~half a day.

H4. **Agent operating manual** at `docs/agents/operating-manual.md`. The canonical prompt the agent reads at session start. Covers:

- **Identity**: who the agent is, what API key label it should use
- **Tools available**: link to MCP tool reference, mention the third-party MCPs we're attaching
- **Guardrails**: paper-trading-only, daily churn limits per portfolio, when to ask Tim vs proceed, what scopes are required for write operations
- **Workflow**: how to claim ExplorationTasks, when to file new ones, when to file GitHub Issues for platform requests
- **Context bootstrap**: where to read about Zebu (CLAUDE.md, agent-platform-proposal.md, prior ExplorationTask findings)
- This is also what the multi-agent split (H5) builds on — each agent role gets its own section or its own derived doc.
- **Owner**: written by hand or by Claude Code interactively with Tim.
- **Effort**: ~half a day.

H5. **Multi-agent identity prep** (no behavior change yet — just designing for it). Audit places we hardcode "the API key" vs read the key's `label` from the request context:

- Verify `AuthenticatedUser` carries the API-key label all the way from auth → handler
- Verify the activity feed (H2) groups by label, not just user
- Verify the audit / log lines on each write endpoint include the label
- **Don't** build separate code paths per role yet — just make sure when we mint a second key (say `claude-code-laptop-strategist`), the existing observability hooks already differentiate it.
- **Owner**: `backend-swe` (audit + small fixes).
- **Effort**: ~half a day.

**Total Phase H**: ~3.5 days of focused work, parallelizable into ~1–2 days wall-clock with multiple agents.

**Risk**: Low. Mostly UI + small read endpoints over existing data.

---

### Phase I — Polish surfaced during real use (NEW)

**Goal**: Address the small-but-annoying things that came up during the smoke test and frontend revamp.

**Tasks**:

I1. **Display font legibility fix**. Fraunces at `opsz: 144` is high-stroke-contrast didone — beautiful for headings, hard to read on numerics like `+24.44%`. Three options to evaluate:

| Option | Effect | Effort |
|---|---|---|
| Lower `opsz` to ~36–48 in the `MetricStat` numeric variant | Reduces stroke contrast; keeps Fraunces | 30 min |
| Restrict serif to headings only; render display numbers in IBM Plex Mono at large sizes | Numbers become tabular and clear; serif still does eyebrow + heading work | 1–2 hrs |
| Swap display font entirely (EB Garamond, Source Serif 4 Display, or another humanist transitional) | More legible mid-contrast serif throughout | 2–3 hrs |

**Recommendation**: Try (a) first — cheapest, preserves design intent. If still too hard to read, go to (b). Reserve (c) for a later coherence pass.

- **Owner**: `frontend-swe`.
- **Effort**: 30 min – 3 hrs depending on path.

I2. **Sanity-check pass on the editorial revamp**. Tim has been using the dark theme for ~24 hrs as of Phase I scoping. Surface anything else that's annoyed him in real use, batch-fix.

- **Owner**: collect feedback, dispatch small fixes.

**Total Phase I**: ~half a day.

**Parallelizable with**: Phase H — different agents, different files.

---

### Phase E — Agent-authored strategies (carry-over from original plan)

**Goal**: Let agents generate value via parameter sweeps within existing strategy types. New types via PR is a separate ongoing capability.

**Tasks**:

E1. **Parameter sweep workflow**. Agent reads an `ExplorationTask`, generates N parameter combinations (`fast_window` × `slow_window` × `invest_fraction` for MA-crossover; `frequency_days` × `amount_per_period` for DCA), runs backtests in parallel via `mcp__zebu__run_backtest`, ranks by metric, recommends.

- **Pure agent behavior — no new Zebu code.** Just clear documentation in the agent operating manual (Phase H4) of how to do this efficiently (parallel `run_backtest` calls; what metrics matter; how to format the finding).

E2. **Structured `submit_exploration_finding` payload**. Today the finding is a free-form text body. Agents would benefit from a structured schema for:

- chosen `parameters` (typed dict matching the strategy type)
- key `metrics` (return, sharpe, max_drawdown, n_trades)
- `comparison_to_baseline` (vs the buy-and-hold equivalent)
- agent's qualitative `reasoning`
- `confidence` 0–1
- The dashboard then has structured data to render (instead of just a markdown blob).
- **Owner**: `architect` (entity design) + `backend-swe` (schema migration) + `frontend-swe` (rendering).
- **Effort**: ~1 day.

E3. **"New strategy type via PR" workflow** (already implicitly available — agent has `gh` CLI). Just document the convention in the operating manual: when you want a fundamentally new strategy type, draft a PR adding the `StrategyType` enum value + handler + tests, file an ExplorationTask flagged "blocked-on-PR" with the PR number, Tim reviews and merges, agent picks back up.

**Total Phase E**: ~1.5 days of structural work + ongoing agent-loop time. Most of the value comes for free once the operating manual (H4) is in place.

**Risk**: Low. Bounded by existing strategy types and the backtest engine.

**Depends on**: H1 (ExplorationTask UI), H4 (operating manual).

---

### Phase F — Long-running harness + agent-in-the-loop strategies (carry-over)

**Goal**: Move from "Tim manually triggers the agent" to "scheduled agent runs daily after market close."

**Tasks**:

F1. **Pick a runtime model**. Tim's current preference: manual today, loop soon. Recommendation:

- **Local `/loop dynamic`** for ad-hoc exploration during waking hours (e.g. `/loop /explore-tasks`) — model paces itself between checks, checks back when something changes
- **Anthropic-hosted scheduled remote agent** for daily after-market-close runs — runs without Tim's machine being on
- Both use the same `ZEBU_API_KEY` (or a separate role-keyed one per H5)

F2. **First scheduled agent**: `zebu-strategy-explorer`. Daily after US market close (e.g. 22:00 UTC). Calls `mcp__zebu__list_exploration_tasks(status='open')`, claims one, executes Phase E1 sweep, submits findings.

- **Effort**: ~1 day to wire up the schedule + the agent's prompt.

F3. **`StrategyConditionTrigger` domain concept** (the most interesting Phase F deliverable). New entity + scheduler integration:

- Entity fields: `id`, `activation_id` FK, `condition_type` (`DRAWDOWN_THRESHOLD` / `VOLATILITY_SPIKE` / `EARNINGS_PROXIMITY` / `CUSTOM_RULE`), `condition_params` dict, `agent_prompt` free-form, `cooldown` (don't re-fire within N hours), `last_fired_at`, `status`
- Evaluated by the scheduler each tick alongside `StrategyExecutionService`
- When a condition fires, **invokes a remote agent via the Anthropic Messages API** (or queues an urgent ExplorationTask) with the strategy + trigger context + `agent_prompt`
- Agent response: BUY / SELL / HOLD / modify-strategy / "needs human" (escalates to a dashboard notification)
- **Owner**: `architect` (entity + flow design) → `backend-swe` (implementation) → `frontend-swe` (configuration UI in Phase G).
- **Effort**: ~1 week.

F4. **Concurrency / safety guardrails**:

- Atomic `claim_exploration_task` (already implemented)
- Per-API-key rate limit on `run_backtest` (so a runaway agent doesn't fill the DB)
- Per-portfolio per-day cap on agent-initiated trade volume
- Kill-switch admin endpoint that disables `claim_exploration_task` and trigger-based agent invocation
- All agent-initiated transactions tagged with `api_key_id` and `exploration_task_id` / `trigger_id` for audit

**Total Phase F**: ~2 weeks. Scheduling is quick (F1 + F2 ≈ 2 days). `StrategyConditionTrigger` is the substantive new feature (~1 week). Guardrails (F4) woven throughout.

**Risk**: Medium-high — first time non-interactive agents make real (paper) trading decisions. Mitigations: full audit trail, kill switch, per-portfolio caps, paper-trading-only.

**Depends on**: Phase H (operating manual + observability so we can debug what the scheduled agent does).

---

### Phase G — Observability dashboard (carry-over, partially subsumed by Phase H)

**Goal**: Close the loop visually — every agent decision is visible and queryable.

Phase H delivers the basic versions of these (G1, G2 below). Phase G is the deeper version after Phase F lands.

**Tasks**:

G1. **Strategy provenance display**. On a strategy card or detail page, show: "authored by agent X on 2026-05-15, exploring task Y" + "has N agent-in-loop triggers." Backed by Phase H5 multi-agent identity work.

G2. **Trigger-fire log view** (the audit trail that makes Phase F trustworthy). Every time an agent-in-loop trigger fires, render: timestamp, condition that triggered, context passed to the agent, agent's response, resulting trade (if any). This is non-negotiable for trust in agent-in-loop.

G3. **Agent activity drill-down**. From the recent-activity feed (H2), click into "show me everything `claude-code-laptop-explorer` did this week."

G4. **"Ask an agent" button on dashboard**. Quick-file an ExplorationTask from a portfolio detail page or a strategy page. Pre-fills target portfolio / tickers from context.

**Effort**: 1–2 weeks of frontend work, sequenced after Phase F so we have data to render.

**Depends on**: Phase F (`StrategyConditionTrigger` data) + Phase H (foundations).

---

### Phase D Wave 3 — Research-context tools (DEFERRED)

**Original plan**: build `web_search`, `fetch_news`, `fetch_url`, `get_earnings_calendar` as Zebu MCP tools.

**Recommendation**: **Don't build these.** Several mature MCP servers exist that an agent can attach alongside `zebu`:

- **Brave Search MCP** — `web_search`, fully featured
- **Tavily MCP** — research-grade web search with summaries
- **Anthropic-hosted news / web tools** (when available)
- **Custom small MCPs** for specific data sources if needed (e.g., a SEC filing fetcher), but only if the third-party landscape doesn't already cover it

The agent operating manual (H4) should document which MCPs to attach for which tasks. This keeps Zebu's MCP surface focused on what only Zebu can answer (your portfolios, your strategies, your backtests) instead of duplicating commodity capabilities.

**If we ever need to revisit**: re-open this section with specific gaps (e.g., "no third-party MCP gives us the macro indicator we need").

---

## 4. Sequencing Recommendation

Order: **H → I → E → F → G**, with parallelization within each phase.

| Phase | Wall-clock | Critical-path | Parallelizable with |
|---|---|---|---|
| H | 1–2 days | Yes — unblocks daily use | Phase I |
| I | half a day | No | Phase H |
| E | ~1 day infra + ongoing agent time | After H | Phase D Wave 3 (deferred) |
| F | ~2 weeks | After E (operating manual + sweep workflow informs it) | — |
| G | 1–2 weeks | After F | Phase E2 |

**Smallest set of work that gives Tim a real daily loop**: just Phase H. Everything else is incremental capability on top of that foundation.

---

## 5. Open questions

| # | Question | Default |
|---|---|---|
| Q1 | API-key UI: where in the dashboard? Settings page, or a top-level `/api-keys` route? | Settings page (less prominent, cleaner) |
| Q2 | Should the activity feed (H2) show ALL events or only "interesting" ones (excluding routine `list_*` reads)? | Only writes + claims + activations — reads are noise |
| Q3 | Multi-agent identity: encoded only via API-key label, or do we want a typed `AgentRole` enum on the key? | Label-only for v1; enum in Phase F if we need it for routing |
| Q4 | Phase F runtime: Anthropic-hosted scheduled agents (`/schedule`) or self-hosted on Tim's Proxmox? | `/schedule` for production, `/loop` for iteration (per Q4 in original) |
| Q5 | `StrategyConditionTrigger` agent-prompt: free-form (per Q7 of original) or templated? | Free-form, with a recommended structure documented in operating manual |
| Q6 | Phase D Wave 3: confirm we're going third-party-MCPs route? | Yes (recommendation above) — re-open if specific gaps surface |

---

## Appendix — Key file pointers

- This proposal: `docs/planning/agent-platform-proposal.md`
- What shipped: `docs/planning/agent-platform-completed.md`
- Original 2026-05-09 framing: `docs/planning/archive/agent-platform-proposal-2026-05-09.md`
- MCP server: `mcp/` (in-tree)
- ExplorationTask backend: `backend/src/zebu/adapters/inbound/api/exploration_tasks.py` + domain entity
- API-key auth: `backend/src/zebu/adapters/auth/api_key_adapter.py`, `backend/src/zebu/adapters/inbound/api/api_keys.py`
- Live execution: `backend/src/zebu/application/services/strategy_execution_service.py`
- Frontend pages to extend: `frontend/src/pages/` (Activations.tsx is the closest model for a list-and-detail page)
- Memory: `~/.claude/projects/-Users-timchild-github-PaperTrade/memory/` (project_zebu_aesthetic_direction.md, project_phase_d_orchestration.md, etc.)
