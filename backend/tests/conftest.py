"""Pytest configuration and shared fixtures."""

from collections.abc import AsyncGenerator
from uuid import UUID

import pytest
import pytest_asyncio
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

# Import all models to ensure they're registered with SQLModel metadata.
# The trigger models must be imported *before* tables are created because
# the F-5 migration adds a FK ``transactions.trigger_id`` ->
# ``strategy_condition_triggers.id`` — table creation requires the
# target table to be present in the metadata.
from zebu.adapters.outbound.database.api_key_model import (  # noqa: F401
    ApiKeyModel,
)
from zebu.adapters.outbound.database.models import (  # noqa: F401
    BackfillTaskModel,
    BacktestRunModel,
    ExplorationTaskModel,
    JobExecutionModel,
    PortfolioModel,
    PortfolioSnapshotModel,
    StrategyActivationModel,
    StrategyConditionTriggerModel,
    StrategyModel,
    TransactionModel,
    TriggerFireRecordModel,
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
    """Create an in-memory SQLite engine for testing, with FK enforcement on.

    SQLite has FK checks off by default; we enable them via
    ``PRAGMA foreign_keys=ON`` on every new connection so tests catch
    referential-integrity violations the same way production Postgres
    would. This matches the long-standing behavior of the lower-level
    ``backend/tests/integration/conftest.py`` ``engine`` fixture.

    Production parity is the goal: FK ordering bugs (#287), missing-
    parent-row writes (#291), and the ``api_key_id`` audit-stamping
    chain all rely on FK enforcement to fail loudly in tests instead of
    in production. The catch-all in ``transaction_repository.save`` /
    ``save_all`` that previously translated every ``IntegrityError`` to
    ``DuplicateTransactionError`` has been narrowed to PK conflicts
    only (Task #216), so FK violations now propagate as expected.
    """
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )

    # Enforce FK constraints in SQLite (off by default).
    @event.listens_for(engine.sync_engine, "connect")
    def _enable_sqlite_fks(dbapi_connection: object, _record: object) -> None:
        cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    yield engine

    # Cleanup
    await engine.dispose()


