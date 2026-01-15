# Task 035: Dockerize Backend and Frontend Applications

**Agent**: quality-infra
**Priority**: High
**Estimated Effort**: 2-3 hours

## Objective

Create production-ready Dockerfiles for both the backend (FastAPI) and frontend (React/Vite) applications, and update docker-compose.yml to orchestrate all services together. This will enable the entire application stack to run with a single `docker compose up` command without blocking terminals.

## Context

Currently:
- PostgreSQL and Redis run via docker-compose.yml
- Backend and frontend run via `task dev:backend` and `task dev:frontend`, which block terminals
- No Dockerfiles exist for backend or frontend
- Development workflow requires manually starting services in separate terminals

## Requirements

### Backend Dockerfile (`backend/Dockerfile`)

Create a multi-stage Dockerfile using Python 3.12+ and uv:

1. **Build best practices**:
   - Multi-stage build (builder + runtime)
   - Layer caching optimization (copy dependency files first, then source code)
   - Use `uv` for fast dependency installation
   - Non-root user for security
   - Health check endpoint
   - Minimal final image size

2. **Development variant** (`backend/Dockerfile.dev`):
   - Hot-reload support for development
   - Mount source code as volume
   - Include dev dependencies

3. **Environment**:
   - Expose port 8000
   - Set PYTHONUNBUFFERED=1
   - Configure appropriate working directory
   - Use .dockerignore to exclude unnecessary files

### Frontend Dockerfile (`frontend/Dockerfile`)

Create a multi-stage Dockerfile for the Vite React app:

1. **Build stage**:
   - Node.js 20
   - Copy package.json and package-lock.json first (cache layer)
   - npm ci for reproducible builds
   - npm run build to create production assets

2. **Production stage**:
   - Use nginx:alpine for serving static files
   - Copy built assets from build stage
   - Configure nginx for SPA routing (fallback to index.html)
   - Expose port 80
   - Health check on root path

3. **Development variant** (`frontend/Dockerfile.dev`):
   - Hot-reload with Vite dev server
   - Expose port 5173
   - Mount source code as volume

### Docker Compose Updates (`docker-compose.yml`)

Update the existing docker-compose.yml to include:

```yaml
services:
  postgres:
    # ... existing configuration ...

  redis:
    # ... existing configuration ...

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile.dev  # or Dockerfile for prod
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://zebu:zebu@postgres:5432/zebu
      REDIS_URL: redis://redis:6379/0
      ALPHA_VANTAGE_API_KEY: ${ALPHA_VANTAGE_API_KEY:-demo}
    depends_on:
      - postgres
      - redis
    volumes:
      - ./backend:/app  # Dev: mount source for hot-reload
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 10s
      timeout: 5s
      retries: 3

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.dev  # or Dockerfile for prod
    ports:
      - "5173:5173"  # Dev port (or 80 for prod)
    environment:
      VITE_API_URL: http://localhost:8000
    depends_on:
      - backend
    volumes:
      - ./frontend:/app  # Dev: mount source for hot-reload
      - /app/node_modules  # Prevent overwriting node_modules
```

### Docker Ignore Files

Create `.dockerignore` files:

**backend/.dockerignore**:
```
__pycache__/
*.pyc
*.pyo
*.pyd
.pytest_cache/
.ruff_cache/
.mypy_cache/
*.egg-info/
dist/
build/
.venv/
.env
*.db
*.sqlite
```

**frontend/.dockerignore**:
```
node_modules/
dist/
.vite/
*.log
.env
.DS_Store
coverage/
```

### Taskfile Updates

Add new tasks to `Taskfile.yml`:

```yaml
docker:build:
  desc: Build all Docker images
  cmds:
    - docker compose build

docker:up:dev:
  desc: Start all services in development mode
  cmds:
    - docker compose up -d

docker:logs:
  desc: Follow logs for all services
  cmds:
    - docker compose logs -f

docker:restart:
  desc: Restart all services
  cmds:
    - docker compose restart

docker:build:prod:
  desc: Build production images
  cmds:
    - docker compose -f docker-compose.prod.yml build
```

## Technical Specifications

### Cache Layer Optimization

Backend Dockerfile should copy files in this order:
1. `pyproject.toml` and `uv.lock` → install deps
2. Source code → build application

Frontend Dockerfile should copy files in this order:
1. `package.json` and `package-lock.json` → install deps
2. Source code → build assets

### Security Best Practices

- Run as non-root user
- Use specific base image versions (not `latest`)
- Minimize attack surface (multi-stage builds)
- No secrets in Dockerfiles (use environment variables)

### Performance Considerations

- Use `.dockerignore` to reduce build context
- Leverage layer caching for faster rebuilds
- Use `COPY --from` for multi-stage builds
- Alpine base images where appropriate

## Success Criteria

- [ ] `backend/Dockerfile` exists with multi-stage build
- [ ] `backend/Dockerfile.dev` exists for development with hot-reload
- [ ] `frontend/Dockerfile` exists with nginx serving
- [ ] `frontend/Dockerfile.dev` exists for Vite dev server
- [ ] Both `.dockerignore` files created
- [ ] `docker-compose.yml` updated with all 4 services
- [ ] Optional: `docker-compose.prod.yml` for production config
- [ ] `docker compose up` starts all services successfully
- [ ] Backend accessible at http://localhost:8000
- [ ] Frontend accessible at http://localhost:5173 (dev) or http://localhost:80 (prod)
- [ ] Hot-reload works in development mode
- [ ] Health checks pass for all services
- [ ] All existing tests still pass
- [ ] Taskfile updated with docker commands

## Testing Steps

1. Build images: `docker compose build`
2. Start services: `docker compose up -d`
3. Verify backend: `curl http://localhost:8000/health`
4. Verify frontend: `curl http://localhost:5173/`
5. Check logs: `docker compose logs -f`
6. Test hot-reload: Modify a file, verify it rebuilds
7. Run tests inside containers: `docker compose exec backend uv run pytest`
8. Verify database migrations work
9. Clean up: `docker compose down`

## References

- Current docker-compose.yml (PostgreSQL + Redis already configured)
- Backend: FastAPI, Python 3.12+, uv package manager
- Frontend: React + Vite + TypeScript
- [Dockerfile best practices](https://docs.docker.com/develop/develop-images/dockerfile_best-practices/)
- [Multi-stage builds](https://docs.docker.com/build/building/multi-stage/)

## Notes

- Maintain separate dev and prod configurations
- Dev mode should prioritize hot-reload and debugging
- Prod mode should prioritize security and performance
- Ensure .env file usage is documented
- Update README.md with new Docker commands after implementation
