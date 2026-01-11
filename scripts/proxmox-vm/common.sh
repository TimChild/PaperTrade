#!/usr/bin/env bash
# Common utilities for Proxmox VM deployment scripts
# Provides error handling, colored output, and shared functions

# Strict error handling
set -euo pipefail

# Color codes for output
readonly COLOR_RESET='\033[0m'
readonly COLOR_RED='\033[0;31m'
readonly COLOR_GREEN='\033[0;32m'
readonly COLOR_YELLOW='\033[1;33m'
readonly COLOR_BLUE='\033[0;34m'
readonly COLOR_CYAN='\033[0;36m'
readonly COLOR_BOLD='\033[1m'

# Output functions with colored formatting
log_info() {
    echo -e "${COLOR_BLUE}ℹ${COLOR_RESET} $*"
}

log_success() {
    echo -e "${COLOR_GREEN}✓${COLOR_RESET} $*"
}

log_warning() {
    echo -e "${COLOR_YELLOW}⚠${COLOR_RESET} $*"
}

log_error() {
    echo -e "${COLOR_RED}✗${COLOR_RESET} $*" >&2
}

log_step() {
    echo -e "${COLOR_CYAN}→${COLOR_RESET} ${COLOR_BOLD}$*${COLOR_RESET}"
}

# Error handler
error_exit() {
    log_error "$1"
    exit "${2:-1}"
}

# Load environment variables with defaults
load_env_with_defaults() {
    # Proxmox Connection
    export PROXMOX_HOST="${PROXMOX_HOST:-root@proxmox}"

    # VM Configuration
    export PROXMOX_VM_ID="${PROXMOX_VM_ID:-200}"
    export PROXMOX_VM_HOSTNAME="${PROXMOX_VM_HOSTNAME:-papertrade}"
    export PROXMOX_VM_CORES="${PROXMOX_VM_CORES:-4}"
    export PROXMOX_VM_MEMORY="${PROXMOX_VM_MEMORY:-8192}"  # MB
    export PROXMOX_VM_DISK_SIZE="${PROXMOX_VM_DISK_SIZE:-50}"  # GB

    # Network Configuration
    export PROXMOX_VM_BRIDGE="${PROXMOX_VM_BRIDGE:-vmbr0}"
    export PROXMOX_VM_IP_MODE="${PROXMOX_VM_IP_MODE:-dhcp}"
    export PROXMOX_VM_IP_ADDRESS="${PROXMOX_VM_IP_ADDRESS:-}"
    export PROXMOX_VM_GATEWAY="${PROXMOX_VM_GATEWAY:-}"

    # Application Configuration
    export APP_DIR="${APP_DIR:-/opt/papertrade}"

    # VM Default Credentials (from community script)
    export VM_DEFAULT_USER="${VM_DEFAULT_USER:-root}"
    export VM_DEFAULT_PASSWORD="${VM_DEFAULT_PASSWORD:-docker}"
}

