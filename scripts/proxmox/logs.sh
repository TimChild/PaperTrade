#!/usr/bin/env bash
set -euo pipefail

# PaperTrade Proxmox Logs Script
# View application logs

PROXMOX_HOST="${PROXMOX_HOST:-root@proxmox}"
CONTAINER_ID="${PROXMOX_CONTAINER_ID:-107}"
APP_DIR="/opt/papertrade"
SERVICE="${1:-}"

if [[ -n "${SERVICE}" ]]; then
    ssh "${PROXMOX_HOST}" "pct exec ${CONTAINER_ID} -- docker compose -f ${APP_DIR}/docker-compose.prod.yml logs -f ${SERVICE}"
else
    ssh "${PROXMOX_HOST}" "pct exec ${CONTAINER_ID} -- docker compose -f ${APP_DIR}/docker-compose.prod.yml logs -f"
fi
