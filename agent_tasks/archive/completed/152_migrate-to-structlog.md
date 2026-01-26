# Task 152: Migrate to Structlog for Structured Logging

**Agent**: backend-swe
**Priority**: Medium
**Type**: Infrastructure Enhancement
**Depends On**: Task 151 (cache completeness fix)
**Related**: PR #137 (observability improvements)

## Objective

Migrate from Python's standard `logging` library to `structlog` for better structured logging capabilities. This enhances our observability infrastructure with incremental context binding, JSON output, and better performance.

## Context

**Current State** (after PR #137):
- Using standard library `logging` with `extra={}` dicts for structured data
- Logs are human-readable but harder to parse programmatically
- Context must be repeated in every log call
- No request correlation IDs

**Desired State** (with structlog):
- JSON-formatted logs for machine parsing (Loki/Grafana integration)
- Incremental context binding (attach `ticker` once, use in multiple statements)
- Automatic request correlation IDs
- Better performance (lazy evaluation)
- Standardized log format across all services

**Why Now**:
- Observability infrastructure is in place (PR #137)
- Logging patterns are established (good time to standardize)
- Prepares us for Grafana Cloud integration (Task 153 - to be created)

## Requirements

### 1. Install and Configure Structlog

**Dependencies**:
```toml
# Add to pyproject.toml
[project.dependencies]
structlog = "^24.1.0"
python-json-logger = "^2.0.7"  # For JSON formatting
```

**Configuration**:
```python
# backend/src/zebu/infrastructure/logging.py (new file)

import logging
import structlog
from structlog.processors import (
    add_log_level,
    TimeStamper,
    StackInfoRenderer,
    format_exc_info,
    UnicodeDecoder,
    ExceptionPrettyPrinter,
    CallsiteParameterAdder,
)
from structlog.stdlib import (
    ProcessorFormatter,
    add_logger_name,
    BoundLogger,
)


def setup_structlog(
    log_level: str = "INFO",
    json_output: bool = True,
) -> None:
    """Configure structlog for the application.

    Args:
        log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR)
        json_output: If True, output JSON lines. If False, human-readable
    """
    # Shared processors for all loggers
    shared_processors = [
        add_log_level,  # Add log level to event dict
        add_logger_name,  # Add logger name to event dict
        TimeStamper(fmt="iso", utc=True),  # Add timestamp in ISO format
        StackInfoRenderer(),  # Render stack info if available
        format_exc_info,  # Format exceptions
        UnicodeDecoder(),  # Decode unicode
        CallsiteParameterAdder(
            parameters=[
                CallsiteParameter.FILENAME,
                CallsiteParameter.FUNC_NAME,
                CallsiteParameter.LINENO,
            ]
        ),  # Add call site info
    ]

    if json_output:
        # Production: JSON output for machine parsing
        from pythonjsonlogger import jsonlogger

        handler = logging.StreamHandler()
        handler.setFormatter(jsonlogger.JsonFormatter())

        structlog.configure(
            processors=shared_processors + [
                structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
            ],
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )
    else:
        # Development: Human-readable colored output
        structlog.configure(
            processors=shared_processors + [
                ExceptionPrettyPrinter(),  # Pretty print exceptions
                structlog.dev.ConsoleRenderer(),  # Colored console output
            ],
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )

    # Configure stdlib logging
    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, log_level.upper()),
        handlers=[handler] if json_output else None,
    )
```

### 2. Initialize Logging in Application

**File**: `backend/src/zebu/main.py`

```python
from zebu.infrastructure.logging import setup_structlog
from zebu.infrastructure.config import settings

# At application startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Setup logging
    setup_structlog(
        log_level=settings.log_level,
        json_output=settings.environment == "production",
    )

    logger = structlog.get_logger(__name__)
    logger.info(
        "Application starting",
        environment=settings.environment,
        log_level=settings.log_level,
    )

    # ... (existing startup code)
    yield

    logger.info("Application shutting down")
```

### 3. Add Request Context Middleware

**File**: `backend/src/zebu/infrastructure/middleware/logging_middleware.py` (new file)

```python
import uuid
from typing import Callable
import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class LoggingContextMiddleware(BaseHTTPMiddleware):
    """Add request correlation ID and context to all logs."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ) -> Response:
        # Generate correlation ID
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())

        # Bind context for all logs in this request
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            correlation_id=correlation_id,
            request_path=request.url.path,
            request_method=request.method,
            client_ip=request.client.host if request.client else None,
        )

        logger = structlog.get_logger(__name__)
        logger.info(
            "Request started",
            path=request.url.path,
            method=request.method,
        )

        # Process request
        response = await call_next(request)

        # Add correlation ID to response headers
        response.headers["X-Correlation-ID"] = correlation_id

        logger.info(
            "Request completed",
            status_code=response.status_code,
        )

        return response
```

**Register middleware**:
```python
# backend/src/zebu/main.py
from zebu.infrastructure.middleware.logging_middleware import LoggingContextMiddleware

app = FastAPI(...)
app.add_middleware(LoggingContextMiddleware)
```

### 4. Migrate Existing Loggers

**Pattern**:
```python
# OLD: Standard logging with extra={}
import logging
logger = logging.getLogger(__name__)

logger.info(
    "Price history request",
    extra={
        "ticker": ticker.symbol,
        "start": start.isoformat(),
        "end": end.isoformat(),
    }
)

# NEW: Structlog with bound context
import structlog

logger = structlog.get_logger(__name__)

# Bind context once (reused in all subsequent logs)
log = logger.bind(
    ticker=ticker.symbol,
    start=start.isoformat(),
    end=end.isoformat(),
)

log.info("Price history request")  # Shorter, cleaner!

# Later in same function
log.info("Fetching from API")  # ticker/start/end automatically included!
log.info("Returning cached data", cached_points=len(history))
```

**Migration Priority** (start with critical paths):

1. **Alpha Vantage Adapter** (`alpha_vantage_adapter.py`):
   ```python
   # Bind ticker context at start of get_price_history
   log = structlog.get_logger(__name__).bind(
       ticker=ticker.symbol,
       interval=interval,
   )

   log.info("Price history request", start=start.isoformat(), end=end.isoformat())
   # ... (cache query)
   log.info("Cache query result", cached_points=len(history))
   # ... (API fetch)
   log.info("Fetching from Alpha Vantage API")
   ```

2. **Price Repository** (`price_repository.py`)
3. **API Endpoints** (`prices.py`)
4. **Backfill Script** (`backfill_prices.py`)

### 5. Testing

**No new tests required** - logging is infrastructure, behavior unchanged.

**Validation**:
- Run application and verify JSON output in production mode
- Run application and verify colored output in development mode
- Check that correlation IDs appear in all logs for a single request
- Verify bound context persists across multiple log statements

## Success Criteria

1. ✅ Structlog installed and configured
2. ✅ Application startup logs in JSON format (production) or colored (dev)
3. ✅ Request correlation IDs added to all logs
4. ✅ Middleware binds request context automatically
5. ✅ Critical paths migrated (Alpha Vantage adapter, repository, API endpoints)
6. ✅ Development experience improved (less code duplication)
7. ✅ CI passes (no test failures from logging changes)

## Quality Standards

### Architecture
- ✅ Logging infrastructure in `infrastructure/` layer
- ✅ Middleware in `infrastructure/middleware/`
- ✅ No domain/application layer dependencies on logging library

### Code Quality
- ✅ Type hints for all logging config functions
- ✅ Docstrings for `setup_structlog()` and middleware
- ✅ Settings for log level and output format

### Best Practices
- ✅ JSON output in production (Loki/Grafana integration ready)
- ✅ Human-readable output in development (better DX)
- ✅ Correlation IDs for request tracing
- ✅ Incremental context binding (reduce duplication)
- ✅ Lazy evaluation (performance)

## Migration Strategy

### Phase 1: Infrastructure (this task)
1. Install structlog
2. Configure logging setup
3. Add middleware for correlation IDs
4. Migrate critical paths (Alpha Vantage, price repository, API endpoints)

### Phase 2: Complete Migration (follow-up)
- Migrate remaining adapters
- Migrate use cases
- Update documentation

### Phase 3: Grafana Integration (Task 153)
- Configure Loki agent to ship JSON logs
- Create Grafana dashboards
- Set up alerts

## Example Output

**Development Mode** (human-readable):
```
2026-01-17T20:30:45.123Z [info     ] Application starting           environment=development log_level=INFO
2026-01-17T20:30:45.456Z [info     ] Request started                correlation_id=abc-123 method=GET path=/api/v1/prices/AAPL/history
2026-01-17T20:30:45.500Z [info     ] Price history request          ticker=AAPL start=2026-01-10T00:00:00Z end=2026-01-17T23:59:59Z
2026-01-17T20:30:45.520Z [info     ] Cache query result             ticker=AAPL cached_points=3
2026-01-17T20:30:45.521Z [info     ] Cached data incomplete         ticker=AAPL reason=missing_early_dates
2026-01-17T20:30:45.600Z [info     ] Fetching from Alpha Vantage    ticker=AAPL
2026-01-17T20:30:46.200Z [info     ] Request completed              correlation_id=abc-123 status_code=200
```

**Production Mode** (JSON):
```json
{"event": "Application starting", "level": "info", "timestamp": "2026-01-17T20:30:45.123Z", "environment": "production"}
{"event": "Request started", "level": "info", "timestamp": "2026-01-17T20:30:45.456Z", "correlation_id": "abc-123", "method": "GET", "path": "/api/v1/prices/AAPL/history"}
{"event": "Price history request", "level": "info", "timestamp": "2026-01-17T20:30:45.500Z", "ticker": "AAPL", "start": "2026-01-10T00:00:00Z", "end": "2026-01-17T23:59:59Z"}
{"event": "Cache query result", "level": "info", "timestamp": "2026-01-17T20:30:45.520Z", "ticker": "AAPL", "cached_points": 3}
```

## References

- **Structlog Docs**: https://www.structlog.org/en/stable/
- **Best Practices**: https://www.structlog.org/en/stable/standard-library.html
- **FastAPI Integration**: https://www.structlog.org/en/stable/frameworks.html#fastapi

## Out of Scope

- ❌ Grafana/Loki integration (separate task 153)
- ❌ Log aggregation infrastructure
- ❌ Metrics (use Prometheus, not logs)
- ❌ Migrating every single log statement (focus on critical paths)

## Estimated Effort

- Configuration: 2-3 hours
- Middleware: 1-2 hours
- Migration (critical paths): 3-4 hours
- Validation: 1 hour
- **Total**: ~7-10 hours

## Notes

- Keep migration incremental - don't try to migrate everything at once
- Test in development mode first (colored output is easier to debug)
- JSON output prepares us for Grafana Cloud integration
- Correlation IDs are essential for tracing requests across services
