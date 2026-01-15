# Rename Follow-up Tasks

This document lists items that still require manual updates to complete the transition from PaperTrade to Zebu.

## Critical Items

### 1. GitHub Repository Name
**Status**: ⏳ Pending (requires admin action)

The GitHub repository name is still `TimChild/PaperTrade` and needs to be manually renamed.

**Steps**:
1. Go to repository Settings → General
2. Change repository name from "PaperTrade" to "Zebu" or "ZebuTrader"
3. Update any external integrations that reference the old repository name

**Impact**:
- Git clone URLs will change
- Existing clones will need to update their remote URL: `git remote set-url origin https://github.com/TimChild/Zebu.git`
- CI badges in README.md will need updating

### 2. Database Migration (Future)
**Status**: ⏳ Optional (deferred)

Database identifiers were intentionally kept as `papertrade` to avoid requiring immediate migration:
- Database name: `papertrade_dev` (development), `papertrade` (production)
- Database user: `papertrade`
- SQLite filename: `papertrade.db`

**When to migrate**:
- When doing a fresh production deployment
- During a planned maintenance window
- When migrating to new infrastructure

**Migration steps** (when ready):
1. Create database dump: `pg_dump -U papertrade papertrade > backup.sql`
2. Create new database: `CREATE DATABASE zebu_dev;`
3. Create new user: `CREATE USER zebu WITH PASSWORD 'secure_password';`
4. Restore data: `psql -U zebu zebu_dev < backup.sql`
5. Update `.env` files to use new database identifiers
6. Test thoroughly before removing old database

### 3. Proxmox VM Redeployment
**Status**: ⏳ Pending

The production Proxmox VM needs to be redeployed with the new branding.

**Steps**:
1. Update `.env.proxmox` with new configuration
2. Run deployment script: `./scripts/proxmox-vm/deploy.sh`
3. Update PROXMOX_VM_HOSTNAME to `zebu` (currently may be `papertrade`)
4. Update APP_DIR to `/opt/zebu` (currently may be `/opt/papertrade`)
5. Test the deployed application
6. Update DNS/domain configuration for zebutrader.com

**Files to review before deployment**:
- `.env.proxmox`
- `scripts/proxmox-vm/deploy.sh`
- `scripts/proxmox-vm/create-vm.sh`

## References That Cannot Be Changed

### Git Clone URLs in Scripts
**Status**: ✅ Acceptable

Scripts that clone the repository will continue to use the old repository name until the GitHub repository is renamed:
```bash
git clone https://github.com/TimChild/PaperTrade.git
```

**Files affected**:
- `scripts/proxmox-vm/deploy.sh`
- `.github/copilot-instructions.md` (example path references)

**Action**: Update these after GitHub repository rename is complete.

### Historical Documentation
**Status**: ✅ Intentionally Preserved

Historical documentation is intentionally unchanged to preserve project history:
- `agent_progress_docs/` - Historical agent work logs
- `architecture_plans/` - Historical architecture decisions
- Git commit messages

**Action**: No changes needed or wanted.

### Local File Paths
**Status**: ✅ Acceptable

Some configuration files contain local file paths that reference the old repository name:
- `.vscode/mcp.json` - Line 39: `/Users/timchild/github/PaperTrade`
- `.github/copilot-instructions.md` - pylancePythonEnvironments path

**Action**: These are local paths and will naturally update when developers clone the renamed repository.

## External Integrations

### Domain Configuration
**Status**: ✅ Ready

Domain `zebutrader.com` is already registered (per Task 089).

**Steps**:
1. Configure NPMplus reverse proxy for zebutrader.com
2. Update CORS origins in backend configuration
3. Update frontend VITE_API_BASE_URL for production
4. Test SSL certificate generation

### Monitoring & Alerting
**Status**: ⏳ Review Needed

Any monitoring or alerting services may reference "PaperTrade":
- Application names in monitoring dashboards
- Alert notification messages
- Log aggregation service names

**Action**: Review and update as needed.

### Third-Party Services
**Status**: ⏳ Review Needed

Services that may need updating:
- Clerk authentication (check application name in dashboard)
- Alpha Vantage API (no changes needed - API key works regardless)
- Any analytics or error tracking services

**Action**: Review service dashboards and update branding as needed.

## Completed Items ✅

- ✅ Python package renamed: `papertrade` → `zebu`
- ✅ NPM package renamed: `papertrade-frontend` → `zebu-frontend`
- ✅ All Python imports updated
- ✅ User-facing text and UI updated
- ✅ API titles and messages updated
- ✅ Docker network names updated
- ✅ Redis key prefixes updated: `papertrade:*` → `zebu:*`
- ✅ Documentation updated (README, CONTRIBUTING, all docs/)
- ✅ Agent instructions updated
- ✅ Deployment scripts comments updated
- ✅ Test email addresses updated: `@papertrade.dev` → `@zebutrader.com`
- ✅ All tests passing (545 backend, 197 frontend)

## Timeline

| Task | Priority | Estimated Effort | Target Date |
|------|----------|------------------|-------------|
| GitHub repository rename | High | 15 minutes | After PR merge |
| Update CI badges | Medium | 5 minutes | After repo rename |
| Proxmox VM redeployment | Medium | 2 hours | When ready for production |
| Database migration | Low | 1 hour | Future maintenance window |
| External integrations review | Low | 1 hour | Ongoing |

## Notes

- The database identifiers were intentionally kept as `papertrade` to maintain backward compatibility and avoid forcing immediate migration.
- This approach allows the code to be fully rebranded while keeping data migration as an optional future task.
- When the GitHub repository is renamed, many of these follow-up tasks will be easier to complete.
