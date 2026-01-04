"""LoginUser command - Authenticate a user and generate tokens."""

from dataclasses import dataclass

from pydantic import EmailStr

from papertrade.application.ports.user_repository import UserRepository
from papertrade.application.services.jwt_service import JWTService
from papertrade.domain.exceptions import (
    InactiveUserError,
    InvalidCredentialsError,
    UserNotFoundError,
)
from papertrade.domain.services.password_service import PasswordService


@dataclass(frozen=True)
class LoginUserCommand:
    """Input data for user login.

    Attributes:
        email: User's email address
        password: Plaintext password
    """

    email: EmailStr
    password: str


@dataclass(frozen=True)
class LoginUserResult:
    """Result of user login.

    Attributes:
        access_token: JWT access token (short-lived, 15 minutes)
        refresh_token: JWT refresh token (long-lived, 7 days)
        token_type: Token type (always "Bearer")
    """

    access_token: str
    refresh_token: str
    token_type: str = "Bearer"


class LoginUserHandler:
    """Handler for LoginUser command.

    Authenticates a user with email and password, then generates JWT tokens
    for API access.
    """

    def __init__(
        self,
        user_repository: UserRepository,
        password_service: PasswordService,
        jwt_service: JWTService,
    ) -> None:
        """Initialize handler with dependencies.

        Args:
            user_repository: Repository for user lookup
            password_service: Service for password verification
            jwt_service: Service for JWT token generation
        """
        self._user_repository = user_repository
        self._password_service = password_service
        self._jwt_service = jwt_service

    async def execute(self, command: LoginUserCommand) -> LoginUserResult:
        """Execute the LoginUser command.

        Args:
            command: Command with login credentials

        Returns:
            Result containing access and refresh tokens

        Raises:
            InvalidCredentialsError: If email or password is incorrect
            InactiveUserError: If user account is inactive
        """
        # Find user by email (case-insensitive)
        user = await self._user_repository.get_by_email(command.email)
        if user is None:
            # Don't reveal whether email exists (prevent user enumeration)
            raise InvalidCredentialsError("Incorrect email or password")

        # Verify password
        is_valid = self._password_service.verify_password(
            command.password, user.hashed_password
        )
        if not is_valid:
            raise InvalidCredentialsError("Incorrect email or password")

        # Check if user is active
        if not user.is_active:
            raise InactiveUserError("User account is inactive")

        # Generate tokens
        access_token = self._jwt_service.create_access_token(user.id)
        refresh_token = self._jwt_service.create_refresh_token(user.id)

        return LoginUserResult(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="Bearer",
        )
