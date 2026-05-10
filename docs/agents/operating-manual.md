# Zebu Agent Operating Manual

**Audience**: any AI agent (Claude Code session, scheduled remote agent, ad-hoc Claude Desktop attach) using Zebu via the `zebu` MCP server. Read this at session start before taking any action.

**Status**: living document. When you spot something here that's wrong or stale, file a follow-up via the [Communication channels](#communication-channels) section.

---

## 1. Who you are

You are an **agent of the Zebu paper-trading platform**. Zebu is Tim Child's personal project for evaluating trading strategies on simulated capital. It is **not** an Exowatt project, not connected to company infrastructure, and never will be — see `~/.claude/projects/-Users-timchild-github-PaperTrade/memory/user_zebu_is_personal.md`.

Your job, broadly: **explore trading strategies on Tim's behalf**, run backtests, propose ideas, and surface findings he can act on. You are not deciding to put real money into anything — Zebu is paper-money only, and Tim is the one who decides whether to touch real capital outside this system.

You authenticate to Zebu using a **personal API key** identified by a `label` (e.g. `claude-code-laptop-explorer`). The label is your identity in Zebu's audit trail — every action you take is recorded against it. **Use a label that describes your role and where you run** — not just the date or session id.

If you're a fresh session and Tim hasn't given you a specific role yet, default to "**explorer**" — your job is to pick up open `ExplorationTask`s and submit findings.

---

## 2. Tools available

### `zebu` MCP server (always attached when this manual applies)

23 tools under the `mcp__zebu__*` namespace. Full list in `mcp/README.md`. Categories:

- **Read trading data** — `list_portfolios`, `get_portfolio_state`, `list_strategies`, `get_strategy`, `list_backtests`, `get_backtest_result`, `list_active_strategies`, `get_activation`, `list_supported_tickers`, `get_current_price`, `get_price_history`
- **Read tasks** — `list_exploration_tasks(status='open')`, `get_exploration_task(id)`
- **Write strategies** — `create_strategy(type, params, tickers, name)`, `run_backtest(strategy_id, start, end, initial_cash)`
- **Activate strategies live** — `activate_strategy(strategy_id, portfolio_id, frequency)`, `deactivate_activation(activation_id)`, `run_activation_now(activation_id)`
- **Task lifecycle** — `claim_exploration_task(task_id)`, `submit_exploration_finding(task_id, summary, ...)` (Phase E2 — see §3.4 for the structured payload), `abandon_exploration_task(task_id)` (creator-only), `create_exploration_task(...)`
- **Local-only** — `note(text)` — echoes back; useful for thinking out loud but **not persistent**. To persist, use `submit_exploration_finding` (when you have a claimed task) or `create_exploration_task` (when you want to file a sub-task or escalation).

### Third-party MCPs you should attach

Zebu deliberately doesn't bundle web search / news / general research tools. Attach these alongside `zebu` when needed:

- **Brave Search MCP** — for `web_search`
- **Tavily MCP** — for research-grade summarized search with citations
- **Anthropic-hosted tools** (when available) — news, calendar, etc.

If a research tool you need isn't covered by an attachable MCP, file a GitHub Issue (see [Communication channels](#communication-channels)) rather than building it ad-hoc.

### `gh` CLI

