# Proxmox VM Deployment: Community Script vs qm Commands

## TL;DR Recommendation

**Stick with the community script (interactive approach)** for your use case.

**Why?** The script does significant heavy lifting with Docker installation that would be complex to replicate. Since you're creating VMs infrequently, the interactive overhead is minimal compared to the maintenance burden of reimplementing all the script's functionality.

## What the Community Script Actually Does

### Key Value: Docker Pre-Installation
The script uses `virt-customize` to **inject Docker into the disk image before first boot**:

```bash
# Downloads Debian 12 cloud image
curl https://cloud.debian.org/images/cloud/bookworm/latest/debian-12-nocloud-amd64.qcow2

# Modifies the image OFFLINE using libguestfs
virt-customize -a debian-12.qcow2 --install qemu-guest-agent,docker-ce,...
virt-customize -a debian-12.qcow2 --run-command "install Docker GPG keys"
virt-customize -a debian-12.qcow2 --run-command "add Docker apt repo"
virt-customize -a debian-12.qcow2 --run-command "apt-get install docker-ce..."
virt-customize -a debian-12.qcow2 --run-command "systemctl enable docker"
```

**This is brilliant because:**
- Docker is pre-installed before VM ever boots
- No waiting for cloud-init to finish
- No dpkg lock issues
- Image is ready to use immediately

### Other Important Features

1. **Storage Pool Selection**: Interactive menu to choose storage (local-lvm, ZFS, NFS, etc.)
2. **Smart VM ID Generation**: Checks for conflicts with both VMs and LXCs
3. **Disk Resizing**: Expands the cloud image to your requested size
4. **EFI Configuration**: Properly sets up OVMF/EFI for modern boot
5. **QEMU Guest Agent**: Installed and enabled
6. **Error Handling**: Cleanup on failure, proper trap handlers
7. **Proxmox Version Checking**: Ensures compatibility with PVE 8.x/9.x

## Comparison Matrix

| Aspect | Community Script | qm Commands |
|--------|-----------------|-------------|
| **Docker Installation** | ✅ Pre-baked into image | ❌ Manual post-boot install |
| **Automation** | ❌ Requires interactive terminal | ✅ Fully scriptable |
| **Maintenance** | ✅ Community maintains | ❌ We maintain |
| **Setup Time** | ~5 minutes interactive | ~2 minutes automated + post-install |
| **First Boot** | ✅ Docker ready immediately | ❌ Need cloud-init wait + install |
| **Storage Selection** | ✅ Interactive picker | ❌ Hardcoded in script |
| **Error Handling** | ✅ Built-in cleanup | ❌ We implement |
| **Updates** | ✅ Get upstream fixes | ❌ Manual updates |
| **CI/CD** | ❌ Can't automate | ✅ Can automate |
| **Complexity** | Low (run script) | High (200+ lines to replicate) |

## The qm Alternative (What We'd Need to Implement)

### Minimum Viable Approach
```bash
# Download cloud image
wget debian-12-generic-amd64.qcow2

# Create VM
qm create $VMID --name $HOSTNAME --memory $RAM --cores $CORES \
  --net0 virtio,bridge=$BRIDGE --agent enabled=1

# Import and configure disk
qm importdisk $VMID debian-12-generic-amd64.qcow2 local-lvm
qm set $VMID --scsihw virtio-scsi-pci --scsi0 local-lvm:vm-$VMID-disk-0
qm set $VMID --boot c --bootdisk scsi0

# Cloud-init
qm set $VMID --ide2 local-lvm:cloudinit
qm set $VMID --ipconfig0 ip=$IP/24,gw=$GATEWAY
qm set $VMID --ciuser root --cipassword docker
qm set $VMID --sshkeys ~/.ssh/authorized_keys

# Start VM
qm start $VMID

# Wait for cloud-init (30-60 seconds)
ssh $VM_IP 'cloud-init status --wait'

# Install Docker POST-BOOT (another 2-5 minutes)
ssh $VM_IP 'curl -fsSL https://get.docker.com | sh'
ssh $VM_IP 'systemctl enable --now docker'
```

