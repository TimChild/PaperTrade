# Resume From Here

> **Written**: March 8, 2026
> **Purpose**: Temporary file for the next agent/session to quickly understand current state. Delete after reading.

## Current State

**Production is deployed and healthy** at `192.168.4.112` (Proxmox VM). All services running at zebutrader.com.

**All phases (1–4) are COMPLETE and deployed to production**, including the Phase 4 frontend backtesting UI.

**No open PRs.** Repository is clean on main.

**Test count**: 835 backend tests passing (4 skipped), 311 frontend tests.

## What Was Done (March 8, 2026)

### PR #207 — Frontend Backtesting UI (Merged)
- Strategy creation and configuration forms (Buy & Hold, DCA, MA Crossover)
- Backtest run management: trigger runs, list history, view detailed results
- Performance chart showing portfolio value over time with trade markers
- Strategy comparison UI: side-by-side metrics for multiple backtest runs

### Documentation Cleanup (PR #208)
- BACKLOG.md rewritten — completed items removed, only actual backlog remains
- PROGRESS.md updated — Phase 4 frontend added, test counts corrected (1,146 total)
- README.md updated — feature list reflects all completed phases, Python version corrected
- `session_handoff.md` moved from `agent_docs/procedures/` to `agent_docs/reusable/`
- `agent_docs/procedures/` directory removed

## Current Focus Areas

1. **CD pipeline automation** — `alembic upgrade head` should run automatically in deploy script
2. **Live strategy execution** — next major feature (scheduled paper-trading based on saved strategies)
3. **Error monitoring** — Sentry for frontend, structlog already in place for backend

## Key Architecture Reference

- Design doc: `docs/architecture/phase4-trading-strategies.md`
- Backend API: `POST/GET/DELETE /api/v1/strategies`, `POST/GET/DELETE /api/v1/backtests`
- Portfolio filtering: `GET /api/v1/portfolios?include_backtest=true` (backtest portfolios excluded by default)
- Orchestration guide: `agent_docs/orchestration-guide.md`

## Useful Commands

```bash
task docs:serve           # Serve MkDocs locally
task quality:backend      # Format + lint + type check + test backend
task quality:frontend     # Format + lint + type check + test frontend
task proxmox-vm:deploy    # Deploy to production
task proxmox-vm:status    # Check production health
```
