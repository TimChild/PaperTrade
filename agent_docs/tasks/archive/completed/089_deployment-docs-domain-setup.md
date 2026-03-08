# Task 089: Deployment Documentation & Domain Setup Guide

**Date**: 2026-01-11
**Agent**: quality-infra
**Branch**: Create PR against `copilot/production-ready-proxmox-deployment` (PR #118)
**Priority**: High

## Objective

Update deployment documentation and create comprehensive domain setup guide:
1. Fix proxmox deployment docs (remove outdated tarball references)
2. Create domain/SSL setup guide (NPMplus + Cloudflare)
3. Add production readiness checklist
4. Ensure all docs reflect new env file structure (from Task 088)

## Context

PR #118 has working deployment but documentation needs updates:
- Some docs reference outdated tarball deployment approach
- No guidance on domain setup (zebutrader.com + NPMplus)
- Missing SSL/HTTPS configuration
- Env file references will change after Task 088

**Current PR Branch**: `copilot/production-ready-proxmox-deployment`

**Your Task**: Create a new branch off PR #118's branch, update docs, then create a PR to merge into #118's branch.

**Important**: This task can proceed in parallel with Task 088. If env file structure changes, you'll need to update references, but the domain setup guide is independent.

## Requirements

### 1. Update Proxmox Deployment Docs

**File**: `docs/deployment/proxmox-vm-deployment.md`

**Issues to Fix**:
- Remove/update any references to tarball deployment
- Confirm all workflow descriptions match actual implementation (git clone/pull)
- Update environment file references to match new structure (`.env.proxmox.example`, etc.)
- Ensure script commands are accurate
- Add troubleshooting section if missing

**Current Implementation** (verify in `scripts/proxmox-vm/deploy.sh`):
- Uses git clone on first deployment
- Uses git pull on subsequent deployments
- Preserves `.env` on VM across redeployments
- No tarball creation/transfer

**Action Items**:
1. Read `scripts/proxmox-vm/deploy.sh` to understand actual flow
2. Update docs to accurately reflect implementation
3. Remove any tarball references
4. Update env file paths/names (coordinate with Task 088 if needed)
5. Add section on updating deployments (git pull workflow)

### 2. Create Domain Setup Guide

**New File**: `docs/deployment/domain-and-ssl-setup.md`

This is a comprehensive, one-time setup guide for configuring a domain name with SSL.

**Assumptions**:
- App is already running on Proxmox VM (IP: 192.168.4.111)
- Domain registered: `zebutrader.com` (Cloudflare DNS)
- NPMplus (Nginx Proxy Manager) available on Proxmox host (192.168.4.200)
- User has Cloudflare account access

**Guide Should Cover**:

#### Part 1: DNS Configuration (Cloudflare)
- Log into Cloudflare dashboard
- Navigate to DNS settings for zebutrader.com
- Create A record pointing to Proxmox host public IP (or local if behind NAT)
- Proxy settings (proxied vs DNS only)
- Subdomain setup if desired (app.zebutrader.com)

#### Part 2: NPMplus Configuration
**What is NPMplus**: Pre-installed Nginx reverse proxy manager on Proxmox host

**Steps**:
1. Access NPMplus web interface (typically http://192.168.4.200:81)
2. Login with admin credentials
3. Add new proxy host:
   - Domain name: zebutrader.com (or app.zebutrader.com)
   - Scheme: http
   - Forward hostname/IP: 192.168.4.111 (VM IP)
   - Forward port: 80 (frontend)
   - Websockets support: Enabled (if needed)
4. Configure SSL:
   - Request Let's Encrypt certificate
   - Force SSL toggle
   - HTTP/2 support
5. Save and test

#### Part 3: Backend CORS Configuration
**Issue**: Frontend on zebutrader.com needs to call backend API

**Solutions**:
- Option A: Backend subdomain (api.zebutrader.com)
  - Add NPMplus proxy host for api.zebutrader.com → VM:8000
  - Update backend CORS to allow zebutrader.com
  - Update frontend VITE_API_BASE_URL
- Option B: Path-based routing
  - NPMplus routes /api/* → VM:8000
  - Simpler but less flexible

**Backend Code Changes**:
- Update CORS allowed origins in `backend/src/zebu/main.py`
- Add domain to allowed origins list
- Environment variable for ALLOWED_ORIGINS

#### Part 4: Frontend Environment Update
- Update `.env` on VM with production domain:
  ```bash
  VITE_API_BASE_URL=https://api.zebutrader.com/api/v1
  # or
  VITE_API_BASE_URL=https://zebutrader.com/api
  ```
- Rebuild frontend Docker image: `docker compose -f docker-compose.prod.yml build frontend`
- Restart: `docker compose -f docker-compose.prod.yml up -d`

#### Part 5: Verification & Testing
- [ ] https://zebutrader.com loads (SSL cert valid)
- [ ] Frontend can connect to backend API
- [ ] Authentication works (Clerk redirects)
- [ ] No CORS errors in browser console
- [ ] API docs accessible (if exposed)

#### Part 6: Troubleshooting
Common issues:
- DNS propagation delays (24-48h, use DNS checker)
- NPMplus certificate renewal issues
- CORS errors (check backend logs, allowed origins)
- Websocket connection issues
- Cloudflare proxy interfering (try DNS only mode)

### 3. Production Readiness Checklist

**New File**: `docs/deployment/production-checklist.md`

Comprehensive checklist for production deployment:

#### Security
- [ ] Secure passwords for all services (Postgres, Redis if applicable)
- [ ] SECRET_KEY generated with strong randomness
- [ ] HTTPS/SSL enabled
- [ ] Firewall configured (only expose 80/443)
- [ ] SSH key-based authentication (no password auth)
- [ ] Regular security updates scheduled
- [ ] Sensitive env files gitignored
- [ ] API rate limiting configured (if applicable)

#### Database
- [ ] Database backups configured (automated)
- [ ] Backup restoration tested
- [ ] Connection pooling configured
- [ ] Database credentials secured
- [ ] Migrations tested and run

#### Application
- [ ] Health checks working for all services
- [ ] Error monitoring/logging configured
- [ ] Resource limits set (memory, CPU)
- [ ] Restart policies configured
- [ ] Graceful shutdown handling
- [ ] Static assets served efficiently

#### Monitoring
- [ ] Service health monitoring
- [ ] Disk space monitoring
- [ ] Log rotation configured
- [ ] Error alerting (optional for small scale)

#### Performance
- [ ] Static assets cached/CDN
- [ ] Database queries optimized
- [ ] Connection pooling configured
- [ ] Resource usage acceptable under load

#### Deployment Process
- [ ] Rollback procedure documented
- [ ] Zero-downtime deployment strategy (if needed)
- [ ] Deployment verification steps
- [ ] Incident response plan

### 4. Update Related Documentation

**Files to Check/Update**:
- `README.md` - Ensure deployment section references correct docs
- `docs/deployment/deployment_strategy.md` - Update if outdated
- `docs/README.md` - Add links to new docs
- Any other files referencing deployment

## Success Criteria

### Documentation Quality
- [ ] All docs are accurate and up-to-date
- [ ] No references to outdated deployment methods
- [ ] Clear step-by-step instructions
- [ ] Troubleshooting sections included
- [ ] Code examples are correct

### Domain Setup Guide
- [ ] Complete end-to-end walkthrough
- [ ] Covers all required services (Cloudflare, NPMplus, CORS)
- [ ] Includes verification steps
- [ ] Troubleshooting section comprehensive
- [ ] Matches actual infrastructure (NPMplus on 192.168.4.200)

### Checklist Completeness
- [ ] Covers security, database, app, monitoring
- [ ] Actionable items (can check off)
- [ ] References to implementation details
- [ ] Appropriate for small-scale production

## Implementation Notes

**Branching Strategy**:
```bash
# Start from PR #118's branch
git checkout copilot/production-ready-proxmox-deployment
git pull origin copilot/production-ready-proxmox-deployment

# Create your improvement branch
git checkout -b docs/deployment-domain-setup

# Make changes, commit, push
# Create PR targeting copilot/production-ready-proxmox-deployment
```

**Research Needed**:
- Review actual deploy.sh implementation for accuracy
- Check NPMplus typical configuration patterns
- Verify Cloudflare + Let's Encrypt integration
- Check backend CORS implementation

**Coordination with Task 088**:
- Environment file names may change
- Update references after Task 088 is merged
- Or use expected new names if working in parallel

## References

- PR #118: https://github.com/TimChild/Zebu/pull/118
- Current deployment docs: `docs/deployment/proxmox-vm-deployment.md`
- Deployment scripts: `scripts/proxmox-vm/deploy.sh`
- NPMplus docs: https://nginxproxymanager.com/
- Cloudflare DNS: https://developers.cloudflare.com/dns/

## Deliverables

1. Updated `docs/deployment/proxmox-vm-deployment.md`
2. New `docs/deployment/domain-and-ssl-setup.md`
3. New `docs/deployment/production-checklist.md`
4. Updated related docs (README, etc.)
5. PR created against PR #118's branch

## Notes

The domain setup guide should be comprehensive enough that someone with basic knowledge can follow it to set up a production domain. Include screenshots or detailed descriptions of UI elements where helpful.
