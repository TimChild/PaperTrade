# Proxmox Deployment - Key Learnings from Prototype

**Date**: January 11, 2026
**Source**: Prototype work in `feat/proxmox-deployment-automation` branch and PR #117 evaluation

## Purpose

This document captures key learnings from our Proxmox deployment prototype to inform a production-ready implementation. The prototype successfully deployed Zebu to Proxmox but identified important architectural and security considerations.

## Executive Summary

**Key Finding**: While Docker-in-LXC works for development, **VM-based deployment is the recommended production approach** for security, simplicity, and maintainability.

## Deployment Architecture Considerations

### Why VM Over LXC for Production

**LXC Limitations Discovered**:
- **Privileged containers required** for Docker compatibility (on newer Proxmox kernels)
- **AppArmor must be disabled** to avoid Docker build failures
- **Security implications**: Container escape = full host compromise
- **Added complexity**: User namespace mapping, overlay filesystem configuration

**VM Advantages**:
- **Full hardware virtualization** = strong isolation
- **Native Docker support** without special configuration
- **Better security posture** for production workloads
- **Simpler to configure** and maintain
- **Live migration** and **backup/restore** more reliable

**Bottom Line**: VMs provide better security with lower complexity for Docker workloads.

### Community Scripts as Foundation

The Proxmox community maintains battle-tested scripts for Docker deployment:
- **Docker VM Script**: https://community-scripts.github.io/ProxmoxVE/scripts?id=docker-vm
- **Script Repository**: https://github.com/community-scripts/ProxmoxVE

**Why Use Them**:
- Maintained by community with thousands of deployments
- Handle edge cases we discovered (AppArmor, networking, storage)
- Regular updates for new Proxmox versions
- Configurable for different use cases

**Recommendation**: Build on top of these scripts rather than custom VM creation.

## What Worked Well

### Taskfile Integration Pattern

Using Task (go-task) for deployment automation proved highly effective:
- Simple interface: `task proxmox:deploy`, `task proxmox:status`
- Environment variable configuration
- Easy to extend with new commands
- Cross-platform compatibility

**Pattern to Preserve**: Continue using Taskfile as the primary interface.

### Deployment Workflow Structure

The prototype established a good workflow pattern:
1. **Create infrastructure** (one-time setup)
2. **Deploy application** (repeatable)
3. **Monitor status** (operational)
4. **Manage lifecycle** (start/stop/restart)

**Pattern to Preserve**: Maintain this separation of concerns.

### Health Check Verification

Automated verification that services are healthy before deployment completes:
- Prevents silent failures
- Clear feedback on deployment status
- Timeout-based with visual progress

**Pattern to Preserve**: Always verify deployment success programmatically.

## Security Considerations

### Secrets Management

**What We Learned**:
- Generating random passwords on each deploy breaks persistence
- Plain text `.env` files are acceptable for development, problematic for production
- Need strategy for both CI/CD (GitHub Secrets) and local development (`.env`)

**Considerations for New Implementation**:
- Preserve secrets across redeployments
- Support both GitHub Secrets and local `.env` workflows
- Consider secrets rotation strategy
- Document security model clearly

### Network Configuration

**What We Learned**:
- DHCP IPs can change, breaking bookmarks and automation
- Static IP configuration is important for production
- Firewall rules should be configurable

**Considerations for New Implementation**:
- Make network configuration flexible (DHCP vs static)
- Document firewall requirements
- Consider future GHA automation needs (webhook endpoints, etc.)

### Resource Allocation

**What We Learned**:
- Container/VM sizing should be configurable
- Different environments need different resources
- Community scripts often have sensible defaults

**Considerations for New Implementation**:
- Make resource allocation configurable
- Provide recommended minimums
- Allow overrides for specific use cases

## Automation & CI/CD Readiness

### Future GitHub Actions Integration

While not implementing now, design should consider:
- **Tag-based deployments**: Push tag → deploy that version to Proxmox
- **Secrets flow**: GitHub Secrets → Proxmox deployment
- **Remote execution**: GHA can SSH to Proxmox or use Proxmox API
- **Deployment verification**: Health checks should be automation-friendly

**Design Principles**:
- Scripts should work from both local shell and CI/CD
- Configuration via environment variables
- Clear success/failure exit codes
- JSON output option for machine parsing

## Implementation Guidelines for New Solution

### What to Build

1. **VM creation automation** (leveraging community script)
2. **Application deployment scripts** (transferring code, building images, starting services)
3. **Lifecycle management** (start, stop, restart, status, logs)
4. **Documentation** (setup guide, configuration reference, troubleshooting)

### What to Avoid

- Don't reinvent VM creation (use community scripts)
- Don't over-engineer (avoid unnecessary abstraction layers)
- Don't lock in specific IPs/hostnames (make configurable)
- Don't include prototype-specific workarounds in clean implementation

### Design Goals

- **Production-ready**: Secure by default
- **Well-documented**: Clear setup and usage instructions
- **Configurable**: Support different environments/requirements
- **Maintainable**: Use community standards and tools
- **Future-proof**: Consider GHA automation compatibility

## Resources for Implementation

- **Community Docker VM Script**: https://community-scripts.github.io/ProxmoxVE/scripts?id=docker-vm
- **Evaluation Document**: See prototype branch for detailed security analysis
- **Proxmox Environment**: Details in separate document

## Non-Goals

The new implementation does NOT need to:
- Support LXC deployment (VM only)
- Implement custom secrets management (GitHub Secrets + .env is sufficient)
- Build container registry (build in VM is fine)
- Support multiple deployment targets (single Proxmox host is fine)

---

**Note**: This document intentionally avoids specific implementation details (bash code, exact configurations) to allow the implementing agent to make optimal design decisions based on current best practices and available tools.
