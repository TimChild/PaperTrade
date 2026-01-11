# PaperTrade Proxmox Deployment Scripts

Automated deployment scripts for deploying PaperTrade to Proxmox LXC containers.

## Overview

These scripts automate the complete deployment workflow:
1. Create a privileged LXC container with Docker support
2. Deploy the full PaperTrade stack (PostgreSQL, Redis, Backend, Frontend)
3. Manage the container lifecycle (start, stop, restart, logs)

## Quick Start

### Prerequisites

- Proxmox VE server accessible via SSH
- SSH key-based authentication configured for Proxmox root user
- Sufficient resources (4GB RAM, 2 CPU cores, 20GB disk recommended)

### Basic Deployment

```bash
# 1. Create container (one-time setup)
task proxmox:create-container

# 2. Deploy application
task proxmox:deploy

# 3. Check status
task proxmox:status

# 4. View logs
task proxmox:logs
```

## Configuration

All configuration is done via environment variables:

### Container Configuration

```bash
# Proxmox connection
PROXMOX_HOST="root@proxmox"           # SSH connection string
PROXMOX_CONTAINER_ID="107"             # Container ID (must be unique)

# Container resources
PROXMOX_CONTAINER_HOSTNAME="papertrade"  # Container hostname
PROXMOX_CONTAINER_MEMORY="4096"          # RAM in MB
PROXMOX_CONTAINER_CORES="2"              # CPU cores
PROXMOX_CONTAINER_DISK="20"              # Disk size in GB

# Network (optional - defaults to DHCP)
PROXMOX_CONTAINER_IP="dhcp"              # Or "192.168.1.100/24" for static IP
PROXMOX_CONTAINER_GATEWAY=""             # Required if static IP (e.g., "192.168.1.1")
```

### Examples

**Create container with custom resources:**
```bash
PROXMOX_CONTAINER_MEMORY=8192 PROXMOX_CONTAINER_CORES=4 task proxmox:create-container
```

**Create container with static IP:**
```bash
PROXMOX_CONTAINER_IP="192.168.1.100/24" \
PROXMOX_CONTAINER_GATEWAY="192.168.1.1" \
task proxmox:create-container
```

**Deploy to specific container:**
```bash
PROXMOX_CONTAINER_ID=108 task proxmox:deploy
```

## Available Commands

### Container Creation

```bash
task proxmox:create-container
```
Creates a new privileged LXC container with Docker support. One-time setup per deployment.

### Deployment

```bash
task proxmox:deploy
```
Deploys or updates the PaperTrade application:
- Creates tarball of application code
- Transfers to container
- Sets up environment variables (preserves secrets on redeployment)
- Builds and starts Docker containers
- Runs database migrations
- Verifies deployment health

**Note**: On first deployment, generates random passwords for PostgreSQL and SECRET_KEY. On subsequent deployments, **preserves existing secrets** to maintain database state.

### Status & Monitoring

```bash
# Check deployment status
task proxmox:status

# View all logs (live)
task proxmox:logs

# View specific service logs
task proxmox:logs SERVICE=backend
task proxmox:logs SERVICE=frontend
task proxmox:logs SERVICE=db
task proxmox:logs SERVICE=redis
```

### Container Lifecycle

```bash
# Stop containers (preserves data)
task proxmox:stop

# Start containers (if already deployed)
task proxmox:start

# Restart containers
task proxmox:restart

# Update to latest code
task proxmox:update
```

### Maintenance

```bash
# Create Proxmox backup
task proxmox:backup

# DESTRUCTIVE: Delete container (all data lost)
task proxmox:destroy
```

## Architecture

### Container Type: Privileged LXC

**Current Configuration:**
- Privileged container (`--unprivileged 0`)
- Docker nesting enabled (`--features nesting=1,keyctl=1`)
- No AppArmor restrictions

