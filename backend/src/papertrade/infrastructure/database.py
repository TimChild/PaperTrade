"""Database configuration and session management.

Provides database engine setup, connection pooling, and session management
for SQLModel repositories.
"""

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

# Database URL configuration
# For development/testing: SQLite
# For production: PostgreSQL (configured via environment variables)
DATABASE_URL = "sqlite+aiosqlite:///./papertrade.db"


# Create async engine
# echo=True logs all SQL statements (useful for development)
# connect_args for SQLite compatibility
engine = create_async_engine(
    DATABASE_URL,
    echo=True,  # Log SQL statements
    connect_args={"check_same_thread": False},  # SQLite specific
)


# Session factory for creating database sessions
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Keep objects usable after commit
)


async def init_db() -> None:
    """Initialize database by creating all tables.

    This should be called on application startup.
    In production, use Alembic migrations instead.
    """
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database sessions.

    Yields:
        AsyncSession: Database session that automatically commits on success
                      and rolls back on exception.

    Example:
        ```python
        @router.get("/portfolios/{id}")
        async def get_portfolio(
            id: UUID,
            session: Annotated[AsyncSession, Depends(get_session)]
        ):
            # Use session here
            result = await session.execute(...)
        ```
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# Type alias for session dependency
SessionDep = Annotated[AsyncSession, Depends(get_session)]
