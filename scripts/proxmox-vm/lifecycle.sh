#!/usr/bin/env bash
# Lifecycle management for Zebu services on Proxmox VM
# Handles start, stop, restart, status, and logs

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source common utilities
# shellcheck source=./common.sh
source "$SCRIPT_DIR/common.sh"

# Load environment variables with defaults
load_env_with_defaults

# Show usage
usage() {
    echo "Usage: $0 {start|stop|restart|status|logs}"
    echo ""
    echo "Commands:"
    echo "  start    - Start all services"
    echo "  stop     - Stop all services"
    echo "  restart  - Restart all services"
    echo "  status   - Show status of all services"
    echo "  logs     - Show logs from all services (follow mode)"
    exit 1
}

# Get VM connection info
get_vm_connection() {
    # Check if VM exists
    if ! vm_exists "$PROXMOX_VM_ID"; then
        error_exit "VM $PROXMOX_VM_ID does not exist"
    fi

    # Get VM IP
    local vm_ip
    vm_ip=$(get_vm_ip "$PROXMOX_VM_ID" 10)

    if [ -z "$vm_ip" ]; then
        error_exit "Could not determine VM IP address"
    fi

    echo "$vm_ip"
}

# Start services
cmd_start() {
    log_step "Starting PaperTrade services..."

    local vm_ip
    vm_ip=$(get_vm_connection)

    ssh "$VM_DEFAULT_USER@$vm_ip" "cd $APP_DIR && docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d"

    log_success "Services started"
    log_info "Check status with: task proxmox-vm:status"
}

# Stop services
cmd_stop() {
    log_step "Stopping PaperTrade services..."

    local vm_ip
    vm_ip=$(get_vm_connection)

    ssh "$VM_DEFAULT_USER@$vm_ip" "cd $APP_DIR && docker compose -f docker-compose.yml -f docker-compose.prod.yml down"

    log_success "Services stopped"
}

# Restart services
cmd_restart() {
    log_step "Restarting PaperTrade services..."

    local vm_ip
    vm_ip=$(get_vm_connection)

    ssh "$VM_DEFAULT_USER@$vm_ip" "cd $APP_DIR && docker compose -f docker-compose.yml -f docker-compose.prod.yml restart"

    log_success "Services restarted"
    log_info "Check status with: task proxmox-vm:status"
}

