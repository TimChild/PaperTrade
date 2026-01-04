# ADR 004: Configuration Management (TOML-Based)

**Status**: Approved
**Date**: 2025-12-28
**Deciders**: Architecture Team
**Context**: Phase 2 Market Data Integration

## Context

Phase 2 introduces new configuration needs:
- **Alpha Vantage API**: API key, base URL, timeout settings
- **Rate Limiting**: Calls per minute/day, tier selection
- **Caching**: Redis URL, TTL values
- **Scheduler**: Cron expressions, job settings
- **Feature Flags**: Enable/disable Phase 2b features

### Current State (Phase 1)

**Backend**:
- `.env` file for secrets (DATABASE_URL, SECRET_KEY)
- Hard-coded defaults in code
- No centralized configuration

**Frontend**:
- `.env` file for Vite variables (VITE_API_URL)
- Hard-coded feature flags

### Problems with Current Approach

1. **Scattered Configuration**: Settings spread across .env, code, and deployment scripts
2. **No Validation**: Typos and invalid values only caught at runtime
3. **Poor Discoverability**: Developers don't know what's configurable
4. **No Type Safety**: .env values are strings (need manual parsing/validation)
5. **No Environment Defaults**: Every developer manually creates .env

## Decision

Implement **TOML-based configuration** with **Pydantic Settings** (backend) and **TypeScript validation** (frontend).

### Configuration Hierarchy

```
1. Default values (in TOML file, committed to repo)
2. Environment-specific overrides (config.dev.toml, config.prod.toml)
3. Environment variables (.env, not committed)
4. Command-line args (highest priority, for testing)
```

### File Structure

```
backend/
├── config.toml              # Default configuration (committed)
├── config.example.toml      # Template for new developers
├── config.dev.toml          # Development overrides (optional, gitignored)
├── config.prod.toml         # Production config (gitignored, managed by ops)
└── .env                     # Secrets only (API keys, DB passwords)

frontend/
├── config.toml              # Default configuration (committed)
├── config.example.toml      # Template for new developers
└── .env                     # Build-time variables (API URL, feature flags)
```

## Backend Configuration (Python + Pydantic)

### Config File Structure (backend/config.toml)

```toml
# PaperTrade Backend Configuration
# See docs/configuration.md for full documentation

[app]
environment = "development"  # "development", "staging", "production"
debug = true
log_level = "INFO"

[database]
# Use environment variable for sensitive connection string
url = "${DATABASE_URL}"
pool_size = 10
pool_timeout = 30
echo_sql = false  # Log all SQL queries (debug only)

[market_data]
# Provider selection
provider = "alpha_vantage"  # Future: "finnhub", "polygon"

# Alpha Vantage settings
[market_data.alpha_vantage]
api_key = "${ALPHA_VANTAGE_API_KEY}"  # From .env
base_url = "https://www.alphavantage.co/query"
timeout_seconds = 5
retry_attempts = 3
retry_delay_seconds = 1

# Rate limiting
[market_data.rate_limit]
tier = "free"  # "free" or "premium"

# Free tier limits
free_calls_per_minute = 5
free_calls_per_day = 500

# Premium tier limits
premium_calls_per_minute = 75
premium_calls_per_day = 100000

# Active limits (based on tier)
calls_per_minute = 5
calls_per_day = 500

# Safety margins
minute_reserve = 1
day_reserve = 50

[cache]
# Redis configuration
redis_url = "redis://localhost:6379"
redis_db = 0
redis_password = "${REDIS_PASSWORD}"  # From .env (optional)

# Price cache settings
price_ttl_seconds = 3600  # 1 hour
price_key_prefix = "papertrade:price"

# Rate limiter cache
ratelimit_key_prefix = "papertrade:ratelimit"

[scheduler]
# Enable/disable background jobs
enabled = true

# Daily refresh schedule (cron expression)
refresh_cron = "0 0 * * *"  # Midnight UTC

# Job persistence
jobstore = "postgresql"
jobstore_url = "${DATABASE_URL}"
timezone = "UTC"
max_instances = 1

[scheduler.refresh]
# Refresh job settings
sources = ["portfolio", "common", "recent"]
max_age_hours = 24
batch_size = 5
batch_delay_seconds = 60
max_error_rate = 0.15

[logging]
# Log configuration
format = "json"  # "json" or "text"
level = "INFO"
file = "/var/log/papertrade/app.log"
max_bytes = 10485760  # 10 MB
backup_count = 5

[api]
# FastAPI settings
title = "PaperTrade API"
version = "1.0.0"
cors_origins = ["http://localhost:5173", "http://localhost:3000"]
```

