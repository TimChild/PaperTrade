# Phase L — Agent-driven backtests (L-1 through L-6)

**Date**: 2026-05-23 → 2026-05-24
**Orchestrator**: Claude Opus 4.7 (dispatcher-as-Claude pattern)
**Phase scope**: All of `docs/planning/agent-platform-next-steps.md` §3 except L-7 (sample comparison report — exploratory, defer to interactive session).

## TL;DR

Phase L (originally labelled J-1..J-7 in the proposal; renamed L externally because Phase J already shipped) is now functional end-to-end. The backend foundation chain (entity → adapter → executor), the cost guardrail, the UI, and the operating-manual updates all shipped across **6 PRs in one orchestration cycle**. The only remaining item is L-7, which is an exploratory data-analysis task best driven interactively.

A LIVE backtest with `agent_invocation_mode: "live"` and `agent_max_cost_usd: <cap>` will now:

1. Evaluate the user's live triggers on each simulated day.
2. On fire, invoke Anthropic Haiku-4.5 via the L-2 wrapper with the simulated-date-enforced `BACKTEST_SAFE_TOOLS` whitelist.
3. Apply the agent's decision to the simulated trade book (BUY/SELL via the existing builder; MODIFY_STRATEGY recorded but not applied).
4. Persist one `BacktestAgentInvocation` row per fire.
5. If `agent_max_cost_usd` is set and cumulative spend crosses it, substitute `MockBacktestAgentInvocationPort` for the rest of the run; log a synthetic `BUDGET_EXHAUSTED` marker row.
6. Surface the full invocation log on the result page.

## PRs landed

| PR | Title | Scope |
|---|---|---|
| #298 | `docs(planning): scope L-1/L-2/L-3 specs for agent-driven backtests` | Architect-drafted spec files for the foundation chain; 5 open design questions resolved before implementation started |
| #299 | `feat(backend): BacktestAgentInvocation entity + repo + migration (Task L-1)` | Domain VO + entity + port + in-memory + SQLModel adapter + Alembic migration. Adds `backtest_runs.agent_invocation_mode` column per the Q5 flip. |
| #300 | `feat(backend): BacktestAgentInvocationAdapter + tool-call enforcement (Task L-2)` | Wrapping adapter that enforces simulated-date filter + `BACKTEST_SAFE_TOOLS` whitelist. Introduces the first multi-turn tool-use loop in the codebase via a dispatch-callback on the inner Anthropic adapter (F-3 unaffected). |
| #301 | `feat(backend): wire agent invocation into BacktestExecutor (Task L-3)` | Day-loop integration. Trigger universe resolution, per-simulation cooldown dict, agent-first-then-strategy ordering, batch persistence of audit rows. |
| #302 | `feat(backend): per-backtest agent cost guardrails (Task L-6)` | `agent_max_cost_usd` on `RunBacktestCommand`; pricing table (`anthropic_pricing.py`); halt-and-downgrade-to-MOCK on budget exceeded; synthetic `BUDGET_EXHAUSTED` marker row. Plus the operating-manual cost section. |
| #303 | `feat(fe): agent-mode toggle + invocation log on backtest pages (Task L-4)` | Form gets None/Mock/Live radio; result page gets the new "Agent invocations" section with offset-based "Load more" pagination. Plus the operating-manual user-facing section (§7.6). |

**Cumulative**: ~7500 LOC added; ~150 new tests (2175 backend, 674 frontend at session end).

## Orchestration mechanics that worked

- **Architect-first for substantive new work.** PR #298 produced three written specs (217 / 218 / 219) before any implementer touched code. I (orchestrator) reviewed and resolved the architect's flagged design questions in conversation with Tim (Q1 enforcement mechanism, Q2 dispatch-callback pattern, Q3 trigger universe, Q4 MODIFY_STRATEGY behaviour, Q5 column-on-run). Specs updated in place to "Design decisions (resolved 2026-05-23)" before the implementer dispatch. Three sequential backend PRs (L-1 → L-2 → L-3) all merged on first review pass — the spec-first investment paid off in zero "what did you mean by..." back-and-forth.