# Show status
cmd_status() {
    log_step "Checking PaperTrade deployment status..."
    echo ""

    # Check Proxmox connection
    if ! check_proxmox_connection; then
        error_exit "Cannot connect to Proxmox host"
    fi

    # Check if VM exists
    if ! vm_exists "$PROXMOX_VM_ID"; then
        log_error "VM $PROXMOX_VM_ID does not exist"
        log_info "Create VM with: task proxmox-vm:create"
        exit 1
    fi

    # Get VM status
    local vm_status
    vm_status=$(get_vm_status "$PROXMOX_VM_ID")

    echo "VM Status:"
    echo "  ID:        $PROXMOX_VM_ID"
    echo "  Hostname:  $PROXMOX_VM_HOSTNAME"
    echo "  Status:    $vm_status"

    if [ "$vm_status" != "running" ]; then
        echo ""
        log_warning "VM is not running"
        log_info "Start VM with: ssh $PROXMOX_HOST qm start $PROXMOX_VM_ID"
        exit 0
    fi

    # Get VM IP
    local vm_ip
    vm_ip=$(get_vm_ip "$PROXMOX_VM_ID" 10)

    if [ -z "$vm_ip" ]; then
        echo "  IP:        (not available)"
        echo ""
        log_warning "Could not determine VM IP address"
        exit 0
    fi

    echo "  IP:        $vm_ip"
    echo ""

    # Check if we can connect via SSH
    if ! ssh -o ConnectTimeout=2 -o BatchMode=yes -o StrictHostKeyChecking=no \
         "$VM_DEFAULT_USER@$vm_ip" "exit" 2>/dev/null; then
        log_warning "Cannot connect to VM via SSH"
        exit 0
    fi

    # Check if Docker is installed
    if ! ssh "$VM_DEFAULT_USER@$vm_ip" "command -v docker &>/dev/null"; then
        log_warning "Docker is not installed on VM"
        exit 0
    fi

    # Check if application is deployed
    if ! ssh "$VM_DEFAULT_USER@$vm_ip" "test -d $APP_DIR"; then
        log_warning "Application is not deployed to VM"
        log_info "Deploy application with: task proxmox-vm:deploy"
        exit 0
    fi

    # Show deployed version (git info)
    echo "Deployed Version:"
    if ssh "$VM_DEFAULT_USER@$vm_ip" "test -d $APP_DIR/.git"; then
        local deployed_version deployed_branch
        deployed_version=$(ssh "$VM_DEFAULT_USER@$vm_ip" "cd $APP_DIR && git describe --always --dirty" 2>/dev/null || echo "unknown")
        deployed_branch=$(ssh "$VM_DEFAULT_USER@$vm_ip" "cd $APP_DIR && git rev-parse --abbrev-ref HEAD" 2>/dev/null || echo "unknown")
        echo "  Branch:    $deployed_branch"
        echo "  Commit:    $deployed_version"
    else
        echo "  (Not a git repository)"
    fi
    echo ""

    # Show Docker services status
    echo "Docker Services:"
    ssh "$VM_DEFAULT_USER@$vm_ip" "cd $APP_DIR && docker compose -f docker-compose.yml -f docker-compose.prod.yml ps"
    echo ""

    # Check service health
    echo "Service Health:"

    # Check PostgreSQL
    if ssh "$VM_DEFAULT_USER@$vm_ip" "docker exec papertrade-postgres-prod pg_isready -U papertrade &>/dev/null"; then
        echo "  PostgreSQL:  ✓ Healthy"
    else
        echo "  PostgreSQL:  ✗ Unhealthy"
    fi

    # Check Redis
    if ssh "$VM_DEFAULT_USER@$vm_ip" "docker exec papertrade-redis-prod redis-cli ping &>/dev/null"; then
        echo "  Redis:       ✓ Healthy"
    else
        echo "  Redis:       ✗ Unhealthy"
    fi

    # Check Backend
    if ssh "$VM_DEFAULT_USER@$vm_ip" "curl -f -s http://localhost:8000/health &>/dev/null"; then
        echo "  Backend:     ✓ Healthy"
    else
        echo "  Backend:     ✗ Unhealthy"
    fi

    # Check Frontend
    if ssh "$VM_DEFAULT_USER@$vm_ip" "curl -f -s http://localhost:80/ &>/dev/null"; then
        echo "  Frontend:    ✓ Healthy"
    else
        echo "  Frontend:    ✗ Unhealthy"
    fi

    echo ""
    echo "Access URLs:"
    echo "  Frontend:    http://$vm_ip"
    echo "  Backend API: http://$vm_ip:8000"
    echo "  API Docs:    http://$vm_ip:8000/docs"
}

# Show logs
cmd_logs() {
    log_step "Showing service logs (press Ctrl+C to exit)..."
    echo ""

    local vm_ip
    vm_ip=$(get_vm_connection)

    # Follow logs from all services
    ssh "$VM_DEFAULT_USER@$vm_ip" "cd $APP_DIR && docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f"
}

# Main function
main() {
    local command="${1:-}"

    if [ -z "$command" ]; then
        usage
    fi

    # Check Proxmox connection (except for status which does its own checks)
    if [ "$command" != "status" ]; then
        if ! check_proxmox_connection; then
            error_exit "Cannot connect to Proxmox host"
        fi
    fi

    case "$command" in
        start)
            cmd_start
            ;;
        stop)
            cmd_stop
            ;;
        restart)
            cmd_restart
            ;;
        status)
            cmd_status
            ;;
        logs)
            cmd_logs
            ;;
        *)
            log_error "Unknown command: $command"
            usage
            ;;
    esac
}

# Run main function
main "$@"
