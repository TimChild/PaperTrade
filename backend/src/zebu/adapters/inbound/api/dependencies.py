"""FastAPI dependency injection.

Provides factory functions for repositories and other dependencies used by API routes.
"""

import logging
import os
from collections.abc import Awaitable, Callable
from datetime import date
from typing import Annotated
from uuid import UUID

import httpx
import structlog
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis.asyncio import Redis

from zebu.adapters.auth.api_key_adapter import ApiKeyAuthAdapter
from zebu.adapters.auth.api_key_hasher import API_KEY_PREFIX, get_api_key_hasher
from zebu.adapters.auth.clerk_adapter import ClerkAuthAdapter
from zebu.adapters.auth.in_memory_adapter import InMemoryAuthAdapter
from zebu.adapters.outbound.database.api_key_repository import (
    SQLModelApiKeyRepository,
)
from zebu.adapters.outbound.database.backfill_task_repository import (
    SQLModelBackfillTaskRepository,
)
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
from zebu.adapters.outbound.market_data.deterministic_mock_adapter import (
    DeterministicMockMarketDataAdapter,
)
from zebu.adapters.outbound.repositories.price_repository import (
    PriceRepository,
)
from zebu.application.ports.auth_port import AuthenticatedUser, AuthPort
from zebu.application.ports.inbound_rate_limiter_port import (
    InboundRateLimiterPort,
)
from zebu.application.ports.market_data_port import MarketDataPort
from zebu.application.services.snapshot_job import SnapshotJobService
from zebu.domain.exceptions import InvalidTokenError
from zebu.domain.value_objects.api_key_scope import ApiKeyScope
from zebu.infrastructure.cache.price_cache import PriceCache
from zebu.infrastructure.database import SessionDep
from zebu.infrastructure.inbound_rate_limiter import InMemoryInboundRateLimiter
from zebu.infrastructure.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)

# Security scheme for Bearer token authentication.
# auto_error=False so we can fall back to the API-key path when no Bearer
# header is present. The composite get_current_user dependency owns the
# final 401 decision.
security = HTTPBearer(auto_error=False)


def _is_production() -> bool:
    """Check if APP_ENV is production.

    Returns:
        True when APP_ENV environment variable equals "production".
    """
    return os.getenv("APP_ENV", "development") == "production"


def get_admin_user_ids() -> frozenset[str]:
    """Read the comma-separated allowlist of admin Clerk user IDs from env.

    Reads ADMIN_USER_IDS at call time (rather than module import) so that
    test fixtures can mutate the environment via monkeypatch.setenv between
    tests without reloading the dependencies module.

    Returns:
        Frozen set of admin Clerk user IDs (the raw string IDs from the
        auth provider, not the deterministic UUIDs derived from them).
    """
    raw = os.getenv("ADMIN_USER_IDS", "")
    return frozenset(part.strip() for part in raw.split(",") if part.strip())


def is_admin_user(user_id: str, admin_ids: frozenset[str]) -> bool:
    """Check whether the given Clerk user ID is in the admin allowlist.

    Args:
        user_id: Clerk user ID (e.g. "user_2abc123") from AuthenticatedUser.id
        admin_ids: Allowlist of admin user IDs

    Returns:
        True if user_id is in the allowlist; False otherwise.
    """
    return user_id in admin_ids


# Default earliest date for an operator-driven "catch up" backfill if
# ``ZEBU_HISTORY_EPOCH`` is not set in the environment. 2015-01-01 is a
# round, deliberately-old anchor that covers ~10 years of daily bars —
# enough for any realistic backtest window without paying the cost of
# fetching pre-2015 history that Alpha Vantage's free tier mostly
# returns sparsely anyway.
_DEFAULT_HISTORY_EPOCH: date = date(2015, 1, 1)


