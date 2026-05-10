"""Authentication port interface.

Defines the contract for authentication operations following the ports and
adapters pattern. Implementations can use Clerk, in-memory storage for
testing, or other authentication providers.
"""

from dataclasses import dataclass, field
from typing import Literal, Protocol
from uuid import UUID

# The auth path that produced an :class:`AuthenticatedUser`.
#
# - ``"clerk"`` — Clerk Bearer JWT (a human in a browser).
# - ``"api_key"`` — :class:`ApiKeyAuthAdapter` (a machine identity:
#   agent, scheduled task, MCP server).
#
# Two paths today; future federated providers would add their own value.
AuthMethod = Literal["clerk", "api_key"]


@dataclass(frozen=True)
class AuthenticatedUser:
    """User identity from authentication provider.

    Represents a verified user identity returned after successful token
    validation. Carries the originating auth path on every response so
    downstream code (logging, future rate-limit hooks, audit trails) can
    differentiate between a human request and a machine-identity request
    without re-inspecting the inbound headers.

    The shape is path-agnostic: route handlers continue to treat
    ``AuthenticatedUser`` as a single uniform identity. Per Phase H5 of
    the agent-platform proposal, when an API-key request hits the
    backend the ``api_key_id`` and ``api_key_label`` fields are
    populated; on the Clerk path they stay ``None`` and ``auth_method``
    is ``"clerk"``.

    Attributes:
        id: Unique user identifier from the auth provider (the Clerk
            user-id string, e.g. ``"user_2abc123"``). The same value is
            returned regardless of which auth path produced it — see
            :class:`zebu.adapters.auth.api_key_adapter.ApiKeyAuthAdapter`
            for how this is round-tripped on the API-key path.
        email: User's email address (empty string on the API-key path —
            machine identities have no inherent email).
        auth_method: How the request authenticated. Defaults to
            ``"clerk"`` so existing call sites that build
            ``AuthenticatedUser`` directly (Clerk + InMemory adapters)
            don't need to be updated.
        api_key_id: When ``auth_method == "api_key"``, the persisted
            :class:`zebu.domain.entities.api_key.ApiKey` ID that
            authorised the request. ``None`` on the Clerk path.
        api_key_label: When ``auth_method == "api_key"``, the
            human-readable label of the key (e.g.
            ``"claude-code-laptop-explorer"``). This is the **identity
            column** for the activity feed (Phase H2) and rate limiter
            (Phase F): a single human user can mint multiple keys with
            different labels and have them surface independently in
            observability. ``None`` on the Clerk path.
    """

    id: str  # Clerk user ID (string format, e.g., "user_2abc123")
    email: str
    auth_method: AuthMethod = field(default="clerk")
    api_key_id: UUID | None = field(default=None)
    api_key_label: str | None = field(default=None)


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
