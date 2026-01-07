# Docker Commands Reference

Common Docker and Docker Compose commands for local development.

## Starting Services

```bash
task docker:up                # PostgreSQL, Redis only
task docker:up:all            # Include backend/frontend
```

## Stopping Services

```bash
task docker:down              # Stop all services
```

## Status & Logs

```bash
docker ps                     # Running containers
docker-compose ps             # Service health
docker-compose logs -f        # All logs (follow)
docker-compose logs -f backend  # Specific service
```

## Common Operations

**Reset database** (deletes all data):
```bash
task docker:down
docker volume rm papertrade_postgres_data
task docker:up
```

**Restart service**:
```bash
docker-compose restart backend
```

**Execute in container**:
```bash
docker-compose exec backend bash
docker-compose exec db psql -U postgres
```

## Troubleshooting

| Issue | Command |
|-------|---------|
| Port in use | `lsof -ti:5432 \| xargs kill -9` |
| Container won't start | `docker-compose logs <service-name>` |
| Reset container | `docker-compose rm <service-name> && task docker:up` |
| Check DB running | `docker-compose ps db` |
