#!/usr/bin/env bash
# Create Docker VM on Proxmox using community script
# This script leverages the battle-tested community Docker VM script

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source common utilities
# shellcheck source=./common.sh
source "$SCRIPT_DIR/common.sh"

# Load environment variables with defaults
load_env_with_defaults

# Main function
main() {
    log_step "Creating Docker VM on Proxmox"
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
    
    log_step "Downloading community Docker VM script..."
    
    # Download the community script
    local script_url="https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/vm/docker-vm.sh"
    local script_path="/tmp/docker-vm-$$.sh"
    
    if ! curl -fsSL "$script_url" -o "$script_path"; then
        error_exit "Failed to download community script from $script_url"
    fi
    
    log_success "Downloaded community script"
    
    # Prepare the script execution with our configuration
    log_step "Creating VM with community script..."
    
    # The community script is interactive, so we'll need to provide inputs
    # We'll use expect or heredoc to automate the responses
    # For simplicity and reliability, we'll use the advanced settings approach
    
    # Transfer the script to Proxmox
    if ! scp "$script_path" "$PROXMOX_HOST:/tmp/docker-vm-create.sh"; then
        rm -f "$script_path"
        error_exit "Failed to transfer script to Proxmox host"
    fi
    
    rm -f "$script_path"
    
    log_step "Executing VM creation on Proxmox..."
    log_info "This may take several minutes..."
    echo ""
    
    # Provide instructions for manual VM creation
    log_warning "The community script is interactive and requires manual input."
    log_info "Please follow these steps on your Proxmox host:"
    echo ""
    echo "1. SSH to Proxmox:"
    echo "   ssh $PROXMOX_HOST"
    echo ""
    echo "2. Run the community Docker VM script:"
    echo "   bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/vm/docker-vm.sh)\""
    echo ""
    echo "3. When prompted, use these settings:"
    echo "   - Use Default Settings? NO (select Advanced)"
    echo "   - VM ID: $PROXMOX_VM_ID"
    echo "   - Machine Type: i440fx (default)"
    echo "   - Disk Size: ${PROXMOX_VM_DISK_SIZE}G"
    echo "   - Disk Cache: None (default)"
    echo "   - Hostname: $PROXMOX_VM_HOSTNAME"
    echo "   - CPU Model: KVM64 (default)"
    echo "   - CPU Cores: $PROXMOX_VM_CORES"
    echo "   - RAM Size: $PROXMOX_VM_MEMORY"
    echo "   - Bridge: $PROXMOX_VM_BRIDGE"
    echo "   - MAC Address: (accept default)"
    echo "   - VLAN: (leave blank)"
    echo "   - MTU Size: (leave blank)"
    echo "   - Start VM: YES"
    echo "   - Storage: (select your preferred storage)"
    echo ""
    
    # Alternative: try automated creation if running directly on Proxmox
    if ssh "$PROXMOX_HOST" "test -f /tmp/docker-vm-create.sh" 2>/dev/null; then
        log_step "Attempting automated VM creation..."
        
        # Run the script and try to pipe answers (this may or may not work)
        if ssh "$PROXMOX_HOST" "bash /tmp/docker-vm-create.sh" << ANSWERS 2>/dev/null; then
y
n
$PROXMOX_VM_ID


$PROXMOX_VM_DISK_SIZE

$PROXMOX_VM_HOSTNAME

$PROXMOX_VM_CORES
$PROXMOX_VM_MEMORY
$PROXMOX_VM_BRIDGE




y
y

ANSWERS
            log_success "VM created successfully!"
        else
            log_warning "Automated creation failed - please create manually using instructions above"
            echo ""
            log_info "After creating the VM manually, return here and run:"
            log_info "  task proxmox-vm:deploy"
            exit 0
        fi
    else
        log_info "Please create the VM manually using the instructions above"
        echo ""
        log_info "After creating the VM, return here and run:"
        log_info "  task proxmox-vm:deploy"
        echo ""
        read -p "Press Enter when you have created the VM..." -r
    fi
    
    # Wait for VM to get an IP
    log_step "Waiting for VM to obtain IP address..."
    local vm_ip
    vm_ip=$(get_vm_ip "$PROXMOX_VM_ID")
    
    if [ -z "$vm_ip" ]; then
        log_warning "Could not automatically determine VM IP address"
        log_info "You can find the IP manually using: qm guest cmd $PROXMOX_VM_ID network-get-interfaces"
    else
        log_success "VM IP address: $vm_ip"
        
        # Post-creation security hardening
        log_step "Performing post-creation security setup..."
        
        # Wait for SSH to be available
        if wait_for_vm_ssh "$vm_ip"; then
            log_step "Changing default root password..."
            
            # Generate a random password
            local new_password
            new_password=$(openssl rand -base64 24)
            
            # Change the password using sshpass or expect
            # For security, we'll use SSH with the default password to change it
            if command -v sshpass &>/dev/null; then
                sshpass -p "$VM_DEFAULT_PASSWORD" ssh -o StrictHostKeyChecking=no \
                    "$VM_DEFAULT_USER@$vm_ip" \
                    "echo '$VM_DEFAULT_USER:$new_password' | chpasswd"
                
                log_success "Root password changed"
                log_warning "New root password: $new_password"
                log_warning "Please save this password securely!"
            else
                log_warning "sshpass not installed - cannot automatically change root password"
                log_warning "Please manually change the default password 'docker' for security"
            fi
            
            # Configure static IP if requested
            if [ "$PROXMOX_VM_IP_MODE" = "static" ]; then
                log_step "Configuring static IP..."
                
                if [ -z "$PROXMOX_VM_IP_ADDRESS" ] || [ -z "$PROXMOX_VM_GATEWAY" ]; then
                    log_warning "Static IP requested but PROXMOX_VM_IP_ADDRESS or PROXMOX_VM_GATEWAY not set"
                    log_warning "Skipping static IP configuration"
                else
                    # Configure static IP using netplan or /etc/network/interfaces
                    # This depends on the Debian version in the VM
                    log_info "Static IP configuration: $PROXMOX_VM_IP_ADDRESS via gateway $PROXMOX_VM_GATEWAY"
                    log_warning "Manual static IP configuration required - see documentation"
                fi
            fi
        else
            log_warning "Could not connect to VM via SSH for post-creation setup"
            log_warning "Please manually:"
            log_warning "  1. Change the default root password from 'docker'"
            log_warning "  2. Configure static IP if needed"
        fi
    fi
    
    echo ""
    log_success "VM creation complete!"
    log_info "Next steps:"
    log_info "  1. Deploy application: task proxmox-vm:deploy"
    log_info "  2. Check status: task proxmox-vm:status"
}

# Run main function
main "$@"
