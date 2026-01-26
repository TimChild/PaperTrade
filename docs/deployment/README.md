# Deployment Documentation

**Last Updated**: January 26, 2026

This directory contains comprehensive guides for deploying Zebu to production environments.

---

## Quick Navigation

| Guide | Purpose | When to Use |
|-------|---------|-------------|
| **[Proxmox VM Deployment](./proxmox-vm-deployment.md)** | Complete deployment guide for Proxmox | **Start here** for production deployment |
| **[Domain & SSL Setup](./domain-setup.md)** | Configure custom domain with HTTPS | After initial deployment |
| **[Production Checklist](./production-checklist.md)** | Verification and best practices | Before going live |

---

## Deployment Overview

### Recommended Deployment Path

**For Production (Proxmox VM)**:
1. Follow **[Proxmox VM Deployment](./proxmox-vm-deployment.md)** guide
2. Configure **[Domain & SSL](./domain-setup.md)** for custom domain
3. Verify with **[Production Checklist](./production-checklist.md)**

**For Local Development**:
- Use Docker Compose: `task docker:up` (see root README.md)
- No deployment needed - runs entirely on localhost

---

## What Each Guide Covers

### 📘 [Proxmox VM Deployment](./proxmox-vm-deployment.md)

**Complete production deployment guide** covering:
- VM creation using community Docker script
- Application deployment automation
- Service management (start/stop/restart/logs)
- Troubleshooting and security
- CI/CD integration examples

**Prerequisites**:
- Proxmox VE 8.x+ server
- SSH access to Proxmox host
- Basic familiarity with Docker

**Time**: 15-20 minutes for initial deployment

---

### 🌐 [Domain & SSL Setup](./domain-setup.md)