**Problems with this:**
1. **No virt-customize**: Installing Docker post-boot is slow and error-prone
2. **Cloud-init timing**: Have to wait for first boot completion
3. **Network dependency**: Need VM network working to install Docker
4. **Error handling**: Need to implement VM cleanup on failure
5. **Storage hardcoded**: No flexibility for different Proxmox setups

### Complete Replication (What It Would Really Take)

To match the community script's robustness:

```bash
# 1. Install libguestfs-tools on Proxmox host
apt-get install libguestfs-tools

# 2. Download cloud image
wget https://cloud.debian.org/images/cloud/bookworm/latest/debian-12-nocloud-amd64.qcow2

# 3. Customize image with Docker (COMPLEX)
virt-customize -a debian-12.qcow2 \
  --install qemu-guest-agent,apt-transport-https,ca-certificates,curl,gnupg,software-properties-common \
  --run-command "mkdir -p /etc/apt/keyrings" \
  --run-command "curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg" \
  --run-command "echo 'deb [arch=amd64 signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian bookworm stable' > /etc/apt/sources.list.d/docker.list" \
  --run-command "apt-get update -qq && apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin" \
  --run-command "systemctl enable docker" \
  --hostname "$HOSTNAME"

# 4. Expand image to full size
qemu-img create -f qcow2 expanded.qcow2 ${DISK_SIZE}
virt-resize --expand /dev/sda1 debian-12.qcow2 expanded.qcow2
mv expanded.qcow2 debian-12.qcow2

# 5. Create VM with proper settings
qm create $VMID -agent 1 -tablet 0 -localtime 1 -bios ovmf \
  -cores $CORES -memory $RAM -name $HOSTNAME \
  -net0 virtio,bridge=$BRIDGE,macaddr=$MAC \
  -onboot 1 -ostype l26 -scsihw virtio-scsi-pci

# 6. Import and configure disks
pvesm alloc $STORAGE $VMID vm-$VMID-disk-0 4M
qm importdisk $VMID debian-12.qcow2 $STORAGE
qm set $VMID \
  -efidisk0 $STORAGE:vm-$VMID-disk-0,efitype=4m \
  -scsi0 $STORAGE:vm-$VMID-disk-1,size=${DISK_SIZE} \
  -boot order=scsi0 \
  -serial0 socket

# 7. Cleanup
rm debian-12.qcow2
```

**This is 50+ lines just for the core logic**, and we'd still need:
- Storage pool detection/selection
- VM ID conflict checking
- Error handling and cleanup
- Proxmox version compatibility checks
- Support for different storage types (NFS, ZFS, local-lvm, dir, btrfs)

## Automation Requirements Analysis

### How often will you create VMs?

**Your use case:** "I don't expect to be creating the VM on the proxmox server often"

Typical scenarios:
- **Initial setup**: Once (already done!)
- **Testing new configs**: 2-3 times per prototype iteration
- **Production rebuild**: Maybe quarterly?

**Total time cost per year**: ~30 minutes of interactive VM creation

### Would automation provide value?

**For CI/CD**: Yes, but you don't have CI/CD creating VMs currently
**For disaster recovery**: Moderate value - but manual is acceptable for rare events
**For development iteration**: Low value - infrequent operation
**For learning**: High value - but you learn more from community script

## Recommended Hybrid Approach

**Keep the community script interactive**, but streamline the wrapper:

### Option 1: Documentation-First (Recommended)
Update `scripts/proxmox-vm/create-vm.sh` to guide the user:

```bash
#!/usr/bin/env bash
# Create Docker VM on Proxmox using community script

# Source common utilities
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"
load_env_with_defaults
display_config
echo ""

log_step "Creating Docker VM using community script"
log_info "The community script is interactive and will prompt for settings."
log_info "Recommended settings based on your .env.proxmox:"
echo ""
echo "  VM ID:       $PROXMOX_VM_ID"
echo "  Hostname:    $PROXMOX_VM_HOSTNAME"
echo "  Cores:       $PROXMOX_VM_CORES"
echo "  Memory:      ${PROXMOX_VM_MEMORY}MB"
echo "  Disk Size:   ${PROXMOX_VM_DISK_SIZE}G"
echo "  Bridge:      $PROXMOX_VM_BRIDGE"
echo ""
log_info "Opening SSH session to Proxmox..."
log_info "Run this command when prompted:"
echo ""
echo "  bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/vm/docker-vm.sh)\""
echo ""
log_warning "After VM creation completes, run: task proxmox-vm:deploy"
echo ""

# Open SSH session for user
ssh -t "$PROXMOX_HOST"
```

