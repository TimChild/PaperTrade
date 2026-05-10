# Proposal: Agent Platform — Modernizing Zebu for Agent-Driven Trading (ARCHIVED 2026-05-10)

**Status**: ARCHIVED — superseded by [`agent-platform-completed.md`](../agent-platform-completed.md) (what shipped) + [`agent-platform-proposal.md`](../agent-platform-proposal.md) (what's next)
**Author**: Tim Child (with Claude Opus 4.7)
**Created**: 2026-05-09 — preserved here as the original framing of the seven-phase A→G plan. Phases A–D Wave 2 shipped between 2026-05-09 and 2026-05-10; the new proposal picks up from there.
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

Zebu is a healthy, deployed v1.0.0 platform with strong agent-orchestrated dev practices — but those practices were built for **GitHub Copilot Coding Agents** (PR-by-PR work), not for **Claude Code** (interactive, MCP-aware, scheduled). The codebase shipped fast under earlier (less capable) agents, which means **structural debt and quality risks have probably accumulated** that are worth surfacing before adding major new feature surface. To get to "long-running agents trying out trading strategies, with the app as the human-facing GUI," we need four workstreams that can run loosely in parallel:

1. **Modernize Claude infrastructure** (✅ done 2026-05-09 — Phase A) — `CLAUDE.md`, `.claude/agents/`, `.claude/skills/`, removed Copilot-flavored duplication.
2. **Codebase health audit & foundation refactor** (Phase B — new) — multi-agent thorough audit of architecture, tests, CI flakiness, code quality, security, docs. Output: prioritized findings → critical fixes → foundation refactors. Treat it like a "team of senior SWEs joins the project" pass. **Important: this is foundational; agent-platform write-side work shouldn't ship until B's findings are addressed or accepted as known debt.**
3. **Live strategy execution + machine identity** (Phase C — Task #210, plus an API-key auth path) — already scoped in `agent_docs/tasks/210_live_strategy_execution.md`; extend so agents can drive it.
4. **Agent-facing surface** (Phases D–G) — MCP server, agent-authored strategies (parameter sweeps + **agent-in-the-loop strategies** that wake an agent on conditions to make decisions), long-running agent harness, GUI for observability.

Once those land we get the loop the user described: **human in GUI → free-form prompt: "explore mean-reversion on tech stocks, watch for FOMC reactions"** → **looped / scheduled agents pick up tasks via MCP** → **agents pull context (prices, holdings, news headlines, web search), iterate strategies, run backtests, optionally activate live with self-callbacks for ambiguous moments** → **human reviews progress in GUI**.

This doc is the plan. It's structured as phases A–G so it can be picked off incrementally.

---

## 1. Where We Are (May 2026)

### Production state

- **Live**: zebutrader.com (Proxmox VM, `192.168.4.112`)
- **Version**: v1.0.0, Phase 4 (trading strategies + backtesting) complete
- **CD**: push-to-main auto-deploys via self-hosted runner `papertrade-proxmox`
- **Tests**: 831 backend + 311 frontend = 1,142 (March 8, 2026)
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

1. **Human (GUI)**: free-form prompt — "I want to explore mean-reversion strategies on AAPL/MSFT/NVDA in paper-trading portfolio P, paying attention to recent earnings reactions." → adds an `ExplorationTask` to the queue.
2. **Looped agent (Claude Code)**: wakes up, calls MCP `list_open_exploration_tasks`, picks one.
3. **Agent gathers context broadly** — not just trading data:
   - Trading data: `get_price_history`, `get_portfolio_state`, `list_strategies`, `list_backtests`
   - Market context: news headlines, web search, earnings calendars, macro context
   - Past attempts: prior `ExplorationTask` findings on similar tickers / themes
4. **Agent designs and tests** strategy variants, calls `run_backtest`, evaluates results, iterates.
5. **Agent activates** — if a variant looks good, calls `activate_strategy` to put it into live paper-trading rotation. May configure the strategy with **self-callback conditions** (Phase E, agent-in-the-loop): "if drawdown > 5% over 3 days, or unusual volume spike, wake me up to investigate before executing the next signal."
6. **Agent logs findings** via `submit_exploration_finding`.
7. **Human (GUI)**: opens dashboard, sees: "Agent X tried 3 variants of MA-crossover on AAPL last night; #2 had 14% return vs 9% baseline; live-active on portfolio P with a self-callback on 5% drawdown."

That loop has clean phase boundaries we can ship incrementally — and the "agent-in-the-loop strategies" concept means agents aren't just *authors* of fully-autonomous rules, they can also stay involved at decision points where their judgment beats hard-coded logic.

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

Today, only three hard-coded strategy types exist (`BUY_AND_HOLD`, `DOLLAR_COST_AVERAGING`, `MOVING_AVERAGE_CROSSOVER`). For agents to "try various strategies," we have a progression of agent freedom levels — each unlocking more interesting behavior:

1. **Parameter sweeps within existing types** — agents iterate `(fast_window, slow_window, invest_fraction)` for MA-crossover, `(frequency_days, amount_per_period, allocation)` for DCA. Pure configuration, no code. **Cheapest, unlocks 60–70% of the early value.**
2. **Agent-in-the-loop strategies** — strategies that include conditions which trigger an *agent wake-up call* mid-execution. Examples:
   - "If drawdown > 5% over 3 days → wake me up to decide whether to keep holding or exit."
   - "If implied volatility spikes > 50% in 1 day on any holding → wake me up to investigate."
   - "If a holding's earnings are within 2 trading days → wake me up to decide BUY/SELL/HOLD."

   The strategy provides scaffolding (which tickers, which conditions, what context to pass); the *agent* handles the judgment at trigger time using the full breadth of tools (price history, news, web search, prior findings). This is the most interesting freedom lane — it gets us hybrid rule+judgment trading, which is closer to how a thoughtful human investor actually operates than either pure rules or pure agent-driven trading. **New domain concept needed: `StrategyConditionTrigger` (or similar) — a structured rule that fires an agent wake-up via MCP / scheduled remote agent.**

3. **Agent-authored new strategy types as code** — when an agent wants to try a fundamentally new strategy *type* (not just new parameters), it drafts a PR that adds a new `StrategyType` enum value + handler. Goes through normal review (`backend-swe` + `architect` agents). **Naturally bounds agent capability** — they can iterate freely on parameters and on agent-in-loop conditions, but new strategy types still get human review.

Phases E and F in the plan below ship these lanes progressively. Lane 1 (parameter sweeps) ships in Phase E using existing APIs. Lane 3 (new strategy types via PR) is an ongoing capability that opens up once Phase B's foundation refactors land. Lane 2 (agent-in-the-loop) ships in Phase F alongside the long-running agent harness — they're naturally coupled, since the harness IS the wake-up mechanism.

### 3.5 Agent-observability gap

Grafana Cloud is wired for production logs but there's no view of "what has each agent tried, and how did it do." We need an agent-history view in the GUI fed by an `agent_runs` / `exploration_runs` table.

### 3.6 Stale-state markers (small but worth fixing)

- `resume-from-here.md` (March 8) — explicitly marked "delete after reading" but still present
- `roadmap.md` lists Phase 4 as in-progress when it's complete
- `PROGRESS.md` calls out 831 tests; `README.md` says 835+; `roadmap.md` says 796 — pick a source of truth
- BACKLOG admin-auth TODOs (analytics endpoints) — relevant once agents can hit the API

---

## 4. The Plan — Seven Phases

Phases A–G. **A is done; B is foundational; C–G build the agent platform.** Some parallelism is possible (flagged per phase) but the recommended ordering for risk-management reasons is A → B → C → D → E → F → G.

### Phase A — Modernize Claude infrastructure ✅ DONE

Shipped 2026-05-09. See top-of-doc status callout for the file-by-file list. Bootstrapped `CLAUDE.md`, migrated 7 specialist agents to `.claude/agents/`, created 6 procedural skills under `.claude/skills/`, promoted Clean Architecture rules to a published doc, removed Copilot-flavored duplication, fixed staleness markers, bootstrapped project memory.

**Effort**: ~4 hours, one session.
**Risk**: Low — additive; nothing broken.

### Phase B — Codebase health audit & foundation refactor (NEW)

**Goal**: Treat this like a team of senior SWEs joining the project to do a thorough evaluation and any necessary refactor — get the project on a solid foundation before adding major new feature surface. The codebase shipped fast under earlier (less capable) agents, which means **structural debt and quality risks have probably accumulated**. Surface them, fix the critical ones, accept the rest as known debt.

**Tasks**:

B1. **Comprehensive multi-agent audit pass** — dispatch specialist agents in parallel against different audit dimensions, each producing a findings report under `agent_docs/audits/2026-05-NN/<dimension>.md`:

| Dimension | Agent | Focus |
|---|---|---|
| Architecture | `architect` | Clean Architecture compliance — find any Domain → Infrastructure leaks, missing repository ports, side effects in domain logic, primitive obsession |
| Backend code quality | `backend-swe` (audit mode) | Type-checker suppressions, `Any` usage, long methods, premature/missing abstractions, error handling patterns, async correctness |
| Frontend code quality | `frontend-swe` (audit mode) | `any` usage, `useEffect`-as-state-sync anti-patterns, ESLint suppressions, accessibility, key prop usage, data-testid coverage |
| Test quality & flakiness | `quality-infra` | Behavior-vs-implementation tests, mock placement (boundaries only?), flaky-test root causes, coverage of critical paths, test-pyramid balance |
| CI infrastructure | `quality-infra` | Why CI has been flaky — Tim flagged that **past flakiness was largely auth-related** (Clerk rate-limiting, token-passing in tests, etc.), so start there. Confirm the self-hosted runner (`papertrade-proxmox`) is materially faster than GitHub-hosted and that its logs are genuinely useful for agent debugging — if not, fix it. Cache strategy, parallelism, dependency caching, secret rotation, artifact lifecycle |
| Domain model | `architect` + `refactorer` | Entity naming, invariant enforcement, value-object opportunities, domain-language coherence |
| API design | `backend-swe` + `architect` | REST consistency, error response shape, pagination/filtering patterns, OpenAPI completeness |
| Security | `quality-infra` | Auth coverage (BACKLOG mentions admin-auth TODOs), input validation, output encoding, secret management, dependency vulnerabilities |
| Database | `backend-swe` | Migration history hygiene, index coverage (BACKLOG mentions transaction indexes), query performance hot spots, connection pooling |
| Documentation | `docs-refactorer` | Onboarding usability, runbook completeness, accuracy vs. current code, dead links, archive-vs-delete pass |
| Dependencies | `quality-infra` | Outdated packages, unused dependencies, security advisories, license compatibility |
| **Claude infrastructure** | `architect` + `docs-refactorer` (audit mode) | The new `CLAUDE.md`, `.claude/agents/`, `.claude/skills/` were a verbatim-ish migration from Copilot in Phase A. Where can each be tightened? Are agent definitions specific enough? Are skills granular enough? Are there workflows that should be promoted to new shared skills? Anything redundant with mature Claude Code patterns now available? **This is arguably the most crucial dimension** — these prompts shape every future agent session in this repo. Findings feed B7. |

Output: a single consolidated report at `agent_docs/audits/2026-05-NN/SUMMARY.md` with **prioritized findings** (P0 critical / P1 high / P2 medium / P3 nice-to-have). All findings cite specific files / lines.

B2. **P0 critical fixes** — anything that blocks future work or is actively broken (e.g., the persistent CI flakiness if we still have it; any architectural violations that would propagate into Phase C+ code; security gaps that matter once agents can hit the API).

B3. **High-value foundation refactors** — P1 findings selected for fixing now because (a) they make Phase C–G work easier or (b) they're cheap. Track the rest as P2/P3 backlog with explicit deferral notes.

B4. **Test-quality pass** — convert any obviously implementation-focused tests to behavior-focused. Move misplaced mocks. Eliminate flaky tests at root cause (don't just retry-mark them). Goal: zero skipped tests, zero quarantined tests, deterministic on every run.

B5. **CI / infra hardening** — based on B1 audit findings. Fix any flakiness root causes. Document the self-hosted runner setup so we'd know how to rebuild it. Add observability so future flakiness is diagnosable.

B6. **Documentation pass** — `docs-refactorer` agent: kill stale docs, archive chronological artifacts, sync onboarding doc with actual setup, fix all internal cross-links.

B7. **Claude-infra refresh + sync skill** (intentionally last in Phase B) — the `CLAUDE.md` / `.claude/agents/` / `.claude/skills/` content shipped in Phase A was a verbatim-ish migration from the Copilot originals. Now that B2–B6 have refactored the codebase substantially, the agent prompts should be re-tuned to the new state — **and the migration left them at "good enough" rather than "great"**. This is the chance to make them really sharp.

- **Re-tune each agent definition** against fresh examples from the post-refactor code. Drop instructions that no longer apply; add ones capturing newly-codified patterns; tighten language.
- **Identify recurring patterns** across agent definitions that should be promoted to new shared skills.
- **Look for gap skills** — workflows that recurred during B2–B6 audit / refactor work and should be codified for future reuse.
- **Trim / merge / split** agents whose responsibilities overlap awkwardly.
- **Build a `claude-infra-sync` skill** — runs on demand (and ideally on a schedule, e.g., end of every major phase) to detect drift in `CLAUDE.md` and agents (stale paths, broken file references, outdated test counts, removed endpoints, agent definitions referencing concepts that no longer exist), suggest skill candidates from observed patterns, and output a findings doc the user / `docs-refactorer` can act on. **The sync skill itself is the long-term insurance against Claude infra drifting from code reality** as Phases C–G evolve the codebase further.

**Owner**: orchestrator (Claude Code) dispatching the specialist agents above in parallel. Tim reviews the consolidated findings and signs off on what fixes get prioritized.

**Effort**: 2–4 weeks depending on findings volume. The audit pass (B1) is highly parallelizable (~1 session of orchestrator time + parallel agent runs). Critical fixes (B2), foundation refactors (B3), and the test/CI/docs/Claude-infra hardening passes (B4–B7) are the variable cost.

**Risk**: Medium — refactors can introduce regressions. Mitigated by: existing test suite as safety net, refactorer-agent constraint that all tests stay green, P0/P1 prioritization to avoid over-scope.

**Parallelizable with**: Phase A (already done). The **audit pass (B1) can run while early Phase C scoping happens**; but **B2/B3 critical fixes should land before Phase C/D ships** to avoid building new features on questionable foundations.

**Latitude**: this is the team's chance to do whatever it takes to get this codebase right. We're not yet deployed to external customers, so meaningful refactors and even short-term feature removal are on the table if they materially improve the foundation. The constraint is *direction*, not preservation: every change should make the codebase a stronger base for Phases C–G. Document any functionality removal in a `B-changes/removed-features.md` so it can be re-added intentionally later if missed.

### Phase C — Live strategy execution + machine identity

**Goal**: Land Task #210 *and* give agents a way to authenticate.

**Tasks**:

C1. **Implement Task #210 as currently scoped** — domain entity, repo, scheduler job, API endpoints, frontend UI.

- Per the existing task file, this is 4 phases inside #210. Backend SWE first, then frontend.

C2. **Add API-key auth path** alongside Clerk:

- New `AuthPort` implementation `ApiKeyAuthAdapter` that maps a hashed key → `AuthenticatedUser`
- Stored in a new `api_keys` table (Alembic migration)
- The middleware tries `Authorization: Bearer <jwt>` (Clerk) first, falls back to `Authorization: ApiKey <key>` or `X-API-Key: <key>`
- New endpoints (Clerk-gated) for the human to mint/revoke keys: `POST /api-keys`, `GET /api-keys`, `DELETE /api-keys/{id}`
- Each key carries a label and scopes — at minimum `read`, `trade`, `admin`

C3. **Manual `run-now` endpoint surfaces an "agent-triggered" path** — Task #210 already includes `POST /activations/{id}/run-now`; ensure it's invokable with API-key auth (not just Clerk).

C4. **`ExplorationTask` entity & queue** (the new thing this proposal adds beyond #210):

- A new domain entity representing "human-queued exploration request" — fields: `id`, `created_by`, `target_portfolio_id`, `tickers` (optional — could be empty for free-form), `prompt` (free-form user request — primary input), `constraints` (optional structured limits), `status` (`open|in_progress|done|abandoned`), `claimed_by` (agent identifier), timestamps.
- **Per resolved Q7**: prompt is **free-form from day one**, accepting initial limitations on what agents can act on. Constraints are optional structured guardrails (e.g., "don't activate live trading on this exploration"), not the primary input.
- Endpoints: `POST/GET/DELETE /exploration-tasks`, `POST /exploration-tasks/{id}/claim`, `POST /exploration-tasks/{id}/findings`.
- This is **the** key new abstraction — without it, agents have no input from the human.

**Effort**: ~1–2 weeks (Task #210 alone is multi-day; C2/C4 add ~3–4 days).
**Owner**: Backend SWE agent (parallel sub-tasks: #210 in flight, C2 + C4 as new sibling tasks).
**Risk**: Medium — touches auth and adds a new domain concept.
**Depends on**: Phase B critical/foundation fixes — don't build write-side auth on a foundation we know has gaps.
**Parallelizable with**: Phase D once C2 lands.

### Phase D — MCP server

**Goal**: Expose the backend as named MCP tools so Claude Code agents can call it directly.

**Tasks**:

D1. **Decide MCP topology**. Options (per resolved Q6: `*.apps.exowatt.com` is **off the table** — this is a personal project that must never touch company infra):

| Option | What | Pros | Cons |
|---|---|---|---|
| **In-tree** | MCP server inside the existing FastAPI repo as a separate process (`backend/src/zebu/adapters/inbound/mcp/`) | Shares domain code, single deploy | Adds runtime complexity to a stable service |
| **Sidecar repo on personal Proxmox** | A small standalone repo (`zebu-mcp`) that calls the backend via HTTP using API key, deployed alongside the existing zebu services on Tim's Proxmox VM | Clean separation; can be developed independently; durable URL for non-local consumers | Two services to deploy |
| **Thin local-only stdio MCP** | Stdio MCP that runs on the developer's machine and proxies to `https://zebutrader.com` with a personal API key | Zero infra change; instantly usable | Can't be shared, no central state |

**Recommendation**: start **(c) thin local-only**, graduate to **(b) sidecar on personal Proxmox** once we know what tools we actually want. (a) is over-engineering until proven.

D2. **MCP tools** (first cut — read tools should cover both **trading-data context** AND **broader research context**):

**Read tools — trading data**:

- `list_supported_tickers`
- `get_price_history(ticker, start, end, interval)`
- `get_portfolio_state(portfolio_id)`
- `list_strategies()`, `get_strategy(id)`
- `list_backtests(strategy_id)`, `get_backtest_result(id)`
- `list_active_strategies()`
- `list_exploration_tasks(status?)`, `get_exploration_task(id)`
- `list_findings(filter?)` — search prior `ExplorationTask` findings (lessons compounded)

**Read tools — broader research context** (per user feedback, agents need more than trading data):

- `web_search(query)` — proxy to a public web search provider (e.g., Brave or DuckDuckGo API) so agents can find context, headlines, analysis.
- `fetch_news(ticker?, since?, sources?)` — pull headlines tied to a ticker or general market news (e.g., via Alpha Vantage News & Sentiment API or similar)
- `fetch_url(url)` — fetch and clean a specific URL (research reports, SEC filings, etc.)
- `get_earnings_calendar(ticker?, date_range?)` — upcoming earnings dates for context
- *(future)* `get_sec_filing(ticker, type)`, `get_macro_indicator(name)`

These broader tools may live in a *separate* MCP server (composable) rather than the Zebu MCP — Claude Code can attach multiple MCP servers, so we don't have to bundle them. **Decision deferred** to D-execution time: bundle vs. compose.

**Write tools**:

- `create_strategy(type, params, tickers, name)`
- `run_backtest(strategy_id, start, end, initial_cash)`
- `activate_strategy(strategy_id, portfolio_id, frequency)` / `deactivate_strategy(activation_id)`
- `claim_exploration_task(task_id)` / `submit_exploration_finding(task_id, summary, links)`
- `note(text)` — freeform note attached to an exploration run, for the human dashboard

D3. **Build it with the `claude-api` skill** patterns and document the auth flow (uses an API key minted in C2).

D4. **Integration test** — a smoke test that runs the MCP server locally, connects from Claude Code, lists supported tickers, runs one backtest end-to-end.

**Effort**: 3–4 days for the trading-data MCP. Broader research tools add ~1–2 days each but can ship incrementally.
**Owner**: Claude Code (you + me) — interactive iteration.
**Risk**: Low — additive, behind an API key, doesn't affect production traffic.
**Parallelizable with**: tail end of Phase C (read-only tools can be built before Phase C's write capabilities ship).

### Phase E — Agent-authored strategies (parameter sweeps + new types via PR)

**Goal**: Let agents generate value by exploring within existing strategy types (Lane 1 from §3.4) and proposing new types as code (Lane 3). Lane 2 (agent-in-the-loop) ships in Phase F.

**Tasks**:

E1. **Parameter sweep in existing strategy types** — agents propose `(fast_window, slow_window, invest_fraction)` combinations for MA-crossover; `(frequency_days, amount_per_period, allocation)` combinations for DCA; etc. Run backtests, compare. Pure use of existing APIs — no new domain code.

E2. **Structured `submit_exploration_finding` payload** — agents return a typed result the GUI can render: chosen parameters, backtest summary metrics, comparison to baseline, agent's qualitative reasoning, confidence.

E3. **"New strategy type via PR" workflow** — when an agent wants to try a fundamentally new strategy type, it drafts a PR (using `backend-swe`) adding a new `StrategyType` enum value + handler + tests. Goes through the normal review pipeline. Naturally bounds agent capability: parameters / agent-in-loop conditions are free; new strategy types get human review. **Depends on Phase B foundation** so the agent isn't extending a shaky base.

**Effort**: 1 week of agent-loop time (mostly running, not coding).
**Owner**: Looped Claude Code agent.
**Risk**: Low — bounded by existing strategy types and backtest engine.
**Depends on**: Phase B (audit done), Phase C (Task #210 + ExplorationTask), Phase D (MCP).

### Phase F — Long-running agent harness + agent-in-the-loop strategies

**Goal**: Decide how agents *actually* run on a recurring basis, AND add the most interesting strategy capability — strategies that wake an agent on conditions to make decisions (Lane 2 from §3.4).

**Tasks**:

F1. **Pick a runtime model**. Options:

- **`/loop` interval** on a developer machine — quickest, ties up that machine
- **`/loop` dynamic** with `ScheduleWakeup` — model-paced, better for "check back later when something is queued"
- **Scheduled remote agent** (`/schedule`) on Anthropic infrastructure — runs without a local machine; closest to "long-running agent" intent
- **Cron-driven local Claude Code via Claude Agent SDK** — most control, more setup

**Recommendation**: scheduled remote agents (`/schedule`) for production loops, with `/loop` for ad-hoc local runs while iterating. (Per resolved Q4.)

F2. **First scheduled agent**: `zebu-strategy-explorer` — runs daily after market close, pulls open `ExplorationTask`s from the MCP, claims one, executes parameter sweep (Phase E1), submits findings.

F3. **`StrategyConditionTrigger` domain concept** — the new entity that makes Lane 2 work:

- Fields: `id`, `activation_id` (FK to `StrategyActivation`), `condition_type` (e.g., `DRAWDOWN_THRESHOLD`, `VOLATILITY_SPIKE`, `EARNINGS_PROXIMITY`, `CUSTOM_RULE`), `condition_params` (dict), `agent_prompt` (free-form: what should the woken agent investigate / decide?), `cooldown` (don't re-fire within N hours), `last_fired_at`, `status`.
- Evaluated by the scheduler each tick alongside the `StrategyExecutionService`.
- When fired, **invokes a remote agent via the Anthropic Agent API** (or queues an `ExplorationTask` flagged `urgent` for the next harness wake-up) with the strategy context, the trigger context, and the configured `agent_prompt`.
- The agent's response can be: BUY signal, SELL signal, HOLD, modify-strategy, or "needs human" (escalate to dashboard notification).

F4. **API + UI for configuring triggers** — when activating a strategy, user can attach one or more triggers from a library (cooldown, drawdown, vol spike, earnings) and add a free-form `agent_prompt`. Power-users can write custom-rule triggers.

F5. **Concurrency / safety guardrails**:

- Tasks must be `claim`-ed atomically so two agents don't fight for the same one
- Per-agent rate limits on backtest creation (so a runaway agent doesn't fill the DB)
- Per-portfolio per-day cap on agent-initiated trade volume
- "Kill switch" env var or admin endpoint that disables `claim_exploration_task` and trigger-based agent invocation
- All agent-initiated transactions tagged with `agent_id` and `exploration_task_id` / `trigger_id` for full audit trail

**Effort**: 1–2 weeks. F1+F2 are quick (2–3 days). F3+F4 are the substantive new feature (~1 week). F5 is woven through.
**Owner**: Claude Code (orchestrator) + `backend-swe` for F3 + `frontend-swe` for F4.
**Risk**: Medium-High — first time non-interactive agents make real (paper) trading decisions. Mitigations: full audit trail, kill switch, per-portfolio caps, paper-trading-only.
**Depends on**: Phases C, D, E.

### Phase G — GUI for agent observability

**Goal**: Close the loop — the human can see what agents have done.

**Tasks**:

G1. **Agent-runs view** — list `ExplorationTask`s, their status, the agent that claimed each, and the findings.

G2. **Strategy comparison view** extension — already exists for backtests (PR #207). Extend to show "this strategy was authored by agent X exploring task Y" and "this strategy has N agent-in-loop triggers" so provenance and decision-points are visible.

G3. **Activity timeline** — for a given portfolio, all agent-driven actions chronologically. Backed by transaction history + agent-runs metadata + trigger-fire log.

G4. **Manual "ask an agent" button** — file an `ExplorationTask` directly from the GUI without going through MCP. Tightens the human ↔ agent loop.

G5. **Trigger-fire log view** — show every time an agent-in-loop trigger fired, what the agent decided, why, and what trade (if any) resulted. The audit-trail surface that makes agent-in-loop trustworthy.

**Effort**: 1–2 weeks of frontend work.
**Owner**: Frontend SWE agent.
**Depends on**: Phases C + E + F for data; Phase A for the `frontend-swe` definition.

---

## 5. Quick Wins ✅ DONE

All shipped in the same 2026-05-09 session as Phase A:

- [x] Delete `resume-from-here.md`
- [x] Bootstrap `CLAUDE.md`
- [x] Create the first project memory entries
- [x] Update `roadmap.md` to mark Phase 4 complete and add Phase 5 pointing to this proposal
- [x] Reconcile test counts in PROGRESS / README / roadmap to 831 / 311 / 1,142
- [x] Add this proposal to the docs site nav (`mkdocs.yml`)

---

## 6. Decisions

Resolved on 2026-05-09 review pass:

| # | Question | Resolution |
|---|---|---|
| Q1 | MCP topology — local-stdio first, sidecar later? | ✅ **YES**: start with thin local-stdio, graduate to sidecar on personal Proxmox once tool surface stabilizes |
| Q2 | API-key vs M2M Clerk for agent auth? | ✅ **API key** — simpler, single-user-personal-project fits the model |
| Q3 | Should `.github/agents/*` stay or be deleted after migration? | ✅ **DELETED** — single source of truth in `.claude/`, no diverging instructions |
| Q4 | Agent runtime: scheduled remote vs. local `/loop`? | ✅ **Remote `/schedule` for production, `/loop` for iteration** |
| Q5 | OSS-readiness for agent-platform design? | ✅ **Design as if OSS-ready from day one** — no hard-coded personal credentials in code; secrets via env. Worth open-sourcing one day |
| Q6 | Where to host MCP sidecar (when we get there) — personal Proxmox or `*.apps.exowatt.com`? | ✅ **Personal Proxmox ONLY**. This is a personal side project on personal time; **must never touch company infrastructure** (no `*.apps.exowatt.com`, no shared Exowatt services). Codified in user-memory `user_zebu_is_personal.md` |
| Q7 | `ExplorationTask` scope — free-form prompts or constrained schema? | ✅ **Free-form prompts from day one**, accepting initial limitations on what agents can act on. Constraints are optional structured guardrails, not the primary input |

These decisions are baked into Phases B–G above.

**Remaining open**: none currently. New questions can be added back here if discovered during execution.

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

**Phase A is done.** The next priority is **Phase B (codebase health audit & foundation refactor)** — this is the user-flagged "team of senior SWEs joins the project" stream. Before adding the major new feature surface in Phases C–G, we need to know what structural debt and quality risks we're standing on, fix the critical ones, and accept the rest as known.

**Recommended ordering**: A → **B** → C → D → E → F → G.

Within Phase B, the most efficient first move is the **B1 audit pass** — it's highly parallelizable (specialist agents per dimension, all running concurrently) and produces the prioritized findings doc that drives everything else. Tim reviews the consolidated findings, decides what's P0/P1, and we go from there.

Possible parallelization:

- B1 (audit) is the gating step. Once findings exist, **B2/B3/B4/B5/B6 can run in parallel** with each other (different agents, different files).
- A small **Phase D read-only MCP prototype** could be built in parallel with later parts of Phase B if it doesn't interfere with refactor in flight — useful for validating the MCP ergonomics before Phase C decides API surface.

**Avoid**: starting Phase C (Task #210 + auth + ExplorationTask) before B2's P0 fixes are in. We don't want to ship live-execution and machine identity on a foundation we know has gaps.

---

## Appendix — Key file pointers

- This proposal: `docs/planning/agent-platform-proposal.md`
- Phase 4 architecture (canonical): `docs/architecture/phase4-trading-strategies.md`
- Live-exec task spec: `agent_docs/tasks/210_live_strategy_execution.md`
- Auth code: `backend/src/zebu/adapters/auth/`, `backend/src/zebu/adapters/inbound/api/dependencies.py`
- Strategy domain: `backend/src/zebu/domain/entities/strategy.py`, `backend/src/zebu/domain/services/strategies/protocol.py`
- Backtest engine: `backend/src/zebu/application/services/backtest_executor.py`
- Scheduler: `backend/src/zebu/infrastructure/scheduler.py`
