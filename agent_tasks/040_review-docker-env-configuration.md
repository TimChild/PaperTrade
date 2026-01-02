# Task 040: Review Docker Compose Environment Variable Configuration

**Agent**: quality-infra
**Priority**: High
**Estimated Effort**: 2-3 hours
**Related**: Task #035 (Dockerize Application)

## Objective

Review and update the Docker Compose configuration (from Task #035) to ensure proper environment variable loading for both development and production scenarios. Address the issue where the backend couldn't access the `.env` file until a symlink was manually created.

## Context

**Current Situation**:
- Root `.env` file contains all configuration (database, Redis, Alpha Vantage API key)
- Backend requires access to environment variables to function
- During local development testing, had to manually create symlink: `backend/.env -> ../.env`
- Task #035 is implementing Docker Compose setup for full stack

**Problem**:
The backend needs environment variables (especially `ALPHA_VANTAGE_API_KEY`) to be available, but:
1. Development mode: Backend runs via `task dev:backend` which needs access to `.env`
2. Docker mode: Backend runs in container and needs env vars passed correctly
3. Current setup required manual symlink creation, which isn't ideal

## Requirements

### 1. Review Task #035 Docker Implementation

Once Task #035 is complete, review the Docker Compose configuration to ensure:

- Environment variables are properly loaded from root `.env` file
- Backend container has access to all required env vars
- Frontend container receives necessary env vars (API URL, etc.)
- No manual symlink creation required
- Both development and production modes work

### 2. Environment Variable Strategy

Implement one of these approaches (or hybrid):

**Option A: Direct Environment Variables in docker-compose.yml**
```yaml
services:
  backend:
    environment:
      DATABASE_URL: ${DATABASE_URL}
      REDIS_URL: ${REDIS_URL}
      ALPHA_VANTAGE_API_KEY: ${ALPHA_VANTAGE_API_KEY}
    env_file:
      - .env  # Load from root
```

**Option B: Volume Mount .env File**
```yaml
services:
  backend:
    volumes:
      - ./.env:/app/.env:ro  # Read-only mount
```

**Option C: Explicit env_file Reference**
```yaml
services:
  backend:
    env_file:
      - .env
    # Docker Compose automatically loads .env from project root
```

### 3. Development Mode Configuration

For local development (non-Docker):

**Current Workaround** (manual symlink):
```bash
cd backend && ln -s ../.env .env
```

**Better Solution** - Update Taskfile to handle this:
```yaml
dev:backend:
  desc: "Start backend development server"
  dir: "{{.BACKEND_DIR}}"
  deps:
    - docker:up
  cmds:
    # Ensure .env access (create symlink if needed)
    - test -f .env || ln -s ../.env .env
    - 'echo "Starting backend server on http://localhost:8000"'
    - uv run uvicorn papertrade.main:app --reload --host 0.0.0.0 --port 8000
```

Or use `dotenv` in the command:
```yaml
dev:backend:
  desc: "Start backend development server"
  dir: "{{.PROJECT_ROOT}}"  # Run from root to access .env
  deps:
    - docker:up
  cmds:
    - 'cd backend && uv run uvicorn papertrade.main:app --reload --host 0.0.0.0 --port 8000'
  env:
    # Explicitly pass env vars from .env
    ALPHA_VANTAGE_API_KEY: ${ALPHA_VANTAGE_API_KEY}
    DATABASE_URL: ${DATABASE_URL}
    # ... other vars
```

### 4. Documentation Updates

Update the following files:

1. **`README.md`**:
   - Document how environment variables are loaded
   - Explain `.env` file structure
   - Provide example `.env.example` file

2. **`backend/README.md`** (if exists):
   - Explain backend-specific env var requirements
   - Document development setup

3. **`docker-compose.yml`** and **`docker-compose.dev.yml`**:
   - Add comments explaining env var loading strategy
   - Document which vars are required vs optional

4. **`.env.example`**:
   - Create if doesn't exist
   - Include all required variables with placeholder values
   - Add comments explaining each variable

### 5. Validation Script

Create a script to validate environment setup:

**`scripts/validate-env.sh`**:
```bash
#!/bin/bash
# Validate environment configuration

echo "Validating environment setup..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ .env file not found in project root"
    echo "   Copy .env.example to .env and configure"
    exit 1
fi

# Check required variables
REQUIRED_VARS=("POSTGRES_PASSWORD" "ALPHA_VANTAGE_API_KEY" "SECRET_KEY")

for var in "${REQUIRED_VARS[@]}"; do
    if ! grep -q "^${var}=" .env; then
        echo "❌ Missing required variable: $var"
        exit 1
    fi
done

# Check for placeholder values
if grep -q "your_api_key_here" .env; then
    echo "⚠️  Warning: .env contains placeholder values"
fi

# Test database connection
if ! docker ps | grep -q papertrade-postgres; then
    echo "⚠️  Warning: PostgreSQL container not running"
fi

echo "✅ Environment validation passed"
```

## Technical Specifications

### Files to Review/Modify

From Task #035 output:
1. **`docker-compose.yml`** - Production configuration
2. **`docker-compose.dev.yml`** (if created) - Development overrides
3. **`backend/Dockerfile`** and **`backend/Dockerfile.dev`**
4. **`Taskfile.yml`** - Update dev:backend task

New files to create:
1. **`.env.example`** - Template for environment variables
2. **`scripts/validate-env.sh`** - Environment validation script
3. **`docs/ENVIRONMENT_SETUP.md`** - Detailed environment docs (optional)

### Environment Variables to Document

**Required**:
- `ALPHA_VANTAGE_API_KEY` - API key for market data (get from https://www.alphavantage.co/support/#api-key)
- `POSTGRES_PASSWORD` - Database password
- `SECRET_KEY` - Application secret for sessions/JWT

**Optional**:
- `DATABASE_URL` - Override default database connection
- `REDIS_URL` - Override default Redis connection
- `APP_ENV` - Environment (development/production)
- `API_PORT` - Override default port 8000

### .env.example Template

```bash
# Database Configuration
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=papertrade_dev
POSTGRES_USER=papertrade
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
   ```bash
   rm -rf backend/.env  # Remove any existing symlink
   task dev:backend
   # Should work without manual intervention
   ```

4. **Test Environment Validation**:
   ```bash
   ./scripts/validate-env.sh
   # Should pass with valid .env
   # Should fail with missing .env or missing vars
   ```

## References

- Task #035: Dockerize Backend and Frontend Applications
- Current root `.env` file
- `Taskfile.yml` - Current dev:backend task
- `orchestrator_procedures/playwright_e2e_testing.md` - Testing session that discovered the issue

## Notes

- This task depends on Task #035 being completed first
- May need to coordinate with quality-infra agent working on Task #035
- Consider creating separate docker-compose files for dev vs prod
- Ensure `.env` is in `.gitignore` (already is, but verify)
- Backend may need `python-dotenv` package to load .env files (check if already included)
