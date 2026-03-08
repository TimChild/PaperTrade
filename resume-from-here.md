# Resume From Here

> **Written**: March 8, 2026 (updated)
> **Purpose**: Temporary file for the next agent/session to quickly understand current state. Delete after reading.

## Current State

**Production is deployed and healthy** at `192.168.4.112` (Proxmox VM). All services running at zebutrader.com.

**All phases (1–4) are COMPLETE. v1.0.0 deployed to production.**

**CD pipeline is live** — push to main auto-deploys to production via self-hosted runner.

**No open PRs.** Repository is clean on main.

**Test count**: 831 backend tests (0 skipped), 311 frontend tests.

## What Was Done (March 8, 2026)

### CD Pipeline & Versioning (pushed to main)
- Self-hosted GitHub Actions runner (`papertrade-proxmox`) on production VM
- `.github/workflows/cd.yml` — auto-deploy on push to main
- Hatch dynamic versioning: `backend/src/zebu/__init__.py` → `__version__ = "1.0.0"`
- Frontend `package.json` version bumped to 1.0.0
- Docker builds fixed for hatch version source (copy `__init__.py` before pip install)
- Deploy uses `actions/checkout@v4` + `COMPOSE_PROJECT_NAME=papertrade`
- Health checks for all 4 services, concurrency control, `[skip deploy]` support

### PR #207 — Frontend Backtesting UI (Merged)
- Strategy creation forms, backtest management, comparison UI, performance charts

### PR #208 — Documentation Cleanup (Merged)
- BACKLOG.md pruned, PROGRESS.md updated, README.md synced

### Docs & Planning
- Created `agent_docs/reusable/docs_tidy.md` — reusable docs cleanup procedure
- Created `agent_docs/tasks/210_live_strategy_execution.md` — next major feature task

## Next Steps (Priority Order)

1. **Live strategy execution** (Task #210) — the natural next major feature
   - Backend SWE: StrategyActivation entity, execution service, scheduler integration, API
   - Frontend SWE: Activate button, status display, execution log
   - Task file: `agent_docs/tasks/210_live_strategy_execution.md`
2. **Alembic in CD pipeline** — add `alembic upgrade head` to cd.yml when first migration arrives
3. **Error monitoring** — Sentry for frontend
4. **S&P 500 benchmark** — overlay on backtest charts

## Key Architecture

- CD workflow: `.github/workflows/cd.yml`
- Self-hosted runner: `papertrade-proxmox` (systemd service on VM)
- Deploy strategy: `actions/checkout@v4` → docker compose build/up in runner workspace
- Production .env: `/opt/papertrade/.env` (copied into workspace during deploy)
- Version source: `backend/src/zebu/__init__.py` (hatch dynamic version)

## Useful Commands

```bash
task quality:backend      # Format + lint + type check + test backend
task quality:frontend     # Format + lint + type check + test frontend
task proxmox-vm:status    # Check production health
# CD pipeline: just push to main — deployment is automatic
```