**Security Implications:**
- ⚠️ **Not recommended for production** without additional hardening
- Suitable for development, testing, and homelab environments
- See `docs/deployment/proxmox-deployment-evaluation.md` for detailed security analysis

### Deployment Flow

```
Local Machine
    ↓ [Create tarball]
    ↓ [SCP to Proxmox host]
Proxmox Host
    ↓ [Push to container]
LXC Container
    ↓ [Extract & build]
Docker Compose
    ├── PostgreSQL (database)
    ├── Redis (cache)
    ├── Backend (FastAPI)
    └── Frontend (Nginx + React)
```

### Secrets Management

**First Deployment:**
1. Generates random PostgreSQL password
2. Generates random SECRET_KEY
3. Reads ALPHA_VANTAGE_API_KEY from local `.env`
4. Creates `/opt/papertrade/.env` in container

**Subsequent Deployments:**
1. Preserves existing `.env` (including secrets)
2. Updates only non-secret configuration (API key, environment, log level)
3. **Database state is maintained**

### Health Checks

The deployment script verifies all services become healthy:
- Timeout: 2 minutes
- Expected healthy services: 4 (db, redis, backend, frontend)
- Progress indicated by dots (`.`)

## Troubleshooting

### SSH Connection Fails

```
[ERROR] Cannot connect to Proxmox host: root@proxmox
```

**Solutions:**
1. Verify host is reachable: `ping proxmox`
2. Test SSH manually: `ssh root@proxmox`
3. Check SSH key is configured for passwordless login
4. Verify username (usually `root` for Proxmox)

### Container Already Exists

```
[ERROR] Container 107 already exists!
```

**Solutions:**
- Use existing container: `PROXMOX_CONTAINER_ID=107 task proxmox:deploy`
- Create new container: `PROXMOX_CONTAINER_ID=108 task proxmox:create-container`
- Destroy old container: `task proxmox:destroy` (⚠️ data loss!)

### Services Not Healthy

```
[WARN] Not all services became healthy within timeout
```

**Solutions:**
1. Check logs: `task proxmox:logs`
2. Check individual service: `task proxmox:logs SERVICE=backend`
3. Verify container resources are sufficient
4. Check Proxmox host has available resources

### Deployment Breaks Database

**This should NOT happen with current implementation** - secrets are preserved.

If it does happen:
1. Check `.env` still exists: `ssh root@proxmox "pct exec 107 -- cat /opt/papertrade/.env"`
2. Restore from backup: Use Proxmox restore feature
3. File an issue - this is a bug

## Security Considerations

### Current Security Level: ⚠️ Development/Homelab

**Suitable for:**
- Personal homelab (isolated network)
- Development and testing
- Proof-of-concept deployments

**NOT suitable for:**
- Production with real user data
- Internet-exposed applications
- Compliance-required environments

### Hardening Recommendations

For production use, see `docs/deployment/proxmox-deployment-evaluation.md` for:
1. Migration to unprivileged containers
2. Migration to VM-based deployment
3. Proper secrets management
4. Network isolation
5. Security scanning

## Files

- `create-container.sh` - Creates LXC container with Docker
- `deploy.sh` - Main deployment script
- `status.sh` - Shows deployment status
- `logs.sh` - Views container logs
- `README.md` - This file

## Related Documentation

- [Proxmox Deployment Evaluation](../../docs/deployment/proxmox-deployment-evaluation.md) - Security analysis and recommendations
- [Proxmox Deployment Guide](../../docs/deployment/proxmox-deployment.md) - Detailed deployment documentation
- [Taskfile Deployment](../../docs/deployment/TASKFILE_DEPLOYMENT.md) - Taskfile usage guide

## Support

For issues or questions:
1. Check this README
2. Review evaluation document for security/architecture questions
3. Check deployment guide for detailed procedures
4. File an issue on GitHub

---

**Last Updated**: January 11, 2026  
**Version**: 1.1 (with quick win improvements)