# Validate required environment variables
validate_env() {
    local required_vars=("$@")
    local missing_vars=()

    for var in "${required_vars[@]}"; do
        if [ -z "${!var:-}" ]; then
            missing_vars+=("$var")
        fi
    done

    if [ ${#missing_vars[@]} -gt 0 ]; then
        log_error "Missing required environment variables:"
        for var in "${missing_vars[@]}"; do
            log_error "  - $var"
        done
        return 1
    fi

    return 0
}

# Check if SSH connection to Proxmox is available
check_proxmox_connection() {
    log_step "Checking connection to Proxmox host: $PROXMOX_HOST"

    if ! ssh -o ConnectTimeout=5 -o BatchMode=yes "$PROXMOX_HOST" "exit" 2>/dev/null; then
        log_error "Cannot connect to Proxmox host: $PROXMOX_HOST"
        log_error "Please ensure:"
        log_error "  - SSH access is configured"
        log_error "  - SSH keys are set up (recommended)"
        log_error "  - The host is reachable"
        return 1
    fi

    log_success "Connected to Proxmox host"
    return 0
}

# Check if VM exists
vm_exists() {
    local vm_id="$1"
    ssh "$PROXMOX_HOST" "qm status $vm_id" &>/dev/null
}

# Get VM status
get_vm_status() {
    local vm_id="$1"
    ssh "$PROXMOX_HOST" "qm status $vm_id 2>/dev/null | awk '{print \$2}'" || echo "not_found"
}

# Wait for VM to be accessible via SSH
wait_for_vm_ssh() {
    local vm_ip="$1"
    local max_attempts="${2:-60}"
    local attempt=1

    log_step "Waiting for VM to be accessible via SSH at $vm_ip..."

    while [ $attempt -le $max_attempts ]; do
        if ssh -o ConnectTimeout=2 -o BatchMode=yes -o StrictHostKeyChecking=no \
           "$VM_DEFAULT_USER@$vm_ip" "exit" 2>/dev/null; then
            log_success "VM is accessible via SSH"
            return 0
        fi

        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done

    echo ""
    log_error "VM did not become accessible within timeout"
    return 1
}

# Get VM IP address
get_vm_ip() {
    local vm_id="$1"
    local max_attempts="${2:-30}"
    local attempt=1

    log_step "Retrieving VM IP address..." >&2

    while [ $attempt -le $max_attempts ]; do
        local vm_ip
        # Use sed instead of grep -P for macOS compatibility
        vm_ip=$(ssh "$PROXMOX_HOST" "qm guest cmd $vm_id network-get-interfaces 2>/dev/null" | \
                sed -n 's/.*"ip-address"[[:space:]]*:[[:space:]]*"\([0-9.]*\)".*/\1/p' | \
                grep -v "127.0.0.1" | \
                head -1)

        if [ -n "$vm_ip" ]; then
            echo "$vm_ip"
            return 0
        fi

        echo -n "." >&2
        sleep 2
        attempt=$((attempt + 1))
    done

    echo "" >&2
    log_error "Could not retrieve VM IP address" >&2
    return 1
}

# Check if a service is healthy in VM
check_service_health() {
    local vm_ip="$1"
    local service_name="$2"
    local health_url="$3"

    log_step "Checking $service_name health..."

    if ssh "$VM_DEFAULT_USER@$vm_ip" "curl -f -s $health_url > /dev/null 2>&1"; then
        log_success "$service_name is healthy"
        return 0
    else
        log_warning "$service_name is not healthy yet"
        return 1
    fi
}

# Wait for all services to be healthy
wait_for_services_healthy() {
    local vm_ip="$1"
    local max_attempts="${2:-60}"
    local attempt=1

    log_step "Waiting for all services to become healthy..."

    local services=(
        "PostgreSQL:http://localhost:8000/health"
        "Backend:http://localhost:8000/health"
        "Frontend:http://localhost:80/health"
    )

    while [ $attempt -le $max_attempts ]; do
        local all_healthy=true

        for service in "${services[@]}"; do
            local service_name="${service%%:*}"
            local health_url="${service##*:}"

            if ! ssh "$VM_DEFAULT_USER@$vm_ip" "curl -f -s $health_url > /dev/null 2>&1"; then
                all_healthy=false
                break
            fi
        done

        if [ "$all_healthy" = true ]; then
            log_success "All services are healthy!"
            return 0
        fi

        echo -n "."
        sleep 5
        attempt=$((attempt + 1))
    done

    echo ""
    log_error "Services did not become healthy within timeout"
    return 1
}

# Confirm destructive action
confirm_action() {
    local prompt="$1"
    local force="${2:-false}"

    if [ "$force" = true ]; then
        return 0
    fi

    echo -e "${COLOR_YELLOW}${prompt}${COLOR_RESET}"
    read -r -p "Type 'yes' to confirm: " response

    if [ "$response" = "yes" ]; then
        return 0
    else
        log_info "Action cancelled"
        return 1
    fi
}

# Display configuration
display_config() {
    log_step "Current Configuration:"
    echo "  Proxmox Host:      $PROXMOX_HOST"
    echo "  VM ID:             $PROXMOX_VM_ID"
    echo "  VM Hostname:       $PROXMOX_VM_HOSTNAME"
    echo "  VM Cores:          $PROXMOX_VM_CORES"
    echo "  VM Memory:         ${PROXMOX_VM_MEMORY}MB"
    echo "  VM Disk Size:      ${PROXMOX_VM_DISK_SIZE}GB"
    echo "  Network Bridge:    $PROXMOX_VM_BRIDGE"
    echo "  IP Mode:           $PROXMOX_VM_IP_MODE"
    if [ "$PROXMOX_VM_IP_MODE" = "static" ]; then
        echo "  Static IP:         $PROXMOX_VM_IP_ADDRESS"
        echo "  Gateway:           $PROXMOX_VM_GATEWAY"
    fi
    echo "  App Directory:     $APP_DIR"
}
