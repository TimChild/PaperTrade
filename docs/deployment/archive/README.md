# Deployment Documentation Archive

This directory contains historical deployment documentation that provides valuable context but has been superseded by the current deployment guides.

## Archived Documents

### community-scripts-reference.md
**Date**: January 11, 2026  
**Status**: Reference information integrated into main proxmox.md guide  
**Value**: Detailed analysis of Proxmox community Docker VM script

This document provided a deep dive into the community script's functionality. The key insights have been integrated into the main Proxmox deployment guide.

### proxmox-environment-reference.md
**Date**: January 11, 2026  
**Status**: Reference information, configuration now in .env.proxmox.example  
**Value**: Environment-specific configuration examples

This document captured our specific Proxmox environment details. The valuable parts (configurable parameters, resource requirements) are now in the main guide and example configuration files.

### proxmox-learnings.md
**Date**: January 11, 2026  
**Status**: Historical context, key insights integrated  
**Value**: Lessons learned from prototype deployment work

Documents the journey from LXC experiments to the final VM-based approach. The architectural decisions and rationale are preserved in the main guide's "Why VM over LXC?" section.

**Key Insight**: VMs provide better security isolation and simpler Docker deployment compared to LXC containers, especially on newer Proxmox kernels.

### proxmox-vm-approach-comparison.md
**Date**: January 11, 2026  
**Status**: Historical analysis, decision documented in main guide  
**Value**: Detailed comparison of community script vs manual qm commands

An in-depth analysis of whether to use the community Docker VM script interactively or implement fully automated VM creation with qm commands. 

**Decision**: Use community script for VM creation (infrequent operation) and focus automation on deployment/lifecycle (frequent operations).

## Why Archive These?

These documents were created during the exploration and prototyping phase of Proxmox deployment. They contain:
- Decision-making rationale
- Comparisons of different approaches
- Environment-specific details that informed the final design
- Historical context for future reference

The current deployment guides ([proxmox.md](../proxmox.md), [domain-setup.md](../domain-setup.md)) are authoritative and should be used for actual deployment. These archived documents provide the "why" behind design decisions for anyone who needs deeper context.

## Active Deployment Guides

For current deployment instructions, see:
- **[../README.md](../README.md)** - Deployment overview and index
- **[../proxmox.md](../proxmox.md)** - Complete Proxmox deployment guide
- **[../domain-setup.md](../domain-setup.md)** - Domain and SSL setup
- **[../production-checklist.md](../production-checklist.md)** - Production readiness checklist

---

*These documents are preserved for historical context and to document the evolution of our deployment approach.*
