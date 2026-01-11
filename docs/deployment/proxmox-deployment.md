# PaperTrade Proxmox Deployment Guide

**Date**: January 10, 2026
**Container ID**: 106
**Container IP**: 192.168.4.104
**Hostname**: papertrade

## Container Specifications

- **OS**: Ubuntu 24.04 LTS (Noble)
- **CPU**: 2 cores
- **RAM**: 4GB
- **Storage**: 20GB
- **Features**: Docker nesting enabled (required for Docker-in-Docker)
- **Network**: Bridge mode (vmbr0), DHCP

## Deployment Steps Completed

### 1. LXC Container Creation

```bash
# Created container 106 with Docker support
pct create 106 local:vztmpl/ubuntu-24.04-standard_24.04-2_amd64.tar.zst \
  --hostname papertrade \
  --memory 4096 \
  --cores 2 \
  --net0 name=eth0,bridge=vmbr0,ip=dhcp \
  --storage local-lvm \
  --rootfs local-lvm:20 \
  --unprivileged 1 \
  --features nesting=1,keyctl=1 \
  --onboot 1 \
  --description 'PaperTrade - Stock Market Paper Trading Platform'
```

### 2. Docker Installation

```bash
# Installed Docker Engine and Docker Compose inside container
pct exec 106 -- bash -c 'curl -fsSL https://get.docker.com -o get-docker.sh && sh get-docker.sh'

# Versions installed:
# - Docker Engine: 29.1.4
# - Docker Compose: v5.0.1
```

### 3. Application Deployment

```bash
# Created project directory
pct exec 106 -- mkdir -p /opt/papertrade

# Transferred application files (3.1MB tarball)
# Extracted to /opt/papertrade/

# Created production .env file with:
# - PostgreSQL database credentials (auto-generated password)
# - SECRET_KEY for JWT/session security (auto-generated)
# - ALPHA_VANTAGE_API_KEY: DK1ACPJOWOIGLVIJ
# - APP_ENV=production, APP_DEBUG=false

# Started application stack
cd /opt/papertrade && docker compose -f docker-compose.prod.yml up --build -d
```

## Application Stack

The following containers are running inside LXC 106:

1. **papertrade-postgres-prod**: PostgreSQL 16 database
   - Port: 5432 (internal to container)
   - Volume: postgres_data (persistent)

2. **papertrade-redis-prod**: Redis 7 cache
   - Port: 6379 (internal to container)
   - Volume: redis_data (persistent)

3. **papertrade-backend-prod**: FastAPI backend
   - Port: 8000 (exposed on container IP)
   - Environment: Production

4. **papertrade-frontend-prod**: Nginx serving React SPA
   - Port: 80 (exposed on container IP)
   - Environment: Production

## Access Information

**Application URL**: http://192.168.4.104
**API Docs**: http://192.168.4.104:8000/docs (if backend port is exposed)

**SSH Access**:
```bash
# From Proxmox host
pct enter 106

# Or via network
ssh root@192.168.4.104  # (if SSH is configured)
```

## Health Checks

```bash
# Check all containers
pct exec 106 -- docker compose -f /opt/papertrade/docker-compose.prod.yml ps

# View logs
pct exec 106 -- docker compose -f /opt/papertrade/docker-compose.prod.yml logs -f

# Check specific service
pct exec 106 -- docker compose -f /opt/papertrade/docker-compose.prod.yml logs backend
```

## Management Commands

### Start/Stop Application

```bash
# Stop all services
pct exec 106 -- docker compose -f /opt/papertrade/docker-compose.prod.yml down

# Start all services
pct exec 106 -- docker compose -f /opt/papertrade/docker-compose.prod.yml up -d

# Restart specific service
pct exec 106 -- docker compose -f /opt/papertrade/docker-compose.prod.yml restart backend
```

### Database Migrations

```bash
# Run Alembic migrations
pct exec 106 -- docker compose -f /opt/papertrade/docker-compose.prod.yml exec backend alembic upgrade head

# Check migration status
pct exec 106 -- docker compose -f /opt/papertrade/docker-compose.prod.yml exec backend alembic current
```

### View Logs

```bash
# All services
pct exec 106 -- docker compose -f /opt/papertrade/docker-compose.prod.yml logs -f

# Specific service
pct exec 106 -- docker compose -f /opt/papertrade/docker-compose.prod.yml logs -f backend
pct exec 106 -- docker compose -f /opt/papertrade/docker-compose.prod.yml logs -f frontend

# Last 100 lines
pct exec 106 -- docker compose -f /opt/papertrade/docker-compose.prod.yml logs --tail=100
```

## Backup Strategy

### Database Backups

**Automated Daily Backups** (via cron inside container):

