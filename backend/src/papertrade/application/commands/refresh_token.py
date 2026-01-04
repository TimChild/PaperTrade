"""RefreshToken command - Generate new tokens from a refresh token."""

from dataclasses import dataclass

from papertrade.application.ports.user_repository import UserRepository
from papertrade.application.services.jwt_service import JWTService
from papertrade.domain.exceptions import (
    InactiveUserError,
    InvalidTokenError,
    UserNotFoundError,
)


@dataclass(frozen=True)
class RefreshTokenCommand:
    """Input data for token refresh.

    Attributes:
        refresh_token: JWT refresh token
    """

    refresh_token: str


@dataclass(frozen=True)
class RefreshTokenResult:
    """Result of token refresh.

    Attributes:
        access_token: New JWT access token (short-lived, 15 minutes)
        refresh_token: New JWT refresh token (long-lived, 7 days)
        token_type: Token type (always "Bearer")
    """

    access_token: str
    refresh_token: str
    token_type: str = "Bearer"


class RefreshTokenHandler:
    """Handler for RefreshToken command.

    Validates a refresh token and generates new access and refresh tokens.
    This implements token rotation for enhanced security.
    """

    def __init__(
        self,
        user_repository: UserRepository,
        jwt_service: JWTService,
    ) -> None:
        """Initialize handler with dependencies.

        Args:
            user_repository: Repository for user lookup
            jwt_service: Service for JWT token operations
        """
        self._user_repository = user_repository
        self._jwt_service = jwt_service

    async def execute(self, command: RefreshTokenCommand) -> RefreshTokenResult:
        """Execute the RefreshToken command.

        Args:
            command: Command with refresh token

        Returns:
            Result containing new access and refresh tokens

        Raises:
            InvalidTokenError: If refresh token is invalid or expired
            UserNotFoundError: If user no longer exists
            InactiveUserError: If user account is inactive
        """
        # Decode and validate refresh token
        try:
            payload = self._jwt_service.decode_token(command.refresh_token)
        except InvalidTokenError as e:
            raise InvalidTokenError(f"Invalid refresh token: {e}") from e

        # Verify token type
        token_type = payload.get("type")
        if token_type != "refresh":
            raise InvalidTokenError(
                "Token is not a refresh token (expected type='refresh')"
            )

        # Extract user ID
        user_id = self._jwt_service.get_user_id_from_token(command.refresh_token)

        # Get user from database
        user = await self._user_repository.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError(f"User {user_id} not found")

        # Check if user is active
        if not user.is_active:
            raise InactiveUserError("User account is inactive")

        # Generate new tokens (token rotation)
        access_token = self._jwt_service.create_access_token(user.id)
        refresh_token = self._jwt_service.create_refresh_token(user.id)

        return RefreshTokenResult(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="Bearer",
        )
