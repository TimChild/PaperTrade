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

    Supports two modes:
    1. Strict mode (default): Only accepts exact token matches
    2. Permissive mode (E2E): Accepts any token for a default test user

    Attributes:
        _users: Mapping of user IDs to AuthenticatedUser instances
        _tokens: Mapping of tokens to user IDs
        _permissive_mode: If True, accepts any token for default test user
        _default_user: User to return in permissive mode
    """

    def __init__(
        self,
        users: dict[str, AuthenticatedUser] | None = None,
        permissive_mode: bool = False,
        default_user: AuthenticatedUser | None = None,
    ) -> None:
        """Initialize the adapter with optional pre-populated users.

        Args:
            users: Optional dictionary of user_id -> AuthenticatedUser
            permissive_mode: If True, accepts any token for default_user
            default_user: User to return in permissive mode when no token match
        """
        self._users = users or {}
        self._tokens: dict[str, str] = {}  # token -> user_id
        self._permissive_mode = permissive_mode
        self._default_user = default_user

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

        In strict mode (default), only accepts exact token matches.
        In permissive mode (E2E testing), accepts any non-empty token
        and returns the default test user.

        Args:
            token: Authentication token to verify

        Returns:
            AuthenticatedUser: The authenticated user

        Raises:
            InvalidTokenError: If token is invalid or user not found
        """
        # Try exact token match first
        user_id = self._tokens.get(token)
        if user_id and user_id in self._users:
            return self._users[user_id]

        # In permissive mode, accept any non-empty token
        if self._permissive_mode and token and self._default_user:
            return self._default_user

        raise InvalidTokenError("Invalid token")

    async def get_user(self, user_id: str) -> AuthenticatedUser | None:
        """Get user by ID.

        Args:
            user_id: Unique user identifier

        Returns:
            AuthenticatedUser if found, None otherwise
        """
        return self._users.get(user_id)
