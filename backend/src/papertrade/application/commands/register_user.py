"""RegisterUser command - Register a new user account."""

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from pydantic import EmailStr

from papertrade.application.ports.user_repository import UserRepository
from papertrade.domain.entities.user import User
from papertrade.domain.exceptions import DuplicateEmailError
from papertrade.domain.services.password_service import PasswordService


@dataclass(frozen=True)
class RegisterUserCommand:
    """Input data for registering a new user.

    Attributes:
        email: User's email address (used for login)
        password: Plaintext password (will be hashed before storage)
    """

    email: EmailStr
    password: str


@dataclass(frozen=True)
class RegisterUserResult:
    """Result of registering a user.

    Attributes:
        user: The newly created User entity
    """

    user: User


class RegisterUserHandler:
    """Handler for RegisterUser command.

    Registers a new user account with email and password. Validates that
    email is unique and securely hashes the password before storage.
    """

    def __init__(
        self,
        user_repository: UserRepository,
        password_service: PasswordService,
    ) -> None:
        """Initialize handler with dependencies.

        Args:
            user_repository: Repository for user persistence
            password_service: Service for password hashing
        """
        self._user_repository = user_repository
        self._password_service = password_service

    async def execute(self, command: RegisterUserCommand) -> RegisterUserResult:
        """Execute the RegisterUser command.

        Args:
            command: Command with registration parameters

        Returns:
            Result containing the newly created User

        Raises:
            DuplicateEmailError: If email is already registered
            ValueError: If password is empty or invalid
        """
        # Validate password is not empty
        if not command.password or not command.password.strip():
            raise ValueError("Password cannot be empty")

        # Validate password length (minimum 8 characters)
        if len(command.password) < 8:
            raise ValueError("Password must be at least 8 characters")

        # Check if email already exists (case-insensitive)
        existing_user = await self._user_repository.get_by_email(command.email)
        if existing_user is not None:
            raise DuplicateEmailError(f"Email {command.email} is already registered")

        # Hash password
        hashed_password = self._password_service.hash_password(command.password)

        # Generate user ID and timestamp
        user_id = uuid4()
        now = datetime.now(UTC)

        # Create User entity
        user = User(
            id=user_id,
            email=command.email,
            hashed_password=hashed_password,
            created_at=now,
            is_active=True,
        )

        # Persist user
        created_user = await self._user_repository.create(user)

        return RegisterUserResult(user=created_user)
