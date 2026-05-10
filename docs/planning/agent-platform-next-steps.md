# Agent Platform — Next Steps (post Phases H/I/E/F/G)

**Status**: Draft proposal — picks up after the Phase H/I/E/F/G orchestration cycle (PRs #249–#268, all merged 2026-05-10).  
**Author**: Tim Child (with Claude Opus 4.7)  
**Created**: 2026-05-10  
**Supersedes**: nothing — extends [`agent-platform-proposal.md`](agent-platform-proposal.md) (now fully executed) and [`agent-platform-completed.md`](agent-platform-completed.md).

---

## TL;DR

The trigger system is shipped end-to-end (entities → evaluator → Anthropic invocation → API → safety guardrails → smoke-test verification → UI). One real exploration task surfaced three issues, two of which are fixed in PR #270, one of which needs a data backfill on prod.

This doc captures **what's next** — three forward directions plus the carry-over gaps:

1. **Multi-provider agent invocation** — Gemini CLI alongside Anthropic, with optional desktop-Claude integration via the existing ExplorationTask queue.
2. **Agent-driven backtests** — run the trigger pipeline against historical data so we can evaluate agent judgment before paying for it in live execution. Substantial scope, real pitfalls (data leakage, cost, non-determinism).
3. **The follow-up sweep** — gaps from this cycle that need closing.

---

## 1. What's known to be broken or incomplete

### 1.1 Pre-fixed (PR #270)

The 2026-05-10 smoke-test ExplorationTask `450cb185` surfaced three issues on prod backtests; PR #270 (this branch) addresses two:

- **`POST /api/v1/backtests` returned 500 with empty body** — no operator signal. Now catches all exceptions, logs the stack via structlog, re-raises (so the next 500 produces a diagnosable backend log line).
- **`TickerNotFoundError` propagated as 500** — now mapped to 503 with a meaningful message.
- **Failed backtests still consumed rate-limit tokens** — `InboundRateLimiterPort.refund()` now exists and is called on every failure path (404 / 503 / catch-all 5xx).

### 1.2 Still open

**AAPL OHLC historical data missing on prod.** `get_current_price(AAPL)` returns the Friday close ✓ but `get_price_history(AAPL, 2024-01-01, 2024-12-31)` returns 404 "Ticker not found." The backfill job has lapsed. Two paths:

1. **Manual refresh**: `POST /api/v1/analytics/prices/refresh` (admin-only) triggers the same job that runs on the scheduled cron. Should pull fresh historical bars for all active tickers.
2. **Diagnose why the cron didn't run**: check the scheduler's `refresh_active_stocks` job state on prod. May be a scheduler-runtime issue rather than the data source.

### 1.3 Side-quests from the orchestration cycle

Items I flagged in earlier reports but didn't address:

- **No `GET /activations/:id` endpoint** — `ActivationDetail.tsx` filters the list endpoint client-side. Won't scale beyond ~100 activations. Small backend follow-up.
- **Stub `EarningsCalendarPort`** — `EarningsProximityEvaluator` always returns no-fire because the adapter is a stub. Needs a real source attached via third-party MCP.
- **Trigger E2E flake** ([issue #269](https://github.com/TimChild/PaperTrade/issues/269)) — full activation→trigger E2E currently `test.skip(...)`. Unit coverage compensates.
- **I1 font follow-up** — `PortfolioCard.tsx`, `PortfolioSummaryCard.tsx`, `HoldingsTable.tsx`, `PriceStats.tsx` still apply raw `.font-display` to numeric values. The agent flagged these as out-of-scope; small sweep PR would close.
- **Stale agent worktrees** — `.claude/worktrees/agent-*` directories from this cycle are locked but no longer used. `git worktree prune` when convenient.
- **Many shared `<dialog>` patterns** — the conditional-render fix I applied to `AskAnAgentButton` (PR #267) is a one-off. The `Dialog` component itself mounts children regardless of `isOpen`. Could refactor `Dialog` to conditionally render — would fix any future similar gotcha and is a 5-line change.

---

## 2. Forward direction A — Multi-provider agent invocation

### 2.1 Motivation

The F-3 trigger invocation is hardcoded to Anthropic. Tim asked:

> Is there a way for the agent triggers to trigger back to the claude desktop? (that would be nice because claude desktop is already connected to web search and a bunch of other info for example). Is there a way I can connect this to gemini in the cli? Is there any way to trigger gemini on events from Zebu (similar to the ask about triggering desktop claude?)?

The architecture is already abstract via `AgentInvocationPort`. Adding providers is mechanical; the harder question is **which provider for which trigger**.

### 2.2 Three integration patterns

#### Pattern A — Direct API invocation (current F-3, Anthropic)

The trigger fires → backend calls the Anthropic Messages API directly → parses the response → executes the decision.

**Pros**: deterministic latency, no human-in-loop, fully audited.  
**Cons**: limited tool surface — only what we explicitly hand the agent in the prompt. No native web search / news / earnings unless we wire those into our own MCP server (Phase D Wave 3 deferred).

**Status**: shipped (F-3 with `claude-haiku-4-5-20251001` default).

#### Pattern B — File urgent ExplorationTask → poll-and-claim (Claude Desktop / Gemini CLI)

The trigger fires → backend files an `ExplorationTask` flagged `[URGENT]` instead of (or in addition to) the inline API call. The desktop client (Claude Desktop / Gemini CLI) already has `zebu` MCP attached plus its own connectors (Brave Search, Tavily, Google services, etc.). The human (or a scheduled session) polls for urgent tasks and processes them.

**Pros**:

- Reuses the user's existing MCP + connector setup — no Zebu work to integrate web search / news / Gmail / Drive
- Works across Claude Desktop, Claude Code, Gemini CLI, any future MCP-aware client
- Audit trail same as any other ExplorationTask

**Cons**:

- Requires the human to invoke the agent client (or schedule it via Claude Code's `/schedule`)
- No latency guarantee — the trigger fires but the agent may not see it for hours
- The agent still has to manually decide what to do with the trade — no auto-execution

**Status**: works today as a convention. To make it ergonomic:

- **Backend**: extend `TriggerInvocationOrchestrator` to support a `mode: "direct" | "queue"` field on the trigger entity. When `mode=queue`, the trigger fire creates a `[URGENT]` ExplorationTask instead of calling Anthropic.
- **Operating manual update**: `§3.5` should describe both modes and how to choose.
- **UI**: trigger configuration form gets a radio: "Inline (Anthropic Haiku)" vs "Queue (poll from your agent client)".
- **Effort**: ~1 day. Mostly backend, small UI touch.

#### Pattern C — Direct API invocation, different provider (Gemini API)

Same as Pattern A but with Gemini Pro / Gemini Flash via Google's Generative Language API instead of Anthropic.

**Pros**: provider flexibility, cost comparison, future-proofing.  
**Cons**: doubles the integration surface (auth, prompt format, response parsing differ); not all features map 1:1 (tool use, prompt caching, etc.).

**Status**: not built. Implementation sketch:

- Add `GeminiAgentInvocationAdapter` next to `AnthropicAgentInvocationAdapter`
- Extract a shared `AgentResponseParser` that handles both tool-use formats
- Trigger entity gets a `provider: "anthropic" | "gemini"` field
- New env var `GOOGLE_API_KEY`
- **Effort**: ~2-3 days. The port is already abstract; this is a parallel adapter.

### 2.3 Recommended sequencing

1. **Pattern B first** (queue-mode triggers) — biggest leverage for least work, and uses what's already there. Unlocks Claude Desktop and Gemini CLI immediately.
2. **Pattern C only if needed** — if you find the Anthropic Haiku decisions aren't good enough, OR you want cost comparison, OR you want one provider as failover for the other.

---

## 3. Forward direction B — Backtests with agent decision points

### 3.1 Motivation

Tim asked:

> Is there any way to run backtests that include the agent decision points (would have to be a bit careful about ones that include web searching since it would effectively see into the future).

Without this, every trigger goes live in production with **untested judgment** — the only way to know if an agent's drawdown response is sensible is to ship it. Agent-decision backtests let us evaluate judgment before paying for it in live execution.

### 3.2 Why this is hard

Three pitfalls, in order of severity:

1. **Future-data leakage via tools.** `web_search`, `fetch_news`, the live-API `get_current_price` all see "today's" data even when the backtest is simulating 2023. The agent would effectively read tomorrow's headlines. **Backtest mode must restrict tools.**
2. **Cost.** Every trigger fire = one Anthropic call. A 2-year backtest with weekly fires = ~100 calls × ~$0.01 (Haiku 4.5) = manageable. Daily fires push to ~$5/run. Multi-strategy parameter sweeps add up fast.
3. **Non-determinism.** LLM responses don't repeat exactly. A backtest re-run can produce different decisions. You get a distribution, not a number. **Communicate this in the result.**

### 3.3 Architecture sketch

```
RunBacktestCommand                BacktestExecutor
    │                                  │
    │                                  ├── load Strategy + activation history
    │                                  │
    │  agent_invocation_port           ├── for each simulated day:
    │  (BacktestAgent or No-op)        │      ├── evaluate triggers (using historical state)
    │  ─────────────────────────►      │      ├── if fire:
    │                                  │      │     └── agent_invocation_port.invoke(
    │                                  │      │            tools=BACKTEST_SAFE_TOOLS,
    │                                  │      │            simulated_date=current_date,
    │                                  │      │          )
    │                                  │      └── execute decision (simulated trade)
    │                                  │
    │                                  └── persist BacktestRun + AgentDecisionLog[]
```

### 3.4 New entities

- **`BacktestAgentInvocation`** — one row per simulated trigger fire. Fields: `id`, `backtest_run_id` FK, `simulated_date`, `trigger_id` FK, `condition_evaluation_data`, `agent_response`, `rationale`, `decision_executed`. Audit trail.
- **`BacktestRunRequest.agent_invocation_mode`** — new enum: `NONE` (current behavior, no agent), `MOCK` (always returns HOLD — for cheap testing the integration), `LIVE` (real Anthropic calls).

### 3.5 Tool restrictions ("BACKTEST_SAFE_TOOLS")

A whitelist of MCP tools the agent can use during a backtest:

- `get_price_history(ticker, start, end)` — capped at `end <= simulated_date`. Enforced server-side via a request middleware that reads the `X-Zebu-Simulated-Date` header set by the backtest executor.
- `get_portfolio_state(portfolio_id, as_of=simulated_date)` — reconstructs holdings from transactions up to `simulated_date`. Already exists for analytics; just need to wire the `as_of` parameter.
- `list_exploration_tasks(status=done, claimed_before=simulated_date)` — historical findings only.
- **Banned**: `web_search`, `fetch_news`, `get_current_price`, anything calling third-party APIs.

The MCP server enforces. The agent prompt explicitly lists what's available.

### 3.6 Phased delivery

- **J-1** Domain entity `BacktestAgentInvocation` + repository + migration. ~1 day backend.
- **J-2** `BacktestAgentInvocationAdapter` (port impl) — wraps real Anthropic adapter, intercepts tool calls, enforces simulated-date filter, returns the agent's structured decision. ~2 days backend.
- **J-3** `BacktestExecutor` integration — pass the adapter through, call it on trigger fires, persist invocations. ~2 days backend.
- **J-4** UI: backtest config form gets an "Agent mode" toggle (NONE / MOCK / LIVE); backtest result page renders the `BacktestAgentInvocation` log inline with the trade timeline. ~2 days frontend.
- **J-5** Operating manual update — backtest-mode prompt + tool surface. ~half day.
- **J-6** Cost guardrails: per-user-per-backtest budget cap, halt-on-exceed. ~half day.
- **J-7** Sample backtest report comparing identical strategy with/without agent intervention. ~1 day, exploratory.

**Total**: ~1.5–2 weeks of focused work. Not a small phase.

### 3.7 What NOT to build

- **Don't try to make it deterministic.** Live with the distribution; communicate the variance in the report.
- **Don't try to backtest the live-execution scheduler.** Backtests should be one-shot synchronous; trigger evaluation runs in-line, not via the APScheduler tick.
- **Don't expand the tool surface in backtest mode.** Future-leak is sneakier than it looks; keep the whitelist tight.

---

## 4. Sequencing recommendation

| Step | Effort | Unlocks |
|---|---|---|
| Land PR #270 (backtest 500 fixes) | merged | the agent can retry backtests intelligently |
| Backfill AAPL OHLC on prod | 5 min (admin call) | smoke-test exploration tasks actually run |
| Pattern B — queue-mode triggers | ~1 day | desktop Claude / Gemini CLI participate |
| Follow-up sweep (gaps in §1.3) | ~1 day total | clean state for the next iteration |
| Pattern C — Gemini adapter | ~2-3 days | provider parity, cost comparison |
| Agent-decision backtests (J-1..J-7) | ~1.5-2 weeks | evaluate agent judgment before live execution |

Recommended order: **fix-and-stabilize → multi-provider → backtests**. The backtest phase is the biggest unlock for trust in agent judgment but also the biggest single piece of work; saving it for last lets you build it on top of a known-good substrate.

---

## 5. Open questions

| # | Question | Default position |
|---|---|---|
| Q1 | Should queue-mode triggers (Pattern B) also call the inline Anthropic adapter as fallback if no one claims within N minutes? | No fallback for v1 — keep the modes distinct. Reconsider if urgent tasks are getting starved. |
| Q2 | When backtests fail with `TickerNotFoundError` on prod (per smoke-test 450cb185), should the executor write a FAILED BacktestRun row (current pipeline-internal behavior) or 503 + no row? | The current pipeline-internal behavior is good — operators get an audit row. The pre-pipeline 503 path (added in PR #270) is the right error shape for early failures. |
| Q3 | Should backtest-mode agent invocations have a different model than live mode? (e.g., always Haiku for cost, Sonnet for live decisions) | Configurable per backtest, defaulting to whatever `ZEBU_AGENT_MODEL` is set to. Same code path; just an env override. |
| Q4 | Backtest non-determinism: store a `seed` in the request that controls anything we can (e.g., temperature → 0)? | Yes — `temperature=0` by default, surfaced as an optional `agent_temperature` in the backtest request body. |
| Q5 | Pattern C (Gemini) — first or after the backtest work? | After. Pattern B handles most of the "I want to use Gemini" workflow already via the desktop integration. Direct-Gemini invocation is nice-to-have, not critical-path. |
| Q6 | Should we deprecate the inline Anthropic call entirely in favor of queue-mode? | No — they serve different latency profiles. Keep both. |

---

## 6. Quick-reference: enabling triggers in prod (recap from Phase F-7)

After PR #270 lands:

1. **Backfill historical data** for any tickers used in your strategies:

   ```bash
   curl -X POST https://zebutrader.com/api/v1/analytics/prices/refresh \
     -H "Authorization: Bearer <admin-clerk-jwt>"
   ```

2. **Run the smoke test** to confirm the trigger pipeline works end-to-end:

   ```bash
   ANTHROPIC_API_KEY=... \
   uv run scripts/trigger_smoke_test.py \
     --mode api \
     --base-url https://zebutrader.com \
     --api-key <your-trade-key>
   ```

3. **Flip the production flag**:

   ```bash
   ssh papertrade-proxmox 'sed -i "s/ZEBU_TRIGGER_FIRES_ENABLED=false/ZEBU_TRIGGER_FIRES_ENABLED=true/" /opt/papertrade/.env && cd /opt/papertrade && docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --force-recreate backend'
   ```

4. **Configure your first trigger** via the activation detail page or the API.

---

## Appendix — key file pointers

- This proposal: `docs/planning/agent-platform-next-steps.md`
- Previous proposal (now executed): `docs/planning/agent-platform-proposal.md`
- What shipped through Phase D Wave 2: `docs/planning/agent-platform-completed.md`
- Phase F design (executed): `docs/architecture/phase-f-agent-in-the-loop.md`
- Operating manual: `docs/agents/operating-manual.md`
- Smoke-test script: `scripts/trigger_smoke_test.py`
- Production checklist: `docs/deployment/production-checklist.md`
- Agent-platform memory: `~/.claude/projects/-Users-timchild-github-PaperTrade/memory/`
