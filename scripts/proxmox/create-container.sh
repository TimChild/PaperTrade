#!/usr/bin/env bash
set -euo pipefail

# PaperTrade Proxmox Container Creation Script
# Creates a PRIVILEGED LXC container for Docker support

PROXMOX_HOST="${PROXMOX_HOST:-root@proxmox}"
CONTAINER_ID="${PROXMOX_CONTAINER_ID:-107}"
CONTAINER_HOSTNAME="${PROXMOX_CONTAINER_HOSTNAME:-papertrade}"
CONTAINER_MEMORY="${PROXMOX_CONTAINER_MEMORY:-4096}"
CONTAINER_CORES="${PROXMOX_CONTAINER_CORES:-2}"
CONTAINER_DISK="${PROXMOX_CONTAINER_DISK:-20}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $*"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*"
}

# Check if container already exists
check_existing() {
    log_info "Checking if container ${CONTAINER_ID} already exists..."
    
    if ssh "${PROXMOX_HOST}" "pct status ${CONTAINER_ID}" &>/dev/null; then
        log_error "Container ${CONTAINER_ID} already exists!"
        log_error "To use this container, set PROXMOX_CONTAINER_ID=${CONTAINER_ID} and run deploy"
        log_error "To create a new container, set a different PROXMOX_CONTAINER_ID"
        exit 1
    fi
    
    log_info "Container ID ${CONTAINER_ID} is available"
}

# Download template if needed
download_template() {
    log_info "Checking for Ubuntu 24.04 template..."
    
    if ! ssh "${PROXMOX_HOST}" "ls /var/lib/vz/template/cache/ubuntu-24.04-standard_24.04-2_amd64.tar.zst" &>/dev/null; then
        log_info "Downloading Ubuntu 24.04 template..."
        ssh "${PROXMOX_HOST}" "pveam download local ubuntu-24.04-standard_24.04-2_amd64.tar.zst"
    else
        log_info "Template already exists"
    fi
}

# Create container
create_container() {
    log_info "Creating privileged LXC container ${CONTAINER_ID}..."
    
    ssh "${PROXMOX_HOST}" "pct create ${CONTAINER_ID} local:vztmpl/ubuntu-24.04-standard_24.04-2_amd64.tar.zst \
        --hostname ${CONTAINER_HOSTNAME} \
        --memory ${CONTAINER_MEMORY} \
        --cores ${CONTAINER_CORES} \
        --net0 name=eth0,bridge=vmbr0,ip=dhcp \
        --storage local-lvm \
        --rootfs local-lvm:${CONTAINER_DISK} \
        --unprivileged 0 \
        --features nesting=1,keyctl=1 \
        --onboot 1 \
        --description 'PaperTrade - Stock Market Paper Trading Platform (Privileged for Docker)'"
    
    log_info "Container ${CONTAINER_ID} created"
}

# Start container
start_container() {
    log_info "Starting container..."
    
    ssh "${PROXMOX_HOST}" "pct start ${CONTAINER_ID}"
    
    log_info "Waiting for container to boot..."
    sleep 10
}

# Install Docker
install_docker() {
    log_info "Installing Docker in container..."
    
    # Update packages
    ssh "${PROXMOX_HOST}" "pct exec ${CONTAINER_ID} -- apt-get update -qq"
    ssh "${PROXMOX_HOST}" "pct exec ${CONTAINER_ID} -- apt-get install -y -qq curl ca-certificates"
    
    # Install Docker
    ssh "${PROXMOX_HOST}" "pct exec ${CONTAINER_ID} -- bash -c 'curl -fsSL https://get.docker.com -o get-docker.sh && sh get-docker.sh'"
    
    log_info "Docker installed successfully"
}

# Get container info
get_container_info() {
    log_info "Container information:"
    
    local container_ip
    container_ip=$(ssh "${PROXMOX_HOST}" "pct exec ${CONTAINER_ID} -- ip addr show eth0" | grep 'inet ' | awk '{print $2}' | cut -d'/' -f1)
    
    echo "  Container ID: ${CONTAINER_ID}"
    echo "  Hostname: ${CONTAINER_HOSTNAME}"
    echo "  IP Address: ${container_ip}"
    echo "  Memory: ${CONTAINER_MEMORY}MB"
    echo "  Cores: ${CONTAINER_CORES}"
    echo "  Disk: ${CONTAINER_DISK}GB"
    
    # Check Docker
    local docker_version
    docker_version=$(ssh "${PROXMOX_HOST}" "pct exec ${CONTAINER_ID} -- docker --version")
    echo "  Docker: ${docker_version}"
}

# Main execution
main() {
    log_info "Creating PaperTrade Proxmox container..."
    
    check_existing
    download_template
    create_container
    start_container
    install_docker
    get_container_info
    
    log_info "Container creation complete!"
    log_info "Next step: Run 'task proxmox:deploy' to deploy the application"
}

main "$@"
