# Task 074: Production-Ready Proxmox Deployment via Docker VM

**Date**: 2026-01-11
**Agent**: quality-infra
**Branch**: main
**Priority**: High

## Objective

Implement a **production-ready deployment solution** for PaperTrade to Proxmox using a VM-based Docker environment. This is a clean implementation informed by prototype learnings, not an iteration on the prototype.

## Context

We have completed a prototype Proxmox deployment that successfully worked but identified that **VM-based deployment is superior to LXC** for production use. This task is to create a production-quality implementation from scratch, leveraging:

1. **Community Proxmox Scripts**: Battle-tested Docker VM creation
2. **Prototype Learnings**: What worked, what didn't, architectural insights
3. **Production Requirements**: Security, reliability, automation-readiness

### Key Resources (Read These First)

All resources are in the `docs/deployment/` directory:

1. **proxmox-learnings.md**: Why VM > LXC, what patterns worked, design goals
2. **community-scripts-reference.md**: Info about the Docker VM community script
3. **proxmox-environment-reference.md**: Environment details, configurable parameters

## Requirements

### Architecture

**VM-Based Docker Deployment**:
- Use the community Docker VM script for VM creation
  - URL: https://community-scripts.github.io/ProxmoxVE/scripts?id=docker-vm
  - Script: https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/vm/docker-vm.sh
  - **Important**: Fetch and examine this script to understand its parameters/configuration
- Deploy PaperTrade stack (PostgreSQL, Redis, Backend, Frontend) via Docker Compose
- Support both local development and future CI/CD workflows

### Core Functionality

Implement deployment automation that handles:

1. **Infrastructure Setup** (one-time):
   - VM creation using community script
   - Post-creation security hardening (change default password, configure SSH keys)
   - Network configuration (support both DHCP and static IP)

2. **Application Deployment** (repeatable):
   - Transfer application code to VM
   - Build Docker images in VM
   - Deploy stack with docker-compose.prod.yml
   - Verify all services are healthy

3. **Lifecycle Management**:
   - Start/stop services
   - Restart services
   - View logs
   - Check deployment status
   - Destroy VM (with confirmation)

4. **Operational Tools**:
   - Health check verification
   - Deployment status display
   - Troubleshooting information

### Configuration Strategy

**Configurable Parameters** (via environment variables with sensible defaults):

```bash
# Proxmox Connection
PROXMOX_HOST="${PROXMOX_HOST:-root@proxmox}"

# VM Configuration
PROXMOX_VM_ID="${PROXMOX_VM_ID:-200}"
PROXMOX_VM_HOSTNAME="${PROXMOX_VM_HOSTNAME:-papertrade}"
PROXMOX_VM_CORES="${PROXMOX_VM_CORES:-4}"
PROXMOX_VM_MEMORY="${PROXMOX_VM_MEMORY:-8192}"  # MB
PROXMOX_VM_DISK_SIZE="${PROXMOX_VM_DISK_SIZE:-50}"  # GB

# Network Configuration
PROXMOX_VM_BRIDGE="${PROXMOX_VM_BRIDGE:-vmbr0}"
PROXMOX_VM_IP_MODE="${PROXMOX_VM_IP_MODE:-dhcp}"
# If static:
PROXMOX_VM_IP_ADDRESS="${PROXMOX_VM_IP_ADDRESS:-}"  # e.g., "192.168.1.100/24"
PROXMOX_VM_GATEWAY="${PROXMOX_VM_GATEWAY:-}"  # e.g., "192.168.1.1"

# Application Configuration
APP_DIR="${APP_DIR:-/opt/papertrade}"
```

**Secrets Management**:
- Support both `.env` file (local development)
- Support GitHub Secrets (for future CI/CD)
- Never regenerate secrets on redeployment (preserve existing `.env` in VM)
- Clear documentation on required secrets

### Tool Selection

**Primary Interface**: Taskfile (go-task)
- Proven pattern from prototype
- User-friendly commands: `task proxmox:deploy`, `task proxmox:status`
- Environment variable integration
- Cross-platform compatibility

**Implementation Language**: Bash scripts
- Called by Taskfile tasks
- Located in `scripts/proxmox-vm/` (new directory, not reusing prototype scripts)
- Well-structured with error handling (`set -euo pipefail`)
- Colored output for user feedback
- Clear error messages

### Future Automation Considerations

While not implementing now, design should support **tag-based deployments** via GitHub Actions:

- Scripts should work non-interactively (from CI/CD)
- Clear success/failure exit codes
- Environment variable configuration (no interactive prompts)
- SSH key-based authentication support
- Deployment verification built-in

**Workflow Vision**:
```
Push tag v1.0.0 → GHA runs → SSH to Proxmox → Deploy via scripts → Verify → Success
```

## Deliverables

### 1. Deployment Scripts

Create in `scripts/proxmox-vm/` directory:

- **create-vm.sh**: VM creation wrapper
  - Leverage community Docker VM script
  - Configure VM parameters
  - Post-creation hardening (passwords, SSH keys)
  - Network configuration
  
- **deploy.sh**: Application deployment
  - Transfer code to VM (efficient method - tarball, rsync, or git)
  - Build Docker images
  - Deploy with docker-compose.prod.yml
  - Verify deployment success (health checks with timeout)
  