def get_history_epoch() -> date:
    """Read the ``ZEBU_HISTORY_EPOCH`` env knob.

    Defines the earliest target date for an operator-driven "catch up"
    backfill. The admin data-coverage endpoint computes
    ``[ZEBU_HISTORY_EPOCH, today]`` as the canonical backfill range and
    uses the same span to compute ``gap_days_count`` so the metric
    actually moves when a backfill lands.

    Env value must be a parseable ISO 8601 date (``YYYY-MM-DD``).
    Invalid values raise ``RuntimeError`` so the misconfiguration
    surfaces as a hard 500 on first admin coverage call rather than
    silently falling back. The read happens at call time (not at module
    import) so test fixtures can use ``monkeypatch.setenv`` between
    tests.

    Returns:
        Parsed ISO date. Defaults to :data:`_DEFAULT_HISTORY_EPOCH`
        (``2015-01-01``) if the env var is unset.

    Raises:
        RuntimeError: If ``ZEBU_HISTORY_EPOCH`` is set to a value that
            ``date.fromisoformat`` cannot parse.
    """
    raw = os.getenv("ZEBU_HISTORY_EPOCH")
    if raw is None or raw.strip() == "":
        return _DEFAULT_HISTORY_EPOCH
    try:
        return date.fromisoformat(raw.strip())
    except ValueError as exc:
        raise RuntimeError(
            f"ZEBU_HISTORY_EPOCH must be an ISO 8601 date (YYYY-MM-DD); got {raw!r}"
        ) from exc


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


def get_api_key_repository(
    session: SessionDep,
) -> SQLModelApiKeyRepository:
    """Get API key repository instance.

    Args:
        session: Database session from dependency injection

    Returns:
        SQLModelApiKeyRepository instance
    """
    return SQLModelApiKeyRepository(session)


def get_api_key_auth_adapter(
    repository: Annotated[SQLModelApiKeyRepository, Depends(get_api_key_repository)],
) -> ApiKeyAuthAdapter:
    """Build an :class:`ApiKeyAuthAdapter` for the current request.

    The hasher is read from env config via :func:`get_api_key_hasher`. The
    repository is request-scoped (bound to the per-request session) so a
    successful auth's ``last_used_at`` bump commits with the rest of the
    request's unit of work.

    Args:
        repository: Per-request SQLModel API-key repository.

    Returns:
        Configured :class:`ApiKeyAuthAdapter`.
    """
    return ApiKeyAuthAdapter(
        repository=repository,
        hasher=get_api_key_hasher(),
    )


def get_auth_port() -> AuthPort:
    """Get authentication port implementation.

    Returns the appropriate AuthPort implementation based on environment
    configuration. Uses ClerkAuthAdapter when a Clerk secret is configured,
    or InMemoryAuthAdapter for tests / local development.

    In production (APP_ENV=production), a missing or placeholder
    CLERK_SECRET_KEY is a configuration error: the function raises
    RuntimeError so the misconfiguration surfaces as a hard 500 on first
    request rather than as a silent swap to an empty in-memory adapter
    (which would deny every login but mask the underlying cause).

    Returns:
        AuthPort implementation (ClerkAuthAdapter or InMemoryAuthAdapter)

    Raises:
        RuntimeError: If APP_ENV=production and CLERK_SECRET_KEY is missing
            or set to the placeholder "test".
    """
    clerk_secret_key = os.getenv("CLERK_SECRET_KEY", "")

    # Use Clerk adapter if secret key is configured
    if clerk_secret_key and clerk_secret_key != "test":
        return ClerkAuthAdapter(secret_key=clerk_secret_key)

    # Fail fast in production rather than silently swap in the in-memory
    # adapter. The in-memory adapter has no users registered, so every
    # request would return 401 with no indication that auth itself is
    # misconfigured.
    if _is_production():
        raise RuntimeError(
            "CLERK_SECRET_KEY must be configured when APP_ENV=production. "
            "Refusing to fall back to in-memory auth adapter."
        )

    # Fall back to in-memory adapter for testing / local development.
    # In test environments, this will be overridden with a properly
    # configured InMemoryAuthAdapter.
    return InMemoryAuthAdapter()


