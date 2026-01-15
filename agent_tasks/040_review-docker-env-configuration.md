# Task 040: Review Docker Compose Environment Variable Configuration

**Agent**: quality-infra
**Priority**: Medium (enhancement)
**Estimated Effort**: 1-2 hours
**Related**: Task #035 (Dockerize Application) - PR #47 ✅ Reviewed and Approved
**Status**: Ready to start after PR #47 is merged

## Objective

Enhance the Docker Compose configuration (from Task #035/PR #47) to use `env_file` directive for cleaner environment variable management. This is an enhancement to the already-functional Docker implementation.

## Context

**PR #47 Status**: ✅ Reviewed and approved
- Docker implementation is **functional and working**
- Environment variables currently passed individually in docker-compose.yml
- Uses `${ALPHA_VANTAGE_API_KEY:-demo}` syntax for variable substitution
- All CI tests passing

**Enhancement Opportunity**:
The current implementation lists each environment variable individually in the `environment:` section of docker-compose.yml. While this works, using the `env_file:` directive would be cleaner and more maintainable.

**Background**:
- Root `.env` file contains all configuration (database, Redis, Alpha Vantage API key)
- During local development testing, had to manually create symlink: `backend/.env -> ../.env`
- This was a development workaround - Docker setup doesn't have this issue

## Requirements

### 1. Implement env_file Directive

**Current PR #47 Implementation**:
```yaml
services:
  backend:
    environment:
      DATABASE_URL: postgresql+asyncpg://zebu:zebu_dev_password@db:5432/zebu_dev
      POSTGRES_HOST: db
      POSTGRES_PORT: 5432
      # ... 10+ individual env vars listed
      ALPHA_VANTAGE_API_KEY: ${ALPHA_VANTAGE_API_KEY:-demo}
```

**Recommended Enhancement**:
```yaml
services:
  backend:
    env_file:
      - .env  # Load all variables from root .env file
    environment:
      # Only override vars that differ in Docker context
      DATABASE_URL: postgresql+asyncpg://zebu:zebu_dev_password@db:5432/zebu_dev
      REDIS_HOST: redis
      POSTGRES_HOST: db
```

**Benefits**:
- ✅ Automatically loads all .env variables (no need to list individually)
- ✅ Easier to maintain - add new vars to .env without updating docker-compose.yml
- ✅ Cleaner configuration - only Docker-specific overrides in environment section
- ✅ Addresses the manual symlink issue for local development

### 2. Update Development Mode Configuration (Optional)

The current Taskfile.yml `dev:backend` task works but could be enhanced:

**Current** (works fine):
```yaml
dev:backend:
  desc: "Start backend development server"
  dir: "{{.BACKEND_DIR}}"
  cmds:
    - uv run uvicorn zebu.main:app --reload --host 0.0.0.0 --port 8000
```

**Enhancement** (if symlink issues persist):
```yaml
dev:backend:
  desc: "Start backend development server"
  dir: "{{.BACKEND_DIR}}"
  deps:
    - docker:up
  cmds:
    # Auto-create symlink if needed (idempotent)
    - test -L .env || ln -s ../.env .env
    - uv run uvicorn zebu.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Create .env.example Template

Create a template file documenting all environment variables:

**`.env.example`**:
```bash
# Database Configuration
POSTGRES_DB=zebu_dev
POSTGRES_USER=zebu
POSTGRES_PASSWORD=zebu_dev_password
DATABASE_URL=postgresql+asyncpg://zebu:zebu_dev_password@localhost:5432/zebu_dev

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Alpha Vantage API (get your free key: https://www.alphavantage.co/support/#api-key)
ALPHA_VANTAGE_API_KEY=your_api_key_here

# Application Configuration
APP_ENV=development
APP_DEBUG=true
SECRET_KEY=dev_secret_key_change_in_production
```

### 4. Documentation Updates

Update `README.md` with environment setup section:

```markdown
## Environment Setup

1. Copy the environment template:
   ```bash
   cp .env.example .env
   ```

2. Get Alpha Vantage API key (free): https://www.alphavantage.co/support/#api-key

3. Update `.env` with your API key:
   ```
   ALPHA_VANTAGE_API_KEY=YOUR_ACTUAL_KEY_HERE
   ```

4. The default database and Redis settings work for local development.
```
- `APP_ENV` - Environment (development/production)
- `API_PORT` - Override default port 8000

### .env.example Template

```bash
# Database Configuration
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=zebu_dev
POSTGRES_USER=zebu
POSTGRES_PASSWORD=your_secure_password_here

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Application
APP_ENV=development
APP_DEBUG=true
SECRET_KEY=your_secret_key_here  # Generate: python -c "import secrets; print(secrets.token_urlsafe(32))"

# Market Data API
ALPHA_VANTAGE_API_KEY=your_api_key_here  # Get from: https://www.alphavantage.co/support/#api-key

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
```

## Success Criteria

- [ ] Docker Compose properly loads environment variables from root `.env`
- [ ] Backend container has access to all required env vars
- [ ] Frontend container receives necessary configuration
- [ ] Development mode works without manual symlink creation
- [ ] `.env.example` file created and documented
- [ ] Environment validation script works
- [ ] Documentation updated (README.md, comments in docker-compose.yml)
- [ ] Both `docker compose up` and `task dev:backend` work correctly
- [ ] No sensitive values committed to git
- [ ] Setup guide tested on fresh clone

## Testing Steps

1. **Test Docker Mode**:
   ```bash
   git clone <repo>
   cp .env.example .env
   # Edit .env with real values
   docker compose up -d
   curl http://localhost:8000/health
   curl http://localhost:5173/
   ```

2. **Test Development Mode**:
   ```bash
   task dev:backend  # Should not require manual symlink
   # Verify backend can access ALPHA_VANTAGE_API_KEY
   ```

3. **Test Fresh Setup**:
## Success Criteria

### Must Have

1. ✅ **env_file Directive Implemented**: docker-compose.yml uses `env_file: [.env]` for backend service
2. ✅ **.env.example Created**: Template file with all required variables documented
3. ✅ **README.md Updated**: Environment setup instructions added
4. ✅ **Docker Testing**: `docker compose up` loads .env variables correctly
5. ✅ **Local Development**: `task dev:backend` works without manual symlink creation

### Nice to Have

- 🎯 Auto-create symlink in dev:backend task if needed (idempotent check)
- 🎯 Validation script (scripts/validate-env.sh) for environment checking
- 🎯 Comments in docker-compose.yml explaining env strategy
- 🎯 Production docker-compose.prod.yml also uses env_file approach

## Testing Checklist

1. **Fresh Checkout Test**:
   ```bash
   git clone <repo>
   cp .env.example .env
   # Edit .env with actual API key
   task setup
   docker compose up
   # Backend should start without errors
   # API calls should work (not using demo key)
   ```

2. **Development Mode Test**:
   ```bash
   rm -rf backend/.env  # Remove any existing symlink
   task dev:backend
   # Should work without manual symlink intervention
   ```

3. **Environment Variable Validation**:
   ```bash
   # Start Docker services
   docker compose up -d backend

   # Verify env vars loaded
   docker compose exec backend printenv | grep ALPHA_VANTAGE_API_KEY
   # Should show actual API key, not "demo"
   ```

## References

- ✅ **PR #47**: Docker implementation (reviewed and approved)
- `agent_progress_docs/2026-01-02_00-40-20_dockerize-backend-frontend.md` - Docker task documentation
- `orchestrator_procedures/playwright_e2e_testing.md` - Testing session that discovered the symlink issue
- Current root `.env` file in project

## Implementation Notes

**Priority**: This is an enhancement, not a blocker
- Current PR #47 implementation works functionally
- This task improves maintainability and developer experience
- Can be implemented as a follow-up PR after #47 is merged

**Scope**:
- Focus on docker-compose.yml env_file directive (primary goal)
- Create .env.example for documentation (secondary)
- README update for onboarding clarity (tertiary)
- Development task enhancement is optional (current workaround is acceptable)

**Coordination**:
- Wait for PR #47 to be merged before starting
- This is a refinement of working code, not a fix