- **lifecycle.sh**: Service management
  - Start/stop/restart operations
  - Status checking
  - Log viewing
  
- **destroy.sh**: VM destruction
  - Confirmation prompt (unless forced)
  - Clean removal of VM

### 2. Taskfile Tasks

Add to `Taskfile.yml` under `proxmox-vm:` namespace:

```yaml
proxmox-vm:create:
  desc: "Create Docker VM on Proxmox"
  
proxmox-vm:deploy:
  desc: "Deploy PaperTrade to Proxmox VM"
  
proxmox-vm:status:
  desc: "Check deployment status"
  
proxmox-vm:logs:
  desc: "View application logs"
  
proxmox-vm:start:
  desc: "Start services"
  
proxmox-vm:stop:
  desc: "Stop services"
  
proxmox-vm:restart:
  desc: "Restart services"
  
proxmox-vm:destroy:
  desc: "Destroy VM (WARNING: destructive)"
```

### 3. Documentation

Create `docs/deployment/proxmox-vm-deployment.md`:

- **Quick Start**: Get running in 5 minutes
- **Configuration Reference**: All environment variables
- **Deployment Guide**: Step-by-step instructions
- **Troubleshooting**: Common issues and solutions
- **Security Considerations**: What to know for production
- **CI/CD Integration Guide**: How to use with GitHub Actions (future)

### 4. Configuration Examples

Create `.env.example.proxmox` showing:
- All required configuration
- Commented explanations
- Both DHCP and static IP examples

## Success Criteria

- [ ] VM can be created with single command: `task proxmox-vm:create`
- [ ] Application deploys successfully: `task proxmox-vm:deploy`
- [ ] Health checks verify all 4 services are running
- [ ] Deployment survives `task proxmox-vm:restart`
- [ ] Secrets are preserved across redeployments
- [ ] Clear error messages for common failures
- [ ] Documentation is comprehensive and accurate
- [ ] All configuration is via environment variables (no hard-coded IPs/values)
- [ ] Works with both DHCP and static IP configuration
- [ ] Scripts have proper error handling and exit codes

## Testing Notes

**Important**: The agent will not have access to the actual Proxmox server during implementation. Design for testability:

- Scripts should validate configuration before attempting connections
- Clear error messages for SSH connection failures
- Dry-run mode would be helpful (optional)
- We will test manually after implementation

## Design Principles

### Do's ✅

- Use community Docker VM script (don't reinvent VM creation)
- Make everything configurable via environment variables
- Provide sensible defaults for all parameters
- Include comprehensive error handling
- Write clear, well-documented code
- Consider future automation needs (GHA)
- Preserve secrets across deployments
- Verify deployment success before completion

### Don'ts ❌

- Don't hard-code IP addresses, hostnames, or IDs
- Don't reinvent what community scripts already do
- Don't copy/maintain the community script (fetch it)
- Don't include prototype-specific workarounds
- Don't over-engineer (KISS principle)
- Don't require manual intervention for CI/CD-compatible tasks
- Don't regenerate secrets on every deployment

## Architecture Decisions

### Why VM (not LXC)?

See `proxmox-learnings.md` for full analysis. TL;DR:
- Better security (full hardware virtualization)
- Simpler configuration (no AppArmor issues)
- Production-ready isolation
- Community script handles complexity

### Why Community Script?

- Maintained by community (thousands of deployments)
- Handles edge cases we discovered in prototype
- Regular updates for new Proxmox versions
- Battle-tested and reliable

### Why Taskfile?

- Proven in prototype
- Simple, cross-platform
- Environment variable integration
- Easy to extend

## Non-Goals

This implementation does NOT need to:

- Support LXC deployment (VM only)
- Support multiple Proxmox hosts (single host is fine)
- Implement custom secrets management (GitHub Secrets + .env is sufficient)
- Build container registry (build in VM is fine)
- Support Kubernetes or Swarm (Docker Compose is sufficient)
- Migrate data from prototype (fresh deployment)

## References

1. **Learnings Document**: `docs/deployment/proxmox-learnings.md`
2. **Community Script Info**: `docs/deployment/community-scripts-reference.md`
3. **Environment Reference**: `docs/deployment/proxmox-environment-reference.md`
4. **Community Script**: https://community-scripts.github.io/ProxmoxVE/scripts?id=docker-vm
5. **Script Source**: https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/vm/docker-vm.sh

## Implementation Notes

1. **Start by examining the community script**: Understand what it does, what's configurable, what defaults it uses
2. **Design wrapper scripts** that complement (not duplicate) the community script
3. **Test configuration validation** thoroughly (we can't test actual deployment)
4. **Write excellent documentation** (we'll need it for manual testing)
5. **Think about the user experience**: Clear commands, helpful output, good error messages

## Agent Instructions

1. Read all three reference documents in `docs/deployment/`
2. Fetch and examine the community Docker VM script to understand its capabilities
3. Design the deployment automation architecture
4. Implement scripts, Taskfile tasks, and documentation
5. Ensure everything is production-ready and well-documented

---

**Remember**: This is a clean implementation, not an iteration on the prototype. Design for production use from day one. The prototype taught us what works - now implement it properly!
