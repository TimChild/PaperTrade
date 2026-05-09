"""Pytest configuration and shared fixtures."""

from collections.abc import AsyncGenerator
from uuid import UUID

import pytest
import pytest_asyncio
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

# Import all models to ensure they're registered with SQLModel metadata
from zebu.adapters.outbound.database.api_key_model import (  # noqa: F401
    ApiKeyModel,
)
from zebu.adapters.outbound.database.models import (  # noqa: F401
    BacktestRunModel,
    ExplorationTaskModel,
    PortfolioModel,
    PortfolioSnapshotModel,
    StrategyActivationModel,
    StrategyModel,
    TransactionModel,
)
from zebu.adapters.outbound.models.price_history import (  # noqa: F401
    PriceHistoryModel,
)
from zebu.adapters.outbound.models.ticker_watchlist import (  # noqa: F401
    TickerWatchlistModel,
)
from zebu.infrastructure.database import get_session
from zebu.main import app


@pytest_asyncio.fixture
async def test_engine() -> AsyncGenerator[AsyncEngine, None]:
    """Create an in-memory SQLite engine for testing."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    yield engine

    # Cleanup
    await engine.dispose()


@pytest.fixture
def client(test_engine: AsyncEngine) -> TestClient:
    """Create a test client with test database and in-memory market data.

    Overrides the application's database session to use an in-memory test
    database, the market data adapter to use an in-memory implementation,
    and the auth adapter to use an in-memory implementation.
    This ensures integration tests are fast and don't require external
    dependencies (Redis, API keys, Clerk).
    """
    from zebu.adapters.auth.in_memory_adapter import InMemoryAuthAdapter
    from zebu.adapters.inbound.api.dependencies import (
        get_auth_port,
        get_market_data,
    )
    from zebu.adapters.outbound.market_data.in_memory_adapter import (
        InMemoryMarketDataAdapter,
    )
    from zebu.application.ports.auth_port import AuthenticatedUser

    async def get_test_session() -> AsyncGenerator[AsyncSession, None]:
        """Override session dependency to use test database."""
        async with AsyncSession(test_engine, expire_on_commit=False) as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def get_test_market_data(
        session: AsyncSession = Depends(get_test_session),  # type: ignore[assignment]  # noqa: B008
    ) -> InMemoryMarketDataAdapter:
        """Override market data dependency to use in-memory adapter.

        Seeds the adapter with default test prices for common tickers.

        Prices are seeded at a timestamp 1 minute in the past to ensure
        queries for "current" or "recent" times will find them using the
        "at or before" timestamp semantics.

        Args:
            session: Database session from dependency injection (not used
                     for in-memory adapter)
        """
        from datetime import UTC, datetime, timedelta
        from decimal import Decimal

        from zebu.domain.value_objects.money import Money
        from zebu.domain.value_objects.price_point import PricePoint
        from zebu.domain.value_objects.ticker import Ticker

        adapter = InMemoryMarketDataAdapter()

        # Seed prices 1 minute in the past so queries for "now" will find them
        # This works with the "at or before" semantics of get_price_at()
        seed_time = datetime.now(UTC) - timedelta(minutes=1)

        # Seed with default test prices
        test_prices = [
            PricePoint(
                ticker=Ticker("AAPL"),
                price=Money(Decimal("150.00"), "USD"),
                timestamp=seed_time,
                source="database",
                interval="real-time",
            ),
            PricePoint(
                ticker=Ticker("GOOGL"),
                price=Money(Decimal("2800.00"), "USD"),
                timestamp=seed_time,
                source="database",
                interval="real-time",
            ),
            PricePoint(
                ticker=Ticker("MSFT"),
                price=Money(Decimal("380.00"), "USD"),
                timestamp=seed_time,
                source="database",
                interval="real-time",
            ),
        ]

        adapter.seed_prices(test_prices)
        return adapter

    def get_test_auth_port() -> InMemoryAuthAdapter:
        """Override auth port dependency to use in-memory adapter.

        Creates a singleton adapter pre-configured with a test user and token.
        Tests can use the default test user or add additional users as needed.

        The adapter is created once and cached to ensure all requests in a
        test use the same adapter instance.
        """
        # Use a closure variable to cache the adapter instance
        if not hasattr(get_test_auth_port, "_adapter"):
            adapter = InMemoryAuthAdapter()

            # Add a default test user with a known token
            # This matches the default_user_id fixture for backward compatibility
            test_user = AuthenticatedUser(
                id="test-user-default",
                email="test@zebutrader.com",
            )
            adapter.add_user(test_user, "test-token-default")

            get_test_auth_port._adapter = adapter  # type: ignore[attr-defined]

        return get_test_auth_port._adapter  # type: ignore[attr-defined, return-value]

    # Phase C2: seed an in-memory API-key adapter pointed at the same
    # test database the rest of the dependencies use. The default test
    # API key (raw value: "test-token-default") hashes to a stable value
    # under the test pepper and is owned by "test-user-default" — so the
    # parameterized auth-scheme tests resolve to the same user as the
    # Bearer path.
    from zebu.adapters.auth.api_key_adapter import ApiKeyAuthAdapter
    from zebu.adapters.auth.api_key_hasher import ApiKeyHasher
    from zebu.adapters.inbound.api.dependencies import (
        get_api_key_auth_adapter,
        get_api_key_repository,
    )
    from zebu.application.ports.in_memory_api_key_repository import (
        InMemoryApiKeyRepository,
    )

    _test_pepper = "test-api-key-pepper-do-not-use-in-production"
    _test_hasher = ApiKeyHasher(secret=_test_pepper)

    def get_test_api_key_repository() -> InMemoryApiKeyRepository:
        """Singleton in-memory API-key repository for the test session.

        Pre-seeded with one active key whose raw value is
        ``"test-token-default"`` and whose owner is ``"test-user-default"``
        (the same user the Bearer fixture authenticates as).
        """
        from datetime import UTC, datetime
        from uuid import NAMESPACE_DNS, uuid4, uuid5

        from zebu.domain.entities.api_key import ApiKey
        from zebu.domain.value_objects.api_key_scope import ApiKeyScope

        if not hasattr(get_test_api_key_repository, "_repo"):
            repo = InMemoryApiKeyRepository()
            seed_key = ApiKey(
                id=uuid4(),
                user_id=uuid5(NAMESPACE_DNS, "test-user-default"),
                clerk_user_id="test-user-default",
                label="test-default",
                key_hash=_test_hasher.hash("test-token-default"),
                scopes=frozenset(
                    [ApiKeyScope.READ, ApiKeyScope.TRADE, ApiKeyScope.ADMIN]
                ),
                created_at=datetime.now(UTC),
            )
            # Seed via direct dict assignment so we can call from a sync
            # closure — InMemoryApiKeyRepository.save is async.
            repo._by_id[seed_key.id] = seed_key
            get_test_api_key_repository._repo = repo  # type: ignore[attr-defined]
        return get_test_api_key_repository._repo  # type: ignore[attr-defined, return-value]

    def get_test_api_key_auth_adapter() -> ApiKeyAuthAdapter:
        """API-key auth adapter for tests, sharing the in-memory repo."""
        return ApiKeyAuthAdapter(
            repository=get_test_api_key_repository(),
            hasher=_test_hasher,
        )

    # Override dependencies
    app.dependency_overrides[get_session] = get_test_session
    app.dependency_overrides[get_market_data] = get_test_market_data
    app.dependency_overrides[get_auth_port] = get_test_auth_port
    app.dependency_overrides[get_api_key_repository] = get_test_api_key_repository
    app.dependency_overrides[get_api_key_auth_adapter] = get_test_api_key_auth_adapter

    with TestClient(app) as test_client:
        yield test_client

    # Clean up overrides and cached adapter
    app.dependency_overrides.clear()
    if hasattr(get_test_auth_port, "_adapter"):
        delattr(get_test_auth_port, "_adapter")
    if hasattr(get_test_api_key_repository, "_repo"):
        delattr(get_test_api_key_repository, "_repo")


@pytest.fixture
def default_user_id() -> UUID:
    """Provide a default user ID for tests.

    This creates a deterministic UUID from the default test user ID.
    This maintains backward compatibility with existing tests while
    supporting the new authentication system.
    """
    from uuid import NAMESPACE_DNS, uuid5

    # Create UUID from the same user ID used in the test auth adapter
    return uuid5(NAMESPACE_DNS, "test-user-default")


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """Provide authentication headers for test requests (Bearer JWT — current).

    Returns headers with a valid Bearer token for the default test user.
    This is the canonical fixture for current-state integration tests; today
    Clerk Bearer is the only auth path the backend accepts.

    For Phase C, when ``ApiKeyAuthAdapter`` lands and the middleware accepts
    ``Authorization: ApiKey <key>`` / ``X-API-Key: <key>``, prefer the
    ``auth_headers_for_scheme`` fixture below so the same test body can be run
    against either scheme via parameterization.
    """
    return {"Authorization": "Bearer test-token-default"}


# Auth schemes the backend accepts. Phase C2 (PR #233) added the
# ``ApiKeyAuthAdapter`` and middleware support, so the parameter list
# now includes both api-key transports alongside Bearer. The
# ``_AUTH_SCHEMES_PHASE_C`` alias is kept for callers that pinned to it.
_AUTH_SCHEMES_CURRENT: tuple[str, ...] = (
    "bearer",
    "api_key_authorization",
    "api_key_header",
)
_AUTH_SCHEMES_PHASE_C: tuple[str, ...] = _AUTH_SCHEMES_CURRENT


def _build_auth_headers(
    scheme: str, token: str = "test-token-default"
) -> dict[str, str]:
    """Build an Authorization-style header dict for a given scheme.

    Schemes:

    - ``bearer`` — ``Authorization: Bearer <token>`` (current Clerk path)
    - ``api_key_authorization`` — ``Authorization: ApiKey <token>`` (Phase C)
    - ``api_key_header`` — ``X-API-Key: <token>`` (Phase C alt)

    Note: the Phase C schemes are NOT YET ACCEPTED by the backend. Tests that
    parameterize over them will fail (as 401) until Phase C lands the matching
    ``ApiKeyAuthAdapter`` and middleware update. This is by design — keeping
    the fixture in place lets us flip the scheme list at flag time without
    a test refactor.
    """
    if scheme == "bearer":
        return {"Authorization": f"Bearer {token}"}
    if scheme == "api_key_authorization":
        return {"Authorization": f"ApiKey {token}"}
    if scheme == "api_key_header":
        return {"X-API-Key": token}
    raise ValueError(f"Unknown auth scheme: {scheme!r}")


@pytest.fixture(params=_AUTH_SCHEMES_CURRENT, ids=lambda s: f"auth-{s}")
def auth_scheme(request: pytest.FixtureRequest) -> str:
    """Parametrized auth scheme — currently ``bearer`` only.

    To run a test against both Bearer and the Phase C api-key paths, override
    this in a test module or class with::

        pytestmark = pytest.mark.parametrize(
            "auth_scheme",
            ["bearer", "api_key_authorization", "api_key_header"],
            indirect=True,
        )

    The fixture is structured so when Phase C lands, switching the default
    parameter list in ``conftest.py`` is the only change needed to exercise
    every existing parametrized test against the new path.
    """
    scheme = request.param
    if not isinstance(scheme, str):
        raise TypeError(f"auth_scheme param must be str, got {type(scheme)}")
    return scheme


@pytest.fixture
def auth_headers_for_scheme(auth_scheme: str) -> dict[str, str]:
    """Auth headers for the currently-parametrized scheme.

    Use this in tests that should be exercised against every supported auth
    scheme (Bearer today; Bearer + ApiKey + X-API-Key in Phase C). For tests
    that are deliberately scoped to one scheme, use ``auth_headers`` (Bearer)
    or build headers directly.
    """
    return _build_auth_headers(auth_scheme)


@pytest.fixture(scope="module")
def vcr_config() -> dict[str, object]:
    """Configure pytest-recording for VCR cassettes.

    VCR cassettes allow recording HTTP interactions once and replaying them
    in subsequent test runs. This enables testing external API integrations
    without requiring real API keys or network access.

    Returns:
        Configuration dict for pytest-recording
    """
    return {
        "filter_headers": ["authorization", "x-api-key"],
        "record_mode": "none",  # Never record, only playback
        "match_on": ["uri", "method"],
        "decode_compressed_response": True,
        "cassette_library_dir": "tests/cassettes",
    }


@pytest_asyncio.fixture(autouse=True)
async def reset_global_singletons() -> AsyncGenerator[None, None]:
    """Reset global singleton dependencies between tests.

    This prevents test isolation issues where one test's market data
    adapter (with Redis/HTTP client connections) affects another test's
    behavior.

    The fixture runs automatically for all tests (autouse=True) and
    cleans up after each test completes, ensuring each test starts
    with a fresh state.
    """
    # Import here to avoid circular imports
    from zebu.adapters.inbound.api import dependencies

    # Run the test
    yield

    # Clean up after test - close any open connections first
    if dependencies._http_client is not None:
        await dependencies._http_client.aclose()

    if dependencies._redis_client is not None:
        await dependencies._redis_client.aclose()

    # Reset singletons to None
    dependencies._redis_client = None
    dependencies._http_client = None
