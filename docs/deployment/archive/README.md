# Deployment Documentation Archive

This directory contains historical deployment documentation preserved for context and reference.

**These documents are not needed for current deployments** - see the parent directory for active guides.

---

## Archived Documents

### [Proxmox Learnings](./proxmox-learnings.md)
**Date**: January 11, 2026  
**Purpose**: Captured lessons from prototype deployment work

**Key insights preserved**:
- Why VM deployment is preferred over LXC (security, simplicity)
- Benefits of using community Docker VM scripts
- Secrets management considerations
- Network configuration best practices

**Status**: Historical - insights have been integrated into current deployment guide

---

### [VM vs LXC Comparison](./proxmox-vm-approach-comparison.md)
**Date**: January 11, 2026  
**Purpose**: Detailed technical comparison of VM vs LXC deployment approaches

**Decision made**: Use VM-based deployment with community script

**Key points**:
- LXC requires privileged containers and AppArmor modifications
- VMs provide better security isolation
- Community script handles Docker pre-installation elegantly
- Interactive VM creation is acceptable for infrequent operations

**Status**: Historical - decision has been made, comparison preserved for reference

---

### [Environment Reference](./proxmox-environment-reference.md)
**Date**: January 11, 2026  
**Purpose**: Reference configuration for original Proxmox environment

**Content**:
- Network configuration patterns
- Resource allocation guidelines
- VM identification conventions
- Storage configuration approaches

**Status**: Historical - specific to original environment, current guide uses configurable parameters

---

### [Community Scripts Reference](./community-scripts-reference.md)
**Date**: January 11, 2026  
**Purpose**: Documentation about Proxmox community Docker VM script

**Content**:
- Script source and installation
- Default configuration
- Integration strategy
- What the script handles vs what our scripts handle

**Status**: Historical - information integrated into main deployment guide

---

## Why These Are Archived

These documents served important purposes during development:

1. **Decision Documentation**: Captured reasoning for architectural choices (VM vs LXC)
2. **Learning Capture**: Preserved insights from prototype work
3. **Context Preservation**: Detailed exploration of trade-offs and alternatives
4. **Reference Material**: Background on community scripts and environment setup

However, they are **not needed for deployment** because:

- ✅ Insights have been integrated into active guides
- ✅ Decisions have been made and implemented
- ✅ Current guides are comprehensive and actionable
- ✅ Historical context adds unnecessary complexity for new users

---

## When to Read These

You might find these useful if you:

- **Want historical context** on why certain decisions were made
- **Are considering alternative approaches** (e.g., LXC instead of VM)
- **Are debugging issues** related to the original prototype work
- **Are documenting your own deployment decisions** and want examples

For **actual deployment**, use the guides in the parent directory:
- [Proxmox VM Deployment](../proxmox-vm-deployment.md)
- [Domain & SSL Setup](../domain-setup.md)
- [Production Checklist](../production-checklist.md)

---

## Preservation Policy

These documents are preserved for:
- Historical record
- Decision rationale
- Learning reference
- Future comparisons

They will not be updated to reflect current practices. For current information, see parent directory guides.

---

**Return to**: [Deployment Documentation](../README.md)