```bash
# Create backup script
pct exec 106 -- bash -c 'cat > /opt/papertrade/backup-db.sh << "EOF"
#!/bin/bash
BACKUP_DIR="/opt/papertrade/backups"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR
docker compose -f /opt/papertrade/docker-compose.prod.yml exec -T db \
  pg_dump -U papertrade papertrade | gzip > $BACKUP_DIR/papertrade_$DATE.sql.gz
# Keep only last 7 days
find $BACKUP_DIR -name "papertrade_*.sql.gz" -mtime +7 -delete
EOF
chmod +x /opt/papertrade/backup-db.sh'

# Add to crontab (daily at 2 AM)
pct exec 106 -- bash -c 'echo "0 2 * * * /opt/papertrade/backup-db.sh" | crontab -'
```

### Proxmox Backup Server (PBS)

**Container-Level Backups**:

```bash
# Configure backup job in Proxmox (via web UI or CLI)
# Backup schedule: Daily at 3 AM
# Retention: Keep 7 daily, 4 weekly, 6 monthly

# Or via CLI:
vzdump 106 --storage <backup-storage> --mode snapshot --compress zstd
```

## Monitoring

### Resource Usage

```bash
# Container stats
pct exec 106 -- docker stats

# Check disk usage
pct exec 106 -- df -h
pct exec 106 -- docker system df

# Check logs size
pct exec 106 -- du -sh /var/lib/docker/containers/*/*-json.log
```

### Health Checks

```bash
# Backend health endpoint
curl -f http://192.168.4.104:8000/health

# Frontend health endpoint
curl -f http://192.168.4.104/health

# Database connection
pct exec 106 -- docker compose -f /opt/papertrade/docker-compose.prod.yml exec db \
  pg_isready -U papertrade

# Redis connection
pct exec 106 -- docker compose -f /opt/papertrade/docker-compose.prod.yml exec redis \
  redis-cli ping
```

## Updating the Application

### Pull Latest Code

```bash
# On local machine, create new tarball
cd /Users/timchild/github/PaperTrade
git pull origin main
tar -czf /tmp/papertrade-update.tar.gz \
  --exclude='.git' \
  --exclude='node_modules' \
  --exclude='frontend/dist' \
  --exclude='backend/__pycache__' \
  --exclude='backend/.venv' \
  .

# Transfer to Proxmox
scp /tmp/papertrade-update.tar.gz root@proxmox:/tmp/

# Copy to container
ssh root@proxmox "pct push 106 /tmp/papertrade-update.tar.gz /opt/papertrade/update.tar.gz"

# Extract and rebuild
pct exec 106 -- bash -c '
  cd /opt/papertrade
  docker compose -f docker-compose.prod.yml down
  tar -xzf update.tar.gz
  rm update.tar.gz
  docker compose -f docker-compose.prod.yml up --build -d
'
```

## Troubleshooting

### Container Won't Start

```bash
# Check container status
pct status 106

# View container logs
journalctl -u pvecontainer@106.service -n 100

# Start manually
pct start 106
```

### Docker Services Failing

```bash
# Check Docker service
pct exec 106 -- systemctl status docker

# Restart Docker
pct exec 106 -- systemctl restart docker

# Check disk space
pct exec 106 -- df -h

# Clean up Docker resources
pct exec 106 -- docker system prune -af
```

### Database Connection Errors

```bash
# Check PostgreSQL is running
pct exec 106 -- docker compose -f /opt/papertrade/docker-compose.prod.yml ps db

# View database logs
pct exec 106 -- docker compose -f /opt/papertrade/docker-compose.prod.yml logs db

# Connect to database
pct exec 106 -- docker compose -f /opt/papertrade/docker-compose.prod.yml exec db \
  psql -U papertrade -d papertrade
```

### Network Issues

```bash
# Check container IP
pct exec 106 -- ip addr show eth0

# Test connectivity from container
pct exec 106 -- ping -c 3 google.com

# Check firewall (if configured)
pct exec 106 -- ufw status
```

## Security Considerations

1. **Firewall**: Currently no firewall configured - consider `ufw` if exposing to internet
2. **SSL/TLS**: Currently HTTP only - add reverse proxy (Nginx/Caddy) for HTTPS if needed
3. **Secrets**: All secrets stored in /opt/papertrade/.env - ensure proper file permissions
4. **Updates**: Keep Docker and Ubuntu packages updated regularly

```bash
# Update packages inside container
pct exec 106 -- apt-get update && apt-get upgrade -y
```

## Notes

- Container automatically starts on Proxmox boot (`--onboot 1`)
- All data persists in Docker volumes (survives container restarts)
- Container IP may change if DHCP lease expires - consider static IP assignment
- Backend build uses pip instead of uv due to SSL certificate compatibility in Docker

## Support & Maintenance

**Documentation**: See [/Users/timchild/github/PaperTrade/docs/](/Users/timchild/github/PaperTrade/docs/)
**Repository**: https://github.com/TimChild/PaperTrade
**Deployment Strategy**: [docs/planning/deployment_strategy.md](/Users/timchild/github/PaperTrade/docs/planning/deployment_strategy.md)
