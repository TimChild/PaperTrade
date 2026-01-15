"""Debug endpoint for runtime environment information.

Provides diagnostic information about the runtime environment,
configuration, and service status. Useful for troubleshooting
deployment and configuration issues.

Security: This endpoint redacts sensitive information (API keys,
passwords) and only shows safe metadata like key prefixes and lengths.
"""

import os
import sys
from datetime import UTC, datetime
from typing import Any

import fastapi
from redis.asyncio import Redis
from sqlmodel import select

from zebu.infrastructure.database import SessionDep, engine

router = fastapi.APIRouter(prefix="/debug", tags=["debug"])


def _redact_api_key(key: str | None) -> dict[str, Any]:
    """Safely redact an API key, showing only metadata.

    Args:
        key: The API key to redact (or None if not set)

    Returns:
        Dictionary with safe metadata about the key
    """
    if not key or key in ("your_api_key_here", ""):
        return {"present": False}

    # Show first 8 characters for longer keys, 4 for shorter
    prefix_len = 8 if len(key) >= 8 else min(4, len(key))
    prefix = key[:prefix_len]

    return {
        "present": True,
        "prefix": prefix,
        "length": len(key),
    }


def _get_environment_info() -> dict[str, Any]:
    """Get environment and runtime information.

    Returns:
        Dictionary with environment metadata
    """
    import fastapi

    return {
        "environment": os.getenv("APP_ENV", "unknown"),
        "python_version": sys.version.split()[0],
        "fastapi_version": fastapi.__version__,
    }


async def _get_database_status(session: SessionDep) -> dict[str, Any]:
    """Get database connection status.

    Args:
        session: Database session

    Returns:
        Dictionary with database status
    """
    try:
        # Try to execute a simple query to verify connection
        # Use SQLModel select with literal 1
        stmt = select(1)  # type: ignore[arg-type]  # select(1) is valid for testing connection
        await session.exec(stmt)
        connected = True
    except Exception:
        connected = False

    # Get database URL (redact password)
    db_url = str(engine.url)
    if "@" in db_url:
        # Remove password from URL: user:password@host -> user:***@host
        parts = db_url.split("@")
        if ":" in parts[0]:
            user_part = parts[0].split(":")[0]
            db_url = f"{user_part}:***@{parts[1]}"

    # Get pool size - it's a property/method depending on pool type
    pool_size = 0
    try:
        if hasattr(engine.pool, "size"):
            pool_size_val = engine.pool.size  # type: ignore[attr-defined]
            # size() is callable in some pool types
            pool_size = pool_size_val() if callable(pool_size_val) else pool_size_val
    except Exception:
        pool_size = 0

    return {
        "connected": connected,
        "url": db_url,
        "pool_size": pool_size,
    }


async def _get_redis_status() -> dict[str, Any]:
    """Get Redis connection status.

    Returns:
        Dictionary with Redis status
    """
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    try:
        # Try to connect to Redis
        redis = await Redis.from_url(
            redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
        # ping() returns Union[Awaitable[bool], bool]
        # We need to handle both cases
        ping_response = redis.ping()
        # Check if it's awaitable
        if hasattr(ping_response, "__await__"):
            ping_result = await ping_response  # type: ignore[misc]
        else:
            ping_result = ping_response  # type: ignore[assignment]
        await redis.aclose()
        connected = bool(ping_result)
    except Exception:
        connected = False

    # Redact password from Redis URL
    safe_url = redis_url
    if "@" in safe_url:
        parts = safe_url.split("@")
        if ":" in parts[0]:
            protocol_part = parts[0].split("://")[0]
            safe_url = f"{protocol_part}://***@{parts[1]}"

    return {
        "connected": connected,
        "url": safe_url,
        "ping": "OK" if connected else "FAILED",
    }


def _get_api_keys_status() -> dict[str, Any]:
    """Get API keys status (redacted).

    Returns:
        Dictionary with redacted API key information
    """
    clerk_key = os.getenv("CLERK_SECRET_KEY")
    alpha_vantage_key = os.getenv("ALPHA_VANTAGE_API_KEY")

    return {
        "clerk_secret_key": _redact_api_key(clerk_key),
        "alpha_vantage_api_key": _redact_api_key(alpha_vantage_key),
    }


async def _get_services_health() -> dict[str, Any]:
    """Get external services health status.

    Returns:
        Dictionary with service health information
    """
    services: dict[str, Any] = {}

    clerk_key = os.getenv("CLERK_SECRET_KEY")
    if clerk_key and clerk_key not in ("", "your_api_key_here", "test"):
        services["clerk"] = {
            "configured": True,
            "last_check": datetime.now(UTC).isoformat(),
        }

    alpha_vantage_key = os.getenv("ALPHA_VANTAGE_API_KEY")
    if alpha_vantage_key and alpha_vantage_key not in ("", "your_api_key_here"):
        services["alpha_vantage"] = {
            "configured": True,
            "last_check": datetime.now(UTC).isoformat(),
        }

    return services


@router.get("")
async def get_debug_info(
    session: SessionDep,
) -> dict[str, Any]:
    """Get runtime debug information.

    Returns diagnostic information about the application's runtime
    environment, database connectivity, Redis status, and configured
    API keys (redacted).

    Security Note: This endpoint does NOT expose:
    - Full API key values (only prefixes/lengths)
    - Database passwords (redacted in URLs)
    - Any user data or PII

    Returns:
        Dictionary containing:
        - environment: Runtime environment info
        - database: Database connection status
        - redis: Redis connection status
        - api_keys: Redacted API key information
        - services: External services health

    Example:
        ```json
        {
          "environment": {
            "environment": "development",
            "python_version": "3.13.1",
            "fastapi_version": "0.115.6"
          },
          "database": {
            "connected": true,
            "url": "postgresql+asyncpg://papertrade:***@localhost:5432/papertrade_dev"
          },
          "redis": {
            "connected": true,
            "url": "redis://localhost:6379/0",
            "ping": "OK"
          },
          "api_keys": {
            "clerk_secret_key": {
              "present": true,
              "prefix": "sk_test_",
              "length": 64
            }
          }
        }
        ```
    """
    return {
        "environment": _get_environment_info(),
        "database": await _get_database_status(session),
        "redis": await _get_redis_status(),
        "api_keys": _get_api_keys_status(),
        "services": await _get_services_health(),
    }
