"""Pytest configuration and shared fixtures."""

from collections.abc import AsyncGenerator
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel

from papertrade.infrastructure.database import get_session
from papertrade.main import app

# Import all models to ensure they're registered with SQLModel metadata
from papertrade.adapters.outbound.database.models import (  # noqa: F401
    PortfolioModel,
    TransactionModel,
)
from papertrade.adapters.outbound.models.price_history import (  # noqa: F401
    PriceHistoryModel,
)
from papertrade.adapters.outbound.models.ticker_watchlist import (  # noqa: F401
    TickerWatchlistModel,
)


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

    Overrides the application's database session to use an in-memory test database
    and the market data adapter to use an in-memory implementation. This ensures
    integration tests are fast and don't require external dependencies (Redis, API keys).
    """
    from papertrade.adapters.inbound.api.dependencies import get_market_data
    from papertrade.adapters.outbound.market_data.in_memory_adapter import (
        InMemoryMarketDataAdapter,
    )

    async def get_test_session() -> AsyncGenerator[AsyncSession, None]:
        """Override session dependency to use test database."""
        async with AsyncSession(test_engine, expire_on_commit=False) as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    def get_test_market_data() -> InMemoryMarketDataAdapter:
        """Override market data dependency to use in-memory adapter.
        
        Seeds the adapter with default test prices for common tickers.
        """
        from datetime import UTC, datetime
        from decimal import Decimal
        
        from papertrade.application.dtos.price_point import PricePoint
        from papertrade.domain.value_objects.money import Money
        from papertrade.domain.value_objects.ticker import Ticker
        
        adapter = InMemoryMarketDataAdapter()
        
        # Seed with default test prices
        test_prices = [
            PricePoint(
                ticker=Ticker("AAPL"),
                price=Money(Decimal("150.00"), "USD"),
                timestamp=datetime.now(UTC),
                source="database",
                interval="real-time",
            ),
            PricePoint(
                ticker=Ticker("GOOGL"),
                price=Money(Decimal("2800.00"), "USD"),
                timestamp=datetime.now(UTC),
                source="database",
                interval="real-time",
            ),
            PricePoint(
                ticker=Ticker("MSFT"),
                price=Money(Decimal("380.00"), "USD"),
                timestamp=datetime.now(UTC),
                source="database",
                interval="real-time",
            ),
        ]
        
        adapter.seed_prices(test_prices)
        return adapter

    # Override dependencies
    app.dependency_overrides[get_session] = get_test_session
    app.dependency_overrides[get_market_data] = get_test_market_data

    with TestClient(app) as test_client:
        yield test_client

    # Clean up overrides
    app.dependency_overrides.clear()


@pytest.fixture
def default_user_id() -> UUID:
    """Provide a default user ID for tests."""
    return uuid4()


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
    from papertrade.adapters.inbound.api import dependencies

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
    dependencies._market_data_adapter = None
