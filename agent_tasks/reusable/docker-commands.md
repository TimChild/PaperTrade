# Docker Commands Reference

Common Docker and Docker Compose commands for local development.

## Starting Services

Start all services (PostgreSQL, Redis):
```bash
task docker:up
```

Start all services including backend/frontend:
```bash
task docker:up:all
```

## Stopping Services

Stop all Docker services:
```bash
task docker:down
```

## Checking Status

View running containers:
```bash
docker ps
```

Check service health:
```bash
docker-compose ps
```

## Viewing Logs

Backend logs:
```bash
docker-compose logs -f backend
```

Database logs:
```bash
docker-compose logs -f db
```

All service logs:
```bash
docker-compose logs -f
```

## Common Operations

Reset database (WARNING: deletes all data):
```bash
task docker:down
docker volume rm papertrade_postgres_data
task docker:up
```

Restart a specific service:
```bash
docker-compose restart backend
```

Execute command in running container:
```bash
docker-compose exec backend bash
docker-compose exec db psql -U postgres
```

## Troubleshooting

### Port already in use
```bash
# Find and kill process using port 5432 (PostgreSQL)
lsof -ti:5432 | xargs kill -9

# Or use different port in docker-compose.yml
```

### Container won't start
```bash
# Check logs for errors
docker-compose logs <service-name>

# Remove and recreate
docker-compose rm <service-name>
task docker:up
```

### Database connection issues
```bash
# Verify database is running
docker-compose ps db

# Check connection from backend
docker-compose exec backend python -c "from papertrade.infrastructure.database import engine; print(engine)"
```
