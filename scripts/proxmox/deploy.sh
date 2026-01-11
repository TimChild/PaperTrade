#!/usr/bin/env bash
set -euo pipefail

# PaperTrade Proxmox Deployment Script
# This script deploys PaperTrade to a Proxmox LXC container

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
CONTAINER_ID="${PROXMOX_CONTAINER_ID:-107}"
PROXMOX_HOST="${PROXMOX_HOST:-root@proxmox}"
APP_DIR="/opt/papertrade"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $*"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*"
}

# Check SSH connection to Proxmox host
check_ssh_connection() {
    log_info "Checking SSH connection to ${PROXMOX_HOST}..."
    
    if ! ssh -o ConnectTimeout=5 -o BatchMode=yes "${PROXMOX_HOST}" "echo ok" &>/dev/null; then
        log_error "Cannot connect to Proxmox host: ${PROXMOX_HOST}"
        log_error ""
        log_error "Troubleshooting steps:"
        log_error "  1. Check if host is reachable: ping ${PROXMOX_HOST#*@}"
        log_error "  2. Verify SSH key is configured for passwordless login"
        log_error "  3. Check username (usually 'root' for Proxmox)"
        log_error "  4. Test manually: ssh ${PROXMOX_HOST}"
        exit 1
    fi
    
    log_info "SSH connection successful"
}

# Check if container exists and is running
check_container() {
    log_info "Checking if container ${CONTAINER_ID} exists..."

    if ! ssh "${PROXMOX_HOST}" "pct status ${CONTAINER_ID}" &>/dev/null; then
        log_error "Container ${CONTAINER_ID} does not exist!"
        log_error "Run 'task proxmox:create-container' first or set PROXMOX_CONTAINER_ID to an existing container"
        exit 1
    fi

    local status
    status=$(ssh "${PROXMOX_HOST}" "pct status ${CONTAINER_ID}" | awk '{print $2}')

    if [[ "${status}" != "running" ]]; then
        log_warn "Container ${CONTAINER_ID} is ${status}. Starting it..."
        ssh "${PROXMOX_HOST}" "pct start ${CONTAINER_ID}"
        sleep 5
    fi

    log_info "Container ${CONTAINER_ID} is running"
}

# Create tarball of application
create_tarball() {
    log_info "Creating application tarball..."

    cd "${REPO_ROOT}"

    tar -czf /tmp/papertrade.tar.gz \
        --exclude='.git' \
        --exclude='node_modules' \
        --exclude='frontend/dist' \
        --exclude='frontend/node_modules' \
        --exclude='backend/__pycache__' \
        --exclude='backend/.venv' \
        --exclude='backend/.pytest_cache' \
        --exclude='.pytest_cache' \
        --exclude='*.pyc' \
        --exclude='.DS_Store' \
        --exclude='.env.local' \
        .

    log_info "Tarball created: $(ls -lh /tmp/papertrade.tar.gz | awk '{print $5}')"
}

# Transfer files to container
transfer_files() {
    log_info "Transferring files to container..."

    # Copy to Proxmox host
    scp /tmp/papertrade.tar.gz "${PROXMOX_HOST}:/tmp/"

    # Create app directory in container
    ssh "${PROXMOX_HOST}" "pct exec ${CONTAINER_ID} -- mkdir -p ${APP_DIR}"

    # Copy into container
    ssh "${PROXMOX_HOST}" "pct push ${CONTAINER_ID} /tmp/papertrade.tar.gz ${APP_DIR}/papertrade.tar.gz"

    # Extract in container
    ssh "${PROXMOX_HOST}" "pct exec ${CONTAINER_ID} -- tar -xzf ${APP_DIR}/papertrade.tar.gz -C ${APP_DIR} 2>&1 | grep -v 'Ignoring unknown extended header' || true"
    ssh "${PROXMOX_HOST}" "pct exec ${CONTAINER_ID} -- rm ${APP_DIR}/papertrade.tar.gz"

    # Cleanup local tarball
    rm /tmp/papertrade.tar.gz

    log_info "Files transferred successfully"
}

