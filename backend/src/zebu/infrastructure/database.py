"""Database configuration and session management.

Provides database engine setup, connection pooling, and session management
for SQLModel repositories.
"""

import os
from collections.abc import AsyncGenerator
from typing import Annotated, Any

from fastapi import Depends
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

# Database URL configuration
# For development/testing: SQLite (default)
# For production/Docker: PostgreSQL (configured via DATABASE_URL environment variable)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./papertrade.db")
DB_AUTO_CREATE = os.getenv("DB_AUTO_CREATE", "").lower() in {"1", "true", "yes"}


# Create async engine
# echo=True logs all SQL statements (useful for development)
# SQLite-specific connect_args only applied when using SQLite
engine_kwargs: dict[str, Any] = {"echo": True}
if "sqlite" in DATABASE_URL:
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_async_engine(DATABASE_URL, **engine_kwargs)


# Session factory for creating database sessions
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Keep objects usable after commit
)


def should_auto_create_schema(
    *,
    database_url: str,
    db_auto_create: bool,
    has_alembic_version_table: bool,
) -> bool:
    """Decide whether SQLModel should bootstrap tables on startup.

    SQLite always uses ``create_all()``. PostgreSQL normally relies on Alembic,
    but legacy or brand-new databases without an ``alembic_version`` table still
    need the original bootstrap behavior so later migrations have the core tables
    they expect.
    """
    if "sqlite" in database_url or db_auto_create:
        return True

    return not has_alembic_version_table


async def init_db() -> None:
    """Initialize database by creating all tables.

    This should be called on application startup.
    SQLite always uses SQLModel's create_all. PostgreSQL prefers Alembic, but
    still bootstraps core tables when no alembic history exists yet.
    """
    async with engine.begin() as conn:
        has_alembic_version_table = await conn.run_sync(
            lambda sync_conn: inspect(sync_conn).has_table("alembic_version")
        )

        if not should_auto_create_schema(
            database_url=DATABASE_URL,
            db_auto_create=DB_AUTO_CREATE,
            has_alembic_version_table=has_alembic_version_table,
        ):
            return

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
