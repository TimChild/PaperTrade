# Proxmox Deployment Tasks for PaperTrade

This document describes the Taskfile commands for deploying and managing PaperTrade on Proxmox.

## Prerequisites

- SSH access configured to Proxmox host: `root@proxmox`
- Ubuntu 24.04 LXC template downloaded on Proxmox
- Alpha Vantage API key in local `.env` file

## Initial Setup

### `task deploy:proxmox:setup`

Creates and configures a new LXC container (ID: 106) on Proxmox with full Docker support.

```bash
task deploy:proxmox:setup
```

**What it does:**
1. Creates privileged LXC container with Docker nesting enabled
2. Allocates 4GB RAM, 2 CPU cores, 20GB storage
3. Installs Docker and Docker Compose
4. Deploys application files
5. Configures production environment
6. Builds and starts all services

**Container specifications:**
- ID: 106
- Hostname: papertrade
- Type: Privileged (required for Docker)
- Resources: 4GB RAM, 2 cores, 20GB disk
- Network: DHCP on vmbr0
- Auto-start: Enabled

## Deployment & Updates

### `task deploy:proxmox:push`

Deploy or update the application code to an existing Proxmox container.

```bash
task deploy:proxmox:push
```

**What it does:**
1. Packages application (excludes .git, node_modules, build artifacts)
2. Transfers to Proxmox container
3. Extracts files to `/opt/papertrade/`
4. Configures environment (if .env doesn't exist)
5. Builds Docker images
6. Starts services
7. Runs database migrations

**Use this after:**
- Making code changes
- Updating dependencies
- Modifying Docker configurations

## Service Management

### `task deploy:proxmox:up`

Start all application services.

```bash
task deploy:proxmox:up
```

### `task deploy:proxmox:down`

Stop all application services.

```bash
task deploy:proxmox:down
```

### `task deploy:proxmox:restart`

Restart all services (down + up).

```bash
task deploy:proxmox:restart
```

## Monitoring & Debugging

### `task deploy:proxmox:status`

Check deployment status and get access URLs.

```bash
task deploy:proxmox:status
```

**Displays:**
- Container IP address
- Docker container status
- Access URLs (frontend, backend, API docs)

### `task deploy:proxmox:logs`

View application logs.

```bash
# All services
task deploy:proxmox:logs

# Specific service
task deploy:proxmox:logs SERVICE=backend
task deploy:proxmox:logs SERVICE=frontend
task deploy:proxmox:logs SERVICE=db
task deploy:proxmox:logs SERVICE=redis
```

### `task deploy:proxmox:shell`

Open an interactive shell in the container.

```bash
task deploy:proxmox:shell
```

## Database Management

### `task deploy:proxmox:migrate`

Run database migrations.

```bash
task deploy:proxmox:migrate
```

### `task deploy:proxmox:backup`

Create a database backup.

```bash
task deploy:proxmox:backup
```

Backups are stored in `/opt/papertrade/backups/` inside the container with timestamp filenames.

## Advanced Usage

### Build Only

```bash
task deploy:proxmox:build
```

Rebuilds Docker images without restarting services.

### Execute Custom Commands

```bash
# Via pct exec (from Proxmox host)
ssh root@proxmox "pct exec 106 -- bash -c 'your command here'"

# Inside container
task deploy:proxmox:shell
# then run commands interactively
```

## Typical Workflows

### First-Time Deployment

```bash
# 1. Initial setup (creates container, installs Docker, deploys app)
task deploy:proxmox:setup

# 2. Check status
task deploy:proxmox:status

# 3. View logs to verify everything started
task deploy:proxmox:logs
```

### Update After Code Changes

```bash
# 1. Push new code and rebuild
task deploy:proxmox:push

# 2. Verify deployment
task deploy:proxmox:status

# 3. Check logs if needed
task deploy:proxmox:logs SERVICE=backend
```

### Troubleshooting

```bash
# 1. Check status
task deploy:proxmox:status

# 2. View logs
task deploy:proxmox:logs

# 3. If services are down, restart
task deploy:proxmox:restart

# 4. If issues persist, open shell and investigate
task deploy:proxmox:shell
```

## Configuration Details

### Environment Variables

The deployment automatically generates a `.env` file in `/opt/papertrade/` with:

- **POSTGRES_PASSWORD**: Auto-generated (32-byte random)
- **SECRET_KEY**: Auto-generated (32-byte random)
- **ALPHA_VANTAGE_API_KEY**: Copied from your local `.env` file
- **APP_ENV**: production
- **APP_DEBUG**: false

### Port Mapping

- **Frontend**: Port 8080 (http://CONTAINER_IP:8080)
- **Backend**: Port 8000 (http://CONTAINER_IP:8000)
- **PostgreSQL**: Internal only (not exposed)
- **Redis**: Internal only (not exposed)

Port 8080 is used instead of 80 to avoid permission issues with unprivileged port binding.

### Data Persistence

Docker volumes ensure data persists across container restarts:
- `postgres_data`: PostgreSQL database
- `redis_data`: Redis cache

## Security Considerations

1. **Container Type**: Uses privileged LXC container (required for Docker nesting)
2. **Network**: Container accessible on local network only
3. **Secrets**: Generated automatically, stored in container `.env` file
4. **Firewall**: No firewall configured by default - add if exposing to internet
5. **SSL/TLS**: Currently HTTP only - add reverse proxy for HTTPS if needed

## Backup Strategy

### Automated Daily Backups (Recommended)

Set up cron job inside container:

```bash
task deploy:proxmox:shell

# Inside container:
crontab -e

# Add line:
0 2 * * * cd /opt/papertrade && docker compose -f docker-compose.prod.yml exec -T db pg_dump -U papertrade papertrade | gzip > backups/papertrade_$(date +\%Y\%m\%d_\%H\%M\%S).sql.gz

# Clean up old backups (keep 7 days):
0 3 * * * find /opt/papertrade/backups -name "papertrade_*.sql.gz" -mtime +7 -delete
```

### Proxmox Container Backups

Configure in Proxmox web UI or via CLI:

```bash
# Manual backup
ssh root@proxmox "vzdump 106 --storage local --mode snapshot --compress zstd"

# Or schedule via Proxmox Datacenter > Backup
```

## Troubleshooting Common Issues

### Container Won't Start

```bash
ssh root@proxmox "pct status 106"
ssh root@proxmox "pct start 106"
```

### Services Not Running

```bash
task deploy:proxmox:status
task deploy:proxmox:logs

# Restart services
task deploy:proxmox:restart
```

### Can't Access Application

1. Get container IP: `task deploy:proxmox:status`
2. Check services are running: `task deploy:proxmox:logs`
3. Test from local network: `curl http://CONTAINER_IP:8080`
4. Check firewall if applicable

### Database Connection Errors

```bash
# Check PostgreSQL is running
task deploy:proxmox:logs SERVICE=db

# Restart database
task deploy:proxmox:down
task deploy:proxmox:up
```

### Out of Disk Space

```bash
# Clean up Docker resources
task deploy:proxmox:shell
docker system prune -af
docker volume prune -f
```

## Support

For issues or questions, refer to:
- Main documentation: `docs/deployment/proxmox-deployment.md`
- Deployment strategy: `docs/planning/deployment_strategy.md`
- Repository: https://github.com/TimChild/PaperTrade
