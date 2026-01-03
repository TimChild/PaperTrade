# Task 036: Docker Infrastructure Improvements & Documentation

**Agent**: quality-infra
**Priority**: MEDIUM
**Created**: 2026-01-03
**Status**: Not Started
**Parent PR**: #47 (merged)

## Objective

Address remaining issues and documentation gaps from PR #47 (Docker infrastructure implementation). Focus on production readiness, developer experience improvements, and comprehensive documentation.

## Context

PR #47 successfully implemented full-stack Docker containerization, but several improvements and documentation tasks were deferred due to time constraints. This task addresses those items to ensure a solid foundation for future development.

**Verified Working** (as of 2026-01-03):
- ✅ All services build successfully (PostgreSQL, Redis, Backend, Frontend)
- ✅ Health checks passing for all services
- ✅ Backend accessible on http://localhost:8000
- ✅ Frontend accessible on http://localhost:5173
- ✅ Frontend hot-reload working (Vite HMR detected)
- ✅ Database migrations auto-apply on startup
- ✅ Environment variables properly configured in docker-compose.yml

**Issues to Address** (from PR #47 progress doc):
1. Backend hot-reload not working (uvicorn --reload doesn't detect file changes)
2. SSL certificate workaround in Dockerfile.dev (--trusted-host for pip)
3. Production Dockerfiles not tested with proper SSL
4. Docker setup instructions not in README.md
5. No comprehensive environment variable documentation
6. Missing .env.production.example file

## Requirements

### 1. Fix Backend Hot-Reload

**Problem**: Backend Dockerfile.dev uses `python -m uvicorn` with `--reload` flag, but file changes in mounted volumes don't trigger reloads.

**Investigation needed**:
- Test if uvicorn's file watcher works with Docker volume mounts
- Consider using `watchdog` or `watchfiles` library explicitly
- Check if the issue is macOS-specific (Docker Desktop volume performance)
- Verify `PYTHONPATH` is correctly set for module resolution

**Acceptance Criteria**:
- [ ] Modify backend Dockerfile.dev CMD to ensure hot-reload works
- [ ] Document any platform-specific limitations (if any)
- [ ] Verify with manual test: edit `/backend/src/papertrade/main.py`, confirm uvicorn restarts
- [ ] Add troubleshooting section to README if workarounds needed

### 2. Remove SSL Certificate Workarounds

**Current state**: `backend/Dockerfile.dev` uses:
```dockerfile
RUN pip install --no-cache-dir \
    --trusted-host pypi.org \
    --trusted-host files.pythonhosted.org \
    -e ".[dev]"
```

**Tasks**:
- [ ] Investigate if SSL issues were CI-specific or general
- [ ] Test removing `--trusted-host` flags locally
- [ ] If SSL issues persist, document proper certificate installation
- [ ] Keep workaround only if necessary, but add comment explaining why
- [ ] Ensure production Dockerfile does NOT use --trusted-host

**Note**: Development Dockerfile can keep workaround if needed for convenience, but production must use proper SSL.

### 3. Test Production Docker Configuration

**Tasks**:
- [ ] Build production images: `task docker:build:prod`
- [ ] Test production stack locally: `task docker:up:prod`
- [ ] Verify backend production Dockerfile builds with uv (not pip)
- [ ] Confirm multi-stage builds properly minimize image size
- [ ] Test health checks work in production mode
- [ ] Verify non-root user (appuser) has correct permissions
- [ ] Document image sizes (backend prod vs dev, frontend prod vs dev)

**Expected outcomes**:
```bash
# Example expected sizes
papertrade-backend:latest (dev)   ~800MB
papertrade-backend:prod           ~400MB
papertrade-frontend:latest (dev)  ~600MB
papertrade-frontend:prod          ~50MB (nginx-alpine)
```

### 4. Comprehensive Docker Documentation in README

**Add new section to README.md**: "Docker Development"

**Content to include**:
```markdown
## Docker Development

### Quick Start with Docker

Run the entire stack with one command:

```bash
# Development mode (with hot-reload)
task docker:up:all

# View logs
task docker:logs

# Stop all services
task docker:down
```

Access:
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Production Mode

```bash
# Build production images
task docker:build:prod

# Start production stack
task docker:up:prod
```

Access:
- Frontend: http://localhost:80
- Backend API: http://localhost:8000

### Environment Variables

Copy `.env.example` to `.env` and configure:

**Required**:
- `ALPHA_VANTAGE_API_KEY`: Get from https://www.alphavantage.co/support/#api-key

**Optional** (defaults provided):
- `POSTGRES_PASSWORD`: Database password (default: papertrade_dev_password)
- `SECRET_KEY`: App secret key (default: dev-secret-key-change-in-production)

**Production Only**:
- `APP_LOG_LEVEL`: Logging level (default: INFO)

### Docker Commands

```bash
task docker:up:all          # Start all services
task docker:build           # Rebuild images
task docker:logs            # View all logs
task docker:logs:backend    # Backend logs only
task docker:logs:frontend   # Frontend logs only
task docker:restart         # Restart all services
task docker:clean           # Remove volumes (⚠️ deletes data)
```

### Troubleshooting

**Services won't start**:
```bash
# Check container status
docker compose ps

# View detailed logs
docker compose logs backend
docker compose logs frontend
```

**Database connection errors**:
```bash
# Ensure PostgreSQL is healthy
docker compose ps db

# Reset database
task docker:clean && task docker:up:all
```

**Port conflicts**:
If ports 5432, 6379, 8000, or 5173 are in use:
```bash
# Stop conflicting services
lsof -ti:5432 | xargs kill -9  # PostgreSQL
lsof -ti:6379 | xargs kill -9  # Redis
```
```

### 5. Environment Variable Documentation

**Create**: `.env.production.example`
```dotenv
# Production Environment Configuration for PaperTrade
# Copy this file to .env and fill in your values

# ============================================================================
# DATABASE CONFIGURATION (Required)
# ============================================================================
POSTGRES_HOST=db
POSTGRES_PORT=5432
POSTGRES_DB=papertrade
POSTGRES_USER=papertrade
POSTGRES_PASSWORD=<GENERATE_SECURE_PASSWORD>
# Generate with: openssl rand -base64 32

# ============================================================================
# REDIS CONFIGURATION
# ============================================================================
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
# REDIS_PASSWORD=<optional_redis_password>

# ============================================================================
# APPLICATION SECURITY (Required)
# ============================================================================
SECRET_KEY=<GENERATE_SECURE_SECRET_KEY>
# Generate with: python -c "import secrets; print(secrets.token_urlsafe(32))"

# ============================================================================
# MARKET DATA API (Required for Phase 2+)
# ============================================================================
ALPHA_VANTAGE_API_KEY=<YOUR_API_KEY>
# Get free key: https://www.alphavantage.co/support/#api-key
# Free tier: 5 calls/min, 500/day
# Premium: https://www.alphavantage.co/premium/

# Rate limits (adjust based on your tier)
ALPHA_VANTAGE_RATE_LIMIT_PER_MIN=5
ALPHA_VANTAGE_RATE_LIMIT_PER_DAY=500

# ============================================================================
# APPLICATION CONFIGURATION
# ============================================================================
APP_ENV=production
APP_DEBUG=false
APP_LOG_LEVEL=INFO  # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL

# ============================================================================
# COMPOSITE DATABASE URL (Auto-generated from above)
# ============================================================================
DATABASE_URL=postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}
```

**Update**: `.env.example` to clearly indicate it's for development

**Tasks**:
- [ ] Create `.env.production.example`
- [ ] Add header to `.env.example` indicating "Development Configuration"
- [ ] Add section to README linking to environment variable documentation
- [ ] Document required vs optional variables
- [ ] Add instructions for generating secure secrets

### 6. Copilot Agent Environment Setup

**Verify Copilot agents have necessary configuration**:

**In `.github/workflows/copilot-setup-steps.yml`**:
- [ ] Ensure Docker services (PostgreSQL, Redis) are available if tests need them
- [ ] Verify ALPHA_VANTAGE_API_KEY secret is available
- [ ] Document any required repository secrets in README or agent instructions
- [ ] Consider adding Docker service definitions if agents need to run integration tests

**Potential additions**:
```yaml
services:
  postgres:
    image: postgres:16
    env:
      POSTGRES_DB: papertrade_test
      POSTGRES_USER: papertrade
      POSTGRES_PASSWORD: test_password
    options: >-
      --health-cmd pg_isready
      --health-interval 10s
      --health-timeout 5s
      --health-retries 5

  redis:
    image: redis:7-alpine
    options: >-
      --health-cmd "redis-cli ping"
      --health-interval 10s
      --health-timeout 5s
      --health-retries 5
```

**Documentation**:
- [ ] Add section to `.github/copilot-instructions.md` about required secrets
- [ ] Document how to add ALPHA_VANTAGE_API_KEY to repository secrets
- [ ] List any IP whitelist requirements (if applicable)

## Testing Methodology

### Manual Testing Checklist

**Development Mode**:
```bash
# 1. Clean start
task docker:down && task docker:clean
task docker:up:all

# 2. Verify all services healthy
docker compose ps
# All should show (healthy) status

# 3. Test hot-reload (backend)
# Edit backend/src/papertrade/main.py - add comment
# Check logs: docker compose logs backend --tail 20
# Should see uvicorn restart message

# 4. Test hot-reload (frontend)
# Edit frontend/src/App.tsx - add comment
# Check logs: docker compose logs frontend --tail 20
# Should see HMR update message

# 5. Test API
curl http://localhost:8000/health
curl http://localhost:8000/docs  # Should load

# 6. Test frontend
curl http://localhost:5173/  # Should return HTML
```

**Production Mode**:
```bash
# 1. Build and start
task docker:build:prod
task docker:up:prod

# 2. Verify services
docker compose -f docker-compose.prod.yml ps

# 3. Test endpoints
curl http://localhost:8000/health
curl http://localhost:80/  # Should return HTML
```

### Automated Testing

**Add to Taskfile.yml**:
```yaml
test:docker:dev:
  desc: "Test Docker development setup"
  cmds:
    - task: docker:down
    - task: docker:clean
    - task: docker:up:all
    - sleep 10
    - curl -f http://localhost:8000/health || exit 1
    - curl -f http://localhost:5173/ || exit 1
    - echo "✓ Docker development setup working"

test:docker:prod:
  desc: "Test Docker production setup"
  cmds:
    - task: docker:build:prod
    - docker compose -f docker-compose.prod.yml up -d
    - sleep 15
    - curl -f http://localhost:8000/health || exit 1
    - curl -f http://localhost:80/ || exit 1
    - docker compose -f docker-compose.prod.yml down
    - echo "✓ Docker production setup working"
```

## Success Criteria

- [ ] Backend hot-reload works when editing source files
- [ ] SSL certificate workarounds removed or properly documented
- [ ] Production Docker images build and run successfully
- [ ] README.md has comprehensive Docker section
- [ ] `.env.production.example` created with all required variables
- [ ] Copilot agent environment properly configured and documented
- [ ] All manual tests pass
- [ ] Documentation is clear and complete

## Non-Goals

- ❌ Kubernetes/orchestration configuration (future work)
- ❌ Multi-architecture builds (works on both amd64 and arm64 by default)
- ❌ Docker registry/publishing (future work)
- ❌ Performance optimization beyond basic best practices

## Files to Modify

1. `backend/Dockerfile.dev` - Fix hot-reload, remove/document SSL workaround
2. `backend/Dockerfile` - Ensure production-ready (no --trusted-host)
3. `README.md` - Add Docker Development section
4. `.env.production.example` - Create with comprehensive docs
5. `.env.example` - Add header indicating "Development"
6. `Taskfile.yml` - Add Docker testing tasks
7. `.github/copilot-instructions.md` - Document required secrets
8. `.github/workflows/copilot-setup-steps.yml` - Consider adding Docker services

## Related References

- PR #47: Docker infrastructure implementation
- Agent Progress Doc: `agent_progress_docs/2026-01-02_00-40-20_dockerize-backend-frontend.md`
- Docker Compose docs: https://docs.docker.com/compose/
- Uvicorn auto-reload: https://www.uvicorn.org/deployment/#development
- GitHub Copilot agent setup: https://docs.github.com/en/copilot/how-tos/use-copilot-agents/coding-agent/customize-the-agent-environment

## Notes for Agent

- Take time to thoroughly test hot-reload solutions
- Production Dockerfile is higher priority than dev convenience features
- Documentation should be beginner-friendly (assume user is new to Docker)
- If SSL issues are hard to solve, it's okay to keep workaround but document why
- Test on a clean checkout if possible to ensure setup instructions work