### Pydantic Settings Class

**Implementation Location**: `backend/src/papertrade/infrastructure/config.py`

**Key Features**:
- Type-safe configuration (validated at startup)
- Environment variable interpolation (`${VAR_NAME}`)
- Nested configuration (sections map to nested classes)
- Validation errors with helpful messages

**Example Usage**:

```python
from papertrade.infrastructure.config import settings

# Access configuration
api_key = settings.market_data.alpha_vantage.api_key
calls_per_min = settings.market_data.rate_limit.calls_per_minute
redis_url = settings.cache.redis_url
```

**Validation**:
- API key format (not empty, alphanumeric)
- Rate limits (positive integers)
- URLs (valid format)
- Cron expressions (valid syntax)

### Environment Variable Overrides

**.env file** (secrets only, never committed):

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/papertrade

# Market Data
ALPHA_VANTAGE_API_KEY=your_api_key_here

# Redis (optional, has defaults)
REDIS_PASSWORD=optional_password

# Environment
PAPERTRADE_ENV=development  # development, staging, production
```

**Loading Priority**:
1. Command-line args (for testing)
2. Environment variables (.env file)
3. config.{env}.toml (if exists)
4. config.toml (defaults)

### Configuration Validation

**Startup Checks**:

When application starts, validate:
- ✅ All required environment variables set
- ✅ API key not empty or placeholder
- ✅ Database URL format valid
- ✅ Redis URL reachable (warn if not)
- ✅ Rate limits within reasonable range

**Example Error Message**:

```
Configuration Error: market_data.alpha_vantage.api_key

  ALPHA_VANTAGE_API_KEY is required but not set.

  To fix:
  1. Copy .env.example to .env
  2. Set ALPHA_VANTAGE_API_KEY=your_actual_key
  3. Get a key from: https://www.alphavantage.co/support/#api-key

  Current value: None
  Expected: Non-empty alphanumeric string
```

## Frontend Configuration (TypeScript + Vite)

### Config File Structure (frontend/config.toml)

```toml
# PaperTrade Frontend Configuration

[app]
environment = "development"
name = "PaperTrade"
version = "1.0.0"

[api]
# Backend API base URL
base_url = "http://localhost:8000/api/v1"
timeout_ms = 10000

[features]
# Feature flags (Phase 2+)
enable_real_prices = true      # Phase 2a
enable_price_charts = false    # Phase 2b
enable_backtesting = false     # Phase 3
enable_automation = false      # Phase 5

[cache]
# Frontend caching settings
price_update_interval_ms = 60000  # 1 minute
query_stale_time_ms = 300000      # 5 minutes
query_cache_time_ms = 600000      # 10 minutes

[ui]
# UI preferences
default_currency = "USD"
date_format = "YYYY-MM-DD"
theme = "light"  # "light", "dark", "auto"
```

### TypeScript Validation

**Challenge**: TypeScript has no native TOML parser with Pydantic-like validation.

**Solution**: Use **zod** for runtime validation + type generation.

**Implementation Location**: `frontend/src/config/index.ts`

**Dependencies**:
- `smol-toml` - TOML parser (lightweight)
- `zod` - Schema validation

**Schema Definition** (structured specification):

Define Zod schema:
- Schema mirrors TOML structure
- Types inferred from schema (type-safe access)
- Runtime validation on config load
- Helpful error messages

**Example Usage**:

```typescript
import { config } from './config';

