"""User entity - Represents an authenticated user."""

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from pydantic import EmailStr

from papertrade.domain.exceptions import InvalidEntityError


class InvalidUserError(InvalidEntityError):
    """Raised when User entity invariants are violated."""

    pass


@dataclass(frozen=True)
class User:
    """Represents an authenticated user in the system.

    User is an entity with identity and lifecycle. It manages user authentication
    credentials and profile information. User is fully immutable after creation.

    Attributes:
        id: Unique user identifier
        email: User's email address (used for login, must be unique)
        hashed_password: Bcrypt hashed password (never store plaintext)
        created_at: When user account was created (UTC timezone)
        is_active: Whether the user account is active (can login)

    Raises:
        InvalidUserError: If invariants are violated
    """

    id: UUID
    email: EmailStr
    hashed_password: str
    created_at: datetime
    is_active: bool = True

    def __post_init__(self) -> None:
        """Validate User invariants after initialization."""
        # Validate email is not empty
        if not self.email:
            raise InvalidUserError("User email cannot be empty")

        # Validate hashed_password is not empty
        if not self.hashed_password or not self.hashed_password.strip():
            raise InvalidUserError("User hashed_password cannot be empty")

        # Validate created_at is not in future
        now = datetime.now(UTC)
        created_at_utc = (
            self.created_at
            if self.created_at.tzinfo is not None
            else self.created_at.replace(tzinfo=UTC)
        )

        if created_at_utc > now:
            raise InvalidUserError("User created_at cannot be in the future")

    def __eq__(self, other: object) -> bool:
        """Equality based on ID only.

        Args:
            other: Object to compare

        Returns:
            True if other is User with same ID
        """
        if not isinstance(other, User):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        """Hash based on ID for use in dicts/sets.

        Returns:
            Hash of user ID
        """
        return hash(self.id)

    def __repr__(self) -> str:
        """Return repr for debugging.

        Returns:
            String like "User(id=UUID('...'), email='user@example.com')"
        """
        return f"User(id={self.id}, email='{self.email}', is_active={self.is_active})"
