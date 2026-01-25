# Deployment Guide

This directory contains comprehensive documentation for deploying and operating Zebu in different environments.

## 🎯 Quick Navigation

### Running Locally
For local development, see the main [README.md](../../README.md) setup instructions:
- Uses `task setup` for one-command local environment setup
- Docker Compose manages all services (PostgreSQL, Redis, Backend, Frontend)
- Changes reload automatically with hot-reload enabled
- SQLite option available for simpler local development

### Production Deployment
For production deployment to Proxmox:
1. **[Proxmox Deployment Guide](./proxmox.md)** - Complete production deployment walkthrough
2. **[Domain & SSL Setup](./domain-setup.md)** - Configure custom domain with HTTPS
3. **[Production Checklist](./production-checklist.md)** - Pre-deployment verification

---

## 📖 Documentation Overview

### Core Guides

| Document | Purpose | When to Use |
|----------|---------|-------------|
| **[proxmox.md](./proxmox.md)** | Complete Proxmox VM deployment guide | Deploying to production on Proxmox |
| **[domain-setup.md](./domain-setup.md)** | Domain registration and SSL/HTTPS configuration | After Proxmox deployment, when configuring custom domain |
| **[production-checklist.md](./production-checklist.md)** | Comprehensive production readiness verification | Before going live with real users |

### Archive

Historical documentation and learnings preserved for reference:
- **[archive/](./archive/)** - Older docs with valuable context but superseded by current guides

---

## 🚀 Deployment Quick Start

### Local Development

```bash
# Clone repository
git clone https://github.com/TimChild/PaperTrade.git
cd PaperTrade

# One-command setup
task setup

# Start development
task dev
```

See main [README.md](../../README.md) for detailed local setup instructions.

### Production on Proxmox

```bash
# 1. Configure Proxmox connection
export PROXMOX_HOST=root@proxmox

# 2. Create VM (interactive, ~10 minutes)
task proxmox-vm:create

# 3. Deploy application (~5-10 minutes)
task proxmox-vm:deploy

# 4. Verify deployment
task proxmox-vm:status
```

See **[proxmox.md](./proxmox.md)** for complete production deployment guide.

---

## 🔐 Security Considerations

### Local Development
- Default credentials are acceptable for local-only development
- `.env` files should be in `.gitignore` (already configured)
- Never commit secrets to version control

### Production
- **Required**: Change all default passwords
- **Required**: Use strong, randomly generated secrets
- **Required**: Enable HTTPS/SSL
- **Recommended**: Use SSH key authentication
- **Recommended**: Configure firewall rules
- **Recommended**: Set up regular backups

See [Production Checklist](./production-checklist.md) for comprehensive security verification.

---

## 📁 Directory Structure

```
docs/deployment/
├── README.md                    # This file - deployment overview
├── proxmox.md                   # Production deployment to Proxmox
├── domain-setup.md              # Domain registration and SSL setup
├── production-checklist.md      # Pre-deployment verification
└── archive/                     # Historical documentation
    ├── community-scripts-reference.md
    ├── proxmox-environment-reference.md
    ├── proxmox-learnings.md
    └── proxmox-vm-approach-comparison.md
```

---

## 🛠️ Operations

### Common Tasks

| Task | Command | Description |
|------|---------|-------------|
| **Deploy/Update** | `task proxmox-vm:deploy` | Deploy latest code or specific version |
| **Deploy Version** | `VERSION=v1.0.0 task proxmox-vm:deploy` | Deploy specific git tag/branch |
| **Check Status** | `task proxmox-vm:status` | View service health and status |
| **View Logs** | `task proxmox-vm:logs` | Follow application logs |
| **Restart Services** | `task proxmox-vm:restart` | Restart all services |
| **Stop Services** | `task proxmox-vm:stop` | Stop all services |
| **Start Services** | `task proxmox-vm:start` | Start all services |

See [proxmox.md](./proxmox.md#operations) for detailed operations guide.

---

## 📚 Additional Resources

- **[scripts/proxmox-vm/README.md](../../scripts/proxmox-vm/README.md)** - Deployment scripts documentation
- **[Main README](../../README.md)** - Project overview and local setup
- **[Architecture Docs](../architecture/)** - System architecture and design
- **[User Guide](../USER_GUIDE.md)** - End-user documentation

---

## 🆘 Getting Help

**Deployment Issues:**
1. Check the **Troubleshooting** section in [proxmox.md](./proxmox.md#troubleshooting)
2. Review service logs: `task proxmox-vm:logs`
3. Check service status: `task proxmox-vm:status`
4. Review [Production Checklist](./production-checklist.md) for common gotchas

**Questions or Bugs:**
- Open an issue on [GitHub](https://github.com/TimChild/PaperTrade/issues)
- Include logs and configuration (redact secrets!)
- Specify environment (local dev vs Proxmox production)

---

**Happy Deploying! 🎉**
