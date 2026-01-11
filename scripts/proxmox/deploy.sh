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

    # Create .env file in container using a temporary file
    cat > /tmp/papertrade.env << EOF
# Database
POSTGRES_DB=papertrade
POSTGRES_USER=papertrade
POSTGRES_PASSWORD=$(openssl rand -base64 32)

# Application Security
SECRET_KEY=$(openssl rand -base64 32)

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

    log_info "Environment configured"
}

# Fix backend Dockerfile
fix_dockerfile() {
    log_info "Fixing backend Dockerfile..."

    # Create fixed Dockerfile using temporary file
    cat > /tmp/Dockerfile.backend << 'EOF'
FROM python:3.12-slim AS builder
RUN apt-get update && apt-get install -y gcc curl && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY src/ ./src/
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -e "."
COPY alembic.ini ./
COPY migrations/ ./migrations/

FROM python:3.12-slim AS runtime
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /app /app
EXPOSE 8000
CMD ["uvicorn", "papertrade.main:app", "--host", "0.0.0.0", "--port", "8000"]
EOF

    # Transfer and replace
    scp /tmp/Dockerfile.backend "${PROXMOX_HOST}:/tmp/"
    ssh "${PROXMOX_HOST}" "pct push ${CONTAINER_ID} /tmp/Dockerfile.backend ${APP_DIR}/backend/Dockerfile"

    # Cleanup
    rm /tmp/Dockerfile.backend
    ssh "${PROXMOX_HOST}" "rm /tmp/Dockerfile.backend"

    log_info "Dockerfile fixed"
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

    check_container
    create_tarball
    transfer_files
    setup_environment
    fix_dockerfile
    deploy_app
    verify_deployment

    log_info "Deployment complete!"
}

main "$@"