def extract_api_key_from_request(request: Request) -> str | None:
    """Pull a raw API key from the request headers, if any.

    Tries, in order:

    1. ``Authorization: ApiKey <key>``
    2. ``X-API-Key: <key>``

    Returns ``None`` if neither header is present. The Bearer scheme is
    handled by :class:`fastapi.security.HTTPBearer` and parsed separately.

    Args:
        request: The active FastAPI request.

    Returns:
        The raw API key string if present, otherwise ``None``.
    """
    auth_header = request.headers.get("authorization") or request.headers.get(
        "Authorization"
    )
    if auth_header:
        # "ApiKey zk_xxx" — case-insensitive scheme match.
        scheme, _, value = auth_header.partition(" ")
        if scheme.lower() == "apikey" and value:
            return value.strip()

    x_api_key = request.headers.get("x-api-key") or request.headers.get("X-API-Key")
    if x_api_key:
        return x_api_key.strip()

    return None


def _bind_actor_to_log_context(user: AuthenticatedUser) -> None:
    """Bind the resolved actor identity to structlog contextvars.

    Once bound, every log line emitted during the rest of the request
    handler (and the dependencies that run after this) automatically
    carries the actor fields — no per-handler ``extra={...}`` needed.
    The :class:`LoggingContextMiddleware` clears the context at the
    start of each request, so there's no cross-request leak.

    Phase H5 (multi-agent identity prep): the ``api_key_label`` is the
    identity column the activity feed (Phase H2) and per-key rate
    limiter (Phase F) will key on. Surfacing it on every authenticated
    log line makes "find everything `claude-code-laptop-explorer` did
    today" a one-grep operation instead of a join across DB tables.

    Args:
        user: The authenticated user produced by :func:`get_current_user`.
    """
    bindings: dict[str, str] = {
        "auth_method": user.auth_method,
        "clerk_user_id": user.id,
    }
    if user.api_key_id is not None:
        bindings["api_key_id"] = str(user.api_key_id)
    if user.api_key_label is not None:
        bindings["api_key_label"] = user.api_key_label
    structlog.contextvars.bind_contextvars(**bindings)


async def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    auth: Annotated[AuthPort, Depends(get_auth_port)],
    api_key_auth: Annotated[ApiKeyAuthAdapter, Depends(get_api_key_auth_adapter)],
) -> AuthenticatedUser:
    """Extract and verify user from the request's auth headers.

    Supports two schemes:

    - ``Authorization: Bearer <jwt>`` — Clerk JWT, verified via
      :class:`AuthPort`.
    - ``Authorization: ApiKey <raw>`` or ``X-API-Key: <raw>`` — Phase C2
      API-key path, verified via :class:`ApiKeyAuthAdapter`.

    Returns the same :class:`AuthenticatedUser` shape regardless of which
    scheme authenticated the request. Downstream code does not need to
    care which path the request came in on. The
    :class:`AuthenticatedUser` carries the originating ``auth_method``
    plus, on the API-key path, the persisted key's ``id`` and
    ``label`` — surfaced to every log line via structlog contextvars
    (Phase H5).

    Selection rule: a Bearer token wins if both are present; this keeps
    behaviour unchanged for browser clients that always send ``Bearer``.
    A request that looks like an API key (``Bearer zk_...`` or matching
    the API-key prefix) is routed to the API-key adapter even when sent
    through the Bearer slot — this lets curl-style ``Authorization:
    Bearer zk_xxx`` work without forcing callers to remember the
    ``ApiKey`` scheme name.

    Args:
        request: The active FastAPI request (used to read non-Bearer
            auth headers).
        credentials: Optional ``HTTPAuthorizationCredentials`` parsed by
            :class:`fastapi.security.HTTPBearer` (auto_error disabled).
        auth: Auth port (Clerk in prod, in-memory in tests).
        api_key_auth: API-key auth adapter (always available — validates
            against the request-scoped DB session).

    Returns:
        AuthenticatedUser: Verified user identity.

    Raises:
        HTTPException: 401 if neither scheme produces a valid identity.
    """
    bearer_token: str | None = (
        credentials.credentials if credentials is not None else None
    )
    api_key_token: str | None = extract_api_key_from_request(request)

    # Bearer token that *looks* like an API key: route it to the API-key
    # adapter. Lets agents send `Authorization: Bearer zk_xxx` and have it
    # work, which is what most HTTP libraries default to.
    if (
        bearer_token is not None
        and bearer_token.startswith(API_KEY_PREFIX)
        and api_key_token is None
    ):
        api_key_token = bearer_token
        bearer_token = None

    last_error: InvalidTokenError | None = None

    if bearer_token is not None:
        try:
            user = await auth.verify_token(bearer_token)
        except InvalidTokenError as exc:
            last_error = exc
        else:
            _bind_actor_to_log_context(user)
            return user

    if api_key_token is not None:
        try:
            user = await api_key_auth.verify_token(api_key_token)
        except InvalidTokenError as exc:
            last_error = exc
        else:
            _bind_actor_to_log_context(user)
            return user

    if last_error is None:
        # Neither scheme presented anything — the request was missing auth.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=f"Invalid authentication credentials: {str(last_error)}",
        headers={"WWW-Authenticate": "Bearer"},
    ) from last_error


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


