# Community Proxmox Scripts - Docker VM Information

**Source**: https://community-scripts.github.io/ProxmoxVE/scripts?id=docker-vm
**Date Captured**: January 11, 2026

## Overview

The Proxmox VE Helper-Scripts community maintains a Docker VM script that automates the creation of a Debian-based VM with Docker Engine and Docker Compose pre-installed.

**Project Repository**: https://github.com/community-scripts/ProxmoxVE

## Docker VM Script

### Description

Docker is an open-source project for automating the deployment of applications as portable, self-sufficient containers. This template includes:
- Docker Engine
- Docker Compose Plugin
- Debian 12 base system

**Architecture Support**: Works on both amd64 and arm64.

### Installation Command

**Important**: The agent should attempt to fetch this directly from the URL below rather than copying/maintaining it locally.

```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/vm/docker-vm.sh)"
```

### Default Configuration

The script creates a VM with these defaults:
- **OS**: Debian 12
- **CPU**: 2 vCPU
- **Memory**: 4GB RAM
- **Disk**: 10GB storage

### Default Credentials

**Important**: These are the default credentials for the VM created by the community script.

- **Username**: `root`
- **Password**: `docker`

**Security Note**: These credentials should be changed immediately after VM creation or as part of the deployment automation.

### Script Customization

The community script is designed to be run interactively or can be customized via environment variables (the agent should examine the script directly to determine available configuration options).

**Script Source**: https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/vm/docker-vm.sh

The agent should:
1. Fetch the script to understand its parameters
2. Determine what can be configured (VM ID, resources, network, etc.)
3. Design wrapper scripts that leverage the community script with appropriate configurations
4. Avoid duplicating the community script's functionality

### What the Community Script Handles

Based on the description and typical Proxmox VM creation patterns, the script likely handles:
- VM creation and ID assignment
- Operating system installation (Debian 12)
- Docker Engine installation
- Docker Compose Plugin installation
- Basic networking configuration
- Storage allocation

### What Our Deployment Scripts Should Handle

Since the community script creates the Docker-ready VM, our scripts should focus on:
- Transferring the Zebu application code
- Building Docker images
- Deploying the application stack (PostgreSQL, Redis, Backend, Frontend)
- Configuring secrets and environment variables
- Managing application lifecycle (start, stop, restart, logs)
- Health checking and verification

## Integration Strategy

### Recommended Approach

1. **VM Creation**: Use community script with appropriate configuration
2. **Post-Creation Setup**:
   - Change default root password (automation-friendly)
   - Configure SSH key access
   - Set static IP if needed
3. **Application Deployment**:
   - Transfer code to VM
   - Build and run Docker containers
   - Verify deployment success

### Configuration Points to Expose

Our deployment automation should make these configurable:
- Proxmox host connection details
- VM resource allocation (if community script supports it)
- Network configuration (static IP vs DHCP)
- Application-specific settings (database passwords, API keys)

## Additional Resources

- **Main Documentation**: https://community-scripts.github.io/ProxmoxVE/
- **GitHub Repository**: https://github.com/community-scripts/ProxmoxVE
- **Script Source**: https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/vm/docker-vm.sh
- **Discord Community**: https://discord.gg/3AnUqsXnmK (for questions/support)

## Notes for Implementation

1. **Fetch Script Directly**: Always use the latest version from the repository
2. **Understand Parameters**: Examine the script to see what's configurable
3. **Don't Fork**: Avoid maintaining a local copy; let the community maintain it
4. **Complement, Don't Duplicate**: Build deployment automation that works with the VM the script creates
5. **Stay Updated**: Community scripts receive updates for new Proxmox versions and bug fixes

---

**Important**: This document provides reference information only. The implementing agent should fetch and examine the actual script to determine the best integration approach.