- **`/code-review` as the substitute for GitHub Copilot.** Codified in PR #297 the same day. Each implementer agent invokes `/code-review <PR#>` via the Skill tool after opening its PR; the skill posts one inline review comment with confidence-≥80 findings; the implementer addresses them, then self-merges on green CI. **Real bugs caught by this**:
  - L-1 #299 → `BacktestRunRepository.save` UPDATE path was silently dropping the new column on lifecycle transitions; `save_all` was N+1 not the documented single round-trip; dead-code branch in MOCK invariants.
  - L-2 #300 → four separate exception-leak bugs in the tool-dispatch helpers (`InvalidTickerError`, `InvalidPortfolioError`, `TickerNotFoundError`, `MarketDataUnavailableError` all bubbled past L-3's `AgentInvocationError` catch); SQL limit-then-filter ordering under-returning results; signature drift on `BacktestAgentInvocationAdapter.invoke` (missing the new `dispatch_tool_call` kwarg → Protocol non-conformance).
  - L-3 #301 → hoisted-import typing, empty-rationale defence on LIVE non-INVOCATION_FAILED, synthetic activation UUID.
  - L-6 #302 → **the most consequential catch**: `_extract_usage` was reading only `Message.usage.input_tokens`, missing `cache_read_input_tokens` (0.1× rate) and `cache_creation_input_tokens` (1.25× rate). Phase F-3's prompt caching means cache-reads dominate multi-turn invocations; under-billing by 5-25% would have let LIVE backtests overshoot `agent_max_cost_usd` by the same fraction. The whole point of L-6 is to bound spend; the bug defeated the bound. Fixed in `cafc2d2` before merge.
  - L-4 #303 → pagination grew `limit` past `MAX_PAGE_LIMIT=100` (422 after second "Load more"); `simulated_date` rendered the wrong day in non-UTC timezones; test weakened to mask the tz bug; UTF-16 surrogate split risk on truncation.

- **Workflow drop-off pattern observed.** Two of six implementer agents (L-2 and L-6) ran `/code-review`, posted findings, but then stopped at "report findings" instead of completing the address → push → wait → merge chain. I (orchestrator) caught both: for L-2, took over the merge after addressing the comment had already pushed; for L-6, addressed the cache-token bug myself (`cafc2d2`) since the agent had stopped. L-1, L-3, L-4 followed the full workflow correctly. **Tightening the per-agent `.md` file's "PR + review" section with explicit "don't stop at report findings" language helped but didn't fully eliminate the pattern** — worth iterating again if it recurs.

- **Parallel dispatch where files are disjoint.** L-4 (frontend) + L-6 (backend) ran in parallel; only the operating-manual file overlapped, and each updated a different section. Zero merge conflicts.

- **Worktree cleanup on every cycle.** Every dispatched agent gets `isolation: "worktree"` → its own copy of the repo. The closeout step (per `orchestrate-zebu` skill) removes worktrees + prunes `worktree-agent-*` local branches. Repo state at session end: one main worktree, no orphans.

## Carry-overs / follow-ups

- **L-7 — Sample backtest report comparing identical strategy with/without agent intervention.** Exploratory data-analysis task; ~1 day. Best driven interactively (Tim watching) once a first real LIVE backtest has run on a known strategy. Deferred.
- **Workflow self-improvement.** The two-of-six drop-off rate on the post-`/code-review` merge step suggests the agent definition's "PR + review" subsection isn't quite emphatic enough. Possible iteration: have the agent record `"workflow_state": "review_posted"` in a tiny status file the orchestrator can poll, OR move the merge step into a dedicated `/finalize-pr` skill the agent must call to mark completion. Worth a small follow-up if the pattern recurs.
- **Cache-token usage on F-3 inline invocations.** L-6's cost fix added cache-read/creation accumulation in the inner Anthropic adapter's tool-use loop and single-shot path. F-3's live trigger invocations (Phase F-3 shipped earlier) go through the SAME `_extract_usage` now — so live invocation cost-tracking (whenever someone wires it up) gets the cache fix for free. No live-trigger cost-cap exists today; if someone adds one later, the plumbing is correct.
- **Agent-mode toggle gating on "user has API key configured".** L-4's prompt suggested gating the Live radio on a user-API-key check, but the existing trade-attribution check (`isUsableTradeKey`) isn't the right semantic — the LLM-cost path uses the server-side `ANTHROPIC_API_KEY`. Settled for the amber "Charges to your account" warning chip. If we ever add a per-user LLM-cost surface (e.g. user-supplied Anthropic key for separate billing), this is a one-line addition.

