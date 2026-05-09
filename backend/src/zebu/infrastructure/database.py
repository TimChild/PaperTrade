"""Database configuration and session management.

Provides database engine setup, connection pooling, and session management
for SQLModel repositories.
"""

import os
from collections.abc import AsyncGenerator
from typing import Annotated, Any

from fastapi import Depends
from sqlalchemy import event
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

# Database URL configuration
# For development/testing: SQLite (default)
# For production/Docker: PostgreSQL (configured via DATABASE_URL environment variable)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./papertrade.db")


# Create async engine
# DB_ECHO controls SQL statement logging (default: false).
# Set DB_ECHO=true for local debugging only — never in production
# (full queries + bind params are logged on every statement).
# SQLite-specific connect_args only applied when using SQLite
DB_ECHO = os.getenv("DB_ECHO", "false").lower() == "true"
engine_kwargs: dict[str, Any] = {"echo": DB_ECHO}
if "sqlite" in DATABASE_URL:
    # SQLite has no real pool; just allow cross-thread access.
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    # Postgres / async-network DB pool config:
    # - pool_pre_ping: validate connections before checkout, recover from
    #   server-side idle timeouts and DB restarts during deploys.
    # - pool_recycle: proactively recycle connections every 30 min to avoid
    #   accumulating long-lived idle connections.
    # - pool_size / max_overflow: tunable via env for scale-up; defaults
    #   chosen for a single-node Phase B workload (FastAPI + scheduler).
    engine_kwargs["pool_pre_ping"] = True
    engine_kwargs["pool_recycle"] = int(os.getenv("DB_POOL_RECYCLE", "1800"))
    engine_kwargs["pool_size"] = int(os.getenv("DB_POOL_SIZE", "10"))
    engine_kwargs["max_overflow"] = int(os.getenv("DB_MAX_OVERFLOW", "20"))

engine = create_async_engine(DATABASE_URL, **engine_kwargs)


# SQLite has FK enforcement disabled by default; turn it on so dev/test
# behaves like production Postgres (which always enforces declared FKs).
# The decorator registers _enable_sqlite_fks as a connection event handler;
# it's not called directly from this module (hence the pyright suppression).
if "sqlite" in DATABASE_URL:

    @event.listens_for(engine.sync_engine, "connect")
    def _enable_sqlite_fks(  # pyright: ignore[reportUnusedFunction]
        dbapi_connection: object, _record: object
    ) -> None:
        cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


# Session factory for creating database sessions
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Keep objects usable after commit
)


async def init_db() -> None:
    """Initialize database by creating all tables.

    SQLite uses SQLModel's create_all for lightweight local/test setups.
    PostgreSQL environments rely on Alembic migrations for schema management.
    """
    if "sqlite" not in DATABASE_URL:
        return

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
