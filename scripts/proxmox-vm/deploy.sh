#!/usr/bin/env bash
# Deploy PaperTrade application to Proxmox VM
# Handles code transfer, Docker build, and service deployment

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source common utilities
# shellcheck source=./common.sh
source "$SCRIPT_DIR/common.sh"

# Load environment variables with defaults
load_env_with_defaults

# Get repository root (two levels up from scripts/proxmox-vm)
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Main function
main() {
    log_step "Deploying PaperTrade to Proxmox VM"
    echo ""

    # Display configuration
    display_config
    echo ""

    # Check Proxmox connection
    if ! check_proxmox_connection; then
        error_exit "Cannot connect to Proxmox host"
    fi

    # Check if VM exists
    if ! vm_exists "$PROXMOX_VM_ID"; then
        error_exit "VM $PROXMOX_VM_ID does not exist. Create it first with: task proxmox-vm:create"
    fi

    # Check VM status
    local vm_status
    vm_status=$(get_vm_status "$PROXMOX_VM_ID")

    if [ "$vm_status" != "running" ]; then
        log_warning "VM is not running (status: $vm_status)"
        log_step "Starting VM..."

        ssh "$PROXMOX_HOST" "qm start $PROXMOX_VM_ID"
        sleep 10
    fi

    # Get VM IP
    log_step "Retrieving VM IP address..."
    local vm_ip
    vm_ip=$(get_vm_ip "$PROXMOX_VM_ID")

    if [ -z "$vm_ip" ]; then
        error_exit "Could not determine VM IP address"
    fi

    log_success "VM IP: $vm_ip"

    # Wait for VM SSH
    if ! wait_for_vm_ssh "$vm_ip"; then
        error_exit "VM is not accessible via SSH"
    fi

    # Prepare environment file
    log_step "Preparing environment configuration..."

    local env_file="$REPO_ROOT/.env"

    if [ ! -f "$env_file" ]; then
        log_warning "No .env file found at $env_file"
        log_info "Creating .env file from .env.production.example..."

        cp "$REPO_ROOT/.env.production.example" "$env_file"

        log_warning "Please edit $env_file with your production secrets"
        log_warning "Required secrets:"
        log_warning "  - POSTGRES_PASSWORD"
        log_warning "  - SECRET_KEY"
        log_warning "  - ALPHA_VANTAGE_API_KEY"

        error_exit "Environment file created but needs configuration. Please edit and re-run deployment."
    fi

    # Check for required secrets in .env file
    log_step "Validating environment configuration..."

    local missing_secrets=()

    for secret in POSTGRES_PASSWORD SECRET_KEY ALPHA_VANTAGE_API_KEY; do
        if ! grep -q "^${secret}=" "$env_file" || \
           grep "^${secret}=" "$env_file" | grep -q "CHANGE_ME\|your_api_key_here"; then
            missing_secrets+=("$secret")
        fi
    done

    if [ ${#missing_secrets[@]} -gt 0 ]; then
        log_error "Missing or unconfigured secrets in $env_file:"
        for secret in "${missing_secrets[@]}"; do
            log_error "  - $secret"
        done
        error_exit "Please configure required secrets in .env file"
    fi

    log_success "Environment configuration validated"

    # Deploy application code via git
    log_step "Deploying application code via git..."

    # Get current branch
    local current_branch
    current_branch=$(git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD)

    # Check if repository exists on VM
    if ssh "$VM_DEFAULT_USER@$vm_ip" "test -d $APP_DIR/.git"; then
        log_info "Repository exists - pulling latest changes..."

        # Pull latest changes
        ssh "$VM_DEFAULT_USER@$vm_ip" "cd $APP_DIR && git fetch origin && git checkout $current_branch && git pull origin $current_branch"

        # Show deployed version
        local deployed_version
        deployed_version=$(ssh "$VM_DEFAULT_USER@$vm_ip" "cd $APP_DIR && git describe --always --dirty")
        log_success "Deployed version: $deployed_version"
    else
        log_info "Cloning repository for first deployment..."

        # Clone repository
        ssh "$VM_DEFAULT_USER@$vm_ip" "git clone git@github.com:TimChild/PaperTrade.git $APP_DIR && cd $APP_DIR && git checkout $current_branch"

        log_success "Repository cloned"
    fi

    # Check if .env already exists on VM (preserve existing secrets)
    log_step "Configuring environment variables on VM..."

    if ssh "$VM_DEFAULT_USER@$vm_ip" "test -f $APP_DIR/.env"; then
        log_info "Existing .env file found on VM - preserving secrets"

        # Backup existing .env
        ssh "$VM_DEFAULT_USER@$vm_ip" "cp $APP_DIR/.env $APP_DIR/.env.backup"
        log_info "Existing .env backed up to .env.backup"
    else
        log_info "No existing .env file - transferring from local"

        # Transfer .env file to VM
        scp "$env_file" "$VM_DEFAULT_USER@$vm_ip:$APP_DIR/.env"
    fi

    log_success "Environment variables configured"

    # Build Docker images on VM
    log_step "Building Docker images on VM..."
    log_info "This may take 5-10 minutes on first build..."

    ssh "$VM_DEFAULT_USER@$vm_ip" "cd $APP_DIR && docker compose -f docker-compose.prod.yml build"

    log_success "Docker images built"

    # Deploy services
    log_step "Starting services..."

    ssh "$VM_DEFAULT_USER@$vm_ip" "cd $APP_DIR && docker compose -f docker-compose.prod.yml up -d"

    log_success "Services started"

    # Wait for services to be healthy
    log_step "Waiting for services to become healthy..."
    log_info "This may take 1-2 minutes..."

    if wait_for_services_healthy "$vm_ip" 60; then
        log_success "All services are healthy!"
    else
        log_warning "Some services may not be healthy yet"
        log_info "Check status with: task proxmox-vm:status"
        log_info "Check logs with: task proxmox-vm:logs"
    fi

    # Display deployment summary
    echo ""
    log_success "Deployment complete!"
    echo ""
    log_info "Access your application:"
    log_info "  Frontend: http://$vm_ip"
    log_info "  Backend API: http://$vm_ip:8000"
    log_info "  API Docs: http://$vm_ip:8000/docs"
    echo ""
    log_info "Useful commands:"
    log_info "  Check status: task proxmox-vm:status"
    log_info "  View logs: task proxmox-vm:logs"
    log_info "  Restart: task proxmox-vm:restart"
}

# Run main function
main "$@"
