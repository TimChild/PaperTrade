# Proxmox VM Deployment Scripts

This directory contains scripts for deploying Zebu to Proxmox using a VM-based Docker environment.

## Scripts Overview

| Script | Purpose | Usage |
|--------|---------|-------|
| `common.sh` | Shared utilities and functions | Sourced by other scripts |
| `create-vm.sh` | Create Docker VM on Proxmox | `task proxmox-vm:create` |
| `deploy.sh` | Deploy application to VM | `task proxmox-vm:deploy` |
| `lifecycle.sh` | Manage services (start/stop/restart/status/logs) | `task proxmox-vm:status` etc. |
| `destroy.sh` | Destroy VM (destructive) | `task proxmox-vm:destroy` |

## Quick Start

```bash
# 1. Configure connection to Proxmox
export PROXMOX_HOST=root@proxmox

# 2. Create VM
task proxmox-vm:create

# 3. Deploy application
task proxmox-vm:deploy

# 3a. Deploy specific version (tag, branch, or commit)
VERSION=v1.0.0 task proxmox-vm:deploy

# 4. Check status
task proxmox-vm:status
```

## Environment Variables

All scripts use environment variables for configuration. See `.env.proxmox.example` for complete reference.

Key variables:
- `PROXMOX_HOST` - SSH connection to Proxmox (default: `root@proxmox`)
- `PROXMOX_VM_ID` - VM identifier (default: `200`)
- `PROXMOX_VM_HOSTNAME` - VM hostname (default: `papertrade`)
- `PROXMOX_VM_CORES` - CPU cores (default: `4`)
- `PROXMOX_VM_MEMORY` - RAM in MB (default: `8192`)
- `PROXMOX_VM_DISK_SIZE` - Disk in GB (default: `50`)
- `VERSION` - Git tag, branch, or commit to deploy (optional, defaults to current branch)

## Architecture

These scripts implement a production-ready VM-based deployment:

1. **VM Creation** - Uses community Docker VM script to create Debian 12 VM with Docker pre-installed
2. **Application Deployment** - Transfers code, builds images, starts services
3. **Service Management** - Standard lifecycle operations
4. **Health Checking** - Verifies all services are healthy

## Design Principles

- **Environment-based configuration** - No hard-coded values
- **Idempotent operations** - Can be run multiple times safely
- **Error handling** - Fail fast with clear error messages
- **Colored output** - Visual feedback for operations
- **Secrets preservation** - Maintains secrets across redeployments

## Deployment Options

The deployment script supports deploying different versions using the `VERSION` environment variable:

```bash
# Deploy current branch (default behavior)
task proxmox-vm:deploy

# Deploy a specific git tag
VERSION=v1.0.0 task proxmox-vm:deploy

# Deploy a specific branch
VERSION=main task proxmox-vm:deploy
VERSION=feature/new-feature task proxmox-vm:deploy

# Deploy a specific commit
VERSION=abc123def task proxmox-vm:deploy
```

The script automatically detects whether the VERSION is a tag, branch, or commit SHA and handles it appropriately.

## Common Functions (common.sh)

The `common.sh` script provides reusable utilities:

**Output Functions:**
- `log_info()` - Informational messages
- `log_success()` - Success messages
- `log_warning()` - Warning messages
- `log_error()` - Error messages
- `log_step()` - Step indicators

**Configuration:**
- `load_env_with_defaults()` - Load all env vars with defaults
- `display_config()` - Show current configuration
- `validate_env()` - Validate required variables

**VM Operations:**
- `check_proxmox_connection()` - Test SSH to Proxmox
- `vm_exists()` - Check if VM exists
- `get_vm_status()` - Get VM status (running, stopped, etc.)
- `get_vm_ip()` - Retrieve VM IP address
- `wait_for_vm_ssh()` - Wait for SSH accessibility
- `wait_for_services_healthy()` - Wait for all services to be healthy

## Testing

Scripts cannot be fully tested without a Proxmox environment, but you can:

```bash
# Test syntax
bash -n scripts/proxmox-vm/*.sh

# Test configuration loading
bash -c 'source scripts/proxmox-vm/common.sh && load_env_with_defaults && display_config'

# Dry run (will fail at Proxmox connection)
PROXMOX_HOST=test@test task proxmox-vm:status
```

## CI/CD Integration

Scripts are designed for use in GitHub Actions:

```yaml
- name: Deploy to Proxmox
  env:
    PROXMOX_HOST: ${{ secrets.PROXMOX_HOST }}
    PROXMOX_VM_ID: ${{ secrets.PROXMOX_VM_ID }}
  run: task proxmox-vm:deploy
```

## Error Handling

All scripts use `set -euo pipefail` for strict error handling:
- `set -e` - Exit on error
- `set -u` - Exit on undefined variable
- `set -o pipefail` - Pipeline failures cause exit

## Documentation

See `docs/deployment/proxmox.md` for comprehensive documentation including:
- Quick start guide
- Configuration reference
- Troubleshooting
- Security considerations
- CI/CD integration examples

## Support

For issues or questions, see the main deployment documentation or open an issue on GitHub.
