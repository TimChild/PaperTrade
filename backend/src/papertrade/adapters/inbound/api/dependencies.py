"""FastAPI dependency injection.

Provides factory functions for repositories and other dependencies used by API routes.
"""

import os
from typing import Annotated
from uuid import UUID

import httpx
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
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
from papertrade.adapters.outbound.repositories.price_repository import (
    PriceRepository,
)
from papertrade.application.ports.market_data_port import MarketDataPort
from papertrade.infrastructure.cache.price_cache import PriceCache
from papertrade.infrastructure.database import SessionDep
from papertrade.infrastructure.rate_limiter import RateLimiter

# OAuth2 password bearer for JWT token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


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


def get_price_repository(
    session: SessionDep,
) -> PriceRepository:
    """Get price repository instance.

    Args:
        session: Database session from dependency injection

    Returns:
        PriceRepository instance
    """
    return PriceRepository(session)


async def get_current_user_id(
    token: Annotated[str, Depends(oauth2_scheme)],
) -> UUID:
    """Get current user ID from JWT token.

    Validates the JWT token and extracts the user ID from the 'sub' claim.

    Args:
        token: JWT access token from Authorization header

    Returns:
        User UUID from token

    Raises:
        HTTPException: 401 if token is invalid, expired, or missing user ID
    """
    from fastapi import HTTPException, status

    from papertrade.application.services.jwt_service import JWTService
    from papertrade.domain.exceptions import InvalidTokenError
    from papertrade.infrastructure.settings import get_settings

    settings = get_settings()
    jwt_service = JWTService(
        secret_key=settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    try:
        user_id = jwt_service.get_user_id_from_token(token)
        return user_id
    except InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


# Global singletons for market data dependencies
# These are created once and reused across requests
_redis_client: Redis | None = None  # type: ignore[type-arg]  # Redis generic type parameter not needed for singleton
_http_client: httpx.AsyncClient | None = None


async def get_market_data(session: SessionDep) -> MarketDataPort:
    """Provide MarketDataPort implementation (AlphaVantageAdapter).

    This dependency creates and caches the AlphaVantageAdapter with all its
    infrastructure dependencies (Redis, rate limiter, cache, HTTP client,
    price repository).

    The core adapter infrastructure is created once and reused, but the price
    repository is created per-request using the provided session.

    Args:
        session: Database session from dependency injection

    Returns:
        MarketDataPort implementation (AlphaVantageAdapter)

    Raises:
        RuntimeError: If required environment variables are not set
    """
    global _redis_client, _http_client

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

    # Create price repository (per-request, uses session)
    price_repository = PriceRepository(session)

    # Create adapter (per-request to include fresh repository)
    return AlphaVantageAdapter(
        rate_limiter=rate_limiter,
        price_cache=price_cache,
        http_client=_http_client,
        api_key=alpha_vantage_api_key,
        price_repository=price_repository,
    )


# Type aliases for route dependency injection
PortfolioRepositoryDep = Annotated[
    SQLModelPortfolioRepository, Depends(get_portfolio_repository)
]
TransactionRepositoryDep = Annotated[
    SQLModelTransactionRepository, Depends(get_transaction_repository)
]
PriceRepositoryDep = Annotated[PriceRepository, Depends(get_price_repository)]
CurrentUserDep = Annotated[UUID, Depends(get_current_user_id)]
MarketDataDep = Annotated[MarketDataPort, Depends(get_market_data)]