async def get_active_api_key_id(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> UUID | None:
    """Return the API key ID if the request authenticated via API key, else None.

    Routes use this to stamp the originating API-key id onto entities they
    write so the recent-activity feed (Phase H2) can join back to
    ``api_keys`` and surface the human-readable label.

    For Clerk-authenticated requests this returns ``None`` — the activity
    feed will render those rows as ``actor_kind="user"``.
    """
    return current_user.api_key_id


async def verify_admin(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> UUID:
    """Verify that the authenticated user is in the admin allowlist.

    Reads the env-driven `ADMIN_USER_IDS` allowlist (comma-separated Clerk
    user IDs) and rejects any caller whose `current_user.id` is not in that
    list. This is intentionally strict: an empty allowlist means every
    admin endpoint returns 403, which is the correct posture for a fresh
    deploy that has not yet been provisioned.

    Args:
        current_user: Authenticated user from `get_current_user`

    Returns:
        UUID: Admin user's ID as a deterministic UUID (so admin endpoints
        can use it interchangeably with `CurrentUserDep`).

    Raises:
        HTTPException: 403 if the user is not in the admin allowlist.
    """
    from uuid import NAMESPACE_DNS, uuid5

    admin_ids = get_admin_user_ids()
    if not is_admin_user(current_user.id, admin_ids):
        logger.warning(
            "Admin endpoint access denied for non-admin user",
            extra={"clerk_user_id": current_user.id},
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )

    return uuid5(NAMESPACE_DNS, current_user.id)


# Global singletons for market data dependencies
# These are created once and reused across requests
_redis_client: Redis | None = None  # type: ignore[type-arg]  # Redis generic type parameter not needed for singleton
_http_client: httpx.AsyncClient | None = None

# Phase F-6: per-process in-memory inbound rate limiter for backtest
# requests. Singleton so the bucket state persists across requests within
# a single FastAPI process. Configured lazily on first use from env so
# tests that monkeypatch the limits before the first request still see
# the patched values.
_inbound_backtest_rate_limiter: InMemoryInboundRateLimiter | None = None


def _get_backtest_rate_limiter() -> InMemoryInboundRateLimiter:
    """Lazy singleton accessor for the backtest rate limiter.

    Defaults (per design §6.2):

    - 5 requests / minute / API key (``ZEBU_BACKTEST_RATE_LIMIT_MIN``)
    - 100 requests / day / API key (``ZEBU_BACKTEST_RATE_LIMIT_DAY``)

    The limiter is constructed lazily on first call so the env-driven
    config is read after pytest fixtures have set up any monkeypatch.
    """
    global _inbound_backtest_rate_limiter
    if _inbound_backtest_rate_limiter is None:
        minute_limit = int(os.getenv("ZEBU_BACKTEST_RATE_LIMIT_MIN", "5"))
        day_limit = int(os.getenv("ZEBU_BACKTEST_RATE_LIMIT_DAY", "100"))
        _inbound_backtest_rate_limiter = InMemoryInboundRateLimiter(
            minute_limit=minute_limit,
            day_limit=day_limit,
        )
    return _inbound_backtest_rate_limiter


def get_backtest_rate_limiter() -> InboundRateLimiterPort:
    """FastAPI dependency — returns the inbound rate limiter port.

    Returns the per-process singleton; can be overridden via
    ``app.dependency_overrides`` in tests that need isolated state.
    """
    return _get_backtest_rate_limiter()


async def get_market_data(session: SessionDep) -> MarketDataPort:
    """Provide MarketDataPort implementation.

    Routes to a real or mock adapter based on the ``MARKET_DATA_PROVIDER``
    environment variable:

    - ``alpha_vantage`` (default, production behaviour): the real
      :class:`AlphaVantageAdapter` with Redis-backed caching and rate
      limiting. The Alpha Vantage API key, rate limits, and Redis URL are
      all read from the environment.
    - ``mock`` / ``in_memory``: a deterministic, network-free
      :class:`DeterministicMockMarketDataAdapter` used by E2E tests and
      local-fake stacks. This avoids depending on the public Alpha Vantage
      ``demo`` key (5/min, 25/day, IBM-only), which is the dominant
      historical source of CI E2E flakiness.

    The Alpha Vantage adapter's core infrastructure (Redis, HTTP client) is
    created once and reused; only the per-request price repository is built
    each call so it stays bound to the supplied session. The mock adapter has
    no shared state to cache.

    Args:
        session: Database session from dependency injection.

    Returns:
        MarketDataPort implementation.

    Raises:
        RuntimeError: If a value other than ``alpha_vantage``, ``mock``, or
            ``in_memory`` is supplied for ``MARKET_DATA_PROVIDER``.
    """
    provider = os.getenv("MARKET_DATA_PROVIDER", "alpha_vantage").strip().lower()

    if provider in {"mock", "in_memory"}:
        # Deterministic, network-free adapter for E2E / local-fake stacks.
        # No Redis, no HTTP client, no rate limiter. Defaults are sufficient
        # for E2E tests; tests that need richer ticker behaviour can override
        # the dependency directly via app.dependency_overrides.
        return DeterministicMockMarketDataAdapter()

    if provider != "alpha_vantage":
        raise RuntimeError(
            f"Unsupported MARKET_DATA_PROVIDER='{provider}'. "
            "Valid values: 'alpha_vantage' (default), 'mock', 'in_memory'."
        )

    global _redis_client, _http_client

    # Get configuration from environment variables
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    alpha_vantage_api_key = os.getenv("ALPHA_VANTAGE_API_KEY", "")

    if not alpha_vantage_api_key or alpha_vantage_api_key == "your_api_key_here":
        # Use demo key for development/testing
        alpha_vantage_api_key = "demo"

    # Get rate limits from environment or use defaults.
    # Phase J / Task #212 Layer 2 — ``ALPHA_VANTAGE_DAILY_CAP`` is the
    # operator-facing knob (default 25, matching the free-tier daily cap;
    # ``0`` = unbounded for paid AV). It takes precedence over the older
    # ``ALPHA_VANTAGE_RATE_LIMIT_PER_DAY`` (default 500) but the legacy
    # name is kept as a fallback so an existing prod deployment doesn't
    # silently flip caps until the env file is updated.
    calls_per_minute = int(os.getenv("ALPHA_VANTAGE_RATE_LIMIT_PER_MIN", "5"))
    daily_cap_raw = os.getenv("ALPHA_VANTAGE_DAILY_CAP")
    if daily_cap_raw is not None:
        calls_per_day = int(daily_cap_raw)
    else:
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

    # Phase J / Task #212 Layer 3: wire the L2 backfill-task port into the
    # market-data adapter so partial-coverage results enqueue a high-
    # priority backfill before raising IncompleteHistoricalDataError.
    backfill_task_repository = SQLModelBackfillTaskRepository(session)

    # Create adapter (per-request to include fresh repository)
    return AlphaVantageAdapter(
        rate_limiter=rate_limiter,
        price_cache=price_cache,
        http_client=_http_client,
        api_key=alpha_vantage_api_key,
        price_repository=price_repository,
        backfill_task_repository=backfill_task_repository,
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


def require_scope(
    scope: ApiKeyScope,
) -> "Callable[[Request, SQLModelApiKeyRepository], Awaitable[None]]":
    """Build a dependency that gates on an API-key scope.

    Behaviour:

    - Clerk Bearer auth always passes (humans authenticated through the UI
      are full-trust). Only API-key requests are gated.
    - API-key requests must carry the requested scope (or ``ADMIN``, which
      is always sufficient).

    Phase C2 deliberately wires this helper but does *not* apply it
    broadly. Most non-admin endpoints stay open to any authenticated
    identity for now — Phase D follow-up will sweep through and apply
    ``READ`` / ``TRADE`` gates per-route.

    Usage:

    ::

        @router.post(
            "/trades",
            dependencies=[Depends(require_scope(ApiKeyScope.TRADE))],
        )
        async def execute_trade(...): ...

    Args:
        scope: The minimum scope an API-key request must carry.

    Returns:
        An async dependency callable that raises 403 on scope mismatch
        and is a no-op for Clerk-authenticated requests.
    """

    async def _check(
        request: Request,
        api_key_repo: Annotated[
            SQLModelApiKeyRepository, Depends(get_api_key_repository)
        ],
    ) -> None:
        raw_key = extract_api_key_from_request(request)
        # Allow `Authorization: Bearer zk_...` to satisfy the API-key route.
        auth_header = request.headers.get("authorization") or request.headers.get(
            "Authorization"
        )
        if raw_key is None and auth_header:
            scheme, _, value = auth_header.partition(" ")
            if scheme.lower() == "bearer" and value.startswith(API_KEY_PREFIX):
                raw_key = value.strip()

        if raw_key is None:
            # Clerk Bearer path — no scope check applies.
            return

        # Look up the key. We trust get_current_user (which ran first as a
        # dependency on the route) to have rejected revoked/expired keys
        # already, but we re-verify the hash to load the scope set.
        hasher = get_api_key_hasher()
        record = await api_key_repo.get_by_hash(hasher.hash(raw_key))
        if record is None:
            # Should not happen if get_current_user passed, but treat as
            # 401 to be safe rather than masking it as 403.
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if record.has_scope(ApiKeyScope.ADMIN):
            return
        if record.has_scope(scope):
            return

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"API key missing required scope: {scope.value}",
        )

    return _check


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
ApiKeyRepositoryDep = Annotated[
    SQLModelApiKeyRepository, Depends(get_api_key_repository)
]
AuthPortDep = Annotated[AuthPort, Depends(get_auth_port)]
CurrentUser = Annotated[AuthenticatedUser, Depends(get_current_user)]
CurrentUserDep = Annotated[UUID, Depends(get_current_user_id)]
ActiveApiKeyIdDep = Annotated[UUID | None, Depends(get_active_api_key_id)]
AdminUserDep = Annotated[UUID, Depends(verify_admin)]
MarketDataDep = Annotated[MarketDataPort, Depends(get_market_data)]
BacktestRateLimiterDep = Annotated[
    InboundRateLimiterPort, Depends(get_backtest_rate_limiter)
]
HistoryEpochDep = Annotated[date, Depends(get_history_epoch)]