## Files touched (cumulative across the six PRs)

Domain / VOs:

- `backend/src/zebu/domain/value_objects/backtest_agent_invocation_mode.py` (new)
- `backend/src/zebu/domain/value_objects/backtest_safe_tool.py` (new)
- `backend/src/zebu/domain/value_objects/anthropic_pricing.py` (new)
- `backend/src/zebu/domain/entities/backtest_agent_invocation.py` (new)
- `backend/src/zebu/domain/entities/backtest_run.py` (extended)
- `backend/src/zebu/domain/exceptions.py` (added `InvalidBacktestAgentInvocationError`, `BacktestSafetyViolationError`)

Application:

- `backend/src/zebu/application/ports/backtest_agent_invocation_repository.py` (new)
- `backend/src/zebu/application/ports/in_memory_backtest_agent_invocation_repository.py` (new)
- `backend/src/zebu/application/ports/backtest_agent_invocation_factory.py` (new Protocol)
- `backend/src/zebu/application/ports/in_memory_backtest_agent_invocation_factory.py` (new test fake)
- `backend/src/zebu/application/ports/agent_invocation_port.py` (added `agent_temperature`, `cache_read_input_tokens`, `cache_creation_input_tokens` to `AgentInvocationResult`)
- `backend/src/zebu/application/ports/in_memory_agent_invocation_port.py` (added `MockBacktestAgentInvocationPort`)
- `backend/src/zebu/application/commands/run_backtest.py` (added `agent_invocation_mode`, `agent_temperature`, `agent_max_cost_usd`)
- `backend/src/zebu/application/services/backtest_executor.py` (agent integration, cost accumulator, budget halt)

Adapters / DB:

- `backend/migrations/versions/l001_backtest_agent_invocations.py` (new)
- `backend/src/zebu/adapters/outbound/database/backtest_agent_invocation_repository.py` (new SQL adapter)
- `backend/src/zebu/adapters/outbound/database/models.py` (added `BacktestAgentInvocationModel`, extended `BacktestRunModel`)
- `backend/src/zebu/adapters/outbound/anthropic/__init__.py` (exports)
- `backend/src/zebu/adapters/outbound/anthropic/agent_invocation_adapter.py` (multi-turn tool-use loop + cache-token accumulation)
- `backend/src/zebu/adapters/outbound/anthropic/backtest_agent_invocation_adapter.py` (new L-2 wrapper)
- `backend/src/zebu/adapters/outbound/anthropic/backtest_agent_invocation_factory.py` (new production factory)
- `backend/src/zebu/adapters/inbound/api/backtests.py` (API wiring + new GET endpoint)

Frontend:

- `frontend/src/components/features/backtests/RunBacktestForm.tsx` (Agent-mode radio)
- `frontend/src/components/features/backtests/AgentInvocationsSection.tsx` (new)
- `frontend/src/pages/BacktestResult.tsx` (renders the new section)
- `frontend/src/services/api/types.ts` (new DTOs + extended existing ones)
- `frontend/src/services/api/backtests.ts` (new list call)
- `frontend/src/hooks/useBacktests.ts` (new `useBacktestAgentInvocations` hook)
- `frontend/src/components/features/triggers/AgentDecisionBadge.tsx` (handles `MODIFY_STRATEGY` canonical + `MODIFY` legacy alias)
- `frontend/src/utils/formatters.ts` (new `formatSimulatedDate` helper)

Docs / specs:

- `agent_docs/tasks/217_backtest_agent_invocation_entity.md` (new — L-1 spec)
- `agent_docs/tasks/218_backtest_agent_invocation_adapter.md` (new — L-2 spec)
- `agent_docs/tasks/219_backtest_executor_agent_integration.md` (new — L-3 spec)
- `docs/agents/operating-manual.md` (§7.6 user-facing + cost-guardrails section; L-5 folded into L-4 and L-6 PRs)
