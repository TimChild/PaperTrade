# Resume From Here

> **Written**: March 8, 2026
> **Purpose**: Temporary file for the next agent/session to quickly understand current state. Delete after reading.

## Current State

**Production is deployed and healthy** at `192.168.4.112` (Proxmox VM). All services running.

**Phase 4 (Trading Strategies & Backtesting) is COMPLETE.** Deployed to production.

**No open PRs.** Repository is clean on main.

**Test count**: 831 backend tests passing, 4 skipped.

## What Was Done This Session (March 8, 2026)

### Phase 4 Implementation — Complete

All phases implemented via GitHub Copilot agents (`gh agent-task create`), orchestrated from local VS Code:

| PR | Phase | Description |
|----|-------|-------------|
| #201 | 4.1 prereq | `trade_factory.py` extraction, `backfill_snapshots()` bug fix |
| #202 | 4.1 | Domain entities, value objects, migrations, repos |
| #203 | 4.2 | `BacktestExecutor`, `BacktestTransactionBuilder`, `HistoricalDataPreparer`, Buy & Hold strategy, CRUD API endpoints |
| #204 | 4.3 | DCA + MA Crossover strategies, encapsulation fix, strategy parameter validation, portfolio type filtering |
| #205 | — | Dark mode fix for analytics performance summary cards |
| #206 | 4.4 | Ticker validation, 503 error handling, integration tests, docs |

### Orchestration Guide Updated

`agent_docs/orchestration-guide.md` updated with learnings:
- Task scoping guidance (scope by functional area, not micro-tasks)
- Fix-forward pattern (address small quality issues in next task, don't accumulate)
- Effective review workflow (checkout, read key files, run tests, check CI)
- Parallel execution patterns (local sub-agents for quick UI fixes while backend agents run)

## What's Next

Phase 4 is done. Potential next work:

1. **Frontend for backtesting** — UI to create strategies, run backtests, view results. No frontend for Phase 4 was built — only backend API endpoints exist. This would be the natural next step.
2. **Strategy comparison views** — Compare multiple backtest runs side by side
3. **Live paper-trading UI improvements** — Based on user feedback
4. **`full-stack-swe.md` agent** — TODO to create a combined frontend+backend agent for cross-cutting tasks
5. **Production deployment automation** — Consider running `alembic upgrade head` automatically in deploy script

### Key Architecture Reference

- Design doc: `docs/architecture/phase4-trading-strategies.md`
- Backend API endpoints: `POST/GET/DELETE /api/v1/strategies`, `POST/GET/DELETE /api/v1/backtests`
- Portfolio filtering: `GET /api/v1/portfolios?include_backtest=true` (backtest portfolios excluded by default)
- Orchestration guide: `agent_docs/orchestration-guide.md`
- Synchronous execution for v1 (3-year max date range)
- Pre-fetch all price data before simulation loop
- Summary metrics stored on `BacktestRun` entity (not a separate table for v1)

### Open Questions (see design doc Section 10)

Fractional shares, MA warm-up period, strategy deletion behavior, failure cleanup, concurrent backtests, backtest portfolio immutability, rate limit handling.

## Useful Commands

- `task docs:serve` — Serve MkDocs locally (uses `uvx`, no install needed)
- `task quality:backend` — Format + lint + type check + test backend
- `task quality:frontend` — Format + lint + type check + test frontend
- `task proxmox-vm:deploy` — Deploy to production
- `task proxmox-vm:status` — Check production health

## Test Counts (as of this session)

- Backend: ~717 tests passing
- Frontend: ~263 tests passing