@pytest_asyncio.fixture
async def test_engine_with_fks(
    test_engine: AsyncEngine,
) -> AsyncGenerator[AsyncEngine, None]:
    """Compatibility alias for ``test_engine`` — now identical.

    Historically (PR #292) ``test_engine_with_fks`` was the *only* FK-
    enforcing engine — the default ``test_engine`` had FKs off because
    turning them on globally surfaced ~17 pre-existing fixture violations
    plus one repo bug (``transaction_repository`` catching every
    ``IntegrityError`` as ``DuplicateTransactionError``). Task #216
    closed that gap, so the two fixtures are now equivalent. New tests
    should depend on ``test_engine`` directly; this alias is kept only
    to avoid churning the smoke-flow import in
    ``backend/tests/integration/test_mcp_smoke_flows.py``.
    """
    yield test_engine


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
        # Phase J / Task #214 — the portfolio-balance query also fetches
        # the previous trading day's close to compute daily change. The
        # handler now refuses to return a partial result, so without a
        # historical observation seeded the integration tests would all
        # see 503-fetching instead of 200 with concrete numbers. Seed a
        # second price point ~10 days back to cover that fetch.
        prev_seed_time = datetime.now(UTC) - timedelta(days=10)

        # Seed with default test prices
        test_prices = [
            PricePoint(
                ticker=Ticker("AAPL"),
                price=Money(Decimal("148.00"), "USD"),
                timestamp=prev_seed_time,
                source="database",
                interval="real-time",
            ),
            PricePoint(
                ticker=Ticker("AAPL"),
                price=Money(Decimal("150.00"), "USD"),
                timestamp=seed_time,
                source="database",
                interval="real-time",
            ),
            PricePoint(
                ticker=Ticker("GOOGL"),
                price=Money(Decimal("2780.00"), "USD"),
                timestamp=prev_seed_time,
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
                price=Money(Decimal("377.00"), "USD"),
                timestamp=prev_seed_time,
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

    # Phase C2: seed the default test API key directly into the SQL
    # ``api_keys`` table. Production code stamps ``api_key_id`` on every
    # write surface (transactions, strategies, activations, etc.) with
    # a FK reference to ``api_keys.id`` — with FK enforcement on (Task
    # #216) the SQL row must exist before any of those writes flush.
    #
    # The default test key (raw value: ``"test-token-default"``) hashes
    # to a stable value under the test pepper and is owned by
    # ``"test-user-default"`` — so the parameterized auth-scheme tests
    # resolve to the same user as the Bearer path.
    #
    # Both reads (auth lookup) and writes (HTTP-minted keys) go through
    # the real SQL repository now, matching production behavior. The
    # in-memory variant is no longer used here.
    from zebu.adapters.auth.api_key_adapter import ApiKeyAuthAdapter
    from zebu.adapters.auth.api_key_hasher import ApiKeyHasher
    from zebu.adapters.inbound.api.dependencies import (
        get_api_key_auth_adapter,
        get_api_key_repository,
    )
    from zebu.adapters.outbound.database.api_key_model import (
        ApiKeyModel as _ApiKeyModel,
    )
    from zebu.adapters.outbound.database.api_key_repository import (
        SQLModelApiKeyRepository,
    )

    _test_pepper = "test-api-key-pepper-do-not-use-in-production"
    _test_hasher = ApiKeyHasher(secret=_test_pepper)

    # Seed the default test API key into the SQL table once per fixture
    # instance. We do this synchronously via ``asyncio.run`` because the
    # ``client`` fixture itself is sync and we need the row in place
    # before any HTTP request runs.
    import asyncio
    from datetime import UTC, datetime
    from uuid import NAMESPACE_DNS, uuid4, uuid5

    from zebu.domain.value_objects.api_key_scope import ApiKeyScope

    _seed_key_id = uuid4()
    _seed_key_user_uuid = uuid5(NAMESPACE_DNS, "test-user-default")
    _seed_key_hash = _test_hasher.hash("test-token-default")

    async def _seed_default_api_key() -> None:
        async with AsyncSession(test_engine, expire_on_commit=False) as session:
            session.add(
                _ApiKeyModel(
                    id=_seed_key_id,
                    user_id=_seed_key_user_uuid,
                    clerk_user_id="test-user-default",
                    label="test-default",
                    key_hash=_seed_key_hash,
                    scopes=[
                        ApiKeyScope.READ.value,
                        ApiKeyScope.TRADE.value,
                        ApiKeyScope.ADMIN.value,
                    ],
                    created_at=datetime.now(UTC),
                )
            )
            await session.commit()

    asyncio.run(_seed_default_api_key())

    async def get_test_api_key_repository(
        session: AsyncSession = Depends(get_test_session),  # type: ignore[assignment]  # noqa: B008
    ) -> SQLModelApiKeyRepository:
        """SQL-backed API-key repository for tests (Task #216).

        Was previously an in-memory singleton, which broke the FK from
        ``transactions.api_key_id`` to ``api_keys.id`` once FK
        enforcement was turned on — minted keys lived in memory but the
        FK targets the SQL table. Switching to ``SQLModelApiKeyRepository``
        unifies reads/writes against the same source of truth as
        production.
        """
        return SQLModelApiKeyRepository(session)

    async def get_test_api_key_auth_adapter(
        repository: SQLModelApiKeyRepository = Depends(get_test_api_key_repository),  # type: ignore[assignment]  # noqa: B008
    ) -> ApiKeyAuthAdapter:
        """API-key auth adapter for tests, sharing the SQL repo."""
        return ApiKeyAuthAdapter(
            repository=repository,
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

    # Clean up after test - close any open connections first. The Redis
    # async client was opened in the request handler's event loop; the
    # pytest-asyncio teardown runs in a different loop, so a clean
    # ``aclose`` can raise ``RuntimeError: Event loop is closed`` on its
    # underlying transport. Swallow that — the connections will be GC'd
    # along with the references we null out below. (Pre-dates Task #216;
    # widened to also cover the http-client path which can fail the same
    # way under contention.)
    import contextlib

    if dependencies._http_client is not None:
        with contextlib.suppress(RuntimeError):
            await dependencies._http_client.aclose()

    if dependencies._redis_client is not None:
        with contextlib.suppress(RuntimeError):
            await dependencies._redis_client.aclose()

    # Reset singletons to None
    dependencies._redis_client = None
    dependencies._http_client = None
    # Phase F-6: reset the inbound rate-limiter singleton so each test
    # starts with a fresh per-key bucket state.
    dependencies._inbound_backtest_rate_limiter = None