# Setup environment variables
setup_environment() {
    log_info "Setting up environment variables..."

    # Read Alpha Vantage API key from local .env
    if [[ -f "${REPO_ROOT}/.env" ]]; then
        ALPHA_VANTAGE_API_KEY=$(grep ALPHA_VANTAGE_API_KEY "${REPO_ROOT}/.env" | cut -d'=' -f2)
    else
        log_warn "No .env file found, using placeholder API key"
        ALPHA_VANTAGE_API_KEY="PLACEHOLDER"
    fi

    # Check if .env already exists in container (preserve secrets on redeployment)
    if ssh "${PROXMOX_HOST}" "pct exec ${CONTAINER_ID} -- test -f ${APP_DIR}/.env" 2>/dev/null; then
        log_info "Using existing .env file (preserves secrets and database state)"
        
        # Update only non-secret values
        ssh "${PROXMOX_HOST}" "pct exec ${CONTAINER_ID} -- bash -c '
            sed -i \"s|^ALPHA_VANTAGE_API_KEY=.*|ALPHA_VANTAGE_API_KEY=${ALPHA_VANTAGE_API_KEY}|\" ${APP_DIR}/.env
            sed -i \"s|^APP_ENV=.*|APP_ENV=production|\" ${APP_DIR}/.env
            sed -i \"s|^APP_DEBUG=.*|APP_DEBUG=false|\" ${APP_DIR}/.env
            sed -i \"s|^APP_LOG_LEVEL=.*|APP_LOG_LEVEL=INFO|\" ${APP_DIR}/.env
        '"
        
        log_info "Updated .env with latest configuration"
    else
        log_info "Creating new .env file with generated secrets"
        
        # Generate secrets only on first deploy
        POSTGRES_PASSWORD=$(openssl rand -base64 32)
        SECRET_KEY=$(openssl rand -base64 32)
        
        # Create .env file in container using a temporary file
        cat > /tmp/papertrade.env << EOF
# Database
POSTGRES_DB=papertrade
POSTGRES_USER=papertrade
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}

# Application Security
SECRET_KEY=${SECRET_KEY}

# Market Data API
ALPHA_VANTAGE_API_KEY=${ALPHA_VANTAGE_API_KEY}

# App Configuration
APP_ENV=production
APP_DEBUG=false
APP_LOG_LEVEL=INFO
EOF

        # Copy to Proxmox and then to container
        scp /tmp/papertrade.env "${PROXMOX_HOST}:/tmp/"
        ssh "${PROXMOX_HOST}" "pct push ${CONTAINER_ID} /tmp/papertrade.env ${APP_DIR}/.env"

        # Cleanup
        rm /tmp/papertrade.env
        ssh "${PROXMOX_HOST}" "rm /tmp/papertrade.env"
        
        log_info "New secrets generated and saved"
    fi

    log_info "Environment configured"
}

# Deploy application
deploy_app() {
    log_info "Building and starting application..."

    ssh "${PROXMOX_HOST}" "pct exec ${CONTAINER_ID} -- bash -c 'cd ${APP_DIR} && docker compose -f docker-compose.prod.yml up --build -d'"

    log_info "Waiting for services to start..."
    sleep 10

    # Run migrations
    log_info "Running database migrations..."
    ssh "${PROXMOX_HOST}" "pct exec ${CONTAINER_ID} -- docker compose -f ${APP_DIR}/docker-compose.prod.yml exec -T backend alembic upgrade head" || log_warn "Migration failed (may be OK if database already initialized)"
}

# Verify deployment
verify_deployment() {
    log_info "Verifying deployment..."

    # Wait for services to become healthy
    log_info "Waiting for services to become healthy (timeout: 2 minutes)..."
    local max_attempts=24  # 24 * 5s = 2 minutes
    local attempt=0
    local all_healthy=false
    
    while [ $attempt -lt $max_attempts ]; do
        # Check if all services are healthy
        local healthy_count
        healthy_count=$(ssh "${PROXMOX_HOST}" "pct exec ${CONTAINER_ID} -- docker compose -f ${APP_DIR}/docker-compose.prod.yml ps --format json 2>/dev/null" | grep -c '"Health":"healthy"' || echo "0")
        
        # We expect 4 services to be healthy (db, redis, backend, frontend)
        if [ "$healthy_count" -ge 4 ]; then
            all_healthy=true
            break
        fi
        
        attempt=$((attempt + 1))
        echo -n "."
        sleep 5
    done
    
    echo ""  # New line after progress dots
    
    if [ "$all_healthy" = false ]; then
        log_warn "Not all services became healthy within timeout"
        log_warn "You may need to check logs with: task proxmox:logs"
    else
        log_info "All services are healthy!"
    fi

    # Check container status
    log_info "Container status:"
    ssh "${PROXMOX_HOST}" "pct exec ${CONTAINER_ID} -- docker compose -f ${APP_DIR}/docker-compose.prod.yml ps"

    # Get container IP
    local container_ip
    container_ip=$(ssh "${PROXMOX_HOST}" "pct exec ${CONTAINER_ID} -- ip addr show eth0" | grep 'inet ' | awk '{print $2}' | cut -d'/' -f1)

    log_info "Container IP: ${container_ip}"
    log_info "Application URL: http://${container_ip}"
    log_info "API Docs: http://${container_ip}:8000/docs"
}

# Main execution
main() {
    log_info "Starting PaperTrade deployment to Proxmox container ${CONTAINER_ID}..."

    check_ssh_connection
    check_container
    create_tarball
    transfer_files
    setup_environment
    deploy_app
    verify_deployment

    log_info "Deployment complete!"
}

main "$@"
