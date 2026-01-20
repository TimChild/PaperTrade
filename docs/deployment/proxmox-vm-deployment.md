# Proxmox VM Deployment Guide

**Last Updated**: January 11, 2026
**Agent**: quality-infra
**Deployment Method**: VM-based Docker using community script

---

## Overview

This guide covers deploying Zebu to a Proxmox VM using the [community Docker VM script](https://github.com/community-scripts/ProxmoxVE). The community script uses `virt-customize` to pre-install Docker into the VM image before first boot, providing a production-ready Docker environment immediately.

**Why use the community script?**
See [proxmox-vm-approach-comparison.md](./proxmox-vm-approach-comparison.md) for a detailed analysis. Key benefits:
- Docker installed before first boot (no cloud-init wait)
- Avoids dpkg lock issues during initial setup
- Battle-tested by thousands of Proxmox users
- Handles storage selection, EFI, cleanup automatically

The script runs interactively with a terminal UI, which is acceptable since VM creation is infrequent (<10 times/year typical). All other operations (deploy, status, logs) are fully automated.

---

## Table of Contents

- [Quick Start](#quick-start)
- [Prerequisites](#prerequisites)
- [Configuration](#configuration)
- [Deployment Steps](#deployment-steps)
- [Operations](#operations)
- [Troubleshooting](#troubleshooting)
- [Security Considerations](#security-considerations)
- [CI/CD Integration](#cicd-integration)
- [Architecture](#architecture)

---

## Quick Start

Get Zebu running on Proxmox in 10-15 minutes:

```bash
# 1. Configure Proxmox connection
export PROXMOX_HOST=root@proxmox

# 2. Configure VM settings (optional - defaults are sensible)
export PROXMOX_VM_ID=200
export PROXMOX_VM_HOSTNAME=zebu-vm

# 3. Create VM using community script (interactive)
task proxmox-vm:create
# Follow the interactive prompts using the recommended settings displayed

# 4. Deploy application
task proxmox-vm:deploy

# 5. Check status
task proxmox-vm:status
```

Your application will be accessible at the VM's IP address (displayed after creation).

**Note**: Step 3 is interactive and requires answering prompts in a terminal UI. The script will display recommended values from your configuration. This typically happens <10 times/year, so the interactivity is acceptable.

---

## Prerequisites

### On Your Local Machine

- **Task** (go-task) - Task runner for executing deployment commands
- **SSH access** to Proxmox host (key-based authentication recommended)
- **curl** - For downloading community scripts
- **git** - For version control and tracking deployments

Optional but recommended:
- **sshpass** - For automated password changes (improves security)

### On Proxmox Host

- **Proxmox VE 8.x or 9.0-9.1** - Community script compatibility
- **SSH access** enabled for root user
- **Sufficient resources** for VM:
  - Minimum: 2 CPU cores, 4GB RAM, 20GB disk
  - Recommended: 4 CPU cores, 8GB RAM, 50GB disk
- **Network access** for VM (bridged networking)
- **Storage pool** with available space

### On the VM (Installed Automatically)

The community script and deployment process automatically handle:
- **Docker Engine and Docker Compose** - Pre-installed by community script
- **Git** - Installed during first deployment for code management
- **QEMU Guest Agent** - Pre-installed for VM management

### SSH Setup

Key-based authentication is strongly recommended:

```bash
# Generate SSH key if you don't have one
ssh-keygen -t rsa -b 4096

# Copy key to Proxmox host
ssh-copy-id root@proxmox

# Test connection
ssh root@proxmox
```

---

## Configuration

### Environment Variables

All configuration is managed through environment variables with sensible defaults.

#### Method 1: Export Variables (Quick Testing)

```bash
export PROXMOX_HOST=root@proxmox
export PROXMOX_VM_ID=200
export PROXMOX_VM_HOSTNAME=zebu
# ... etc
```

#### Method 2: .env File (Recommended)

```bash
# Create configuration file
cp .env.proxmox.example .env.proxmox

# Edit configuration
nano .env.proxmox

# Source before running tasks
source .env.proxmox
```

#### Method 3: Inline with Task Commands

```bash
PROXMOX_HOST=root@proxmox PROXMOX_VM_ID=201 task proxmox-vm:create
```

### Configuration Parameters

See `.env.proxmox.example` for complete reference. Key parameters:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `PROXMOX_HOST` | `root@proxmox` | SSH connection to Proxmox |
| `PROXMOX_VM_ID` | `200` | Unique VM identifier |
| `PROXMOX_VM_HOSTNAME` | `zebu` | VM hostname |
| `PROXMOX_VM_CORES` | `4` | CPU cores |
| `PROXMOX_VM_MEMORY` | `8192` | RAM in MB |
| `PROXMOX_VM_DISK_SIZE` | `50` | Disk size in GB |
| `PROXMOX_VM_BRIDGE` | `vmbr0` | Network bridge |
| `PROXMOX_VM_IP_MODE` | `dhcp` | IP mode: `dhcp` or `static` |
| `APP_DIR` | `/opt/zebu` | App directory in VM |

### Application Secrets

Application requires secrets in `.env` file (see `.env.production.example`):

```bash
# Required secrets
POSTGRES_PASSWORD=<secure-password>
SECRET_KEY=<django-secret-key>
ALPHA_VANTAGE_API_KEY=<your-api-key>

# Generate secure values:
POSTGRES_PASSWORD=$(openssl rand -base64 32)
SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
```

**Important**: Secrets are preserved across redeployments. On first deployment, they are transferred to the VM and reused on subsequent deployments.

---

## Deployment Steps

### Step 1: Initial Configuration

```bash
# 1. Configure Proxmox connection
export PROXMOX_HOST=root@your-proxmox-host

# 2. (Optional) Customize VM settings
export PROXMOX_VM_ID=200
export PROXMOX_VM_CORES=4
export PROXMOX_VM_MEMORY=8192

# 3. Create application secrets
cp .env.production.example .env
# Edit .env with your secrets
```

### Step 2: Create VM (Interactive)

```bash
task proxmox-vm:create
```

The script will:
1. Display recommended configuration values from your environment
2. Guide you to SSH into Proxmox
3. Run the community Docker VM script interactively
4. Verify the VM was created successfully

**Interactive Prompts** (recommended values will be displayed):
- **Use Default Settings?** → NO (select Advanced for custom configuration)
- **VM ID** → 200 (or your configured value)
- **Machine Type** → i440fx (default)
- **Disk Size** → 50G (or your configured value)
- **Disk Cache** → None (default)
- **Hostname** → zebu-vm
- **CPU Model** → KVM64 (default)
- **CPU Cores** → 4
- **RAM Size** → 8192
- **Bridge** → vmbr0
- **MAC Address** → (auto-generated, accept default)
- **VLAN** → Default (leave blank)
- **Interface MTU Size** → Default (leave blank)
- **Start VM** → YES
- **Storage** → Select your preferred storage pool (e.g., local-lvm)

**Note**: The script may take 5-10 minutes to complete. The virt-resize step (expanding disk) can take a minute or two - **do not interrupt it**.

**What the community script does**:
1. Downloads Debian 12 cloud image (~500MB)
2. Uses `virt-customize` to inject Docker, qemu-guest-agent into the image offline
3. Configures hostname and enables Docker service
4. Resizes disk to requested size
5. Creates VM with cloud-init configuration for SSH and networking
6. Starts VM with Docker pre-installed and ready

**Duration**: 5-10 minutes (includes image download and offline customization)

**Technical Details**: The script uses `libguestfs-tools` to modify the cloud image before first boot. This installs Docker packages and configures services without needing to wait for cloud-init or deal with dpkg locks during first boot.

### Step 3: Deploy Application

```bash
task proxmox-vm:deploy
```

This will:
- Transfer application code to VM
- Build Docker images on VM
- Start all services (PostgreSQL, Redis, Backend, Frontend)
- Verify services are healthy
- Display access URLs

**Duration**: 5-10 minutes (first deployment builds images)

### Step 4: Verify Deployment

```bash
# Check status
task proxmox-vm:status

# View logs
task proxmox-vm:logs
```

Access your application:
- **Frontend**: `http://<vm-ip>`
- **Backend API**: `http://<vm-ip>:8000`
- **API Docs**: `http://<vm-ip>:8000/docs`

---

## Operations

### Lifecycle Management

```bash
# Check deployment status
task proxmox-vm:status

# View logs (follow mode)
task proxmox-vm:logs

# Start services
task proxmox-vm:start

# Stop services
task proxmox-vm:stop

# Restart services
task proxmox-vm:restart
```

### Updating Deployments (Redeployment)

The deployment script supports deploying specific versions using the `VERSION` environment variable. This allows you to deploy:
- **Git tags** (e.g., `v1.0.0`)
- **Branches** (e.g., `main`, `feature/new-feature`)
- **Commit SHAs** (e.g., `abc123def`)

**To deploy the latest code from current branch:**

```bash
task proxmox-vm:deploy
```

**To deploy a specific version:**

```bash
# Deploy a specific git tag
VERSION=v1.0.0 task proxmox-vm:deploy

# Deploy a specific branch
VERSION=main task proxmox-vm:deploy
VERSION=feature/new-feature task proxmox-vm:deploy

# Deploy a specific commit
VERSION=abc123def task proxmox-vm:deploy
```

The deployment script automatically detects whether the VERSION is a tag, branch, or commit and handles it appropriately.

**What happens during deployment:**

When `VERSION` is specified:
1. Fetch all refs (tags and branches) from origin
2. Detect ref type (tag, branch, or commit)
3. Checkout the specified version
4. For branches: also pull latest changes
5. For tags/commits: checkout directly (detached HEAD)
6. Rebuild Docker images (only rebuilds changed layers)
7. Restart services with zero-downtime strategy
8. **Preserve** existing secrets (`.env` file not overwritten)

When `VERSION` is not specified (default behavior):
1. Use the currently checked out branch locally
2. Pull latest changes from that branch via git
3. Rebuild and restart as above

**What happens during redeployment:**
- If repository exists on VM → fetch and checkout specified version
- If repository doesn't exist → clone and checkout specified version (first deployment only)
- Shows deployed git version after update
- Existing `.env` file is preserved (secrets not changed)
- `.env` is backed up to `.env.backup` as a safety measure

**Manual git operations on VM:**

You can also SSH into the VM and perform git operations manually:

```bash
# SSH into VM
ssh root@<vm-ip>

# Navigate to app directory
cd /opt/zebu

# Check current version
git log -1 --oneline

# View uncommitted changes (if any)
git status

# Switch to a different branch
git checkout main
git pull origin main

# Rollback to a specific commit
git checkout <commit-hash>

# Return to latest version
git checkout main
git pull origin main

# Rebuild and restart after manual git operations
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d
```

**Best Practices:**
- **Use VERSION parameter for production**: `VERSION=v1.0.0 task proxmox-vm:deploy`
- Use semantic versioning for tags (e.g., `v1.0.0`, `v1.1.0`)
- Deploy from tagged releases in production (ensures reproducibility)
- Test in staging before deploying to production
- Always deploy from a clean git state (no uncommitted changes locally)
- Keep track of deployed versions with `task proxmox-vm:status`
- Document deployment versions in your changelog

### VM Management

```bash
# Start VM (if stopped)
ssh root@proxmox qm start 200

# Stop VM
ssh root@proxmox qm stop 200

# Restart VM
ssh root@proxmox qm reboot 200

# View VM console
ssh root@proxmox qm monitor 200
```

### Destroy VM

**WARNING**: This is destructive and cannot be undone!

```bash
task proxmox-vm:destroy
```

You will be prompted for confirmation. The VM and all its data will be permanently deleted.

---

## Troubleshooting

### Connection Issues

**Problem**: Cannot connect to Proxmox host

```bash
# Test SSH connection
ssh root@proxmox

# If password authentication fails, use SSH keys
ssh-copy-id root@proxmox
```

**Problem**: VM is not accessible via SSH

```bash
# Check VM status
ssh root@proxmox qm status 200

# View VM console (if VNC configured)
# Access through Proxmox web UI

# Check network configuration
ssh root@proxmox qm guest cmd 200 network-get-interfaces
```

### Deployment Issues

**Problem**: Services not healthy after deployment

```bash
# Check individual service status
task proxmox-vm:status

# View service logs
task proxmox-vm:logs

# SSH into VM and check manually
ssh root@<vm-ip>
cd /opt/zebu
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs
```

**Problem**: Missing or invalid secrets

```bash
# Verify .env file locally
cat .env | grep -E "POSTGRES_PASSWORD|SECRET_KEY|ALPHA_VANTAGE_API_KEY"

# Check .env on VM
ssh root@<vm-ip> cat /opt/zebu/.env
```

**Problem**: Build failures

```bash
# SSH into VM
ssh root@<vm-ip>

# Check disk space
df -h

# Check Docker status
docker ps
docker images

# Rebuild manually
cd /opt/zebu
docker compose -f docker-compose.prod.yml build --no-cache
```

### Network Issues

**Problem**: Cannot determine VM IP

```bash
# Method 1: Query guest agent
ssh root@proxmox qm guest cmd 200 network-get-interfaces

# Method 2: Check DHCP server logs
# (depends on your network setup)

# Method 3: Access VM console and run
ip addr show
```

**Problem**: Static IP not working

```bash
# SSH into VM
ssh root@<vm-ip>

# Check network configuration
cat /etc/network/interfaces
# or
cat /etc/netplan/*.yaml

# Reconfigure network (Debian 12 uses netplan)
# See: https://www.debian.org/doc/manuals/debian-reference/ch05.en.html
```

### Performance Issues

**Problem**: Services slow or unresponsive

```bash
# Check VM resource usage
ssh root@<vm-ip>
top
free -h
df -h

# Check Docker resource usage
docker stats

# Consider increasing VM resources
# Stop VM and reconfigure in Proxmox web UI
```

---

## Security Considerations

### Production Security Checklist

- [ ] **Change default VM password** (done automatically if `sshpass` installed)
- [ ] **Use SSH key authentication** (disable password auth)
- [ ] **Generate strong secrets** (POSTGRES_PASSWORD, SECRET_KEY)
- [ ] **Configure firewall rules** on Proxmox/VM
- [ ] **Use static IP** for predictable access
- [ ] **Regular updates** (Proxmox, VM OS, Docker images)
- [ ] **Backup strategy** (VM snapshots, database backups)
- [ ] **Monitor logs** for suspicious activity
- [ ] **Rotate secrets** periodically
- [ ] **HTTPS/TLS** for production (reverse proxy like Caddy or Nginx)

### SSH Hardening (VM)

```bash
# SSH into VM
ssh root@<vm-ip>

# Disable password authentication
nano /etc/ssh/sshd_config
# Set: PasswordAuthentication no
# Set: PermitRootLogin prohibit-password

# Restart SSH
systemctl restart sshd
```

### Firewall Configuration

```bash
# On VM, allow only necessary ports
apt install ufw
ufw allow 22/tcp   # SSH
ufw allow 80/tcp   # Frontend
ufw allow 8000/tcp # Backend API (or restrict to internal only)
ufw enable
```

### HTTPS Configuration

For production, use a reverse proxy with automatic HTTPS:

```bash
# Option 1: Caddy (simplest)
docker run -d \
  -p 443:443 \
  -v caddy_data:/data \
  caddy:latest \
  caddy reverse-proxy --from zebu.example.com --to localhost:80

# Option 2: Nginx + Certbot (more control)
# See: https://certbot.eff.org/
```

---

## CI/CD Integration

The deployment scripts are designed to work in CI/CD environments like GitHub Actions.

### GitHub Actions Example

```yaml
name: Deploy to Proxmox

on:
  push:
    tags:
      - 'v*'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Install Task
        run: |
          sh -c "$(curl --location https://taskfile.dev/install.sh)" -- -d -b ~/.local/bin

      - name: Setup SSH
        run: |
          mkdir -p ~/.ssh
          echo "${{ secrets.PROXMOX_SSH_KEY }}" > ~/.ssh/id_rsa
          chmod 600 ~/.ssh/id_rsa
          ssh-keyscan -H ${{ secrets.PROXMOX_HOST }} >> ~/.ssh/known_hosts

      - name: Configure environment
        run: |
          echo "POSTGRES_PASSWORD=${{ secrets.POSTGRES_PASSWORD }}" >> .env
          echo "SECRET_KEY=${{ secrets.SECRET_KEY }}" >> .env
          echo "ALPHA_VANTAGE_API_KEY=${{ secrets.ALPHA_VANTAGE_API_KEY }}" >> .env

      - name: Deploy to Proxmox
        env:
          PROXMOX_HOST: ${{ secrets.PROXMOX_HOST }}
          PROXMOX_VM_ID: ${{ secrets.PROXMOX_VM_ID }}
          VERSION: ${{ github.ref_name }}  # Deploys the git tag that triggered the workflow
        run: |
          task proxmox-vm:deploy

      - name: Verify deployment
        run: |
          task proxmox-vm:status
```

### Required GitHub Secrets

For CI/CD deployment, configure these secrets in your repository:

| Secret | Description |
|--------|-------------|
| `PROXMOX_HOST` | SSH connection string (e.g., `root@proxmox`) |
| `PROXMOX_SSH_KEY` | Private SSH key for Proxmox access |
| `PROXMOX_VM_ID` | VM ID to deploy to |
| `POSTGRES_PASSWORD` | Database password |
| `SECRET_KEY` | Application secret key |
| `ALPHA_VANTAGE_API_KEY` | Market data API key |

### Non-Interactive Execution

Scripts support non-interactive execution for CI/CD:

```bash
# Deploy without prompts (default: current branch)
task proxmox-vm:deploy

# Deploy specific version in CI/CD
VERSION=v1.0.0 task proxmox-vm:deploy

# Deploy git tag from GitHub Actions trigger
VERSION=${{ github.ref_name }} task proxmox-vm:deploy

# Destroy VM with force flag (skip confirmation)
bash scripts/proxmox-vm/destroy.sh force
```

**CI/CD Best Practices:**
- Use `VERSION` parameter to deploy specific tags
- Set `VERSION=${{ github.ref_name }}` in GitHub Actions when deploying from tags
- Test deployments in a staging environment first
- Keep deployment logs for troubleshooting

---

## Architecture

### Deployment Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Proxmox Host                        │
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │         Docker VM (Debian 12)                  │    │
│  │                                                 │    │
│  │  ┌──────────────────────────────────────────┐ │    │
│  │  │  Docker Compose Stack                    │ │    │
│  │  │                                          │ │    │
│  │  │  ┌──────────┐  ┌───────┐  ┌─────────┐  │ │    │
│  │  │  │PostgreSQL│  │ Redis │  │ Backend │  │ │    │
│  │  │  └──────────┘  └───────┘  └─────────┘  │ │    │
│  │  │                                          │ │    │
│  │  │  ┌──────────┐                           │ │    │
│  │  │  │ Frontend │                           │ │    │
│  │  │  │ (Nginx)  │                           │ │    │
│  │  │  └──────────┘                           │ │    │
│  │  └──────────────────────────────────────────┘ │    │
│  │                                                 │    │
│  └────────────────────────────────────────────────┘    │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### Why VM over LXC?

**VM Advantages** (see `proxmox-learnings.md` for full analysis):
- Full hardware virtualization = better security isolation
- No AppArmor configuration needed for Docker
- No privileged container requirements
- Production-ready without workarounds
- Simpler configuration and maintenance

### Community Script

We leverage the [community Docker VM script](https://community-scripts.github.io/ProxmoxVE/scripts?id=docker-vm) which:
- Creates Debian 12 VM
- Pre-installs Docker Engine and Docker Compose
- Configures QEMU guest agent
- Handles storage allocation
- Battle-tested by thousands of deployments

Our scripts wrap and enhance the community script with:
- Zebu-specific configuration
- Automated deployment workflow
- Secrets management
- Health checking
- Operational commands

### File Structure

```
Zebu/
├── scripts/proxmox-vm/
│   ├── common.sh          # Shared utilities
│   ├── create-vm.sh       # VM creation
│   ├── deploy.sh          # Application deployment
│   ├── lifecycle.sh       # Service management
│   └── destroy.sh         # VM destruction
├── .env.proxmox.example   # VM configuration template
├── .env.production.example # App secrets template
├── .env                   # Your secrets (not in git)
└── docker-compose.prod.yml # Production stack definition
```

---

## Additional Resources

- **Community Scripts**: https://community-scripts.github.io/ProxmoxVE/
- **Proxmox Documentation**: https://pve.proxmox.com/pve-docs/
- **Docker Documentation**: https://docs.docker.com/
- **Zebu Repository**: https://github.com/TimChild/Zebu

---

## Support

For issues or questions:
1. Check [Troubleshooting](#troubleshooting) section above
2. Review deployment logs: `task proxmox-vm:logs`
3. Check service status: `task proxmox-vm:status`
4. Open an issue on GitHub with logs and configuration (redact secrets!)

---

**Happy Deploying! 🚀**
