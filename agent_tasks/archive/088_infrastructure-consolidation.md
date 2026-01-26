# Task 088: Infrastructure Consolidation - Docker Compose & Environment Files

**Date**: 2026-01-11
**Agent**: quality-infra
**Branch**: Create PR against `copilot/production-ready-proxmox-deployment` (PR #118)
**Priority**: High

## Objective

Consolidate and simplify our deployment infrastructure by:
1. Eliminating docker-compose file duplication using override pattern
2. Cleaning up environment file chaos (5 files → 3 clear examples)
3. Updating deployment scripts to work with new structure
4. Preserving actual secrets during cleanup

## Context

PR #118 implements working Proxmox deployment but has technical debt:
- `docker-compose.yml` and `docker-compose.prod.yml` are ~90% duplicated
- 5 environment files with overlapping/unclear purposes
- `.env.proxmox` is committed (should be gitignored)
- Maintenance burden of keeping two compose files in sync

**Current PR Branch**: `copilot/production-ready-proxmox-deployment`

**Your Task**: Create a new branch off PR #118's branch, make these improvements, then create a PR to merge into #118's branch.

## Requirements

### 1. Docker Compose Consolidation

Use Docker Compose override pattern to eliminate duplication:

**New Structure**:
```
docker-compose.yml          # Base configuration (shared services)
docker-compose.override.yml # Dev overrides (auto-loaded, gitignored)
docker-compose.prod.yml     # Production overrides (explicit -f flag)
```

**Key Differences to Handle**:
- Container names: `papertrade-*` (base) vs `papertrade-*-dev` (dev) vs `papertrade-*-prod` (prod)
- Dockerfiles: `Dockerfile` (prod) vs `Dockerfile.dev` (dev)
- Environment: hardcoded dev values vs `.env` variables
- Volumes: dev has source code mounts for hot-reload, prod doesn't
- Restart policies: prod has `unless-stopped`, dev doesn't
- Healthcheck intervals: dev 10s, prod 30s
- Ports: frontend dev 5173, prod 80

**Implementation Guide**:
1. `docker-compose.yml` becomes the base with shared service definitions
2. `docker-compose.override.yml` contains dev-specific overrides (gitignored, with example)
3. `docker-compose.prod.yml` contains only prod-specific overrides
4. Use `extends` or ensure proper override behavior
5. Test: `docker compose up` (dev) vs `docker compose -f docker-compose.yml -f docker-compose.prod.yml up` (prod)

**Reference**: https://docs.docker.com/compose/multiple-compose-files/extends/

### 2. Environment File Cleanup

**Current Mess** (on PR #118 branch):
- `.env.example` - dev defaults
- `.env.example.proxmox` - proxmox VM config (4505 bytes)
- `.env.production.example` - app secrets (3321 bytes)
- `.env.production.template` - duplicate? (1084 bytes)
- `.env.proxmox` - **committed but should be gitignored!** (526 bytes)
- `.env` - actual secrets (1160 bytes) - gitignored

**New Structure** (3 clear files):
```
.env.example              # Local development defaults (committed)
.env.production.example   # Production secrets template (committed)
.env.proxmox.example      # Proxmox VM config template (committed)
```

**All actual `.env*` files** (except `.example` suffix) should be gitignored.

**Actions**:
1. **Preserve secrets**: Extract all actual secret values from existing `.env*` files (don't commit these!)
2. Consolidate `.env.production.example` and `.env.production.template` (keep the better one)
3. Rename `.env.example.proxmox` → `.env.proxmox.example`
4. Delete `.env.proxmox` from git (add to .gitignore)
5. Update `.gitignore` to properly ignore all non-example env files
6. Each example file should have clear header comments explaining:
   - What it's for
   - How to use it (copy to `.env` or `.env.proxmox`)
   - What values need to be changed
   - How to generate secure values (for secrets)

**Critical**: The deployment should preserve existing `.env` files on the VM (don't overwrite secrets).

### 3. Update Deployment Scripts

Scripts in `scripts/proxmox-vm/` need updates:

**Files to Update**:
- `deploy.sh` - Check `.env` file paths, ensure works with new structure
- `common.sh` - Update any env file references
- `create-vm.sh` - Check env file loading
- `lifecycle.sh` - Verify compatibility

**Key Changes**:
- Update references from `.env.production.example` to final naming
- Ensure `.env.proxmox.example` → `.env.proxmox` workflow is clear
- Update error messages about missing env files

**Test Deployment Workflow**:
1. User copies `.env.proxmox.example` to `.env.proxmox` (gitignored)
2. User copies `.env.production.example` to `.env` (gitignored)
3. User edits both files with their values
4. Scripts read from `.env.proxmox` for VM config
5. Scripts transfer `.env` to VM for application config
6. Docker Compose on VM uses `.env` for secrets

### 4. Update .gitignore

Ensure all non-example env files are ignored:
```gitignore
# Environment files (only commit .example versions)
.env
.env.local
.env.*.local
.env.production
.env.proxmox
docker-compose.override.yml
```

### 5. Preserve Secrets During Cleanup

**Before** making changes:
1. Extract all unique secret values from all `.env*` files
2. Create a temporary reference file (NOT committed) with actual values
3. After cleanup, verify all secrets are preserved in appropriate files

**Secrets to Preserve**:
- Database passwords
- API keys (Alpha Vantage, Clerk)
- Secret keys
- Any other credentials

## Success Criteria

### Functional Tests
- [ ] `docker compose up` works locally (dev mode with hot-reload)
- [ ] `docker compose -f docker-compose.yml -f docker-compose.prod.yml up` works (prod mode)
- [ ] All services start healthy in both modes
- [ ] Hot-reload works in dev mode
- [ ] Production build works without volume mounts

### File Structure Tests
- [ ] Only 3 `.env.example` files exist (committed)
- [ ] All non-example `.env` files are gitignored
- [ ] No duplicate docker-compose configurations
- [ ] All actual secrets preserved (not committed, documented)

### Script Tests
- [ ] `task proxmox-vm:deploy` still works with new env structure
- [ ] Scripts provide clear error messages for missing env files
- [ ] Documentation references match new file structure

### Documentation Tests
- [ ] All env file references updated in scripts
- [ ] README or deployment docs reference new structure
- [ ] Clear migration guide for existing deployments

## Implementation Notes

**Branching Strategy**:
```bash
# Start from PR #118's branch
git checkout copilot/production-ready-proxmox-deployment
git pull origin copilot/production-ready-proxmox-deployment

# Create your improvement branch
git checkout -b infra/consolidate-docker-env

# Make changes, commit, push
# Create PR targeting copilot/production-ready-proxmox-deployment
```

**Testing Approach**:
1. Test docker-compose changes locally first
2. Verify both dev and prod compose configurations work
3. Check that proxmox deployment scripts work with new structure
4. Document any migration steps needed

**Secret Handling**:
- Never commit actual secrets
- Provide clear examples with placeholder values
- Document how to generate secure secrets
- Ensure existing VM deployments preserve their secrets

## References

- PR #118: https://github.com/TimChild/PaperTrade/pull/118
- Docker Compose extends: https://docs.docker.com/compose/multiple-compose-files/extends/
- Current deployment docs: `docs/deployment/proxmox-vm-deployment.md`
- Current scripts: `scripts/proxmox-vm/`

## Deliverables

1. Consolidated docker-compose structure (base + overrides)
2. Clean environment file organization (3 examples)
3. Updated .gitignore
4. Updated deployment scripts
5. Migration notes (if needed)
6. PR created against PR #118's branch

## Notes

This is a cleanup/refactoring task on an existing working implementation. The goal is to reduce technical debt and improve maintainability without breaking existing functionality.