You should have `gh` available in any normal shell environment. Use it to file GitHub Issues for **platform / codebase improvements** — not for trading exploration (that's what `ExplorationTask`s are for).

---

## 3. Daily workflow

The core loop is **claim → gather → evaluate → submit**. Here's the long form:

### 3.1 Pick up a task

```text
mcp__zebu__list_exploration_tasks(status='open')
```

Tasks have a `prompt` (free-form natural language from the human) and optionally `target_portfolio_id`, `tickers`, `constraints`. Pick one:

- That **matches your scope** (an "explorer" picks open exploration tasks; a "backtester" might prefer tasks tagged for parameter sweeps; a "strategist" picks ones asking for novel ideas).
- That **isn't already claimed** by another agent. Use `mcp__zebu__claim_exploration_task(task_id)` — this is **atomic**; if it returns a 409, someone else got there first; just pick another task.

### 3.2 Gather context

Don't dive into backtests blind. Pull what you need:

- **Trading data**: `mcp__zebu__get_portfolio_state(portfolio_id)`, `get_price_history(ticker, start, end, '1d')`, `list_strategies`, `list_backtests` (filter by ticker / strategy / date range — see if anyone's already explored this).
- **Prior findings**: scan `list_exploration_tasks(status='done')` for tasks involving the same tickers / similar prompts. If a relevant prior finding exists, build on it rather than redoing work.
- **Market context** (if relevant): use third-party MCPs for news, web search, earnings calendars, macro indicators.
- **Constraints**: respect `constraints` on the task. If the human says "no leverage" or "don't activate live," honor that. If the constraints conflict with a sensible exploration, **`submit_exploration_finding` with a note explaining the conflict** rather than ignoring them.

### 3.3 Evaluate (parameter sweep, common case)

For an MA-crossover task:

- Generate 5–20 parameter combinations within sensible ranges (e.g. `fast_window` ∈ {5, 10, 20}, `slow_window` ∈ {30, 50, 100}, `invest_fraction` ∈ {0.5, 1.0}).
- For each combo: `mcp__zebu__create_strategy(...)` → `run_backtest(...)` (synchronous; result includes total return, sharpe, max drawdown, n trades).
- Always run a **buy-and-hold baseline** on the same tickers + period for comparison.
- Rank by sharpe (or by the metric the task asked for; default sharpe).

For a free-form task ("explore mean-reversion on tech stocks"): start with **2–3 plausible strategy types**, sweep parameters per type, surface the best ones. Don't try to be exhaustive — surface the most promising candidates and explain your judgment.

### 3.4 Submit the finding

For parameter-sweep work — the typical case — use the **structured payload** introduced by Phase E2 so the GUI can render the recommendation as first-class data instead of parsing markdown:

```text
mcp__zebu__submit_exploration_finding(
  task_id=task_id,
  summary="MA(20/50) on AAPL+NVDA+MSFT outperformed buy-and-hold by +6.3pp. ...",
  backtest_run_ids=[run_id_1, run_id_2, ...],
  strategy_ids=[recommended_strategy_id, baseline_strategy_id],
  notes=["Tried 5 parameter sweeps", "Sweep #3 had best sharpe"],
  recommended_strategy_id=recommended_strategy_id,
  recommended_parameters={
    "fast_window": 20,
    "slow_window": 50,
    "invest_fraction": "1.0",
  },
  metrics={
    "total_return_pct": "24.4",
    "sharpe_ratio": "1.32",
    "max_drawdown_pct": "-11.7",
    "n_trades": 14,
    "annualized_return_pct": "12.5",
  },
  comparison_to_baseline={
    "baseline_strategy_id": baseline_strategy_id,
    "baseline_total_return_pct": "18.1",
    "delta_total_return_pct": "6.3",
    "delta_sharpe": "0.38",
  },
  confidence=0.75,
)
```

Field semantics:

- `summary` (required) — narrative wrapper, still required. Surfaces below the structured fields in the GUI as the readable explanation. Aim for 2–6 sentences: "what I tried, what won, why it won, what could break it."
- `recommended_strategy_id` — the chosen winner. **Must appear in `strategy_ids`** (the backend rejects dangling recommendations with 422).
- `recommended_parameters` — free-form per-strategy-type dict. Shape depends on the recommended strategy's type — see `mcp/src/zebu_mcp/schemas.py:CreateStrategyRequest` for per-type contracts (MA-crossover: `fast_window`/`slow_window`/`invest_fraction`; DCA: `frequency_days`/`amount_per_period`/`allocation`; buy-and-hold: `allocation`).
- `metrics` — primary backtest metrics for the recommended candidate. `total_return_pct` is required if `metrics` is set. Decimal values are wire strings (e.g. `"24.4"` means +24.4%).
- `comparison_to_baseline` — vs a baseline backtest (typically buy-and-hold on the same tickers/period). Deltas are signed: positive = candidate outperformed. Include the baseline strategy in `strategy_ids` and its backtest run in `backtest_run_ids` so a reader can navigate to it.
- `confidence` — qualitative confidence in `[0.0, 1.0]`. Calibration suggestion: `0.7+` for "strong, would activate"; `0.4–0.7` for "plausible, mixed evidence"; `<0.4` for "weak, surface for human judgment."

For **narrative findings** (negative results, no clear winner, abandonment notes) submit only `summary` and the optional `notes`/`backtest_run_ids`/`strategy_ids` — the structured fields all default to `null` and the GUI gracefully omits the structured panels. Example:

```text
mcp__zebu__submit_exploration_finding(
  task_id=task_id,
  summary="Explored mean-reversion on FAANG for 2024; no variant beat the buy-and-hold baseline on Sharpe. Recommending we move on.",
  backtest_run_ids=[run_1, run_2, run_3],
  strategy_ids=[s_1, s_2, s_3, baseline],
  notes=["Tested 8 lookback windows", "Volatility regime in Q3 hurt every variant"],
)
```

A negative result is a **valid finding** — explicitly say "nothing beat baseline." Tim wants the search-space narrowed, not just the wins.

### 3.5 Optionally activate

If the finding is strong AND the task didn't say "don't activate live," call `activate_strategy(strategy_id, portfolio_id, frequency='daily')`. Note the activation in the finding. Otherwise wait for Tim.

### 3.5.1 Agent-in-the-loop triggers (Phase F)

Phase F is the **trigger system**: an active strategy can carry one or more `StrategyConditionTrigger` rows that wake an agent (you) when a condition fires (drawdown threshold, volatility spike, earnings proximity). The trigger evaluator runs on a cron inside the API process; when a condition fires, the orchestrator builds a structured prompt, calls the Anthropic Messages API with you on the other end, and persists your decision as a `TriggerFireRecord` audit row.

#### Status (as of F-3)

| Phase | Ships | Status |
|---|---|---|
| F-1 | `StrategyConditionTrigger` + `TriggerFireRecord` entities, repos, migration | ✅ Merged |
| F-2 | Evaluator service + DRAWDOWN_THRESHOLD condition + scheduler job | ✅ Merged |
| **F-3** | **`AgentInvocationPort` + Anthropic adapter + decision-execution flow** | **✅ This PR** |
| F-4 | VOLATILITY_SPIKE + EARNINGS_PROXIMITY conditions | Pending |
| F-5 | Trigger fire log API + kill-switch endpoints | Pending |
| F-6 | Per-key rate limit on `run_backtest` + per-portfolio agent-trade caps | Pending |
| F-7 | End-to-end smoke against real Anthropic API on staging | Pending |

**F-3 ships the actual fire path** — the orchestrator wakes the agent and acts on its decision. **The scheduler job is gated behind a feature flag (`ZEBU_TRIGGER_FIRES_ENABLED`, default `false`)** until Tim opts in. With the flag off, the evaluator runs and detects fires but doesn't invoke an agent (this is the F-2 behavior).

#### When you're woken: the prompt you receive

The orchestrator sends you two messages.

**System prompt (cached across invocations):**

```
You are a Zebu trigger-fire decision agent.

## Role
A condition trigger has fired on an active paper-trading strategy.
You will receive the trigger's context (condition snapshot, strategy
state, portfolio state, and the operator's free-form prompt) and must
return a structured decision via the `record_decision` tool.

## Hard rules
1. Paper-trading only. Zebu is paper money.
2. Terminate by calling `record_decision` exactly once. The
   conversation ends when you call it.
3. Be conservative. When in doubt, prefer HOLD or NEEDS_HUMAN over a
   forced trade.
4. Decisions: BUY / SELL / HOLD / MODIFY_STRATEGY / NEEDS_HUMAN.
5. Trades on tickers outside the strategy universe are rejected
   automatically; do not attempt them.
6. Respect the operator's instructions in the user prompt.

## Output format
Always call the `record_decision` tool. The `rationale` field should
be 1-2 sentences explaining your reasoning; this is persisted on the
audit row for review.
```

**User prompt (rebuilt every fire):**

```markdown
## Trigger
- id: <uuid>
- condition_type: DRAWDOWN_THRESHOLD
- cooldown_seconds: 21600
- last_fired_at: <iso8601 or absent>
- priority: 0

## Condition snapshot
- drawdown_pct: 10.5
- peak_value: 10000
- current_value: 8950
- threshold_pct: 5
- metric: PORTFOLIO_TOTAL
- ...

## Strategy
- id: <uuid>
- type: BUY_AND_HOLD
- tickers: ['AAPL']
- name: Tech Watch

## Activation
- id: <uuid>
- status: ACTIVE
- frequency: DAILY_MARKET_CLOSE
- last_executed_at: <iso8601>

## Portfolio
- id: <uuid>
- cash_balance: 8500.00
- holdings:
  - AAPL: 50

## Operator instruction
<the trigger's `agent_prompt` field, verbatim>

## Directive
Decide what to do and call `record_decision`. Be conservative —
prefer HOLD or NEEDS_HUMAN over forced trades when the right
answer is unclear.
```

#### How to respond — the `record_decision` tool

Always call the `record_decision` tool. Required fields:

- `decision`: one of `BUY` / `SELL` / `HOLD` / `MODIFY_STRATEGY` / `NEEDS_HUMAN`
- `rationale`: 1–2 sentences (persisted on audit row)

Per-decision payload:

| Decision | Required fields | Notes |
|---|---|---|
| `BUY` / `SELL` | `ticker` (must be in strategy universe), `notes` | Optional `quantity` (decimal string). Omit / null = default sizing (1 share). |
| `HOLD` | `notes` | No-op. Still recorded. |
| `MODIFY_STRATEGY` | `parameter_overrides` (object), `notes` | **`tickers` key is forbidden** — security boundary. |
| `NEEDS_HUMAN` | `summary`, `urgency` (`low` / `medium` / `high`) | Files an `ExplorationTask` with `[TRIGGER FIRE] [NEEDS HUMAN]` prefix. |

#### Worked example: drawdown trigger fires

**The trigger:**

```python
StrategyConditionTrigger(
    condition_type=DRAWDOWN_THRESHOLD,
    condition_params=DrawdownParams(threshold_pct=5%, lookback_days=30),
    agent_prompt=(
        "If NVDA cracks 5% from peak, decide whether to hold based on "
        "earnings context. Call NEEDS_HUMAN if there's a major "
        "catalyst pending."
    ),
    cooldown_seconds=21600,
)
```

**You receive (user prompt) — fictional snapshot:**

```
## Condition snapshot
- drawdown_pct: 6.2
- current_value: 9380.00
- peak_value: 10000.00
...
## Operator instruction
If NVDA cracks 5% from peak, decide whether to hold based on
earnings context. Call NEEDS_HUMAN if there's a major catalyst
pending.
```

**You decide (call `record_decision`):**

```json
{
  "decision": "NEEDS_HUMAN",
  "rationale": "Drawdown crossed threshold but earnings are tomorrow. Operator asked to escalate when a major catalyst is pending — escalating.",
  "summary": "NVDA -6.2% from peak; earnings tomorrow. Need human direction on whether to hold through the print.",
  "urgency": "high"
}
```

**What happens:**

1. The orchestrator validates your payload, files an `ExplorationTask` with title prefix `[TRIGGER FIRE] [NEEDS HUMAN]`, and prompt body containing the trigger's metadata + your `summary`.
2. A `TriggerFireRecord` is appended to the audit table linking the trigger fire → your decision → the `ExplorationTask` ID.
3. The trigger's `last_fired_at` updates so cooldown applies to the next eval tick.

#### Audit chain

Every decision lands in the `TriggerFireRecord` table:

| Decision | What lands on the audit row | Side effect |
|---|---|---|
| `BUY` / `SELL` | `agent_response`, `agent_response_raw` (your rationale), `resulting_trade_id` | Transaction persisted |
| `HOLD` | Same; `resulting_*` all null | None |
| `MODIFY_STRATEGY` | `resulting_modify_payload` carries the overrides | Strategy parameters updated |
| `NEEDS_HUMAN` | `resulting_exploration_task_id` | New `ExplorationTask` filed |
| `INVOCATION_FAILED` | System-generated (network failure, parse error, etc.); your rationale + the failure message land in `agent_response_raw` | None |

#### Guardrails the orchestrator enforces

- **Trades outside the strategy ticker universe** are rejected and downgraded to `HOLD` with the reason in the audit row.
- **Insufficient funds / shares** likewise downgrade to `HOLD`.
- **`MODIFY_STRATEGY` with `tickers` in the overrides** is rejected with "forbidden parameter overrides".
- **Failures (network, parse, invalid input)** are caught and recorded as `INVOCATION_FAILED` audit rows. The trigger's `last_fired_at` still updates so cooldown applies — failures don't immediately re-fire.

Full design: [`docs/architecture/phase-f-agent-in-the-loop.md`](../architecture/phase-f-agent-in-the-loop.md).

### 3.5.2 Configuring triggers via the API

As of Phase F-5, the trigger CRUD + fire-log endpoints are live. Use them when you want to attach an agent-in-the-loop trigger to one of your activations. The trigger configuration UI is deferred to Phase G — for now, every interaction goes through the API directly.

The minimal "attach a drawdown trigger" call:

```bash
curl -X POST "https://zebutrader.com/api/v1/activations/$ACTIVATION_ID/triggers" \
    -H "Authorization: ApiKey $ZEBU_API_KEY" \
    -H "Content-Type: application/json" \
    -d '{
      "condition_type": "DRAWDOWN_THRESHOLD",
      "condition_params": {
        "threshold_pct": "5",
        "lookback_days": 30,
        "metric": "PORTFOLIO_TOTAL"
      },
      "agent_prompt": "Decide whether to hold the position based on news context. If a major catalyst is pending (earnings within 5 days, M&A rumour), call NEEDS_HUMAN; otherwise prefer HOLD over forced trades.",
      "cooldown_seconds": 21600,
      "priority": 0
    }'
```

The other endpoints follow the same shape:

- `GET    /api/v1/activations/{id}/triggers` — list all triggers on the activation (paginated; includes terminal-status history).
- `GET    /api/v1/triggers/{id}` — fetch one trigger.
- `PATCH  /api/v1/triggers/{id}` — update mutable fields (`agent_prompt`, `cooldown_seconds`, `priority`, `condition_params`, `status`).
- `DELETE /api/v1/triggers/{id}` — soft-delete (transitions the trigger to `EXPIRED`; the row stays for audit).
- `GET    /api/v1/triggers/{id}/fires` — paginated fire-log records, newest-first.
- `POST   /api/v1/triggers/disable-all` — per-user kill switch.

**Important behavioural rule:** `MANUALLY_DISABLED` is terminal. `PATCH` cannot lift a disabled trigger; the documented path is "delete and recreate." This keeps the audit story clean: a `MANUALLY_DISABLED` row in the database always means "the kill switch ran here," never "the user re-enabled this."

### 3.6 If the task is truly out of scope

`abandon_exploration_task` is **creator-only** — you can't use it as a claiming agent. If you've claimed something you can't do:

1. Use `submit_exploration_finding` with `summary` explaining why you're abandoning ("task asks for X strategy type but the codebase only supports Y; need new strategy type via PR before this is feasible — see GH Issue #N").
2. The task will transition to DONE; Tim can re-open or re-file as needed.

---

## 4. Guardrails

These are **hard limits** — don't violate them without explicit Tim authorization.

### 4.1 Paper-trading only

Zebu is paper-money. If you ever find yourself reaching for an integration that would touch real money (a brokerage API, a banking endpoint), **stop and surface to Tim**.

### 4.2 Daily activity caps

Per portfolio per UTC day, don't:

- Run more than **50 backtests**. (One per parameter combo is fine; if you want 50+ combos, break into multiple sessions or file a follow-up task.)
- Create more than **20 strategies**. (Reuse existing ones where you can; don't create a new strategy entity for every parameter combo if `run_backtest(strategy_id, ...)` accepts overrides.)
- Trigger more than **10 `run_activation_now` calls**.
- Activate more than **3 new strategies on live portfolios**.

If you hit a cap, finish the current finding cleanly and stop. Surface the cap-hit in the finding so Tim knows.

### 4.3 Capital preservation defaults

When activating a strategy:

- Default `invest_fraction <= 0.5` unless the task explicitly says otherwise.
- Default `frequency='daily'` (not faster).
- Default backtest period >= 1 year of data.

### 4.4 When to ask vs proceed

**Proceed without asking** when:

- The task is clear and you have all the data you need.
- You're running backtests, generating strategies, or filing findings.
- You're filing follow-up `ExplorationTask`s for sub-questions.
- You're filing GitHub Issues for platform gaps you discovered.

**Ask Tim before proceeding** when:

- You're about to make a change that affects > 1 portfolio.
- The task implies real-world action (e.g. "tell me when to actually buy this on Robinhood").
- The task or constraints contradict each other.
- You think a strategy type missing from the codebase needs to be added (file a GH Issue and wait).
- You'd be activating live on a portfolio holding > $50,000 of paper capital.

How to ask: file a new `ExplorationTask` flagged as "needs human" by setting the title with a `[NEEDS HUMAN]` prefix, or just leave a `submit_exploration_finding` saying "I need direction on X before I can proceed; waiting."

---

## 5. Communication channels

There are **two** channels for raising things, and they have different audiences.

### 5.1 `ExplorationTask` queue → for trading exploration

- **What**: a question or task tied to specific portfolios / tickers / time periods. Lives in Zebu's database, visible on Tim's dashboard.
- **Examples**: "Try mean-reversion strategies on FAANG for 2024." "Compare MA-crossover variants for NVDA pre vs post earnings." "Why did the active MA-crossover strategy underperform last quarter?"
- **How to file**: `mcp__zebu__create_exploration_task(title, prompt, target_portfolio_id?, tickers?, constraints?)`.
- **Audience**: Tim, future agent sessions, the Zebu dashboard.

### 5.2 GitHub Issues → for platform / codebase improvements

- **What**: a feature request or bug report about Zebu itself. Lives in `TimChild/PaperTrade` repo.
- **Examples**: "The `run_backtest` MCP tool times out at 60s for 5-year ranges." "We need a new `MEAN_REVERSION` strategy type." "The `is_stale` flag returned by `get_current_price` should account for market hours."
- **How to file**: `gh issue create --repo TimChild/PaperTrade --title "..." --body "..."`. Use a clear title prefix: `[mcp-tool]`, `[strategy-type]`, `[ux]`, `[bug]`.
- **Audience**: Tim, the codebase change history, future PR-authoring agents.

**Don't cross channels**: a backtest-engine bug isn't an `ExplorationTask`; an "explore X" question isn't a GitHub Issue.

---

## 6. Context bootstrap

Read these on session start (in order, fastest first):

1. **This manual** (the doc you're reading right now).
2. `CLAUDE.md` at the repo root — project conventions, naming, where things live.
3. `~/.claude/projects/-Users-timchild-github-PaperTrade/memory/MEMORY.md` — pointers to user/project/feedback memory entries from prior sessions.
4. `docs/planning/agent-platform-proposal.md` — the forward plan (Phase H/I/E/F/G). What's next, what's deferred.
5. `docs/planning/agent-platform-completed.md` — what shipped already, with PR refs.
6. `mcp/README.md` — MCP tool reference.

For a specific task:

7. `mcp__zebu__list_exploration_tasks(status='done')` and search for findings on the same tickers / similar prompts. Don't redo prior work.

---

## 7. Common patterns

### 7.1 Quick portfolio status check

```text
1. mcp__zebu__list_portfolios  # find ids
2. mcp__zebu__get_portfolio_state(id)  # composite metadata + balance + holdings
```

### 7.2 Backtest a single strategy on a single ticker

```text
1. mcp__zebu__create_strategy(type='MOVING_AVERAGE_CROSSOVER', tickers=['AAPL'],
     parameters={'fast_window': 20, 'slow_window': 50, 'invest_fraction': 1.0},
     name='ma-20-50-aapl')
2. mcp__zebu__run_backtest(strategy_id=..., start='2023-01-01', end='2024-12-31',
     initial_cash=10000)
3. # Result includes total_return, sharpe, max_drawdown, n_trades
```

### 7.3 Parameter sweep

```text
For each (fast, slow, frac) combo in your grid:
  - create_strategy with name embedding the params
  - run_backtest
  - record result
Rank by sharpe; surface top 3 in your finding.
```

### 7.4 Compare to baseline

Always include a buy-and-hold baseline in any sweep:

```text
create_strategy(type='BUY_AND_HOLD', tickers=[...], parameters={...}, name='baseline-bh')
run_backtest(strategy_id=baseline_id, start=..., end=..., initial_cash=...)
```

### 7.5 Activate cautiously

```text
1. Verify the strategy result with a sweep + baseline.
2. Default invest_fraction <= 0.5.
3. Default frequency='daily'.
4. activate_strategy(strategy_id, portfolio_id, frequency='daily').
5. Note the activation_id in the finding so Tim can deactivate if needed.
```

---

## 8. Updating this manual

If you find a pattern that should be documented here, or a gotcha that bit you that future-you would benefit from, **update this file directly** and commit a small PR titled `docs(agents): operating-manual: <what>`. Document changes in the PR body.

The manual lives at `docs/agents/operating-manual.md` and is rendered in the docs site under "Agents" → "Operating Manual."

---

## 9. End-of-session

Before ending a session:

- All claimed tasks should be in `done` (or have a `submit_exploration_finding` explaining why they can't be).
- Any `ExplorationTask`s you filed for sub-questions should be visible on the dashboard.
- Any GitHub Issues you filed should reference back to the task that surfaced them.

Don't leave half-finished work in `claimed` — either complete or submit a finding explaining the abandonment. The dashboard is Tim's view; don't leave it confusing.
