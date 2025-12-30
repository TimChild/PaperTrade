"""FastAPI dependency injection.

Provides factory functions for repositories and other dependencies used by API routes.
"""

import os
from typing import Annotated
from uuid import UUID

import httpx
from fastapi import Depends, Header
from redis.asyncio import Redis

from papertrade.adapters.outbound.database.portfolio_repository import (
    SQLModelPortfolioRepository,
)
from papertrade.adapters.outbound.database.transaction_repository import (
    SQLModelTransactionRepository,
)
from papertrade.adapters.outbound.market_data.alpha_vantage_adapter import (
    AlphaVantageAdapter,
)
from papertrade.application.ports.market_data_port import MarketDataPort
from papertrade.infrastructure.cache.price_cache import PriceCache
from papertrade.infrastructure.database import SessionDep
from papertrade.infrastructure.rate_limiter import RateLimiter


def get_portfolio_repository(
    session: SessionDep,
) -> SQLModelPortfolioRepository:
    """Get portfolio repository instance.

    Args:
        session: Database session from dependency injection

    Returns:
        SQLModelPortfolioRepository instance
    """
    return SQLModelPortfolioRepository(session)


def get_transaction_repository(
    session: SessionDep,
) -> SQLModelTransactionRepository:
    """Get transaction repository instance.

    Args:
        session: Database session from dependency injection

    Returns:
        SQLModelTransactionRepository instance
    """
    return SQLModelTransactionRepository(session)


async def get_current_user_id(
    x_user_id: Annotated[str | None, Header()] = None,
) -> "UUID":
    """Get current user ID from request headers.

    This is a mock implementation for Phase 1. In production, this would:
    - Validate JWT token
    - Extract user ID from token
    - Raise 401 if unauthorized

    For now, we accept a user ID via X-User-Id header for testing.

    Args:
        x_user_id: User ID from X-User-Id header

    Returns:
        User UUID

    Raises:
        HTTPException: 400 if X-User-Id header is missing or invalid
    """
    from uuid import UUID

    from fastapi import HTTPException

    if not x_user_id:
        raise HTTPException(
            status_code=400,
            detail="X-User-Id header is required (authentication not yet implemented)",
        )

    try:
        return UUID(x_user_id)
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid X-User-Id header: must be a valid UUID, got '{x_user_id}'",
        ) from e


# Global singletons for market data dependencies
# These are created once and reused across requests
_redis_client: Redis | None = None  # type: ignore[type-arg]
_http_client: httpx.AsyncClient | None = None
_market_data_adapter: AlphaVantageAdapter | None = None


async def get_market_data() -> MarketDataPort:
    """Provide MarketDataPort implementation (AlphaVantageAdapter).

    This dependency creates and caches the AlphaVantageAdapter with all its
    infrastructure dependencies (Redis, rate limiter, cache, HTTP client).

    The adapter is created once and reused across all requests for efficiency.

    Returns:
        MarketDataPort implementation (AlphaVantageAdapter)

    Raises:
        RuntimeError: If required environment variables are not set
    """
    global _redis_client, _http_client, _market_data_adapter

    # Return cached adapter if already initialized
    if _market_data_adapter is not None:
        return _market_data_adapter

    # Get configuration from environment variables
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    alpha_vantage_api_key = os.getenv("ALPHA_VANTAGE_API_KEY", "")
    
    if not alpha_vantage_api_key or alpha_vantage_api_key == "your_api_key_here":
        # Use demo key for development/testing
        alpha_vantage_api_key = "demo"

    # Get rate limits from environment or use defaults
    calls_per_minute = int(os.getenv("ALPHA_VANTAGE_RATE_LIMIT_PER_MIN", "5"))
    calls_per_day = int(os.getenv("ALPHA_VANTAGE_RATE_LIMIT_PER_DAY", "500"))

    # Create Redis client (singleton)
    if _redis_client is None:
        _redis_client = await Redis.from_url(
            redis_url,
            encoding="utf-8",
            decode_responses=True,
        )

    # Create HTTP client (singleton)
    if _http_client is None:
        _http_client = httpx.AsyncClient(timeout=5.0)

    # Create rate limiter
    rate_limiter = RateLimiter(
        redis=_redis_client,
        key_prefix="papertrade:ratelimit:alphavantage",
        calls_per_minute=calls_per_minute,
        calls_per_day=calls_per_day,
    )

    # Create price cache
    price_cache = PriceCache(
        redis=_redis_client,
        key_prefix="papertrade:price",
        default_ttl=3600,  # 1 hour
    )

    # Create adapter (singleton)
    _market_data_adapter = AlphaVantageAdapter(
        rate_limiter=rate_limiter,
        price_cache=price_cache,
        http_client=_http_client,
        api_key=alpha_vantage_api_key,
    )

    return _market_data_adapter


# Type aliases for route dependency injection
PortfolioRepositoryDep = Annotated[
    SQLModelPortfolioRepository, Depends(get_portfolio_repository)
]
TransactionRepositoryDep = Annotated[
    SQLModelTransactionRepository, Depends(get_transaction_repository)
]
CurrentUserDep = Annotated[UUID, Depends(get_current_user_id)]
MarketDataDep = Annotated[MarketDataPort, Depends(get_market_data)]
