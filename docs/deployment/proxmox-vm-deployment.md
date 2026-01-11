# Proxmox VM Deployment Guide

**Last Updated**: January 11, 2026  
**Agent**: quality-infra  
**Deployment Method**: VM-based Docker using community scripts

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

Get PaperTrade running on Proxmox in 5 minutes:

```bash
# 1. Configure Proxmox connection
export PROXMOX_HOST=root@proxmox

# 2. Create and configure secrets
cp .env.production.example .env
# Edit .env with your secrets (POSTGRES_PASSWORD, SECRET_KEY, etc.)

# 3. Create VM
task proxmox-vm:create

# 4. Deploy application
task proxmox-vm:deploy

# 5. Check status
task proxmox-vm:status
```

Your application will be accessible at the VM's IP address.

---

## Prerequisites

### On Your Local Machine

- **Task** (go-task) - Task runner for executing deployment commands
- **SSH access** to Proxmox host (key-based authentication recommended)
- **curl** - For downloading community scripts
- **tar** - For packaging application code

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
export PROXMOX_VM_HOSTNAME=papertrade
# ... etc
```

#### Method 2: .env File (Recommended)

```bash
# Create configuration file
cp .env.example.proxmox .env.proxmox

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

See `.env.example.proxmox` for complete reference. Key parameters:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `PROXMOX_HOST` | `root@proxmox` | SSH connection to Proxmox |
| `PROXMOX_VM_ID` | `200` | Unique VM identifier |
| `PROXMOX_VM_HOSTNAME` | `papertrade` | VM hostname |
| `PROXMOX_VM_CORES` | `4` | CPU cores |
| `PROXMOX_VM_MEMORY` | `8192` | RAM in MB |
| `PROXMOX_VM_DISK_SIZE` | `50` | Disk size in GB |
| `PROXMOX_VM_BRIDGE` | `vmbr0` | Network bridge |
| `PROXMOX_VM_IP_MODE` | `dhcp` | IP mode: `dhcp` or `static` |
| `APP_DIR` | `/opt/papertrade` | App directory in VM |

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

### Step 2: Create VM

```bash
task proxmox-vm:create
```

This will:
- Download the community Docker VM script
- Create a Debian 12 VM with Docker pre-installed
- Configure VM with specified resources
- Start the VM
- Attempt to change the default password (requires `sshpass`)
- Display VM IP address

**Duration**: 5-10 minutes (downloads Debian image)

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

### Redeployment

To deploy code changes:

```bash
task proxmox-vm:deploy
```

This will:
- Transfer updated code
- Rebuild Docker images
- Restart services
- **Preserve** existing secrets

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
cd /opt/papertrade
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs
```

**Problem**: Missing or invalid secrets

```bash
# Verify .env file locally
cat .env | grep -E "POSTGRES_PASSWORD|SECRET_KEY|ALPHA_VANTAGE_API_KEY"

# Check .env on VM
ssh root@<vm-ip> cat /opt/papertrade/.env
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
cd /opt/papertrade
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
  caddy reverse-proxy --from papertrade.example.com --to localhost:80

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

Scripts support non-interactive execution:

```bash
# Deploy without prompts (useful for CI/CD)
task proxmox-vm:deploy

# Destroy VM with force flag (skip confirmation)
bash scripts/proxmox-vm/destroy.sh force
```

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
- PaperTrade-specific configuration
- Automated deployment workflow
- Secrets management
- Health checking
- Operational commands

### File Structure

```
PaperTrade/
├── scripts/proxmox-vm/
│   ├── common.sh          # Shared utilities
│   ├── create-vm.sh       # VM creation
│   ├── deploy.sh          # Application deployment
│   ├── lifecycle.sh       # Service management
│   └── destroy.sh         # VM destruction
├── .env.example.proxmox   # Configuration template
├── .env                   # Your secrets (not in git)
└── docker-compose.prod.yml # Production stack definition
```

---

## Additional Resources

- **Community Scripts**: https://community-scripts.github.io/ProxmoxVE/
- **Proxmox Documentation**: https://pve.proxmox.com/pve-docs/
- **Docker Documentation**: https://docs.docker.com/
- **PaperTrade Repository**: https://github.com/TimChild/PaperTrade

---

## Support

For issues or questions:
1. Check [Troubleshooting](#troubleshooting) section above
2. Review deployment logs: `task proxmox-vm:logs`
3. Check service status: `task proxmox-vm:status`
4. Open an issue on GitHub with logs and configuration (redact secrets!)

---

**Happy Deploying! 🚀**
