"""Authentication API routes.

Provides REST endpoints for user authentication:
- Register new user
- Login with email/password
- Refresh access token
"""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr

from papertrade.adapters.inbound.api.dependencies import SessionDep
from papertrade.adapters.outbound.database.user_repository import (
    SQLModelUserRepository,
)
from papertrade.application.commands.login_user import (
    LoginUserCommand,
    LoginUserHandler,
)
from papertrade.application.commands.refresh_token import (
    RefreshTokenCommand,
    RefreshTokenHandler,
)
from papertrade.application.commands.register_user import (
    RegisterUserCommand,
    RegisterUserHandler,
)
from papertrade.application.services.jwt_service import JWTService
from papertrade.domain.services.password_service import PasswordService
from papertrade.infrastructure.settings import get_settings

router = APIRouter(prefix="/auth", tags=["authentication"])


# Request/Response Models


class RegisterRequest(BaseModel):
    """Request to register a new user."""

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Response containing JWT tokens."""

    access_token: str
    refresh_token: str
    token_type: str = "Bearer"


class RefreshRequest(BaseModel):
    """Request to refresh access token."""

    refresh_token: str


# Dependency Providers


def get_jwt_service() -> JWTService:
    """Provide JWT service with settings."""
    settings = get_settings()
    return JWTService(
        secret_key=settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
        access_token_expire_minutes=settings.access_token_expire_minutes,
        refresh_token_expire_days=settings.refresh_token_expire_days,
    )


def get_password_service() -> PasswordService:
    """Provide password service."""
    return PasswordService()


# API Endpoints


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    session: SessionDep,
    password_service: Annotated[PasswordService, Depends(get_password_service)],
) -> dict[str, str]:
    """Register a new user account.

    Args:
        request: Registration details (email, password)
        session: Database session
        password_service: Password hashing service

    Returns:
        Success message with user email

    Raises:
        409 Conflict: Email already registered
        400 Bad Request: Invalid email or password
    """
    user_repo = SQLModelUserRepository(session)
    handler = RegisterUserHandler(user_repo, password_service)

    command = RegisterUserCommand(email=request.email, password=request.password)
    result = await handler.execute(command)

    return {"message": "User registered successfully", "email": result.user.email}


@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: SessionDep,
    password_service: Annotated[PasswordService, Depends(get_password_service)],
    jwt_service: Annotated[JWTService, Depends(get_jwt_service)],
) -> TokenResponse:
    """Login with email and password.

    Args:
        form_data: OAuth2 form with username (email) and password
        session: Database session
        password_service: Password verification service
        jwt_service: JWT token generation service

    Returns:
        TokenResponse with access and refresh tokens

    Raises:
        401 Unauthorized: Invalid credentials or inactive account
    """
    user_repo = SQLModelUserRepository(session)
    handler = LoginUserHandler(user_repo, password_service, jwt_service)

    # OAuth2PasswordRequestForm uses 'username' field for email
    command = LoginUserCommand(email=form_data.username, password=form_data.password)
    result = await handler.execute(command)

    return TokenResponse(
        access_token=result.access_token,
        refresh_token=result.refresh_token,
        token_type=result.token_type,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: RefreshRequest,
    session: SessionDep,
    jwt_service: Annotated[JWTService, Depends(get_jwt_service)],
) -> TokenResponse:
    """Refresh access token using refresh token.

    Args:
        request: Refresh token
        session: Database session
        jwt_service: JWT token operations service

    Returns:
        TokenResponse with new access and refresh tokens

    Raises:
        401 Unauthorized: Invalid or expired refresh token
        404 Not Found: User no longer exists
    """
    user_repo = SQLModelUserRepository(session)
    handler = RefreshTokenHandler(user_repo, jwt_service)

    command = RefreshTokenCommand(refresh_token=request.refresh_token)
    result = await handler.execute(command)

    return TokenResponse(
        access_token=result.access_token,
        refresh_token=result.refresh_token,
        token_type=result.token_type,
    )
