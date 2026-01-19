"""In-memory authentication adapter for testing.

Provides a simple in-memory implementation of AuthPort that doesn't require
external dependencies. Ideal for unit and integration tests.
"""

from zebu.application.ports.auth_port import AuthenticatedUser, AuthPort
from zebu.domain.exceptions import InvalidTokenError


class InMemoryAuthAdapter(AuthPort):
    """In-memory authentication adapter for testing.

    Stores users and tokens in memory without requiring Clerk or any external
    authentication service. This adapter enables fast, deterministic tests
    without network dependencies.

    Attributes:
        _users: Mapping of user IDs to AuthenticatedUser instances
        _tokens: Mapping of tokens to user IDs
    """

    def __init__(self, users: dict[str, AuthenticatedUser] | None = None) -> None:
        """Initialize the adapter with optional pre-populated users.

        Args:
            users: Optional dictionary of user_id -> AuthenticatedUser
        """
        self._users = users or {}
        self._tokens: dict[str, str] = {}  # token -> user_id

    def add_user(self, user: AuthenticatedUser, token: str) -> None:
        """Add a user with their token for testing.

        This method is for test setup only, allowing tests to configure
        valid users and tokens before making authenticated requests.

        Args:
            user: The authenticated user to add
            token: The token that will authenticate this user
        """
        self._users[user.id] = user
        self._tokens[token] = user.id

    async def verify_token(self, token: str) -> AuthenticatedUser:
        """Verify authentication token and return user identity.

        Args:
            token: Authentication token to verify

        Returns:
            AuthenticatedUser: The authenticated user

        Raises:
            InvalidTokenError: If token is invalid or user not found
        """
        user_id = self._tokens.get(token)
        if not user_id or user_id not in self._users:
            raise InvalidTokenError("Invalid token")
        return self._users[user_id]

    async def get_user(self, user_id: str) -> AuthenticatedUser | None:
        """Get user by ID.

        Args:
            user_id: Unique user identifier

        Returns:
            AuthenticatedUser if found, None otherwise
        """
        return self._users.get(user_id)