**Benefits:**
- Minimal code to maintain
- Uses battle-tested community solution
- Clear guidance for user
- SSH session ready to go

### Option 2: Pre-Answered Prompts (If You Want More Automation)

Create an expect script that answers the prompts:

```bash
#!/usr/bin/expect -f
set timeout 300

# Read environment variables
set vmid $env(PROXMOX_VM_ID)
set hostname $env(PROXMOX_VM_HOSTNAME)
set cores $env(PROXMOX_VM_CORES)
set memory $env(PROXMOX_VM_MEMORY)
set disk_size $env(PROXMOX_VM_DISK_SIZE)

spawn ssh $env(PROXMOX_HOST)
expect "# "
send "bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/vm/docker-vm.sh)\"\r"

expect "Use Default Settings?"
send "\t\r"  # Select "Advanced"

expect "Virtual Machine ID"
send "$vmid\r"

# ... etc for each prompt ...
```

**Trade-offs:**
- Requires `expect` installed
- Fragile if community script UI changes
- More complex than pure documentation
- Still leverages community script's Docker magic

## Post-Creation Workflow

Regardless of how VM is created, the deployment flow is identical:

```bash
# 1. Create VM (community script - interactive OR qm commands - automated)
task proxmox-vm:create

# 2. Deploy application (fully automated)
task proxmox-vm:deploy

# 3. Manage lifecycle (fully automated)
task proxmox-vm:status
task proxmox-vm:logs
task proxmox-vm:restart
```

The **deployment** is the frequently-run operation, and that's already automated.

## Decision Framework

Choose **Community Script** if:
- ✅ You create VMs infrequently (< 10/year)
- ✅ You value battle-tested solutions
- ✅ You want Docker pre-installed
- ✅ You prefer minimal maintenance
- ✅ Interactive is acceptable

Choose **qm Commands** if:
- ✅ You need full CI/CD automation
- ✅ You create VMs frequently (> 50/year)
- ✅ You have complex custom requirements
- ✅ You're willing to maintain the code
- ✅ You need deterministic, non-interactive execution

## Recommendation for Zebu

**Use the community script with documentation wrapper.**

### Rationale:
1. **Infrequent operation**: VM creation is rare, interactive is fine
2. **Docker complexity**: Community script's virt-customize approach is superior
3. **Maintenance burden**: Let the community handle updates/fixes
4. **Learning value**: See how experts do it
5. **Deploy automation**: The frequently-run operations ARE automated

### Implementation:
1. Update `create-vm.sh` to be a documentation/helper script
2. Keep all other scripts (deploy, lifecycle, etc.) fully automated
3. Document the recommended settings in `.env.proxmox`
4. Maybe add expect script later if repetition becomes annoying

## Alternative: Packer (Future Enhancement)

If you later want full automation without reimplementing the script:

```hcl
# packer/proxmox-docker-vm.pkr.hcl
source "proxmox" "debian-docker" {
  proxmox_url = "https://proxmox:8006/api2/json"
  node        = "proxmox"

  iso_file    = "debian-12-generic-amd64.qcow2"

  # Use virt-customize via shell provisioner
  ssh_username = "root"
}

build {
  provisioner "shell" {
    inline = [
      "curl -fsSL https://get.docker.com | sh",
      "systemctl enable docker"
    ]
  }
}
```

**Benefits:**
- Declarative configuration
- Repeatable builds
- Version controlled
- Industry standard tool

**Downsides:**
- Another tool to learn
- More complex setup
- Overkill for rare operations

## Conclusion

**Stick with the community script.** The value it provides (virt-customize Docker pre-installation, storage selection, error handling) far outweighs the minor inconvenience of interactive prompts for an infrequent operation.

Update the wrapper script to be more of a "helpful guide" than an "automation attempt", and focus your automation efforts on the deployment and lifecycle scripts that you'll actually run frequently.
