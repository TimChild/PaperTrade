"""FastAPI dependency injection.

Provides factory functions for repositories and other dependencies used by API routes.
"""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header

from papertrade.adapters.outbound.database.portfolio_repository import (
    SQLModelPortfolioRepository,
)
from papertrade.adapters.outbound.database.transaction_repository import (
    SQLModelTransactionRepository,
)
from papertrade.infrastructure.database import SessionDep


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


async def get_current_user_id(
    x_user_id: Annotated[str | None, Header()] = None,
) -> UUID:
    """Get current user ID from request headers.

    This is a mock implementation for Phase 1. In production, this would:
    - Validate JWT token
    - Extract user ID from token
    - Raise 401 if unauthorized

    For now, we accept a user ID via X-User-Id header for testing.

    Args:
        x_user_id: User ID from X-User-Id header

    Returns:
        User UUID

    Raises:
        HTTPException: 400 if X-User-Id header is missing or invalid
    """
    from fastapi import HTTPException

    if not x_user_id:
        raise HTTPException(
            status_code=400,
            detail="X-User-Id header is required (authentication not yet implemented)",
        )

    try:
        return UUID(x_user_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid X-User-Id header: must be a valid UUID, got '{x_user_id}'",
        )


# Type aliases for route dependency injection
PortfolioRepositoryDep = Annotated[
    SQLModelPortfolioRepository, Depends(get_portfolio_repository)
]
TransactionRepositoryDep = Annotated[
    SQLModelTransactionRepository, Depends(get_transaction_repository)
]
CurrentUserDep = Annotated[UUID, Depends(get_current_user_id)]
