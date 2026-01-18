#!/bin/bash
# Promtail Installation Script for Zebu Production Monitoring
#
# This script installs and configures Promtail to ship logs from Docker containers
# to Grafana Cloud Loki for centralized log aggregation and monitoring.
#
# Usage:
#   1. Set LOKI_URL, LOKI_USERNAME, and LOKI_API_KEY environment variables
#   2. Run: sudo bash install-promtail.sh
#
# Prerequisites:
#   - Docker installed and running
#   - Root access (sudo)
#   - Internet connectivity for downloading Promtail

set -e  # Exit on error
set -u  # Exit on undefined variable

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}✓${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

# Configuration - These should be set via environment variables
LOKI_URL="${LOKI_URL:-}"
LOKI_USERNAME="${LOKI_USERNAME:-}"
LOKI_API_KEY="${LOKI_API_KEY:-}"

# Promtail version
PROMTAIL_VERSION="2.9.3"

# Validate configuration
if [ -z "$LOKI_URL" ] || [ -z "$LOKI_USERNAME" ] || [ -z "$LOKI_API_KEY" ]; then
    log_error "Missing required configuration!"
    echo "Please set the following environment variables:"
    echo "  LOKI_URL       - Grafana Cloud Loki endpoint (e.g., https://logs-prod-us-central1.grafana.net)"
    echo "  LOKI_USERNAME  - Grafana Cloud instance ID"
    echo "  LOKI_API_KEY   - Grafana Cloud API key"
    echo ""
    echo "Example:"
    echo "  export LOKI_URL='https://logs-prod-us-central1.grafana.net'"
    echo "  export LOKI_USERNAME='123456'"
    echo "  export LOKI_API_KEY='your-api-key-here'"
    echo "  sudo -E bash install-promtail.sh"
    exit 1
fi

log_info "Starting Promtail installation..."
echo "  Loki URL: $LOKI_URL"
echo "  Instance ID: $LOKI_USERNAME"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    log_error "This script must be run as root (use sudo)"
    exit 1
fi

# Install unzip if not available
if ! command -v unzip &> /dev/null; then
    log_info "Installing unzip..."
    apt-get update -qq && apt-get install -y unzip
fi

# Download Promtail
log_info "Downloading Promtail v${PROMTAIL_VERSION}..."
cd /tmp
curl -L -o promtail-linux-amd64.zip "https://github.com/grafana/loki/releases/download/v${PROMTAIL_VERSION}/promtail-linux-amd64.zip"

# Extract and install
log_info "Installing Promtail binary..."
unzip -q -o promtail-linux-amd64.zip
chmod +x promtail-linux-amd64
mv promtail-linux-amd64 /usr/local/bin/promtail
rm -f promtail-linux-amd64.zip

# Verify installation
if ! command -v promtail &> /dev/null; then
    log_error "Promtail installation failed"
    exit 1
fi

log_info "Promtail binary installed: $(promtail --version | head -n1)"

# Create config directory
log_info "Creating configuration directory..."
mkdir -p /etc/promtail

# Create Promtail configuration
log_info "Writing Promtail configuration..."
cat > /etc/promtail/config.yml << 'EOF'
# Promtail Configuration for Zebu Production Monitoring
# This configuration ships logs from Docker containers to Grafana Cloud Loki

server:
  http_listen_port: 9080
  grpc_listen_port: 0
  log_level: info

positions:
  filename: /tmp/positions.yaml

clients:
  - url: ${LOKI_URL}/loki/api/v1/push
    basic_auth:
      username: ${LOKI_USERNAME}
      password: ${LOKI_API_KEY}

scrape_configs:
  # Zebu Backend - JSON Structured Logs
  - job_name: zebu-backend
    static_configs:
      - targets:
          - localhost
        labels:
          job: zebu-backend
          container: zebu-backend-prod
          __path__: /var/lib/docker/containers/*/*.log
    pipeline_stages:
      # Parse Docker JSON log format
      - json:
          expressions:
            log: log
            stream: stream
            time: time
      # Extract the actual log content
      - output:
          source: log
      # Parse application JSON logs
      - json:
          expressions:
            level: level
            timestamp: timestamp
            event: event
            logger: logger
            correlation_id: correlation_id
            ticker: ticker
            action: action
            error: error
            duration_ms: duration_ms
            duration_seconds: duration_seconds
            status_code: status_code
          source: log
      # Extract level and logger as labels
      - labels:
          level:
          logger:
      # Use timestamp from log entry
      - timestamp:
          source: timestamp
          format: RFC3339

  # Zebu Frontend - Nginx Access Logs
  - job_name: zebu-frontend
    static_configs:
      - targets:
          - localhost
        labels:
          job: zebu-frontend
          container: zebu-frontend-prod
          __path__: /var/lib/docker/containers/*/*.log

  # PostgreSQL Database Logs
  - job_name: zebu-postgres
    static_configs:
      - targets:
          - localhost
        labels:
          job: zebu-postgres
          container: zebu-postgres-prod
          __path__: /var/lib/docker/containers/*/*.log

  # Redis Cache Logs
  - job_name: zebu-redis
    static_configs:
      - targets:
          - localhost
        labels:
          job: zebu-redis
          container: zebu-redis-prod
          __path__: /var/lib/docker/containers/*/*.log
EOF

# Substitute environment variables in config
sed -i "s|\${LOKI_URL}|$LOKI_URL|g" /etc/promtail/config.yml
sed -i "s|\${LOKI_USERNAME}|$LOKI_USERNAME|g" /etc/promtail/config.yml
sed -i "s|\${LOKI_API_KEY}|$LOKI_API_KEY|g" /etc/promtail/config.yml

log_info "Configuration written to /etc/promtail/config.yml"

# Create systemd service
log_info "Creating systemd service..."
cat > /etc/systemd/system/promtail.service << 'EOF'
[Unit]
Description=Promtail log shipper for Grafana Cloud
Documentation=https://grafana.com/docs/loki/latest/clients/promtail/
After=network.target docker.service
Requires=docker.service

[Service]
Type=simple
User=root
ExecStart=/usr/local/bin/promtail -config.file=/etc/promtail/config.yml
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths=/tmp

[Install]
WantedBy=multi-user.target
EOF

log_info "Systemd service created"

# Reload systemd, enable and start Promtail
log_info "Starting Promtail service..."
systemctl daemon-reload
systemctl enable promtail
systemctl start promtail

# Wait a moment and check status
sleep 2
if systemctl is-active --quiet promtail; then
    log_info "Promtail is running successfully!"
else
    log_error "Promtail failed to start"
    systemctl status promtail --no-pager
    exit 1
fi

# Display status and next steps
echo ""
log_info "Installation complete!"
echo ""
echo "Promtail Status:"
systemctl status promtail --no-pager | head -n 10
echo ""
echo "Next steps:"
echo "  1. Check Promtail logs:  sudo journalctl -u promtail -f"
echo "  2. Verify logs in Grafana Cloud (may take 30-60 seconds)"
echo "  3. Configure dashboards and alerts in Grafana Cloud"
echo ""
echo "Useful commands:"
echo "  - Check status:  sudo systemctl status promtail"
echo "  - Restart:       sudo systemctl restart promtail"
echo "  - View logs:     sudo journalctl -u promtail -f"
echo "  - Stop:          sudo systemctl stop promtail"
