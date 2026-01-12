# Infrastructure Consolidation - Docker Compose & Environment Files

**Branch**: `infra/consolidate-docker-env`  
**Target**: PR #118 (`copilot/production-ready-proxmox-deployment`)  
**Date**: 2026-01-12

## Summary

This change consolidates Docker Compose and environment files to eliminate duplication and improve maintainability.

## What Changed

### Docker Compose Files (Before → After)

**Before**:
- `docker-compose.yml` - 134 lines (dev configuration)
- `docker-compose.prod.yml` - 113 lines (prod configuration)
- ~90% duplication between files

**After**:
- `docker-compose.yml` - Base configuration (shared services)
- `docker-compose.override.yml.example` - Dev-specific settings (gitignored template)
- `docker-compose.prod.yml` - Production-specific settings only

**Savings**: Reduced from 247 lines to ~220 lines, eliminated all duplication

### Environment Files (Before → After)

**Before** (5 files):
- `.env.example` - Dev defaults
- `.env.example.proxmox` - Proxmox VM config
- `.env.production.example` - Production secrets template (3321 bytes)
- `.env.production.template` - Duplicate template (1084 bytes)
- `.env.proxmox` - Committed accidentally (526 bytes)

**After** (3 files):
- `.env.example` - Local development defaults
- `.env.production.example` - Application secrets template
- `.env.proxmox.example` - VM infrastructure configuration

**Result**: Clear separation of concerns, no duplicates, proper gitignore

## How to Use

### Development Mode

```bash
# 1. Copy override file (one-time setup)
cp docker-compose.override.yml.example docker-compose.override.yml

# 2. Start services (automatically uses override)
docker compose up

# Features enabled:
# - Source code volume mounts for hot-reload
# - Development container names (-dev suffix)
# - Trust-based PostgreSQL authentication
# - Development Dockerfiles (Dockerfile.dev)
```

### Production Mode

```bash
# Explicit -f flags required for production
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Features enabled:
# - Production Dockerfiles (optimized builds)
# - Production container names (-prod suffix)
# - No source code mounts (security)
# - Automatic restart policies
# - Extended healthcheck intervals
```

### Environment Configuration

```bash
# For local development
cp .env.example .env
# Edit .env with API keys if needed (ALPHA_VANTAGE_API_KEY, CLERK_*)

# For production deployment
cp .env.production.example .env
# Edit .env with secure secrets (required!)

# For Proxmox VM deployment
cp .env.proxmox.example .env.proxmox
# Edit .env.proxmox with your Proxmox host and VM config
```

## Migration Guide

### For Existing Local Developers

1. Copy the dev override file:
   ```bash
   cp docker-compose.override.yml.example docker-compose.override.yml
   ```

2. Your existing `.env` file is preserved (no changes needed)

3. Continue using `docker compose up` as before

### For Existing Production Deployments

1. No code changes required - deployment scripts handle everything

2. Your existing `.env` file on the VM is preserved

3. If you have `.env.proxmox`, it's now gitignored (good!)

4. Rename local file:
   ```bash
   # If you have this file locally (not on VM)
   mv .env.example.proxmox .env.proxmox.example  # Now matches repo
   ```

## Benefits

1. **Reduced Duplication**: Base config shared, overrides only where needed
2. **Clear Separation**: Dev vs Prod intentions are explicit
3. **Better Security**: All non-example .env files properly gitignored
4. **Easier Maintenance**: Change base once, applies to all environments
5. **Better Documentation**: Clear headers explain each file's purpose

## Technical Details

### Docker Compose Override Pattern

Docker Compose automatically loads `docker-compose.override.yml` if present:

```bash
# These are equivalent:
docker compose up
docker compose -f docker-compose.yml -f docker-compose.override.yml up
```

For production, we explicitly specify files to skip the override:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up
```

### Key Differences

| Aspect | Development | Production |
|--------|-------------|------------|
| Container names | `*-dev` | `*-prod` |
| Dockerfiles | `Dockerfile.dev` | `Dockerfile` |
| Volumes | Source code mounted | No mounts |
| Restart | No restart | `unless-stopped` |
| Healthcheck interval | 10s | 30s |
| Frontend port | 5173 | 80 |
| PostgreSQL auth | Trust mode | Password required |

## Files Modified

- ✏️ `docker-compose.yml` - Converted to base config
- ✏️ `docker-compose.prod.yml` - Reduced to production overrides only
- ➕ `docker-compose.override.yml.example` - New dev override template
- ✏️ `.env.example` - Updated header with clear instructions
- ✏️ `.env.production.example` - Updated header, better organization
- 🔄 `.env.example.proxmox` → `.env.proxmox.example` - Renamed
- ❌ `.env.production.template` - Removed (duplicate)
- ❌ `.env.proxmox` - Removed from git (should be gitignored)
- ✏️ `.gitignore` - Added explicit .env file rules
- ✏️ `docs/deployment/proxmox-vm-deployment.md` - Updated references
- ✏️ `scripts/proxmox-vm/create-vm.sh` - Fixed env file references
- ✏️ `scripts/proxmox-vm/README.md` - Updated documentation

## Validation

All changes tested and validated:

✅ Dev mode config validates: `docker compose config --quiet`  
✅ Prod mode config validates: `docker compose -f docker-compose.yml -f docker-compose.prod.yml config --quiet`  
✅ Container naming correct: `-dev` vs `-prod` suffixes  
✅ Volumes correct: Mounts in dev, none in prod  
✅ Dockerfiles correct: `Dockerfile.dev` vs `Dockerfile`  
✅ Secrets preserved: Backed up to `/tmp` (not committed)  
✅ Documentation updated: All references point to new file names  

## Next Steps

1. Review this PR
2. Test locally with `docker compose up`
3. Merge into PR #118
4. Deploy to Proxmox VM for integration testing
5. Monitor for any issues

## Questions?

See the updated documentation in:
- `docs/deployment/proxmox-vm-deployment.md`
- `scripts/proxmox-vm/README.md`
