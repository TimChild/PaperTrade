"""Authentication port interface.

Defines the contract for authentication operations following the ports and
adapters pattern. Implementations can use Clerk, in-memory storage for
testing, or other authentication providers.
"""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class AuthenticatedUser:
    """User identity from authentication provider.

    Represents a verified user identity returned after successful token
    validation. This is a minimal representation focused on what the
    application needs from the authentication provider.

    Attributes:
        id: Unique user identifier from the auth provider (e.g., Clerk user ID)
        email: User's email address
    """

    id: str  # Clerk user ID (string format, e.g., "user_2abc123")
    email: str


class AuthPort(Protocol):
    """Port for authentication operations.

    This protocol defines the contract that authentication adapters must
    implement. It follows the Dependency Inversion Principle by having
    the domain/application layer define the interface it needs, rather
    than depending on external authentication implementations.
    """

    async def verify_token(self, token: str) -> AuthenticatedUser:
        """Verify authentication token and return user identity.

        Validates the provided token with the authentication provider and
        returns the authenticated user's information.

        Args:
            token: Authentication token (typically a JWT)

        Returns:
            AuthenticatedUser: Verified user identity

        Raises:
            InvalidTokenError: If token is invalid, expired, or malformed
        """
        ...

    async def get_user(self, user_id: str) -> AuthenticatedUser | None:
        """Get user by ID.

        Retrieves user information from the authentication provider.

        Args:
            user_id: Unique user identifier

        Returns:
            AuthenticatedUser if found, None otherwise
        """
        ...