// Type-safe access
const apiUrl = config.api.base_url;
const enableCharts = config.features.enable_price_charts;
```

**Build-Time vs Runtime**:

- **Build-Time**: Vite environment variables (`VITE_API_URL`)
  - For values that change per deployment
  - Baked into bundle (not changeable without rebuild)

- **Runtime**: TOML config (loaded dynamically)
  - For feature flags and preferences
  - Can change without rebuild

### Environment-Specific Configs

**Development** (frontend/config.dev.toml):
```toml
[api]
base_url = "http://localhost:8000/api/v1"

[features]
enable_real_prices = true
enable_price_charts = true  # Enable in dev for testing
```

**Production** (frontend/config.prod.toml):
```toml
[api]
base_url = "${VITE_API_URL}"  # From build environment

[features]
enable_real_prices = true
enable_price_charts = false  # Controlled rollout
```

## Alternatives Considered

### Alternative 1: JSON Configuration

**Pros**:
- Native JavaScript support
- No parsing library needed

**Cons**:
- ❌ No comments (less readable)
- ❌ Awkward for nested config
- ❌ Trailing commas cause errors

**Decision**: **Rejected** - TOML more readable

### Alternative 2: YAML Configuration

**Pros**:
- Human-readable
- Supports complex structures

**Cons**:
- ❌ Indentation-sensitive (error-prone)
- ❌ Spec too complex (multiple ways to do same thing)
- ❌ Security issues (arbitrary code execution)

**Decision**: **Rejected** - TOML safer and simpler

### Alternative 3: Python File (settings.py)

**Pros**:
- No parsing needed (just import)
- Can use Python logic

**Cons**:
- ❌ Not data (code execution risk)
- ❌ Hard to override in deployment
- ❌ No frontend equivalent

**Decision**: **Rejected** - Config should be data, not code

### Alternative 4: Environment Variables Only

**Pros**:
- 12-factor app pattern
- No files needed
- Works everywhere

**Cons**:
- ❌ Poor discoverability (what vars exist?)
- ❌ No structure (flat namespace)
- ❌ No type safety (all strings)
- ❌ Awkward for nested config

**Decision**: **Rejected** - .env for secrets, TOML for config

### Alternative 5: Database Configuration

**Pros**:
- Centralized (multiple instances share config)
- Can update without redeploy

**Cons**:
- ❌ Chicken-and-egg (how to connect to database?)
- ❌ Slower to load
- ❌ Harder to version control

**Decision**: **Rejected** - File-based simpler for Phase 2

## Rationale for Chosen Approach

### Why TOML?

1. **Readable**: Designed for config files (better than JSON/YAML)
2. **Comments**: Inline documentation
3. **Sections**: Nested structure maps to classes
4. **Type Safety**: Pydantic validates at startup
5. **Standard**: Used by Rust (Cargo.toml), Python (pyproject.toml)

### Why Pydantic Settings?

1. **Type Safety**: Catch config errors at startup (not runtime)
2. **Environment Variables**: Automatic ${VAR} interpolation
3. **Validation**: Custom validators (e.g., URL format)
4. **IDE Support**: Type hints = autocomplete
5. **Documentation**: Self-documenting (types in schema)

### Why Separate .env and config.toml?

| File | Purpose | Committed? | Contains |
|------|---------|------------|----------|
| **config.toml** | Defaults and structure | ✅ Yes | Non-sensitive settings |
| **.env** | Secrets and overrides | ❌ No | API keys, passwords |
| **config.{env}.toml** | Environment-specific | ❌ No | Per-environment tweaks |

**Rationale**:
- Secrets never committed
- Defaults always available (onboarding friendly)
- Environment overrides are optional (production only)

## Implementation Guide

### Backend Setup

**Step 1**: Install dependencies
```bash
pip install pydantic-settings tomli
```

**Step 2**: Create config schema (see interfaces.md for structure)

**Step 3**: Load configuration at startup
```python
# main.py
from papertrade.infrastructure.config import settings

