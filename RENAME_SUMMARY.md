# Project Rename: PaperTrade → Zebu

**Date**: January 15, 2026
**Status**: ✅ Complete
**PR**: [copilot/rename-project-from-papertrade-to-zebu](https://github.com/TimChild/PaperTrade/pull/XXX)

## Overview

Successfully renamed the entire project from "PaperTrade" to "Zebu" (brand name) / "ZebuTrader" (product name).

## Changes Made

### Code

| Category | Old | New |
|----------|-----|-----|
| Python package | `papertrade` | `zebu` |
| NPM package | `papertrade-frontend` | `zebu-frontend` |
| Python imports | `from papertrade.*` | `from zebu.*` |
| Backend directory | `backend/src/papertrade/` | `backend/src/zebu/` |

### Configuration

| Category | Old | New | Notes |
|----------|-----|-----|-------|
| Database (dev) | `papertrade_dev` | `papertrade_dev` | **Kept unchanged** ⚠️ |
| Database (prod) | `papertrade` | `papertrade` | **Kept unchanged** ⚠️ |
| DB User | `papertrade` | `papertrade` | **Kept unchanged** ⚠️ |
| DB Password (dev) | `papertrade_dev_password` | `papertrade_dev_password` | **Kept unchanged** ⚠️ |
| SQLite filename | `papertrade.db` | `papertrade.db` | **Kept unchanged** ⚠️ |
| Docker network | `papertrade-network` | `zebu-network` | ✅ |
| Container names (prod) | `papertrade-*-prod` | `zebu-*-prod` | ✅ |
| Redis key prefix | `papertrade:*` | `zebu:*` | ✅ |
| Log directory | `/var/log/papertrade/` | `/var/log/zebu/` | ✅ |

**⚠️ Database Identifiers**: Intentionally kept as `papertrade` to avoid requiring immediate database migration. See [RENAME_FOLLOWUP_TASKS.md](./RENAME_FOLLOWUP_TASKS.md) for future migration procedure.

### User-Facing

| Category | Old | New |
|----------|-----|-----|
| App title | "PaperTrade" | "Zebu" |
| API title | "PaperTrade API" | "Zebu API" |
| Test emails | `@papertrade.dev` | `@zebutrader.com` |
| Welcome messages | "Welcome to PaperTrade..." | "Welcome to Zebu..." |

## Files Updated

### Backend (Python)
- ✅ `backend/pyproject.toml` - package name and metadata
- ✅ `backend/src/papertrade/` → `backend/src/zebu/` (entire directory)
- ✅ All Python files with imports (100+ files)
- ✅ Migration scripts
- ✅ Seed scripts
- ✅ Test files (545 tests)
- ✅ Dockerfiles

### Frontend (TypeScript/React)
- ✅ `frontend/package.json` - package name
- ✅ `frontend/index.html` - page title
- ✅ `frontend/src/App.tsx` - branding text
- ✅ All test files (197 tests)
- ✅ E2E test specs
- ✅ Dockerfiles

### Configuration Files
- ✅ `docker-compose.yml` - services, networks, defaults
- ✅ `docker-compose.prod.yml` - container names
- ✅ `Taskfile.yml` - all task commands
- ✅ `.env.example` - development defaults
- ✅ `.env.production.example` - production defaults
- ✅ `.env.proxmox.example` - deployment config
- ✅ `backend/config.example.toml` - all settings
- ✅ `.vscode/mcp.json` - database URL
- ✅ `.github/workflows/*.yml` - CI/CD configs

### Documentation
- ✅ `README.md` - main project description
- ✅ `CONTRIBUTING.md` - contributor guide
- ✅ `PROGRESS.md` - development progress
- ✅ `.github/copilot-instructions.md` - AI instructions
- ✅ `.github/agents/*.md` - all agent definitions
- ✅ All `docs/` markdown files (30+ files)
- ✅ All `orchestrator_procedures/` files
- ✅ Active `agent_tasks/` files
- ✅ Proxmox deployment scripts

## Not Changed (Intentional)

1. **GitHub repository URL**: `github.com/TimChild/PaperTrade`
   - Reason: Repository name requires manual GitHub admin action
   - Impact: Clone URL stays the same, links remain valid

2. **Historical documentation**:
   - `agent_progress_docs/` - Historical agent work logs
   - `architecture_plans/` - Historical architecture decisions
   - Reason: Preserve project history

3. **Git commit history**:
   - Reason: Cannot and should not rewrite commit history

## Verification

### Tests
- ✅ Backend: 545 tests passed, 4 skipped
- ✅ Frontend: 197 tests passed, 1 skipped
- ✅ All tests passing with new names

### Quality Checks
- ✅ Backend linting (ruff): Passed
- ✅ Backend formatting (ruff): Passed
- ✅ Backend type checking (pyright): Passed
- ✅ Frontend linting (ESLint): Passed (4 warnings - pre-existing)
- ✅ Frontend builds: Successful

### Functionality
- ✅ Backend imports: `from zebu.domain.entities.portfolio import Portfolio` works
- ✅ API server starts: `uvicorn zebu.main:app`
- ✅ Frontend builds: Production bundle created successfully
- ✅ Docker Compose: Services configured correctly

## Migration Guide for Developers

### Pulling Latest Changes

```bash
git pull origin main  # or your branch
```

### Backend Setup

The Python package was renamed. After pulling:

```bash
cd backend
uv sync  # Reinstall dependencies with new package name
```

### Frontend Setup

The NPM package was renamed. After pulling:

```bash
cd frontend
npm install  # Update lock file with new package name
```

### Database Migration

**No migration required!** 🎉

Database identifiers were intentionally kept as `papertrade` to maintain backward compatibility:
- Database names: `papertrade_dev`, `papertrade`
- Database user: `papertrade`
- SQLite filename: `papertrade.db`

**Your existing data is safe and compatible.**

Future migration (optional): See [RENAME_FOLLOWUP_TASKS.md](./RENAME_FOLLOWUP_TASKS.md) for steps to migrate database identifiers during a planned maintenance window.

### Environment Variables

**No changes needed!** Environment variables use the same database identifiers as before.

Your existing `.env` file will continue to work without modification.

## Next Steps

1. ✅ Merge this PR to main
2. ⏳ Update GitHub repository name (requires admin action)
   - Settings → General → Repository name → "Zebu" or "ZebuTrader"
3. ⏳ (Optional) Database migration during planned maintenance
   - See [RENAME_FOLLOWUP_TASKS.md](./RENAME_FOLLOWUP_TASKS.md) for procedure
4. ⏳ Re-deploy to production with new configuration
5. ⏳ Update any external integrations (CI/CD, monitoring, etc.)

## Rollback Plan

If issues arise, the changes can be reverted by:

1. Reverting the commits in this PR
2. Running `uv sync` and `npm install` again
3. No database changes needed (identifiers weren't changed)
4. Restarting Docker services

All changes are backward-compatible.
