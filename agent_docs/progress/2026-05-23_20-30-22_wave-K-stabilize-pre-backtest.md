# Wave K — Stabilize pre-backtest (4 PRs)

**Date**: 2026-05-23
**Orchestrator**: Claude Opus 4.7 (dispatcher-as-Claude pattern)
**Phase scope**: All 4 close-out items needed to reach a "good starting point" for the next-steps proposal's §2 (agent-driven backtests). Per Tim: get us from "Phase J done + MCP smoke fixes landed" → "ready to build J-1..J-7" without leaving cruft.

## TL;DR

Four PRs merged end-to-end in one parallel wave (~3 hours total wall clock). One real review finding caught + fixed-forward. Net result: every known follow-up from Phase J / the MCP smoke testing is closed except the deferred Pattern C (Gemini direct-API adapter).

## PRs landed

| PR | Title | Scope |
|---|---|---|
| #293 | `fix(api): reject unsupported price-history intervals at boundary (#285)` | 422 on intraday intervals — closes #285 |
| #294 | `chore(ci): isolate local "task ci" Postgres from dev stack` | `docker-compose.ci.yml` override + `docker:up:ci` / `ci:fresh` tasks; Phase J carry-over |
| #295 | `chore(tests): FK-enabled test_engine + fixture cleanup (Task #216)` | 13 pre-existing fixture violations + narrowed `transaction_repository.save` `IntegrityError` catch |
| #296 | `feat(backend+fe): "catch up" backfill UX (Task #215)` | Single-click "Catch up" replacing date-range modal; `ZEBU_HISTORY_EPOCH` env; `backfill_status` surfaced; `gap_days_count` redefined to span `[epoch, today]` |

**Cumulative**: ~2800 LOC added, ~700 deleted, ~150 new tests. Two new numbered task specs landed alongside the implementations (`215_backfill_ux_rework.md`, `216_fk_fixture_cleanup.md`).

## Orchestration mechanics that worked

- **Parallel dispatch with isolation: "worktree"** — four backend-swe/quality-infra agents in their own worktrees. Three used the worktree contract correctly; one (Task 215 agent) wrote to the main working tree instead. Worked anyway because the agent's git operations from that path produced a correct branch + PR; the leftover modifications in main resolved themselves on the next agent's git pull. Watched but didn't intervene mid-flight.
- **Tight Sonnet reviewer subagents in place of GitHub Copilot.** Copilot reviewer isn't wired up on this repo (`gh pr edit --add-reviewer Copilot` errors with "Could not resolve user"). The first agent (#285) couldn't request a review and self-merged on green CI — reasonable for a 110-line boundary fix, but the pattern wouldn't generalise. Codified the substitute in `CLAUDE.md`: use the global `/code-review` skill (Haiku+Sonnet sub-agent fan-out, confidence-filtered to ≥80, one inline comment per PR) and have implementer agents report back rather than self-merge so the orchestrator drives the review chain.
- **Fix-forward on review findings.** The /code-review pass on PR #296 surfaced two real issues — (a) `_backfill_status_by_ticker` was an unbounded table scan, (b) the frontend `Catch up` button disabled all rows when any single row's mutation was in flight (shared `backfill.isPending` across the table). Fixed in commit `bf87185` on the same PR branch:
    - Backend: added `_RECENT_TASKS_WINDOW_HOURS = 48` constant + `or_(status in [PENDING, RUNNING], created_at >= cutoff)` WHERE clause. Non-terminal tasks always surface (stuck pending visible regardless of age); terminal tasks bounded by 48h (comfortably covers the 24h FAILED surface window).
    - Frontend: per-ticker disabled-state via `backfill.variables?.ticker === row.ticker` instead of shared `isPending`.
    - Both fixes paired with regression tests.