# Validate config early (fail fast)
settings.validate()

# Log configuration (mask secrets)
logger.info(f"Loaded config: {settings.to_safe_dict()}")
```

**Step 4**: Use in dependency injection
```python
# FastAPI dependency
def get_market_data_adapter():
    return AlphaVantageAdapter(
        api_key=settings.market_data.alpha_vantage.api_key,
        base_url=settings.market_data.alpha_vantage.base_url,
        # ...
    )
```

### Frontend Setup

**Step 1**: Install dependencies
```bash
npm install smol-toml zod
```

**Step 2**: Create config schema with Zod (see interfaces.md)

**Step 3**: Load config at app initialization
```typescript
// main.tsx
import { loadConfig } from './config';

const config = await loadConfig();
// Validation errors throw here (fail fast)
```

**Step 4**: Use in API client
```typescript
// api/client.ts
import { config } from './config';

const apiClient = axios.create({
  baseURL: config.api.base_url,
  timeout: config.api.timeout_ms,
});
```

## Testing Strategy

### Unit Tests

Test configuration loading:
- Valid config file loads successfully
- Invalid config raises validation error
- Environment variable override works
- Default values used when not specified

### Integration Tests

Test with different configs:
- Development config (local database, debug on)
- Production config (cloud database, debug off)
- Minimal config (only required fields)

### CI/CD Tests

Verify:
- `.env.example` has all required variables
- `config.example.toml` matches actual config structure
- No secrets in committed files (git-secrets scan)

## Documentation

### For Developers

**README.md** section:
```markdown
## Configuration

1. Copy example files:
   ```bash
   cp backend/.env.example backend/.env
   cp backend/config.example.toml backend/config.toml
   ```

2. Edit `.env` with your secrets:
   - Get Alpha Vantage API key: https://www.alphavantage.co/support/#api-key
   - Set DATABASE_URL for your local PostgreSQL

3. (Optional) Customize `config.toml` for local development

4. Start application:
   ```bash
   task dev
   ```
```

### For Operations

**docs/configuration.md**:
- Full reference of all config options
- Validation rules and constraints
- Environment-specific examples
- Troubleshooting common issues

## Consequences

### Positive

- ✅ **Type Safety**: Configuration errors caught at startup
- ✅ **Discoverability**: config.toml shows all options
- ✅ **Onboarding**: .env.example guides new developers
- ✅ **Testability**: Easy to test with different configs
- ✅ **Observability**: Can log configuration (mask secrets)

### Negative

- ⚠️ **Learning Curve**: Developers must learn TOML syntax
- ⚠️ **File Proliferation**: config.toml + .env + config.{env}.toml
- ⚠️ **Frontend Complexity**: Zod validation adds bundle size

### Neutral

- 🔄 **Migration**: Need to move hard-coded values to config
- 🔄 **Maintenance**: Keep example files in sync

## Migration Plan

### Phase 2a (Week 1)

1. Create `backend/config.toml` with market data settings
2. Implement Pydantic Settings schema
3. Update `.env.example` with API key template
4. Move hard-coded URLs to config

### Phase 2b (Week 2)

1. Create `frontend/config.toml` with feature flags
2. Implement Zod validation
3. Document configuration in README
4. Add config validation to CI pipeline

## Future Enhancements

### Phase 3+

- **Dynamic Reload**: Reload config without restart (for feature flags)
- **Admin UI**: Edit configuration via web interface
- **Config Versioning**: Track config changes (audit log)
- **Encrypted Secrets**: Use HashiCorp Vault or AWS Secrets Manager

## References

- [TOML Specification](https://toml.io/)
- [Pydantic Settings Documentation](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [Zod Documentation](https://zod.dev/)
- [12-Factor App: Config](https://12factor.net/config)
- [smol-toml (TypeScript)](https://github.com/squirrelchat/smol-toml)
