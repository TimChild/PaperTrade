#!/usr/bin/env bash
# Guide for creating Docker VM on Proxmox using community script
#
# This script helps you use the battle-tested community Docker VM script
# which uses virt-customize to pre-install Docker before first boot.
#
# See docs/deployment/proxmox-vm-approach-comparison.md for rationale.

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source common utilities
# shellcheck source=./common.sh
source "$SCRIPT_DIR/common.sh"

# Load environment variables with defaults
load_env_with_defaults

# Main function
main() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║     Proxmox Docker VM Creation Guide                          ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    echo ""

    # Display configuration
    display_config
    echo ""

    # Check Proxmox connection
    if ! check_proxmox_connection; then
        error_exit "Cannot connect to Proxmox host"
    fi

    # Check if VM already exists
    if vm_exists "$PROXMOX_VM_ID"; then
        error_exit "VM $PROXMOX_VM_ID already exists. Use 'task proxmox-vm:destroy' to remove it first."
    fi

    log_step "VM will be created using the community Docker VM script"
    echo ""
    echo "The script will:"
    echo "  ✓ Download Debian 12 cloud image"
    echo "  ✓ Use virt-customize to pre-install Docker BEFORE first boot"
    echo "  ✓ Configure VM with qemu-guest-agent"
    echo "  ✓ Set up cloud-init for SSH and networking"
    echo ""

    log_step "Recommended settings for interactive prompts:"
    echo ""
    echo "  Use Default Settings:  NO (select Advanced)"
    echo "  VM ID:                 $PROXMOX_VM_ID"
    echo "  Machine Type:          i440fx (default)"
    echo "  Disk Size:             ${PROXMOX_VM_DISK_SIZE:-50}G"
    echo "  Disk Cache:            None (default)"
    echo "  Hostname:              $PROXMOX_VM_HOSTNAME"
    echo "  CPU Model:             KVM64 (default)"
    echo "  CPU Cores:             ${PROXMOX_VM_CORES:-4}"
    echo "  RAM:                   ${PROXMOX_VM_MEMORY:-8192} MB"
    echo "  Bridge:                ${PROXMOX_VM_BRIDGE:-vmbr0}"
    echo "  MAC Address:           (accept auto-generated default)"
    echo "  VLAN:                  Default (leave blank)"
    echo "  Interface MTU:         Default (leave blank)"
    echo "  Start VM:              YES"
    echo "  Storage:               Choose from available (e.g., local-lvm)"
    if [ "${PROXMOX_VM_IP:-}" != "" ]; then
        echo ""
        echo "  Optional static IP:    $PROXMOX_VM_IP/${PROXMOX_VM_CIDR:-24}"
        echo "  Gateway:               ${PROXMOX_VM_GATEWAY:-192.168.4.1}"
    fi
    echo ""
    log_warning "IMPORTANT: Do not interrupt the virt-resize step (expanding disk) - it takes 1-2 minutes"
    echo ""
    log_step "SSH to Proxmox and run the community script:"
    echo ""
    echo "  ssh $PROXMOX_HOST"
    echo ""
    echo "  bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/vm/docker-vm.sh)\""
    echo ""
    echo ""

    log_step "Press Enter when ready to run the script..."
    read -r -p ""

    # Open SSH connection in a way that allows interaction
    log_step "Opening interactive SSH session to Proxmox..."
    echo ""
    echo "The community script will now run interactively."
    echo "After it completes, the script will verify the VM was created."
    echo ""

    # Run the community script interactively via SSH
    ssh -t "$PROXMOX_HOST" "bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/vm/docker-vm.sh)\""

    local ssh_exit_code=$?
    echo ""

    if [ $ssh_exit_code -ne 0 ]; then
        log_warning "SSH session exited with code $ssh_exit_code"
        log_info "If you chose not to create the VM, you can run this script again later."
        exit $ssh_exit_code
    fi

    # Verify VM was created
    log_step "Verifying VM creation..."

    if ! vm_exists "$PROXMOX_VM_ID"; then
        log_warning "VM $PROXMOX_VM_ID was not found"
        log_info "If you used a different VM ID, update .env.proxmox and try again."
        exit 1
    fi

    log_success "VM $PROXMOX_VM_ID created successfully!"


    log_success "VM $PROXMOX_VM_ID created successfully!"
    echo ""

    # Wait for VM to get an IP
    log_step "Waiting for VM to obtain IP address..."
    local vm_ip
    vm_ip=$(get_vm_ip "$PROXMOX_VM_ID")

    if [ -z "$vm_ip" ]; then
        log_warning "Could not automatically determine VM IP address"
        echo ""
        echo "You can find the IP using:"
        echo "  ssh $PROXMOX_HOST \"qm guest cmd $PROXMOX_VM_ID network-get-interfaces\""
        echo ""
        log_info "Once you have the IP, update .env.proxmox if using static IP mode"
    else
        log_success "VM IP address: $vm_ip"

        if [ "${PROXMOX_VM_IP:-}" != "" ] && [ "$PROXMOX_VM_IP" != "$vm_ip" ]; then
            log_warning "Expected IP: $PROXMOX_VM_IP, Got: $vm_ip"
            log_info "Update .env.proxmox with the actual IP if needed"
        fi
    fi

    # Configure SSH access automatically
    log_step "Configuring SSH access..."
    echo ""

    # Check if SSH is installed (community script may not include it)
    log_info "Checking SSH installation..."
    local ssh_installed
    ssh_installed=$(ssh "$PROXMOX_HOST" "qm guest exec $PROXMOX_VM_ID -- bash -c 'dpkg -l openssh-server 2>/dev/null | grep -q ^ii && echo yes || echo no'" 2>/dev/null | grep -o 'yes\|no')

    if [ "$ssh_installed" != "yes" ]; then
        log_info "Installing OpenSSH server on VM..."
        ssh "$PROXMOX_HOST" "qm guest exec $PROXMOX_VM_ID -- bash -c 'DEBIAN_FRONTEND=noninteractive apt-get update -qq && apt-get install -y -qq openssh-server >/dev/null 2>&1'" >/dev/null 2>&1
        log_success "OpenSSH server installed"
    else
        log_info "OpenSSH server already installed"
    fi

    # Set root password to 'docker' (community script default)
    log_info "Setting root password..."
    ssh "$PROXMOX_HOST" "qm guest exec $PROXMOX_VM_ID -- bash -c 'echo \"root:docker\" | chpasswd'" >/dev/null 2>&1
    log_success "Root password set to 'docker'"

    # Copy local SSH public key to VM
    local ssh_key_path="${SSH_KEY_PATH:-$HOME/.ssh/id_ed25519.pub}"
    if [ ! -f "$ssh_key_path" ]; then
        ssh_key_path="$HOME/.ssh/id_rsa.pub"
    fi

    if [ -f "$ssh_key_path" ]; then
        log_info "Copying SSH public key to VM..."
        local ssh_pub_key
        ssh_pub_key=$(cat "$ssh_key_path")

        ssh "$PROXMOX_HOST" "qm guest exec $PROXMOX_VM_ID -- bash -c 'mkdir -p /root/.ssh && chmod 700 /root/.ssh && echo \"$ssh_pub_key\" > /root/.ssh/authorized_keys && chmod 600 /root/.ssh/authorized_keys'" >/dev/null 2>&1

        log_success "SSH key authentication configured"

        # Test SSH connection
        if [ -n "$vm_ip" ]; then
            log_info "Testing SSH connection..."
            sleep 2  # Give SSH service a moment to be ready

            if ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no -o BatchMode=yes "root@$vm_ip" "echo 'SSH OK'" >/dev/null 2>&1; then
                log_success "SSH connection verified!"
            else
                log_warning "Could not verify SSH connection (may need more time to initialize)"
                log_info "You can test manually with: ssh root@$vm_ip"
            fi
        fi
    else
        log_warning "No SSH public key found at $HOME/.ssh/id_ed25519.pub or $HOME/.ssh/id_rsa.pub"
        log_info "SSH password authentication is enabled (password: docker)"
        log_info "Consider generating an SSH key with: ssh-keygen -t ed25519"
    fi

    echo ""

    echo ""
    log_success "VM creation complete!"
    echo ""
    log_step "Next steps:"
    echo "  1. Verify Docker is installed and running:"
    echo "     ssh root@$vm_ip 'docker --version && docker ps'"
    echo ""
    echo "  2. Deploy Zebu application:"
    echo "     task proxmox-vm:deploy"
    echo ""
    echo "  3. Check deployment status:"
    echo "     task proxmox-vm:status"
    echo ""
}

# Run main function
main "$@"
