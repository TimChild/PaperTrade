#!/usr/bin/env bash
set -euo pipefail

# PaperTrade Proxmox Status Script
# Shows current deployment status

PROXMOX_HOST="${PROXMOX_HOST:-root@proxmox}"
CONTAINER_ID="${PROXMOX_CONTAINER_ID:-107}"
APP_DIR="/opt/papertrade"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $*"
}

# Check if container exists
if ! ssh "${PROXMOX_HOST}" "pct status ${CONTAINER_ID}" &>/dev/null; then
    echo "Container ${CONTAINER_ID} does not exist"
    echo "Run 'task proxmox:create-container' to create it"
    exit 1
fi

# Get container status
log_info "Container Status:"
ssh "${PROXMOX_HOST}" "pct status ${CONTAINER_ID}"

# Get container IP
log_info "Container IP:"
ssh "${PROXMOX_HOST}" "pct exec ${CONTAINER_ID} -- ip addr show eth0" | grep 'inet ' | awk '{print $2}'

# Check Docker containers
log_info "Docker Containers:"
ssh "${PROXMOX_HOST}" "pct exec ${CONTAINER_ID} -- docker compose -f ${APP_DIR}/docker-compose.prod.yml ps 2>/dev/null" || echo "Application not deployed yet"

# Get container IP for URL
container_ip=$(ssh "${PROXMOX_HOST}" "pct exec ${CONTAINER_ID} -- ip addr show eth0" | grep 'inet ' | awk '{print $2}' | cut -d'/' -f1)

echo ""
log_info "Access URLs:"
echo "  Application: http://${container_ip}"
echo "  API Docs: http://${container_ip}:8000/docs"
