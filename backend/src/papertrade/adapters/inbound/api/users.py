"""User API routes.

Provides REST endpoints for user operations:
- Get current user profile
"""

from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel

from papertrade.adapters.inbound.api.dependencies import CurrentUserDep, SessionDep
from papertrade.adapters.outbound.database.user_repository import (
    SQLModelUserRepository,
)
from papertrade.application.queries.get_user import GetUserHandler, GetUserQuery

router = APIRouter(prefix="/users", tags=["users"])


# Response Models


class UserResponse(BaseModel):
    """User profile response."""

    id: UUID
    email: str
    created_at: str  # ISO 8601 format
    is_active: bool


# API Endpoints


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    user_id: CurrentUserDep,
    session: SessionDep,
) -> UserResponse:
    """Get current authenticated user's profile.

    Args:
        user_id: Current user ID from JWT token
        session: Database session

    Returns:
        UserResponse with user profile data

    Raises:
        401 Unauthorized: Invalid or missing token
        404 Not Found: User not found
    """
    user_repo = SQLModelUserRepository(session)
    handler = GetUserHandler(user_repo)

    query = GetUserQuery(user_id=user_id)
    result = await handler.execute(query)

    return UserResponse(
        id=result.user.id,
        email=result.user.email,
        created_at=result.user.created_at.isoformat(),
        is_active=result.user.is_active,
    )