**Configure custom domain with automatic HTTPS** covering:
- DNS configuration (Cloudflare example)
- Reverse proxy setup (NPMplus)
- SSL certificate automation (Let's Encrypt)
- CORS configuration for production
- Troubleshooting common issues

**Prerequisites**:
- Deployed Zebu application (see Proxmox guide above)
- Registered domain name
- Access to DNS provider
- Reverse proxy (NPMplus or similar)

**Time**: 30-60 minutes (DNS propagation can take time)

---

### ✅ [Production Checklist](./production-checklist.md)

**Comprehensive verification and best practices** covering:
- Pre-deployment setup (infrastructure, security, database)
- Deployment verification (services, network, performance)
- Post-deployment operations (monitoring, backups, maintenance)
- Ongoing operations schedule (weekly, monthly, quarterly)
- Incident response procedures

**Use Cases**:
- Final verification before public launch
- Periodic security audits
- Onboarding new team members
- Disaster recovery planning

---

## Deployment Architecture

### Production Environment

```
┌─────────────────────────────────────────────────────────┐
│                  Internet / Users                       │
└────────────────────────┬────────────────────────────────┘
                         │
                  ┌──────▼──────┐
                  │   Router    │
                  │  (Firewall) │
                  └──────┬──────┘
                         │ Port Forward 80/443
                  ┌──────▼──────────┐
                  │   NPMplus       │
                  │ Reverse Proxy   │
                  │  (SSL/HTTPS)    │
                  └──────┬──────────┘
                         │
┌────────────────────────┼────────────────────────────────┐
│         Proxmox Host   │                                │
│                 ┌──────▼───────────────────────┐        │
│                 │   Docker VM (Debian 12)      │        │
│                 │                              │        │
│                 │  ┌────────────────────────┐  │        │
│                 │  │  Docker Compose Stack  │  │        │
│                 │  │                        │  │        │
│                 │  │  ┌──────┐  ┌───────┐  │  │        │
│                 │  │  │ PSQL │  │ Redis │  │  │        │
│                 │  │  └──────┘  └───────┘  │  │        │
│                 │  │                        │  │        │
│                 │  │  ┌──────┐  ┌───────┐  │  │        │
│                 │  │  │Backend  │Frontend│  │  │        │
│                 │  │  └──────┘  └───────┘  │  │        │
│                 │  └────────────────────────┘  │        │
│                 └──────────────────────────────┘        │
└─────────────────────────────────────────────────────────┘
```

**Key Points**:
- **VM-based**: Full hardware virtualization for security and isolation
- **Docker Compose**: All services in containers
- **Reverse Proxy**: Handles SSL/TLS termination and routing
- **Port Forwarding**: Only ports 80/443 exposed to internet

---

## Local Development vs Production

| Aspect | Local Development | Production (Proxmox) |
|--------|-------------------|----------------------|
| **Platform** | Docker Compose on host | Docker Compose in Proxmox VM |
| **Database** | PostgreSQL or SQLite | PostgreSQL only |
| **HTTPS** | No (HTTP only) | Yes (Let's Encrypt SSL) |
| **Domain** | localhost | Custom domain |
| **Authentication** | Clerk test keys | Clerk production keys |
| **API Rate Limits** | Relaxed | Production limits |
| **Secrets** | `.env` file | `.env` in VM (secured) |
| **Backup** | Manual | Automated (recommended) |
| **Monitoring** | Optional | Recommended |

---

## Task Commands

All deployment operations use the Task runner:

```bash
# Proxmox VM Operations
task proxmox-vm:create     # Create VM (interactive)
task proxmox-vm:deploy     # Deploy application
task proxmox-vm:status     # Check service status
task proxmox-vm:logs       # View service logs
task proxmox-vm:start      # Start all services
task proxmox-vm:stop       # Stop all services
task proxmox-vm:restart    # Restart all services
task proxmox-vm:destroy    # Destroy VM (destructive!)

# Local Development
task docker:up             # Start local stack
task docker:down           # Stop local stack
task docker:logs           # View local logs
task docker:clean          # Clean all containers/volumes
```

See `task --list` for all available commands.

---

## Deployment Scripts

Location: `scripts/proxmox-vm/`

| Script | Purpose |
|--------|---------|
| `common.sh` | Shared utilities and configuration |
| `create-vm.sh` | VM creation helper |
| `deploy.sh` | Application deployment automation |
| `lifecycle.sh` | Service management operations |
| `destroy.sh` | VM destruction |

These scripts are called via Task commands - you typically don't run them directly.

---

## Environment Configuration

### Proxmox VM Configuration

File: `.env.proxmox` (create from `.env.proxmox.example`)

```bash
# Proxmox Connection
PROXMOX_HOST=root@proxmox

# VM Configuration
PROXMOX_VM_ID=200
PROXMOX_VM_HOSTNAME=zebu
PROXMOX_VM_CORES=4
PROXMOX_VM_MEMORY=8192
PROXMOX_VM_DISK_SIZE=50
```

### Application Secrets

File: `.env` (create from `.env.production.example`)

```bash
# Database
POSTGRES_PASSWORD=<secure-password>

# Application
SECRET_KEY=<django-secret-key>
APP_ENV=production

# External APIs
ALPHA_VANTAGE_API_KEY=<api-key>

# CORS
CORS_ORIGINS=https://yourdomain.com,https://api.yourdomain.com
```

**Security**: Never commit `.env` files to version control!

---

## Troubleshooting

### Quick Diagnostics

```bash
# Check all services
task proxmox-vm:status

# View recent logs
task proxmox-vm:logs

# SSH into VM for manual inspection
ssh root@<vm-ip>
cd /opt/zebu
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs
```

### Common Issues

| Problem | Solution |
|---------|----------|
| Cannot connect to Proxmox | Check SSH keys: `ssh root@proxmox` |
| VM not accessible | Check VM is running: `ssh root@proxmox qm status 200` |
| Services unhealthy | Check logs: `task proxmox-vm:logs` |
| CORS errors | Verify `CORS_ORIGINS` in `.env` |
| SSL certificate issues | Check NPMplus configuration and DNS |

For detailed troubleshooting, see individual guide troubleshooting sections.

---

## Security Best Practices

- [ ] Use **SSH key authentication** (disable password auth)
- [ ] Generate **strong secrets** (32+ characters)
- [ ] Configure **firewall rules** (only expose 80/443)
- [ ] Enable **HTTPS/SSL** with Let's Encrypt
- [ ] Restrict **CORS origins** to production domains only
- [ ] Regular **security updates** for OS and dependencies
- [ ] Implement **backup strategy** (VM snapshots + database backups)
- [ ] Monitor **logs and metrics** for suspicious activity
- [ ] Use **static IP** for VM (or DHCP reservation)
- [ ] Change **all default passwords** immediately

See [Production Checklist](./production-checklist.md) for complete security checklist.

---

## CI/CD Integration

The deployment scripts support GitHub Actions automation:

```yaml
- name: Deploy to Proxmox
  env:
    PROXMOX_HOST: ${{ secrets.PROXMOX_HOST }}
    VERSION: ${{ github.ref_name }}
  run: task proxmox-vm:deploy
```

See [Proxmox VM Deployment Guide](./proxmox-vm-deployment.md#cicd-integration) for complete examples.

---

## Additional Resources

- **[Proxmox Documentation](https://pve.proxmox.com/pve-docs/)** - Official Proxmox VE docs
- **[Docker Documentation](https://docs.docker.com/)** - Docker and Docker Compose
- **[Community Scripts](https://community-scripts.github.io/ProxmoxVE/)** - Proxmox helper scripts
- **[Let's Encrypt](https://letsencrypt.org/)** - Free SSL certificates
- **[Cloudflare Docs](https://developers.cloudflare.com/)** - DNS and CDN

---

## Archive

Historical documentation and design decisions are archived in `archive/`:

- **[Proxmox Learnings](./archive/proxmox-learnings.md)** - Lessons from prototype deployment
- **[VM vs LXC Comparison](./archive/proxmox-vm-approach-comparison.md)** - Architecture decision rationale
- **[Environment Reference](./archive/proxmox-environment-reference.md)** - Historical environment details
- **[Community Scripts Reference](./archive/community-scripts-reference.md)** - Background on community scripts

These are preserved for historical context but are not needed for deployment.

---

## Getting Help

1. **Read the guides** - Start with [Proxmox VM Deployment](./proxmox-vm-deployment.md)
2. **Check troubleshooting** - Each guide has a troubleshooting section
3. **Review logs** - Run `task proxmox-vm:logs` for diagnostics
4. **Search issues** - Check GitHub issues for similar problems
5. **Open an issue** - Include logs and configuration (redact secrets!)

---

**Ready to Deploy?** Start with **[Proxmox VM Deployment Guide](./proxmox-vm-deployment.md)** 🚀
