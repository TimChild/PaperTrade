#!/usr/bin/env bash
# Destroy Proxmox VM
# WARNING: This is a destructive operation that will delete the VM and all its data

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source common utilities
# shellcheck source=./common.sh
source "$SCRIPT_DIR/common.sh"

# Load environment variables with defaults
load_env_with_defaults

# Main function
main() {
    local force="${1:-false}"
    
    log_step "Destroy Proxmox VM"
    echo ""
    
    # Display configuration
    echo "VM Configuration:"
    echo "  Proxmox Host: $PROXMOX_HOST"
    echo "  VM ID:        $PROXMOX_VM_ID"
    echo "  VM Hostname:  $PROXMOX_VM_HOSTNAME"
    echo ""
    
    # Check Proxmox connection
    if ! check_proxmox_connection; then
        error_exit "Cannot connect to Proxmox host"
    fi
    
    # Check if VM exists
    if ! vm_exists "$PROXMOX_VM_ID"; then
        log_warning "VM $PROXMOX_VM_ID does not exist"
        exit 0
    fi
    
    # Get VM status
    local vm_status
    vm_status=$(get_vm_status "$PROXMOX_VM_ID")
    
    echo "Current VM Status: $vm_status"
    echo ""
    
    # Confirm destructive action
    log_warning "This will permanently delete VM $PROXMOX_VM_ID and all its data!"
    log_warning "This action cannot be undone."
    echo ""
    
    if ! confirm_action "Are you sure you want to destroy this VM?" "$force"; then
        exit 0
    fi
    
    echo ""
    
    # Stop VM if running
    if [ "$vm_status" = "running" ]; then
        log_step "Stopping VM..."
        ssh "$PROXMOX_HOST" "qm stop $PROXMOX_VM_ID"
        
        # Wait for VM to stop
        local attempts=0
        while [ $attempts -lt 30 ]; do
            vm_status=$(get_vm_status "$PROXMOX_VM_ID")
            if [ "$vm_status" = "stopped" ]; then
                break
            fi
            sleep 1
            attempts=$((attempts + 1))
        done
        
        if [ "$vm_status" != "stopped" ]; then
            log_warning "VM did not stop gracefully, forcing shutdown..."
            ssh "$PROXMOX_HOST" "qm stop $PROXMOX_VM_ID --skiplock"
            sleep 2
        fi
        
        log_success "VM stopped"
    fi
    
    # Destroy VM
    log_step "Destroying VM..."
    
    if ssh "$PROXMOX_HOST" "qm destroy $PROXMOX_VM_ID --purge"; then
        log_success "VM $PROXMOX_VM_ID destroyed successfully"
    else
        error_exit "Failed to destroy VM"
    fi
    
    echo ""
    log_info "VM has been completely removed from Proxmox"
    log_info "To create a new VM, run: task proxmox-vm:create"
}

# Run main function
main "$@"
