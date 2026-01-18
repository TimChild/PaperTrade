"""FastAPI dependency injection.

Provides factory functions for repositories and other dependencies used by API routes.
"""

import os
from typing import Annotated
from uuid import UUID

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis.asyncio import Redis

from zebu.adapters.auth.clerk_adapter import ClerkAuthAdapter
from zebu.adapters.auth.in_memory_adapter import InMemoryAuthAdapter
from zebu.adapters.outbound.database.portfolio_repository import (
    SQLModelPortfolioRepository,
)
from zebu.adapters.outbound.database.snapshot_repository import (
    SQLModelSnapshotRepository,
)
from zebu.adapters.outbound.database.transaction_repository import (
    SQLModelTransactionRepository,
)
from zebu.adapters.outbound.market_data.alpha_vantage_adapter import (
    AlphaVantageAdapter,
)
from zebu.adapters.outbound.repositories.price_repository import (
    PriceRepository,
)
from zebu.application.ports.auth_port import AuthenticatedUser, AuthPort
from zebu.application.ports.market_data_port import MarketDataPort
from zebu.application.services.snapshot_job import SnapshotJobService
from zebu.domain.exceptions import InvalidTokenError
from zebu.infrastructure.cache.price_cache import PriceCache
from zebu.infrastructure.database import SessionDep
from zebu.infrastructure.rate_limiter import RateLimiter

# Security scheme for Bearer token authentication
security = HTTPBearer()


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


def get_snapshot_repository(
    session: SessionDep,
) -> SQLModelSnapshotRepository:
    """Get snapshot repository instance.

    Args:
        session: Database session from dependency injection

    Returns:
        SQLModelSnapshotRepository instance
    """
    return SQLModelSnapshotRepository(session)


def get_auth_port() -> AuthPort:
    """Get authentication port implementation.

    Returns the appropriate AuthPort implementation based on environment
    configuration:
    - E2E_TEST_MODE=true: InMemoryAuthAdapter in permissive mode (accepts any token)
    - CLERK_SECRET_KEY set: ClerkAuthAdapter for production authentication
    - Otherwise: InMemoryAuthAdapter in strict mode (for unit tests)

    E2E test mode allows frontend E2E tests to authenticate without requiring
    valid Clerk sessions, making tests more reliable and faster.

    Returns:
        AuthPort implementation (ClerkAuthAdapter or InMemoryAuthAdapter)
    """
    import logging

    logger = logging.getLogger(__name__)

    # Check for E2E test mode (for Playwright tests)
    e2e_mode = os.getenv("E2E_TEST_MODE", "").lower() in ("true", "1", "yes")

    if e2e_mode:
        logger.info(
            "E2E_TEST_MODE enabled - using InMemoryAuthAdapter in permissive mode"
        )
        from zebu.application.ports.auth_port import AuthenticatedUser

        # Create a default test user for E2E tests
        default_user = AuthenticatedUser(
            id=os.getenv("E2E_CLERK_USER_ID", "user_e2e_test"),
            email=os.getenv("E2E_CLERK_USER_EMAIL", "test-e2e@papertrade.dev"),
        )

        # Permissive mode: accepts any non-empty token for the default user
        # This allows E2E tests to work without valid Clerk sessions
        return InMemoryAuthAdapter(
            permissive_mode=True,
            default_user=default_user,
        )

    clerk_secret_key = os.getenv("CLERK_SECRET_KEY", "")

    # Use Clerk adapter if secret key is configured
    if clerk_secret_key and clerk_secret_key != "test":
        logger.info("Using ClerkAuthAdapter for authentication")
        return ClerkAuthAdapter(secret_key=clerk_secret_key)

    # Fall back to in-memory adapter for testing
    # In test environments, this will be overridden with a properly
    # configured InMemoryAuthAdapter
    logger.info("Using InMemoryAuthAdapter (no Clerk secret key)")
    return InMemoryAuthAdapter()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    auth: Annotated[AuthPort, Depends(get_auth_port)],
) -> AuthenticatedUser:
    """Extract and verify user from Authorization header.

    Validates the Bearer token and returns the authenticated user.
    This dependency can be used in route handlers to require authentication.

    Args:
        credentials: Bearer token credentials from Authorization header
        auth: Authentication port implementation

    Returns:
        AuthenticatedUser: Verified user identity

    Raises:
        HTTPException: 401 if authentication fails
    """
    import logging

    logger = logging.getLogger(__name__)
    logger.info(
        f"Authenticating user with auth adapter: {auth.__class__.__name__}"
    )

    try:
        user = await auth.verify_token(credentials.credentials)
        logger.info(f"Authentication successful for user: {user.id}")
        return user
    except InvalidTokenError as e:
        logger.warning(f"Authentication failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication credentials: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


async def get_current_user_id(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> UUID:
    """Get current user ID as UUID from authenticated user.

    This is a compatibility layer that converts the Clerk user ID (string)
    to a UUID. This allows existing code that expects UUID user IDs to
    continue working during the migration.

    For new code, prefer using get_current_user directly to get the
    AuthenticatedUser object.

    Args:
        current_user: Authenticated user from get_current_user

    Returns:
        UUID: User ID as UUID (hashed from Clerk user ID string)

    Note:
        This creates a deterministic UUID from the Clerk user ID string.
        The same Clerk ID will always produce the same UUID.
    """
    from uuid import NAMESPACE_DNS, uuid5

    # Create deterministic UUID from Clerk user ID
    # This ensures the same Clerk user ID always maps to the same UUID
    return uuid5(NAMESPACE_DNS, current_user.id)


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


async def get_snapshot_job(
    session: SessionDep,
) -> SnapshotJobService:
    """Get snapshot job service instance.

    Creates SnapshotJobService with all required dependencies.

    Args:
        session: Database session from dependency injection

    Returns:
        SnapshotJobService instance
    """
    portfolio_repo = get_portfolio_repository(session)
    transaction_repo = get_transaction_repository(session)
    snapshot_repo = get_snapshot_repository(session)
    market_data = await get_market_data(session)

    return SnapshotJobService(
        portfolio_repo=portfolio_repo,
        transaction_repo=transaction_repo,
        snapshot_repo=snapshot_repo,
        market_data=market_data,
    )


# Type aliases for route dependency injection
PortfolioRepositoryDep = Annotated[
    SQLModelPortfolioRepository, Depends(get_portfolio_repository)
]
TransactionRepositoryDep = Annotated[
    SQLModelTransactionRepository, Depends(get_transaction_repository)
]
PriceRepositoryDep = Annotated[PriceRepository, Depends(get_price_repository)]
SnapshotRepositoryDep = Annotated[
    SQLModelSnapshotRepository, Depends(get_snapshot_repository)
]
AuthPortDep = Annotated[AuthPort, Depends(get_auth_port)]
CurrentUser = Annotated[AuthenticatedUser, Depends(get_current_user)]
CurrentUserDep = Annotated[UUID, Depends(get_current_user_id)]
MarketDataDep = Annotated[MarketDataPort, Depends(get_market_data)]