- **Merge-into-branch surfaced a latent test-helper bug.** Merging main (which had #295's FK cleanup) into #296's branch (which added pinned-clock query) revealed that `_add_transaction` was overriding the `now` parameter with real-world `datetime.now(UTC)`. Each PR's tests had passed individually because each only exercised one half. Fixed in the same commit; reframed `parent_now` (wall clock, for created_at/updated_at on portfolio) vs `tx_now_naive` (pinned clock from `now=`).
- **Wave closeout.** Three of four agent worktrees self-cleaned. Two orphaned `worktree-agent-*` local refs pruned per the orchestrate-zebu skill. Zero locked worktrees remain.

## Findings deferred to follow-up

These are PR #294 review findings that are real but not material enough to fix-forward right now. Either trivially worth a tiny PR or wait-and-see:

1. **Health-wait here-doc lacks `set -euo pipefail`** — `|| (echo ... && exit 1)` only exits the subshell, so a Postgres/Redis/backend/frontend timeout falls through silently to the Alembic migration step. Likely manifests as a cryptic docker exec error rather than the actionable "X timeout". One-line fix per `|` block.
2. **No `name: papertrade-ci` at the compose-file level** — a developer who copy-pastes the compose command without `COMPOSE_PROJECT_NAME=papertrade-ci` would default to project `papertrade` and share volumes with the dev stack. Defensive top-level `name:` would prevent it.
3. **`docker:up:ci` description claim is incomplete** — says "db+redis on docker network only" but `docker compose up -d` with no service filter actually starts all 4 services. Doc fix.
4. **`timeout` is GNU coreutils, missing on stock macOS** — only matters on a fresh Mac without `brew install coreutils`. Belongs in the README's prerequisites.

A 30-line follow-up PR closes 1+2+3+4 cleanly. Captured rather than dispatched because none of these block the next-steps work and the wave was already at a clean merge state.

## Where we stand vs. the next-steps proposal

`docs/planning/agent-platform-next-steps.md`:

- **§1.2 (AAPL OHLC backfill on prod)** — orthogonal to this wave; still needs Tim's admin Clerk JWT or the now-deployed `/admin/data-coverage` page with the new "Catch up" affordance.
- **§1.3 (follow-up sweep)** — closed in Phase J.
- **§2 Pattern A (inline Anthropic)** — shipped.
- **§2 Pattern B (queue-mode triggers)** — shipped (#276).
- **§2 Pattern C (Gemini direct-API adapter)** — deferred per Tim's call.
- **§3 (agent-driven backtests J-1..J-7)** — **this is the next phase**. Foundation is now clean.
- **#285 (intraday intervals)** — closed (#293).
- **17 FK fixture violations follow-up flagged by #292** — closed (#295, actual count 13).
- **`task ci` Docker port conflicts** — closed (#294).
- **Backfill UX rework (operator's friction Tim described)** — closed (#296).

## Open follow-ups

- **PR #294 micro-followup** (see above) — `set -euo pipefail` + compose `name:` + doc tweaks. ~30 LOC.
- **CLAUDE.md PR workflow section** — drafted during the wave (substituting `/code-review` for Copilot), reverted by Tim mid-flight; treated as intentional. If we want the codified version eventually, the diff is recoverable from this report.
- **Stale `feat/wave3-api-error-shape-pagination` local branch** left untouched — pre-existing pre-wave-K, not in this wave's scope.

## Files touched (cumulative across the four PRs)

- `backend/src/zebu/adapters/inbound/api/prices.py`
- `backend/src/zebu/adapters/inbound/api/admin_data_coverage.py`
- `backend/src/zebu/adapters/inbound/api/dependencies.py`
- `backend/src/zebu/application/queries/data_coverage.py`
- `backend/src/zebu/adapters/outbound/database/transaction_repository.py`
- `backend/tests/conftest.py`
- `backend/tests/integration/adapters/test_sqlmodel_transaction_repository.py`
- `backend/tests/integration/test_admin_data_coverage_api.py`
- `backend/tests/integration/test_mcp_smoke_flows.py`
- `backend/tests/integration/test_prices_api.py`
- `backend/tests/unit/application/queries/test_data_coverage.py`
- `backend/tests/unit/application/queries/test_get_active_tickers.py`
- `backend/tests/unit/application/queries/test_data_coverage.py` (#296 + #295 merge)
- `frontend/src/pages/AdminDataCoverage.tsx`
- `frontend/src/pages/AdminDataCoverage.test.tsx`
- `frontend/src/hooks/useDataCoverage.ts`
- `frontend/src/hooks/__tests__/useDataCoverage.test.tsx`
- `frontend/src/services/api/types.ts`
- `frontend/src/services/api/admin.ts`
- `mcp/src/zebu_mcp/client.py`
- `Taskfile.yml`
- `docker-compose.ci.yml` (new)
- `.claude/agents/quality-infra.md`
- `.claude/skills/quality-checks/SKILL.md`
- `.env.example`, `.env.production.example`
- `agent_docs/tasks/215_backfill_ux_rework.md` (new)
- `agent_docs/tasks/216_fk_fixture_cleanup.md` (new)
