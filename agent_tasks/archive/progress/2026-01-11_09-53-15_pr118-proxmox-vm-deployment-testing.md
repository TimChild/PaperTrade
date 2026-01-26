# PR #118 Proxmox VM Deployment Testing

**Date**: 2026-01-11
**Agent**: Orchestrator (Manual Testing)
**Related Task**: agent_tasks/097_production-proxmox-deployment.md
**PR**: #118 (copilot/production-ready-proxmox-deployment)

## Task Summary

Tested the production-ready Proxmox VM deployment implementation created by agent #118. Identified critical compatibility issues and successfully created VM manually to understand the workflow.

## Issues Found

### 1. macOS Compatibility Issue (FIXED)
**Problem**: `grep -P` (Perl regex) used in `get_vm_ip()` function is not available on macOS.

**Location**: `scripts/proxmox-vm/common.sh` line 169

**Error**:
```
grep: invalid option -- P
usage: grep [-abcdDEFGHhIiJLlMmnOopqRSsUVvwXxZz] [-A num] [-B num] [-C[num]]
```

**Solution**: Replaced with portable `sed` command:
```bash
# Before (Linux-only)
vm_ip=$(ssh "$PROXMOX_HOST" "qm guest cmd $vm_id network-get-interfaces 2>/dev/null" | \
        grep -oP '"ip-address":\s*"\K[0-9.]+' | \
        grep -v "127.0.0.1" | \
        head -1)

# After (macOS + Linux compatible)
vm_ip=$(ssh "$PROXMOX_HOST" "qm guest cmd $vm_id network-get-interfaces 2>/dev/null" | \
        sed -n 's/.*"ip-address"[[:space:]]*:[[:space:]]*"\([0-9.]*\)".*/\1/p' | \
        grep -v "127.0.0.1" | \
        head -1)
```

**Status**: ✅ Fixed and committed (commit a819936)

### 2. Community Docker VM Script Non-Interactive Issue
**Problem**: The community Docker VM creation script requires an interactive terminal and cannot be automated via stdin/heredoc.

**Evidence**:
- Script checks for TERM environment variable
- Uses interactive dialogs for configuration
- `printf | ssh bash script` approach fails with "User exited script"
- `TERM environment variable not set` errors

**Impact**: Cannot automatically create VM as documented in agent's implementation

**Workaround**: Manual VM creation using `qm` commands directly

### 3. Docker Installation Not Automated
**Problem**: Created VM has Debian 12 but no Docker installation.

**Root Cause**: Community script installs Docker, but since it can't run non-interactively, VM needs Docker installed separately.

**Current State**:
- VM 200 created successfully at 192.168.4.230
- SSH access working (cloud-init configured keys)
- Docker not installed
- cloud-init still running on first boot (holding dpkg lock)

## Successful Manual VM Creation

Created VM 200 manually using `qm` commands as proof of concept:

```bash
# Downloaded Debian 12 cloud image
wget https://cloud.debian.org/images/cloud/bookworm/latest/debian-12-generic-amd64.qcow2

# Created VM with qm
qm create 200 --name papertrade --memory 8192 --cores 4 --net0 virtio,bridge=vmbr0
qm importdisk 200 debian-12-generic-amd64.qcow2 local-lvm
qm set 200 --scsihw virtio-scsi-pci --scsi0 local-lvm:vm-200-disk-0
qm set 200 --ide2 local-lvm:cloudinit
qm set 200 --boot c --bootdisk scsi0
qm set 200 --serial0 socket --vga serial0
qm set 200 --agent enabled=1
qm resize 200 scsi0 50G

# Configured static IP and SSH keys via cloud-init
qm set 200 --ipconfig0 ip=192.168.4.230/24,gw=192.168.4.1
qm set 200 --ciuser root
qm set 200 --cipassword docker
qm set 200 --sshkeys /root/.ssh/authorized_keys
```

**Result**: VM successfully created, started, and accessible at 192.168.4.230

## Recommendations

### 1. Update create-vm.sh Script
Replace community script automation with direct `qm` commands:

```bash
# Use qm directly instead of relying on community script
qm create $VMID --name $HOSTNAME \
  --memory $MEMORY --cores $CORES \
  --net0 virtio,bridge=$BRIDGE

# Import cloud image
qm importdisk $VMID /path/to/debian-cloud-image.qcow2 local-lvm

# Configure VM (disk, cloud-init, networking)
# Add Docker installation step after VM boots
```

### 2. Add Docker Installation Function
Create `install-docker.sh` or add function to `deploy.sh`:

```bash
# Wait for cloud-init to finish
ssh $VM_IP 'cloud-init status --wait'

# Install Docker
ssh $VM_IP 'bash -s' << 'EOF'
  apt-get update && apt-get install -y curl
  curl -fsSL https://get.docker.com | sh
  systemctl enable --now docker
EOF
```

### 3. Document Manual VM Creation
Add fallback instructions for when automation fails:
- Provide exact `qm` commands users can run
- Document cloud-init configuration
- Include Docker installation steps

### 4. Consider Packer for VM Image
Long-term solution: Use Packer to pre-build VM image with Docker:
- Creates reproducible VM template
- Includes Docker pre-installed
- Faster deployment (no package installation needed)
- Can be stored in Proxmox as template

## Next Steps

1. **Update create-vm.sh**: Replace community script with direct `qm` commands
2. **Test Docker installation**: Complete Docker setup on VM 200
3. **Test full deployment**: Run `task proxmox-vm:deploy` once Docker is ready
4. **Document limitations**: Update docs with macOS-specific issues
5. **Consider Packer approach**: Evaluate for future enhancement

## Testing Notes

### Environment
- Proxmox VE 8 (Debian 13, kernel 6.14.11-4-pve)
- Proxmox host: 192.168.4.200
- VM 200: 192.168.4.230 (static IP)
- Local machine: macOS (where `grep -P` issue was discovered)

### Commands Tested
- ✅ `task proxmox-vm:create` - Started but failed due to grep issue
- ✅ Manual VM creation - Successful
- ✅ SSH to VM - Successful (cloud-init SSH keys working)
- ⏳ Docker installation - In progress (cloud-init blocking dpkg)
- ⏸️ `task proxmox-vm:deploy` - Not yet tested
- ⏸️ Full stack deployment - Not yet tested

## Files Modified

- `scripts/proxmox-vm/common.sh` - Fixed grep -P compatibility issue

## Known Limitations

1. **macOS/Linux portability**: Some bash features may differ
2. **Community script dependency**: Cannot be automated as designed
3. **First boot timing**: cloud-init holds dpkg lock during first boot
4. **No VM template**: Each deployment creates VM from scratch

## Additional Observations

- Cloud-init works well for SSH key injection and static IP configuration
- qm commands provide more control than community script
- VM boots quickly (~30 seconds to SSH accessible)
- Static IP configuration via cloud-init works reliably
- Root SSH access enabled (should consider security hardening)
