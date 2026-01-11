# Proxmox Environment - Reference Configuration

**Date**: January 11, 2026

## Purpose

This document provides reference information about our Proxmox environment to inform deployment script design. All specific values should be treated as **configurable parameters**, not hard-coded constants.

## Proxmox Host Configuration

### Version & Platform

- **Proxmox VE Version**: 8.x
- **Debian Version**: 13 (Trixie)
- **Kernel Version**: 6.14.11-4-pve
- **Architecture**: x86_64 (amd64)

### Key Characteristics

**Important for Docker Deployment**:
- Modern kernel version (6.14+) has implications for LXC AppArmor compatibility
- VM-based Docker deployment avoids these kernel-specific issues
- Hardware virtualization support available

## Network Environment

### Network Configuration Pattern

Our Proxmox environment uses a typical home network setup:
- **Type**: Bridged networking
- **IP Allocation**: DHCP or Static (should be configurable)
- **Network Segments**: Private RFC1918 address space

### Configurable Network Parameters

Deployment scripts should support configuration for:
- `PROXMOX_HOST`: SSH connection string (e.g., `root@<hostname-or-ip>`)
- `VM_IP_MODE`: "dhcp" or "static"
- `VM_IP_ADDRESS`: If static mode (e.g., "192.168.x.x/24")
- `VM_GATEWAY`: If static mode (e.g., "192.168.x.1")
- `VM_BRIDGE`: Proxmox network bridge (typically "vmbr0")

## VM Resource Requirements

### Minimum Resources for PaperTrade

Based on prototype testing:
- **CPU**: 2 cores (minimum)
- **Memory**: 4GB RAM (minimum for all services)
- **Disk**: 20GB storage (10GB OS + 10GB for application data)

### Recommended Production Resources

- **CPU**: 4 cores (for better concurrent user handling)
- **Memory**: 8GB RAM (comfortable headroom)
- **Disk**: 50GB storage (allows for logs, backups, growth)

### Configurable Resource Parameters

```bash
PROXMOX_VM_CORES="4"          # Number of CPU cores
PROXMOX_VM_MEMORY="8192"       # RAM in MB
PROXMOX_VM_DISK_SIZE="50"      # Disk size in GB
```

## Storage Configuration

### Proxmox Storage

- **Type**: Local storage (common in homelab)
- **Path**: Typically /var/lib/vz or designated storage pool
- **Backend**: ZFS, LVM, or directory-based (varies)

### Configurable Storage Parameters

```bash
PROXMOX_STORAGE="local"        # Proxmox storage pool name
```

**Note**: The community Docker VM script may have its own storage configuration. Our scripts should respect or complement those settings.

## VM Identification

### VM ID Assignment

- **Range**: Proxmox VM IDs are typically 100-999999
- **Convention**: Use IDs 100+ for VMs (< 100 reserved for internal use)
- **Uniqueness**: Must be unique across the Proxmox cluster

### Configurable VM Parameters

```bash
PROXMOX_VM_ID="200"            # Unique VM identifier
PROXMOX_VM_HOSTNAME="papertrade"  # VM hostname
```

## Authentication & Access

### SSH Access Pattern

- **Method**: SSH key-based authentication (preferred)
- **Fallback**: Password authentication (if necessary)
- **User**: root (on Proxmox host and created VMs)

### Configurable Access Parameters

```bash
PROXMOX_HOST="root@proxmox.local"  # SSH connection string
PROXMOX_SSH_KEY="~/.ssh/id_rsa"    # SSH key path (optional)
```

### VM Access After Creation

Community Docker VM script creates VM with:
- **Username**: root
- **Default Password**: docker (should be changed)

Deployment scripts should:
1. Change default password or configure SSH keys
2. Disable password authentication (security best practice)
3. Configure for automation access

## Secrets & Environment Variables

### Deployment Context

Scripts will run in two contexts:
1. **Local development**: Using `.env` file
2. **GitHub Actions**: Using GitHub Secrets

### Required Secrets

```bash
# Application secrets (both contexts)
POSTGRES_PASSWORD="<secure-password>"
SECRET_KEY="<django-secret-key>"
ALPHA_VANTAGE_API_KEY="<api-key>"

# Proxmox access (primarily for GHA)
PROXMOX_HOST="<host>"
PROXMOX_SSH_PRIVATE_KEY="<key-content>"  # For GHA
```

### Security Considerations

- Secrets should never be committed to repository
- `.env` files should be in `.gitignore`
- GitHub Secrets should be used for CI/CD
- Consider secrets rotation strategy

## Docker Compose Stack

### Services Required

PaperTrade requires these services:
1. **PostgreSQL** (database)
2. **Redis** (cache/pub-sub)
3. **Backend** (FastAPI application)
4. **Frontend** (React + Nginx)

### Port Allocations

Typical port mapping:
- PostgreSQL: 5432
- Redis: 6379
- Backend API: 8000
- Frontend: 8080 (or 80)

### Health Checks

All services should have health checks configured in docker-compose.yml.

## Automation Considerations

### Tag-Based Deployment (Future)

When implementing GitHub Actions automation:
- Trigger: Git tag push (e.g., `v1.0.0`)
- Action: Deploy that version to Proxmox VM
- Verification: Health check before marking success

### Required Capabilities

Scripts should support:
- Non-interactive execution (for GHA)
- Clear exit codes (0 = success, non-zero = failure)
- JSON output option (for machine parsing)
- Progress indication (for human monitoring)

## Platform Assumptions

### What We Can Assume

- Standard Proxmox VE installation
- SSH access to Proxmox host
- Network connectivity from deployment machine to Proxmox
- Sufficient resources available for VM creation

### What We Should NOT Assume

- Specific IP addresses or network ranges
- Specific storage pool names
- Specific VM ID availability
- Existing VM or container configurations

## Configuration Strategy

### Recommended Approach

1. **Sensible Defaults**: Provide defaults that work for most cases
2. **Environment Variables**: Allow overriding via env vars
3. **Validation**: Check configuration before proceeding
4. **Documentation**: Clear examples for different scenarios

### Example Configuration File

```bash
# Proxmox Connection
PROXMOX_HOST="${PROXMOX_HOST:-root@proxmox}"

# VM Configuration
PROXMOX_VM_ID="${PROXMOX_VM_ID:-200}"
PROXMOX_VM_HOSTNAME="${PROXMOX_VM_HOSTNAME:-papertrade}"
PROXMOX_VM_CORES="${PROXMOX_VM_CORES:-4}"
PROXMOX_VM_MEMORY="${PROXMOX_VM_MEMORY:-8192}"
PROXMOX_VM_DISK_SIZE="${PROXMOX_VM_DISK_SIZE:-50}"

# Network
PROXMOX_VM_BRIDGE="${PROXMOX_VM_BRIDGE:-vmbr0}"
PROXMOX_VM_IP_MODE="${PROXMOX_VM_IP_MODE:-dhcp}"
```

---

**Important**: All specific values in this document are examples or reference data. The implementing agent should design scripts that use configurable parameters, not hard-coded values based on our specific environment.
