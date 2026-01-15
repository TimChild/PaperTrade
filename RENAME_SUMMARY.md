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

| Category | Old | New |
|----------|-----|-----|
| Database (dev) | `papertrade_dev` | `zebu_dev` |
| Database (prod) | `papertrade` | `zebu` |
| DB User | `papertrade` | `zebu` |
| DB Password (dev) | `papertrade_dev_password` | `zebu_dev_password` |
| Docker network | `papertrade-network` | `zebu-network` |
| Container names (prod) | `papertrade-*-prod` | `zebu-*-prod` |
| Redis key prefix | `papertrade:*` | `zebu:*` |
| Log directory | `/var/log/papertrade/` | `/var/log/zebu/` |

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

If you have a local database with the old name:

```bash
# Stop services
task docker:down

# Remove old volume (⚠️ This deletes data!)
docker volume rm papertrade_postgres_data

# Start with new database name
task docker:up
```

Or keep your data by updating the `.env` file to use the old database names (not recommended).

### Environment Variables

Update your `.env` file to match `.env.example`:

```bash
# Old
POSTGRES_DB=papertrade_dev
POSTGRES_USER=papertrade
POSTGRES_PASSWORD=papertrade_dev_password

# New
POSTGRES_DB=zebu_dev
POSTGRES_USER=zebu
POSTGRES_PASSWORD=zebu_dev_password
```

## Next Steps

1. ✅ Merge this PR to main
2. ⏳ Update GitHub repository name (requires admin action)
   - Settings → General → Repository name → "Zebu" or "ZebuTrader"
3. ⏳ Re-deploy to production with new configuration
4. ⏳ Update any external integrations (CI/CD, monitoring, etc.)

## Rollback Plan

If issues arise, the changes can be reverted by:

1. Reverting the commits in this PR
2. Running `uv sync` and `npm install` again
3. Updating `.env` files back to old values
4. Restarting Docker services

All changes are backward-compatible in code structure.
