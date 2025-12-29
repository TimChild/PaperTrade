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
    """Create a test client with test database.
    
    Overrides the application's database session to use an in-memory test database.
    This allows integration tests to run against a clean database for each test.
    """

    async def get_test_session() -> AsyncGenerator[AsyncSession, None]:
        """Override session dependency to use test database."""
        async with AsyncSession(test_engine, expire_on_commit=False) as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    # Override the database session dependency
    app.dependency_overrides[get_session] = get_test_session

    with TestClient(app) as test_client:
        yield test_client

    # Clean up overrides
    app.dependency_overrides.clear()


@pytest.fixture
def default_user_id() -> UUID:
    """Provide a default user ID for tests."""
    return uuid4()
